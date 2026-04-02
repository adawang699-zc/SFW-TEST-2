@echo off
chcp 65001 >nul
echo 启动 IEC 61850 服务端（接收端）...
python server_gui.py
pause

