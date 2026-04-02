#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查远程 Agent 文件"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main.agent_manager import agent_manager

def check_host(host):
    """检查主机上的文件"""
    print(f"\n{'='*60}")
    print(f"检查 {host}: C:/packet_agent/packet_agent.py")
    print('='*60)

    # 连接
    success, msg = agent_manager.connect_to_host(host, 'tdhx', 'tdhx@2017', 22)
    if not success:
        print(f"连接失败：{msg}")
        return

    print(f"连接成功：{msg}")

    # 检测系统类型
    system_type = agent_manager.detect_system_type(host, 22)
    print(f"系统类型：{system_type}")

    # 检查文件
    connection_key = f'{host}:22'
    ssh = agent_manager.connections[connection_key]['ssh']
    remote_path = 'C:/packet_agent/packet_agent.py'

    # 检查文件是否存在
    check_cmd = f'if exist "{remote_path}" echo FILE_EXISTS'
    stdin, stdout, stderr = ssh.exec_command(check_cmd)
    exist_result = stdout.read().decode('gbk', errors='ignore').strip()
    print(f"文件存在性：{exist_result}")

    # 获取文件大小
    size_cmd = f'dir "{remote_path}" 2>nul | findstr /R /C:"[0-9].*[0-9] packet_agent.py"'
    stdin, stdout, stderr = ssh.exec_command(size_cmd)
    size_result = stdout.read().decode('gbk', errors='ignore').strip()
    print(f"文件大小：{size_result if size_result else '(无法获取)'}")

    # 检查关键代码 - sending 字段
    grep_cmd = f'findstr /C:"_update_state(sending=True)" "{remote_path}"'
    stdin, stdout, stderr = ssh.exec_command(grep_cmd)
    grep_result = stdout.read().decode('gbk', errors='ignore').strip()

    if grep_result:
        print(f"[OK] sending 字段代码：已包含修复")
        print(f"     匹配内容：{grep_result[:200]}")
    else:
        print(f"[WARN] sending 字段代码：未找到 (可能是旧版本)")

    # 检查 start_send 方法
    grep_cmd2 = f'findstr /C:"def start_send" "{remote_path}"'
    stdin, stdout, stderr = ssh.exec_command(grep_cmd2)
    grep_result2 = stdout.read().decode('gbk', errors='ignore').strip()
    print(f"start_send 方法：{'存在' if grep_result2 else '不存在'}")

    # 列出目录内容
    list_cmd = f'dir "C:/packet_agent" 2>nul'
    stdin, stdout, stderr = ssh.exec_command(list_cmd)
    dir_result = stdout.read().decode('gbk', errors='ignore').strip()
    print(f"\nC:/packet_agent 目录内容:")
    print(dir_result[:2500] if len(dir_result) > 2500 else dir_result)

if __name__ == '__main__':
    print("检查远程 Agent 文件...")

    # 检查两个主机（都使用 C:/packet_agent/路径）
    hosts = ['10.40.30.35', '10.40.30.34']

    for host in hosts:
        try:
            check_host(host)
        except Exception as e:
            print(f"检查 {host} 失败：{e}")
            import traceback
            traceback.print_exc()

    print("\n完成!")
