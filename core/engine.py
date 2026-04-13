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
        self.start_time: float | None = None
        self._callbacks: list = []

    def on_log(self, cb):
        self._callbacks.append(cb)
        self.fragmenter.on_log(cb)

    def _emit(self, msg):
        logger.info(msg)
        for cb in self._callbacks:
            try:
                cb(msg)
            except Exception:
                pass

    def start_async(self, dns_name: str = DEFAULT_DNS, done_cb=None):
        """Bypass'ı arka planda başlat (GUI donmaz)."""
        if self.active:
            if done_cb:
                done_cb(True)
            return

        def _worker():
            result = self._do_start(dns_name)
            if done_cb:
                done_cb(result)

        t = threading.Thread(target=_worker, daemon=True, name="engine-start")
        t.start()

    def _do_start(self, dns_name: str = DEFAULT_DNS) -> bool:
        """Bypass başlatma (ağır işler burada — arka plan thread'i)."""
        self._emit("🚀 CemByeDPI başlatılıyor...")

        # 1. DNS (DoH + hosts dosyası + sistem DNS)
        self._emit(f"🌐 DNS ayarlanıyor → {dns_name} (DoH + hosts)")
        if not self.dns.set_dns(dns_name):
            self._emit("⚠️ DNS ayarlanamadı, yine de devam ediliyor...")

        # 2. SNI Fragmenter
        if not self.fragmenter.start():
            self._emit("❌ SNI Fragmenter başlatılamadı!")
            self.dns.restore_dns()
            return False

        self.active = True
        self.start_time = time.time()
        self._emit("✅ CemByeDPI aktif — Discord erişimi sağlanıyor")
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
                exe = sys.executable
                script = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "main.py")
                )
                winreg.SetValueEx(
                    key, APP_NAME, 0, winreg.REG_SZ,
                    f'"{exe}" "{script}" --minimized',
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
