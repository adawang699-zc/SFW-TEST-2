"""
SSH 命令执行模块
支持远程命令执行、重试机制、批量执行和命令可用性检查
"""

import logging
import time
from typing import Tuple, List, Optional
import paramiko

logger = logging.getLogger(__name__)


class CommandExecutionError(Exception):
    """命令执行异常"""
    pass


def execute_remote_command(ssh: paramiko.SSHClient, command: str,
                           timeout: int = 30,
                           check_exit_status: bool = True) -> Tuple[int, str, str]:
    """
    执行远程命令

    Args:
        ssh: SSH 连接
        command: 命令字符串
        timeout: 超时时间（秒）
        check_exit_status: 是否检查退出状态

    Returns:
        (退出状态，标准输出，标准错误)
    """
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)

        # 设置通道超时
        if stdout.channel:
            stdout.channel.settimeout(timeout)
        if stderr.channel:
            stderr.channel.settimeout(timeout)

        # 获取退出状态
        exit_status = stdout.channel.recv_exit_status() if check_exit_status else 0

        # 读取输出
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')

        return exit_status, output, error

    except Exception as e:
        logger.exception(f"命令执行失败：{command}")
        return -1, "", str(e)


def execute_command_with_retry(ssh: paramiko.SSHClient, command: str,
                               max_retries: int = 3,
                               retry_delay: int = 2,
                               timeout: int = 30) -> Tuple[int, str, str]:
    """
    执行命令带重试逻辑

    Args:
        ssh: SSH 连接
        command: 命令
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
        timeout: 超时时间

    Returns:
        (退出状态，输出，错误)
    """
    last_exit, last_out, last_err = -1, "", ""

    for attempt in range(max_retries):
        exit_status, output, error = execute_remote_command(ssh, command, timeout)

        # 如果成功或不是连接错误，直接返回
        if exit_status == 0 or "SSH session not active" not in error:
            return exit_status, output, error

        # 记录重试日志
        logger.warning(f"命令执行失败，准备重试 ({attempt+1}/{max_retries}): {error}")
        last_exit, last_out, last_err = exit_status, output, error

        # 等待重试
        time.sleep(retry_delay)

    return last_exit, last_out, last_err


def execute_multi_command(ssh: paramiko.SSHClient, commands: List[str],
                         stop_on_error: bool = False) -> List[dict]:
    """
    执行多个命令

    Args:
        ssh: SSH 连接
        commands: 命令列表
        stop_on_error: 遇到错误是否停止

    Returns:
        每个命令的执行结果列表
    """
    results = []

    for cmd in commands:
        exit_status, output, error = execute_remote_command(ssh, cmd)

        results.append({
            'command': cmd,
            'exit_status': exit_status,
            'output': output,
            'error': error,
            'success': exit_status == 0
        })

        if stop_on_error and exit_status != 0:
            break

    return results


def check_command_available(ssh: paramiko.SSHClient, command: str) -> Tuple[bool, str]:
    """
    检查命令是否可用

    Args:
        ssh: SSH 连接
        command: 命令名称

    Returns:
        (是否可用，路径/错误信息)
    """
    exit_status, output, error = execute_remote_command(ssh, f'which {command}')

    if exit_status == 0 and output.strip():
        return True, output.strip()

    return False, f"命令 {command} 不可用"
