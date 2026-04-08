#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试环境工具模块
提供SSH文件传输、Agent部署等功能
"""

import paramiko
import os
import logging
import socket
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Agent进程状态（用于跟踪运行状态）
agent_processes = {}  # {env_id: {'pid': pid, 'thread': thread}}
agent_lock = threading.Lock()


def execute_ssh_command(host, user, password, port=22, command='', env_type='linux', timeout=30):
    """
    通过SSH执行命令（支持Windows和Linux）
    
    Args:
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        port: SSH端口
        command: 要执行的命令
        env_type: 环境类型 ('windows' 或 'linux')
        timeout: 超时时间（秒）
    
    Returns:
        tuple: (success: bool, output: str, error: str)
    """
    ssh = None
    try:
        # 建立SSH连接
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port, user, password, timeout=10)
        
        # 根据环境类型调整命令
        if env_type == 'windows':
            # Windows: 使用PowerShell或cmd执行
            # 如果命令看起来是PowerShell命令，直接执行
            # 否则使用cmd执行
            if command.strip().startswith('powershell') or command.strip().startswith('ps '):
                final_command = command
            else:
                # 使用cmd执行，并确保输出编码正确
                final_command = f'cmd /c "{command}"'
        else:
            # Linux: 直接执行命令
            final_command = command
        
        logger.info(f'执行命令 [{env_type}]: {final_command}')
        
        # 执行命令
        stdin, stdout, stderr = ssh.exec_command(final_command, timeout=timeout)
        
        # 读取输出 - 根据环境类型选择编码
        if env_type == 'windows':
            # Windows通常使用GBK或GB2312编码
            try:
                output = stdout.read().decode('gbk', errors='ignore')
                error = stderr.read().decode('gbk', errors='ignore')
            except:
                # 如果GBK解码失败，尝试UTF-8
                output = stdout.read().decode('utf-8', errors='ignore')
                error = stderr.read().decode('utf-8', errors='ignore')
        else:
            # Linux使用UTF-8编码
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
        
        exit_status = stdout.channel.recv_exit_status()
        
        # 合并输出和错误
        if error:
            if output:
                full_output = output + '\n' + error
            else:
                full_output = error
        else:
            full_output = output
        
        if exit_status == 0:
            return True, full_output, ''
        else:
            return False, full_output, f'命令执行失败，退出码: {exit_status}'
            
    except socket.timeout:
        error_msg = f'命令执行超时（{timeout}秒）'
        logger.error(f'SSH命令执行超时: {host}:{port}, 命令: {command}')
        return False, '', error_msg
    except paramiko.AuthenticationException as e:
        error_msg = f'SSH认证失败: {str(e)}'
        logger.error(f'SSH认证失败: {host}:{port}@{user}')
        return False, '', error_msg
    except paramiko.SSHException as e:
        error_msg = f'SSH异常: {str(e)}'
        logger.error(f'SSH异常: {host}:{port}, 错误: {e}')
        return False, '', error_msg
    except Exception as e:
        error_msg = f'执行命令时出错: {str(e)}'
        logger.exception(f'执行SSH命令时出错: {e}')
        return False, '', error_msg
    finally:
        if ssh:
            try:
                ssh.close()
            except:
                pass


def test_ssh_connection(host, user, password, port=22):
    """
    测试SSH连接
    
    Args:
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        port: SSH端口
    
    Returns:
        bool: 连接是否成功
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port, user, password, timeout=10)
        ssh.close()
        return True
    except Exception as e:
        logger.error(f'SSH连接测试失败: {e}')
        return False


