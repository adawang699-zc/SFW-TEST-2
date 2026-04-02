#!/usr/bin/env python3
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname='10.40.30.35', port=22, username='tdhx', password='tdhx@2017')

# 尝试启动 industrial_protocol_agent 并获取错误
print('=== 尝试启动 industrial_protocol_agent ===')
cmd = 'cd /d C:\\packet_agent && python industrial_protocol_agent.py 8889'
stdin, stdout, stderr = ssh.exec_command(cmd)

# 等待 10 秒
time.sleep(10)

# 获取输出
try:
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    print(f'Output: {output[:2000] if output else "无输出"}')
    print(f'Error: {error[:2000] if error else "无错误"}')
except Exception as e:
    print(f'读取输出失败：{e}')

# 检查端口
print('\n=== 检查 8889 端口 ===')
stdin, stdout, stderr = ssh.exec_command('netstat -ano | findstr :8889')
output = stdout.read().decode('utf-8', errors='ignore')
print(f'8889: {output if output.strip() else "未监听"}')

# 检查进程
print('\n=== 检查进程 ===')
stdin, stdout, stderr = ssh.exec_command('tasklist | findstr python')
output = stdout.read().decode('utf-8', errors='ignore')
print(f'Python: {output if output.strip() else "无"}')

ssh.close()
