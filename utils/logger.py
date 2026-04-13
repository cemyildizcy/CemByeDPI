"""
CemByeDPI - Loglama Ayarları
"""

import logging
import os
from datetime import datetime


def setup_logger(log_dir: str | None = None) -> logging.Logger:
    """Uygulama loglamasını yapılandır."""
    logger = logging.getLogger("CemByeDPI")
    logger.setLevel(logging.DEBUG)

    # Konsol handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s — %(message)s", datefmt="%H:%M:%S")
    console.setFormatter(fmt)
    logger.addHandler(console)

    # Dosya handler
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        fh = logging.FileHandler(
            os.path.join(log_dir, f"cembyedpi_{today}.log"), encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger
