#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 文件自动同步模块

监控本地 packet_agent/ 目录文件变化，自动上传到远程主机并重启 Agent 服务。
"""

import os
import sys
import time
import hashlib
import threading
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# 全局同步状态
sync_state = {
    'running': False,
    'enabled': True,  # 是否启用自动同步
    'watch_dir': None,
    'remote_hosts': [],
    'remote_user': 'tdhx',
    'remote_password': 'tdhx@2017',
    'remote_port': 22,
    'cooldown': 3,  # 文件修改后等待 3 秒再上传（防抖）
    'lock': threading.Lock(),
    'pending_files': {},  # {file_path: last_modified_time}
    'uploading': False,  # 是否正在上传
}

# 远程路径配置 - 只同步必要的文件
REMOTE_PATHS = {
    # 核心 Agent 文件
    'packet_agent.py': 'C:/packet_agent/packet_agent.py',
    'industrial_protocol_agent.py': 'C:/packet_agent/industrial_protocol_agent.py',
    'goose_sv_api.py': 'C:/packet_agent/goose_sv_api.py',
    'mail_client.py': 'C:/packet_agent/mail_client.py',

    # agent/ 子目录（packet_agent.py 的模块）
    'agent/__init__.py': 'C:/packet_agent/agent/__init__.py',
    'agent/capture.py': 'C:/packet_agent/agent/capture.py',
    'agent/command_executor.py': 'C:/packet_agent/agent/command_executor.py',
    'agent/file_transfer.py': 'C:/packet_agent/agent/file_transfer.py',
    'agent/listeners.py': 'C:/packet_agent/agent/listeners.py',
    'agent/packet_sender.py': 'C:/packet_agent/agent/packet_sender.py',
    'agent/replay.py': 'C:/packet_agent/agent/replay.py',
    'agent/scanner.py': 'C:/packet_agent/agent/scanner.py',
}

# 允许同步的文件模式（白名单）
ALLOWED_PATTERNS = [
    '*.py',  # Python 源文件
]

# 排除的目录和文件（黑名单）
EXCLUDED_DIRS = [
    '__pycache__',
    'build',
    'dist',
    'http',
    'mail_storage',
    '.git',
]

EXCLUDED_FILES = [
    '*.pyc',
    '*.pyo',
    '*.spec',
    '*.bat',
    '*.cmd',
    '*.exe',
    '*.log',
    '*.db',
    '*.json',
    'requirements.txt',
    'README*',
    'PsExec.exe',
    'build_exe.py',
    'build_exe.bat',
]


def calculate_md5(file_path):
    """计算文件 MD5 值"""
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_file_size(file_path):
    """获取文件大小"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def upload_file_to_hosts(ssh_conn, local_path, remote_path, host):
    """上传文件到远程主机"""
    try:
        from .agent_manager import agent_manager

        # 使用 SFTP 上传
        sftp = ssh_conn['sftp']
        temp_path = remote_path + '.tmp'

        # 上传到临时文件
        sftp.put(local_path, temp_path)

        # 重命名（原子操作）
        if sync_state['remote_user'] == 'tdhx':  # Windows
            cmd = f'move /Y "{temp_path}" "{remote_path}"'
        else:  # Linux
            cmd = f'mv "{temp_path}" "{remote_path}"'

        stdin, stdout, stderr = ssh_conn['ssh'].exec_command(cmd)
        stdout.read()

        local_size = get_file_size(local_path)
        logger.info(f"[{host}] 文件上传成功：{remote_path} ({local_size} 字节)")
        return True

    except Exception as e:
        logger.error(f"[{host}] 文件上传失败：{e}")
        return False


def restart_remote_agent(host, port=8888):
    """重启远程 Agent"""
    try:
        from .agent_manager import agent_manager

        # 停止 Agent
        success, msg = agent_manager.stop_agent(host, sync_state['remote_port'], port)
        logger.info(f"[{host}] 停止 Agent (端口{port}): {msg}")

        time.sleep(1)

        # 启动 Agent
        remote_path = REMOTE_PATHS.get('packet_agent.py', 'C:/packet_agent/packet_agent.py')
        if port == 8889:
            remote_path = remote_path.replace('packet_agent.py', 'industrial_protocol_agent.py')

        success, msg = agent_manager.start_agent(host, remote_path, sync_state['remote_port'], port)
        logger.info(f"[{host}] 启动 Agent (端口{port}): {msg}")

        return success

    except Exception as e:
        logger.error(f"[{host}] 重启 Agent 失败：{e}")
        return False


