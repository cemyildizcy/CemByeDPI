"""
CemByeDPI - Ağ Yardımcıları
"""

import socket
import subprocess
import logging

logger = logging.getLogger("CemByeDPI")


def check_internet(host: str = "1.1.1.1", port: int = 443, timeout: float = 5) -> bool:
    """Basit TCP bağlantısı ile internet erişimi kontrol et."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def check_discord(timeout: float = 5) -> bool:
    """Discord sunucularına erişim var mı kontrol et."""
    try:
        sock = socket.create_connection(("discord.com", 443), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def get_active_adapters() -> list[str]:
    """Aktif ağ adaptörlerinin isimlerini döndür."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} "
                "| Select-Object -ExpandProperty Name",
            ],
            capture_output=True, text=True, timeout=10,
        )
        return [n.strip() for n in result.stdout.strip().split("\n") if n.strip()]
    except Exception as e:
        logger.error(f"Adaptör listesi alınamadı: {e}")
        return []
