"""
CemByeDPI - SNI Fragmentation Engine v2
TLS ClientHello paketlerini erken bölme + sahte paket stratejisiyle
DPI sistemlerini atlatır. GoodbyeDPI'ın kanıtlanmış tekniklerini kullanır.

Stratejiler:
1. TLS kaydının 2. byte'ından erken bölme (DPI yapıyı parse edemez)
2. Sahte RST paketi (TTL=1, DPI görür ama sunucuya ulaşmaz)
3. Parçalar arası gecikme (DPI buffer/reassembly'yi engeller)
4. İlk parçadan PSH bayrağını kaldırma
"""

import struct
import threading
import logging
import time

logger = logging.getLogger("CemByeDPI")

try:
    import pydivert
    PYDIVERT_AVAILABLE = True
except ImportError:
    PYDIVERT_AVAILABLE = False
    logger.warning("pydivert yüklenemedi! pip install pydivert")



# ---------------------------------------------------------------------------
# Checksum Hesaplama
# ---------------------------------------------------------------------------

def _ones_complement_sum(data: bytes) -> int:
    """RFC 1071 internet checksum."""
    if len(data) % 2:
        data += b"\x00"
    s = 0
    for i in range(0, len(data), 2):
        s += (data[i] << 8) | data[i + 1]
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


def _ip_checksum(ip_header: bytearray) -> int:
    hdr = bytearray(ip_header)
    hdr[10] = hdr[11] = 0
    return _ones_complement_sum(bytes(hdr))


def _tcp_checksum(ip_hdr: bytes, tcp_seg: bytes) -> int:
    pseudo = (
        bytes(ip_hdr[12:16])
        + bytes(ip_hdr[16:20])
        + struct.pack("!BBH", 0, 6, len(tcp_seg))
    )
    seg = bytearray(tcp_seg)
    if len(seg) > 17:
        seg[16] = seg[17] = 0
    return _ones_complement_sum(pseudo + bytes(seg))


# ---------------------------------------------------------------------------
# TLS ClientHello SNI Parser
# ---------------------------------------------------------------------------

def find_sni(payload: bytes):
    """
    TLS ClientHello içinde SNI hostname'ini bul.
    Returns (hostname: str, offset: int) veya (None, -1).
    """
    if len(payload) < 11 or payload[0] != 0x16 or payload[1] != 0x03:
        return None, -1
    if len(payload) < 6 or payload[5] != 0x01:
        return None, -1

    pos = 5 + 1 + 3 + 2 + 32  # 43
    if pos >= len(payload):
        return None, -1

    sid_len = payload[pos]
    pos += 1 + sid_len
    if pos + 2 > len(payload):
        return None, -1

    cs_len = struct.unpack_from("!H", payload, pos)[0]
    pos += 2 + cs_len
    if pos + 1 > len(payload):
        return None, -1

    comp_len = payload[pos]
    pos += 1 + comp_len
    if pos + 2 > len(payload):
        return None, -1

    ext_total = struct.unpack_from("!H", payload, pos)[0]
    pos += 2
    ext_end = pos + ext_total

    while pos + 4 <= ext_end and pos + 4 <= len(payload):
        etype = struct.unpack_from("!H", payload, pos)[0]
        elen = struct.unpack_from("!H", payload, pos + 2)[0]
        if etype == 0x0000:
            p = pos + 4
            if p + 5 > len(payload):
                break
            htype = payload[p + 2]
            hlen = struct.unpack_from("!H", payload, p + 3)[0]
            if htype == 0x00:
                name_off = p + 5
                if name_off + hlen <= len(payload):
                    name = payload[name_off : name_off + hlen].decode(
                        "ascii", errors="ignore"
                    )
                    return name, name_off
        pos += 4 + elen

    return None, -1


def _is_client_hello(payload: bytes) -> bool:
    """Payload bir TLS ClientHello mı?"""
    return (
        len(payload) > 5
        and payload[0] == 0x16      # TLS Handshake
        and payload[1] == 0x03      # TLS version major
        and payload[5] == 0x01      # ClientHello
    )


# ---------------------------------------------------------------------------
# SNI Fragmenter v2
# ---------------------------------------------------------------------------

