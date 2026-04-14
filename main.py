"""
CemByeDPI — Discord Erişim Engeli Aşma Aracı
Ana giriş noktası.

Kullanım:
  python main.py              Normal başlatma
  python main.py --minimized  Sistem tepsisinde başlat (autostart için)

YÖNETİCİ OLARAK ÇALIŞTIRILMALIDIR.
"""

import sys
import os
import glob
import shutil
import atexit

APP_VERSION = "v1.2.3"


def _cleanup_old_mei():
    """PyInstaller --onefile modunun bıraktığı eski _MEI klasörlerini temizle."""
    try:
        mei_base = getattr(sys, '_MEIPASS', None)
        if not mei_base:
            return
        tmp_dir = os.path.dirname(mei_base)
        for d in glob.glob(os.path.join(tmp_dir, "_MEI*")):
            if d != mei_base and os.path.isdir(d):
                try:
                    shutil.rmtree(d, ignore_errors=True)
                except Exception:
                    pass
    except Exception:
        pass


_cleanup_old_mei()
atexit.register(_cleanup_old_mei)

# Çalışma dizinini script konumuna ayarla
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from utils.admin_check import is_admin, run_as_admin
from utils.logger import setup_logger

# Loglama
setup_logger(log_dir="logs")

# Yönetici kontrolü
if not is_admin():
    run_as_admin()
    sys.exit(0)

# PyQt6 importları (admin kontrolünden sonra)
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CemByeDPI")
    app.setQuitOnLastWindowClosed(False)  # Tray'de çalışmaya devam et

    minimized = "--minimized" in sys.argv
    window = MainWindow(start_minimized=minimized, app_version=APP_VERSION)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
