@echo off
chcp 65001 >nul
echo ============================================================
echo packet_agent.exe 打包工具
echo 兼容 Windows 7 和 Windows 10
echo ============================================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

:: 检查并卸载不兼容的enum34包
python -c "import enum34" >nul 2>&1
if %errorlevel% equ 0 (
    echo 检测到不兼容的enum34包，正在卸载...
    python -m pip uninstall enum34 -y >nul 2>&1
    echo enum34已卸载
)

:: 检查PyInstaller是否已安装
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller未安装，正在安装...
    python -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo 错误: PyInstaller安装失败
        pause
        exit /b 1
    )
)

:: 切换到脚本目录
cd /d "%~dp0"

:: 清理旧的构建文件
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist packet_agent.spec del /q packet_agent.spec

echo.
echo 开始打包...
echo.

:: 执行打包命令
pyinstaller --onefile ^
    --windowed ^
    --name=packet_agent ^
    --clean ^
    --noconfirm ^
    --hidden-import=flask ^
    --hidden-import=flask_cors ^
    --hidden-import=scapy ^
    --hidden-import=scapy.all ^
    --hidden-import=scapy.layers.inet ^
    --hidden-import=scapy.layers.l2 ^
    --hidden-import=scapy.sendrecv ^
    --hidden-import=scapy.volatile ^
    --hidden-import=psutil ^
    --hidden-import=ftplib ^
    --collect-all=scapy ^
    --collect-all=flask ^
    --exclude-module=matplotlib ^
    --exclude-module=numpy ^
    --exclude-module=pandas ^
    --exclude-module=tkinter ^
    packet_agent.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo 打包成功！
    echo exe文件位于: dist\packet_agent.exe
    echo ============================================================
    echo.
    echo 使用说明:
    echo 1. 将packet_agent.exe复制到目标Windows系统
    echo 2. 运行方式: packet_agent.exe --host 0.0.0.0 --port 8888
    echo 3. 或者直接双击运行（使用默认配置）
    echo.
) else (
    echo.
    echo ============================================================
    echo 打包失败，请检查错误信息
    echo ============================================================
    echo.
)

pause

