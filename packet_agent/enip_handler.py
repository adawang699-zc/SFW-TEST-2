# -*- coding: utf-8 -*-
"""
enip_handler.py - EtherNet/IP 协议处理器
纯 socket 实现，无外部依赖

提供客户端和服务端功能：
- 客户端: 连接设备、注册会话、读写CIP属性
- 服务端: 模拟CIP对象，响应ListIdentity/RegisterSession等

参考: apps/ENIP/enip_client_entry.py 和 apps/ENIP/enip_server_entry.py
"""

import socket
import struct
import threading
import time
import logging
from typing import Dict, Any, Optional, Tuple, List


# ----- ENIP 常量 -----
ENIP_PORT = 44818
ENIP_IO_PORT = 2222
SENDER_CONTEXT = b"_pycomm_"

# ENIP 命令码
ENIP_COMMANDS = {
    'NOP': 0x0001,
    'ListServices': 0x0004,
    'ListIdentity': 0x0063,
    'ListInterfaces': 0x0064,
    'RegisterSession': 0x0065,
    'UnregisterSession': 0x0066,
    'SendRRData': 0x006F,  # Send Request-Reply Data
    'SendUnitData': 0x0070,  # Send Unit Data
    'IndicateStatus': 0x0072,
    'Cancel': 0x0073,
}

# CPF 项类型
CPF_ITEM_NULL = 0x0000
CPF_ITEM_COMM_CAP = 0x0001
CPF_ITEM_INTERFACE_LIST = 0x0002
CPF_ITEM_CONNECTION_BASED = 0x00A1
CPF_ITEM_CONNECTED_DATA = 0x00B1
CPF_ITEM_UNCONNECTED_MESSAGE = 0x00B2
CPF_ITEM_SEQUENCED_ADDR = 0x8002

# CIP 服务码
CIP_SERVICE_GET_ATTRIBUTE_SINGLE = 0x0E
CIP_SERVICE_SET_ATTRIBUTE_SINGLE = 0x10
CIP_SERVICE_GET_ATTRIBUTE_ALL = 0x01

# CIP 路径段类型
CIP_PATH_CLASS = 0x20
CIP_PATH_INSTANCE = 0x24
CIP_PATH_ATTRIBUTE = 0x30

# Identity 对象类ID (CIP标准对象)
CIP_CLASS_IDENTITY = 0x01


def build_enip_header(command: int, length: int, session_handle: int = 0,
                      status: int = 0, context: bytes = None, options: int = 0) -> bytes:
    """
    构建 EtherNet/IP 封装头 (24字节)

    Args:
        command: 命令码 (uint16)
        length: 数据长度 (uint16)
        session_handle: 会话句柄 (uint32)
        status: 状态码 (uint32)
        context: 发送者上下文 (8字节)
        options: 选项 (uint32)

    Returns:
        24字节 ENIP 封装头
    """
    if context is None:
        context = SENDER_CONTEXT
    context = context.ljust(8, b"\x00")[:8]

    header = struct.pack("<H", command)
    header += struct.pack("<H", length)
    header += struct.pack("<I", session_handle)
    header += struct.pack("<I", status)
    header += context
    header += struct.pack("<I", options)

    return header


def parse_enip_header(header: bytes) -> Optional[Dict[str, Any]]:
    """
    解析 ENIP 封装头

    Args:
        header: 24字节封装头

    Returns:
        解析后的字典或 None
    """
    if not header or len(header) < 24:
        return None

    cmd, length, session, status = struct.unpack("<HHII", header[:12])
    sender_context = header[12:20]
    options = struct.unpack("<I", header[20:24])[0]

    return {
        'command': cmd,
        'length': length,
        'session_handle': session,
        'status': status,
        'sender_context': sender_context,
        'options': options,
    }


