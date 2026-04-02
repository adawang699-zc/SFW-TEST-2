@echo off
cd /d C:\packet_agent || (
    echo [批处理错误] 无法切换到目录 C:\packet_agent >> C:\packet_agent\agent_batch.log 2>&1
    exit /b 1
)

echo [批处理启动] 时间: %date% %time% >> C:\packet_agent\agent_batch.log 2>&1

:: 显式指定 Pythonw 路径（根据实际环境修改，或通过环境变量获取）
set PYTHONW_PATH=C:\Python39\pythonw.exe
if not exist "%PYTHONW_PATH%" (
    echo [批处理错误] 未找到 pythonw.exe，尝试从环境变量获取 >> C:\packet_agent\agent_batch.log 2>&1
    for /f "delims=" %%i in ('where pythonw.exe 2^>nul') do set PYTHONW_PATH=%%i
    if not exist "%PYTHONW_PATH%" (
        echo [批处理错误] 未找到 pythonw.exe，请检查环境变量 >> C:\packet_agent\agent_batch.log 2>&1
        exit /b 1
    )
)
echo [批处理启动] 使用 pythonw.exe 路径: %PYTHONW_PATH% >> C:\packet_agent\agent_batch.log 2>&1

:: 检查 Python 依赖（根据实际依赖修改）
echo [批处理启动] 检查 Python 依赖... >> C:\packet_agent\agent_batch.log 2>&1
"%PYTHONW_PATH%" -c "import flask, scapy" 2>> C:\packet_agent\agent_batch.log
if %errorlevel% neq 0 (
    echo [批处理错误] 缺少 Python 依赖库，请安装：pip install flask scapy >> C:\packet_agent\agent_batch.log 2>&1
    exit /b 1
)

:: 启动 Agent 脚本（packet_agent.py，端口8888）
echo [批处理启动] 执行命令："%PYTHONW_PATH%" "C:\packet_agent\packet_agent.py" --host 0.0.0.0 --port 8888 >> C:\packet_agent\agent_batch.log 2>&1
start /b "%PYTHONW_PATH%" "C:\packet_agent\packet_agent.py" --host 0.0.0.0 --port 8888 >> C:\packet_agent\agent.log 2>&1

:: 等待 2 秒，确保进程启动
timeout /t 2 /nobreak >nul

:: 启动工控协议Agent脚本（industrial_protocol_agent.py，端口8889）
echo [批处理启动] 执行命令："%PYTHONW_PATH%" "C:\packet_agent\industrial_protocol_agent.py" 8889 >> C:\packet_agent\agent_batch.log 2>&1
start /b "%PYTHONW_PATH%" "C:\packet_agent\industrial_protocol_agent.py" 8889 >> C:\packet_agent\industrial_protocol_agent.log 2>&1

:: 等待 2 秒，确保进程启动
timeout /t 2 /nobreak >nul

:: 检查进程是否存在
tasklist | findstr /i pythonw.exe >> C:\packet_agent\agent_batch.log 2>&1
if %errorlevel% equ 0 (
    echo [批处理启动] pythonw.exe 进程已启动 >> C:\packet_agent\agent_batch.log
) else (
    echo [批处理错误] pythonw.exe 启动失败 >> C:\packet_agent\agent_batch.log
)

exit /b 0
