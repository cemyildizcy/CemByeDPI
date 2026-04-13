"""
CemByeDPI - Ana Bypass Motoru
DNS yönetimi ve SNI fragmentation'ı orkestre eder.
"""

import threading
import time
import logging
import winreg
import sys
import os

from core.dns_manager import DNSManager, DNS_SERVERS, DEFAULT_DNS
from core.sni_fragmenter import SNIFragmenter

logger = logging.getLogger("CemByeDPI")

APP_NAME = "CemByeDPI"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


class Engine:
    """Tüm bypass bileşenlerini yönetir."""

    def __init__(self):
        self.dns = DNSManager()
        self.fragmenter = SNIFragmenter()
        self.active = False
        self.start_time = None
        self._on_log_cb = None
        
        # RPC Init
        try:
            from core.rpc import DiscordRPC
            self.rpc = DiscordRPC(client_id="1493344862005624893")
        except ImportError:
            self.rpc = None

    def on_log(self, cb):
        self._on_log_cb = cb
        self.fragmenter.on_log(cb)

    def _emit(self, msg: str):
        if self._on_log_cb:
            self._on_log_cb(msg)
        else:
            logger.info(msg)

    def start_async(self, dns_name: str, target_domains: list[str] = None, done_cb=None):
        """Arayüzü kitlemeden bypass'ı arka planda başlat."""
        t = threading.Thread(target=self._start_thread, args=(dns_name, target_domains, done_cb), daemon=True)
        t.start()

    def _start_thread(self, dns_name: str, target_domains: list[str], done_cb):
        if self.rpc:
            self.rpc.connect()
            self.rpc.update_status(details="Bypass Başlatılıyor...", state="Hazırlanıyor")
            
        ok = self.start(dns_name, target_domains)
        
        if ok and self.rpc:
            self.rpc.update_status(details="Engeller Aşılıyor 🚀", state="Bağlı ve Güvende", start_time=True)
        elif not ok and self.rpc:
            self.rpc.update_status(details="Bypass Başarısız ❌", state="Hata")
            
        if done_cb:
            done_cb(ok)

    def start(self, dns_name: str = DEFAULT_DNS, target_domains: list[str] = None) -> bool:
        """Bypass başlatma (ağır işler burada — arka plan thread'i)."""
        self._emit("🚀 CemByeDPI başlatılıyor...")

        # 1. DNS (DoH + hosts dosyası + sistem DNS)
        self._emit(f"🌐 DNS ayarlanıyor → {dns_name} (DoH + hosts)")
        if not self.dns.set_dns(dns_name, target_domains):
            self._emit("⚠️ DNS ayarlanamadı, yine de devam ediliyor...")

        # 2. SNI Fragmenter
        if not self.fragmenter.start():
            self._emit("❌ SNI Fragmenter başlatılamadı!")
            self.dns.restore_dns()
            return False

        self.active = True
        self.start_time = time.time()
        self._emit("✅ CemByeDPI aktif — Erişim sağlandı")
        return True

    def stop(self):
        """Bypass'ı durdur: Fragmenter kapat + DNS geri al."""
        if not self.active:
            return

        self._emit("🛑 CemByeDPI durduruluyor...")
        self.fragmenter.stop()
        self.dns.restore_dns()
        self.active = False
        self.start_time = None
        
        if self.rpc:
            self.rpc.disconnect()
            
        self._emit("⬛ CemByeDPI durduruldu")

    def get_uptime(self) -> str:
        """Çalışma süresini HH:MM:SS formatında döndür."""
        if not self.start_time:
            return "00:00:00"
        s = int(time.time() - self.start_time)
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{sec:02d}"

    # ---- Autostart ----
    @staticmethod
    def get_autostart() -> bool:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    @staticmethod
    def set_autostart(enable: bool):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE
            )
            if enable:
                if getattr(sys, 'frozen', False):
                    # PyInstaller ile derlenmiş exe
                    exe_path = sys.executable
                    cmd = f'"{exe_path}" --minimized'
                else:
                    # Geliştirme ortamı (python main.py)
                    exe_path = sys.executable
                    script = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..", "main.py")
                    )
                    cmd = f'"{exe_path}" "{script}" --minimized'
                    
                winreg.SetValueEx(
                    key, APP_NAME, 0, winreg.REG_SZ,
                    cmd,
                )
                logger.info("Autostart etkinleştirildi")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
                logger.info("Autostart devre dışı bırakıldı")
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Autostart hatası: {e}")
