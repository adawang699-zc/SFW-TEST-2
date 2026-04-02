"""
设备管理工具模块
提供SSH连接、命令执行等功能
"""
import paramiko
import time
import os
import logging
import socket

logger = logging.getLogger(__name__)

# 默认SSH凭据


DEFAULT_USER = os.environ.get('DEVICE_DEFAULT_USER', 'admin')
DEFAULT_PASSWORD = os.environ.get('DEVICE_DEFAULT_PASSWORD', '')

def execute(cmd, host, user=DEFAULT_USER, password=DEFAULT_PASSWORD, port=22):
    """
    执行SSH命令
    
    Args:
        cmd: 要执行的命令
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        port: SSH端口
    
    Returns:
        命令输出或False（失败时）
    """
    try:
        myssh = paramiko.SSHClient()
        myssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        myssh.connect(host, port, user, password, timeout=10)
        
        # 根据命令类型设置超时时间
        if 'mpstat' in cmd:
            cmd_timeout = 20  # mpstat需要等待采样
        else:
            cmd_timeout = 15  # 其他命令
        
        # 使用交互式shell执行命令，避免命令被中断
        chan = myssh.invoke_shell()
        chan.settimeout(cmd_timeout)
        
        # 发送命令
        chan.send(cmd + '\n')
        time.sleep(0.5)
        
        # 读取输出
        output = ''
        max_wait = cmd_timeout
        start_time = time.time()
        last_data_time = time.time()
        no_data_count = 0
        
        while time.time() - start_time < max_wait:
            if chan.recv_ready():
                data = chan.recv(4096).decode('utf-8', errors='ignore')
                output += data
                last_data_time = time.time()
                no_data_count = 0
                # 如果输出包含命令提示符，说明命令执行完成
                if output.count('\n') > 2:
                    # 检查是否出现提示符（说明命令执行完成）
                    if any(prompt in output[-20:] for prompt in ['# ', '$ ', '> ', '\n#', '\n$', '\n>']):
                        # 再等待一小段时间确保输出完整
                        time.sleep(0.5)
                        if chan.recv_ready():
                            output += chan.recv(4096).decode('utf-8', errors='ignore')
                        break
            else:
                no_data_count += 1
                # 如果连续5次（0.5秒）没有新数据，且已经有输出，可能命令已经完成
                if no_data_count > 5 and output and output.count('\n') > 1:
                    time.sleep(0.3)
                    if chan.recv_ready():
                        output += chan.recv(4096).decode('utf-8', errors='ignore')
                    break
            time.sleep(0.1)
        
        myssh.close()
        
        # 检查是否有命令不完整错误
        if '% Command incomplete.' in output:
            logger.warning(f'命令执行被中断: {cmd}')
            return False
        
        # 清理输出：移除命令本身和提示符
        lines = output.split('\n')
        cleaned_lines = []
        skip_command = True
        for line in lines:
            # 跳过命令回显行
            if skip_command and cmd.strip() in line:
                skip_command = False
                continue
            # 跳过提示符行和空行
            line_stripped = line.strip()
            if line_stripped and not any(line_stripped.endswith(p) for p in ['#', '$', '>', '%']):
                # 跳过包含"Command incomplete"的行
                if 'Command incomplete' not in line_stripped:
                    cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        
        if result:
            return result
        
        logger.warning(f'命令无有效输出: {cmd}, 原始输出前200字符: {output[:200]}')
        return False
    except paramiko.AuthenticationException as err:
        logger.error(f'SSH认证失败: {host}:{port}@{user}, 错误: {err}')
        return False
    except paramiko.SSHException as err:
        logger.error(f'SSH异常: {host}:{port}, 错误: {err}')
        return False
    except socket.timeout:
        logger.error(f'SSH连接超时: {host}:{port}')
        return False
    except Exception as e:
        logger.error(f'执行命令失败: {host}:{port}, 命令: {cmd}, 错误: {e}', exc_info=True)
        return False


