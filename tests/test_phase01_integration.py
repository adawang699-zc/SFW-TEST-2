#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 01 集成测试
验证所有 Phase 01 功能模块协同工作
"""

import os
import sys
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoProject.settings')

import django
django.setup()

from django.test import Client

# 测试报告
class TestReport:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, name):
        self.passed += 1
        print(f"  [PASS] {name}")

    def add_fail(self, name, reason):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  [FAIL] {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"测试结果：{self.passed}/{total} 通过")
        if self.errors:
            print("\n失败项:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


report = TestReport()

print("="*60)
print("Phase 01 集成测试")
print("="*60)

# ==================== 1. 模块导入测试 ====================
print("\n[1/6] 模块导入测试...")

try:
    from main.redis_lock import ResourceLock, acquire_lock, release_lock, check_lock_status
    report.add_pass("main.redis_lock 导入成功")
except Exception as e:
    report.add_fail("main.redis_lock", str(e))

try:
    from main.agent_manager import RemoteAgentManager
    report.add_pass("main.agent_manager 导入成功")
except Exception as e:
    report.add_fail("main.agent_manager", str(e))

try:
    from packet_agent.agent.listeners import start_tcp_listener, stop_tcp_listener, check_port_service
    report.add_pass("packet_agent.agent.listeners 导入成功")
except Exception as e:
    report.add_fail("packet_agent.agent.listeners", str(e))

try:
    from packet_agent.agent.packet_sender import send_tcp_packet, send_udp_packet, send_icmp_packet
    report.add_pass("packet_agent.agent.packet_sender 导入成功")
except Exception as e:
    report.add_fail("packet_agent.agent.packet_sender", str(e))

try:
    from packet_agent.agent.scanner import port_scan, scan_common_ports
    report.add_pass("packet_agent.agent.scanner 导入成功")
except Exception as e:
    report.add_fail("packet_agent.agent.scanner", str(e))

try:
    from packet_agent.agent.capture import start_capture, stop_capture, save_capture_to_pcap
    report.add_pass("packet_agent.agent.capture 导入成功")
except Exception as e:
    report.add_fail("packet_agent.agent.capture", str(e))

try:
    from packet_agent.agent.replay import start_replay, stop_replay, replay_from_pcap
    report.add_pass("packet_agent.agent.replay 导入成功")
except Exception as e:
    report.add_fail("packet_agent.agent.replay", str(e))

try:
    from packet_agent.agent.file_transfer import upload_file, download_file
    report.add_pass("packet_agent.agent.file_transfer 导入成功")
except Exception as e:
    report.add_fail("packet_agent.agent.file_transfer", str(e))

try:
    from packet_agent.agent.command_executor import execute_remote_command, execute_command_with_retry
    report.add_pass("packet_agent.agent.command_executor 导入成功")
except Exception as e:
    report.add_fail("packet_agent.agent.command_executor", str(e))

# ==================== 2. Django API 视图导入测试 ====================
print("\n[2/6] Django API 视图导入测试...")

try:
    from main.views_with_cache import reserve_device, release_device, check_device_status, extend_device_lock
    report.add_pass("设备预留 API 视图导入成功")
except Exception as e:
    report.add_fail("设备预留 API 视图", str(e))

try:
    from main.views_with_cache import service_listener_control, service_client_control
    report.add_pass("服务监听 API 视图导入成功")
except Exception as e:
    report.add_fail("服务监听 API 视图", str(e))

# ==================== 3. URL 路由配置测试 ====================
print("\n[3/6] URL 路由配置测试...")

try:
    from django.urls import reverse, NoReverseMatch

    url_names = [
        'reserve_device',
        'release_device',
        'check_device_status',
        'extend_device_lock',
        'service_listener_control',
        'agent_start',
        'agent_stop',
        'agent_status',
    ]

    for name in url_names:
        try:
            url = reverse(f'main:{name}')
            report.add_pass(f"URL {name} -> {url}")
        except NoReverseMatch:
            report.add_fail(f"URL {name}", "路由未找到")

except Exception as e:
    report.add_fail("URL 路由测试", str(e))

# ==================== 4. 功能测试 - 端口监听 ====================
print("\n[4/6] 功能测试 - 端口监听和报文发送...")

try:
    # 测试 TCP 监听器
    port = 19001
    success, msg = start_tcp_listener(port)
    if success:
        report.add_pass(f"TCP 监听器启动 (端口 {port})")
        time.sleep(0.5)

        # 检查端口服务
        available, check_msg = check_port_service('127.0.0.1', port, 'tcp')
        if available:
            report.add_pass("端口服务检查 - 服务可用")
        else:
            report.add_fail("端口服务检查", check_msg)

        # 停止监听器
        stop_success, stop_msg = stop_tcp_listener(port)
        if stop_success:
            report.add_pass("TCP 监听器停止")
        else:
            report.add_fail("TCP 监听器停止", stop_msg)
    else:
        report.add_fail("TCP 监听器启动", msg)
except Exception as e:
    report.add_fail("端口监听测试", str(e))

# ==================== 5. 功能测试 - 报文发送 ====================
print("\n[5/6] 功能测试 - 报文发送...")

try:
    # 测试 TCP 报文发送
    success, stats = send_tcp_packet(
        '127.0.0.1', '127.0.0.1',
        12345, 8888,
        payload='Integration Test',
        count=2
    )
    if success:
        report.add_pass(f"TCP 报文发送 - 发送 {stats['packets_sent']} 个报文")
    else:
        report.add_fail("TCP 报文发送", stats.get('error', '未知错误'))
except Exception as e:
    report.add_fail("TCP 报文发送", str(e))

try:
    # 测试 UDP 报文发送
    success, stats = send_udp_packet(
        '127.0.0.1', '127.0.0.1',
        12345, 8889,
        payload='UDP Test',
        count=2
    )
    if success:
        report.add_pass(f"UDP 报文发送 - 发送 {stats['packets_sent']} 个报文")
    else:
        report.add_fail("UDP 报文发送", stats.get('error', '未知错误'))
except Exception as e:
    report.add_fail("UDP 报文发送", str(e))

try:
    # 测试端口扫描
    success, result = scan_common_ports('127.0.0.1')
    if success:
        report.add_pass(f"端口扫描 - 发现 {result.get('total_open', 0)} 个开放端口")
    else:
        report.add_fail("端口扫描", result.get('error', '未知错误'))
except Exception as e:
    report.add_fail("端口扫描", str(e))

# ==================== 6. Redis 锁功能测试 ====================
print("\n[6/6] 功能测试 - Redis 分布式锁...")

try:
    # 检查 Redis 连接
    import redis
    redis_client = redis.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        decode_responses=True
    )

    try:
        redis_client.ping()
        report.add_pass("Redis 连接成功")

        # 测试锁获取
        lock = ResourceLock()
        success, msg = lock.acquire("test:device:999", "test_session", timeout=10)
        if success:
            report.add_pass("Redis 锁获取成功")

            # 测试锁状态检查
            status = lock.check_status("test:device:999")
            if status['locked'] and status['owner'] == 'test_session':
                report.add_pass("Redis 锁状态检查正确")
            else:
                report.add_fail("Redis 锁状态检查", f"状态不符：{status}")

            # 测试锁冲突
            success2, msg2 = lock.acquire("test:device:999", "other_session", timeout=10)
            if not success2:
                report.add_pass("Redis 锁冲突检测正确")
            else:
                report.add_fail("Redis 锁冲突检测", "应该获取失败")

            # 测试锁释放
            release_success, release_msg = lock.release("test:device:999", "test_session")
            if release_success:
                report.add_pass("Redis 锁释放成功")
            else:
                report.add_fail("Redis 锁释放", release_msg)

            # 验证锁已释放
            status2 = lock.check_status("test:device:999")
            if not status2['locked']:
                report.add_pass("Redis 锁已释放验证")
            else:
                report.add_fail("Redis 锁已释放验证", "锁仍然存在")
        else:
            report.add_fail("Redis 锁获取", msg)

    except redis.ConnectionError:
        report.add_fail("Redis 连接", "无法连接到 Redis 服务器 - 请确认 Redis 服务已启动 (redis-cli ping)")

except ImportError:
    report.add_fail("Redis 模块", "redis 包未安装")
except Exception as e:
    report.add_fail("Redis 锁测试", str(e))

# ==================== 测试总结 ====================
print("\n")
success = report.summary()

if success:
    print("\n[PASS] Phase 01 集成测试全部通过!")
else:
    print(f"\n[FAIL] Phase 01 集成测试有 {report.failed} 项失败")

sys.exit(0 if success else 1)
