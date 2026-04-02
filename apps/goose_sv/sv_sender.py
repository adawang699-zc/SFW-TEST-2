"""
SV 发送端模块 - 基于 scapy 实现
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


class SVSenderService:
    """SV 发送服务类"""
    
    # SV 组播 MAC 地址范围: 01-0C-CD-04-00-00 到 01-0C-CD-04-01-FF
    SV_MULTICAST_MAC = "01:0C:CD:04:00:01"
    SV_ETHER_TYPE = 0x88BA
    
    def __init__(self, iface="以太网"):
        # 尝试查找可用的网卡接口
        self.iface = self._resolve_interface(iface)
        self.is_running = False
        self.thread = None
        self.config = {
            "appid": 0x4019,  # APPID范围：0x4000~0x7FFF
            "svid": "SV_Line1",  # 前端传入，此处为默认
            "confrev": 1,  # 配置版本号，默认 00000001
            "smpcnt": 0,
            "smpsynch": True,  # 同步标志，默认 1
            "samples": {
                "Voltage_A": 220.1,
                "Voltage_B": 219.8,
                "Voltage_C": 220.3,
                "Current_A": 10.2,
                "Current_B": 10.5,
                "Current_C": 10.1
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
        while self.is_running:
            try:
                # 编码完整的 SV 报文（包含头部和 PDU）
                sv_packet = IEC61850Encoder.encode_sv_packet(self.config)
                
                # 详细验证
                if not sv_packet:
                    if self.callback:
                        self.callback({"error": "SV packet is None"})
                    break
                
                if len(sv_packet) == 0:
                    if self.callback:
                        self.callback({"error": "SV packet is empty (0 bytes)"})
                    break
                
                # 验证报文长度（至少要有头部 8 字节 + 至少一些 PDU 数据）
                if len(sv_packet) < 8:
                    if self.callback:
                        self.callback({"error": f"SV packet too short: {len(sv_packet)} bytes (minimum 8)"})
                    break
                
                # 验证 PDU 部分不为空（跳过头部 8 字节）
                pdu_data = sv_packet[8:]
                if len(pdu_data) == 0:
                    if self.callback:
                        self.callback({"error": "SV PDU is empty (0 bytes after header)"})
                    break
                
                # 验证头部长度字段
                import struct
                appid, length, reserved1, reserved2 = struct.unpack('>HHHH', sv_packet[:8])
                expected_length = 4 + len(pdu_data)  # Reserved1(2) + Reserved2(2) + PDU
                if length != expected_length:
                    if self.callback:
                        self.callback({"error": f"SV length field mismatch: header says {length}, expected {expected_length}"})
                    break
                
                # 构造以太网帧
                # 目标 MAC: SV 组播地址
                # 源 MAC: 本地网卡 MAC
                # 以太网类型: 0x88BA (SV)
                frame = Ether(
                    dst=self.SV_MULTICAST_MAC,
                    src=self.src_mac,
                    type=self.SV_ETHER_TYPE
                ) / Raw(load=sv_packet)
                
                # 发送报文
                sendp(frame, iface=self.iface, verbose=0)
                
                # 增加报文计数
                self.packet_count += 1
                
                if self.callback:
                    self.callback(self.config.copy())
                
                # 采样数递增
                self.config["smpcnt"] += 1
                # SV 发送间隔与 GOOSE 一致（0.5秒）
                time.sleep(0.5)
                
            except Exception as e:
                if self.callback:
                    self.callback({"error": f"SV send error: {str(e)}"})
                import traceback
                traceback.print_exc()
                break
