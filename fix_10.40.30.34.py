#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 10.40.30.34 的 Agent 目录问题并上传文件
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main.agent_manager import agent_manager

HOST = '10.40.30.34'
PORT = 22
USERNAME = 'tdhx'
PASSWORD = 'tdhx@2017'
REMOTE_DIR = 'D:/Agent'
REMOTE_FILE = 'D:/Agent/packet_agent.py'
LOCAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'packet_agent', 'packet_agent.py')

def main():
    print(f'正在处理 {HOST} 的 Agent 更新...')

    # 1. 连接主机
    print('\n[1/4] 连接到远程主机...')
    success, msg = agent_manager.connect_to_host(HOST, USERNAME, PASSWORD, PORT)
    print(f'连接结果：{msg}')
    if not success:
        print('连接失败，退出')
        return

    # 2. 检测系统类型
    print('\n[2/4] 检测系统类型...')
    system_type = agent_manager.detect_system_type(HOST, PORT)
    print(f'系统类型：{system_type}')

    # 3. 创建远程目录
    print(f'\n[3/4] 创建远程目录 {REMOTE_DIR}...')
    connection_key = f'{HOST}:{PORT}'
    ssh = agent_manager.connections[connection_key]['ssh']

    if system_type == 'windows':
        mkdir_cmd = f'if not exist "{REMOTE_DIR}" mkdir "{REMOTE_DIR}"'
    else:
        mkdir_cmd = f'mkdir -p "{REMOTE_DIR}"'

    stdin, stdout, stderr = ssh.exec_command(mkdir_cmd)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode('gbk', errors='ignore')
    error = stderr.read().decode('gbk', errors='ignore')

    print(f'创建目录命令：{mkdir_cmd}')
    print(f'退出状态：{exit_status}')
    print(f'输出：{output.strip() if output.strip() else "(空)" }')
    if error.strip():
        print(f'错误：{error.strip()}')

    # 验证目录是否创建成功
    if system_type == 'windows':
        verify_cmd = f'if exist "{REMOTE_DIR}" echo DIR_EXISTS'
    else:
        verify_cmd = f'test -d "{REMOTE_DIR}" && echo DIR_EXISTS'

    stdin, stdout, stderr = ssh.exec_command(verify_cmd)
    verify_result = stdout.read().decode('gbk', errors='ignore').strip()
    print(f'目录验证：{verify_result}')

    if 'DIR_EXISTS' not in verify_result:
        print('目录创建失败，退出')
        return

    print('目录创建成功！')

    # 4. 上传文件
    print(f'\n[4/4] 上传文件 {LOCAL_FILE} -> {REMOTE_FILE}...')
    success, msg = agent_manager.upload_agent(HOST, LOCAL_FILE, REMOTE_FILE, PORT, force=True)
    print(f'上传结果：{msg}')

    if success:
        print(f'\n✓ {HOST} 的 Agent 更新完成！')
    else:
        print(f'\n✗ {HOST} 的 Agent 更新失败：{msg}')

if __name__ == '__main__':
    main()