def execute_in_vtysh(cmds, host, user=DEFAULT_USER, password=DEFAULT_PASSWORD, log=False):
    """
    在vtysh中执行命令
    
    Args:
        cmds: 命令（字符串或列表）
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        log: 是否使用交互式shell
    
    Returns:
        命令输出或False（失败时）
    """
    if log is False:
        cmds = isinstance(cmds, (list, tuple)) and '\n'.join(cmds) or cmds
        return execute(cmds, host, user, password)
    else:
        comands = isinstance(cmds, (list, tuple)) and cmds or [cmds]
        comands = ['%s\n' % comand for comand in comands]
        
        try:
            myssh = paramiko.SSHClient()
            myssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            myssh.load_system_host_keys()
            myssh.connect(host, 22, user, password, timeout=300)
        except paramiko.SSHException as err:
            logger.error(f'无法连接到 "{host}": {err}')
            return False

        out = ''
        chan = myssh.invoke_shell()
        chan.settimeout(300)
        
        for comand in comands:
            chan.send(comand)
            time.sleep(0.5)
            out += chan.recv(65535).decode('utf-8', errors='ignore')
            
            # 处理分页提示
            while '--More--' in out:
                chan.send(' ')
                time.sleep(0.5)
                out = '\n'.join(out.split('\n')[:-1])
                out += chan.recv(65535).decode('utf-8', errors='ignore')
            
            # 等待命令完成
            while not (out.endswith('# ') or out.endswith(': ') or out.endswith('$ ') or 
                      out.endswith('restart.\r\n') or out.endswith('OK.\r\n')):
                time.sleep(0.5)
                out += chan.recv(65535).decode('utf-8', errors='ignore')

        myssh.close()
        return out


def execute_in_backend(cmds, host, user=DEFAULT_USER, password=DEFAULT_PASSWORD, 
                       backend_password=None, device_type=None):
    """
    进入后台执行命令（输入enter，然后输入密码获取root权限）
    
    Args:
        cmds: 命令（字符串或列表）
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        backend_password: 后台root密码（如果为None，根据device_type自动选择）
        device_type: 设备类型（'ic_firewall'为防火墙，其他为其他设备）
    
    Returns:
        命令输出或False（失败时）
    """
    # 如果是单个命令，转换为列表
    if isinstance(cmds, str):
        cmd = cmds
    else:
        # 如果是列表，合并为单个命令
        cmd = ' && '.join(cmds) if isinstance(cmds, (list, tuple)) else str(cmds)
    
    # 根据设备类型自动选择后台密码
    if backend_password is None:
        if device_type == 'ic_firewall':
            backend_password = DEFAULT_BACKEND_PASSWORD
        else:
            backend_password = DEFAULT_BACKEND_PASSWORD_OTHER
    
    try:
        myssh = paramiko.SSHClient()
        myssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        myssh.connect(host, 22, user, password, timeout=10)
        
        chan = myssh.invoke_shell()
        chan.settimeout(10)  # 减少超时时间，加快响应
        
        # 清空初始输出
        time.sleep(0.1)  # 减少等待时间
        if chan.recv_ready():
            chan.recv(4096)
        
        # 输入enter进入后台
        chan.send('enter\n')
        time.sleep(0.3)
        if chan.recv_ready():
            chan.recv(4096)
        
        # 输入密码获取root权限
        chan.send(backend_password + '\n')
        time.sleep(0.3)
        if chan.recv_ready():
            chan.recv(4096)
        
        # 发送要执行的命令
        chan.send(cmd + '\n')
        time.sleep(0.3)
        
        # 读取输出（优化：减少等待时间）
        output = ''
        max_wait = 10  # 减少最大等待时间
        start_time = time.time()
        last_data_time = time.time()
        no_data_count = 0
        
        while time.time() - start_time < max_wait:
            if chan.recv_ready():
                data = chan.recv(4096).decode('utf-8', errors='ignore')
                output += data
                last_data_time = time.time()
                no_data_count = 0
                # 如果输出包含命令提示符，说明命令执行完成
                if output.count('\n') > 1:
                    # 检查是否出现提示符（说明命令执行完成）
                    if any(prompt in output[-15:] for prompt in ['# ', '$ ', '> ', '\n#', '\n$', '\n>']):
                        # 再等待一小段时间确保输出完整
                        time.sleep(0.2)
                        if chan.recv_ready():
                            output += chan.recv(4096).decode('utf-8', errors='ignore')
                        break
            else:
                no_data_count += 1
                # 如果连续3次（0.3秒）没有新数据，且已经有输出，可能命令已经完成
                if no_data_count > 3 and output and output.count('\n') > 0:
                    time.sleep(0.2)
                    if chan.recv_ready():
                        output += chan.recv(4096).decode('utf-8', errors='ignore')
                    break
            time.sleep(0.1)
        
        myssh.close()
        
        # 检查是否有命令不完整错误
        if '% Command incomplete.' in output:
            logger.warning(f'命令执行被中断: {cmd}')
            return False
        
        # 清理输出：移除命令本身和提示符
        lines = output.split('\n')
        cleaned_lines = []
        skip_until_command = True
        
        for line in lines:
            line_stripped = line.strip()
            
            # 跳过enter和密码输入的回显
            if skip_until_command:
                if 'enter' in line_stripped.lower() or 'Password:' in line_stripped or backend_password in line_stripped:
                    continue
                # 如果遇到命令本身，说明开始执行了
                if cmd.strip() in line or (len(cmd) > 20 and cmd[:20] in line):
                    skip_until_command = False
                    continue
            
            # 保留所有数据行，只跳过纯提示符行
            if line_stripped:
                # 跳过纯提示符行（只有#、$、>的行）
                if line_stripped in ['#', '$', '>'] or (len(line_stripped) == 1 and line_stripped in ['#', '$', '>']):
                    continue
                # 跳过包含"Command incomplete"的行
                if 'Command incomplete' in line_stripped:
                    continue
                # 保留所有其他行（包括数据行，即使它们以#、$、>结尾，因为可能是数据的一部分）
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        
        if result:
            logger.debug(f'命令输出清理后前200字符: {result[:200]}')
            return result
        
        logger.warning(f'命令无有效输出: {cmd}, 原始输出前500字符: {output[:500]}')
        return False
        
    except paramiko.AuthenticationException as err:
        logger.error(f'SSH认证失败: {host}:{22}@{user}, 错误: {err}')
        return False
    except paramiko.SSHException as err:
        logger.error(f'SSH异常: {host}:{22}, 错误: {err}')
        return False
    except socket.timeout:
        logger.error(f'SSH连接超时: {host}:{22}')
        return False
    except Exception as e:
        logger.error(f'执行命令失败: {host}:{22}, 命令: {cmd}, 错误: {e}', exc_info=True)
        return False


