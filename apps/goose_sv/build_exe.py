"""
打包脚本 - 使用 PyInstaller 将程序打包成 exe
支持 Windows 7/10/11
"""
import PyInstaller.__main__
import os
import sys


def build_client():
    """打包客户端"""
    print("正在打包客户端...")
    PyInstaller.__main__.run([
        'client_gui.py',
        '--name=GOOSE_SV_Client',
        '--onefile',
        '--windowed',
        '--hidden-import=goose_sender',
        '--hidden-import=sv_sender',
        '--hidden-import=asn1_encoder',
        '--hidden-import=network_utils',
        '--hidden-import=psutil',
        '--hidden-import=scapy',
        '--hidden-import=scapy.all',
        '--hidden-import=tkinter',
        '--clean',
        '--noconfirm'
    ])
    print("客户端打包完成！")


def build_server():
    """打包服务端"""
    print("正在打包服务端...")
    PyInstaller.__main__.run([
        'server_gui.py',
        '--name=GOOSE_SV_Server',
        '--onefile',
        '--windowed',
        '--hidden-import=goose_receiver',
        '--hidden-import=sv_receiver',
        '--hidden-import=asn1_decoder',
        '--hidden-import=network_utils',
        '--hidden-import=psutil',
        '--hidden-import=scapy',
        '--hidden-import=scapy.all',
        '--hidden-import=tkinter',
        '--clean',
        '--noconfirm'
    ])
    print("服务端打包完成！")


def build_all():
    """打包所有程序"""
    build_client()
    build_server()
    print("\n所有程序打包完成！")
    print("exe 文件位于 dist 目录中")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "client":
            build_client()
        elif sys.argv[1] == "server":
            build_server()
        else:
            print("用法: python build_exe.py [client|server|all]")
    else:
        build_all()

