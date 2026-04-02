# -*- coding: utf-8 -*-
"""
打包工控协议发送器为 exe（支持 Win7 / Win10）
运行: python build_exe.py
生成在 dist/IndustrialProtocolSender.exe（单文件）或 dist/IndustrialProtocolSender/ 目录
"""
import os
import sys
import subprocess

def main():
    # 当前脚本所在目录为工程根目录
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    main_script = os.path.join(root, "main_gui.py")
    if not os.path.isfile(main_script):
        print("未找到 main_gui.py，请在 industrial_protocol_sender 目录下执行")
        sys.exit(1)

    # PyInstaller：单文件，控制台隐藏（GUI 程序），兼容 Win7
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",           # 单文件 exe
        "--windowed",          # 不显示控制台窗口
        "--name", "IndustrialProtocolSender",
        "--clean",
        # 显式包含可能未自动检测的模块
        "--hidden-import", "scapy",
        "--hidden-import", "scapy.all",
        "--hidden-import", "asn1_encoder",
        "--hidden-import", "network_utils",
        "--hidden-import", "goose_sender",
        "--hidden-import", "sv_sender",
        "--hidden-import", "ethercat_sender",
        "--hidden-import", "powerlink_sender",
        "--hidden-import", "dcp_sender",
        # 添加当前目录为路径，使打包后能找到同目录模块
        "--paths", root,
        main_script,
    ]
    print("执行: " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=root)
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("打包完成。exe 位于: dist\\IndustrialProtocolSender.exe")

if __name__ == "__main__":
    main()