def upload_files_via_sftp(host, user, password, port=22, local_dir='packet_agent', env_type='linux'):
    """
    通过SFTP上传目录下的所有文件到远程主机
    
    Args:
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        port: SSH端口
        local_dir: 本地目录路径（相对于项目根目录）
        remote_dir: 远程目录路径
    
    Returns:
        tuple: (success: bool, message: str, files: list)
    """
    try:
        # 根据环境类型确定远程目录
        if env_type == 'windows':
            remote_dir = 'C:\\packet_agent'
        else:
            remote_dir = '/opt/packet_agent'
        
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_path = os.path.join(project_root, local_dir)
        
        if not os.path.exists(local_path):
            return False, f'本地目录不存在: {local_path}', []
        
        # 建立SSH连接
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port, user, password, timeout=30)
        
        # 创建SFTP客户端
        sftp = ssh.open_sftp()
        
        # 在远程主机创建目录（如果不存在）
        if env_type == 'windows':
            # Windows: 使用PowerShell创建目录
            ssh.exec_command(f'powershell -Command "if (-not (Test-Path {remote_dir})) {{ New-Item -ItemType Directory -Path {remote_dir} }}"')
        else:
            # Linux: 使用mkdir -p
            ssh.exec_command(f'mkdir -p {remote_dir}')
        time.sleep(0.5)
        
        uploaded_files = []
        failed_files = []
        
        logger.info(f'[文件上传] 开始上传文件，本地目录: {local_path}, 远程目录: {remote_dir}')
        logger.info(f'[文件上传] 环境类型: {env_type}')
        
        # 遍历本地目录下的所有文件
        for root, dirs, files in os.walk(local_path):
            # 计算相对路径
            rel_path = os.path.relpath(root, local_path)
            if rel_path == '.':
                remote_subdir = remote_dir
            else:
                remote_subdir = os.path.join(remote_dir, rel_path).replace('\\', '/')
            
            # 创建远程子目录
            try:
                sftp.stat(remote_subdir)
            except IOError:
                if env_type == 'windows':
                    ssh.exec_command(f'powershell -Command "if (-not (Test-Path {remote_subdir})) {{ New-Item -ItemType Directory -Path {remote_subdir} }}"')
                else:
                    ssh.exec_command(f'mkdir -p {remote_subdir}')
                time.sleep(0.3)
            
            # 上传文件（跳过industrial_protocol_agent.py和goose_sv_api.py，稍后单独处理）
            for filename in files:
                # 跳过industrial_protocol_agent.py和goose_sv_api.py，稍后单独处理
                if filename in ['industrial_protocol_agent.py', 'goose_sv_api.py']:
                    logger.info(f'[文件上传] 跳过文件（稍后单独处理）: {filename}')
                    continue
                    
                local_file = os.path.join(root, filename)
                remote_file = os.path.join(remote_subdir, filename)
                if env_type == 'windows':
                    remote_file = remote_file.replace('/', '\\')
                else:
                    remote_file = remote_file.replace('\\', '/')
                
                try:
                    logger.debug(f'[文件上传] 上传文件: {local_file} -> {remote_file}')
                    sftp.put(local_file, remote_file)
                    uploaded_files.append(remote_file)
                    logger.info(f'[文件上传] 文件上传成功: {filename} -> {remote_file}')
                except Exception as e:
                    failed_files.append({'file': filename, 'error': str(e)})
                    logger.error(f'[文件上传] 文件上传失败: {local_file} -> {remote_file}, 错误: {e}')
                    import traceback
                    logger.error(f'[文件上传] 详细错误: {traceback.format_exc()}')
        
        # 同时上传industrial_protocol_agent.py和goose_sv_api.py（在关闭sftp之前）
        # 注意：project_root已经在上面计算过了，这里直接使用
        files_to_upload = [
            ('industrial_protocol_agent.py', '工控协议Agent'),
            ('goose_sv_api.py', 'GOOSE/SV API')
        ]
        
        for filename, description in files_to_upload:
            file_path = os.path.join(project_root, 'packet_agent', filename)
            logger.info(f'[文件上传] 检查{description}文件: {file_path}')
            
            if os.path.exists(file_path):
                logger.info(f'[文件上传] {description}文件存在，开始上传')
                remote_file = os.path.join(remote_dir, filename)
                if env_type == 'windows':
                    remote_file = remote_file.replace('/', '\\')
                
                logger.info(f'[文件上传] 目标路径: {remote_file}')
                
                try:
                    # 强制上传，不检查文件是否存在（因为可能检查不准确）
                    logger.info(f'[文件上传] 强制上传{description}文件（不检查远程文件）')
                    
                    # 上传文件
                    logger.info(f'[文件上传] 开始上传文件: {file_path} -> {remote_file}')
                    file_size = os.path.getsize(file_path)
                    logger.info(f'[文件上传] 文件大小: {file_size} 字节')
                    
                    # 直接上传，覆盖已存在的文件
                    sftp.put(file_path, remote_file)
                    uploaded_files.append(remote_file)
                    logger.info(f'[文件上传] SFTP上传完成')
                    
                    # 验证文件是否上传成功
                    try:
                        verify_attr = sftp.stat(remote_file)
                        verify_size = verify_attr.st_size
                        logger.info(f'[文件上传] 上传后验证: 远程文件大小: {verify_size} 字节')
                        if verify_size == file_size:
                            logger.info(f'[文件上传] {description}文件上传成功，文件大小验证通过: {remote_file}')
                        else:
                            logger.warning(f'[文件上传] 文件大小不匹配: 本地 {file_size} 字节, 远程 {verify_size} 字节')
                    except Exception as e:
                        logger.warning(f'[文件上传] 验证远程文件失败: {e}')
                        # 即使验证失败，也认为上传成功（可能是权限问题）
                        logger.info(f'[文件上传] {description}文件上传完成（验证失败但继续）: {remote_file}')
                except Exception as e:
                    failed_files.append({'file': filename, 'error': str(e)})
                    logger.error(f'[文件上传] {description}文件上传失败: {file_path} -> {remote_file}, 错误: {e}')
                    import traceback
                    logger.error(f'[文件上传] 详细错误信息: {traceback.format_exc()}')
            else:
                logger.warning(f'[文件上传] {description}文件不存在: {file_path}')
        
        # 列出packet_agent目录下的文件（用于调试）
        packet_agent_dir = os.path.join(project_root, 'packet_agent')
        if os.path.exists(packet_agent_dir):
            packet_agent_files = os.listdir(packet_agent_dir)
            logger.info(f'[文件上传] packet_agent目录下的文件: {packet_agent_files}')
            if os.path.exists(packet_agent_dir):
                try:
                    dir_files = os.listdir(packet_agent_dir)
                    logger.warning(f'[文件上传] packet_agent目录下的文件: {dir_files}')
                except Exception as e:
                    logger.warning(f'[文件上传] 无法列出目录文件: {e}')
        
        sftp.close()
        ssh.close()
        
        logger.info(f'[文件上传] 上传完成，成功: {len(uploaded_files)} 个文件, 失败: {len(failed_files)} 个文件')
        if uploaded_files:
            logger.info(f'[文件上传] 成功上传的文件列表（前10个）: {uploaded_files[:10]}')
            if len(uploaded_files) > 10:
                logger.info(f'[文件上传] ... 还有 {len(uploaded_files) - 10} 个文件')
        if failed_files:
            logger.error(f'[文件上传] 失败的文件列表: {failed_files}')
        
        if failed_files:
            return True, f'部分文件上传失败: {len(failed_files)} 个文件失败', uploaded_files
        else:
            return True, f'成功上传 {len(uploaded_files)} 个文件', uploaded_files
            
    except Exception as e:
        logger.exception(f'上传文件失败: {e}')
        return False, f'上传文件失败: {str(e)}', []


