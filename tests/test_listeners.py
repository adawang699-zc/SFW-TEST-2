#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端口监听服务测试
"""

import pytest
import time
import socket
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packet_agent.agent.listeners import (
    start_tcp_listener, stop_tcp_listener,
    start_udp_listener, stop_udp_listener,
    check_port_service, get_listener_status
)


class TestTCPListener:
    """TCP 监听器测试"""

    def test_start_stop_tcp_listener(self):
        """测试 TCP 监听器启动和停止"""
        port = 19999
        success, msg = start_tcp_listener(port)
        assert success, f"启动失败：{msg}"

        time.sleep(0.5)  # 等待启动

        # 检查端口是否监听
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        assert result == 0, "端口未监听"

        # 停止监听器
        success, msg = stop_tcp_listener(port)
        assert success, f"停止失败：{msg}"

    def test_check_tcp_service(self):
        """测试 TCP 端口服务检查"""
        port = 19998
        # 先启动监听
        start_tcp_listener(port)
        time.sleep(0.5)

        # 检查服务
        available, msg = check_port_service('127.0.0.1', port, 'tcp')
        assert available, f"服务应该可用：{msg}"

        # 停止后检查
        stop_tcp_listener(port)
        time.sleep(0.5)
        available, msg = check_port_service('127.0.0.1', port, 'tcp')
        assert not available, "服务应该不可用"


class TestUDPListener:
    """UDP 监听器测试"""

    def test_start_stop_udp_listener(self):
        """测试 UDP 监听器启动和停止"""
        port = 19997
        success, msg = start_udp_listener(port)
        assert success, f"启动失败：{msg}"

        time.sleep(0.5)  # 等待启动

        # 停止监听器
        success, msg = stop_udp_listener(port)
        assert success, f"停止失败：{msg}"

    def test_check_udp_service(self):
        """测试 UDP 端口服务检查"""
        port = 19996
        # 先启动监听
        start_udp_listener(port)
        time.sleep(0.5)

        # 检查服务
        available, msg = check_port_service('127.0.0.1', port, 'udp')
        # UDP 检查可能返回"可能开放"
        assert available, f"服务应该可用：{msg}"

        # 停止后检查
        stop_udp_listener(port)
        time.sleep(0.5)


class TestListenerStatus:
    """监听器状态测试"""

    def test_get_listener_status(self):
        """测试获取监听器状态"""
        port = 19995
        # 初始状态应该为空
        status = get_listener_status()
        assert 'tcp' in status
        assert 'udp' in status

        # 启动监听器
        start_tcp_listener(port)
        time.sleep(0.5)

        # 检查状态
        status = get_listener_status()
        assert port in status['tcp']
        assert status['tcp'][port]['running'] is True

        # 停止监听器
        stop_tcp_listener(port)
