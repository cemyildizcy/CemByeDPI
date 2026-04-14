"""
CemByeDPI - Otomatik Güncelleme Motoru (Auto-Updater)
GitHub Releases üzerinden son sürümü kontrol eder ve mevcut exe dosyasını günceller.
"""

import urllib.request
import json
import logging
import os
import sys
import tempfile
import subprocess
import time
import shutil
from packaging import version

logger = logging.getLogger("CemByeDPI")

REPO_API_URL = "https://api.github.com/repos/cemyildizcy/CemByeDPI/releases/latest"

def check_for_updates(current_version: str) -> tuple[bool, str, str]:
    """
    GitHub API'sine bağlanıp daha yeni bir sürüm olup olmadığını kontrol eder.
    Dönüş: (Yeni_mi?, Yeni_Sürüm_Adı, İndirme_URL'si)
    """
    try:
        req = urllib.request.Request(REPO_API_URL, headers={"User-Agent": "CemByeDPI-Updater"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        
        latest_version = data.get("tag_name", "").strip()
        
        # Sürüm isimlerindeki olası 'v' harflerini silip karşılaştırıyoruz
        curr = current_version.lstrip('vV')
        lat = latest_version.lstrip('vV')
        
        if version.parse(lat) > version.parse(curr):
            # Yeni sürüm var. Dosyayı indirilebilir varlıklar arasından (assets) bul.
            assets = data.get("assets", [])
            download_url = ""
            for asset in assets:
                if asset.get("name", "").lower().endswith(".exe"):
                    download_url = asset.get("browser_download_url", "")
                    break
            
            if download_url:
                return True, latest_version, download_url
                
        return False, latest_version, ""
    except Exception as e:
        logger.error(f"Güncelleme kontrolü sırasında hata: {e}")
        return False, "", ""

def download_and_update(download_url: str, progress_callback=None):
    """
    Yeni EXE dosyasını indirir, bir .bat betiği oluşturur ve çalıştırarak ana uygulamayı günceller.
    """
    try:
        logger.info(f"Yeni sürüm indiriliyor: {download_url}")
        
        exe_path = sys.executable
        if not getattr(sys, 'frozen', False):
            # Eğer kod python kodundan (main.py) direkt çalıştırılıyorsa güncelleme yapma
            logger.error("Uygulama derlenmemiş (kaynak kod), otomatik güncellenemez.")
            return False
            
        update_dir = tempfile.gettempdir()
        temp_exe_path = os.path.join(update_dir, "CemByeDPI_update_tmp.exe")
        
        # İndirme işlemi
        req = urllib.request.Request(download_url, headers={"User-Agent": "CemByeDPI-Updater"})
        with urllib.request.urlopen(req, timeout=15) as response, open(temp_exe_path, 'wb') as out_file:
            total_size = response.getheader('Content-Length')
            total_size = int(total_size) if total_size else 0
            downloaded = 0
            chunk_size = 65536
            
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                
                if total_size > 0 and progress_callback:
                    pct = int((downloaded / total_size) * 100)
                    progress_callback(pct)
        
        logger.info("İndirme tamam. Güncelleme betiği çalıştırılıyor...")
        
        # .bat scripti oluşturarak asıl değiştirme işlemini hallediyoruz.
        # Neden? Çünkü Windows, halihazırda çalışan exe dosyasının üzerine yazmaya/silmeye izin vermez.
        bat_path = os.path.join(update_dir, "c_update.bat")
        
        bat_content = f"""@echo off
setlocal enabledelayedexpansion
echo.
echo ==============================================
echo   CemByeDPI Guncelleniyor Lutfen Bekleyin...
echo ==============================================
echo.

:: 1) Uygulamayi ve servisleri durdurdugumuzdan emin olalim
taskkill /F /IM "CemByeDPI.exe" /T >nul 2>&1
sc stop WinDivert >nul 2>&1
sc delete WinDivert >nul 2>&1
timeout /t 2 /nobreak >nul

:: 2) Kopyalama islemi (Retry Logic)
set "retry=0"
:COPY_LOOP
set /a "retry+=1"
echo [Deneme !retry!] Dosya guncelleniyor...
copy /Y "{temp_exe_path}" "{exe_path}" >nul 2>&1

if !errorlevel! neq 0 (
    if !retry! lss 5 (
        echo [!] Dosya su an kilitli, 2 saniye bekleyip tekrar denenecek...
        timeout /t 2 /nobreak >nul
        goto COPY_LOOP
    ) else (
        echo [X] HATA: Dosya guncellenemedi! Lutfen programi kapatip manuel guncelleyin.
        echo Gerekiyorsa Gorev Yoneticisinden CemByeDPI'i kapatin.
        pause
        exit /b 1
    )
)

:: 3) Temizlik ve Baslatma
echo [+] Guncelleme basariyla tamamlandi.
del "{temp_exe_path}" >nul 2>&1
start "" "{exe_path}"
echo [+] Uygulama yeniden baslatiliyor...

:: Kendini sil ve cik
(goto) 2>nul & del "%~f0"
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        
        # Bat dosyasını tamamen bağımsız ve görünür bir şekilde çalıştır.
        # creationflags=subprocess.CREATE_NEW_CONSOLE ile yeni pencere açıyoruz.
        subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        # PyInstaller C bootloader'i atlatmak ve messagebox'i engellemek icin force kill parent
        try:
            ppid = os.getppid()
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.wShowWindow = 0
            subprocess.run(["taskkill", "/F", "/PID", str(ppid)], startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
            
        os._exit(0)
        
    except Exception as e:
        logger.error(f"Güncelleme yüklenirken hata oluştu: {e}")
        return False
