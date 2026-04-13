@echo off
echo ======================================
echo   CemByeDPI - Build Script
echo ======================================
echo.

pip install pyinstaller >nul 2>&1

echo Derleniyor...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name CemByeDPI ^
    --uac-admin ^
    --icon icon.ico ^
    --collect-all pydivert ^
    --hidden-import pydivert ^
    --hidden-import pydivert.windivert ^
    --hidden-import pypresence ^
    --add-data "core;core" ^
    --add-data "gui;gui" ^
    --add-data "utils;utils" ^
    --add-data "icon.ico;." ^
    --clean ^
    --noconfirm ^
    main.py

echo.
if exist dist\CemByeDPI.exe (
    echo ========================================
    echo   BASARILI! 
    echo   Dosya: dist\CemByeDPI.exe
    echo   Cift tiklayarak calistirabilirsiniz.
    echo   Otomatik olarak yonetici izni ister.
    echo ========================================
) else (
    echo HATA: Build basarisiz!
)
pause
