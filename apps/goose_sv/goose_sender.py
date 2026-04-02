"""
GOOSE 发送端模块 - 基于 scapy 实现
"""
try:
    from scapy.all import Ether, sendp, get_if_hwaddr, Raw
except ImportError:
    raise ImportError("请安装 scapy 库: pip install scapy")

import threading
import time
import platform
from asn1_encoder import IEC61850Encoder
from network_utils import find_interface_by_name, validate_interface


class GooseSenderService:
    """GOOSE 发送服务类"""
    
    # GOOSE 组播 MAC 地址范围: 01-0C-CD-01-00-00 到 01-0C-CD-01-01-FF
    GOOSE_MULTICAST_MAC = "01:0C:CD:01:00:01"
    GOOSE_ETHER_TYPE = 0x88B8
    
    def __init__(self, iface="以太网"):
        # 尝试查找可用的网卡接口
        self.iface = self._resolve_interface(iface)
        self.is_running = False
        self.thread = None
        self.config = {
            "appid": 0x100,
            "gocb_ref": "IED1/LLN0$GO$GSE1",
            "datset": "IED1/LLN0$DataSet1",
            "stnum": 1,
            "sqnum": 0,
            "timeallowedtolive": 2000,
            "data": {
                "Switch_1": True,
                "Switch_2": False
            }
        }
        self.callback = None
        self.src_mac = None
        self.packet_count = 0  # 报文计数器
    
    def _resolve_interface(self, iface_name):
        """解析网卡接口名称"""
        if not iface_name:
            return None
        
        # 首先尝试直接使用
        is_valid, msg = validate_interface(iface_name)
        if is_valid:
            return iface_name
        
        # 尝试查找替代接口
        found_iface = find_interface_by_name(iface_name)
        if found_iface:
            return found_iface
        
        # 如果都失败，返回原始名称（让后续错误处理）
        return iface_name
    
    def _get_src_mac(self):
        """获取源 MAC 地址"""
        try:
            self.src_mac = get_if_hwaddr(self.iface)
            return self.src_mac
        except Exception:
            # 如果获取失败，使用默认 MAC
            self.src_mac = "00:00:00:00:00:01"
            return self.src_mac
    
    def set_config(self, config):
        """设置配置"""
        self.config.update(config)
    
    def set_callback(self, callback):
        """设置发送回调函数"""
        self.callback = callback
    
    def start(self):
        """启动发送"""
        if self.is_running:
            return False
        
        try:
            # 验证网卡
            if not self.iface:
                if self.callback:
                    self.callback({"error": "网卡名称未设置"})
                return False
            
            is_valid, msg = validate_interface(self.iface)
            if not is_valid:
                if self.callback:
                    self.callback({"error": f"网卡验证失败: {msg}"})
                return False
            
            # 获取源 MAC 地址
            self._get_src_mac()
            self.is_running = True
            self.thread = threading.Thread(target=self._send_loop, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            if self.callback:
                self.callback({"error": f"启动失败: {str(e)}"})
            return False
    
    def stop(self):
        """停止发送"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def get_packet_count(self):
        """获取已发送报文数量"""
        return self.packet_count
    
    def reset_packet_count(self):
        """重置报文计数"""
        self.packet_count = 0
    
    def _send_loop(self):
        """发送循环"""
        # 首次发送时打印详细字段信息
        first_send = True
        
        while self.is_running:
            try:
                # 首次发送时打印详细调试信息
                # if first_send:
                #     from goose_debug import debug_goose_packet
                #     debug_goose_packet(self.config)
                #     first_send = False
                
                # 编码完整的 GOOSE 报文（包含头部和 PDU）
                goose_packet = IEC61850Encoder.encode_goose_packet(self.config)
                
                # 详细验证
                if not goose_packet:
                    if self.callback:
                        self.callback({"error": "GOOSE packet is None"})
                    break
                
                if len(goose_packet) == 0:
                    if self.callback:
                        self.callback({"error": "GOOSE packet is empty (0 bytes)"})
                    break
                
                # 验证报文长度（至少要有头部 8 字节 + 至少一些 PDU 数据）
                if len(goose_packet) < 8:
                    if self.callback:
                        self.callback({"error": f"GOOSE packet too short: {len(goose_packet)} bytes (minimum 8)"})
                    break
                
                # 验证 PDU 部分不为空（跳过头部 8 字节）
                pdu_data = goose_packet[8:]
                if len(pdu_data) == 0:
                    if self.callback:
                        self.callback({"error": "GOOSE PDU is empty (0 bytes after header)"})
                    break
                
                # 验证头部长度字段
                import struct
                appid, length, reserved1, reserved2 = struct.unpack('>HHHH', goose_packet[:8])
                expected_length = 4 + len(pdu_data)  # Reserved1(2) + Reserved2(2) + PDU
                if length != expected_length:
                    if self.callback:
                        self.callback({"error": f"GOOSE length field mismatch: header says {length}, expected {expected_length}"})
                    break
                
                # 构造以太网帧
                # 目标 MAC: GOOSE 组播地址
                # 源 MAC: 本地网卡 MAC
                # 以太网类型: 0x88B8 (GOOSE)
                frame = Ether(
                    dst=self.GOOSE_MULTICAST_MAC,
                    src=self.src_mac,
                    type=self.GOOSE_ETHER_TYPE
                ) / Raw(load=goose_packet)
                
                # 发送报文
                sendp(frame, iface=self.iface, verbose=0)
                
                # 增加报文计数
                self.packet_count += 1
                
                if self.callback:
                    self.callback(self.config.copy())
                
                # 顺序号递增
                self.config["sqnum"] += 1
                time.sleep(0.5)  # GOOSE 默认发送间隔 0.5 秒
                
            except Exception as e:
                if self.callback:
                    self.callback({"error": f"GOOSE send error: {str(e)}"})
                import traceback
                traceback.print_exc()
                break
