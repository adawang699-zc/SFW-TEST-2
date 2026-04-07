#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程Agent管理模块
支持SSH文件传输、远程执行、状态监控和日志查看
"""

import os
import json
import logging
import paramiko
import threading
import time
import subprocess
import socket
from datetime import datetime
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class RemoteAgentManager:
    """远程Agent管理器"""
    
    def __init__(self):
        self.connections = {}  # 存储SSH连接
        self.agent_status = {}  # 存储Agent状态
        self.log_threads = {}  # 存储日志监控线程
        self.connection_lock = threading.Lock()  # 连接管理锁
    
    def _decode_output(self, raw_bytes: bytes, context: str = "") -> str:
        """
        智能解码SSH命令输出，处理不同编码
        
        Args:
            raw_bytes: 原始字节数据
            context: 上下文信息，用于日志
            
        Returns:
            解码后的字符串
        """
        if not raw_bytes:
            return ""
        
        # 尝试不同的编码方式
        encodings = ['utf-8', 'gbk', 'gb2312', 'cp936']
        
        for encoding in encodings:
            try:
                result = raw_bytes.decode(encoding)
                return result
            except UnicodeDecodeError:
                continue
        
        # 所有编码都失败，使用UTF-8忽略错误
        logger.warning(f"{context} 所有编码尝试失败，使用UTF-8忽略错误模式")
        return raw_bytes.decode('utf-8', errors='ignore')
    
    def _safe_exec_command(self, ssh, command: str, timeout: int = 5) -> Tuple[int, str, str]:
        """安全地执行SSH命令，确保通道正确关闭"""
        stdin = stdout = stderr = None
        try:
            # 检查SSH连接是否有效
            if not ssh:
                logger.debug(f"命令执行失败: SSH对象为空")
                return -1, "", "SSH连接不存在"
            
            try:
                transport = ssh.get_transport()
                if not transport or not transport.is_active():
                    logger.debug(f"命令执行失败: SSH连接已失效")
                    return -1, "", "SSH session not active"
            except Exception as check_e:
                logger.debug(f"命令执行失败: SSH连接检查异常: {check_e}")
                return -1, "", f"SSH连接检查失败: {check_e}"
            
            stdin, stdout, stderr = ssh.exec_command(command)
            
            # 设置超时
            if stdout.channel:
                stdout.channel.settimeout(timeout)
            if stderr.channel:
                stderr.channel.settimeout(timeout)
            
            # 获取退出状态
            exit_status = stdout.channel.recv_exit_status()
            
            # 读取输出
            output = self._decode_output(stdout.read(), f"命令输出-{command}")
            error = self._decode_output(stderr.read(), f"命令错误-{command}")
            
            return exit_status, output, error
            
        except socket.timeout:
            logger.warning(f"命令执行超时 ({timeout}秒): {command}")
            return -1, "", f"命令执行超时 ({timeout}秒)"
        except Exception as e:
            # 对于SSH session not active错误，降低日志级别（这是正常的连接失效情况）
            error_msg = str(e)
            if "SSH session not active" in error_msg or "not active" in error_msg:
                logger.debug(f"命令执行异常（SSH连接已失效）: {error_msg}")
            else:
                logger.warning(f"命令执行异常: {error_msg}")
            return -1, "", error_msg
        finally:
            # 确保所有通道都被关闭
            for channel_stream in [stdin, stdout, stderr]:
                if channel_stream and hasattr(channel_stream, 'channel'):
                    try:
                        if channel_stream.channel and not channel_stream.channel.closed:
                            channel_stream.channel.close()
                    except:
                        pass

    def cleanup_stale_connections(self):
        """清理失效的SSH连接"""
        with self.connection_lock:
            stale_keys = []
            for connection_key, conn_info in self.connections.items():
                try:
                    ssh = conn_info['ssh']
                    # 快速测试连接是否还有效
                    exit_status, output, error = self._safe_exec_command(ssh, 'echo test', timeout=2)
                    if exit_status != 0 or output.strip() != 'test':
                        stale_keys.append(connection_key)
                except:
                    stale_keys.append(connection_key)
            
            # 清理失效连接
            for key in stale_keys:
                try:
                    self.connections[key]['ssh'].close()
                except:
                    pass
                del self.connections[key]
                logger.info(f"清理失效连接: {key}")
            
            if stale_keys:
                logger.info(f"清理了 {len(stale_keys)} 个失效连接")
    
    def test_network_connectivity(self, host: str, port: int = 22, timeout: int = 5) -> Tuple[bool, str]:
        """测试网络连通性（不进行SSH认证）"""
        try:
            # 创建socket连接测试
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return True, "网络连通"
            else:
                return False, f"端口 {port} 不可达"
                
        except socket.gaierror as e:
            return False, f"无法解析主机名: {host}"
        except socket.timeout as e:
            return False, f"连接超时（{timeout}秒）"
        except Exception as e:
            return False, str(e)
        
    def connect_to_host(self, host: str, username: str, password: str, port: int = 22) -> Tuple[bool, str]:
        """连接到远程主机（带重试逻辑）"""
        connection_key = f"{host}:{port}"

        # 先清理失效连接
        self.cleanup_stale_connections()

        # 重试逻辑：最多重试 3 次，指数退避（1s, 2s, 4s）
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # 检查是否已有连接
                if connection_key in self.connections:
                    try:
                        # 测试现有连接是否还有效
                        ssh = self.connections[connection_key]['ssh']
                        exit_status, result, error = self._safe_exec_command(ssh, 'echo test', timeout=3)
                        if exit_status == 0 and result.strip() == "test":
                            return True, "连接成功（复用现有连接）"
                    except:
                        del self.connections[connection_key]

                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=10
                )

                # 测试连接 - 使用简单的命令避免引号问题
                exit_status, result, error_output = self._safe_exec_command(ssh, 'whoami', timeout=5)

                # 只要有输出且不为空，就认为连接成功
                if result and len(result) > 0:
                    self.connections[connection_key] = {
                        'ssh': ssh,
                        'host': host,
                        'port': port,
                        'username': username,
                        'password': password,
                        'connected_at': datetime.now()
                    }
                    return True, f"连接成功，当前用户：{result}"
                else:
                    ssh.close()
                    return False, f"连接测试失败，无法获取用户信息"

            except paramiko.AuthenticationException:
                # 认证失败不重试
                return False, "认证失败，用户名或密码错误"
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # 指数退避：1s, 2s, 4s
                    wait_time = 2 ** attempt
                    logger.warning(f"SSH 连接失败，准备重试 ({attempt+1}/{max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    # 所有重试失败
                    if isinstance(e, socket.timeout):
                        logger.error(f"连接超时：{e}")
                        return False, "连接超时，请检查网络连接和防火墙设置"
                    elif isinstance(e, socket.gaierror):
                        logger.error(f"DNS 解析失败：{e}")
                        return False, f"无法解析主机名：{host}"
                    elif isinstance(e, ConnectionRefusedError):
                        logger.error(f"连接被拒绝：{e}")
                        return False, f"连接被拒绝，请检查 SSH 服务是否运行在端口 {port}"
                    else:
                        logger.exception(f"连接到 {host}:{port} 失败：{e}")
                        return False, f"连接失败：{str(e)}"

        # 理论上不会到这里
        return False, f"连接失败：{last_error}"

    def disconnect_from_host(self, host: str, port: int = 22) -> bool:
        """断开与远程主机的连接"""
        connection_key = f"{host}:{port}"
        if connection_key in self.connections:
            try:
                self.connections[connection_key]['ssh'].close()
                del self.connections[connection_key]
                
                # 清理相关状态
                if connection_key in self.agent_status:
                    del self.agent_status[connection_key]
                if connection_key in self.log_threads:
                    self.log_threads[connection_key]['stop'] = True
                    del self.log_threads[connection_key]
                
                logger.info(f"已断开与 {host}:{port} 的连接")
                return True
            except Exception as e:
                logger.exception(f"断开连接失败: {e}")
                return False
        return False
    
    def check_file_consistency(self, host: str, local_path: str, remote_path: str, port: int = 22) -> Tuple[bool, str]:
        """检查本地和远程文件是否一致"""
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False, "未连接到目标主机"
        
        try:
            import hashlib
            
            # 计算本地文件MD5
            if not os.path.exists(local_path):
                return False, "本地文件不存在"
            
            with open(local_path, 'rb') as f:
                local_md5 = hashlib.md5(f.read()).hexdigest()
            
            ssh = self.connections[connection_key]['ssh']
            system_type = self.detect_system_type(host, port)
            
            # 检查远程文件是否存在并计算MD5
            if system_type == "windows":
                # Windows: 先检查文件是否存在，然后使用兼容性更好的方法计算MD5
                # 使用certutil命令，Win7也支持
                cmd = f'if exist "{remote_path}" (certutil -hashfile "{remote_path}" MD5 | findstr /v "hash" | findstr /v "CertUtil") else (echo FILE_NOT_EXISTS)'
            else:
                # Linux使用md5sum
                cmd = f'if [ -f "{remote_path}" ]; then md5sum "{remote_path}" | cut -d" " -f1; else echo "FILE_NOT_EXISTS"; fi'
            
            exit_status, remote_result, error_output = self._safe_exec_command(ssh, cmd, timeout=10)
            
            remote_result = remote_result.strip()
            
            if remote_result == "FILE_NOT_EXISTS":
                return False, "远程文件不存在，需要上传"
            
            # 处理MD5值
            if system_type == "windows":
                # certutil输出格式可能是中文或英文，MD5值可能用空格分隔
                # 例如: "fd 9b d3 d2 04 63 15 cd ed 91 bc c3 66 13 76 97"
                lines = remote_result.strip().split('\n')
                remote_md5 = ""
                for line in lines:
                    line = line.strip()
                    # 移除所有空格，检查是否是32位十六进制字符串
                    clean_line = line.replace(' ', '').replace('\t', '')
                    if len(clean_line) == 32 and all(c in '0123456789abcdefABCDEF' for c in clean_line):
                        remote_md5 = clean_line.lower()
                        break
                    # 也检查原始行是否是32位十六进制（无空格的情况）
                    elif len(line) == 32 and all(c in '0123456789abcdefABCDEF' for c in line):
                        remote_md5 = line.lower()
                        break
                
                if not remote_md5:
                    return False, "无法获取远程文件MD5值"
            else:
                # Linux md5sum输出格式直接就是MD5值
                remote_md5 = remote_result.lower()
            
            if local_md5 == remote_md5:
                return True, "文件一致，无需更新"
            else:
                return False, f"文件不一致，需要更新 (本地:{local_md5[:8]}... 远程:{remote_md5[:8]}...)"
                
        except Exception as e:
            logger.exception(f"检查文件一致性失败: {e}")
            return False, f"检查失败: {str(e)}"
    
    def check_port_occupation(self, host: str, port: int, agent_port: int, system_type: str) -> Tuple[bool, str]:
        """检查端口是否被占用"""
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False, ""
        
        try:
            ssh = self.connections[connection_key]['ssh']
            
            if system_type == "windows":
                # Windows: 使用netstat查找占用端口的进程
                check_cmd = f'netstat -ano | findstr ":{agent_port}" | findstr "LISTENING"'
            else:
                # Linux: 使用lsof或netstat查找占用端口的进程
                check_cmd = f'lsof -ti:{agent_port} || netstat -tulpn | grep ":{agent_port}" | grep "LISTEN"'
            
            exit_status, result, error_output = self._safe_exec_command(ssh, check_cmd, timeout=5)
            
            if result.strip():
                
                if system_type == "windows":
                    # 解析Windows netstat输出，提取PID
                    import re
                    # 匹配格式: TCP    0.0.0.0:8888    0.0.0.0:0    LISTENING    14300
                    match = re.search(rf':{agent_port}\s+.*?LISTENING\s+(\d+)', result)
                    if match:
                        pid = match.group(1)
                        return True, pid
                else:
                    # 解析Linux输出
                    lines = result.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            # lsof输出直接是PID，netstat需要解析
                            if line.isdigit():
                                return True, line.strip()
                            else:
                                # 从netstat输出中提取PID
                                parts = line.split()
                                if len(parts) > 6:
                                    pid_program = parts[-1]
                                    if '/' in pid_program:
                                        pid = pid_program.split('/')[0]
                                        return True, pid
                
                return True, "unknown"  # 端口被占用但无法确定PID
            else:
                return False, ""
                
        except Exception as e:
            logger.exception(f"检查端口占用失败: {e}")
            return False, ""
    
    def cleanup_port_occupation(self, host: str, port: int, agent_port: int, occupying_pid: str, system_type: str) -> bool:
        """清理占用端口的进程"""
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False
        
        try:
            ssh = self.connections[connection_key]['ssh']
            
            if occupying_pid == "unknown":
                logger.warning(f"[PORT-CLEANUP] 无法确定占用进程PID，尝试通用清理")
                if system_type == "windows":
                    # Windows: 尝试通过端口杀死进程
                    cleanup_cmd = f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr ":{agent_port}" ^| findstr "LISTENING"\') do taskkill /F /PID %a'
                else:
                    # Linux: 使用fuser杀死占用端口的进程
                    cleanup_cmd = f'fuser -k {agent_port}/tcp'
            else:
                logger.info(f"[PORT-CLEANUP] 清理占用进程 PID: {occupying_pid}")
                if system_type == "windows":
                    # Windows: 使用taskkill杀死进程
                    cleanup_cmd = f'taskkill /F /PID {occupying_pid}'
                else:
                    # Linux: 使用kill杀死进程
                    cleanup_cmd = f'kill -9 {occupying_pid}'
            
            logger.info(f"[PORT-CLEANUP] 执行清理命令: {cleanup_cmd}")
            exit_status, cleanup_output, cleanup_error = self._safe_exec_command(ssh, cleanup_cmd, timeout=5)
            
            logger.info(f"[PORT-CLEANUP] 清理结果: {cleanup_output}")
            if cleanup_error:
                logger.warning(f"[PORT-CLEANUP] 清理错误: {cleanup_error}")
            
            # 验证端口是否已释放
            time.sleep(1)
            is_still_occupied, _ = self.check_port_occupation(host, port, agent_port, system_type)
            if not is_still_occupied:
                logger.info(f"[PORT-CLEANUP] 端口 {agent_port} 清理成功")
                return True
            else:
                logger.warning(f"[PORT-CLEANUP] 端口 {agent_port} 仍被占用")
                return False
                
        except Exception as e:
            logger.exception(f"清理端口占用失败: {e}")
            return False

    def fix_file_permissions(self, host: str, port: int, file_path: str, system_type: str) -> Tuple[bool, str]:
        """修复文件权限"""
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False, "未连接到目标主机"
        
        try:
            ssh = self.connections[connection_key]['ssh']
            
            if system_type == "windows":
                # Windows: 给tdhx用户完全控制权限
                # 取消继承并给tdhx完全控制权限
                commands = [
                    f'icacls "{file_path}" /inheritance:r',  # 移除继承权限
                    f'icacls "{file_path}" /grant tdhx:F',   # 给tdhx完全控制
                    f'icacls "{file_path}" /grant Administrators:F',  # 给管理员完全控制
                ]
                
                for cmd in commands:
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    stdout.read()
                
                return True, "Windows权限修复完成"
            else:
                # Linux: 设置执行权限和所有者权限
                commands = [
                    f'chmod 755 "{file_path}"',  # 设置执行权限
                    f'chown $USER:$USER "{file_path}"'  # 设置所有者
                ]
                
                for cmd in commands:
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    stdout.read()
                
                return True, "Linux权限修复完成"
                
        except Exception as e:
            logger.exception(f"修复文件权限失败: {e}")
            return False, str(e)
    
    def upload_agent(self, host: str, local_path: str, remote_path: str, port: int = 22, force: bool = False) -> Tuple[bool, str]:
        """上传Agent文件到远程主机"""
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False, "未连接到目标主机"
        
        try:
            # 如果不是强制上传，先检查文件一致性
            # 注意：文件一致性检查可能不准确（特别是对于新文件），所以即使检查通过也继续上传
            if not force:
                is_consistent, check_msg = self.check_file_consistency(host, local_path, remote_path, port)
                if is_consistent:
                    logger.info(f"文件一致性检查通过: {check_msg}，但继续上传以确保文件存在")
                    # 即使检查通过，也继续上传（因为检查可能不准确，特别是对于新文件）
                else:
                    logger.info(f"文件需要更新: {check_msg}")
            
            ssh = self.connections[connection_key]['ssh']
            sftp = ssh.open_sftp()
            
            # 首先获取系统类型
            system_type = self.detect_system_type(host, port)
            
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path).replace('\\', '/')
            logger.info(f"检查远程目录: {remote_dir}")
            
            try:
                dir_stat = sftp.stat(remote_dir)
                logger.info(f"远程目录已存在: {remote_dir}")
            except FileNotFoundError:
                logger.info(f"远程目录不存在，正在创建: {remote_dir}")
                # 创建远程目录
                if system_type == "windows":
                    mkdir_cmd = f'mkdir "{remote_dir}"'
                else:
                    mkdir_cmd = f'mkdir -p "{remote_dir}"'
                
                stdin, stdout, stderr = ssh.exec_command(mkdir_cmd)
                exit_status = stdout.channel.recv_exit_status()
                mkdir_output = self._decode_output(stdout.read(), "创建目录输出")
                mkdir_error = self._decode_output(stderr.read(), "创建目录错误")
                
                logger.info(f"创建目录命令: {mkdir_cmd}")
                logger.info(f"创建目录结果: 退出码={exit_status}, 输出={mkdir_output}, 错误={mkdir_error}")
            
            # 获取本地文件信息
            local_size = os.path.getsize(local_path)
            logger.info(f"本地文件大小: {local_size} 字节")
            
            # 上传文件
            logger.info(f"开始上传文件: {local_path} -> {remote_path}")
            try:
                sftp.put(local_path, remote_path)
                logger.info(f"文件上传完成")
            except Exception as upload_error:
                logger.error(f"文件上传失败: {upload_error}")
                sftp.close()
                return False, f"文件上传失败: {str(upload_error)}"
            
            # 设置文件权限
            if system_type == "windows":
                try:
                    # 给tdhx用户完全控制权限
                    icacls_cmd = f'icacls "{remote_path}" /grant tdhx:F'
                    stdin, stdout, stderr = ssh.exec_command(icacls_cmd)
                    stdout.read()
                    
                    # 也设置目录权限
                    remote_dir = os.path.dirname(remote_path)
                    dir_icacls_cmd = f'icacls "{remote_dir}" /grant tdhx:F'
                    stdin, stdout, stderr = ssh.exec_command(dir_icacls_cmd)
                    stdout.read()
                except Exception as perm_error:
                    pass
            else:
                try:
                    stdin, stdout, stderr = ssh.exec_command(f'chmod +x "{remote_path}"')
                    stdout.channel.recv_exit_status()
                except Exception as chmod_error:
                    pass
            
            # 同时上传industrial_protocol_agent.py和goose_sv_api.py
            # agent_manager.py在main目录下，需要向上两级到项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            remote_dir = os.path.dirname(remote_path)
            
            # 需要上传的文件列表
            files_to_upload = [
                ('industrial_protocol_agent.py', '工控协议Agent'),
                ('goose_sv_api.py', 'GOOSE/SV API'),
                # 新增协议 handler 文件
                ('enip_handler.py', 'ENIP协议处理器'),
                ('dnp3_handler.py', 'DNP3协议处理器'),
                ('dnp3_server_win.py', 'DNP3服务端子进程'),
                ('bacnet_handler.py', 'BACnet协议处理器'),
                ('mms_handler.py', 'MMS/IEC61850协议处理器')
            ]
            
            for filename, description in files_to_upload:
                file_path = os.path.join(project_root, 'packet_agent', filename)
                if os.path.exists(file_path):
                    logger.info(f"[文件上传] 检测到{description}文件，开始上传: {file_path}")
                    remote_file = os.path.join(remote_dir, filename)
                    if system_type == "windows":
                        remote_file = remote_file.replace('/', '\\')
                    else:
                        remote_file = remote_file.replace('\\', '/')
                    
                    try:
                        logger.info(f"[文件上传] 上传{description}文件到: {remote_file}")
                        sftp.put(file_path, remote_file)
                        logger.info(f"[文件上传] {description}文件上传成功: {remote_file}")
                        
                        # 设置文件权限
                        if system_type == "windows":
                            try:
                                icacls_cmd = f'icacls "{remote_file}" /grant tdhx:F'
                                stdin, stdout, stderr = ssh.exec_command(icacls_cmd)
                                logger.info(f"[文件上传] 设置{description}文件权限")
                            except Exception as e:
                                logger.warning(f"[文件上传] 设置{description}文件权限失败: {e}")
                        else:
                            try:
                                ssh.exec_command(f'chmod +x "{remote_file}"')
                                logger.info(f"[文件上传] 设置{description}文件执行权限")
                            except Exception as e:
                                logger.warning(f"[文件上传] 设置{description}文件执行权限失败: {e}")
                    except Exception as e:
                        logger.error(f"[文件上传] {description}文件上传失败: {e}")
                        import traceback
                        logger.error(f"[文件上传] 详细错误: {traceback.format_exc()}")
                else:
                    logger.warning(f"[文件上传] {description}文件不存在: {file_path}")
            
            # 检查并上传GOOSE/SV相关文件
            goose_sv_dir = os.path.join(project_root, 'apps', 'goose_sv')
            if os.path.exists(goose_sv_dir):
                logger.info(f"[文件上传] 检测到GOOSE/SV目录，开始上传相关文件")
                remote_dir = os.path.dirname(remote_path)
                remote_goose_sv_dir = os.path.join(remote_dir, 'goose_sv')
                if system_type == "windows":
                    remote_goose_sv_dir = remote_goose_sv_dir.replace('/', '\\')
                else:
                    remote_goose_sv_dir = remote_goose_sv_dir.replace('\\', '/')
                
                # 需要上传的关键文件
                goose_sv_files = [
                    'goose_sender.py',
                    'sv_sender.py',
                    'ethercat_sender.py',
                    'powerlink_sender.py',
                    'dcp_sender.py',
                    'asn1_encoder.py',
                    'asn1_decoder.py',
                    'network_utils.py'
                ]
                
                try:
                    # 创建远程目录（如果不存在）
                    try:
                        if system_type == "windows":
                            mkdir_cmd = f'if not exist "{remote_goose_sv_dir}" mkdir "{remote_goose_sv_dir}"'
                        else:
                            mkdir_cmd = f'mkdir -p "{remote_goose_sv_dir}"'
                        stdin, stdout, stderr = ssh.exec_command(mkdir_cmd)
                        stdout.read()  # 等待命令完成
                    except Exception as e:
                        logger.warning(f"[文件上传] 创建GOOSE/SV目录失败: {e}")
                    
                    # 上传文件
                    for filename in goose_sv_files:
                        local_file = os.path.join(goose_sv_dir, filename)
                        if os.path.exists(local_file):
                            remote_file = os.path.join(remote_goose_sv_dir, filename)
                            if system_type == "windows":
                                remote_file = remote_file.replace('/', '\\')
                            else:
                                remote_file = remote_file.replace('\\', '/')
                            
                            try:
                                logger.info(f"[文件上传] 上传GOOSE/SV文件: {filename} -> {remote_file}")
                                sftp.put(local_file, remote_file)
                                logger.info(f"[文件上传] GOOSE/SV文件上传成功: {filename}")
                            except Exception as e:
                                logger.warning(f"[文件上传] GOOSE/SV文件上传失败 {filename}: {e}")
                        else:
                            logger.warning(f"[文件上传] GOOSE/SV文件不存在: {local_file}")
                except Exception as e:
                    logger.error(f"[文件上传] GOOSE/SV文件上传过程异常: {e}")
                    import traceback
                    logger.error(f"[文件上传] 详细错误: {traceback.format_exc()}")
            else:
                logger.warning(f"[文件上传] GOOSE/SV目录不存在: {goose_sv_dir}")
            
            sftp.close()
            
            # 验证文件是否上传成功 - 验证packet_agent.py
            if system_type == "windows":
                exist_cmd = f'if exist "{remote_path}" echo FILE_EXISTS'
            else:
                exist_cmd = f'test -f "{remote_path}" && echo FILE_EXISTS || echo FILE_NOT_EXISTS'
            
            stdin, stdout, stderr = ssh.exec_command(exist_cmd)
            exist_result = self._decode_output(stdout.read(), "文件存在性检查")
            
            if "FILE_EXISTS" in exist_result:
                # 验证文件大小
                if system_type == "windows":
                    size_cmd = f'dir "{remote_path}" /-c | findstr /R /C:"[0-9].*packet_agent.py"'
                else:
                    size_cmd = f'stat -c%s "{remote_path}" 2>/dev/null || wc -c < "{remote_path}"'
                
                exit_status, size_result, size_error = self._safe_exec_command(ssh, size_cmd, timeout=5)
                
                try:
                    # 解析文件大小
                    remote_size = None
                    
                    if system_type == "windows":
                        # Windows dir命令输出格式: "2023/11/25  09:33    188,669 packet_agent.py"
                        # 查找包含文件名的行，提取文件大小
                        import re
                        for line in size_result.strip().split('\n'):
                            line = line.strip()
                            if 'packet_agent.py' in line:
                                # 匹配文件大小（可能包含逗号分隔符）
                                size_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)\s+packet_agent\.py', line)
                                if size_match:
                                    size_str = size_match.group(1).replace(',', '')  # 移除逗号
                                    remote_size = int(size_str)
                                    break
                    else:
                        # Linux: 直接是数字
                        size_lines = size_result.strip().split('\n')
                        for line in size_lines:
                            line = line.strip()
                            if line.isdigit():
                                remote_size = int(line)
                                break
                    
                    if remote_size is not None:
                        local_size = os.path.getsize(local_path)
                        
                        if remote_size == local_size:
                            # 修复文件权限
                            perm_success, perm_msg = self.fix_file_permissions(host, port, remote_path, system_type)
                            
                            # 验证industrial_protocol_agent.py和goose_sv_api.py（如果存在）
                            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                            remote_dir = os.path.dirname(remote_path)
                            
                            files_to_verify = [
                                ('industrial_protocol_agent.py', '工控协议Agent'),
                                ('goose_sv_api.py', 'GOOSE/SV API'),
                                # 新增协议 handler 文件
                                ('enip_handler.py', 'ENIP协议处理器'),
                                ('dnp3_handler.py', 'DNP3协议处理器'),
                                ('dnp3_server_win.py', 'DNP3服务端子进程'),
                                ('bacnet_handler.py', 'BACnet协议处理器'),
                                ('mms_handler.py', 'MMS/IEC61850协议处理器')
                            ]
                            
                            for filename, description in files_to_verify:
                                file_path = os.path.join(project_root, 'packet_agent', filename)
                                if os.path.exists(file_path):
                                    remote_file = os.path.join(remote_dir, filename)
                                    if system_type == "windows":
                                        remote_file = remote_file.replace('/', '\\')
                                        check_cmd = f'if exist "{remote_file}" echo FILE_EXISTS'
                                    else:
                                        remote_file = remote_file.replace('\\', '/')
                                        check_cmd = f'test -f "{remote_file}" && echo FILE_EXISTS'
                                    
                                    stdin_ind, stdout_ind, stderr_ind = ssh.exec_command(check_cmd)
                                    verify_result = self._decode_output(stdout_ind.read(), f"{description}文件检查")
                                    
                                    if "FILE_EXISTS" not in verify_result:
                                        logger.warning(f"[WARN] {description}文件未上传: {remote_file}")
                                    else:
                                        logger.info(f"[OK] {description}文件验证成功: {remote_file}")
                            
                            return True, "文件上传成功，大小匹配"
                        elif abs(remote_size - local_size) < 100:  # 允许小差异
                            perm_success, perm_msg = self.fix_file_permissions(host, port, remote_path, system_type)
                            return True, "文件上传成功，大小接近匹配"
                        elif remote_size > 0:
                            perm_success, perm_msg = self.fix_file_permissions(host, port, remote_path, system_type)
                            return True, "文件上传成功，但大小不匹配"
                        else:
                            return False, "文件上传失败，远程文件为空"
                    else:
                        return True, "文件存在但无法验证大小"
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"解析文件大小异常: {size_result}, 错误: {e}")
                    return True, "文件存在但无法验证大小"
            else:
                logger.error(f"❌ 文件上传后验证失败，文件不存在")
                logger.error(f"存在性检查输出: {exist_result}")
                
                # 尝试列出目录内容进行调试
                remote_dir = os.path.dirname(remote_path)
                if system_type == "windows":
                    list_cmd = f'dir "{remote_dir}"'
                else:
                    list_cmd = f'ls -la "{remote_dir}"'
                
                logger.info(f"列出目录内容进行调试: {list_cmd}")
                stdin, stdout, stderr = ssh.exec_command(list_cmd)
                dir_result = self._decode_output(stdout.read(), "目录列表")
                logger.info(f"目录内容: {dir_result}")
                
                return False, f"文件上传后验证失败，文件不存在于 {remote_path}"
                
        except Exception as e:
            logger.exception(f"上传Agent文件失败: {e}")
            return False, str(e)
    
    def detect_system_type(self, host: str, port: int = 22) -> str:
        """检测远程系统类型"""
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return "unknown"
        
        try:
            ssh = self.connections[connection_key]['ssh']
            
            # 尝试Windows命令
            exit_status, result, error = self._safe_exec_command(ssh, 'ver', timeout=3)
            if exit_status == 0 and ('Windows' in result or 'Microsoft' in result):
                return "windows"
            
            # 尝试Linux命令
            exit_status, result, error = self._safe_exec_command(ssh, 'uname -s', timeout=3)
            if exit_status == 0 and result.strip().lower() in ['linux', 'darwin']:
                return result.strip().lower()
            
            return "unknown"
        except Exception as e:
            logger.warning(f"检测系统类型失败: {e}")
            return "unknown"
    
    def start_agent(self, host: str, agent_path: str, port: int = 22, agent_port: int = 8888) -> Tuple[bool, str]:
        """启动远程Agent"""
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False, "未连接到目标主机"
        
        try:
            ssh = self.connections[connection_key]['ssh']
            system_type = self.detect_system_type(host, port)
            
            # 启动前再次验证文件是否存在
            if system_type == "windows":
                verify_cmd = f'if exist "{agent_path}" echo AGENT_FILE_EXISTS'
            else:
                verify_cmd = f'test -f "{agent_path}" && echo AGENT_FILE_EXISTS'
            
            exit_status, verify_result, verify_error = self._safe_exec_command(ssh, verify_cmd, timeout=5)
            
            if "AGENT_FILE_EXISTS" not in verify_result:
                return False, f"Agent文件不存在: {agent_path}"
            
            # 检查文件权限
            if system_type == "windows":
                perm_cmd = f'icacls "{agent_path}"'
                exit_status, perm_result, perm_error = self._safe_exec_command(ssh, perm_cmd, timeout=5)
                
                # 检查tdhx用户是否有完全控制权限
                if "tdhx:(F)" not in perm_result and "tdhx:F" not in perm_result:
                    fix_perm_cmd = f'icacls "{agent_path}" /grant tdhx:F'
                    exit_status, fix_result, fix_error = self._safe_exec_command(ssh, fix_perm_cmd, timeout=5)
            
            # 检查Agent是否已在运行
            is_running, _ = self.check_agent_status(host, port, agent_port)
            if is_running:
                return False, "Agent已在运行中"
            
            # 检查端口是否被占用
            port_occupied, occupying_pid = self.check_port_occupation(host, port, agent_port, system_type)
            if port_occupied:
                # 强制清理所有占用端口的进程
                if system_type == "windows":
                    # 方法1: 直接杀死占用端口的进程
                    if occupying_pid and occupying_pid != "unknown":
                        kill_cmd = f'taskkill /F /PID {occupying_pid} 2>nul'
                        stdin, stdout, stderr = ssh.exec_command(kill_cmd)
                        stdout.read()
                    
                    # 方法2: 批量清理所有占用8888端口的进程
                    batch_kill_cmd = f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr ":{agent_port}" ^| findstr "LISTENING"\') do taskkill /F /PID %a 2>nul'
                    stdin, stdout, stderr = ssh.exec_command(batch_kill_cmd)
                    
                    # 方法3: 清理所有可能的Agent进程
                    cleanup_cmds = [
                        f'taskkill /F /FI "COMMANDLINE eq *packet_agent*" 2>nul',
                        f'taskkill /F /FI "COMMANDLINE eq *--port {agent_port}*" 2>nul'
                    ]
                    for cleanup_cmd in cleanup_cmds:
                        try:
                            stdin, stdout, stderr = ssh.exec_command(cleanup_cmd)
                            stdout.read()
                        except:
                            pass
                
                # 等待端口完全释放
                time.sleep(5)  # 增加等待时间到5秒
                
                # 再次验证端口是否释放
                port_still_occupied, _ = self.check_port_occupation(host, port, agent_port, system_type)
            
            # 使用唯一可行的启动方式
            log_path = agent_path.replace('.py', '_log.txt')  # 统一定义log_path
            
            if system_type == "windows":
                # Windows: 使用pythonw后台启动，并重定向日志到文件
                cmd = f'pythonw "{agent_path}" --port {agent_port} > "{log_path}" 2>&1'
            else:
                # Linux: 使用nohup后台启动
                cmd = f'nohup python3 "{agent_path}" --port {agent_port} > "{log_path}" 2>&1 &'
            
            commands_to_try = [cmd]
            
            start_success = False
            final_error = ""
            
            for i, command in enumerate(commands_to_try):
                try:
                    stdin, stdout, stderr = ssh.exec_command(command)
                    
                    # 对于pythonw命令，使用定时器强制终止
                    if "pythonw" in command:
                        import threading
                        import time
                        
                        # 设置3秒定时器
                        def force_close():
                            time.sleep(3)
                            try:
                                if stdout.channel and not stdout.channel.closed:
                                    stdout.channel.close()
                            except:
                                pass
                        
                        # 启动定时器线程
                        timer_thread = threading.Thread(target=force_close)
                        timer_thread.daemon = True
                        timer_thread.start()
                        
                        try:
                            # 尝试等待命令完成，但会被定时器中断
                            exit_status = stdout.channel.recv_exit_status()
                            start_output = self._decode_output(stdout.read(), f"启动命令{i+1}输出")
                            start_error = self._decode_output(stderr.read(), f"启动命令{i+1}错误")
                            if start_error:
                                final_error = start_error
                        except Exception as e:
                            exit_status = 0  # 假设成功
                            start_output = "pythonw命令强制终止，Agent后台启动"
                            start_error = ""
                    
                    else:
                        # 非pythonw命令，正常执行
                        stdout.channel.settimeout(8)
                        exit_status = stdout.channel.recv_exit_status()
                        start_output = self._decode_output(stdout.read(), f"启动命令{i+1}输出")
                        start_error = self._decode_output(stderr.read(), f"启动命令{i+1}错误")
                        if start_error:
                            final_error = start_error
                        
                        # 检查是否是严重错误（命令不存在等）
                        if any(err in start_error.lower() for err in ["not found", "不是内部或外部命令", "command not found", "无法识别"]):
                            continue
                    
                    # 检查退出状态 - 对于后台启动命令，退出码不一定是0
                    # 对于Windows后台启动，即使退出码不是0也可能启动成功
                    # 需要通过实际检查Agent状态来判断
                    if exit_status == 0:
                        start_success = True
                        break
                    elif system_type == "windows" and ("pythonw" in command or "start" in command):
                        # Windows后台启动命令，即使退出码不是0也继续检查Agent状态
                        start_success = True  # 标记为可能成功，通过后续状态检查确认
                        break
                    else:
                        final_error = f"命令退出码: {exit_status}"
                        continue
                    
                except Exception as e:
                    logger.warning(f"❌ 启动命令 {i+1} 执行异常: {e}")
                    final_error = str(e)
                    continue
            
            if not start_success:
                return False, f"Agent启动失败: 所有启动命令都失败 - {final_error}"
            
            # 优化的Agent启动检查 - 快速检测
            max_retries = 6  # 增加检查次数但缩短间隔
            
            # 使用递增的检查间隔：0.5秒, 1秒, 1.5秒, 2秒, 2.5秒, 3秒 (总共10.5秒)
            retry_intervals = [0.5, 1, 1.5, 2, 2.5, 3]
            
            is_running = False
            status_msg = ""
            logger.info(f'[启动Agent] 开始检查Agent状态，最多检查{max_retries}次')
            for retry in range(max_retries):
                retry_interval = retry_intervals[retry] if retry < len(retry_intervals) else 3
                time.sleep(retry_interval)
                
                # 简化检查：只检查端口监听状态
                is_running, status_msg = self.check_agent_status(host, port, agent_port)
                logger.debug(f'[启动Agent] 第{retry+1}次检查Agent状态: is_running={is_running}, status_msg={status_msg}')
                
                if is_running:
                    logger.info(f'[启动Agent] Agent状态检查成功（第{retry+1}次检查）')
                    break
            
            logger.info(f'[启动Agent] Agent状态检查完成: is_running={is_running}, status_msg={status_msg}')
            
            if is_running:
                # 更新Agent状态
                agent_url = f"http://{host}:{agent_port}"
                self.agent_status[connection_key] = {
                    'running': True,
                    'agent_port': agent_port,
                    'agent_path': agent_path,
                    'agent_url': agent_url,
                    'log_path': log_path,
                    'started_at': datetime.now(),
                    'system_type': system_type
                }
                
                # 启动日志监控
                self.start_log_monitoring(host, port, log_path)
                
                # 启动工控协议Agent（industrial_protocol_agent.py，端口8889）
                # 改为后台异步启动，不阻塞主请求返回
                def start_industrial_agent_async():
                    try:
                        remote_dir = os.path.dirname(agent_path)
                        industrial_agent_script = os.path.join(remote_dir, 'industrial_protocol_agent.py')
                        industrial_agent_log = os.path.join(remote_dir, 'industrial_protocol_agent.log')
                        
                        if system_type == "windows":
                            industrial_agent_script = industrial_agent_script.replace('/', '\\')
                            industrial_agent_log = industrial_agent_log.replace('/', '\\')
                            # 检查文件是否存在
                            check_cmd = f'if exist "{industrial_agent_script}" (echo FILE_EXISTS) else (echo FILE_NOT_EXISTS)'
                            exit_status_check, check_result, check_error = self._safe_exec_command(ssh, check_cmd, timeout=5)
                            
                            if 'FILE_EXISTS' in check_result:
                                # 启动industrial_protocol_agent.py（使用与packet_agent.py相同的启动方式）
                                if system_type == "windows":
                                # Windows: 使用pythonw后台启动，并重定向日志到文件（与packet_agent.py相同）
                                    cmd_industrial = f'pythonw "{industrial_agent_script}" 8889 > "{industrial_agent_log}" 2>&1'
                                else:
                                    # Linux: 使用nohup后台启动
                                    cmd_industrial = f'nohup python3 {industrial_agent_script} 8889 > {industrial_agent_log} 2>&1 &'
                                
                                try:
                                    logger.info(f'[启动Agent] [后台线程] 执行工控协议Agent启动命令: {cmd_industrial}')
                                    stdin_industrial, stdout_industrial, stderr_industrial = ssh.exec_command(cmd_industrial, timeout=10)
                                    
                                    # 对于pythonw命令，使用定时器强制终止（与packet_agent.py相同）
                                    if "pythonw" in cmd_industrial:
                                        import threading
                                        
                                        # 设置3秒定时器
                                        def force_close():
                                            time.sleep(3)
                                            try:
                                                if stdout_industrial.channel and not stdout_industrial.channel.closed:
                                                    stdout_industrial.channel.close()
                                            except:
                                                pass
                                        
                                        # 启动定时器线程
                                        timer_thread = threading.Thread(target=force_close)
                                        timer_thread.daemon = True
                                        timer_thread.start()
                                        
                                        try:
                                            # 尝试等待命令完成，但会被定时器中断
                                            exit_status = stdout_industrial.channel.recv_exit_status()
                                            start_output = self._decode_output(stdout_industrial.read(), "工控协议Agent启动输出")
                                            start_error = self._decode_output(stderr_industrial.read(), "工控协议Agent启动错误")
                                            if start_error:
                                                logger.warning(f'[启动Agent] [后台线程] 工控协议Agent启动错误: {start_error[:200]}')
                                        except Exception as e:
                                            exit_status = 0  # 假设成功
                                            start_output = "pythonw命令强制终止，工控协议Agent后台启动"
                                    else:
                                        # 非pythonw命令，正常执行
                                        stdout_industrial.channel.settimeout(8)
                                        exit_status = stdout_industrial.channel.recv_exit_status()
                                        start_output = self._decode_output(stdout_industrial.read(), "工控协议Agent启动输出")
                                        start_error = self._decode_output(stderr_industrial.read(), "工控协议Agent启动错误")
                                        if start_error:
                                            logger.warning(f'[启动Agent] [后台线程] 工控协议Agent启动错误: {start_error[:200]}')
                                    
                                    time.sleep(5)  # 等待进程启动
                                    # 检查8889端口（使用兼容win7和win10的方法）
                                    port_check_success = False
                                    log_check_success = False
                                    
                                    # 首先尝试读取日志判断是否启动成功（更快，避免端口检查超时）
                                    try:
                                        log_read_cmd = f'powershell -Command "Get-Content \'{industrial_agent_log}\' -Tail 50 -ErrorAction SilentlyContinue"'
                                        exit_status_log, log_content, log_error = self._safe_exec_command(ssh, log_read_cmd, timeout=8)
                                        if log_content:
                                            # 检查日志中是否有启动成功的标志
                                            success_indicators = [
                                                'Running on',
                                                '监听地址',
                                                'Serving Flask app',
                                                'Running on http://',
                                                'Running on all addresses'
                                            ]
                                            if any(indicator in log_content for indicator in success_indicators):
                                                logger.info(f'[启动Agent] [后台线程] 工控协议Agent启动成功（从日志判断）')
                                                log_check_success = True
                                                port_check_success = True  # 日志显示成功，认为启动成功
                                            else:
                                                logger.debug(f'[启动Agent] [后台线程] 日志中未找到启动成功标志: {log_content[:200]}')
                                    except Exception as log_e:
                                        logger.debug(f'[启动Agent] [后台线程] 读取日志失败（可能日志还未生成）: {log_e}')
                                    
                                    # 如果日志检查未成功，再尝试端口检查
                                    if not log_check_success:
                                        try:
                                            # 方法1: 尝试使用Get-NetTCPConnection（Windows 8+）
                                            try:
                                                port_cmd_industrial = 'powershell -Command "(Get-NetTCPConnection -LocalPort 8889 -State Listen -ErrorAction SilentlyContinue).Count"'
                                                exit_status_port, port_count_ind, port_error = self._safe_exec_command(ssh, port_cmd_industrial, timeout=8)
                                                if exit_status_port == 0 and port_count_ind and port_count_ind.strip().isdigit() and int(port_count_ind.strip()) > 0:
                                                    logger.info(f'[启动Agent] [后台线程] 工控协议Agent启动成功，8889端口已监听（Get-NetTCPConnection）')
                                                    port_check_success = True
                                            except Exception as e1:
                                                logger.debug(f'[启动Agent] [后台线程] Get-NetTCPConnection检查失败（可能不支持win7）: {e1}')
                                            
                                            # 方法2: 如果方法1失败，使用netstat（兼容win7和win10）
                                            if not port_check_success:
                                                try:
                                                    port_cmd_netstat = 'netstat -an | findstr ":8889" | findstr "LISTENING"'
                                                    exit_status_netstat, netstat_output, netstat_error = self._safe_exec_command(ssh, port_cmd_netstat, timeout=8)
                                                    if exit_status_netstat == 0 and netstat_output and ':8889' in netstat_output:
                                                        logger.info(f'[启动Agent] [后台线程] 工控协议Agent启动成功，8889端口已监听（netstat）')
                                                        port_check_success = True
                                                except Exception as e2:
                                                    logger.debug(f'[启动Agent] [后台线程] netstat检查失败: {e2}')
                                            
                                            # 如果端口检查也失败，再次尝试读取日志（可能日志刚生成）
                                            if not port_check_success:
                                                try:
                                                    log_read_cmd = f'powershell -Command "Get-Content \'{industrial_agent_log}\' -Tail 50 -ErrorAction SilentlyContinue"'
                                                    exit_status_log2, log_content2, log_error2 = self._safe_exec_command(ssh, log_read_cmd, timeout=8)
                                                    if log_content2:
                                                        success_indicators = [
                                                            'Running on',
                                                            '监听地址',
                                                            'Serving Flask app',
                                                            'Running on http://',
                                                            'Running on all addresses'
                                                        ]
                                                        if any(indicator in log_content2 for indicator in success_indicators):
                                                            logger.info(f'[启动Agent] [后台线程] 工控协议Agent启动成功（从日志判断，端口检查失败）')
                                                            port_check_success = True
                                                        else:
                                                            logger.warning(f'[启动Agent] [后台线程] 工控协议Agent可能未启动，日志: {log_content2[:500]}')
                                                    else:
                                                        logger.warning(f'[启动Agent] [后台线程] 工控协议Agent可能未启动，8889端口未监听，日志文件为空或读取失败')
                                                except Exception as log_e2:
                                                    logger.warning(f'[启动Agent] [后台线程] 工控协议Agent可能未启动，读取日志失败: {log_e2}')
                                        except Exception as port_check_e:
                                            logger.warning(f'[启动Agent] [后台线程] 端口检查过程异常: {port_check_e}')
                                            # 异常情况下，最后尝试读取日志
                                            try:
                                                log_read_cmd = f'powershell -Command "Get-Content \'{industrial_agent_log}\' -Tail 50 -ErrorAction SilentlyContinue"'
                                                exit_status_log3, log_content3, log_error3 = self._safe_exec_command(ssh, log_read_cmd, timeout=8)
                                                if log_content3:
                                                    success_indicators = [
                                                        'Running on',
                                                        '监听地址',
                                                        'Serving Flask app',
                                                        'Running on http://',
                                                        'Running on all addresses'
                                                    ]
                                                    if any(indicator in log_content3 for indicator in success_indicators):
                                                        logger.info(f'[启动Agent] [后台线程] 工控协议Agent启动成功（从日志判断，端口检查异常）')
                                                        port_check_success = True
                                            except:
                                                pass
                                    
                                    # 记录最终结果
                                    if port_check_success:
                                        logger.info(f'[启动Agent] [后台线程] 工控协议Agent启动成功，8889端口已监听或日志显示已启动')
                                    else:
                                        logger.warning(f'[启动Agent] [后台线程] 工控协议Agent启动状态未知，端口检查和日志检查均未确认启动成功')
                                except Exception as e:
                                    logger.warning(f'[启动Agent] [后台线程] 启动工控协议Agent检查过程异常: {e}')
                                    import traceback
                                    logger.warning(f'[启动Agent] [后台线程] 详细错误: {traceback.format_exc()}')
                                    # 即使工控协议Agent检查失败，也不影响主Agent启动成功的返回
                                    logger.info(f'[启动Agent] [后台线程] 工控协议Agent检查异常，但主Agent已启动，继续返回成功')
                        else:
                            # Linux: 检查文件是否存在
                            check_cmd = f'test -f "{industrial_agent_script}" && echo FILE_EXISTS'
                            exit_status_check, check_result, check_error = self._safe_exec_command(ssh, check_cmd, timeout=5)
                            
                            if 'FILE_EXISTS' in check_result:
                                cmd_industrial = f'cd {remote_dir} && nohup python3 {industrial_agent_script} 8889 > {industrial_agent_log} 2>&1 &'
                                stdin_ind, stdout_ind, stderr_ind = ssh.exec_command(cmd_industrial, timeout=10)
                                stdout_ind.read()
                                time.sleep(3)
                                # 检查8889端口
                                port_cmd_industrial = 'netstat -tlnp 2>/dev/null | grep ":8889 " || ss -tlnp 2>/dev/null | grep ":8889 "'
                                exit_status_port, port_check_ind, port_error = self._safe_exec_command(ssh, port_cmd_industrial, timeout=5)
                                if port_check_ind and ('8889' in port_check_ind or ':8889' in port_check_ind):
                                    logger.info(f'[启动Agent] [后台线程] 工控协议Agent启动成功，8889端口已监听')
                    except Exception as async_e:
                        logger.warning(f'[启动Agent] [后台线程] 工控协议Agent后台启动异常: {async_e}')
                        import traceback
                        logger.warning(f'[启动Agent] [后台线程] 详细错误: {traceback.format_exc()}')
                
                # 在后台线程中启动工控协议Agent，不阻塞主请求
                industrial_thread = threading.Thread(target=start_industrial_agent_async, daemon=True)
                industrial_thread.start()
                logger.info(f'[启动Agent] 工控协议Agent启动任务已提交到后台线程，主请求立即返回')
                
                logger.info(f'[启动Agent] ===== 准备返回启动成功 =====')
                logger.info(f'[启动Agent] is_running={is_running}, 主Agent端口={agent_port}, 工控协议Agent端口=8889')
                logger.info(f'[启动Agent] 返回: True, "Agent启动成功"')
                return True, "Agent启动成功"
            else:
                # 启动失败，进行详细诊断
                logger.error("[ERROR] Agent启动失败，开始深度诊断...")
                
                # 诊断1: 检查Python环境
                logger.info("[DIAG1] Python环境检查")
                python_cmds = ["python --version", "python3 --version", "pythonw --version"] if system_type != "windows" else ["python --version", "pythonw --version"]
                python_available = False
                
                for py_cmd in python_cmds:
                    try:
                        stdin, stdout, stderr = ssh.exec_command(py_cmd)
                        py_output = self._decode_output(stdout.read(), f"Python检查-{py_cmd}")
                        py_error = self._decode_output(stderr.read(), f"Python错误-{py_cmd}")
                        if py_output and "Python" in py_output:
                            logger.info(f"[OK] {py_cmd}: {py_output.strip()}")
                            python_available = True
                        else:
                            logger.info(f"[ERROR] {py_cmd}: 不可用 - {py_error}")
                    except Exception as e:
                        logger.info(f"[ERROR] {py_cmd}: 检查异常 - {e}")
                
                # 诊断2: 检查Agent文件
                logger.info("[DIAG2] Agent文件检查")
                logger.info(f"[DEBUG] 检查Agent路径: {agent_path}")
                
                # 首先检查目录是否存在
                agent_dir = os.path.dirname(agent_path)
                if system_type == "windows":
                    dir_check_cmd = f'dir "{agent_dir}"'
                else:
                    dir_check_cmd = f'ls -la "{agent_dir}"'
                
                try:
                    stdin, stdout, stderr = ssh.exec_command(dir_check_cmd)
                    dir_output = self._decode_output(stdout.read(), "目录检查")
                    dir_error = self._decode_output(stderr.read(), "目录检查错误")
                    logger.info(f"[DEBUG] 目录 {agent_dir} 内容: {dir_output}")
                    if dir_error:
                        logger.warning(f"[DEBUG] 目录检查错误: {dir_error}")
                except Exception as e:
                    logger.warning(f"[DEBUG] 目录检查异常: {e}")
                
                if system_type == "windows":
                    file_cmds = [
                        f'dir "{agent_path}"',
                        f'if exist "{agent_path}" echo FILE_EXISTS_CHECK',
                        f'icacls "{agent_path}"',  # 检查文件权限
                        f'python -m py_compile "{agent_path}"'  # 尝试编译检查语法
                    ]
                else:
                    file_cmds = [
                        f'ls -la "{agent_path}"',
                        f'test -f "{agent_path}" && echo FILE_EXISTS_CHECK',
                        f'python3 -m py_compile "{agent_path}"'  # 尝试编译检查语法
                    ]
                
                for cmd in file_cmds:
                    try:
                        stdin, stdout, stderr = ssh.exec_command(cmd)
                        cmd_output = self._decode_output(stdout.read(), f"文件检查-{cmd}")
                        cmd_error = self._decode_output(stderr.read(), f"文件错误-{cmd}")
                        logger.info(f"[INFO] {cmd}: {cmd_output.strip() if cmd_output else '(无输出)'}")
                        if cmd_error:
                            logger.warning(f"[WARN] {cmd} 错误: {cmd_error.strip()}")
                    except Exception as e:
                        logger.warning(f"[ERROR] {cmd}: 执行异常 - {e}")
                
                # 诊断3: 检查Python模块依赖
                logger.info("[DIAG3] Python模块依赖检查")
                if system_type == "windows":
                    module_cmds = [
                        'python -c "import flask; print(\'Flask: OK\')"',
                        'python -c "try: import requests; print(f\'Requests: {requests.__version__}\'); except ImportError: print(\'Requests: 未安装(可选)\')"',
                        'python -c "import psutil; print(f\'Psutil: {psutil.__version__}\')"',
                        'python -c "import argparse; print(\'Argparse: OK\')"',
                        'python -c "import scapy; print(\'Scapy: OK\')"'
                    ]
                else:
                    module_cmds = [
                        'python3 -c "import flask; print(\'Flask: OK\')"',
                        'python3 -c "try: import requests; print(f\'Requests: {requests.__version__}\'); except ImportError: print(\'Requests: 未安装(可选)\')"',
                        'python3 -c "import psutil; print(f\'Psutil: {psutil.__version__}\')"',
                        'python3 -c "import argparse; print(\'Argparse: OK\')"',
                        'python3 -c "import scapy; print(\'Scapy: OK\')"'
                    ]
                
                for cmd in module_cmds:
                    try:
                        stdin, stdout, stderr = ssh.exec_command(cmd)
                        module_output = self._decode_output(stdout.read(), f"模块检查")
                        module_error = self._decode_output(stderr.read(), f"模块检查错误")
                        if module_output:
                            logger.info(f"[OK] {module_output.strip()}")
                        if module_error:
                            logger.error(f"[ERROR] 模块检查失败: {module_error.strip()}")
                    except Exception as e:
                        logger.warning(f"[ERROR] 模块检查异常: {e}")
                
                # 诊断4: 尝试直接运行Agent（前台测试）
                logger.info("[DIAG4] 前台测试运行")
                
                # 先测试基本的Python执行
                if system_type == "windows":
                    basic_test_cmd = f'python --version'
                    test_cmd = f'python "{agent_path}" --test'
                    simple_run_cmd = f'python "{agent_path}" --port {agent_port}'
                else:
                    basic_test_cmd = f'python3 --version'
                    test_cmd = f'timeout 10 python3 "{agent_path}" --test 2>&1 || echo "TIMEOUT_OR_ERROR"'
                    simple_run_cmd = f'timeout 5 python3 "{agent_path}" --port {agent_port} 2>&1'
                
                # 基本Python测试
                try:
                    logger.info(f"[BASIC] 基本Python测试: {basic_test_cmd}")
                    stdin, stdout, stderr = ssh.exec_command(basic_test_cmd)
                    basic_output = self._decode_output(stdout.read(), "Python版本")
                    logger.info(f"[BASIC] Python版本: {basic_output.strip()}")
                except Exception as e:
                    logger.error(f"[BASIC] Python基本测试失败: {e}")
                
                # Agent测试模式
                try:
                    logger.info(f"[TEST] 测试命令: {test_cmd}")
                    stdin, stdout, stderr = ssh.exec_command(test_cmd)
                    stdout.channel.settimeout(10)  # 10秒超时
                    test_output = self._decode_output(stdout.read(), "前台测试输出")
                    test_error = self._decode_output(stderr.read(), "前台测试错误")
                    
                    logger.info(f"[OUTPUT] 前台测试输出: {test_output}")
                    if test_error:
                        logger.error(f"[ERROR] 前台测试错误: {test_error}")
                        
                        # 分析常见错误
                        if "ModuleNotFoundError" in test_error:
                            logger.error("[RESULT] 诊断结果: Python模块缺失")
                        elif "SyntaxError" in test_error:
                            logger.error("[RESULT] 诊断结果: Python语法错误")
                        elif "Permission denied" in test_error:
                            logger.error("[RESULT] 诊断结果: 权限不足")
                        elif "Address already in use" in test_error:
                            logger.error("[RESULT] 诊断结果: 端口被占用")
                        else:
                            logger.error("[RESULT] 诊断结果: 未知运行时错误")
                    else:
                        logger.info("[OK] 前台测试: Agent脚本可以运行")
                        
                        # 跳过简单运行测试，避免启动完整Agent导致端口冲突
                        logger.info(f"[SIMPLE] 跳过简单运行测试，避免端口冲突")
                        
                        # 跳过手动启动测试，避免端口冲突
                        logger.info(f"[SKIP] 跳过手动启动测试，避免端口冲突")
                        
                except Exception as e:
                    logger.error(f"[ERROR] 前台测试异常: {e}")
                
                # 诊断5: 检查端口占用
                logger.info("[DIAG5] 端口占用检查")
                port_occupied, occupying_pid = self.check_port_occupation(host, port, agent_port, system_type)
                
                if port_occupied:
                    logger.warning(f"[WARN] 端口 {agent_port} 被进程 {occupying_pid} 占用")
                    
                    # 获取占用进程的详细信息
                    if system_type == "windows":
                        if occupying_pid != "unknown":
                            process_info_cmd = f'tasklist /FI "PID eq {occupying_pid}"'
                        else:
                            process_info_cmd = f'netstat -ano | findstr ":{agent_port}"'
                    else:
                        if occupying_pid != "unknown":
                            process_info_cmd = f'ps -p {occupying_pid} -o pid,ppid,cmd'
                        else:
                            process_info_cmd = f'lsof -i:{agent_port}'
                    
                    try:
                        stdin, stdout, stderr = ssh.exec_command(process_info_cmd)
                        process_info = self._decode_output(stdout.read(), "进程信息")
                        logger.info(f"[PROCESS] 占用进程信息: {process_info}")
                    except Exception as e:
                        logger.warning(f"[ERROR] 获取进程信息失败: {e}")
                        
                    # 提示用户可以尝试清理
                    logger.info(f"[SUGGEST] 建议: 可以尝试清理占用端口的进程")
                else:
                    logger.info(f"[OK] 端口 {agent_port} 未被占用")
                
                # 诊断6: 检查系统资源
                logger.info("[DIAG6] 系统资源检查")
                if system_type == "windows":
                    resource_cmds = [
                        'echo %CD%',  # 当前目录
                        'whoami',     # 当前用户
                        'wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /format:list'  # 内存
                    ]
                else:
                    resource_cmds = [
                        'pwd',        # 当前目录
                        'whoami',     # 当前用户
                        'free -m',    # 内存
                        'df -h .'     # 磁盘空间
                    ]
                
                for cmd in resource_cmds:
                    try:
                        stdin, stdout, stderr = ssh.exec_command(cmd)
                        res_output = self._decode_output(stdout.read(), f"资源检查-{cmd}")
                        logger.info(f"[INFO] {cmd}: {res_output.strip() if res_output else '(无输出)'}")
                    except Exception as e:
                        logger.warning(f"[ERROR] {cmd}: 检查异常 - {e}")
                
                return False, f"Agent启动失败: {status_msg}. Python可用: {python_available}"
                
        except Exception as e:
            logger.exception(f"启动Agent失败: {e}")
            return False, str(e)
    
    def stop_agent(self, host: str, port: int = 22, agent_port: int = 8888) -> Tuple[bool, str]:
        """停止远程Agent"""
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False, "未连接到目标主机"
        
        try:
            ssh = self.connections[connection_key]['ssh']
            system_type = self.detect_system_type(host, port)
            
            # 检查是否有Agent状态信息
            connection_key = f"{host}:{port}"
            agent_info = self.agent_status.get(connection_key, {})
            agent_url = agent_info.get('agent_url')
            
            if agent_url:
                # 如果有Agent URL，先尝试通过API优雅停止，然后立即执行psexec确保停止
                try:
                    import requests
                    response = requests.post(f"{agent_url}/api/shutdown", timeout=5)
                    time.sleep(1)  # 给API停止一点时间
                except ImportError:
                    pass
                except Exception:
                    pass
            
            # 根据系统类型构建强制停止命令
            if system_type == "windows":
                # Windows: 优先通过端口 PID 杀死进程（最可靠，不依赖 PsExec）
                import os
                import subprocess
                import re as regex_module

                # 从连接信息中获取用户名和密码
                connection = self.connections.get(connection_key, {})
                username = connection.get('username', '')
                password = connection.get('password', '')

                if not username or not password:
                    return False, "无法获取 SSH 凭据，无法停止 Agent"

                # 获取 psexec.exe 路径（可选，用于备选方案）
                django_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                packet_agent_dir = os.path.join(django_root, 'packet_agent')
                psexec_path = os.path.join(packet_agent_dir, 'PsExec.exe')
                psexec_available = os.path.exists(psexec_path)

                is_running_8888 = False
                is_running_8889 = False

                # 步骤 1: 获取 8888 端口的 PID
                pid_8888 = None
                check_cmd_8888 = f'netstat -ano | findstr ":{agent_port}" | findstr "LISTENING"'
                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)
                if output:
                    match = regex_module.search(rf':{agent_port}\s+.*?LISTENING\s+(\d+)', output)
                    if match:
                        pid_8888 = match.group(1)

                # 步骤 2: 获取 8889 端口的 PID
                pid_8889 = None
                check_cmd_8889 = 'netstat -ano | findstr ":8889" | findstr "LISTENING"'
                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)
                if output:
                    match = regex_module.search(r':8889\s+.*?LISTENING\s+(\d+)', output)
                    if match:
                        pid_8889 = match.group(1)

                # 步骤 3: 杀死占用端口的进程（通过 SSH + taskkill）
                if pid_8888:
                    kill_cmd = f'taskkill /F /PID {pid_8888}'
                    self._safe_exec_command(ssh, kill_cmd, timeout=10)
                if pid_8889:
                    kill_cmd = f'taskkill /F /PID {pid_8889}'
                    self._safe_exec_command(ssh, kill_cmd, timeout=10)

                time.sleep(2)

                # 步骤 4: 检查端口是否已释放
                check_cmd_8888 = f'netstat -ano | findstr ":{agent_port}" | findstr "LISTENING"'
                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)
                is_running_8888 = bool(output and 'LISTENING' in output)

                check_cmd_8889 = 'netstat -ano | findstr ":8889" | findstr "LISTENING"'
                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)
                is_running_8889 = bool(output and 'LISTENING' in output)

                # 步骤 5: 如果端口仍被占用，尝试通用清理
                if is_running_8888 or is_running_8889:
                    # 批量清理所有占用端口的进程
                    batch_kill_cmd = f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr ":{agent_port}" ^| findstr "LISTENING" ^| findstr /v "TIME_WAIT"\') do taskkill /F /PID %a 2>nul'
                    self._safe_exec_command(ssh, batch_kill_cmd, timeout=10)

                    batch_kill_cmd_8889 = f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr ":8889" ^| findstr "LISTENING" ^| findstr /v "TIME_WAIT"\') do taskkill /F /PID %a 2>nul'
                    self._safe_exec_command(ssh, batch_kill_cmd_8889, timeout=10)

                    # 杀死所有 python 和 pythonw 进程（不依赖 PsExec）
                    self._safe_exec_command(ssh, 'taskkill /F /IM python.exe 2>nul', timeout=10)
                    self._safe_exec_command(ssh, 'taskkill /F /IM pythonw.exe 2>nul', timeout=10)

                    time.sleep(3)

                    # 再次检查端口状态
                    check_cmd_8888 = f'netstat -ano | findstr ":{agent_port}" | findstr "LISTENING"'
                    exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)
                    is_running_8888 = bool(output and 'LISTENING' in output)

                    check_cmd_8889 = 'netstat -ano | findstr ":8889" | findstr "LISTENING"'
                    exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)
                    is_running_8889 = bool(output and 'LISTENING' in output)

                # 步骤 6: 如果 PsExec 可用，再执行一次确保清理
                if psexec_available:
                    psexec_cmd = [
                        psexec_path,
                        f'\\{host}',
                        '-u', username,
                        '-p', password,
                        '-s',
                        'taskkill',
                        '/F',
                        '/T',
                        '/IM', 'python.exe'
                    ]
                    try:
                        process = subprocess.Popen(
                            psexec_cmd,
                            cwd=packet_agent_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        )
                        process.communicate(timeout=30)
                        time.sleep(2)
                    except Exception:
                        pass

                status_msg = f"8888 端口：{'运行中' if is_running_8888 else '已停止'}, 8889 端口：{'运行中' if is_running_8889 else '已停止'}"

                is_running = is_running_8888 or is_running_8889
            else:
                # Linux: 通过端口查找并杀死进程（使用相同的方法）
                cmd_8888 = f'lsof -ti:{agent_port} | xargs -r kill -9 2>/dev/null'
                exit_status_8888, output_8888, error_8888 = self._safe_exec_command(ssh, cmd_8888, timeout=10)
                
                time.sleep(1)
                
                cmd_8889 = 'lsof -ti:8889 | xargs -r kill -9 2>/dev/null'
                exit_status_8889, output_8889, error_8889 = self._safe_exec_command(ssh, cmd_8889, timeout=10)
                
                time.sleep(2)
                
                # 检查端口状态
                check_cmd_8888 = f'ss -tlnp 2>/dev/null | grep ":{agent_port} " || netstat -tlnp 2>/dev/null | grep ":{agent_port} "'
                exit_status_check_8888, output_check_8888, error_check_8888 = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)
                is_running_8888 = output_check_8888 and (f':{agent_port}' in output_check_8888 or str(agent_port) in output_check_8888)
                
                check_cmd_8889 = 'ss -tlnp 2>/dev/null | grep ":8889 " || netstat -tlnp 2>/dev/null | grep ":8889 "'
                exit_status_check_8889, output_check_8889, error_check_8889 = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)
                is_running_8889 = output_check_8889 and (':8889' in output_check_8889 or '8889' in output_check_8889)
                
                is_running = is_running_8888 or is_running_8889
                status_msg = f"8888端口: {'运行中' if is_running_8888 else '已停止'}, 8889端口: {'运行中' if is_running_8889 else '已停止'}"
            
            # 验证Agent是否停止
            if not is_running:
                # 更新Agent状态
                if connection_key in self.agent_status:
                    self.agent_status[connection_key]['running'] = False
                    self.agent_status[connection_key]['stopped_at'] = datetime.now()
                
                # 停止日志监控
                if connection_key in self.log_threads:
                    self.log_threads[connection_key]['stop'] = True
                
                return True, "Agent停止成功"
            else:
                return False, f"Agent停止失败，进程仍在运行: {status_msg}"
                
        except Exception as e:
            return False, str(e)
    
    def check_agent_status(self, host: str, port: int = 22, agent_port: int = 8888) -> Tuple[bool, str]:
        """快速检查Agent运行状态 - 优化版本"""
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False, "未连接到目标主机"
        
        try:
            ssh = self.connections[connection_key]['ssh']
            system_type = self.detect_system_type(host, port)
            
            # 优先级1: 端口监听检查 (最可靠)
            if system_type == "windows":
                port_cmd = f'netstat -an | findstr ":{agent_port}" | findstr "LISTENING"'
            else:
                port_cmd = f'ss -tuln | grep ":{agent_port}" 2>/dev/null || netstat -an | grep ":{agent_port}" | grep "LISTEN"'
            
            stdin, stdout, stderr = ssh.exec_command(port_cmd)
            stdout.channel.settimeout(1)  # 减少超时时间到1秒
            port_result = self._decode_output(stdout.read(), "端口检查")
            port_error = self._decode_output(stderr.read(), "端口检查错误")
            
            # 检测逻辑：由于已经过滤了LISTENING，只要有输出就表示端口在监听
            port_listening = bool(port_result.strip())
            
            # 如果基本检测失败，尝试更详细的检测
            if not port_listening and port_result:
                # 检查是否包含端口号
                if f":{agent_port}" in port_result or f" {agent_port} " in port_result:
                    port_listening = True
            
            if port_listening:
                return True, "Agent正在运行"
            else:
                return False, "Agent未运行"
                
        except Exception as e:
            logger.exception(f"Agent状态检查异常: {e}")
            return False, f"检查失败: {str(e)}"
    
    def get_agent_status_web(self, host: str, port: int = 22) -> Dict:
        """Web 页面调用的 Agent 状态查询接口"""
        connection_key = f"{host}:{port}"
        # 先检查是否有 SSH 连接
        if connection_key not in self.connections:
            return {'online': False, 'reason': '未连接'}
        # 检查 Agent 端口
        is_running, _ = self.check_agent_status(host, port, 8888)
        return {
            'online': is_running,
            'port': 8888 if is_running else None,
            'last_check': datetime.now().isoformat()
        }

    def get_agent_logs(self, host: str, port: int = 22, lines: int = 20) -> Tuple[bool, str]:
        """获取Agent日志"""
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False, "未连接到目标主机"
        
        if connection_key not in self.agent_status:
            return False, "Agent状态信息不存在"
        
        try:
            ssh = self.connections[connection_key]['ssh']
            agent_info = self.agent_status[connection_key]
            log_path = agent_info.get('log_path', '')
            
            if not log_path:
                return False, "日志文件路径不存在"
            
            system_type = agent_info.get('system_type', 'unknown')
            
            # 根据系统类型构建读取日志命令
            if system_type == "windows":
                # Windows: 先检查文件是否存在，然后读取内容
                cmd = f'if exist "{log_path}" (type "{log_path}") else (echo 日志文件不存在)'
            else:
                # Linux: 使用tail读取最后几行
                cmd = f'if [ -f "{log_path}" ]; then tail -n {lines} "{log_path}"; else echo "日志文件不存在"; fi'
            
            exit_status, logs, log_error = self._safe_exec_command(ssh, cmd, timeout=10)
            
            if log_error:
                logger.warning(f"读取日志错误: {log_error}")
            
            # 处理日志内容
            if logs:
                if "日志文件不存在" in logs:
                    return False, "日志文件不存在"
                
                # 如果是Windows，需要手动截取最后几行
                if system_type == "windows":
                    log_lines = logs.strip().split('\n')
                    if len(log_lines) > lines:
                        logs = '\n'.join(log_lines[-lines:])
                
                return True, logs
            else:
                return False, "日志内容为空"
            
            return True, logs
            
        except Exception as e:
            logger.exception(f"获取Agent日志失败: {e}")
            return False, str(e)
    
    def start_log_monitoring(self, host: str, port: int, log_path: str):
        """启动日志监控线程"""
        connection_key = f"{host}:{port}"
        
        if connection_key in self.log_threads:
            self.log_threads[connection_key]['stop'] = True
            time.sleep(0.5)
        
        def monitor_logs():
            try:
                # 检查连接是否存在且有效
                if connection_key not in self.connections:
                    logger.warning(f"日志监控失败: SSH连接不存在 ({connection_key})")
                    return
                
                ssh = self.connections[connection_key].get('ssh')
                if not ssh:
                    logger.warning(f"日志监控失败: SSH对象不存在 ({connection_key})")
                    return
                
                # 检查SSH连接是否活跃
                try:
                    if not ssh.get_transport() or not ssh.get_transport().is_active():
                        logger.warning(f"日志监控失败: SSH连接已失效 ({connection_key})")
                        return
                except Exception as check_e:
                    logger.warning(f"日志监控失败: SSH连接检查异常 ({connection_key}): {check_e}")
                    return
                
                system_type = self.detect_system_type(host, port)
                
                # 构建实时监控命令
                if system_type == "windows":
                    # Windows系统暂时不支持实时日志监控，使用定期读取
                    logger.info(f"Windows系统暂时不支持实时日志监控")
                    return
                else:
                    cmd = f'tail -f "{log_path}"'
                
                stdin, stdout, stderr = ssh.exec_command(cmd)
                
                while not self.log_threads[connection_key].get('stop', False):
                    try:
                        line = stdout.readline()
                        if line:
                            # 存储最新日志行
                            if 'recent_logs' not in self.log_threads[connection_key]:
                                self.log_threads[connection_key]['recent_logs'] = []
                            
                            logs = self.log_threads[connection_key]['recent_logs']
                            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {line.strip()}")
                            
                            # 保持最近100行日志
                            if len(logs) > 100:
                                logs.pop(0)
                        else:
                            time.sleep(0.1)
                    except:
                        break
                        
            except Exception as e:
                logger.exception(f"日志监控线程异常: {e}")
        
        self.log_threads[connection_key] = {
            'stop': False,
            'thread': threading.Thread(target=monitor_logs, daemon=True),
            'recent_logs': []
        }
        
        self.log_threads[connection_key]['thread'].start()
    
    def get_recent_logs(self, host: str, port: int = 22) -> List[str]:
        """获取最近的实时日志"""
        connection_key = f"{host}:{port}"
        if connection_key in self.log_threads:
            return self.log_threads[connection_key].get('recent_logs', [])
        return []
    
    def get_all_agent_status(self) -> Dict:
        """获取所有Agent状态"""
        status_summary = {}
        
        for connection_key, connection in self.connections.items():
            host = connection['host']
            port = connection['port']
            
            # 检查连接状态
            try:
                connection['ssh'].exec_command('echo "ping"', timeout=5)
                connection_status = "connected"
            except:
                connection_status = "disconnected"
            
            # 获取Agent状态
            agent_info = self.agent_status.get(connection_key, {})
            agent_port = agent_info.get('agent_port', 8888)
            
            if agent_info.get('running', False):
                is_running, status_msg = self.check_agent_status(host, port, agent_port)
                agent_status = "running" if is_running else "stopped"
            else:
                agent_status = "stopped"
            
            status_summary[connection_key] = {
                'host': host,
                'port': port,
                'username': connection['username'],
                'connection_status': connection_status,
                'agent_status': agent_status,
                'agent_port': agent_port,
                'agent_path': agent_info.get('agent_path', ''),
                'started_at': agent_info.get('started_at'),
                'system_type': agent_info.get('system_type', 'unknown')
            }
        
        return status_summary

    def transfer_file_to_device(self, host: str, local_path: str, remote_path: str,
                                username: str = None, password: str = None,
                                port: int = 22) -> Tuple[bool, str]:
        """
        传输文件到测试设备

        Args:
            host: 目标主机 IP
            local_path: 本地文件路径
            remote_path: 远程文件路径
            username: SSH 用户名（可选，默认使用现有连接或环境变量）
            password: SSH 密码（可选）
            port: SSH 端口

        Returns:
            (成功标志，消息)
        """
        from packet_agent.agent.file_transfer import upload_file

        # 如果没有连接，先建立连接
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections or not self.is_connection_valid(connection_key):
            # 尝试使用提供的凭据或从设备模型获取
            if not username or not password:
                from main.models import TestDevice
                device = TestDevice.objects.filter(ip=host).first()
                if device:
                    username = device.user
                    password = device.password
            if not username or not password:
                return False, "未提供 SSH 凭据且无法从数据库获取"

            success, msg = self.connect_to_host(host, username, password, port)
            if not success:
                return False, f"连接失败：{msg}"

        ssh = self.connections[connection_key]['ssh']
        return upload_file(ssh, local_path, remote_path)

    def download_file_from_device(self, host: str, remote_path: str, local_path: str,
                                 port: int = 22) -> Tuple[bool, str]:
        """
        从测试设备下载文件

        Args:
            host: 目标主机 IP
            remote_path: 远程文件路径
            local_path: 本地文件路径
            port: SSH 端口

        Returns:
            (成功标志，消息)
        """
        from packet_agent.agent.file_transfer import download_file

        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False, "未连接到目标设备"

        ssh = self.connections[connection_key]['ssh']
        return download_file(ssh, remote_path, local_path)

    def execute_command_on_device(self, host: str, command: str,
                                 username: str = None, password: str = None,
                                 port: int = 22, timeout: int = 30,
                                 retry: bool = True) -> Tuple[int, str, str]:
        """
        在测试设备上执行命令

        Args:
            host: 目标主机 IP
            command: 命令字符串
            username: SSH 用户名
            password: SSH 密码
            port: SSH 端口
            timeout: 超时时间（秒）
            retry: 是否启用重试

        Returns:
            (退出状态，输出，错误)
        """
        from packet_agent.agent.command_executor import (
            execute_remote_command, execute_command_with_retry
        )

        # 确保有连接
        connection_key = f"{host}:{port}"
        if connection_key not in self.connections or not self.is_connection_valid(connection_key):
            if not username or not password:
                from main.models import TestDevice
                device = TestDevice.objects.filter(ip=host).first()
                if device:
                    username = device.user
                    password = device.password

            if username and password:
                success, msg = self.connect_to_host(host, username, password, port)
                if not success:
                    return -1, "", msg
            else:
                return -1, "", "未提供 SSH 凭据"

        ssh = self.connections[connection_key]['ssh']

        if retry:
            return execute_command_with_retry(ssh, command, timeout=timeout)
        else:
            return execute_remote_command(ssh, command, timeout=timeout)

    def check_device_command_available(self, host: str, command: str,
                                      port: int = 22) -> Tuple[bool, str]:
        """
        检查设备上某个命令是否可用

        Args:
            host: 目标主机 IP
            command: 命令名称
            port: SSH 端口

        Returns:
            (是否可用，路径/错误信息)
        """
        from packet_agent.agent.command_executor import check_command_available

        connection_key = f"{host}:{port}"
        if connection_key not in self.connections:
            return False, "未连接"

        ssh = self.connections[connection_key]['ssh']
        return check_command_available(ssh, command)

    def is_connection_valid(self, connection_key: str) -> bool:
        """
        检查连接是否有效，包括超时检查

        Args:
            connection_key: 连接键

        Returns:
            连接是否有效
        """
        if connection_key not in self.connections:
            return False

        try:
            conn_info = self.connections[connection_key]
            ssh = conn_info.get('ssh')

            if not ssh:
                return False

            # 检查超时（1 小时）
            connected_at = conn_info.get('connected_at')
            if connected_at and (datetime.now() - connected_at).total_seconds() > 3600:
                logger.info(f"连接 {connection_key} 已超过 1 小时，视为失效")
                return False

            transport = ssh.get_transport()
            if not transport or not transport.is_active():
                return False

            # 快速测试连接
            stdin, stdout, stderr = ssh.exec_command('echo test', timeout=2)
            result = stdout.read().decode().strip()
            return result == 'test'
        except Exception:
            return False

    def detect_device_system_type(self, host: str, port: int = 22) -> str:
        """
        检测设备系统类型（Windows/Linux）

        Args:
            host: 目标主机 IP
            port: SSH 端口

        Returns:
            系统类型：'windows', 'linux', 'unknown'
        """
        import os as os_module

        exit_status, output, _ = self.execute_command_on_device(
            host, 'uname -s' if os_module.name != 'nt' else 'ver', port=port, retry=False
        )
        if exit_status == 0:
            if 'Linux' in output:
                return 'linux'
            elif 'Windows' in output or 'Microsoft' in output:
                return 'windows'

        # 回退方案：执行 Windows 特有命令
        exit_status, _, _ = self.execute_command_on_device(
            host, 'echo %OS%', port=port, retry=False, timeout=5
        )
        if exit_status == 0:
            return 'windows'
        return 'unknown'

    def get_device_network_info(self, host: str, port: int = 22) -> dict:
        """
        获取设备网络信息

        Args:
            host: 目标主机 IP
            port: SSH 端口

        Returns:
            包含网络信息的字典
        """
        system_type = self.detect_device_system_type(host, port)

        if system_type == 'windows':
            cmd = 'ipconfig /all'
        else:
            cmd = 'ip addr show'

        exit_status, output, error = self.execute_command_on_device(
            host, cmd, port=port, retry=False, timeout=10
        )

        return {
            'success': exit_status == 0,
            'output': output,
            'error': error,
            'system_type': system_type
        }


# 全局 Agent 管理器实例
agent_manager = RemoteAgentManager()