def process_pending_files():
    """处理待上传的文件"""
    with sync_state['lock']:
        if not sync_state['pending_files'] or sync_state['uploading']:
            return

        now = time.time()
        files_to_upload = []

        # 检查哪些文件已经过了冷却期
        for file_path, last_modified in list(sync_state['pending_files'].items()):
            if now - last_modified >= sync_state['cooldown']:
                files_to_upload.append(file_path)
                del sync_state['pending_files'][file_path]

        if not files_to_upload:
            return

        sync_state['uploading'] = True

    try:
        from .agent_manager import agent_manager

        logger.info(f"开始同步 {len(files_to_upload)} 个文件到远程主机...")

        # 连接远程主机
        for host in sync_state['remote_hosts']:
            logger.info(f"[{host}] 正在连接...")

            success, msg = agent_manager.connect_to_host(
                host,
                sync_state['remote_user'],
                sync_state['remote_password'],
                sync_state['remote_port']
            )

            if not success:
                logger.error(f"[{host}] 连接失败：{msg}")
                continue

            connection_key = f'{host}:{sync_state["remote_port"]}'
            ssh_conn = {
                'ssh': agent_manager.connections[connection_key]['ssh'],
                'sftp': agent_manager.connections[connection_key]['sftp'],
            }

            # 上传每个文件
            for local_path in files_to_upload:
                # 计算相对路径（相对于 watch_dir）
                rel_path = os.path.relpath(local_path, sync_state['watch_dir'])
                # 转换为 Unix 风格路径（使用 / 而不是 \）
                rel_path = rel_path.replace('\\', '/')

                remote_path = REMOTE_PATHS.get(rel_path)
                if not remote_path:
                    remote_path = f'C:/packet_agent/{rel_path}'

                file_name = os.path.basename(local_path)

                # 验证本地文件
                if not os.path.exists(local_path):
                    logger.warning(f"本地文件不存在：{local_path}")
                    continue

                local_md5 = calculate_md5(local_path)
                logger.info(f"上传文件：{rel_path} (MD5: {local_md5[:8]}...)")

                # 上传
                if upload_file_to_hosts(ssh_conn, local_path, remote_path, host):
                    logger.info(f"[{host}] ✅ {rel_path} 上传成功")

            # 重启 Agent
            logger.info(f"[{host}] 正在重启 Agent...")

            # 重启 packet_agent (8888)
            restart_remote_agent(host, 8888)
            time.sleep(1)

            # 重启 industrial_protocol_agent (8889)
            restart_remote_agent(host, 8889)

            logger.info(f"[{host}] ✅ Agent 重启完成")

    except Exception as e:
        logger.exception(f"同步文件时出错：{e}")

    finally:
        with sync_state['lock']:
            sync_state['uploading'] = False


def file_monitor_worker():
    """文件监控工作线程"""
    watch_dir = sync_state['watch_dir']
    logger.info(f"文件监控已启动，监控目录：{watch_dir}")
    logger.info(f"只同步 REMOTE_PATHS 中配置的文件")

    # 记录文件最后修改时间
    file_mtime = {}

    # 只初始化 REMOTE_PATHS 中配置的文件
    for rel_path in REMOTE_PATHS.keys():
        path = os.path.join(watch_dir, rel_path)
        if os.path.exists(path):
            file_mtime[path] = os.path.getmtime(path)
            logger.info(f"监控文件：{rel_path}")
        else:
            logger.warning(f"文件不存在：{rel_path}")

    while sync_state['running']:
        try:
            # 只检查 REMOTE_PATHS 中配置的文件
            for rel_path in REMOTE_PATHS.keys():
                path = os.path.join(watch_dir, rel_path)

                if not os.path.exists(path):
                    # 文件不存在，从监控列表移除
                    if path in file_mtime:
                        del file_mtime[path]
                    continue

                try:
                    current_mtime = os.path.getmtime(path)

                    # 检测文件变化
                    if path in file_mtime:
                        if current_mtime != file_mtime[path]:
                            # 文件被修改
                            file_mtime[path] = current_mtime
                            with sync_state['lock']:
                                sync_state['pending_files'][path] = time.time()
                            logger.info(f"检测到文件变化：{rel_path}")
                    else:
                        # 新文件
                        file_mtime[path] = current_mtime
                        with sync_state['lock']:
                            sync_state['pending_files'][path] = time.time()
                        logger.info(f"检测到新文件：{rel_path}")

                except OSError:
                    continue

            # 处理待上传的文件
            process_pending_files()

            # 每秒检查一次
            time.sleep(1)

        except Exception as e:
            logger.error(f"文件监控出错：{e}")
            time.sleep(2)

    logger.info("文件监控已停止")


