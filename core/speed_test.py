"""
CemByeDPI - İnternet Hız Testi
Download hızı ve ping ölçümü yapar.
"""

import threading
import urllib.request
import socket
import time
import logging
import ssl

logger = logging.getLogger("CemByeDPI")

# Farklı test URL'leri (biri başarısız olursa diğerini dener)
TEST_URLS = [
    ("https://speed.cloudflare.com/__down?bytes=10000000", 10_000_000),
    ("https://proof.ovh.net/files/10Mb.dat", 10_000_000),
]

PING_HOSTS = [
    ("1.1.1.1", 443),
    ("8.8.8.8", 443),
]


class SpeedTest:
    """İnternet hız testi - download hızı ve ping ölçer."""

    def __init__(self):
        self.running = False
        self._thread: threading.Thread | None = None
        self.download_speed: float = 0.0  # Mbps
        self.ping_ms: float = 0.0
        self._progress_cb = None
        self._done_cb = None

    def on_progress(self, cb):
        """cb(progress_pct: float, current_speed_mbps: float)"""
        self._progress_cb = cb

    def on_done(self, cb):
        """cb(download_mbps: float, ping_ms: float)"""
        self._done_cb = cb

    def start(self):
        """Hız testini arka planda başlat."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="speed-test")
        self._thread.start()

    def _run(self):
        try:
            # 1. Ping testi
            self.ping_ms = self._measure_ping()
            if self._progress_cb:
                self._progress_cb(5.0, 0.0)

            # 2. Download testi
            self.download_speed = self._measure_download()

            # 3. Sonuç
            logger.info(
                f"Hız testi: {self.download_speed:.1f} Mbps, "
                f"Ping: {self.ping_ms:.0f} ms"
            )
            if self._done_cb:
                self._done_cb(self.download_speed, self.ping_ms)

        except Exception as e:
            logger.error(f"Hız testi hatası: {e}")
            if self._done_cb:
                self._done_cb(0.0, 0.0)
        finally:
            self.running = False

    def _measure_ping(self) -> float:
        """TCP handshake ile ping ölç (ms)."""
        results = []
        for host, port in PING_HOSTS:
            for _ in range(3):
                try:
                    t0 = time.perf_counter()
                    s = socket.create_connection((host, port), timeout=5)
                    elapsed = (time.perf_counter() - t0) * 1000
                    s.close()
                    results.append(elapsed)
                except OSError:
                    pass
            if results:
                break

        return min(results) if results else 999.0

    def _measure_download(self) -> float:
        """Dosya indirerek download hızını ölç (Mbps)."""
        ctx = ssl.create_default_context()

        for url, expected in TEST_URLS:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "CemByeDPI-SpeedTest/1.0"},
                )
                t0 = time.perf_counter()
                resp = urllib.request.urlopen(req, timeout=30, context=ctx)

                downloaded = 0
                chunk = 65536
                while True:
                    data = resp.read(chunk)
                    if not data:
                        break
                    downloaded += len(data)
                    elapsed = time.perf_counter() - t0
                    if elapsed > 0:
                        cur_speed = (downloaded * 8) / (elapsed * 1_000_000)
                    else:
                        cur_speed = 0.0
                    pct = min(downloaded / expected * 95, 95) + 5  # 5-100
                    if self._progress_cb:
                        self._progress_cb(pct, cur_speed)

                total = time.perf_counter() - t0
                if total > 0:
                    return (downloaded * 8) / (total * 1_000_000)
            except Exception as e:
                logger.warning(f"Hız testi URL başarısız ({url}): {e}")
                continue

        return 0.0
