#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报文发送测试
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packet_agent.agent.packet_sender import (
    send_tcp_packet, send_udp_packet, send_icmp_packet
)


class TestPacketSender:
    """报文发送测试"""

    def test_send_tcp_packet(self):
        """测试 TCP 报文发送（到回环地址）"""
        success, stats = send_tcp_packet(
            '127.0.0.1', '127.0.0.1',
            12345, 8888,
            payload='Test TCP',
            count=3
        )
        assert success, f"发送失败：{stats}"
        assert stats['packets_sent'] == 3

    def test_send_udp_packet(self):
        """测试 UDP 报文发送"""
        success, stats = send_udp_packet(
            '127.0.0.1', '127.0.0.1',
            12345, 8888,
            payload='Test UDP',
            count=2
        )
        assert success, f"发送失败：{stats}"
        assert stats['packets_sent'] == 2

    def test_send_icmp_packet(self):
        """测试 ICMP 报文发送（可能需要 root）"""
        success, results = send_icmp_packet(
            '127.0.0.1', '127.0.0.1',
            data='Test ICMP',
            count=2
        )
        # ICMP 可能需要特权，只验证不抛出异常
        assert success
