"""
CemByeDPI - Yönetici Hakları Kontrolü
Windows UAC yönetici kontrolü ve yükseltme.
"""

import ctypes
import sys
import os


def is_admin() -> bool:
    """Mevcut process yönetici haklarıyla çalışıyor mu?"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_as_admin():
    """Uygulamayı yönetici olarak yeniden başlat (UAC prompt gösterir)."""
    if is_admin():
        return True

    try:
        script = os.path.abspath(sys.argv[0])
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    except Exception:
        return False
