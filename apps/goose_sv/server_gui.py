"""
GOOSE/SV 服务端 GUI（接收端）
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from goose_receiver import GooseReceiverService
from sv_receiver import SVReceiverService
from network_utils import get_windows_interfaces
import json
from datetime import datetime


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IEC 61850 服务端 - GOOSE/SV 接收端")
        self.root.geometry("900x700")
        
        # 服务实例
        self.goose_receiver = None
        self.sv_receiver = None
        
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
        
        # GOOSE 接收区域
        goose_frame = ttk.LabelFrame(self.root, text="GOOSE 接收", padding=10)
        goose_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # GOOSE 控制按钮
        goose_btn_frame = ttk.Frame(goose_frame)
        goose_btn_frame.pack(fill=tk.X, pady=5)
        self.goose_start_btn = ttk.Button(goose_btn_frame, text="启动 GOOSE 接收", command=self._start_goose)
        self.goose_start_btn.pack(side=tk.LEFT, padx=5)
        self.goose_stop_btn = ttk.Button(goose_btn_frame, text="停止 GOOSE 接收", command=self._stop_goose, state=tk.DISABLED)
        self.goose_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # GOOSE 接收数据显示
        ttk.Label(goose_frame, text="接收到的 GOOSE 报文:").pack(anchor=tk.W, pady=5)
        self.goose_data_text = scrolledtext.ScrolledText(goose_frame, height=8, width=80)
        self.goose_data_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # SV 接收区域
        sv_frame = ttk.LabelFrame(self.root, text="SV 接收", padding=10)
        sv_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # SV 控制按钮
        sv_btn_frame = ttk.Frame(sv_frame)
        sv_btn_frame.pack(fill=tk.X, pady=5)
        self.sv_start_btn = ttk.Button(sv_btn_frame, text="启动 SV 接收", command=self._start_sv)
        self.sv_start_btn.pack(side=tk.LEFT, padx=5)
        self.sv_stop_btn = ttk.Button(sv_btn_frame, text="停止 SV 接收", command=self._stop_sv, state=tk.DISABLED)
        self.sv_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # SV 接收数据显示
        ttk.Label(sv_frame, text="接收到的 SV 报文:").pack(anchor=tk.W, pady=5)
        self.sv_data_text = scrolledtext.ScrolledText(sv_frame, height=8, width=80)
        self.sv_data_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 统计信息
        stats_frame = ttk.LabelFrame(self.root, text="统计信息", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="GOOSE 接收: 0 条 | SV 接收: 0 条")
        self.stats_label.pack()
        
        self.goose_count = 0
        self.sv_count = 0
    
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
    
    def _update_stats(self):
        """更新统计信息"""
        self.stats_label.config(text=f"GOOSE 接收: {self.goose_count} 条 | SV 接收: {self.sv_count} 条")
    
    def _start_goose(self):
        """启动 GOOSE 接收"""
        try:
            # 清空接收框和计数
            self.goose_data_text.delete("1.0", tk.END)
            self.goose_count = 0
            self._update_stats()
            
            iface = self.iface_var.get()
            self.goose_receiver = GooseReceiverService(iface=iface)
            self.goose_receiver.set_callback(self._goose_callback)
            
            if self.goose_receiver.start():
                self.goose_start_btn.config(state=tk.DISABLED)
                self.goose_stop_btn.config(state=tk.NORMAL)
                self._log_goose("GOOSE 接收已启动，等待报文...\n")
            else:
                messagebox.showerror("错误", "启动 GOOSE 接收失败，请检查网卡配置")
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {str(e)}")
    
    def _stop_goose(self):
        """停止 GOOSE 接收"""
        if self.goose_receiver:
            self.goose_receiver.stop()
            self.goose_receiver = None
        self.goose_start_btn.config(state=tk.NORMAL)
        self.goose_stop_btn.config(state=tk.DISABLED)
        self._log_goose("GOOSE 接收已停止")
    
    def _goose_callback(self, data):
        """GOOSE 接收回调"""
        if "error" in data:
            self._log_goose(f"错误: {data['error']}\n")
        elif "info" in data:
            self._log_goose(f"信息: {data['info']}\n")
        else:
            # 只显示收到的报文数量
            self.goose_count = data.get('count', self.goose_count + 1)
            self._update_stats()
    
    def _log_goose(self, message):
        """添加 GOOSE 日志"""
        self.goose_data_text.insert(tk.END, message)
        self.goose_data_text.see(tk.END)
    
    def _start_sv(self):
        """启动 SV 接收"""
        try:
            # 清空接收框和计数
            self.sv_data_text.delete("1.0", tk.END)
            self.sv_count = 0
            self._update_stats()
            
            iface = self.iface_var.get()
            self.sv_receiver = SVReceiverService(iface=iface)
            self.sv_receiver.set_callback(self._sv_callback)
            
            if self.sv_receiver.start():
                self.sv_start_btn.config(state=tk.DISABLED)
                self.sv_stop_btn.config(state=tk.NORMAL)
                self._log_sv("SV 接收已启动，等待报文...\n")
            else:
                messagebox.showerror("错误", "启动 SV 接收失败，请检查网卡配置")
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {str(e)}")
    
    def _stop_sv(self):
        """停止 SV 接收"""
        if self.sv_receiver:
            self.sv_receiver.stop()
            self.sv_receiver = None
        self.sv_start_btn.config(state=tk.NORMAL)
        self.sv_stop_btn.config(state=tk.DISABLED)
        self._log_sv("SV 接收已停止")
    
    def _sv_callback(self, data):
        """SV 接收回调"""
        if "error" in data:
            self._log_sv(f"错误: {data['error']}\n")
        elif "info" in data:
            self._log_sv(f"信息: {data['info']}\n")
        else:
            # 只显示收到的报文数量
            self.sv_count = data.get('count', self.sv_count + 1)
            self._update_stats()
    
    def _log_sv(self, message):
        """添加 SV 日志"""
        self.sv_data_text.insert(tk.END, message)
        self.sv_data_text.see(tk.END)
    
    def on_closing(self):
        """关闭窗口时的清理"""
        self._stop_goose()
        self._stop_sv()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ServerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