def build_ucmm_cpf(cip_data: bytes) -> bytes:
    """
    构建 UCMM (Unconnected Message Manager) CPF 载荷
    用于 SendRRData 请求

    Args:
        cip_data: CIP 报文数据

    Returns:
        CPF 载荷字节
    """
    # Interface Handle (0) + Timeout (0) + Item Count (2)
    cpf = struct.pack("<IHH", 0, 0, 2)
    # NULL item (address)
    cpf += struct.pack("<HH", CPF_ITEM_NULL, 0)
    # Unconnected Message item (data)
    cpf += struct.pack("<HH", CPF_ITEM_UNCONNECTED_MESSAGE, len(cip_data))
    cpf += cip_data

    return cpf


def build_cip_read_request(class_id: int, instance: int, attribute: int) -> bytes:
    """
    构建 CIP Get_Attribute_Single 请求

    Args:
        class_id: CIP 类ID
        instance: 实例号
        attribute: 属性号

    Returns:
        CIP 请求字节
    """
    # Service code (0x0E = Get_Attribute_Single) + Path size
    cip = bytes([CIP_SERVICE_GET_ATTRIBUTE_SINGLE, 0x03])
    # Path: Class (0x20) + Class ID + Instance (0x24) + Instance ID + Attribute (0x30) + Attribute ID
    cip += bytes([CIP_PATH_CLASS, class_id, CIP_PATH_INSTANCE, instance, CIP_PATH_ATTRIBUTE, attribute])

    return cip


def build_cip_write_request(class_id: int, instance: int, attribute: int, value: bytes) -> bytes:
    """
    构建 CIP Set_Attribute_Single 请求

    Args:
        class_id: CIP 类ID
        instance: 实例号
        attribute: 属性号
        value: 要写入的值

    Returns:
        CIP 请求字节
    """
    # Service code (0x10 = Set_Attribute_Single) + Path size
    cip = bytes([CIP_SERVICE_SET_ATTRIBUTE_SINGLE, 0x03])
    # Path
    cip += bytes([CIP_PATH_CLASS, class_id, CIP_PATH_INSTANCE, instance, CIP_PATH_ATTRIBUTE, attribute])
    # Data
    cip += value

    return cip


