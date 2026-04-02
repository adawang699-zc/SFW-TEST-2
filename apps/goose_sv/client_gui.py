"""
GOOSE/SV 客户端 GUI（发送端）
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from goose_sender import GooseSenderService
from sv_sender import SVSenderService
from network_utils import get_windows_interfaces, get_interface_name_hint
import json


class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IEC 61850 客户端 - GOOSE/SV 发送端")
        self.root.geometry("900x700")
        
        # 服务实例
        self.goose_sender = None
        self.sv_sender = None
        
        self._create_widgets()
        self._setup_layout()
    
    def _create_widgets(self):
        # 顶部配置区域
        config_frame = ttk.LabelFrame(self.root, text="网络配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(config_frame, text="网卡名称:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        # 先使用默认值，后台异步加载网卡列表
        default_interfaces = ["以太网", "Ethernet", "eth0"]
        self.iface_var = tk.StringVar(value=default_interfaces[0])
        self.iface_combo = ttk.Combobox(config_frame, textvariable=self.iface_var, width=30, values=default_interfaces)
        self.iface_combo.grid(row=0, column=1, padx=5, pady=5)
        self.iface_combo.set(default_interfaces[0])
        
        # 添加刷新按钮
        refresh_btn = ttk.Button(config_frame, text="刷新", command=self._refresh_interfaces)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(config_frame, text="(选择或输入网卡名称)").grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # 后台异步加载网卡列表（不阻塞界面）
        self.root.after(100, self._load_interfaces_async)
        
        # GOOSE 配置区域
        goose_frame = ttk.LabelFrame(self.root, text="GOOSE 发送配置", padding=5)
        goose_frame.pack(fill=tk.X, padx=10, pady=3)
        
        # GOOSE 参数 - 使用两列布局
        ttk.Label(goose_frame, text="应用标识 (AppID):").grid(row=0, column=0, padx=3, pady=3, sticky=tk.W)
        self.goose_appid_var = tk.StringVar(value="256")
        ttk.Entry(goose_frame, textvariable=self.goose_appid_var, width=15).grid(row=0, column=1, padx=3, pady=3, sticky=tk.W)
        
        ttk.Label(goose_frame, text="GOCB参考:").grid(row=0, column=2, padx=3, pady=3, sticky=tk.W)
        self.goose_gocb_var = tk.StringVar(value="IED1/LLN0$GO$GSE1")
        ttk.Entry(goose_frame, textvariable=self.goose_gocb_var, width=30).grid(row=0, column=3, padx=3, pady=3, sticky=tk.W+tk.E)
        
        ttk.Label(goose_frame, text="数据集:").grid(row=1, column=0, padx=3, pady=3, sticky=tk.W)
        self.goose_dataset_var = tk.StringVar(value="IED1/LLN0$DataSet1")
        ttk.Entry(goose_frame, textvariable=self.goose_dataset_var, width=30).grid(row=1, column=1, columnspan=3, padx=3, pady=3, sticky=tk.W+tk.E)
        
        ttk.Label(goose_frame, text="数据内容 (JSON):").grid(row=2, column=0, padx=3, pady=3, sticky=tk.W)
        self.goose_data_text = scrolledtext.ScrolledText(goose_frame, height=2, width=50)
        self.goose_data_text.insert("1.0", '{"Switch_1": true, "Switch_2": false}')
        self.goose_data_text.grid(row=2, column=1, columnspan=3, padx=3, pady=3, sticky=tk.W+tk.E)
        
        # GOOSE 控制按钮
        goose_btn_frame = ttk.Frame(goose_frame)
        goose_btn_frame.grid(row=3, column=0, columnspan=4, pady=5)
        self.goose_start_btn = ttk.Button(goose_btn_frame, text="启动 GOOSE 发送", command=self._start_goose)
        self.goose_start_btn.pack(side=tk.LEFT, padx=5)
        self.goose_stop_btn = ttk.Button(goose_btn_frame, text="停止 GOOSE 发送", command=self._stop_goose, state=tk.DISABLED)
        self.goose_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 配置列权重
        goose_frame.columnconfigure(3, weight=1)
        
        # SV 配置区域
        sv_frame = ttk.LabelFrame(self.root, text="SV 发送配置", padding=5)
        sv_frame.pack(fill=tk.X, padx=10, pady=3)
        
        # SV 参数 - 使用两列布局
        ttk.Label(sv_frame, text="应用标识 (AppID):").grid(row=0, column=0, padx=3, pady=3, sticky=tk.W)
        self.sv_appid_var = tk.StringVar(value="16409")  # 0x4019，符合0x4000~0x7FFF范围
        ttk.Entry(sv_frame, textvariable=self.sv_appid_var, width=15).grid(row=0, column=1, padx=3, pady=3, sticky=tk.W)
        ttk.Label(sv_frame, text="(范围: 16384~32767)").grid(row=0, column=2, padx=3, pady=3, sticky=tk.W)
        
        ttk.Label(sv_frame, text="SVID:").grid(row=0, column=3, padx=3, pady=3, sticky=tk.W)
        self.sv_svid_var = tk.StringVar(value="SV_Line1")
        ttk.Entry(sv_frame, textvariable=self.sv_svid_var, width=30).grid(row=0, column=4, padx=3, pady=3, sticky=tk.W+tk.E)
        
        ttk.Label(sv_frame, text="采样率 (Hz):").grid(row=1, column=0, padx=3, pady=3, sticky=tk.W)
        self.sv_smprate_var = tk.StringVar(value="50")
        ttk.Entry(sv_frame, textvariable=self.sv_smprate_var, width=15).grid(row=1, column=1, padx=3, pady=3, sticky=tk.W)
        
        ttk.Label(sv_frame, text="采样值 (JSON):").grid(row=1, column=2, padx=3, pady=3, sticky=tk.W)
        self.sv_samples_text = scrolledtext.ScrolledText(sv_frame, height=2, width=50)
        self.sv_samples_text.insert("1.0", '{"Voltage_A": 22010, "Voltage_B": 21980, "Voltage_C": 22030, "Current_A": 1020, "Current_B": 1050, "Current_C": 1010}')
        self.sv_samples_text.grid(row=1, column=3, columnspan=2, padx=3, pady=3, sticky=tk.W+tk.E)
        
        # SV 控制按钮
        sv_btn_frame = ttk.Frame(sv_frame)
        sv_btn_frame.grid(row=2, column=0, columnspan=5, pady=5)
        self.sv_start_btn = ttk.Button(sv_btn_frame, text="启动 SV 发送", command=self._start_sv)
        self.sv_start_btn.pack(side=tk.LEFT, padx=5)
        self.sv_stop_btn = ttk.Button(sv_btn_frame, text="停止 SV 发送", command=self._stop_sv, state=tk.DISABLED)
        self.sv_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 配置列权重
        sv_frame.columnconfigure(4, weight=1)
        
        # 日志区域 - 扩大显示区域
        log_frame = ttk.LabelFrame(self.root, text="发送日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def _setup_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
    
    def _load_interfaces_async(self):
        """异步加载网卡列表（不阻塞界面）"""
        def load_in_thread():
            try:
                interfaces = get_windows_interfaces()
                # 在主线程中更新 UI
                self.root.after(0, lambda: self._update_interface_list(interfaces))
            except Exception as e:
                # 如果加载失败，保持默认值
                pass
        
        # 在后台线程中加载
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()
    
    def _update_interface_list(self, interfaces):
        """更新网卡列表（在主线程中调用）"""
        if interfaces:
            # 过滤掉无效的网卡名称
            valid_interfaces = [iface for iface in interfaces if iface and iface.strip() and iface not in ['_', '-', '.']]
            if valid_interfaces:
                self.iface_combo['values'] = valid_interfaces
                # 如果当前选择不在列表中，选择第一个
                if self.iface_var.get() not in valid_interfaces:
                    self.iface_var.set(valid_interfaces[0])
    
    def _refresh_interfaces(self):
        """刷新网卡列表（异步）"""
        # 显示加载提示
        self.iface_combo['values'] = ["正在加载..."]
        self.iface_combo.set("正在加载...")
        
        def refresh_in_thread():
            try:
                interfaces = get_windows_interfaces()
                # 在主线程中更新 UI
                self.root.after(0, lambda: self._update_interface_list_after_refresh(interfaces))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("刷新失败", f"获取网卡列表失败: {str(e)}"))
        
        # 在后台线程中刷新
        thread = threading.Thread(target=refresh_in_thread, daemon=True)
        thread.start()
    
    def _update_interface_list_after_refresh(self, interfaces):
        """刷新后更新网卡列表（在主线程中调用）"""
        if interfaces:
            # 过滤掉无效的网卡名称
            valid_interfaces = [iface for iface in interfaces if iface and iface.strip() and iface not in ['_', '-', '.']]
            if valid_interfaces:
                self.iface_combo['values'] = valid_interfaces
                # 如果当前选择不在列表中，选择第一个
                if self.iface_var.get() not in valid_interfaces:
                    self.iface_var.set(valid_interfaces[0])
                
                # 显示网卡列表，每行一个
                interface_list = "\n".join([f"  {i+1}. {iface}" for i, iface in enumerate(valid_interfaces[:15])])
                if len(valid_interfaces) > 15:
                    interface_list += f"\n  ... 还有 {len(valid_interfaces) - 15} 个网卡"
                messagebox.showinfo("刷新成功", f"找到 {len(valid_interfaces)} 个网卡:\n{interface_list}")
            else:
                messagebox.showwarning("刷新失败", "未找到有效的网卡")
        else:
            messagebox.showwarning("刷新失败", "未找到网卡")
    
    def _log(self, message):
        """添加日志"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
    
    def _start_goose(self):
        """启动 GOOSE 发送"""
        try:
            iface = self.iface_var.get()
            appid = int(self.goose_appid_var.get())
            gocb_ref = self.goose_gocb_var.get()
            datset = self.goose_dataset_var.get()
            data_str = self.goose_data_text.get("1.0", tk.END).strip()
            data = json.loads(data_str)
            
            # 处理数据：所有值直接使用，不做特殊处理
            processed_data = data
            
            self.goose_sender = GooseSenderService(iface=iface)
            self.goose_sender.set_config({
                "appid": appid,
                "gocb_ref": gocb_ref,
                "datset": datset,
                "stnum": 1,
                "sqnum": 0,
                "timeallowedtolive": 2000,
                "data": processed_data
            })
            self.goose_sender.set_callback(self._goose_callback)
            
            if self.goose_sender.start():
                self.goose_start_btn.config(state=tk.DISABLED)
                self.goose_stop_btn.config(state=tk.NORMAL)
                self._log("GOOSE 发送已启动")
            else:
                messagebox.showerror("错误", "启动 GOOSE 发送失败，请检查网卡配置")
        except json.JSONDecodeError:
            messagebox.showerror("错误", "数据内容 JSON 格式错误")
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {str(e)}")
    
    def _stop_goose(self):
        """停止 GOOSE 发送"""
        if self.goose_sender:
            self.goose_sender.stop()
            self.goose_sender = None
        self.goose_start_btn.config(state=tk.NORMAL)
        self.goose_stop_btn.config(state=tk.DISABLED)
        self._log("GOOSE 发送已停止")
    
    def _goose_callback(self, data):
        """GOOSE 发送回调"""
        if "error" in data:
            self._log(f"GOOSE 发送错误: {data['error']}")
        else:
            self._log(f"GOOSE 已发送 | 顺序号: {data.get('sqnum', 0)} | 数据集: {data.get('datset', '')}")
    
    def _start_sv(self):
        """启动 SV 发送"""
        try:
            iface = self.iface_var.get()
            appid = int(self.sv_appid_var.get())
            # 验证APPID范围：0x4000~0x7FFF (16384~32767)
            if appid < 0x4000 or appid > 0x7FFF:
                messagebox.showerror("错误", f"SV APPID必须在16384~32767范围内（0x4000~0x7FFF），当前值：{appid} (0x{appid:04X})")
                return
            svid = self.sv_svid_var.get()
            smprate = int(self.sv_smprate_var.get())
            samples_str = self.sv_samples_text.get("1.0", tk.END).strip()
            samples = json.loads(samples_str)
            
            self.sv_sender = SVSenderService(iface=iface)
            self.sv_sender.set_config({
                "appid": appid,
                "svid": svid,
                "smpcnt": 128,
                "smprate": smprate,
                "samples": samples
            })
            self.sv_sender.set_callback(self._sv_callback)
            
            if self.sv_sender.start():
                self.sv_start_btn.config(state=tk.DISABLED)
                self.sv_stop_btn.config(state=tk.NORMAL)
                self._log("SV 发送已启动")
            else:
                messagebox.showerror("错误", "启动 SV 发送失败，请检查网卡配置")
        except json.JSONDecodeError:
            messagebox.showerror("错误", "采样值 JSON 格式错误")
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {str(e)}")
    
    def _stop_sv(self):
        """停止 SV 发送"""
        if self.sv_sender:
            self.sv_sender.stop()
            self.sv_sender = None
        self.sv_start_btn.config(state=tk.NORMAL)
        self.sv_stop_btn.config(state=tk.DISABLED)
        self._log("SV 发送已停止")
    
    def _sv_callback(self, data):
        """SV 发送回调"""
        if "error" in data:
            self._log(f"SV 发送错误: {data['error']}")
        else:
            self._log(f"SV 已发送 | SVID: {data.get('svid', '')} | 采样数: {data.get('smpcnt', 0)}")
    
    def on_closing(self):
        """关闭窗口时的清理"""
        self._stop_goose()
        self._stop_sv()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

