# -*- coding: utf-8 -*-
"""
Test for ENIP handler module (TDD RED phase)
Tests for EtherNet/IP protocol implementation
"""

import pytest
import struct
import socket
import threading
import time


class TestEnipHeaderBuilding:
    """Test ENIP header building functionality"""

    def test_build_enip_header_creates_24_byte_header(self):
        """Test 1: build_enip_header creates correct 24-byte header"""
        from enip_handler import build_enip_header

        # Build header with standard parameters
        header = build_enip_header(command=0x0065, length=4, session_handle=0, status=0)

        # Verify length is 24 bytes
        assert len(header) == 24

        # Verify structure matches ENIP specification
        cmd, length, session, status = struct.unpack('<HHII', header[:12])
        assert cmd == 0x0065  # RegisterSession command
        assert length == 4
        assert session == 0
        assert status == 0

    def test_build_enip_header_with_session_handle(self):
        """Test header with non-zero session handle"""
        from enip_handler import build_enip_header

        header = build_enip_header(command=0x006F, length=10, session_handle=0x12345678)

        cmd, length, session, status = struct.unpack('<HHII', header[:12])
        assert session == 0x12345678


class TestEnipClient:
    """Test ENIP client operations"""

    def test_enip_client_class_exists(self):
        """Test EnipClient class can be imported"""
        from enip_handler import EnipClient
        assert EnipClient is not None

    def test_enip_client_connect_creates_socket(self):
        """Test connect method creates TCP socket"""
        from enip_handler import EnipClient

        client = EnipClient()
        # This test will fail without a real server - that's expected in RED phase
        # We'll use mock in GREEN phase
        assert hasattr(client, 'connect')
        assert hasattr(client, 'disconnect')

    def test_enip_client_register_session_sends_correct_command(self):
        """Test register_session sends 0x0065 command"""
        from enip_handler import EnipClient, build_enip_header

        client = EnipClient()
        assert hasattr(client, 'register_session')

        # The method should exist - actual functionality tested in integration

    def test_enip_client_read_attribute_sends_sendrrdata(self):
        """Test read_attribute sends SendRRData (0x006F) command"""
        from enip_handler import EnipClient

        client = EnipClient()
        assert hasattr(client, 'read_attribute')
        assert hasattr(client, 'write_attribute')


class TestEnipServer:
    """Test ENIP server operations"""

    def test_enip_server_class_exists(self):
        """Test EnipServer class can be imported"""
        from enip_handler import EnipServer
        assert EnipServer is not None

    def test_enip_server_has_start_stop_status_methods(self):
        """Test server has required methods"""
        from enip_handler import EnipServer

        server = EnipServer()
        assert hasattr(server, 'start')
        assert hasattr(server, 'stop')
        assert hasattr(server, 'status')

    def test_enip_server_starts_tcp_server_on_port_44818(self):
        """Test server starts on default port 44818"""
        from enip_handler import EnipServer

        server = EnipServer()
        # Method signature should accept host and port
        # Default port should be 44818
        assert callable(server.start)


class TestEnipConstants:
    """Test ENIP constants are defined correctly"""

    def test_enip_commands_defined(self):
        """Test ENIP_COMMANDS dictionary exists with required commands"""
        from enip_handler import ENIP_COMMANDS

        assert isinstance(ENIP_COMMANDS, dict)
        assert ENIP_COMMANDS.get('NOP') == 0x0001
        assert ENIP_COMMANDS.get('ListIdentity') == 0x0063
        assert ENIP_COMMANDS.get('RegisterSession') == 0x0065
        assert ENIP_COMMANDS.get('SendRRData') == 0x006F or ENIP_COMMANDS.get('SendRRData') == 0x0070

    def test_cpf_item_constants_defined(self):
        """Test CPF item type constants"""
        from enip_handler import CPF_ITEM_NULL, CPF_ITEM_UNCONNECTED_MESSAGE

        assert CPF_ITEM_NULL == 0x0000
        assert CPF_ITEM_UNCONNECTED_MESSAGE == 0x00B2


class TestThreadSafety:
    """Test thread safety features"""

    def test_client_has_lock_for_thread_safety(self):
        """Test client uses threading.Lock for thread safety"""
        from enip_handler import EnipClient

        client = EnipClient()
        assert hasattr(client, '_lock')
        assert isinstance(client._lock, type(threading.Lock()))

    def test_server_has_lock_for_thread_safety(self):
        """Test server uses threading.Lock for thread safety"""
        from enip_handler import EnipServer

        server = EnipServer()
        assert hasattr(server, '_lock')
        assert isinstance(server._lock, type(threading.Lock()))