class EnipClient:
    """
    EtherNet/IP 客户端

    支持连接到 ENIP 设备并执行 CIP 操作：
    - 注册会话
    - 读取属性
    - 写入属性

    使用原始 socket 实现，无外部依赖
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._socket: Optional[socket.socket] = None
        self._session_handle: int = 0
        self._connected: bool = False
        self._host: str = ""
        self._port: int = ENIP_PORT
        self._timeout: float = 5.0
        self._connect_time: Optional[str] = None

    def connect(self, host: str, port: int = ENIP_PORT, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        连接到 ENIP 设备

        Args:
            host: 设备IP地址
            port: ENIP端口 (默认44818)
            timeout: 连接超时

        Returns:
            (成功标志, 消息)
        """
        with self._lock:
            try:
                # 断开已有连接
                if self._socket:
                    self._disconnect_internal()

                # 创建新 socket
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(timeout)
                self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                # 连接
                self._socket.connect((host, port))
                self._host = host
                self._port = port
                self._timeout = timeout

                # 注册会话
                success, message, session = self._register_session_internal()
                if success:
                    self._session_handle = session
                    self._connected = True
                    self._connect_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    return (True, f"连接成功，会话句柄: 0x{session:08X}")
                else:
                    self._disconnect_internal()
                    return (False, f"会话注册失败: {message}")

            except socket.timeout:
                return (False, f"连接超时: {host}:{port}")
            except socket.error as e:
                return (False, f"连接错误: {e}")
            except Exception as e:
                return (False, f"连接异常: {e}")

    def disconnect(self) -> Tuple[bool, str]:
        """
        断开连接

        Returns:
            (成功标志, 消息)
        """
        with self._lock:
            if not self._socket:
                return (False, "未连接")

            try:
                # 发送 UnregisterSession
                self._unregister_session_internal()
            except:
                pass

            self._disconnect_internal()
            return (True, "断开连接成功")

    def _disconnect_internal(self):
        """内部断开连接（不加锁）"""
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
        self._socket = None
        self._connected = False
        self._session_handle = 0

    def _register_session_internal(self) -> Tuple[bool, str, int]:
        """
        注册会话（内部方法，不加锁）

        Returns:
            (成功标志, 消息, 会话句柄)
        """
        try:
            # 构建注册会话请求
            # Payload: Protocol Version (0x0100) + Options (0x0000)
            payload = struct.pack("<HH", 0x0100, 0x0000)
            header = build_enip_header(ENIP_COMMANDS['RegisterSession'], len(payload))

            # 发送
            self._socket.sendall(header + payload)

            # 接收响应
            response = self._recv_response()
            if response:
                parsed = parse_enip_header(response)
                if parsed and parsed['status'] == 0:
                    # 从响应数据中提取会话句柄（前4字节）
                    if len(response) >= 28:
                        session = struct.unpack("<I", response[24:28])[0]
                        return (True, "会话注册成功", session)
                    else:
                        # 使用响应头中的 session_handle
                        return (True, "会话注册成功", parsed['session_handle'])
                else:
                    status = parsed['status'] if parsed else -1
                    return (False, f"注册失败，状态码: {status}", 0)
            else:
                return (False, "无响应", 0)

        except Exception as e:
            return (False, str(e), 0)

    def _unregister_session_internal(self):
        """取消注册会话（内部方法）"""
        try:
            header = build_enip_header(ENIP_COMMANDS['UnregisterSession'], 0, self._session_handle)
            self._socket.sendall(header)
        except:
            pass

    def _recv_response(self, timeout: float = None) -> Optional[bytes]:
        """
        接收响应

        Args:
            timeout: 超时时间

        Returns:
            响应字节或 None
        """
        if timeout is None:
            timeout = self._timeout

        try:
            # 接收24字节头
            header_buf = b""
            while len(header_buf) < 24:
                chunk = self._socket.recv(24 - len(header_buf))
                if not chunk:
                    return None
                header_buf += chunk

            # 解析头获取数据长度
            parsed = parse_enip_header(header_buf)
            if not parsed:
                return header_buf

            data_len = parsed['length']

            # 接收数据部分
            data_buf = b""
            if data_len > 0:
                while len(data_buf) < data_len:
                    chunk = self._socket.recv(min(data_len - len(data_buf), 4096))
                    if not chunk:
                        break
                    data_buf += chunk

            return header_buf + data_buf

        except socket.timeout:
            return None
        except Exception:
            return None

    def register_session(self) -> Tuple[bool, str]:
        """
        手动注册会话（通常连接时自动注册）

        Returns:
            (成功标志, 消息)
        """
        with self._lock:
            if not self._socket:
                return (False, "未连接")

            success, message, session = self._register_session_internal()
            if success:
                self._session_handle = session
                self._connected = True
            return (success, message)

    def read_attribute(self, class_id: int, instance: int, attribute: int) -> Tuple[bool, Any, str]:
        """
        读取 CIP 属性

        Args:
            class_id: CIP 类ID (如 0x01 = Identity)
            instance: 实例号
            attribute: 属性号

        Returns:
            (成功标志, 数据, 消息)
        """
        with self._lock:
            if not self._socket or not self._connected:
                return (False, None, "未连接")

            try:
                # 构建 CIP 读请求
                cip_request = build_cip_read_request(class_id, instance, attribute)
                cpf_payload = build_ucmm_cpf(cip_request)

                # 构建 SendRRData 请求
                header = build_enip_header(
                    ENIP_COMMANDS['SendRRData'],
                    len(cpf_payload),
                    self._session_handle
                )

                # 发送
                self._socket.sendall(header + cpf_payload)

                # 接收响应
                response = self._recv_response()
                if response:
                    parsed = parse_enip_header(response)
                    if parsed and parsed['status'] == 0:
                        # 解析 CPF 和 CIP 响应
                        data = self._parse_read_response(response[24:])
                        return (True, data, "读取成功")
                    else:
                        status = parsed['status'] if parsed else -1
                        return (False, None, f"读取失败，状态码: {status}")
                else:
                    return (False, None, "无响应")

            except Exception as e:
                return (False, None, str(e))

    def write_attribute(self, class_id: int, instance: int, attribute: int,
                       value: bytes) -> Tuple[bool, str]:
        """
        写入 CIP 属性

        Args:
            class_id: CIP 类ID
            instance: 实例号
            attribute: 属性号
            value: 要写入的值

        Returns:
            (成功标志, 消息)
        """
        with self._lock:
            if not self._socket or not self._connected:
                return (False, "未连接")

            try:
                # 构建 CIP 写请求
                cip_request = build_cip_write_request(class_id, instance, attribute, value)
                cpf_payload = build_ucmm_cpf(cip_request)

                # 构建 SendRRData 请求
                header = build_enip_header(
                    ENIP_COMMANDS['SendRRData'],
                    len(cpf_payload),
                    self._session_handle
                )

                # 发送
                self._socket.sendall(header + cpf_payload)

                # 接收响应
                response = self._recv_response()
                if response:
                    parsed = parse_enip_header(response)
                    if parsed and parsed['status'] == 0:
                        return (True, "写入成功")
                    else:
                        status = parsed['status'] if parsed else -1
                        return (False, f"写入失败，状态码: {status}")
                else:
                    return (False, "无响应")

            except Exception as e:
                return (False, str(e))

    def _parse_read_response(self, cpf_data: bytes) -> Any:
        """
        解析读取响应

        Args:
            cpf_data: CPF 数据

        Returns:
            解析后的数据
        """
        if len(cpf_data) < 8:
            return None

        # 解析 CPF 项
        interface_handle, timeout, item_count = struct.unpack("<IHH", cpf_data[:8])

        off = 8
        for i in range(item_count):
            if off + 4 > len(cpf_data):
                break
            item_type, item_len = struct.unpack("<HH", cpf_data[off:off+4])
            off += 4

            if item_type == CPF_ITEM_UNCONNECTED_MESSAGE:
                # CIP 响应数据
                cip_data = cpf_data[off:off+item_len]
                if len(cip_data) >= 2:
                    # 检查响应服务码（请求码 + 0x80）
                    service_code = cip_data[0]
                    if service_code & 0x80:  # 响应码
                        # 返回 CIP 数据（跳过服务码和状态）
                        if len(cip_data) >= 4:
                            return cip_data[4:]  # 返回属性数据
                        return cip_data
                return cip_data

            off += item_len

        return None

    def status(self) -> Dict[str, Any]:
        """
        获取客户端状态

        Returns:
            状态字典
        """
        with self._lock:
            return {
                'connected': self._connected,
                'host': self._host,
                'port': self._port,
                'session_handle': self._session_handle,
                'connect_time': self._connect_time,
            }