def get_cpu_info(host, user=DEFAULT_USER, password=DEFAULT_PASSWORD, device_type=None):
    """
    获取CPU使用率
    
    Args:
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        device_type: 设备类型（用于选择正确的后台密码）
    
    Returns:
        CPU使用率百分比
    """
    try:
        # 使用top命令获取CPU使用率（需要在root权限下执行）
        # cmd = "top -bn1 | grep \"Cpu(s)\" | sed \"s/.*, *\\([0-9.]*\\)%* id.*/\\1/\" | awk '{print 100 - $1}'"
        cmd = "top -n1 | grep \"Cpu(s)\" |awk '{print 100 - $8}'"
        result = execute_in_backend(cmd, host, user, password, device_type=device_type)
        if result and result != False:
            # 清理输出：移除所有非数字字符，只保留最后一行数字
            lines = result.strip().split('\n')
            # 查找最后一行包含数字的行
            cpu_value = None
            for line in reversed(lines):
                line = line.strip()
                # 移除所有非数字和点的字符
                cleaned = ''.join(c if c.isdigit() or c == '.' else '' for c in line)
                if cleaned:
                    try:
                        cpu_value = float(cleaned)
                        break
                    except ValueError:
                        continue
            
            if cpu_value is not None:
                if 0 <= cpu_value <= 100:
                    logger.info(f'获取CPU使用率: {cpu_value:.2f}%')
                    return round(cpu_value, 2)
                else:
                    logger.warning(f'CPU使用率超出范围: {cpu_value}')
            else:
                logger.warning(f'未找到有效的CPU使用率数值，输出: {result[:200]}')
        else:
            logger.warning(f'top命令执行失败或返回空')
    except Exception as e:
        logger.error(f'获取CPU信息失败: {e}')
    
    logger.warning(f'CPU获取失败，返回0.0')
    return 0.0


