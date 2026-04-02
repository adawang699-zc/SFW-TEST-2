#!/usr/bin/env python3
"""上传修复后的 packet_agent.py 到远程主机并重启服务"""
import paramiko
import time
import os
import sys

# 配置
HOST = '10.40.30.34'
PORT = 22
USERNAME = 'tdhx'
PASSWORD = 'tdhx@2017'

# 本地文件路径
project_root = os.path.dirname(os.path.abspath(__file__))
local_file = os.path.join(project_root, 'packet_agent', 'packet_agent.py')

# 远程路径
remote_file = 'C:\\packet_agent\\packet_agent.py'

def upload_and_restart():
    """上传文件并重启Agent"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f'Connecting to {HOST}:{PORT}...')
        ssh.connect(HOST, PORT, USERNAME, PASSWORD, timeout=30)
        print('Connected successfully')

        # SFTP 上传
        sftp = ssh.open_sftp()
        print(f'Uploading {local_file} -> {remote_file}...')
        sftp.put(local_file, remote_file)
        print('Upload successful')
        sftp.close()

        # 停止现有 Agent
        print('Stopping existing Agent...')
        stdin, stdout, stderr = ssh.exec_command('taskkill /F /IM python.exe 2>&1')
        output = stdout.read().decode('utf-8', errors='replace')
        # 移除特殊字符避免编码问题
        output = ''.join(c if ord(c) < 128 else '?' for c in output)
        print(output)

        # 等待进程停止
        time.sleep(2)

        # 启动新 Agent
        print('Starting new Agent...')
        # 使用 start 命令在新窗口启动
        cmd = f'start "packet_agent" pythonw {remote_file}'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        time.sleep(3)

        # 检查服务是否启动
        print('Checking Agent status...')
        import requests
        time.sleep(5)
        try:
            r = requests.get(f'http://{HOST}:8888/api/health', timeout=5)
            print(f'Agent response: {r.json()}')
        except Exception as e:
            print(f'Agent not responding: {e}')

        print('Done!')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()

if __name__ == '__main__':
    if not os.path.exists(local_file):
        print(f'本地文件不存在: {local_file}')
        sys.exit(1)
    upload_and_restart()