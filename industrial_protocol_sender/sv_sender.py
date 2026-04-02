"""
SV 发送端模块 - 基于 scapy 实现
"""
try:
    from scapy.all import Ether, sendp, get_if_hwaddr, Raw
except ImportError:
    raise ImportError("请安装 scapy 库: pip install scapy")

import threading
import time
from asn1_encoder import IEC61850Encoder
from network_utils import find_interface_by_name, validate_interface


class SVSenderService:
    """SV 发送服务类"""
    
    SV_MULTICAST_MAC = "01:0C:CD:04:00:01"
    SV_ETHER_TYPE = 0x88BA
    
    def __init__(self, iface="以太网"):
        self.iface = self._resolve_interface(iface)
        self.is_running = False
        self.thread = None
        self.config = {
            "appid": 0x4019,
            "svid": "SV_Line1",
            "confrev": 1,
            "smpcnt": 0,
            "smpsynch": True,
            "samples": {"Voltage_A": 220.1, "Voltage_B": 219.8, "Voltage_C": 220.3, "Current_A": 10.2, "Current_B": 10.5, "Current_C": 10.1}
        }
        self.callback = None
        self.src_mac = None
        self.packet_count = 0
    
    def _resolve_interface(self, iface_name):
        if not iface_name:
            return None
        is_valid, _ = validate_interface(iface_name)
        if is_valid:
            return iface_name
        found = find_interface_by_name(iface_name)
        return found if found else iface_name
    
    def _get_src_mac(self):
        try:
            self.src_mac = get_if_hwaddr(self.iface)
            return self.src_mac
        except Exception:
            self.src_mac = "00:00:00:00:00:01"
            return self.src_mac
    
    def set_config(self, config):
        self.config.update(config)
    
    def set_callback(self, callback):
        self.callback = callback
    
    def start(self):
        if self.is_running:
            return False
        try:
            if not self.iface:
                if self.callback:
                    self.callback({"error": "网卡名称未设置"})
                return False
            is_valid, msg = validate_interface(self.iface)
            if not is_valid:
                if self.callback:
                    self.callback({"error": f"网卡验证失败: {msg}"})
                return False
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
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def get_packet_count(self):
        return self.packet_count
    
    def reset_packet_count(self):
        self.packet_count = 0
    
    def _send_loop(self):
        while self.is_running:
            try:
                sv_packet = IEC61850Encoder.encode_sv_packet(self.config)
                if not sv_packet or len(sv_packet) < 8:
                    if self.callback:
                        self.callback({"error": "SV packet invalid"})
                    break
                frame = Ether(dst=self.SV_MULTICAST_MAC, src=self.src_mac, type=self.SV_ETHER_TYPE) / Raw(load=sv_packet)
                sendp(frame, iface=self.iface, verbose=0)
                self.packet_count += 1
                if self.callback:
                    self.callback(self.config.copy())
                self.config["smpcnt"] += 1
                time.sleep(0.5)
            except Exception as e:
                if self.callback:
                    self.callback({"error": f"SV send error: {str(e)}"})
                break
