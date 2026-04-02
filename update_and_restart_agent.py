#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上传修复后的 Agent 文件到远程主机并重启"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main.agent_manager import agent_manager

def update_agent(host):
    """更新主机上的 Agent 文件"""
    print(f"\n{'='*60}")
    print(f"更新 {host}: C:/packet_agent/packet_agent.py")
    print('='*60)

    # 连接
    print("1. 正在连接...")
    success, msg = agent_manager.connect_to_host(host, 'tdhx', 'tdhx@2017', 22)
    if not success:
        print(f"   连接失败：{msg}")
        return False

    print(f"   连接成功")

    # 本地文件
    local_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'packet_agent', 'packet_agent.py')
    remote_path = 'C:/packet_agent/packet_agent.py'

    print(f"2. 本地文件：{local_file}")
    print(f"   大小：{os.path.getsize(local_file)} 字节")

    # 停止旧 Agent
    print("3. 正在停止旧 Agent...")
    success, msg = agent_manager.stop_agent(host, 22, 8888)
    print(f"   停止结果：{msg}")

    time.sleep(2)

    # 上传文件
    print("4. 正在上传文件...")
    success, msg = agent_manager.upload_agent(host, local_file, remote_path, 22, force=True)
    print(f"   上传结果：{msg}")

    if not success:
        print(f"   上传失败，但继续")

    time.sleep(1)

    # 启动新 Agent
    print("5. 正在启动新 Agent...")
    success, msg = agent_manager.start_agent(host, remote_path, 22, 8888)
    print(f"   启动结果：{msg}")

    # 验证
    print("6. 验证 Agent 状态...")
    time.sleep(3)

    is_running, status_msg = agent_manager.check_agent_status(host, 22, 8888)
    if is_running:
        print(f"   [OK] Agent 正在运行 (端口 8888)")
    else:
        print(f"   [WARN] Agent 可能未运行：{status_msg}")

    # 验证工业协议 Agent
    is_running_8889, _ = agent_manager.check_agent_status(host, 22, 8889)
    if is_running_8889:
        print(f"   [OK] 工业协议 Agent 正在运行 (端口 8889)")
    else:
        print(f"   [INFO] 工业协议 Agent 状态未知")

    return True

if __name__ == '__main__':
    print("更新远程 Agent 文件并重启服务...")

    hosts = ['10.40.30.35', '10.40.30.34']

    for host in hosts:
        try:
            result = update_agent(host)
            if result:
                print(f"\n[OK] {host} 更新完成")
            else:
                print(f"\n[FAIL] {host} 更新失败")
        except Exception as e:
            print(f"\n[ERROR] {host} 更新异常：{e}")
            import traceback
            traceback.print_exc()

    print("\n全部完成!")