def read_remote_log(ssh, log_path, env_type='windows'):
    """
    读取远程日志文件（Windows用gbk解码，Linux用utf-8）
    
    Args:
        ssh: SSH客户端
        log_path: 日志文件路径
        env_type: 环境类型（'windows' 或 'linux'）
    
    Returns:
        str: 日志内容
    """
    try:
        # 先检查文件是否存在
        if env_type == 'windows':
            check_cmd = f'if exist "{log_path}" (echo exists) else (echo not exists)'
            encoding = 'gbk'
        else:
            check_cmd = f'test -f "{log_path}" && echo exists || echo not exists'
            encoding = 'utf-8'
        
        stdin_check, stdout_check, stderr_check = ssh.exec_command(check_cmd, timeout=3)
        file_exists = stdout_check.read().decode(encoding, errors='ignore').strip()
        
        if file_exists != 'exists':
            return f"日志文件不存在: {log_path}"
        
        # 读取文件内容
        if env_type == 'windows':
            read_cmd = f'type "{log_path}"'
        else:
            read_cmd = f'cat "{log_path}"'
        
        stdin_log, stdout_log, stderr_log = ssh.exec_command(read_cmd, timeout=5)
        content = stdout_log.read().decode(encoding, errors='ignore')
        stderr_content = stderr_log.read().decode(encoding, errors='ignore')
        
        if content or stderr_content:
            # 截取前2000字符，避免日志过长
            return f"日志内容：\n{content[:2000]}\n错误：{stderr_content}"
        else:
            return "日志文件为空"
    except Exception as e:
        return f"读取日志失败：{str(e)}"


