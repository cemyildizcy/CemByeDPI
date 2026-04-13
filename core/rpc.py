"""
CemByeDPI - Discord RPC (Oyun Etkinliği) Motoru
"""

import time
import logging
import threading
try:
    from pypresence import Presence
except ImportError:
    Presence = None

logger = logging.getLogger("CemByeDPI")

class DiscordRPC:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.rpc = None
        self.connected = False
        self._start_time = None

    def connect(self):
        if not Presence:
            logger.warning("pypresence modülü kurulu değil. RPC çalışmayacak.")
            return False
            
        try:
            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.connected = True
            logger.info("Discord RPC bağlandı.")
            return True
        except Exception as e:
            logger.warning(f"Discord RPC bağlanamadı: {e} (Discord kapalı olabilir)")
            self.connected = False
            return False

    def update_status(self, details: str, state: str, start_time: bool = False):
        if not self.connected:
            return
            
        try:
            if start_time and not self._start_time:
                self._start_time = int(time.time())
                
            self.rpc.update(
                details=details,
                state=state,
                start=self._start_time if self._start_time else None,
                large_image="logo",  # Discord Dev portalında yüklediğin resim anahtarı
                large_text="CemByeDPI v1.1",
            )
        except Exception as e:
            logger.warning(f"RPC güncellenemedi: {e}")

    def disconnect(self):
        if self.connected and self.rpc:
            try:
                self.rpc.clear()
                self.rpc.close()
            except Exception:
                pass
            self.connected = False
            self._start_time = None
            logger.info("Discord RPC bağlantısı kapatıldı.")
