@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "main_gui.py" (
    echo main_gui.py not found.
    pause
    exit /b 1
)
pip install -r requirements.txt -q 2>nul
python main_gui.py
pause
