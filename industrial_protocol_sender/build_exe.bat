@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Installing dependencies if needed...
pip install -r requirements.txt -q
echo Building exe...
python build_exe.py
if %ERRORLEVEL% equ 0 (
    echo.
    echo Done. Exe: dist\IndustrialProtocolSender.exe
    pause
) else (
    echo Build failed.
    pause
    exit /b 1
)
