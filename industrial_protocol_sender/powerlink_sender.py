# -*- coding: utf-8 -*-
"""
POWERLINK 发送端模块 - 基于 scapy 实现
"""
import time
import threading
import warnings
warnings.filterwarnings("ignore", category=Warning)
try:
    from scapy.all import Ether, sendp, Packet, ByteField, ShortField, IntField, StrField, bind_layers
except ImportError:
    raise ImportError("请安装 scapy 库: pip install scapy")
from network_utils import find_interface_by_name, validate_interface


class POWERLINK_SoC(Packet):
    name = "POWERLINK SoC"
    fields_desc = [
        ByteField("SID", 0x01), ByteField("DA", 0xFF), ByteField("SA", 0xF0),
        ShortField("SyncCounter", 0x6000), ByteField("Reserved1", 0x00), ByteField("Reserved2", 0x00),
        ByteField("Reserved3", 0x00), ByteField("Reserved4", 0x00),
        IntField("Timestamp", 0x0000bebc), IntField("CycleControl", 0x200400d0),
        StrField("Reserved5", b"\x30\x00" + b"\x00" * 28)
    ]


class POWERLINK_PReq(Packet):
    name = "POWERLINK PReq"
    fields_desc = [
        ByteField("SID", 0x03), ByteField("DA", 0x11), ByteField("SA", 0xF0),
        ByteField("Reserved", 0x00), ByteField("Flags", 0x00), ByteField("FLS_SLS", 0x00),
        ByteField("PDOVersion", 0x02), ByteField("Unparsed", 0x00), ShortField("Size", 0x0000),
        StrField("PDOData", b"\xaa" * 8 + b"\x00" * 16 + b"\xaa" * 1 + b"\x00" * 12)
    ]


class POWERLINK_PRes(Packet):
    name = "POWERLINK PRes"
    fields_desc = [
        ByteField("SID", 0x04), ByteField("DA", 0x11), ByteField("SA", 0xF0),
        ByteField("NMTStatus", 0x6d), ByteField("Flags", 0x00), ByteField("FLS_SLS_PR_RS", 0x00),
        ByteField("Version", 0x02), ByteField("Reserved", 0x00), ShortField("Size", 0x2000),
        StrField("PDOData", b"\xbb" * 8 + b"\x00" * 16 + b"\xbb" * 1 + b"\x00" * 12)
    ]


class POWERLINK_SoA(Packet):
    name = "POWERLINK SoA"
    fields_desc = [
        ByteField("SID", 0x05), ByteField("DA", 0xFF), ByteField("SA", 0xF0),
        ByteField("NMTStatus", 0x6d), ByteField("Flags", 0x00), ByteField("FLS_SLS_PR_RS", 0x00),
        ByteField("Version", 0x02), ByteField("Reserved", 0x00), ShortField("Size", 0x2000),
        StrField("Data", b"\xcc" * 8 + b"\x00" * 24)
    ]


class POWERLINK_ASnd(Packet):
    name = "POWERLINK ASnd"
    fields_desc = [
        ByteField("SID", 0x06), ByteField("DA", 0xFF), ByteField("SA", 0xF0),
        ByteField("NMTStatus", 0x6d), ByteField("Flags", 0x00), ByteField("Type", 0x01),
        ByteField("Version", 0x02), ByteField("Reserved", 0x00), ShortField("Size", 0x1000),
        StrField("Data", b"\xdd" * 8 + b"\x00" * 24)
    ]


class POWERLINK_AMNI(Packet):
    name = "POWERLINK AMNI"
    fields_desc = [
        ByteField("SID", 0x07), ByteField("DA", 0xFF), ByteField("SA", 0xF0),
        ByteField("NodeID", 0x11), ByteField("Flags", 0x00), ByteField("Code", 0x00),
        ByteField("Version", 0x02), ByteField("Reserved", 0x00), ShortField("Size", 0x0800),
        StrField("Data", b"\xee" * 8 + b"\x00" * 24)
    ]


for _p in (POWERLINK_SoC, POWERLINK_PReq, POWERLINK_PRes, POWERLINK_SoA, POWERLINK_ASnd, POWERLINK_AMNI):
    bind_layers(Ether, _p, type=0x88AB)

SERVICE_TYPE_MAP = {
    "SoC": POWERLINK_SoC, "Preq": POWERLINK_PReq, "Pres": POWERLINK_PRes,
    "SoA": POWERLINK_SoA, "ASnd": POWERLINK_ASnd, "AMNI": POWERLINK_AMNI,
}


def _clamp_node(v):
    try:
        return max(0, min(255, int(v)))
    except (TypeError, ValueError):
        return 0


def send_powerlink_packet(iface, pkt_class, dst_mac, src_mac, sa, da):
    sa_byte = _clamp_node(sa)
    da_byte = _clamp_node(da)
    frame = Ether(dst=dst_mac, src=src_mac, type=0x88AB) / pkt_class()
    pl = frame.getlayer(1)
    if pl is not None:
        pl.SA, pl.DA = sa_byte, da_byte
    sendp(frame, iface=iface, verbose=0)
    time.sleep(0.05)
    return frame


class PowerlinkSenderService:
    def __init__(self, iface="以太网"):
        self.iface = self._resolve_interface(iface)
        self.is_running = False
        self.thread = None
        self.service_types = ["SoC"]
        self.sa, self.da = 240, 17
        self.dst_mac = "01:11:1e:00:00:01"
        self.src_mac = "00:50:c2:31:3f:dd"
        self.packet_count = 0
        self.callback = None

    def _resolve_interface(self, iface_name):
        if not iface_name:
            return None
        is_valid, _ = validate_interface(iface_name)
        if is_valid:
            return iface_name
        return find_interface_by_name(iface_name) or iface_name

    def set_config(self, config):
        self.service_types = config.get("service_types", ["SoC"])
        self.sa = _clamp_node(config.get("sa", 240))
        self.da = _clamp_node(config.get("da", 17))
        self.dst_mac = config.get("dst_mac", "01:11:1e:00:00:01")
        self.src_mac = config.get("src_mac", "00:50:c2:31:3f:dd")

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
            allowed = [t for t in self.service_types if t in SERVICE_TYPE_MAP]
            if not allowed:
                if self.callback:
                    self.callback({"error": "请至少选择一种服务类型（SoC/Preq/Pres/SoA/ASnd/AMNI）"})
                return False
            self.service_types = allowed
            self.is_running = True
            self.thread = threading.Thread(target=self._send_loop, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            if self.callback:
                self.callback({"error": str(e)})
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
        idx, types, n = 0, self.service_types, len(self.service_types)
        while self.is_running and n:
            name = types[idx % n]
            idx += 1
            pkt_class = SERVICE_TYPE_MAP.get(name)
            if pkt_class is None:
                continue
            try:
                send_powerlink_packet(self.iface, pkt_class, self.dst_mac, self.src_mac, self.sa, self.da)
                self.packet_count += 1
                if self.callback:
                    self.callback({"service_type": name, "count": self.packet_count})
            except Exception as e:
                if self.callback:
                    self.callback({"error": str(e)})
                break
