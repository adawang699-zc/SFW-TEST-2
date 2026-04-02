@echo off
chcp 65001 >nul
echo ========================================
echo IEC 61850 GOOSE/SV 程序打包脚本
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.7+
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo [2/3] 安装 PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败
    pause
    exit /b 1
)

echo.
echo [3/3] 开始打包...
python build_exe.py all

echo.
echo ========================================
echo 打包完成！
echo exe 文件位于 dist 目录中
echo ========================================
pause