def get_memory_info(host, user=DEFAULT_USER, password=DEFAULT_PASSWORD, device_type=None):
    """
    获取内存使用信息
    
    Returns:
        dict: {'total': 总内存(MB), 'used': 已用内存(MB), 'free': 空闲内存(MB), 'usage': 使用率(%)}
    """
    try:
        # 使用free命令获取内存信息（需要在root权限下执行）
        # 获取Mem行的total和-/+ buffers/cache行的used和free
        cmd = "free -m"
        result = execute_in_backend(cmd, host, user, password, device_type=device_type)
        if result and result != False:
            lines = result.strip().split('\n')
            total = 0
            used = 0
            free = 0
            
            logger.debug(f'free命令输出行数: {len(lines)}')
            logger.debug(f'free命令输出内容:\n{result}')
            
            mem_used = 0
            buffers_cache_used = 0
            buffers_cache_free = 0
            
            # 解析Mem行获取total和used
            for line in lines:
                if 'Mem:' in line and not line.strip().startswith('Swap:'):
                    parts = line.split()
                    logger.debug(f'找到Mem行: {line}, parts: {parts}')
                    if len(parts) >= 3:
                        try:
                            # 找到Mem:后面的数字
                            for i, part in enumerate(parts):
                                if part == 'Mem:':
                                    if i + 1 < len(parts):
                                        total = int(parts[i + 1])  # total列
                                    if i + 2 < len(parts):
                                        mem_used = int(parts[i + 2])  # used列
                                    logger.debug(f'解析total: {total}, mem_used: {mem_used}')
                                    break
                            if total > 0:
                                break
                        except (ValueError, IndexError) as e:
                            logger.debug(f'解析Mem行失败: {e}')
                            pass
            
            # 解析-/+ buffers/cache行获取used值
            for line in lines:
                if 'buffers/cache' in line:
                    parts = line.split()
                    logger.debug(f'找到buffers/cache行: {line}, parts: {parts}')
                    if len(parts) >= 3:
                        try:
                            # 找到buffers/cache:后面的数字
                            for i, part in enumerate(parts):
                                if 'buffers/cache' in part:
                                    if i + 1 < len(parts):
                                        buffers_cache_used = int(parts[i + 1])  # used列
                                    if i + 2 < len(parts):
                                        buffers_cache_free = int(parts[i + 2])  # free列
                                    logger.debug(f'解析buffers_cache_used: {buffers_cache_used}, buffers_cache_free: {buffers_cache_free}')
                                    break
                            if buffers_cache_used > 0 or buffers_cache_free > 0:
                                break
                        except (ValueError, IndexError) as e:
                            logger.debug(f'解析buffers/cache行失败: {e}')
                            pass
            
            if total > 0 and mem_used > 0 and buffers_cache_used >= 0:
                # 真实used = Mem行的used - buffers/cache行的used
                used = mem_used - buffers_cache_used
                # free使用buffers/cache行的free
                free = buffers_cache_free
                
                # 实际使用率 = used / total
                usage = (used / total * 100) if total > 0 else 0
                
                logger.info(f'内存: total={total}MB, mem_used={mem_used}MB, buffers_cache_used={buffers_cache_used}MB, used={used}MB, free={free}MB, usage={usage:.2f}%')
                return {
                    'total': total,
                    'used': used,
                    'free': free,
                    'usage': round(usage, 2)
                }
            else:
                logger.warning(f'内存数据不完整: total={total}, mem_used={mem_used}, buffers_cache_used={buffers_cache_used}, 输出: {result[:300]}')
        else:
            logger.warning(f'free命令执行失败或返回空')
    except Exception as e:
        logger.error(f'获取内存信息失败: {e}')
    
    logger.warning(f'内存获取失败，返回0')
    return {'total': 0, 'used': 0, 'free': 0, 'usage': 0.0}


