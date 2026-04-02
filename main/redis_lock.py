#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 分布式锁模块
实现测试设备的互斥访问控制
"""

import redis
import time
import threading
import logging
import os
from typing import Tuple, Optional, Dict
from django.conf import settings

logger = logging.getLogger(__name__)

# Redis 连接配置
REDIS_HOST = getattr(settings, 'REDIS_HOST', os.environ.get('REDIS_HOST', 'localhost'))
REDIS_PORT = getattr(settings, 'REDIS_PORT', int(os.environ.get('REDIS_PORT', 6379)))
REDIS_DB = getattr(settings, 'REDIS_DB', 0)

# 全局 Redis 连接池
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_lock = threading.Lock()


def get_redis_client() -> redis.Redis:
    """获取 Redis 客户端（单例模式）"""
    global _redis_pool

    if _redis_pool is None:
        with _redis_lock:
            if _redis_pool is None:
                _redis_pool = redis.ConnectionPool(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    decode_responses=True
                )

    return redis.Redis(connection_pool=_redis_pool)


class ResourceLock:
    """
    分布式锁实现

    使用 Redis SET key value NX EX timeout 命令实现原子锁
    """

    def __init__(self, redis_host: str = None, redis_port: int = None):
        """
        初始化分布式锁

        Args:
            redis_host: Redis 主机（可选，默认使用配置）
            redis_port: Redis 端口（可选，默认使用配置）
        """
        host = redis_host or REDIS_HOST
        port = redis_port or REDIS_PORT
        self.redis = redis.Redis(host=host, port=port, decode_responses=True)

    def acquire(self, resource_id: str, session_id: str, timeout: int = 300) -> Tuple[bool, str]:
        """
        获取锁

        Args:
            resource_id: 资源标识（如 device_id）
            session_id: 会话标识（如 user_id + timestamp）
            timeout: 锁超时时间（秒），默认 5 分钟

        Returns:
            (是否成功，消息)
        """
        lock_key = f"lock:resource:{resource_id}"

        try:
            # 尝试获取锁（NX=only if not exists, EX=expiration）
            acquired = self.redis.set(lock_key, session_id, nx=True, ex=timeout)

            if acquired:
                logger.info(f"锁已获取：{resource_id} by {session_id}")
                return True, "锁已获取"
            else:
                # 锁已被占用，返回当前持有者信息
                current_owner = self.redis.get(lock_key)
                ttl = self.redis.ttl(lock_key)
                logger.info(f"锁被占用：{resource_id} by {current_owner}, TTL={ttl}")
                return False, f"资源被占用，持有者：{current_owner}, 剩余时间：{ttl}秒"

        except redis.ConnectionError as e:
            logger.error(f"Redis 连接失败：{e}")
            return False, f"Redis 连接失败：{e}"
        except Exception as e:
            logger.exception(f"获取锁异常：{e}")
            return False, f"获取锁异常：{e}"

    def release(self, resource_id: str, session_id: str) -> Tuple[bool, str]:
        """
        释放锁

        Args:
            resource_id: 资源标识
            session_id: 会话标识（必须是当前持有者）

        Returns:
            (是否成功，消息)
        """
        lock_key = f"lock:resource:{resource_id}"

        try:
            # 检查是否是锁的持有者
            current_owner = self.redis.get(lock_key)

            if current_owner is None:
                return True, "锁不存在或已过期"

            if current_owner != session_id:
                logger.warning(f"释放锁失败：{resource_id} 持有者是 {current_owner}, 尝试释放者：{session_id}")
                return False, f"无法释放锁：您不是锁的持有者（当前持有者：{current_owner}）"

            # 删除锁
            self.redis.delete(lock_key)
            logger.info(f"锁已释放：{resource_id} by {session_id}")
            return True, "锁已释放"

        except redis.ConnectionError as e:
            logger.error(f"Redis 连接失败：{e}")
            return False, f"Redis 连接失败：{e}"
        except Exception as e:
            logger.exception(f"释放锁异常：{e}")
            return False, f"释放锁异常：{e}"

    def check_status(self, resource_id: str) -> Dict:
        """
        检查锁状态

        Args:
            resource_id: 资源标识

        Returns:
            {'locked': bool, 'owner': str or None, 'ttl': int}
        """
        lock_key = f"lock:resource:{resource_id}"

        try:
            owner = self.redis.get(lock_key)
            ttl = self.redis.ttl(lock_key) if owner else -1

            return {
                'locked': owner is not None,
                'owner': owner,
                'ttl': ttl
            }

        except Exception as e:
            logger.error(f"检查锁状态失败：{e}")
            return {
                'locked': False,
                'owner': None,
                'ttl': -1,
                'error': str(e)
            }

    def extend(self, resource_id: str, session_id: str,
               additional_time: int = 300) -> Tuple[bool, str]:
        """
        延长锁的过期时间（续期）

        Args:
            resource_id: 资源标识
            session_id: 会话标识（必须是当前持有者）
            additional_time: 延长时间（秒）

        Returns:
            (是否成功，消息)
        """
        lock_key = f"lock:resource:{resource_id}"

        try:
            current_owner = self.redis.get(lock_key)

            if current_owner != session_id:
                return False, "无法续期：您不是锁的持有者"

            # 重新设置过期时间
            self.redis.expire(lock_key, additional_time)
            new_ttl = self.redis.ttl(lock_key)

            logger.info(f"锁已续期：{resource_id}, 新 TTL={new_ttl}")
            return True, f"锁已续期，剩余时间：{new_ttl}秒"

        except Exception as e:
            logger.exception(f"锁续期异常：{e}")
            return False, f"续期异常：{e}"

    def force_release(self, resource_id: str, admin_session: str) -> Tuple[bool, str]:
        """
        强制释放锁（管理员操作）

        Args:
            resource_id: 资源标识
            admin_session: 管理员会话标识

        Returns:
            (是否成功，消息)
        """
        lock_key = f"lock:resource:{resource_id}"

        try:
            # 管理员可以强制删除任何锁
            owner = self.redis.get(lock_key)
            self.redis.delete(lock_key)

            logger.warning(f"锁被强制释放：{resource_id}, 原持有者：{owner}, 管理员：{admin_session}")
            return True, f"锁已强制释放（原持有者：{owner}）"

        except Exception as e:
            logger.exception(f"强制释放锁异常：{e}")
            return False, f"强制释放异常：{e}"


# 便捷函数
_global_lock: Optional[ResourceLock] = None


def get_global_lock() -> ResourceLock:
    """获取全局锁实例"""
    global _global_lock
    if _global_lock is None:
        _global_lock = ResourceLock()
    return _global_lock


def acquire_lock(resource_id: str, session_id: str, timeout: int = 300) -> Tuple[bool, str]:
    """便捷函数：获取锁"""
    return get_global_lock().acquire(resource_id, session_id, timeout)


def release_lock(resource_id: str, session_id: str) -> Tuple[bool, str]:
    """便捷函数：释放锁"""
    return get_global_lock().release(resource_id, session_id)


def check_lock_status(resource_id: str) -> Dict:
    """便捷函数：检查锁状态"""
    return get_global_lock().check_status(resource_id)
