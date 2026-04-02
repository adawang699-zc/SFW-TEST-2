@echo off
chcp 65001 >nul
title 报文发送代理程序

REM 获取脚本所在目录
cd /d "%~dp0"

REM 设置Python编码为UTF-8
set PYTHONIOENCODING=utf-8

REM 启动代理程序（使用默认配置：0.0.0.0:8888）
python -u packet_agent.py

pause