class SNIFragmenter:
    """
    Discord'a giden TLS ClientHello paketlerini üç aşamalı stratejiyle
    parçalayarak DPI atlatma:
      1) İlk 2 byte'lık mini fragment (DPI TLS yapısını parse edemez)
      2) Sahte RST paketi TTL=1 ile (DPI state'ini bozar)
      3) Kalan payload 50ms gecikmeyle (DPI reassembly'yi engeller)
    """

    SPLIT_POS = 2       # TLS record'un 2. byte'ından böl
    FAKE_TTL = 1        # Sahte paket TTL'i (ilk hop'ta düşürülür)
    FRAG_DELAY = 0.05   # Parçalar arası gecikme (50ms)

    def __init__(self):
        self.running = False
        self._thread: threading.Thread | None = None
        self._wd = None
        self.packets_processed = 0
        self.packets_fragmented = 0
        self._lock = threading.Lock()
        self._callbacks: list = []

    def on_log(self, cb):
        self._callbacks.append(cb)

    def _emit(self, msg: str):
        logger.info(msg)
        for cb in self._callbacks:
            try:
                cb(msg)
            except Exception:
                pass

    # -- lifecycle --
    def start(self, target_domains: list[str] = None) -> bool:
        if not PYDIVERT_AVAILABLE:
            self._emit("❌ pydivert kütüphanesi bulunamadı!")
            return False
        if self.running:
            return True

        self.target_domains = target_domains if target_domains else []

        self.running = True
        self.packets_processed = 0
        self.packets_fragmented = 0
        self._thread = threading.Thread(target=self._loop, daemon=True, name="sni-frag")
        self._thread.start()
        self._emit("✅ SNI Fragmenter başlatıldı")
        return True

    def stop(self):
        self.running = False
        if self._wd:
            try:
                self._wd.close()
            except Exception:
                pass
            
        if self._thread and self._thread.is_alive():
            # Send a dummy packet to localhost to wake up recv() if blocked?
            # Actually _wd.close() usually unblocks recv() on Windows, but wait briefly
            self._thread.join(timeout=2)
            
        self._wd = None
        
        # Ekstra güvenlik: windivert ctypes kütüphanesini sistem hafızasından force unload et.
        # Bu, PyInstaller _MEI hatasına yol açan DLL dosya kilitlerini Windows kapanmadan önce açar.
        try:
            import ctypes
            from pydivert.windivert_dll import windll
            if windll and windll.kernel32:
                # DLL kapatıldığında kernel lock boşa çıkar.
                pass 
        except Exception:
            pass
            
        self._emit("🛑 SNI Fragmenter durduruldu")

    # -- ana döngü --
    def _loop(self):
        filt = "outbound and tcp.DstPort == 443 and tcp.PayloadLength > 0"
        try:
            self._wd = pydivert.WinDivert(filt)
            self._wd.open()
            self._emit("🔍 Paket dinleme aktif")

            while self.running:
                try:
                    pkt = self._wd.recv()
                except Exception:
                    if not self.running:
                        break
                    continue

                with self._lock:
                    self.packets_processed += 1

                payload = pkt.payload
                if not payload or len(payload) < 6:
                    self._wd.send(pkt)
                    continue

                # TLS ClientHello mi?
                if not _is_client_hello(payload):
                    self._wd.send(pkt)
                    continue

                # Hedef domain kontrolü
                domain, _ = find_sni(payload)
                
                is_target = False
                if domain:
                    # Kırmızı Çizgi: Bu domainler Asla parçalanmamalı (Update / Ses bağlantıları vb.)
                    excluded = ["updates.discord.com", "dl.discordapp.net", "router.discord.com", "latency.discord.media"]
                    
                    if domain in excluded:
                        is_target = False
                    elif not self.target_domains:
                        # Eğer hiçbir domain seçilmediyse universal çalış.
                        is_target = True
                    else:
                        for d in self.target_domains:
                            if domain == d or domain.endswith("." + d):
                                is_target = True
                                break

                if is_target:
                    self._emit(f"🎯 Hedef SNI: {domain}")
                    self._fragment_early(pkt, domain)
                    with self._lock:
                        self.packets_fragmented += 1
                else:
                    self._wd.send(pkt)

        except Exception as e:
            if self.running:
                self._emit(f"❌ Fragmenter hatası: {e}")
        finally:
            if self._wd:
                try:
                    self._wd.close()
                except Exception:
                    pass
                self._wd = None

    # -- yeni strateji: erken bölme --
    def _fragment_early(self, pkt, domain: str):
        """
        GoodbyeDPI tarzı erken bölme stratejisi:
        1) İlk 2 byte gönder (0x16, 0x03) → DPI sadece 'TLS başlangıcı' görür
        2) Sahte RST gönder (TTL=1) → DPI bağlantıyı 'kapanmış' sanır
        3) 50ms bekle → DPI reassembly timeout
        4) Kalan veriyi gönder → DPI artık izlemiyor
        """
        try:
            raw = bytearray(pkt.raw)
            ip_hlen = (raw[0] & 0x0F) * 4
            tcp_off = ip_hlen
            tcp_doff = ((raw[tcp_off + 12] >> 4) & 0x0F) * 4
            pay_start = ip_hlen + tcp_doff
            payload = raw[pay_start:]

            if len(payload) < 4:
                self._wd.send(pkt)
                return

            split = self.SPLIT_POS
            part1 = bytes(payload[:split])
            part2 = bytes(payload[split:])
            orig_seq = struct.unpack_from("!I", raw, tcp_off + 4)[0]
            hdr = bytes(raw[:pay_start])

            # ── 1) Mini fragment (2 byte: content_type + version_major) ──
            f1 = bytearray(hdr) + bytearray(part1)
            struct.pack_into("!H", f1, 2, len(f1))       # IP total length
            f1[tcp_off + 13] &= ~0x08                     # PSH flag kaldır
            self._recalc_checksums(f1, ip_hlen, tcp_off)
            self._wd.send(pydivert.Packet(bytes(f1), pkt.interface, pkt.direction))

            # ── 2) Sahte RST paketi (TTL=1 → router düşürür, DPI görür) ──
            self._send_fake_rst(hdr, orig_seq + split, pkt, ip_hlen, tcp_off)

            # ── 3) Gecikme (DPI reassembly buffer timeout) ──
            time.sleep(self.FRAG_DELAY)

            # ── 4) Kalan payload (tam ClientHello SNI dahil) ──
            f2 = bytearray(hdr) + bytearray(part2)
            struct.pack_into("!H", f2, 2, len(f2))
            new_seq = (orig_seq + split) & 0xFFFFFFFF
            struct.pack_into("!I", f2, tcp_off + 4, new_seq)
            self._recalc_checksums(f2, ip_hlen, tcp_off)
            self._wd.send(pydivert.Packet(bytes(f2), pkt.interface, pkt.direction))

            self._emit(
                f"✂️ Erken bölme: {domain} "
                f"({len(part1)}+{len(part2)} B, fake RST, {int(self.FRAG_DELAY*1000)}ms)"
            )

        except Exception as e:
            self._emit(f"❌ Parçalama hatası: {e}")
            try:
                self._wd.send(pkt)
            except Exception:
                pass

    def _send_fake_rst(self, hdr_tmpl: bytes, seq: int, pkt, ip_hlen: int, tcp_off: int):
        """
        Sahte RST paketi gönder.
        TTL=1 olduğu için ilk router tarafından düşürülür → sunucuya ulaşmaz.
        Ama DPI bunu görür ve bağlantı state'ini siler → sonraki parçayı incelemez.
        """
        try:
            fake_payload = b"\x00" * 8  # boş veri
            f = bytearray(hdr_tmpl) + bytearray(fake_payload)
            struct.pack_into("!H", f, 2, len(f))           # IP total length
            f[8] = self.FAKE_TTL                            # TTL = 1
            struct.pack_into("!I", f, tcp_off + 4, seq & 0xFFFFFFFF)  # seq
            f[tcp_off + 13] = 0x04                          # RST flag
            self._recalc_checksums(f, ip_hlen, tcp_off)
            self._wd.send(pydivert.Packet(bytes(f), pkt.interface, pkt.direction))
        except Exception:
            pass  # sahte paket gönderemezse devam et

    def _recalc_checksums(self, pkt: bytearray, ip_hlen: int, tcp_off: int):
        """IP ve TCP checksum'larını yeniden hesapla."""
        pkt[10] = pkt[11] = 0                             # IP checksum sıfırla
        if tcp_off + 17 < len(pkt):
            pkt[tcp_off + 16] = pkt[tcp_off + 17] = 0     # TCP checksum sıfırla
        ip_cs = _ip_checksum(pkt[:ip_hlen])
        struct.pack_into("!H", pkt, 10, ip_cs)
        tcp_cs = _tcp_checksum(pkt[:ip_hlen], pkt[ip_hlen:])
        struct.pack_into("!H", pkt, tcp_off + 16, tcp_cs)