# 存储上次网络统计信息（用于计算速率）
_network_cache = {}

def get_network_info(host, user=DEFAULT_USER, password=DEFAULT_PASSWORD, device_type=None):
    """
    获取网络流量信息（包含速率计算）
    
    Args:
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        device_type: 设备类型（用于选择正确的后台密码）
    
    Returns:
        dict: {'rx_bytes': 接收字节数, 'tx_bytes': 发送字节数, 'rx_rate': 接收速率(bps), 'tx_rate': 发送速率(bps)}
    """
    try:
        # 获取网络接口统计信息
        # /proc/net/dev格式: interface | rx_bytes rx_packets ... tx_bytes tx_packets ...
        cmd = "cat /proc/net/dev | grep -E 'eth|ens|enp|agl0|ext' | awk '{rx+=$2; tx+=$10} END {print rx, tx}'"
        result = execute_in_backend(cmd, host, user, password, device_type=device_type)
        if result and result != False:
            # 清理输出：移除所有非数字字符，只保留数字和空格
            lines = result.strip().split('\n')
            # 查找最后一行包含数字的行（通常是命令输出）
            rx_bytes = None
            tx_bytes = None
            
            for line in reversed(lines):
                line = line.strip()
                # 清理行，只保留数字和空格
                cleaned = ''.join(c if c.isdigit() or c.isspace() else ' ' for c in line)
                parts = cleaned.strip().split()
                if len(parts) >= 2:
                    try:
                        rx_bytes = int(parts[0])
                        tx_bytes = int(parts[1])
                        logger.debug(f'网络命令输出: {result}, 解析到: rx={rx_bytes}, tx={tx_bytes}')
                        break
                    except (ValueError, IndexError):
                        continue
            
            if rx_bytes is not None and tx_bytes is not None:
                try:
                    
                    # 计算速率（需要与上次采样对比）
                    cache_key = f"{host}_{user}"
                    rx_rate = 0
                    tx_rate = 0
                    
                    if cache_key in _network_cache:
                        last_data = _network_cache[cache_key]
                        time_diff = time.time() - last_data['timestamp']
                        if time_diff > 0:
                            rx_rate = int((rx_bytes - last_data['rx_bytes']) / time_diff)
                            tx_rate = int((tx_bytes - last_data['tx_bytes']) / time_diff)
                    
                    # 更新缓存
                    _network_cache[cache_key] = {
                        'rx_bytes': rx_bytes,
                        'tx_bytes': tx_bytes,
                        'timestamp': time.time()
                    }
                    logger.info(f'网络: rx={rx_bytes}, tx={tx_bytes}, rx_rate={rx_rate}/s, tx_rate={tx_rate}/s')
                    return {
                        'rx_bytes': rx_bytes,
                        'tx_bytes': tx_bytes,
                        'rx_rate': max(0, rx_rate),  # 确保不为负
                        'tx_rate': max(0, tx_rate)
                    }
                except (ValueError, IndexError) as e:
                    logger.warning(f'解析网络信息失败: {result}, 错误: {e}')
            else:
                logger.warning(f'网络命令输出解析失败，未找到有效数字，输出: {result[:300]}')
        else:
            logger.warning(f'网络命令执行失败或返回空')
        
        # 备用方法：直接读取/proc/net/dev并手动解析（需要在root权限下执行）
        cmd = "cat /proc/net/dev"
        result = execute_in_backend(cmd, host, user, password, device_type=device_type)
        if result:
            rx_total = 0
            tx_total = 0
            for line in result.split('\n'):
                if ':' in line and any(iface in line for iface in ['eth', 'ens', 'enp', 'agl0', 'ext']):
                    parts = line.split()
                    if len(parts) >= 10:
                        try:
                            # $2是rx_bytes, $10是tx_bytes
                            rx_total += int(parts[1])
                            tx_total += int(parts[9])
                        except (ValueError, IndexError):
                            continue
            
            if rx_total > 0 or tx_total > 0:
                cache_key = f"{host}_{user}"
                rx_rate = 0
                tx_rate = 0
                
                if cache_key in _network_cache:
                    last_data = _network_cache[cache_key]
                    time_diff = time.time() - last_data['timestamp']
                    if time_diff > 0:
                        rx_rate = int((rx_total - last_data['rx_bytes']) / time_diff)
                        tx_rate = int((tx_total - last_data['tx_bytes']) / time_diff)
                
                _network_cache[cache_key] = {
                    'rx_bytes': rx_total,
                    'tx_bytes': tx_total,
                    'timestamp': time.time()
                }
                
                logger.info(f'网络(备用): rx={rx_total}, tx={tx_total}, rx_rate={rx_rate}/s, tx_rate={tx_rate}/s')
                return {
                    'rx_bytes': rx_total,
                    'tx_bytes': tx_total,
                    'rx_rate': max(0, rx_rate),
                    'tx_rate': max(0, tx_rate)
                }
    except Exception as e:
        logger.error(f'获取网络信息失败: {e}')
    
    logger.warning(f'网络获取失败，返回0')
    return {'rx_bytes': 0, 'tx_bytes': 0, 'rx_rate': 0, 'tx_rate': 0}


