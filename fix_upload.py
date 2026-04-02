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
print('Killing existing agent (PID 13028)...')
stdin, stdout, stderr = ssh.exec_command('taskkill /F /PID 13028')
output = stdout.read().decode('utf-8', errors='ignore')
print(f'Kill result: {output}')
time.sleep(2)

# Upload to CORRECT path
sftp = ssh.open_sftp()
sftp.put('packet_agent/packet_agent.py', 'C:/packet_agent/packet_agent.py')
print('File uploaded to C:/packet_agent/packet_agent.py')

# Verify MD5
stdin, stdout, stderr = ssh.exec_command('certutil -hashfile "C:\\packet_agent\\packet_agent.py" MD5')
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

# Verify function exists
stdin, stdout, stderr = ssh.exec_command('findstr /C:"_nlst_with_encoding" "C:\\packet_agent\\packet_agent.py"')
output = stdout.read().decode('utf-8', errors='ignore').strip()
print(f'Has _nlst_with_encoding: {"Yes" if output else "No"}')

# Start new agent
print('\nStarting new agent...')
stdin, stdout, stderr = ssh.exec_command('start /B pythonw "C:\\packet_agent\\packet_agent.py" --port 8888')
time.sleep(3)

# Verify started
stdin, stdout, stderr = ssh.exec_command('tasklist | findstr python')
output = stdout.read().decode('utf-8', errors='ignore')
print(f'Running processes: {output.strip() if output.strip() else "None"}')

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

    time.sleep(2)

    # List
    payload = {'protocol': 'ftp', 'action': 'list'}
    resp = requests.post(api_url, json=payload, timeout=30)
    print(f'List: {resp.status_code}')
    print(f'Response: {resp.text[:500] if resp.text else "Empty"}')

    # Get logs
    api_url_logs = f'http://{host}:8888/api/services/logs'
    resp = requests.get(api_url_logs, timeout=5)
    logs = resp.json().get('logs', [])
    print('\nRecent logs:')
    for log in logs[:10]:
        msg = log['message'][:80]
        print(f"{log['timestamp']} [{log['level']}] {log['source']}: {msg}")

except Exception as e:
    print(f'Test error: {e}')