class EnipServer:
    """
    EtherNet/IP 服务端

    模拟 CIP 设备，支持：
    - ListIdentity 响应
    - RegisterSession 处理
    - CIP 属性读写（Identity 对象）

    运行在后台线程中
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._socket: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._host: str = "0.0.0.0"
        self._port: int = ENIP_PORT
        self._sessions: Dict[int, Dict] = {}  # session_handle -> session info
        self._identity_data: Dict[int, bytes] = {
            # Identity 对象属性数据
            1: struct.pack("<H", 1),  # Vendor ID
            2: struct.pack("<H", 1),  # Device Type
            3: struct.pack("<H", 1),  # Product Code
            4: struct.pack("<I", 0x01000000),  # Status
            5: struct.pack("<I", 1),  # Serial Number
            6: "ENIP Simulator".encode('utf-8')[:32].ljust(32, b'\x00'),  # Product Name
        }

    def start(self, host: str = "0.0.0.0", port: int = ENIP_PORT) -> Tuple[bool, str]:
        """
        启动 ENIP 服务端

        Args:
            host: 绑定地址
            port: 监听端口

        Returns:
            (成功标志, 消息)
        """
        with self._lock:
            if self._running:
                return (False, "服务端已在运行")

            try:
                self._host = host
                self._port = port

                # 创建 socket
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._socket.bind((host, port))
                self._socket.listen(5)

                # 启动后台线程
                self._running = True
                self._server_thread = threading.Thread(
                    target=self._server_loop,
                    daemon=True
                )
                self._server_thread.start()

                return (True, f"服务端启动成功: {host}:{port}")

            except socket.error as e:
                self._running = False
                return (False, f"启动失败: {e}")
            except Exception as e:
                self._running = False
                return (False, f"启动异常: {e}")

    def stop(self) -> Tuple[bool, str]:
        """
        停止服务端

        Returns:
            (成功标志, 消息)
        """
        with self._lock:
            if not self._running:
                return (False, "服务端未运行")

            self._running = False

            if self._socket:
                try:
                    self._socket.close()
                except:
                    pass
                self._socket = None

            self._server_thread = None
            self._sessions.clear()

            return (True, "服务端已停止")

    def status(self) -> Dict[str, Any]:
        """
        获取服务端状态

        Returns:
            状态字典
        """
        with self._lock:
            return {
                'running': self._running,
                'host': self._host,
                'port': self._port,
                'active_sessions': len(self._sessions),
            }

    def _server_loop(self):
        """服务端主循环（后台线程）"""
        while self._running:
            try:
                # 设置超时以允许检查 running 状态
                self._socket.settimeout(1.0)

                try:
                    client_socket, client_addr = self._socket.accept()
                    # 处理客户端连接
                    handler_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_addr),
                        daemon=True
                    )
                    handler_thread.start()
                except socket.timeout:
                    continue

            except Exception as e:
                if self._running:
                    print(f"[ENIP Server] Accept error: {e}")
                break

    def _handle_client(self, client_socket: socket.socket, client_addr: tuple):
        """
        处理客户端连接

        Args:
            client_socket: 客户端 socket
            client_addr: 客户端地址
        """
        try:
            client_socket.settimeout(10.0)

            while self._running:
                # 接收请求头
                header_buf = b""
                while len(header_buf) < 24:
                    chunk = client_socket.recv(24 - len(header_buf))
                    if not chunk:
                        return
                    header_buf += chunk

                # 解析请求
                parsed = parse_enip_header(header_buf)
                if not parsed:
                    continue

                command = parsed['command']
                data_len = parsed['length']
                session_handle = parsed['session_handle']

                # 接收数据部分
                data_buf = b""
                if data_len > 0:
                    while len(data_buf) < data_len:
                        chunk = client_socket.recv(min(data_len - len(data_buf), 4096))
                        if not chunk:
                            return
                        data_buf += chunk

                # 处理命令
                response = self._handle_command(command, session_handle, data_buf)

                # 发送响应
                if response:
                    client_socket.sendall(response)

        except socket.timeout:
            pass
        except Exception as e:
            if self._running:
                print(f"[ENIP Server] Client handler error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass

    def _handle_command(self, command: int, session_handle: int, data: bytes) -> Optional[bytes]:
        """
        处理 ENIP 命令

        Args:
            command: 命令码
            session_handle: 会话句柄
            data: 请求数据

        Returns:
            响应字节
        """
        if command == ENIP_COMMANDS['ListIdentity']:
            return self._build_list_identity_response()

        elif command == ENIP_COMMANDS['RegisterSession']:
            return self._handle_register_session(data)

        elif command == ENIP_COMMANDS['UnregisterSession']:
            return self._handle_unregister_session(session_handle)

        elif command == ENIP_COMMANDS['SendRRData']:
            return self._handle_send_rr_data(session_handle, data)

        elif command == ENIP_COMMANDS['NOP']:
            # NOP 响应（空数据）
            return build_enip_header(command, 0, session_handle, 0)

        else:
            # 未知命令
            return build_enip_header(command, 0, session_handle, 1)  # Status=1 (error)

    def _build_list_identity_response(self) -> bytes:
        """
        构建 ListIdentity 响应

        Returns:
            响应字节
        """
        # Identity 数据项
        identity_data = struct.pack("<HHII", 1, 0, 1, 1)  # Vendor, DeviceType, ProductCode, Status
        identity_data += struct.pack("<I", 1)  # Serial Number
        identity_data += bytes([7]) + "ENIPSim".encode('utf-8')  # Product Name (short string)

        # CPF: Null + Identity Data
        cpf = struct.pack("<IHH", 0, 0, 1)  # Interface handle, timeout, item count
        cpf += struct.pack("<HH", 0x000C, len(identity_data))  # Identity item type 0x000C
        cpf += identity_data

        header = build_enip_header(ENIP_COMMANDS['ListIdentity'], len(cpf), 0, 0)
        return header + cpf

    def _handle_register_session(self, data: bytes) -> bytes:
        """
        处理 RegisterSession 请求

        Args:
            data: 请求数据

        Returns:
            响应字节
        """
        # 生成会话句柄
        session_handle = int(time.time() * 1000) & 0xFFFFFFFF

        # 存储会话信息
        with self._lock:
            self._sessions[session_handle] = {
                'created': time.time(),
                'client_protocol_version': 1,
            }

        # 响应数据: Protocol Version + Options
        response_data = struct.pack("<HH", 0x0100, 0x0000)

        header = build_enip_header(
            ENIP_COMMANDS['RegisterSession'],
            len(response_data),
            session_handle,
            0
        )
        return header + response_data

    def _handle_unregister_session(self, session_handle: int) -> bytes:
        """
        处理 UnregisterSession 请求

        Args:
            session_handle: 会话句柄

        Returns:
            响应字节
        """
        # 移除会话
        with self._lock:
            if session_handle in self._sessions:
                del self._sessions[session_handle]

        # 响应（无数据）
        return build_enip_header(ENIP_COMMANDS['UnregisterSession'], 0, session_handle, 0)

    def _handle_send_rr_data(self, session_handle: int, data: bytes) -> bytes:
        """
        处理 SendRRData 请求

        Args:
            session_handle: 会话句柄
            data: CPF 数据

        Returns:
            响应字节
        """
        # 解析 CPF
        if len(data) < 8:
            return build_enip_header(ENIP_COMMANDS['SendRRData'], 0, session_handle, 1)

        interface_handle, timeout, item_count = struct.unpack("<IHH", data[:8])

        cip_response = None
        off = 8

        for i in range(item_count):
            if off + 4 > len(data):
                break
            item_type, item_len = struct.unpack("<HH", data[off:off+4])
            off += 4

            if item_type == CPF_ITEM_UNCONNECTED_MESSAGE:
                # 处理 CIP 请求
                cip_data = data[off:off+item_len]
                cip_response = self._handle_cip_request(cip_data)

            off += item_len

        if cip_response:
            # 构建 CPF 响应
            cpf_response = struct.pack("<IHH", 0, 0, 2)
            cpf_response += struct.pack("<HH", CPF_ITEM_NULL, 0)
            cpf_response += struct.pack("<HH", CPF_ITEM_UNCONNECTED_MESSAGE, len(cip_response))
            cpf_response += cip_response

            header = build_enip_header(
                ENIP_COMMANDS['SendRRData'],
                len(cpf_response),
                session_handle,
                0
            )
            return header + cpf_response
        else:
            return build_enip_header(ENIP_COMMANDS['SendRRData'], 0, session_handle, 1)

    def _handle_cip_request(self, cip_data: bytes) -> bytes:
        """
        处理 CIP 请求

        Args:
            cip_data: CIP 请求数据

        Returns:
            CIP 响应字节
        """
        if len(cip_data) < 2:
            return bytes([0x8E, 1])  # Error response

        service_code = cip_data[0] & 0x3F
        path_size = cip_data[1] if len(cip_data) > 1 else 0

        # 解析路径
        class_id = None
        instance = None
        attribute = None

        if len(cip_data) >= 2 + path_size * 2:
            path_data = cip_data[2:]
            for i in range(min(path_size, len(path_data) // 2)):
                seg_type = path_data[i * 2] if i * 2 < len(path_data) else 0
                seg_value = path_data[i * 2 + 1] if i * 2 + 1 < len(path_data) else 0

                if seg_type == CIP_PATH_CLASS:
                    class_id = seg_value
                elif seg_type == CIP_PATH_INSTANCE:
                    instance = seg_value
                elif seg_type == CIP_PATH_ATTRIBUTE:
                    attribute = seg_value

        # 处理服务
        if service_code == CIP_SERVICE_GET_ATTRIBUTE_SINGLE:
            return self._cip_get_attribute_single(class_id, instance, attribute)

        elif service_code == CIP_SERVICE_SET_ATTRIBUTE_SINGLE:
            # 写入数据
            write_data = cip_data[2 + path_size * 2:] if len(cip_data) > 2 + path_size * 2 else b""
            return self._cip_set_attribute_single(class_id, instance, attribute, write_data)

        elif service_code == CIP_SERVICE_GET_ATTRIBUTE_ALL:
            return self._cip_get_attribute_all(class_id, instance)

        else:
            # 不支持的服务
            return bytes([service_code | 0x80, 8])  # Service not supported

    def _cip_get_attribute_single(self, class_id: int, instance: int, attribute: int) -> bytes:
        """
        CIP Get_Attribute_Single 响应

        Args:
            class_id: 类ID
            instance: 实例号
            attribute: 属性号

        Returns:
            CIP 响应
        """
        if class_id == CIP_CLASS_IDENTITY and attribute in self._identity_data:
            value = self._identity_data[attribute]
            return bytes([CIP_SERVICE_GET_ATTRIBUTE_SINGLE | 0x80, 0]) + value
        else:
            return bytes([CIP_SERVICE_GET_ATTRIBUTE_SINGLE | 0x80, 9])  # Attribute not found

    def _cip_set_attribute_single(self, class_id: int, instance: int,
                                  attribute: int, value: bytes) -> bytes:
        """
        CIP Set_Attribute_Single 响应

        Args:
            class_id: 类ID
            instance: 实例号
            attribute: 属性号
            value: 写入值

        Returns:
            CIP 响应
        """
        if class_id == CIP_CLASS_IDENTITY and attribute in self._identity_data:
            # 更新属性值
            with self._lock:
                self._identity_data[attribute] = value[:len(self._identity_data[attribute])]
            return bytes([CIP_SERVICE_SET_ATTRIBUTE_SINGLE | 0x80, 0])
        else:
            return bytes([CIP_SERVICE_SET_ATTRIBUTE_SINGLE | 0x80, 9])

    def _cip_get_attribute_all(self, class_id: int, instance: int) -> bytes:
        """
        CIP Get_Attribute_All 响应

        Args:
            class_id: 类ID
            instance: 实例号

        Returns:
            CIP 响应
        """
        if class_id == CIP_CLASS_IDENTITY:
            # 返回所有 Identity 属性
            all_data = b""
            for attr_id in [1, 2, 3, 4, 5, 6]:
                if attr_id in self._identity_data:
                    all_data += self._identity_data[attr_id]
            return bytes([CIP_SERVICE_GET_ATTRIBUTE_ALL | 0x80, 0]) + all_data
        else:
            return bytes([CIP_SERVICE_GET_ATTRIBUTE_ALL | 0x80, 8])


# 导出的类和函数
__all__ = [
    'EnipClient',
    'EnipServer',
    'build_enip_header',
    'parse_enip_header',
    'ENIP_COMMANDS',
    'ENIP_PORT',
    'ENIP_IO_PORT',
    'CPF_ITEM_NULL',
    'CPF_ITEM_UNCONNECTED_MESSAGE',
]