def get_coredump_files(host, user=DEFAULT_USER, password=DEFAULT_PASSWORD, coredump_dir='/data/coredump', device_type=None):
    """
    获取coredump文件列表（在root权限下执行）
    
    Args:
        host: 主机地址
        user: SSH用户名
        password: SSH密码
        coredump_dir: coredump目录路径
        device_type: 设备类型（用于选择正确的后台密码）
    
    Returns:
        list: [{'name': 文件名, 'size': 文件大小(字节), 'mtime': 修改时间}]
    """
    try:
        cmd = f"ls -lh {coredump_dir} 2>/dev/null | tail -n +2 | awk '{{print $9, $5, $6, $7, $8}}'"
        result = execute_in_backend(cmd, host, user, password, device_type=device_type)
        files = []
        
        if result:
            for line in result.strip().split('\n'):
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 1:
                        filename = parts[0]
                        
                        # 筛选无效文件：排除包含特殊字符、提示符、命令输出等
                        if not filename or \
                           filename.startswith('[') or \
                           filename.startswith('$') or \
                           filename.startswith('#') or \
                           filename.startswith('{') or \
                           filename.startswith('}') or \
                           'root@' in filename or \
                           '~]' in filename or \
                           filename in ['9,', '$5,', '$6,', '$7,', '$8}'] or \
                           len(filename) < 2:  # 文件名太短可能是无效的
                            continue
                        
                        size_str = parts[1] if len(parts) > 1 else '0'
                        # 解析文件大小
                        size = parse_size(size_str)
                        mtime = ' '.join(parts[2:]) if len(parts) > 2 else ''
                        
                        # 筛选无效的时间格式（包含提示符等）
                        if mtime and ('root@' in mtime or '~]' in mtime or mtime.startswith('[')):
                            continue
                        
                        files.append({
                            'name': filename,
                            'size': size,
                            'size_str': size_str,
                            'mtime': mtime
                        })
        
        return files
    except Exception as e:
        logger.error(f'获取coredump文件列表失败: {e}')
    
    return []


def parse_size(size_str):
    """
    解析文件大小字符串（如 '1.5M', '500K'）为字节数
    
    Args:
        size_str: 大小字符串
    
    Returns:
        字节数
    """
    try:
        size_str = size_str.upper().strip()
        if size_str.endswith('K'):
            return int(float(size_str[:-1]) * 1024)
        elif size_str.endswith('M'):
            return int(float(size_str[:-1]) * 1024 * 1024)
        elif size_str.endswith('G'):
            return int(float(size_str[:-1]) * 1024 * 1024 * 1024)
        else:
            return int(size_str)
    except:
        return 0


def test_connection(host, user=DEFAULT_USER, password=DEFAULT_PASSWORD, port=22):
    """
    测试SSH连接
    
    Returns:
        bool: 连接是否成功
    """
    try:
        myssh = paramiko.SSHClient()
        myssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        myssh.connect(host, port, user, password, timeout=10)
        myssh.close()
        return True
    except Exception as e:
        logger.error(f'连接测试失败: {e}')
        return False

