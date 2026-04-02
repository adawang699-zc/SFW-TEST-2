"""
GOOSE 接收端模块 - 基于 scapy 实现
"""
try:
    from scapy.all import sniff, Ether, Packet, get_if_list
except ImportError:
    raise ImportError("请安装 scapy 库: pip install scapy")

import threading
import queue
from asn1_decoder import GOOSEDecoder
from network_utils import find_interface_by_name


class GOOSEPacket(Packet):
    """GOOSE 报文类"""
    name = "GOOSE"
    fields_desc = []
    
    def extract_payload(self):
        """提取 GOOSE PDU 载荷"""
        if self.payload:
            return bytes(self.payload)
        return b''


class GooseReceiverService:
    """GOOSE 接收服务类"""
    
    GOOSE_ETHER_TYPE = 0x88B8
    
    def __init__(self, iface="以太网", debug=False):
        # 转换网卡名称为scapy可识别的名称
        self.iface_original = iface
        self.iface = self._resolve_interface(iface)
        self.is_running = False
        self.thread = None
        self.callback = None
        self.packet_queue = queue.Queue()
        self.sniffer = None
        self.goose_packet_count = 0
    
    def _resolve_interface(self, iface_name):
        """解析网卡名称，转换为scapy可识别的名称"""
        if not iface_name:
            return None
        
        try:
            # 首先尝试使用network_utils查找
            resolved = find_interface_by_name(iface_name)
            if resolved:
                return resolved
            
            # 如果找不到，尝试直接使用（可能是GUID格式）
            if_list = get_if_list()
            if iface_name in if_list:
                return iface_name
            
            # 尝试部分匹配（不区分大小写）
            iface_lower = iface_name.lower()
            for iface in if_list:
                if iface.lower() == iface_lower or iface.lower().startswith(iface_lower):
                    return iface
            
            # 如果都找不到，返回原始名称（让scapy自己处理）
            return iface_name
        except Exception:
            # 如果出错，返回原始名称
            return iface_name
    
    def set_callback(self, callback):
        """设置接收回调函数"""
        self.callback = callback
    
    def _packet_handler(self, packet):
        """报文处理函数"""
        try:
            # 检查是否有Ether层
            if not packet.haslayer(Ether):
                return
            
            # 检查以太网类型
            if packet[Ether].type != self.GOOSE_ETHER_TYPE:
                return
            
            # 统计收到的GOOSE报文数量
            self.goose_packet_count += 1
            
            # 创建简单的报文信息（不解析内容）
            packet_info = {
                'src_mac': packet[Ether].src,
                'dst_mac': packet[Ether].dst,
                'count': self.goose_packet_count
            }
            
            self.packet_queue.put(packet_info)
        except Exception as e:
            # 只记录严重错误
            if self.callback:
                try:
                    self.callback({"error": f"Packet error: {str(e)}"})
                except:
                    pass
    
    def start(self):
        """启动接收"""
        if self.is_running:
            return False
        
        try:
            self.is_running = True
            # 启动嗅探线程
            self.thread = threading.Thread(target=self._sniff_loop, daemon=True)
            self.thread.start()
            # 启动处理线程
            self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
            self.process_thread.start()
            return True
        except Exception as e:
            self.is_running = False
            return False
    
    def _sniff_loop(self):
        """嗅探循环"""
        try:
            # 验证网卡是否可用
            if not self.iface:
                if self.callback:
                    self.callback({"error": f"无效的网卡名称: {self.iface_original}"})
                return
            
            # 发送启动成功消息
            if self.callback:
                self.callback({"info": f"开始监听网卡: {self.iface_original}"})
            
            # 过滤 GOOSE 报文 (以太网类型 0x88B8)
            filter_str = f"ether proto {self.GOOSE_ETHER_TYPE}"
            
            try:
                sniff(
                    iface=self.iface,
                    prn=self._packet_handler,
                    filter=filter_str,
                    stop_filter=lambda x: not self.is_running,
                    store=0
                )
            except Exception:
                # 如果过滤失败，不使用过滤（捕获所有报文，在_handler中过滤）
                sniff(
                    iface=self.iface,
                    prn=self._packet_handler,
                    stop_filter=lambda x: not self.is_running,
                    store=0
                )
        except OSError as e:
            # 网卡相关错误
            error_msg = f"网卡错误: {str(e)}"
            if "没有这样的设备" in str(e) or "No such device" in str(e):
                error_msg = f"网卡不存在或无法访问: {self.iface_original}"
            if self.callback:
                self.callback({"error": error_msg})
        except Exception as e:
            if self.callback:
                self.callback({"error": f"Sniff错误: {str(e)}"})
    
    def _process_loop(self):
        """处理循环"""
        while self.is_running:
            try:
                # 从队列获取报文（超时 1 秒）
                try:
                    packet_info = self.packet_queue.get(timeout=1)
                    if self.callback:
                        self.callback(packet_info)
                except queue.Empty:
                    continue
            except Exception as e:
                if self.callback:
                    self.callback({"error": str(e)})
                break
    
    def stop(self):
        """停止接收"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        if hasattr(self, 'process_thread') and self.process_thread:
            self.process_thread.join(timeout=2)
