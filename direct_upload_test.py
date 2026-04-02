#!/usr/bin/env python3
import paramiko
import hashlib
import time

# Calculate local MD5
with open('packet_agent/packet_agent.py', 'rb') as f:
    local_md5 = hashlib.md5(f.read()).hexdigest()
print(f'Local MD5: {local_md5}')

# Connect
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname='10.40.30.35', port=22, username='tdhx', password='tdhx@2017')

# Kill existing agent
print('Killing existing agent...')
stdin, stdout, stderr = ssh.exec_command('taskkill /F /IM python*.exe')
time.sleep(2)

# Upload
sftp = ssh.open_sftp()
sftp.put('packet_agent/packet_agent.py', 'C:/Users/administrator/Desktop/packet_agent.py')
print('File uploaded successfully')

# Verify MD5
stdin, stdout, stderr = ssh.exec_command('certutil -hashfile "C:\\Users\\administrator\\Desktop\\packet_agent.py" MD5')
output = stdout.read().decode('utf-8', errors='ignore')
lines = output.strip().split('\r\n')
remote_md5 = ''
for line in lines:
    line = line.strip().replace(' ', '')
    if len(line) == 32 and all(c in '0123456789abcdefABCDEF' for c in line):
        remote_md5 = line
        break

print(f'Remote MD5: {remote_md5}')
print(f'Match: {local_md5.upper() == remote_md5.upper()}')

# Search for function
stdin, stdout, stderr = ssh.exec_command('findstr /C:"_nlst_with_encoding" "C:\\Users\\administrator\\Desktop\\packet_agent.py"')
output = stdout.read().decode('utf-8', errors='ignore').strip()
print(f'\nRemote has _nlst_with_encoding: {"Yes" if output else "No"}')
if output:
    print(f'  {output[:100]}')

# Start new agent
print('\nStarting new agent...')
stdin, stdout, stderr = ssh.exec_command('start /B python "C:\\Users\\administrator\\Desktop\\packet_agent.py"')
time.sleep(3)

# Verify agent is running
stdin, stdout, stderr = ssh.exec_command('tasklist | findstr python')
output = stdout.read().decode('utf-8', errors='ignore')
print(f'Running Python processes: {output.strip() if output.strip() else "None"}')

sftp.close()
ssh.close()

# Test FTP list
print('\n--- Testing FTP list ---')
time.sleep(2)
import requests
host = '10.40.30.35'
api_url = f'http://{host}:8888/api/services/client'

# Connect
payload = {'protocol': 'ftp', 'action': 'connect', 'server_ip': host, 'server_port': 21, 'username': 'tdhx', 'password': 'tdhx@2017'}
try:
    resp = requests.post(api_url, json=payload, timeout=10)
    print(f'Connect: {resp.json()}')
except Exception as e:
    print(f'Connect error: {e}')
