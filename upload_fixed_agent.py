#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上传修复后的 Agent 文件到远程主机并重启"""

import sys
import os
import hashlib
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main.agent_manager import agent_manager

def upload_and_restart(host, remote_path, username, password):
    """上传文件并重启 agent"""
    print(f"\n{'='*60}")
    print(f"处理主机：{host}")
    print(f'{'='*60}')

    # 连接
    print("正在连接...")
    success, msg = agent_manager.connect_to_host(host, username, password, 22)
    if not success:
        print(f"连接失败：{msg}")
        return False

    print(f"连接成功")

    # 本地文件
    local_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'packet_agent', 'packet_agent.py')
    if not os.path.exists(local_file):
        print(f"本地文件不存在：{local_file}")
        return False

    # 计算本地 MD5
    with open(local_file, 'rb') as f:
        local_md5 = hashlib.md5(f.read()).hexdigest()
    print(f"本地 MD5: {local_md5}")

    # 上传
    print("正在上传...")
    success, msg = agent_manager.upload_agent(host, local_file, remote_path, 22, force=True)
    print(f"上传结果：{msg}")

    if not success:
        return False

    # 验证 MD5
    connection_key = f'{host}:22'
    ssh = agent_manager.connections[connection_key]['ssh']

    stdin, stdout, stderr = ssh.exec_command(f'certutil -hashfile "{remote_path}" MD5')
    remote_md5_output = stdout.read().decode('utf-8', errors='ignore')
    # certutil 输出格式可能是：
    # MD5 哈希值:
    # 75 3a fb 04 3d 57 51 e9 9f 84 d5 45 c5 08 1d ba
    # 或 753afb043d5751e99f84d545c5081dba
    lines = remote_md5_output.strip().split('\r\n')
    # 找到包含 MD5 的行（去除空格后是 32 个十六进制字符）
    remote_md5 = ''
    for line in lines:
        line = line.strip()
        # 移除空格
        line_no_spaces = line.replace(' ', '')
        if len(line_no_spaces) == 32 and all(c in '0123456789abcdefABCDEF' for c in line_no_spaces):
            remote_md5 = line_no_spaces
            break

    print(f"远程 MD5: {remote_md5}")

    if local_md5.upper() != remote_md5.upper():
        print(f"MD5 不匹配！本地：{local_md5.upper()}, 远程：{remote_md5}")
        return False

    print("MD5 匹配，文件上传成功")

    # 杀死现有 agent 进程
    print("正在停止 agent 进程...")
    stdin, stdout, stderr = ssh.exec_command('Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force')
    stdout.channel.recv_exit_status()
    time.sleep(1)
    print("Agent 进程已停止")

    # 启动新 agent
    print("正在启动新 agent 进程...")
    cmd = f'Start-Process -FilePath "python" -ArgumentList "{remote_path}" -WindowStyle Hidden'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.channel.recv_exit_status()
    print("Agent 进程已启动")

    # 验证 agent 是否运行
    time.sleep(2)
    stdin, stdout, stderr = ssh.exec_command('Get-Process python* -ErrorAction SilentlyContinue | Select-Object -First 1')
    output = stdout.read().decode('utf-8', errors='ignore')
    if 'python' in output.lower():
        print("Agent 运行验证成功")
    else:
        print("警告：Agent 可能未启动")

    ssh.close()
    print(f"连接已关闭 {host}")
    return True

if __name__ == '__main__':
    print("上传修复后的 Agent 文件并重启...")

    hosts = [
        ('10.40.30.35', 'C:/Users/administrator/Desktop/packet_agent.py', 'tdhx', 'tdhx@2017'),
        ('10.40.30.34', 'C:/Users/administrator/Desktop/packet_agent.py', 'tdhx', 'tdhx@2017'),
    ]

    for host, remote_path, username, password in hosts:
        try:
            result = upload_and_restart(host, remote_path, username, password)
            if result:
                print(f"\n[OK] {host} 处理成功")
            else:
                print(f"\n[FAIL] {host} 处理失败")
        except Exception as e:
            print(f"\n[ERROR] 处理 {host} 失败：{e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("所有主机处理完成!")
    print(f"{'='*60}")
