#!/usr/bin/env python3
"""检查远程 Agent 日志"""
import paramiko
import time

HOST = '10.40.30.34'
PORT = 22
USERNAME = 'tdhx'
PASSWORD = 'tdhx@2017'

def check_logs():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f'Connecting to {HOST}:{PORT}...')
        ssh.connect(HOST, PORT, USERNAME, PASSWORD, timeout=30)
        print('Connected')

        # 检查最近的日志文件
        print('Checking recent agent logs...')
        stdin, stdout, stderr = ssh.exec_command('dir C:\\packet_agent\\logs\\*.log /O-D /B 2>nul | head -5')
        files = stdout.read().decode('utf-8', errors='replace').strip()
        print(f'Log files: {files}')

        # 检查最新的日志内容
        if files:
            latest_log = files.split('\n')[0].strip()
            print(f'Reading {latest_log}...')
            stdin, stdout, stderr = ssh.exec_command(f'type "{latest_log}" | more +50')
            content = stdout.read().decode('utf-8', errors='replace')
            print(content[-2000:] if len(content) > 2000 else content)

    except Exception as e:
        print(f'Error: {e}')
    finally:
        ssh.close()

if __name__ == '__main__':
    check_logs()