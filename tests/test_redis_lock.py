#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 分布式锁测试
"""

import pytest
import time
from main.redis_lock import ResourceLock, acquire_lock, release_lock, check_lock_status


@pytest.fixture
def lock():
    """创建锁实例"""
    return ResourceLock()


@pytest.fixture
def resource_id():
    return "test_resource_001"


@pytest.fixture
def session_a():
    return "session_a"


@pytest.fixture
def session_b():
    return "session_b"


class TestResourceLock:
    """资源锁测试类"""

    def test_acquire_lock_success(self, lock, resource_id, session_a):
        """测试获取锁成功"""
        success, msg = lock.acquire(resource_id, session_a, timeout=10)
        assert success, f"应该获取锁成功：{msg}"
        assert msg == "锁已获取"

    def test_acquire_lock_conflict(self, lock, resource_id, session_a, session_b):
        """测试锁冲突"""
        # A 先获取锁
        lock.acquire(resource_id, session_a, timeout=10)

        # B 尝试获取应该失败
        success, msg = lock.acquire(resource_id, session_b, timeout=10)
        assert not success, "B 应该获取锁失败"
        assert "占用" in msg or "持有者" in msg

    def test_release_lock_success(self, lock, resource_id, session_a):
        """测试释放锁成功"""
        lock.acquire(resource_id, session_a, timeout=10)
        success, msg = lock.release(resource_id, session_a)
        assert success, f"应该释放锁成功：{msg}"

    def test_release_lock_not_owner(self, lock, resource_id, session_a, session_b):
        """测试非持有者释放锁失败"""
        lock.acquire(resource_id, session_a, timeout=10)
        success, msg = lock.release(resource_id, session_b)
        assert not success, "非持有者应该释放失败"
        assert "持有者" in msg

    def test_check_lock_status(self, lock, resource_id, session_a):
        """测试检查锁状态"""
        # 未锁定时
        status = lock.check_status(resource_id)
        assert status['locked'] is False
        assert status['owner'] is None

        # 锁定后
        lock.acquire(resource_id, session_a, timeout=60)
        status = lock.check_status(resource_id)
        assert status['locked'] is True
        assert status['owner'] == session_a
        assert status['ttl'] > 0

    def test_lock_auto_expire(self, lock, resource_id, session_a):
        """测试锁自动过期"""
        lock.acquire(resource_id, session_a, timeout=3)  # 3 秒过期
        time.sleep(4)

        # 锁应该已过期
        status = lock.check_status(resource_id)
        assert status['locked'] is False

        # 其他人可以获取锁
        success, msg = lock.acquire(resource_id, "session_b", timeout=10)
        assert success, "过期后应该可以获取锁"
