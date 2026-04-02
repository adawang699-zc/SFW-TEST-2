# -*- coding: utf-8 -*-
"""
工控协议报文发送器 - 统一 GUI
支持：GOOSE、SV、EtherCAT、POWERLINK、PNRT-DCP
选择网卡 → 选择协议类型及选项 → 发送 / 停止
兼容 Win7 / Win10，使用 tkinter。
"""
import sys
import os
import json
import threading

# 确保当前目录在 path 中，便于打包 exe 后同目录模块导入
if getattr(sys, 'frozen', False):
    _base = os.path.dirname(sys.executable)
else:
    _base = os.path.dirname(os.path.abspath(__file__))
if _base not in sys.path:
    sys.path.insert(0, _base)
os.chdir(_base)

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from network_utils import get_windows_interfaces
from goose_sender import GooseSenderService
from sv_sender import SVSenderService
from ethercat_sender import EthercatSenderService, ECAT_CMD_NAMES
from powerlink_sender import PowerlinkSenderService, SERVICE_TYPE_MAP as POWERLINK_SERVICE_MAP
from dcp_sender import DcpSenderService, FRAME_ID_MAP, SERVICE_ID_MAP, OPTION_MAP, get_suboptions_for_option

PROTOCOLS = ["GOOSE", "SV", "EtherCAT", "POWERLINK", "PNRT-DCP"]


class ProtocolSenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("工控协议报文发送器 (GOOSE / SV / EtherCAT / POWERLINK / PNRT-DCP)")
        self.root.geometry("720x620")
        self.root.minsize(600, 500)

        self.sender = None
        self.iface_var = tk.StringVar(value="")
        self.protocol_var = tk.StringVar(value=PROTOCOLS[0])
        self.options_frame = None
        self._option_widgets = {}

        self._build_ui()
        self.root.after(150, self._load_interfaces)

    def _build_ui(self):
        # 顶部：网卡
        top = ttk.LabelFrame(self.root, text="网卡", padding=8)
        top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(top, text="选择网卡:").pack(side=tk.LEFT, padx=(0, 6))
        self.iface_combo = ttk.Combobox(top, textvariable=self.iface_var, width=42, state="readonly")
        self.iface_combo.pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="刷新", command=self._refresh_interfaces).pack(side=tk.LEFT, padx=6)

        # 协议类型
        proto_frame = ttk.LabelFrame(self.root, text="协议类型", padding=8)
        proto_frame.pack(fill=tk.X, padx=8, pady=6)
        for p in PROTOCOLS:
            ttk.Radiobutton(proto_frame, text=p, variable=self.protocol_var, value=p, command=self._on_protocol_change).pack(side=tk.LEFT, padx=10)

        # 协议选项区域（动态切换）
        self.options_container = ttk.LabelFrame(self.root, text="协议选项", padding=8)
        self.options_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # 发送控制
        ctrl = ttk.Frame(self.root, padding=8)
        ctrl.pack(fill=tk.X, padx=8, pady=6)
        self.btn_start = ttk.Button(ctrl, text="开始发送", command=self._start)
        self.btn_start.pack(side=tk.LEFT, padx=4)
        self.btn_stop = ttk.Button(ctrl, text="停止发送", command=self._stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=4)
        self.lbl_status = ttk.Label(ctrl, text="未发送")
        self.lbl_status.pack(side=tk.LEFT, padx=12)

        # 日志
        log_frame = ttk.LabelFrame(self.root, text="日志", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=80, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self._on_protocol_change()

    def _log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _load_interfaces(self):
        def do():
            try:
                ifaces = get_windows_interfaces()
                self.root.after(0, lambda: self._set_interfaces(ifaces))
            except Exception:
                pass
        threading.Thread(target=do, daemon=True).start()

    def _set_interfaces(self, ifaces):
        valid = [x for x in (ifaces or []) if x and str(x).strip()]
        self.iface_combo["values"] = valid
        if valid and not self.iface_var.get():
            self.iface_var.set(valid[0])

    def _refresh_interfaces(self):
        self.iface_combo["values"] = ["正在加载..."]
        def do():
            try:
                ifaces = get_windows_interfaces()
                self.root.after(0, lambda: self._set_interfaces(ifaces))
                self.root.after(0, lambda: self._log("已刷新网卡列表"))
            except Exception as e:
                self.root.after(0, lambda: self._log("刷新失败: " + str(e)))
        threading.Thread(target=do, daemon=True).start()

    def _on_protocol_change(self):
        for w in self.options_container.winfo_children():
            w.destroy()
        self._option_widgets.clear()
        proto = self.protocol_var.get()
        f = ttk.Frame(self.options_container)
        f.pack(fill=tk.BOTH, expand=True)

        if proto == "GOOSE":
            self._build_goose_options(f)
        elif proto == "SV":
            self._build_sv_options(f)
        elif proto == "EtherCAT":
            self._build_ethercat_options(f)
        elif proto == "POWERLINK":
            self._build_powerlink_options(f)
        elif proto == "PNRT-DCP":
            self._build_dcp_options(f)

    def _build_goose_options(self, parent):
        ttk.Label(parent, text="AppID:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        v = tk.StringVar(value="256")
        self._option_widgets["goose_appid"] = v
        ttk.Entry(parent, textvariable=v, width=12).grid(row=0, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(parent, text="GOCB参考:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        v2 = tk.StringVar(value="IED1/LLN0$GO$GSE1")
        self._option_widgets["goose_gocb"] = v2
        ttk.Entry(parent, textvariable=v2, width=36).grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(parent, text="数据集:").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        v3 = tk.StringVar(value="IED1/LLN0$DataSet1")
        self._option_widgets["goose_datset"] = v3
        ttk.Entry(parent, textvariable=v3, width=36).grid(row=2, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(parent, text="数据(JSON):").grid(row=3, column=0, sticky=tk.NW, padx=4, pady=2)
        txt = scrolledtext.ScrolledText(parent, height=3, width=40)
        txt.insert("1.0", '{"Switch_1": true, "Switch_2": false}')
        txt.grid(row=3, column=1, sticky=tk.W, padx=4, pady=2)
        self._option_widgets["goose_data"] = txt

    def _build_sv_options(self, parent):
        ttk.Label(parent, text="AppID (16384~32767):").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        v = tk.StringVar(value="16409")
        self._option_widgets["sv_appid"] = v
        ttk.Entry(parent, textvariable=v, width=12).grid(row=0, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(parent, text="svID:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        v2 = tk.StringVar(value="SV_Line1")
        self._option_widgets["sv_svid"] = v2
        ttk.Entry(parent, textvariable=v2, width=36).grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(parent, text="采样值(JSON):").grid(row=2, column=0, sticky=tk.NW, padx=4, pady=2)
        txt = scrolledtext.ScrolledText(parent, height=3, width=40)
        txt.insert("1.0", '{"Voltage_A": 220.1, "Voltage_B": 219.8, "Voltage_C": 220.3, "Current_A": 10.2, "Current_B": 10.5, "Current_C": 10.1}')
        txt.grid(row=2, column=1, sticky=tk.W, padx=4, pady=2)
        self._option_widgets["sv_samples"] = txt

    def _build_ethercat_options(self, parent):
        ttk.Label(parent, text="命令码(可多选):").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        cmd_names = list(ECAT_CMD_NAMES.items())[:12]
        f2 = ttk.Frame(parent)
        f2.grid(row=0, column=1, sticky=tk.W, padx=4, pady=2)
        self._option_widgets["ecat_cmds"] = {}
        for i, (code, name) in enumerate(cmd_names):
            var = tk.BooleanVar(value=(code == 0x00))
            self._option_widgets["ecat_cmds"][code] = var
            ttk.Checkbutton(f2, text=f"0x{code:02X} {name}", variable=var).grid(row=i // 4, column=i % 4, sticky=tk.W, padx=4)
        ttk.Label(parent, text="目标MAC:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        v = tk.StringVar(value="01:01:01:01:01:01")
        self._option_widgets["ecat_dst_mac"] = v
        ttk.Entry(parent, textvariable=v, width=24).grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)

    def _build_powerlink_options(self, parent):
        ttk.Label(parent, text="服务类型(可多选):").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        f2 = ttk.Frame(parent)
        f2.grid(row=0, column=1, sticky=tk.W, padx=4, pady=2)
        self._option_widgets["pl_types"] = {}
        for i, name in enumerate(POWERLINK_SERVICE_MAP):
            var = tk.BooleanVar(value=(name == "SoC"))
            self._option_widgets["pl_types"][name] = var
            ttk.Checkbutton(f2, text=name, variable=var).pack(side=tk.LEFT, padx=6)
        ttk.Label(parent, text="SA:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        v_sa = tk.StringVar(value="240")
        self._option_widgets["pl_sa"] = v_sa
        ttk.Entry(parent, textvariable=v_sa, width=8).grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(parent, text="DA:").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        v_da = tk.StringVar(value="17")
        self._option_widgets["pl_da"] = v_da
        ttk.Entry(parent, textvariable=v_da, width=8).grid(row=2, column=1, sticky=tk.W, padx=4, pady=2)

    def _build_dcp_options(self, parent):
        ttk.Label(parent, text="帧类型:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        v_frame = tk.StringVar(value="GETORSET")
        self._option_widgets["dcp_frame"] = v_frame
        ttk.Combobox(parent, textvariable=v_frame, values=list(FRAME_ID_MAP), width=14, state="readonly").grid(row=0, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(parent, text="服务码:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        v_svc = tk.StringVar(value="GET")
        self._option_widgets["dcp_service"] = v_svc
        ttk.Combobox(parent, textvariable=v_svc, values=list(SERVICE_ID_MAP), width=14, state="readonly").grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Label(parent, text="Option:").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        v_opt = tk.StringVar(value="IP")
        self._option_widgets["dcp_option"] = v_opt
        cb_opt = ttk.Combobox(parent, textvariable=v_opt, values=list(OPTION_MAP), width=18, state="readonly")
        cb_opt.grid(row=2, column=1, sticky=tk.W, padx=4, pady=2)
        cb_opt.bind("<<ComboboxSelected>>", lambda e: self._dcp_refresh_suboptions())
        ttk.Label(parent, text="Suboption (根据 Option 显示，可多选):").grid(row=3, column=0, sticky=tk.NW, padx=4, pady=4)
        wrap = ttk.Frame(parent)
        wrap.grid(row=3, column=1, sticky=tk.W, padx=4, pady=4)
        btn_row = ttk.Frame(wrap)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="全选", command=self._dcp_suboption_select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="取消全选", command=self._dcp_suboption_select_none).pack(side=tk.LEFT, padx=2)
        self._option_widgets["dcp_suboption_frame"] = f_sub = ttk.Frame(wrap)
        f_sub.pack(fill=tk.X, pady=4)
        self._option_widgets["dcp_suboption_vars"] = {}  # sub_value -> BooleanVar
        self._dcp_refresh_suboptions()

    def _dcp_suboption_select_all(self):
        for var in (self._option_widgets.get("dcp_suboption_vars") or {}).values():
            var.set(True)

    def _dcp_suboption_select_none(self):
        for var in (self._option_widgets.get("dcp_suboption_vars") or {}).values():
            var.set(False)

    def _dcp_refresh_suboptions(self):
        """根据当前选中的 Option 刷新 Suboption 复选框列表"""
        opt_name = self._option_widgets.get("dcp_option")
        if not opt_name:
            return
        opt_name = opt_name.get() if hasattr(opt_name, "get") else str(opt_name)
        option_value = OPTION_MAP.get(opt_name, 0x01)
        subopts = get_suboptions_for_option(option_value)
        f_sub = self._option_widgets.get("dcp_suboption_frame")
        if not f_sub:
            return
        for w in f_sub.winfo_children():
            w.destroy()
        vars_map = {}
        for i, (sub_val, label) in enumerate(subopts):
            var = tk.BooleanVar(value=(i == 0))
            vars_map[sub_val] = var
            txt = f"0x{sub_val:02X} {label}"
            ttk.Checkbutton(f_sub, text=txt, variable=var).grid(row=i // 4, column=i % 4, sticky=tk.W, padx=6, pady=2)
        self._option_widgets["dcp_suboption_vars"] = vars_map

    def _get_goose_config(self):
        try:
            data_str = self._option_widgets["goose_data"].get("1.0", tk.END).strip()
            data = json.loads(data_str)
        except Exception:
            data = {"Switch_1": True, "Switch_2": False}
        return {
            "appid": int(self._option_widgets["goose_appid"].get() or "256"),
            "gocb_ref": self._option_widgets["goose_gocb"].get() or "IED1/LLN0$GO$GSE1",
            "datset": self._option_widgets["goose_datset"].get() or "IED1/LLN0$DataSet1",
            "stnum": 1, "sqnum": 0, "timeallowedtolive": 2000,
            "data": data,
        }

    def _get_sv_config(self):
        try:
            samples_str = self._option_widgets["sv_samples"].get("1.0", tk.END).strip()
            samples = json.loads(samples_str)
        except Exception:
            samples = {"Voltage_A": 220.1, "Voltage_B": 219.8, "Voltage_C": 220.3, "Current_A": 10.2, "Current_B": 10.5, "Current_C": 10.1}
        appid = int(self._option_widgets["sv_appid"].get() or "16409")
        if appid < 0x4000 or appid > 0x7FFF:
            raise ValueError("SV AppID 须在 16384~32767 之间")
        return {
            "appid": appid,
            "svid": self._option_widgets["sv_svid"].get() or "SV_Line1",
            "smpcnt": 0, "smpsynch": True, "samples": samples,
        }

    def _get_ethercat_config(self):
        codes = [c for c, var in self._option_widgets["ecat_cmds"].items() if var.get()]
        if not codes:
            codes = [0x00]
        return {
            "data_unit_type": 1,
            "command_codes": codes,
            "dst_mac": self._option_widgets["ecat_dst_mac"].get() or "01:01:01:01:01:01",
            "read_len": 2,
        }

    def _get_powerlink_config(self):
        types = [t for t, var in self._option_widgets["pl_types"].items() if var.get()]
        if not types:
            types = ["SoC"]
        return {
            "service_types": types,
            "sa": int(self._option_widgets["pl_sa"].get() or "240"),
            "da": int(self._option_widgets["pl_da"].get() or "17"),
            "dst_mac": "01:11:1e:00:00:01",
            "src_mac": "00:50:c2:31:3f:dd",
        }

    def _get_dcp_config(self):
        vars_map = self._option_widgets.get("dcp_suboption_vars") or {}
        suboptions = [sub_val for sub_val, var in vars_map.items() if var.get()]
        if not suboptions:
            opt_name = self._option_widgets.get("dcp_option")
            opt_name = opt_name.get() if opt_name and hasattr(opt_name, "get") else "IP"
            option_value = OPTION_MAP.get(opt_name, 0x01)
            subopts = get_suboptions_for_option(option_value)
            suboptions = [sub_val for sub_val, _ in subopts[:1]] if subopts else [0x01]
        return {
            "frame_type": self._option_widgets["dcp_frame"].get() or "GETORSET",
            "service_code": self._option_widgets["dcp_service"].get() or "GET",
            "service_type": "request",
            "option": self._option_widgets["dcp_option"].get() or "IP",
            "suboptions": suboptions,
            "dst_mac": "01:0e:cf:00:00:00",
            "src_mac": "00:11:22:33:44:55",
        }

    def _callback(self, data):
        if isinstance(data, dict) and data.get("error"):
            self.root.after(0, lambda: self._log("错误: " + data["error"]))
        else:
            c = self.sender.get_packet_count() if self.sender else 0
            self.root.after(0, lambda: self._update_status(f"已发送: {c}"))

    def _update_status(self, text):
        self.lbl_status.config(text=text)

    def _start(self):
        iface = self.iface_var.get()
        if not iface or not iface.strip():
            messagebox.showwarning("提示", "请先选择网卡")
            return
        proto = self.protocol_var.get()
        try:
            if proto == "GOOSE":
                self.sender = GooseSenderService(iface=iface)
                self.sender.set_config(self._get_goose_config())
            elif proto == "SV":
                self.sender = SVSenderService(iface=iface)
                self.sender.set_config(self._get_sv_config())
            elif proto == "EtherCAT":
                self.sender = EthercatSenderService(iface=iface)
                self.sender.set_config(self._get_ethercat_config())
            elif proto == "POWERLINK":
                self.sender = PowerlinkSenderService(iface=iface)
                self.sender.set_config(self._get_powerlink_config())
            elif proto == "PNRT-DCP":
                self.sender = DcpSenderService(iface=iface)
                self.sender.set_config(self._get_dcp_config())
            else:
                messagebox.showwarning("提示", "未知协议")
                return
            self.sender.set_callback(self._callback)
            if self.sender.start():
                self.btn_start.config(state=tk.DISABLED)
                self.btn_stop.config(state=tk.NORMAL)
                self._update_status("发送中...")
                self._log(f"{proto} 发送已启动，网卡: {iface}")
            else:
                messagebox.showerror("错误", "启动发送失败，请查看日志")
        except Exception as e:
            messagebox.showerror("错误", str(e))
            self._log("启动失败: " + str(e))

    def _stop(self):
        if self.sender:
            self.sender.stop()
            c = self.sender.get_packet_count()
            self.sender = None
        else:
            c = 0
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self._update_status("已停止")
        self._log(f"发送已停止，共发送 {c} 个报文")

    def on_closing(self):
        self._stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ProtocolSenderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
