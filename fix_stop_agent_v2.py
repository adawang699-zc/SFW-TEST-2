#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 agent_manager.py 中的 stop_agent 方法 - CRLF 版本
"""

import re

file_path = r'D:\自动化测试\SFW_CONFIG\djangoProject\main\agent_manager.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 保留 CRLF
crlf = '\r\n'

# 找到要替换的部分：从 "根据系统类型构建强制停止命令" 到 "except Exception as e: return False, str(e)" (Windows 部分结束)
# 我们只替换 Windows 分支

# 旧的 Windows 处理代码的开始标记
old_start = '            # 根据系统类型构建强制停止命令\r\n            if system_type == "windows":\r\n                # Windows: 使用 psexec 在本地执行，而不是通过 SSH 远程执行'

# 找到旧代码的结束位置 (Linux 分支开始之前)
old_end_marker = '            else:\r\n                # Linux: 通过端口查找并杀死进程'

# 新的 Windows 处理代码
new_windows_code = '''            # 根据系统类型构建强制停止命令
            if system_type == "windows":
                # Windows: 优先通过端口 PID 杀死进程（最可靠，不依赖 PsExec）
                import os
                import subprocess
                import re as regex_module

                # 从连接信息中获取用户名和密码
                connection = self.connections.get(connection_key, {})
                username = connection.get('username', '')
                password = connection.get('password', '')

                if not username or not password:
                    return False, "无法获取 SSH 凭据，无法停止 Agent"

                # 获取 psexec.exe 路径（可选，用于备选方案）
                django_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                packet_agent_dir = os.path.join(django_root, 'packet_agent')
                psexec_path = os.path.join(packet_agent_dir, 'PsExec.exe')
                psexec_available = os.path.exists(psexec_path)

                is_running_8888 = False
                is_running_8889 = False

                # 步骤 1: 获取 8888 端口的 PID
                pid_8888 = None
                check_cmd_8888 = f'netstat -ano | findstr ":{agent_port}" | findstr "LISTENING"'
                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)
                if output:
                    match = regex_module.search(rf':{agent_port}\\s+.*?LISTENING\\s+(\\d+)', output)
                    if match:
                        pid_8888 = match.group(1)

                # 步骤 2: 获取 8889 端口的 PID
                pid_8889 = None
                check_cmd_8889 = 'netstat -ano | findstr ":8889" | findstr "LISTENING"'
                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)
                if output:
                    match = regex_module.search(r':8889\\s+.*?LISTENING\\s+(\\d+)', output)
                    if match:
                        pid_8889 = match.group(1)

                # 步骤 3: 杀死占用端口的进程（通过 SSH + taskkill）
                if pid_8888:
                    kill_cmd = f'taskkill /F /PID {pid_8888}'
                    self._safe_exec_command(ssh, kill_cmd, timeout=10)
                if pid_8889:
                    kill_cmd = f'taskkill /F /PID {pid_8889}'
                    self._safe_exec_command(ssh, kill_cmd, timeout=10)

                time.sleep(2)

                # 步骤 4: 检查端口是否已释放
                check_cmd_8888 = f'netstat -ano | findstr ":{agent_port}" | findstr "LISTENING"'
                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)
                is_running_8888 = bool(output and 'LISTENING' in output)

                check_cmd_8889 = 'netstat -ano | findstr ":8889" | findstr "LISTENING"'
                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)
                is_running_8889 = bool(output and 'LISTENING' in output)

                # 步骤 5: 如果端口仍被占用，尝试通用清理
                if is_running_8888 or is_running_8889:
                    # 批量清理所有占用端口的进程
                    batch_kill_cmd = f'for /f "tokens=5" %a in (\\'netstat -ano ^| findstr ":{agent_port}" ^| findstr "LISTENING" ^| findstr /v "TIME_WAIT"\\') do taskkill /F /PID %a 2>nul'
                    self._safe_exec_command(ssh, batch_kill_cmd, timeout=10)

                    batch_kill_cmd_8889 = f'for /f "tokens=5" %a in (\\'netstat -ano ^| findstr ":8889" ^| findstr "LISTENING" ^| findstr /v "TIME_WAIT"\\') do taskkill /F /PID %a 2>nul'
                    self._safe_exec_command(ssh, batch_kill_cmd_8889, timeout=10)

                    # 杀死所有 python 和 pythonw 进程（不依赖 PsExec）
                    self._safe_exec_command(ssh, 'taskkill /F /IM python.exe 2>nul', timeout=10)
                    self._safe_exec_command(ssh, 'taskkill /F /IM pythonw.exe 2>nul', timeout=10)

                    time.sleep(3)

                    # 再次检查端口状态
                    check_cmd_8888 = f'netstat -ano | findstr ":{agent_port}" | findstr "LISTENING"'
                    exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)
                    is_running_8888 = bool(output and 'LISTENING' in output)

                    check_cmd_8889 = 'netstat -ano | findstr ":8889" | findstr "LISTENING"'
                    exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)
                    is_running_8889 = bool(output and 'LISTENING' in output)

                # 步骤 6: 如果 PsExec 可用，再执行一次确保清理
                if psexec_available:
                    psexec_cmd = [
                        psexec_path,
                        f'\\\\\\\\{host}',
                        '-u', username,
                        '-p', password,
                        '-s',
                        'taskkill',
                        '/F',
                        '/T',
                        '/IM', 'python.exe'
                    ]
                    try:
                        process = subprocess.Popen(
                            psexec_cmd,
                            cwd=packet_agent_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        )
                        process.communicate(timeout=30)
                        time.sleep(2)
                    except Exception:
                        pass

                status_msg = f"8888 端口：{{'运行中' if is_running_8888 else '已停止'}}, 8889 端口：{{'运行中' if is_running_8889 else '已停止'}}"

                is_running = is_running_8888 or is_running_8889
'''

# 查找旧代码的起止位置
start_pos = content.find(old_start)
if start_pos == -1:
    print("[ERROR] Cannot find old code start marker")
    # 尝试查找部分匹配
    if '使用 psexec 在本地执行' in content:
        print("[INFO] Found partial match for '使用 psexec 在本地执行'")
    if 'if system_type == "windows":' in content:
        pos = content.find('if system_type == "windows":')
        print(f"[INFO] Found 'if system_type == \"windows\":' at position {pos}")
        print("[INFO] Context:")
        print(repr(content[pos:pos+200]))
else:
    # 找到结束位置（Linux 分支开始）
    end_pos = content.find(old_end_marker, start_pos)
    if end_pos == -1:
        print("[ERROR] Cannot find old code end marker")
    else:
        # 替换
        old_code = content[start_pos:end_pos]
        print(f"[INFO] Found old code: {len(old_code)} bytes")

        new_code = new_windows_code.replace('\n', '\r\n') + '            '
        new_content = content[:start_pos] + new_code + content[end_pos:]

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print("[OK] Fixed successfully!")
