"""
SFTP 文件传输模块
支持上传、下载和文件完整性验证
"""

import paramiko
import os
import logging
from typing import Tuple, Optional, Callable

logger = logging.getLogger(__name__)


def upload_file(ssh: paramiko.SSHClient, local_path: str, remote_path: str,
                callback: Optional[Callable[[int, int], None]] = None) -> Tuple[bool, str]:
    """
    上传文件到远程主机

    Args:
        ssh: 已建立的 SSH 连接
        local_path: 本地文件路径
        remote_path: 远程文件路径
        callback: 进度回调函数 callback(transferred, total)

    Returns:
        (成功标志，消息/错误信息)
    """
    try:
        sftp = ssh.open_sftp()

        # 确保远程目录存在
        remote_dir = os.path.dirname(remote_path).replace('\\', '/')
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            # 递归创建目录
            current = ''
            for part in remote_dir.split('/'):
                current += part + '/'
                try:
                    sftp.stat(current)
                except FileNotFoundError:
                    sftp.mkdir(current)

        # 上传文件
        file_size = os.path.getsize(local_path)

        def progress_callback(transferred: int, total: int):
            if callback:
                callback(transferred, total)
            logger.info(f"上传进度：{transferred}/{total} ({transferred*100//total}%)")

        sftp.put(local_path, remote_path, callback=progress_callback)

        # 验证文件完整性
        remote_stat = sftp.stat(remote_path)
        if remote_stat.st_size != file_size:
            sftp.close()
            return False, f"文件大小不匹配：本地{file_size}, 远程{remote_stat.st_size}"

        sftp.close()
        logger.info(f"文件上传成功：{local_path} -> {remote_path}")
        return True, f"上传成功 ({file_size} bytes)"

    except FileNotFoundError as e:
        logger.exception(f"上传文件失败：文件不存在 - {e}")
        return False, f"文件不存在：{str(e)}"
    except Exception as e:
        logger.exception(f"上传文件失败：{e}")
        return False, str(e)


def download_file(ssh: paramiko.SSHClient, remote_path: str, local_path: str,
                  callback: Optional[Callable[[int, int], None]] = None) -> Tuple[bool, str]:
    """
    从远程主机下载文件

    Args:
        ssh: SSH 连接
        remote_path: 远程文件路径
        local_path: 本地文件路径
        callback: 进度回调函数

    Returns:
        (成功标志，消息/错误信息)
    """
    try:
        sftp = ssh.open_sftp()

        # 确保本地目录存在
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # 下载文件
        sftp.get(remote_path, local_path, callback=callback)

        # 验证
        local_size = os.path.getsize(local_path)
        remote_stat = sftp.stat(remote_path)
        if remote_stat.st_size != local_size:
            sftp.close()
            return False, "文件大小不匹配"

        sftp.close()
        logger.info(f"文件下载成功：{remote_path} -> {local_path}")
        return True, "下载成功"

    except FileNotFoundError as e:
        logger.exception(f"下载文件失败：远程文件不存在 - {e}")
        return False, f"远程文件不存在：{str(e)}"
    except Exception as e:
        logger.exception(f"下载文件失败：{e}")
        return False, str(e)


def verify_file_integrity(ssh: paramiko.SSHClient, remote_path: str,
                          expected_size: int, expected_md5: Optional[str] = None) -> Tuple[bool, str]:
    """
    验证远程文件完整性

    Args:
        ssh: SSH 连接
        remote_path: 远程文件路径
        expected_size: 预期文件大小
        expected_md5: 预期 MD5 哈希（可选）

    Returns:
        (验证是否通过，消息/错误信息)
    """
    try:
        sftp = ssh.open_sftp()
        stat = sftp.stat(remote_path)

        if stat.st_size != expected_size:
            sftp.close()
            return False, f"大小不匹配：{stat.st_size} != {expected_size}"

        if expected_md5:
            # 计算远程 MD5（需要远程主机支持 md5sum 或 certutil）
            stdin, stdout, stderr = ssh.exec_command(f'md5sum "{remote_path}"')
            md5_output = stdout.read().decode().strip()
            remote_md5 = md5_output.split()[0] if md5_output else None

            if remote_md5 != expected_md5:
                sftp.close()
                return False, f"MD5 不匹配：{remote_md5} != {expected_md5}"

        sftp.close()
        logger.info(f"文件完整性验证通过：{remote_path}")
        return True, "完整性验证通过"

    except Exception as e:
        logger.exception(f"验证文件完整性失败：{e}")
        return False, f"验证失败：{e}"
