# -*- coding: utf-8 -*-
"""
EtherCAT 发送端模块 - 基于 scapy 实现
"""
import struct
import time
import threading
try:
    from scapy.all import Ether, sendp, Raw, BitField, ByteField, ShortField, StrLenField, Packet
except ImportError:
    raise ImportError("请安装 scapy 库: pip install scapy")
from network_utils import find_interface_by_name, validate_interface


class ECAT_Header(Packet):
    name = "EtherCAT Header"
    fields_desc = [
        BitField("type", 0x01, 4),
        BitField("reserved", 0, 1),
        BitField("len", 0, 11)
    ]
    def post_build(self, pkt, pay):
        val = (self.type << 12) | (self.reserved << 11) | self.len
        hex_16bit = struct.pack(">H", val)
        return hex_16bit[::-1] + pay


class ECAT_Datagram(Packet):
    name = "EtherCAT Datagram"
    fields_desc = [
        ByteField("cmd", 0x01),
        ByteField("index", 0x00),
        ShortField("dlen", 0x00),
        ShortField("adp", 0x0001),
        ShortField("ado", 0x0130),
        ShortField("cnt", 0x0000),
        StrLenField("data", "", length_from=lambda pkt: pkt.dlen),
        ShortField("wkc", 0x0000)
    ]


try:
    from scapy.all import bind_layers
    bind_layers(Ether, ECAT_Header, type=0x88A4)
    bind_layers(ECAT_Header, ECAT_Datagram)
except Exception:
    pass

ECAT_CMD_NAMES = {
    0x00: "NOP", 0x01: "APRD", 0x02: "APWR", 0x03: "APRW", 0x04: "FPRD", 0x05: "FPWR",
    0x06: "FPRW", 0x08: "BRD", 0x09: "BWR", 0x0A: "LRD", 0x0B: "LWR", 0x0C: "LRW",
    0x0D: "LRMW", 0x0E: "ARMW", 0x0F: "FRMW"
}


def _default_params(cmd_code, read_len=2):
    if cmd_code == 0x00:
        return 0, b"", 0x0001, 0x0130
    if cmd_code in (0x01, 0x04, 0x08, 0x0A):
        return read_len, b"", 0x0001, 0x0230 if read_len == 2 else (0x0430 if read_len == 4 else 0x0230)
    if cmd_code in (0x0D, 0x0E, 0x0F):
        return 4, b"\xFF\x00\x00\x55", 0x0001, 0x0430
    if cmd_code in (0x02, 0x09, 0x0B):
        return 2, b"\x11\x22", 0x0001, 0x0230
    if cmd_code in (0x03, 0x06, 0x0C):
        return 2, b"\x33\x44", 0x0001, 0x0230
    if cmd_code == 0x05:
        return 2, b"\x00\x01", 0x0000, 0x0230
    return read_len, b"", 0x0001, 0x0230


def send_ethercat_packet(data_unit_type, cmd_code, iface, read_len=2, send_data=None, adp=None, ado=None, dst_mac="01:01:01:01:01:01"):
    dlen_val, default_data, default_adp, default_ado = _default_params(cmd_code, read_len)
    if send_data is not None:
        dlen_val = len(send_data)
        default_data = send_data
    if adp is not None:
        default_adp = adp
    if ado is not None:
        default_ado = ado
    datagram_total_len = 10 + dlen_val + 2
    if dlen_val == 0:
        default_ado = 0x0030
    elif dlen_val == 1:
        default_ado = 0x0130
    elif dlen_val == 2:
        default_ado = 0x0230
    elif dlen_val == 4:
        default_ado = 0x0430
    ethercat_pkt = (
        Ether(dst=dst_mac, type=0x88A4)
        / ECAT_Header(type=data_unit_type, reserved=0, len=datagram_total_len)
        / ECAT_Datagram(cmd=cmd_code, dlen=dlen_val, adp=default_adp, ado=default_ado, data=default_data)
    )
    sendp(ethercat_pkt, iface=iface, verbose=0)
    time.sleep(0.1)
    return ethercat_pkt


class EthercatSenderService:
    def __init__(self, iface="以太网"):
        self.iface = self._resolve_interface(iface)
        self.is_running = False
        self.thread = None
        self.data_unit_type = 1
        self.command_codes = [0x00]
        self.dst_mac = "01:01:01:01:01:01"
        self.read_len = 2
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
        self.data_unit_type = config.get("data_unit_type", 1)
        self.command_codes = config.get("command_codes", [0x00])
        self.dst_mac = config.get("dst_mac", "01:01:01:01:01:01")
        self.read_len = config.get("read_len", 2)

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
            if not self.command_codes:
                if self.callback:
                    self.callback({"error": "请至少选择一种命令码"})
                return False
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
        idx, cmd_list, n = 0, self.command_codes, len(self.command_codes)
        while self.is_running and n:
            cmd_code = cmd_list[idx % n]
            idx += 1
            try:
                send_ethercat_packet(self.data_unit_type, cmd_code, self.iface, read_len=self.read_len, dst_mac=self.dst_mac)
                self.packet_count += 1
                if self.callback:
                    self.callback({"cmd": cmd_code, "count": self.packet_count})
            except Exception as e:
                if self.callback:
                    self.callback({"error": str(e)})
                break
