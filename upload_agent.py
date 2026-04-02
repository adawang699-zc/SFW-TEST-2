import paramiko
import time

# SSH 连接
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print('正在连接 10.40.30.34...')
ssh.connect('10.40.30.34', port=22, username='tdhx', password='tdhx@2017')
print('SSH 连接成功!')

# 使用 cmd 创建目录 - 确保路径正确
stdin, stdout, stderr = ssh.exec_command('cmd /c "mkdir D:\\Agent 2>nul || echo directory exists"')
exit_code = stdout.channel.recv_exit_status()
print(f'创建目录结果：{stdout.read().decode("gbk", errors="ignore")}')

# 验证目录存在
stdin, stdout, stderr = ssh.exec_command('cmd /c "if exist D:\\Agent\\ echo exists"')
output = stdout.read().decode('gbk', errors='ignore').strip()
print(f'目录检查：{output}')

if 'exists' not in output.lower():
    print('目录创建失败，尝试其他方法...')
    stdin, stdout, stderr = ssh.exec_command('powershell -Command "New-Item -ItemType Directory -Path D:\\Agent -Force"')
    print(stdout.read().decode('gbk', errors='ignore'))

# SFTP 上传
sftp = ssh.open_sftp()
local_file = 'packet_agent/packet_agent.py'
remote_file = 'D:/Agent/packet_agent.py'

print(f'正在上传 {local_file} 到 {remote_file} ...')
sftp.put(local_file, remote_file)
print('上传成功!')

# 验证文件
stdin, stdout, stderr = ssh.exec_command('cmd /c "findstr /c:\"TCPClientManager\" D:\\Agent\\packet_agent.py | find /c \"TCPClientManager\""')
count = stdout.read().decode('gbk', errors='ignore').strip()
print(f'文件验证：找到 {count} 个 TCPClientManager 引用')

# 停止旧 Agent
print('停止旧 Agent 进程...')
stdin, stdout, stderr = ssh.exec_command('taskkill /F /IM python.exe')
print(stdout.read().decode('gbk', errors='ignore'))

time.sleep(3)

# 启动新 Agent
print('启动新 Agent...')
stdin, stdout, stderr = ssh.exec_command('cd /d "D:\\Agent" && start "packet_agent" python packet_agent.py')
print(stdout.read().decode('gbk', errors='ignore'))

# 验证 Agent 是否启动
time.sleep(5)
stdin, stdout, stderr = ssh.exec_command('netstat -ano | findstr ":8888"')
print(f'Agent 端口状态：{stdout.read().decode("gbk", errors="ignore")}')

sftp.close()
ssh.close()
print('完成!')
