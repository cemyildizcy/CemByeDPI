"""
CemByeDPI - DNS Yöneticisi v3
DNS-over-HTTPS (DoH) ile hızlı paralel domain çözümleme + hosts dosyası.
Tüm subprocess çağrıları gizli pencerede çalışır.
"""

import subprocess
import logging
import urllib.request
import json
import os
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("CemByeDPI")

# Tüm subprocess'leri gizli pencerede çalıştır (mavi PowerShell penceresi yok)
_STARTUPINFO = subprocess.STARTUPINFO()
_STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
_STARTUPINFO.wShowWindow = 0  # SW_HIDE

DNS_SERVERS = {
    "Cloudflare (Önerilen)": ("1.1.1.1", "1.0.0.1"),
    "Google": ("8.8.8.8", "8.8.4.4"),
    "Quad9 (Güvenlik)": ("9.9.9.9", "149.112.112.112"),
    "Yandex": ("77.88.8.8", "77.88.8.1"),
}

DEFAULT_DNS = "Cloudflare (Önerilen)"

DOH_URLS = [
    "https://1.1.1.1/dns-query",
    "https://8.8.8.8/resolve",
    "https://dns.quad9.net:5053/dns-query",
]

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
HOSTS_MARKER_START = "# >>> CemByeDPI Discord Entries - START"
HOSTS_MARKER_END = "# >>> CemByeDPI Discord Entries - END"

DISCORD_CRITICAL_DOMAINS = [
    "discord.com",
    "www.discord.com",
    "cdn.discord.com",
    "media.discord.com",
    "images-ext-1.discordapp.net",
    "images-ext-2.discordapp.net",
    "discordapp.com",
    "www.discordapp.com",
    "dl.discordapp.net",
    "gateway.discord.gg",
    "discord.gg",
    "discordapp.net",
    "discord.media",
    "discordcdn.com",
    "status.discord.com",
    "canary.discord.com",
    "ptb.discord.com",
    "media.discordapp.net",
    "images.discordapp.net",
    "cdn.discordapp.com",
    "updates.discord.com",
    "latency.discord.media",
    "router.discord.com",
]


def _run_hidden(args, **kwargs):
    """Subprocess'i gizli pencerede çalıştır — kullanıcıya pencere göstermez."""
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("timeout", 15)
    kwargs["startupinfo"] = _STARTUPINFO
    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(args, **kwargs)


# ---------------------------------------------------------------------------
# DNS-over-HTTPS Resolver
# ---------------------------------------------------------------------------

def resolve_doh(domain: str) -> list[str]:
    """DNS-over-HTTPS ile domain çöz (HTTPS ile — ISP göremez)."""
    ctx = ssl.create_default_context()
    for doh_url in DOH_URLS:
        try:
            url = f"{doh_url}?name={domain}&type=A"
            req = urllib.request.Request(url, headers={
                "Accept": "application/dns-json",
                "User-Agent": "CemByeDPI/2.0",
            })
            resp = urllib.request.urlopen(req, timeout=5, context=ctx)
            data = json.loads(resp.read())
            ips = [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]
            if ips:
                return ips
        except Exception:
            continue
    return []


def resolve_all_parallel(domains: list[str], max_workers: int = 8) -> dict[str, str]:
    """Tüm domainleri paralel olarak DoH ile çöz — çok hızlı."""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(resolve_doh, d): d for d in domains}
        for future in as_completed(futures):
            domain = futures[future]
            try:
                ips = future.result()
                if ips:
                    results[domain] = ips[0]
            except Exception:
                pass
    return results


# ---------------------------------------------------------------------------
# Hosts Dosyası Yönetimi
# ---------------------------------------------------------------------------