def start_agent(host, user, password, port=22, env_type='linux'):
    """
    启动远程Agent程序
    
    Args:
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        port: SSH端口
        env_type: 环境类型（'windows' 或 'linux'）
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # 根据环境类型确定远程目录
        if env_type == 'windows':
            remote_dir = 'C:\\packet_agent'
        else:
            remote_dir = '/opt/packet_agent'
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port, user, password, timeout=30)
        
        if env_type == 'windows':
            # Windows环境：使用start_agent.bat或start_agent_simple.bat
            # 先检查是否有正在运行的agent进程
            stdin, stdout, stderr = ssh.exec_command('tasklist | findstr python')
            running = stdout.read().decode('utf-8', errors='ignore')
            
            if 'python' in running.lower():
                # 进一步检查是否是packet_agent进程
                stdin2, stdout2, stderr2 = ssh.exec_command(f'wmic process where "commandline like \'%packet_agent%\'" get processid')
                pid = stdout2.read().decode('utf-8', errors='ignore').strip()
                if pid and pid.replace('ProcessId', '').strip():
                    ssh.close()
                    return False, 'Agent程序已在运行中'
            
            # 启动agent（后台运行）
            # 直接执行Python脚本，在后台运行，并将输出重定向到日志文件
            agent_script = os.path.join(remote_dir, 'packet_agent.py').replace('/', '\\')
            log_file = os.path.join(remote_dir, 'agent.log').replace('/', '\\')
            marker_file = os.path.join(remote_dir, 'agent_starting.marker').replace('/', '\\')
            
            # 先创建启动标记文件
            try:
                marker_cmd = f'echo start_time=%date% %time% > {marker_file}'
                stdin_marker, stdout_marker, stderr_marker = ssh.exec_command(marker_cmd, timeout=5)
                stdout_marker.read()
            except Exception as e:
                pass
            
            # 使用已上传的批处理文件启动（通过SFTP上传，避免转义错误）
            batch_file = os.path.join(remote_dir, 'start_agent.bat').replace('/', '\\')
            batch_log_file = os.path.join(remote_dir, 'agent_batch.log').replace('/', '\\')
            start_log_file = os.path.join(remote_dir, 'start_agent_log.log').replace('/', '\\')
            
            # 直接执行批处理文件（已通过SFTP上传，无需远程创建）
            cmd = f'start /b cmd /c ""{batch_file}" > "{start_log_file}" 2>&1 ^& exit"'
            # 设置命令超时，避免卡住
            transport = ssh.get_transport()
            if transport:
                transport.set_keepalive(30)
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
            try:
                stdout.read()
            except:
                pass
            
            # 短等待（3秒）让批处理执行完成
            time.sleep(3)

            # 轮询检查Agent启动状态（最多20秒，每2秒检查一次）
            max_wait_seconds = 20
            check_interval = 2
            agent_started = False

            for wait_time in range(0, max_wait_seconds, check_interval):
                # 检查8888端口是否监听（使用PowerShell命令）
                port_cmd = 'powershell -Command "(Get-NetTCPConnection -LocalPort 8888 -State Listen).Count"'
                stdin_port, stdout_port, stderr_port = ssh.exec_command(port_cmd, timeout=5)
                port_count = stdout_port.read().decode('gbk', errors='ignore').strip()

                if port_count and port_count.isdigit() and int(port_count) > 0:
                    agent_started = True
                    logger.info(f'[启动Agent] Agent启动成功，8888端口已监听（等待{wait_time}秒）')
                    break

                time.sleep(check_interval)

            if not agent_started:
                # 最终检查进程是否存在（兜底检查）
                process_cmd = 'wmic process where "commandline like \'%packet_agent.py%\' and name=\'pythonw.exe\'" get processid, name'
                stdin_proc, stdout_proc, stderr_proc = ssh.exec_command(process_cmd, timeout=10)
                proc_output = stdout_proc.read().decode('gbk', errors='ignore').strip()
                if proc_output and ('pythonw.exe' in proc_output or 'packet_agent' in proc_output.lower()):
                    # 进程存在但端口未监听，再等待5秒
                    time.sleep(5)
                    port_cmd = 'powershell -Command "(Get-NetTCPConnection -LocalPort 8888 -State Listen).Count"'
                    stdin_port, stdout_port, stderr_port = ssh.exec_command(port_cmd, timeout=5)
                    port_count = stdout_port.read().decode('gbk', errors='ignore').strip()
                    if port_count and port_count.isdigit() and int(port_count) > 0:
                        agent_started = True
                        logger.info(f'[启动Agent] Agent启动成功（额外等待后端口监听）')

            if agent_started:
                # Agent启动成功，启动工控协议Agent
                industrial_agent_script = os.path.join(remote_dir, 'industrial_protocol_agent.py').replace('/', '\\')
                industrial_agent_log = os.path.join(remote_dir, 'industrial_protocol_agent.log').replace('/', '\\')

                # 检查industrial_protocol_agent.py是否存在
                check_cmd = f'if exist "{industrial_agent_script}" (echo FILE_EXISTS) else (echo FILE_NOT_EXISTS)'
                stdin_check, stdout_check, stderr_check = ssh.exec_command(check_cmd, timeout=5)
                check_result = stdout_check.read().decode('gbk', errors='ignore')

                if 'FILE_EXISTS' in check_result:
                    # 启动industrial_protocol_agent.py（使用pythonw后台运行）
                    start_industrial_cmd = f'start /b "{os.path.join(remote_dir, "start_industrial_agent.bat").replace("/", "\\")}"'
                    # 先创建启动脚本
                    start_industrial_bat = f'''@echo off
cd /d {remote_dir}
set PYTHONW_PATH=C:\\Python39\\pythonw.exe
if not exist "%PYTHONW_PATH%" (
    for /f "delims=" %%i in ('where pythonw.exe 2^>nul') do set PYTHONW_PATH=%%i
)
if exist "%PYTHONW_PATH%" (
    start /b "%PYTHONW_PATH%" "{industrial_agent_script}" 8889 >> "{industrial_agent_log}" 2>&1
)'''
                    # 创建临时批处理文件
                    temp_bat = os.path.join(remote_dir, 'start_industrial_agent.bat').replace('/', '\\')
                    try:
                        sftp = ssh.open_sftp()
                        with sftp.file(temp_bat, 'w') as f:
                            f.write(start_industrial_bat)
                        sftp.close()
                        time.sleep(1)
                        # 执行启动命令
                        stdin_industrial, stdout_industrial, stderr_industrial = ssh.exec_command(start_industrial_cmd, timeout=10)
                        stdout_industrial.read()
                        time.sleep(2)
                        # 检查8889端口
                        port_cmd_industrial = 'powershell -Command "(Get-NetTCPConnection -LocalPort 8889 -State Listen).Count"'
                        stdin_port_ind, stdout_port_ind, stderr_port_ind = ssh.exec_command(port_cmd_industrial, timeout=5)
                        port_count_ind = stdout_port_ind.read().decode('gbk', errors='ignore').strip()
                        if port_count_ind and port_count_ind.isdigit() and int(port_count_ind) > 0:
                            logger.info(f'[启动Agent] 工控协议Agent启动成功，8889端口已监听')
                    except Exception as e:
                        logger.warning(f'[启动Agent] 启动工控协议Agent失败: {e}')

                # 创建成功标记文件
                try:
                    success_marker = os.path.join(remote_dir, 'agent_running.marker').replace('/', '\\')
                    success_cmd = f'powershell -Command "$startTime = Get-Date -Format \'yyyy-MM-dd HH:mm:ss\'; $content = \"status=running`nstart_time=$startTime`nport=8888\"; Set-Content -Path \'{success_marker}\' -Value $content -Encoding UTF8"'
                    stdin_success, stdout_success, stderr_success = ssh.exec_command(success_cmd, timeout=5)
                    stdout_success.read()
                    # 删除启动标记文件
                    try:
                        ssh.exec_command(f'del {marker_file}', timeout=3)
                    except:
                        pass
                except Exception as e:
                    pass
                ssh.close()
                return True, 'Agent启动成功，8888端口已监听'
            else:
                # Agent启动失败，读取日志排查问题
                logger.warning(f'[启动Agent] Agent启动失败，8888端口未监听')
                try:
                    stdin_log2, stdout_log2, stderr_log2 = ssh.exec_command(f'type {log_file}', timeout=5)
                    log_content2 = stdout_log2.read().decode('utf-8', errors='ignore')
                    if log_content2 and log_content2.strip():
                        error_msg = f'Agent启动失败，8888端口未监听。日志: {log_content2[-500:]}'
                    else:
                        error_msg = 'Agent启动失败，8888端口未监听，日志文件为空。可能进程启动后立即退出，请检查Python环境和依赖'
                except Exception as e:
                    error_msg = 'Agent启动失败，8888端口未监听，请检查日志文件'
                ssh.close()
                return False, error_msg
            
        else:
            # Linux环境：使用nohup后台运行
            # 先检查是否有正在运行的agent进程
            stdin, stdout, stderr = ssh.exec_command(f'ps aux | grep "[p]acket_agent.py"')
            running = stdout.read().decode('utf-8', errors='ignore')
            
            if running.strip():
                ssh.close()
                return False, 'Agent程序已在运行中'
            
            # 启动agent（后台运行）
            agent_script = os.path.join(remote_dir, 'packet_agent.py')
            log_file = os.path.join(remote_dir, 'agent.log')
            marker_file = os.path.join(remote_dir, 'agent_starting.marker')
            
            # 先创建启动标记文件
            try:
                marker_cmd = f'echo "start_time=$(date +\'%Y-%m-%d %H:%M:%S\')" > {marker_file}'
                stdin_marker, stdout_marker, stderr_marker = ssh.exec_command(marker_cmd, timeout=5)
                stdout_marker.read()
            except Exception as e:
                pass
            
            # 使用nohup后台运行，并重定向输出
            cmd = f'cd {remote_dir} && nohup python3 {agent_script} --host 0.0.0.0 --port 8888 > {log_file} 2>&1 &'
            logger.info(f'[启动Agent] 执行启动命令: {cmd}')
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            # 读取命令输出
            stdout_output = stdout.read().decode('utf-8', errors='ignore')
            stderr_output = stderr.read().decode('utf-8', errors='ignore')
            logger.debug(f'[启动Agent] 启动命令输出: stdout={stdout_output}, stderr={stderr_output}')
            
            # 启动工控协议Agent（industrial_protocol_agent.py，端口8889）
            industrial_agent_script = os.path.join(remote_dir, 'industrial_protocol_agent.py')
            industrial_agent_log = os.path.join(remote_dir, 'industrial_protocol_agent.log')
            
            # 检查文件是否存在
            check_cmd = f'test -f {industrial_agent_script} && echo FILE_EXISTS'
            stdin_check, stdout_check, stderr_check = ssh.exec_command(check_cmd, timeout=5)
            check_result = stdout_check.read().decode('utf-8', errors='ignore')
            
            if 'FILE_EXISTS' in check_result:
                logger.info(f'[启动Agent] 启动工控协议Agent（端口8889）')
                cmd_industrial = f'cd {remote_dir} && nohup python3 {industrial_agent_script} 8889 > {industrial_agent_log} 2>&1 &'
                logger.info(f'[启动Agent] 执行工控协议Agent启动命令: {cmd_industrial}')
                stdin_ind, stdout_ind, stderr_ind = ssh.exec_command(cmd_industrial)
                stdout_ind.read()
                logger.info(f'[启动Agent] 工控协议Agent启动命令已执行')
            else:
                logger.warning(f'[启动Agent] industrial_protocol_agent.py文件不存在，跳过启动')
            
            logger.info(f'[启动Agent] 等待进程启动...')
            time.sleep(5)
            
            # 读取日志文件查看启动情况
            try:
                logger.info(f'[启动Agent] 读取日志文件: {log_file}')
                stdin_log, stdout_log, stderr_log = ssh.exec_command(f'tail -n 50 {log_file}')
                log_content = stdout_log.read().decode('utf-8', errors='ignore')
                if log_content:
                    logger.info(f'[启动Agent] 日志文件内容（最后50行）: {log_content}')
                else:
                    logger.warning(f'[启动Agent] 日志文件为空或不存在')
            except Exception as e:
                logger.warning(f'[启动Agent] 读取日志文件失败: {e}')
            
            # 检查是否启动成功：先检查进程，再检查端口
            logger.info(f'[启动Agent] 检查进程是否启动')
            stdin, stdout, stderr = ssh.exec_command(f'ps aux | grep "[p]acket_agent.py"')
            running = stdout.read().decode('utf-8', errors='ignore')
            stderr_output = stderr.read().decode('utf-8', errors='ignore')
            logger.debug(f'[启动Agent] 进程检查输出: {running}, 错误: {stderr_output}')
            
            if running.strip():
                # 检查8888端口是否在监听
                logger.info(f'[启动Agent] 进程已启动，检查8888端口')
                stdin2, stdout2, stderr2 = ssh.exec_command('netstat -tlnp 2>/dev/null | grep :8888 || ss -tlnp 2>/dev/null | grep :8888 || lsof -i :8888 2>/dev/null', timeout=5)
                try:
                    port_check = stdout2.read().decode('utf-8', errors='ignore')
                    port_stderr = stderr2.read().decode('utf-8', errors='ignore')
                    logger.debug(f'[启动Agent] 端口检查输出: {port_check}, 错误: {port_stderr}')
                except Exception as e:
                    logger.warning(f'[启动Agent] 读取端口检查输出时出错: {e}')
                    port_check = ''
                    port_stderr = ''
                
                if ':8888' in port_check or '8888' in port_check:
                    logger.info(f'[启动Agent] Agent启动成功，8888端口已监听')
                    
                    # 检查工控协议Agent的8889端口
                    logger.info(f'[启动Agent] 检查工控协议Agent的8889端口')
                    stdin_port_ind, stdout_port_ind, stderr_port_ind = ssh.exec_command('netstat -tlnp 2>/dev/null | grep :8889 || ss -tlnp 2>/dev/null | grep :8889 || lsof -i :8889 2>/dev/null', timeout=5)
                    try:
                        port_check_ind = stdout_port_ind.read().decode('utf-8', errors='ignore')
                        if ':8889' in port_check_ind or '8889' in port_check_ind:
                            logger.info(f'[启动Agent] 工控协议Agent启动成功，8889端口已监听')
                        else:
                            logger.warning(f'[启动Agent] 工控协议Agent可能未启动，8889端口未监听')
                    except Exception as e:
                        logger.warning(f'[启动Agent] 检查工控协议Agent端口失败: {e}')
                    
                    # 创建成功标记文件
                    try:
                        success_marker = os.path.join(remote_dir, 'agent_running.marker')
                        success_cmd = f'echo -e "status=running\\nstart_time=$(date +\'%Y-%m-%d %H:%M:%S\')\\nport=8888" > {success_marker}'
                        stdin_success, stdout_success, stderr_success = ssh.exec_command(success_cmd, timeout=5)
                        stdout_success.read()
                        # 删除启动标记文件
                        try:
                            ssh.exec_command(f'rm -f {marker_file}', timeout=3)
                        except:
                            pass
                        logger.info(f'[启动Agent] 成功标记文件已创建')
                    except Exception as e:
                        logger.warning(f'[启动Agent] 创建成功标记文件失败: {e}')
                    ssh.close()
                    return True, 'Agent启动成功，8888端口已监听'
                else:
                    # 端口未监听，再次读取日志文件查看错误
                    logger.warning(f'[启动Agent] Agent进程已启动，但8888端口未监听')
                    try:
                        stdin_log2, stdout_log2, stderr_log2 = ssh.exec_command(f'tail -n 100 {log_file}', timeout=5)
                        log_content2 = stdout_log2.read().decode('utf-8', errors='ignore')
                        if log_content2 and log_content2.strip():
                            error_msg = f'Agent进程已启动，但8888端口未监听。日志: {log_content2[-500:]}'
                        else:
                            error_msg = 'Agent进程已启动，但8888端口未监听，请检查日志文件'
                    except Exception as e:
                        error_msg = 'Agent进程已启动，但8888端口未监听，请检查日志文件'
                    ssh.close()
                    return False, error_msg
            else:
                # 进程未找到
                logger.error(f'[启动Agent] Agent启动失败，进程未找到')
                start_log = read_remote_log(ssh, start_log_file, env_type)
                batch_log = read_remote_log(ssh, batch_log_file, env_type)
                agent_log = read_remote_log(ssh, log_file, env_type)
                ssh.close()
                return False, f'Agent启动失败，进程未找到。批处理日志：{batch_log[:500]}，Agent日志：{agent_log[:500]}'
            
    except paramiko.AuthenticationException as e:
        logger.error(f'[启动Agent] SSH认证失败: {e}')
        return False, f'SSH认证失败: {str(e)}'
    except paramiko.SSHException as e:
        logger.error(f'[启动Agent] SSH连接异常: {e}')
        return False, f'SSH连接异常: {str(e)}'
    except socket.timeout as e:
        logger.error(f'[启动Agent] SSH连接超时: {e}')
        return False, f'SSH连接超时: {str(e)}'
    except Exception as e:
        logger.exception(f'[启动Agent] 启动Agent失败: {e}')
        return False, f'启动Agent失败: {str(e)}'


def stop_agent(host, user, password, port=22, env_type='linux'):
    """
    停止远程Agent程序
    
    Args:
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        port: SSH端口
        env_type: 环境类型（'windows' 或 'linux'）
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port, user, password, timeout=30)
        
        if env_type == 'windows':
            # Windows环境：使用wmic查找并杀死进程
            cmd = 'wmic process where "commandline like \'%packet_agent%\'" delete'
            stdin, stdout, stderr = ssh.exec_command(cmd)
            time.sleep(2)
            
            # 停止工控协议Agent（8889端口）- 尝试多种方式
            # 方法1: 通过PowerShell查找并杀死
            cmd_industrial1 = 'powershell -Command "$conn = Get-NetTCPConnection -LocalPort 8889 -State Listen -ErrorAction SilentlyContinue; if ($conn) { $conn | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force } }"'
            stdin_ind1, stdout_ind1, stderr_ind1 = ssh.exec_command(cmd_industrial1)
            stdout_ind1.read()
            time.sleep(1)
            # 方法2: 通过进程名杀死
            cmd_industrial2 = 'wmic process where "commandline like \'%industrial_protocol_agent%\'" delete'
            stdin_ind2, stdout_ind2, stderr_ind2 = ssh.exec_command(cmd_industrial2)
            stdout_ind2.read()
            time.sleep(1)
            # 方法3: 通过netstat查找PID并杀死
            cmd_industrial3 = 'for /f "tokens=5" %a in (\'netstat -ano ^| findstr ":8889" ^| findstr "LISTENING"\') do taskkill /F /PID %a 2>nul'
            stdin_ind3, stdout_ind3, stderr_ind3 = ssh.exec_command(cmd_industrial3)
            stdout_ind3.read()
            time.sleep(1)
            
            # 检查是否已停止
            stdin, stdout, stderr = ssh.exec_command('wmic process where "commandline like \'%packet_agent%\'" get processid')
            pid = stdout.read().decode('utf-8', errors='ignore').strip()
            ssh.close()
            
            if pid and pid.replace('ProcessId', '').strip():
                return False, 'Agent停止失败，进程仍在运行'
            else:
                return True, 'Agent已停止'
        else:
            # Linux环境：使用pkill或killall
            cmd = 'pkill -f packet_agent.py || killall -9 packet_agent.py 2>/dev/null'
            stdin, stdout, stderr = ssh.exec_command(cmd)
            time.sleep(2)
            
            # 停止工控协议Agent（8889端口）- 尝试多种方式
            # 方法1: 通过lsof查找PID并杀死
            cmd_industrial1 = 'lsof -ti:8889 | xargs -r kill -9 2>/dev/null'
            stdin_ind1, stdout_ind1, stderr_ind1 = ssh.exec_command(cmd_industrial1)
            stdout_ind1.read()
            time.sleep(1)
            # 方法2: 通过进程名杀死
            cmd_industrial2 = 'pkill -9 -f "industrial_protocol_agent.py" 2>/dev/null'
            stdin_ind2, stdout_ind2, stderr_ind2 = ssh.exec_command(cmd_industrial2)
            stdout_ind2.read()
            time.sleep(1)
            # 方法3: 通过fuser杀死
            cmd_industrial3 = 'fuser -k 8889/tcp 2>/dev/null'
            stdin_ind3, stdout_ind3, stderr_ind3 = ssh.exec_command(cmd_industrial3)
            stdout_ind3.read()
            time.sleep(1)
            
            # 检查是否已停止
            stdin, stdout, stderr = ssh.exec_command('ps aux | grep "[p]acket_agent.py"')
            running = stdout.read().decode('utf-8', errors='ignore')
            ssh.close()
            
            if running.strip():
                return False, 'Agent停止失败，进程仍在运行'
            else:
                return True, 'Agent已停止'
            
    except Exception as e:
        logger.exception(f'停止Agent失败: {e}')
        return False, f'停止Agent失败: {str(e)}'


def check_agent_status(host, user, password, port=22, env_type='linux'):
    """
    检查Agent运行状态（通过检查8888端口是否监听）
    
    Args:
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        port: SSH端口
        env_type: 环境类型（'windows' 或 'linux'）
    
    Returns:
        bool: Agent是否在运行（8888端口是否监听）
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port, user, password, timeout=10)
        
        if env_type == 'windows':
            # Windows: 检查8888端口是否在监听
            stdin, stdout, stderr = ssh.exec_command('netstat -an | findstr :8888')
            port_check = stdout.read().decode('utf-8', errors='ignore')
            ssh.close()
            return 'LISTENING' in port_check or ':8888' in port_check
        else:
            # Linux: 检查8888端口是否在监听
            stdin, stdout, stderr = ssh.exec_command('netstat -tlnp 2>/dev/null | grep :8888 || ss -tlnp 2>/dev/null | grep :8888 || lsof -i :8888 2>/dev/null')
            port_check = stdout.read().decode('utf-8', errors='ignore')
            ssh.close()
            return ':8888' in port_check or '8888' in port_check
            
    except Exception as e:
        logger.error(f'检查Agent状态失败: {e}')
        return False

