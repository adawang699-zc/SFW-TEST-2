#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
packet_agent.exe的包装脚本
用于在打包成exe时提供更好的Windows兼容性
"""

import sys
import os

# 添加当前目录到Python路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的exe
    application_path = os.path.dirname(sys.executable)
else:
    # 如果是脚本运行
    application_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, application_path)

# 导入主程序
if __name__ == '__main__':
    # 导入packet_agent模块
    try:
        from packet_agent import main
        main()
    except ImportError:
        # 如果导入失败，直接运行packet_agent.py
        import packet_agent
        if hasattr(packet_agent, '__main__'):
            packet_agent.__main__()
        else:
            # 手动启动
            import argparse
            parser = argparse.ArgumentParser(description='报文发送代理程序')
            parser.add_argument('--host', default='0.0.0.0', help='监听地址')
            parser.add_argument('--port', type=int, default=8888, help='监听端口')
            parser.add_argument('--debug', action='store_true', help='调试模式')
            
            args = parser.parse_args()
            
            packet_agent.app.run(
                host=args.host,
                port=args.port,
                debug=args.debug,
                threaded=True
            )

