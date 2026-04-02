#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包packet_agent.py为exe文件的脚本
兼容Windows 7和Windows 10
"""

import os
import sys
import subprocess
import shutil

def check_and_remove_enum34():
    """检查并卸载不兼容的enum34包"""
    try:
        import enum34
        print("检测到不兼容的enum34包，正在卸载...")
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "enum34", "-y"])
        print("enum34已卸载")
    except ImportError:
        pass  # enum34未安装，无需处理
    except Exception as e:
        print(f"警告: 卸载enum34时出错: {e}")

def check_pyinstaller():
    """检查PyInstaller是否已安装"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    """安装PyInstaller"""
    print("正在安装PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("PyInstaller安装完成")

def build_exe():
    """构建exe文件"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    agent_script = os.path.join(script_dir, "packet_agent.py")
    dist_dir = os.path.join(script_dir, "dist")
    build_dir = os.path.join(script_dir, "build")
    spec_file = os.path.join(script_dir, "packet_agent.spec")
    
    # 清理之前的构建
    if os.path.exists(dist_dir):
        print("清理旧的构建文件...")
        shutil.rmtree(dist_dir)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    
    print("=" * 60)
    print("开始打包packet_agent为exe文件...")
    print("=" * 60)
    
    # PyInstaller命令参数
    # --onefile: 打包成单个exe文件
    # --windowed: 无控制台窗口（后台运行）
    # --name: 输出文件名
    # --icon: 图标文件（如果有）
    # --add-data: 添加数据文件
    # --hidden-import: 隐藏导入的模块
    # --collect-all: 收集所有子模块
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",  # 后台运行，不显示控制台
        "--name=packet_agent",
        "--clean",
        "--noconfirm",
        # 隐藏导入的模块
        "--hidden-import=flask",
        "--hidden-import=flask_cors",
        "--hidden-import=scapy",
        "--hidden-import=scapy.all",
        "--hidden-import=scapy.layers.inet",
        "--hidden-import=scapy.layers.l2",
        "--hidden-import=scapy.sendrecv",
        "--hidden-import=scapy.volatile",
        "--hidden-import=psutil",
        "--hidden-import=ftplib",
        # 收集所有子模块
        "--collect-all=scapy",
        "--collect-all=flask",
        # 兼容Windows 7
        "--target-arch=win32",  # 32位，兼容性更好
        # 排除不需要的模块以减小体积
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=tkinter",
        agent_script
    ]
    
    try:
        print("\n执行打包命令...")
        result = subprocess.run(cmd, cwd=script_dir, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        exe_path = os.path.join(dist_dir, "packet_agent.exe")
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print("\n" + "=" * 60)
            print("打包成功！")
            print(f"输出文件: {exe_path}")
            print(f"文件大小: {file_size:.2f} MB")
            print("=" * 60)
            return exe_path
        else:
            print("错误: 未找到生成的exe文件")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        return None
    except Exception as e:
        print(f"打包过程中出错: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("packet_agent.exe 打包工具")
    print("兼容 Windows 7 和 Windows 10")
    print("=" * 60)
    
    # 检查并卸载不兼容的enum34包
    check_and_remove_enum34()
    
    # 检查PyInstaller
    if not check_pyinstaller():
        print("PyInstaller未安装")
        response = input("是否安装PyInstaller? (y/n): ")
        if response.lower() == 'y':
            install_pyinstaller()
        else:
            print("退出")
            return
    
    # 构建exe
    exe_path = build_exe()
    
    if exe_path:
        print("\n提示:")
        print("1. exe文件位于 dist 目录中")
        print("2. 可以将exe文件复制到任何Windows 7/10系统运行")
        print("3. 运行方式: packet_agent.exe --host 0.0.0.0 --port 8888")
        print("4. 或者直接双击运行（使用默认配置）")
    else:
        print("\n打包失败，请检查错误信息")

if __name__ == "__main__":
    main()