def _read_hosts() -> str:
    try:
        with open(HOSTS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as e:
        logger.error(f"Hosts dosyası okunamadı: {e}")
        return ""


def _write_hosts(content: str):
    try:
        with open(HOSTS_PATH, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Hosts dosyası yazılamadı: {e}")
        raise


def add_hosts_entries(entries: dict[str, str]) -> bool:
    try:
        content = _read_hosts()
        content = _remove_entries(content)

        lines = [HOSTS_MARKER_START]
        for domain, ip in entries.items():
            lines.append(f"{ip}\t{domain}")
        lines.append(HOSTS_MARKER_END)

        content = content.rstrip("\n") + "\n\n" + "\n".join(lines) + "\n"
        _write_hosts(content)
        logger.info(f"Hosts dosyasına {len(entries)} girdi eklendi")
        return True
    except Exception as e:
        logger.error(f"Hosts girdileri eklenemedi: {e}")
        return False


def _remove_entries(content: str) -> str:
    lines = content.split("\n")
    result, skip = [], False
    for line in lines:
        if HOSTS_MARKER_START in line:
            skip = True
            continue
        if HOSTS_MARKER_END in line:
            skip = False
            continue
        if not skip:
            result.append(line)
    return "\n".join(result)


def remove_hosts_entries() -> bool:
    try:
        content = _read_hosts()
        _write_hosts(_remove_entries(content))
        logger.info("Hosts girdileri temizlendi")
        return True
    except Exception as e:
        logger.error(f"Hosts temizleme hatası: {e}")
        return False


# ---------------------------------------------------------------------------
# DNS Manager
# ---------------------------------------------------------------------------

class DNSManager:
    """Sistem DNS + DoH hosts yöneticisi. Hiçbir pencere göstermez."""

    def __init__(self):
        self.original_dns: dict[str, list[str]] = {}
        self.active_adapter: str | None = None
        self.hosts_modified = False
        self._on_log_cb = None

    def on_log(self, cb):
        self._on_log_cb = cb

    def _emit(self, msg: str):
        if self._on_log_cb:
            self._on_log_cb(msg)
        else:
            logger.info(msg)

    def get_active_adapter(self) -> str | None:
        try:
            r = _run_hidden([
                "powershell", "-NoProfile", "-Command",
                "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} "
                "| Select-Object -First 1 -ExpandProperty Name",
            ])
            name = r.stdout.strip()
            if name:
                self.active_adapter = name
                logger.info(f"Aktif adaptör: {name}")
                return name
        except Exception as e:
            logger.error(f"Adaptör bulunamadı: {e}")
        return None

    def backup_dns(self):
        if not self.active_adapter:
            self.get_active_adapter()
        if not self.active_adapter:
            return
        try:
            r = _run_hidden([
                "powershell", "-NoProfile", "-Command",
                f"(Get-DnsClientServerAddress -InterfaceAlias '{self.active_adapter}'"
                f" -AddressFamily IPv4).ServerAddresses -join ','",
            ])
            raw = r.stdout.strip()
            dns_list = [d.strip() for d in raw.split(",") if d.strip()]
            self.original_dns[self.active_adapter] = dns_list
            logger.info(f"DNS yedeklendi: {dns_list}")
        except Exception as e:
            logger.error(f"DNS yedekleme hatası: {e}")

    def set_dns(self, dns_name: str = DEFAULT_DNS, target_domains: list[str] = None) -> bool:
        if not self.active_adapter:
            self.get_active_adapter()
        if not self.active_adapter:
            logger.error("Aktif ağ adaptörü bulunamadı!")
            return False

        self.backup_dns()
        primary, secondary = DNS_SERVERS.get(dns_name, DNS_SERVERS[DEFAULT_DNS])

        # 1. Sistem DNS (gizli pencere)
        try:
            _run_hidden([
                "powershell", "-NoProfile", "-Command",
                f"Set-DnsClientServerAddress -InterfaceAlias '{self.active_adapter}'"
                f" -ServerAddresses ('{primary}','{secondary}')",
            ])
            logger.info(f"Sistem DNS: {primary}, {secondary}")
        except Exception as e:
            logger.warning(f"Sistem DNS değiştirilemedi: {e}")

        # 2. DoH ile PARALEL çözümleme → hosts dosyası (çok hızlı)
        domain_list = target_domains if target_domains else []
        logger.info(f"🔐 DoH ile {len(domain_list)} adet hedef domain çözümleniyor...")
        
        if domain_list:
            entries = resolve_all_parallel(domain_list)
            if entries:
                if add_hosts_entries(entries):
                    self.hosts_modified = True
                    logger.info(f"✅ {len(entries)}/{len(domain_list)} domain çözümlendi")
                else:
                    logger.error("Hosts dosyasına yazılamadı!")
            else:
                logger.error("Hiçbir domain DoH ile çözümlenemedi!")
        else:
            logger.info("Hedef domain seçilmedi, sadece SNI motoru çalışacak.")

        # 3. DNS cache temizle (gizli)
        try:
            _run_hidden(["ipconfig", "/flushdns"])
            logger.info("DNS cache temizlendi")
        except Exception:
            pass

        return True

    def restore_dns(self) -> bool:
        success = True

        if self.hosts_modified:
            if remove_hosts_entries():
                self.hosts_modified = False
            else:
                success = False

        if self.active_adapter:
            try:
                saved = self.original_dns.get(self.active_adapter)
                if saved:
                    servers = ",".join(f"'{d}'" for d in saved)
                    cmd = (
                        f"Set-DnsClientServerAddress -InterfaceAlias '{self.active_adapter}'"
                        f" -ServerAddresses ({servers})"
                    )
                else:
                    cmd = (
                        f"Set-DnsClientServerAddress -InterfaceAlias '{self.active_adapter}'"
                        f" -ResetServerAddresses"
                    )
                _run_hidden(["powershell", "-NoProfile", "-Command", cmd])
                logger.info("DNS eski haline getirildi")
            except Exception as e:
                logger.error(f"DNS geri alma hatası: {e}")
                success = False

        try:
            _run_hidden(["ipconfig", "/flushdns"])
        except Exception:
            pass

        return success