def start_agent_sync(watch_dir=None, remote_hosts=None, user=None, password=None, port=22):
    """
    启动 Agent 自动同步

    Args:
        watch_dir: 监控目录，默认为 packet_agent/
        remote_hosts: 远程主机列表
        user: SSH 用户名
        password: SSH 密码
        port: SSH 端口
    """
    if sync_state['running']:
        logger.warning("Agent 同步已在运行中")
        return False

    # 配置默认值
    if watch_dir is None:
        # 默认监控 packet_agent 目录
        watch_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'packet_agent')

    if remote_hosts is None:
        remote_hosts = ['10.40.30.35', '10.40.30.34']

    if not os.path.isdir(watch_dir):
        logger.error(f"监控目录不存在：{watch_dir}")
        return False

    # 更新配置
    with sync_state['lock']:
        sync_state['watch_dir'] = watch_dir
        sync_state['remote_hosts'] = remote_hosts
        if user:
            sync_state['remote_user'] = user
        if password:
            sync_state['remote_password'] = password
        sync_state['remote_port'] = port
        sync_state['running'] = True
        sync_state['enabled'] = True

    logger.info("=" * 60)
    logger.info("Agent 文件自动同步已启动")
    logger.info(f"监控目录：{watch_dir}")
    logger.info(f"远程主机：{', '.join(remote_hosts)}")
    logger.info(f"SSH: {user or sync_state['remote_user']}@*:{port}")
    logger.info(f"同步文件列表：{len(REMOTE_PATHS)} 个文件")
    for rel_path in REMOTE_PATHS.keys():
        logger.info(f"  - {rel_path}")
    logger.info("=" * 60)

    # 启动监控线程
    thread = threading.Thread(target=file_monitor_worker, daemon=True, name='AgentSync')
    thread.start()

    return True


def stop_agent_sync():
    """停止 Agent 自动同步"""
    if not sync_state['running']:
        return False

    sync_state['running'] = False

    # 等待上传完成
    for _ in range(10):
        if not sync_state['uploading']:
            break
        time.sleep(0.5)

    logger.info("Agent 文件自动同步已停止")
    return True


def get_sync_status():
    """获取同步状态"""
    with sync_state['lock']:
        return {
            'running': sync_state['running'],
            'enabled': sync_state['enabled'],
            'watch_dir': sync_state['watch_dir'],
            'remote_hosts': sync_state['remote_hosts'],
            'pending_files': list(sync_state['pending_files'].keys()),
            'uploading': sync_state['uploading'],
        }


# ============== Django 集成 ==============

_sync_started = False


def auto_start_sync():
    """Django 启动时自动启动同步"""
    global _sync_started

    if _sync_started:
        return

    _sync_started = True

    # 从环境变量读取配置
    enabled = os.environ.get('AGENT_AUTO_SYNC', 'false').lower() == 'true'

    if enabled:
        hosts_env = os.environ.get('AGENT_REMOTE_HOSTS', '10.40.30.35,10.40.30.34')
        remote_hosts = [h.strip() for h in hosts_env.split(',')]

        user = os.environ.get('AGENT_SSH_USER', 'tdhx')
        password = os.environ.get('AGENT_SSH_PASSWORD', 'tdhx@2017')
        port = int(os.environ.get('AGENT_SSH_PORT', '22'))

        start_agent_sync(
            remote_hosts=remote_hosts,
            user=user,
            password=password,
            port=port
        )
