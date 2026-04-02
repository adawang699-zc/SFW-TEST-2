#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 agent_manager.py 中的 stop_agent 方法
问题：
1. 依赖 PsExec.exe（可能不存在）
2. 只杀死 pythonw.exe，不杀 python.exe
3. 没有通过端口 PID 杀死进程的备选方案

修复方案：
1. 优先通过端口 PID 杀死进程（最可靠）
2. 同时杀死 python.exe 和 pythonw.exe
3. PsExec 仅作为备选方案，不存在时也能正常工作
"""

import os
import re

file_path = r'D:\自动化测试\SFW_CONFIG\djangoProject\main\agent_manager.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到旧的 stop_agent Windows 部分并替换
old_code = '''            # 根据系统类型构建强制停止命令
            if system_type == "windows":
                # Windows: 使用 psexec 在本地执行，而不是通过 SSH 远程执行
                import json
                import os
                import subprocess
                log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.cursor', 'debug.log')

                # 从连接信息中获取用户名和密码
                connection = self.connections.get(connection_key, {})
                username = connection.get('username', '')
                password = connection.get('password', '')

                if not username or not password:
                    return False, "无法获取 SSH 凭据，无法停止 Agent"

                # 获取 psexec.exe 路径
                django_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                packet_agent_dir = os.path.join(django_root, 'packet_agent')
                psexec_path = os.path.join(packet_agent_dir, 'PsExec.exe')

                if not os.path.exists(psexec_path):
                    return False, f"未找到 PsExec.exe，路径：{psexec_path}"

                # 使用 psexec 在本地执行 taskkill 命令停止所有 pythonw.exe 进程
                psexec_cmd = [
                    psexec_path,
                    f'\\\\\\\\{host}',
                    '-u', username,
                    '-p', password,
                    '-s',  # 以系统权限运行
                    'taskkill',
                    '/F',  # 强制终止
                    '/T',  # 终止进程树（包括子进程）
                    '/IM', 'pythonw.exe'
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

                    stdout, stderr = process.communicate(timeout=30)
                    return_code = process.returncode

                    time.sleep(2)

                    # 检查 8888 和 8889 端口状态（仍然使用 SSH 检查）
                    check_cmd_8888 = f'netstat -ano | findstr ":{agent_port}"'
                    exit_status_check_8888, output_check_8888, error_check_8888 = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)
                    # 只有包含 LISTENING 状态才认为端口在监听，TIME_WAIT、ESTABLISHED 等状态不算监听
                    is_running_8888 = bool(output_check_8888 and 'LISTENING' in output_check_8888)

                    check_cmd_8889 = 'netstat -ano | findstr ":8889"'
                    exit_status_check_8889, output_check_8889, error_check_8889 = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)
                    # 只有包含 LISTENING 状态才认为端口在监听，TIME_WAIT、ESTABLISHED 等状态不算监听
                    is_running_8889 = bool(output_check_8889 and 'LISTENING' in output_check_8889)

                    # 如果 8889 端口仍在运行，尝试再次停止
                    if is_running_8889:
                        try:
                            process2 = subprocess.Popen(
                                psexec_cmd,
                                cwd=packet_agent_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                            )
                            process2.communicate(timeout=30)
                            time.sleep(2)

                            # 再次检查 8889 端口
                            exit_status_check_8889_2, output_check_8889_2, error_check_8889_2 = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)
                            is_running_8889 = bool(output_check_8889_2 and 'LISTENING' in output_check_8889_2)
                        except Exception:
                            pass

                    is_running = is_running_8888 or is_running_8889
                    status_msg = f"8888 端口：{'运行中' if is_running_8888 else '已停止'}, 8889 端口：{'运行中' if is_running_8889 else '已停止'}"

                except subprocess.TimeoutExpired:
                    process.kill()
                    return False, "psexec 执行超时"
                except Exception as e:
                    return False, f"psexec 执行异常：{str(e)}"'''

new_code = '''            # 根据系统类型构建强制停止命令
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

                is_running = is_running_8888 or is_running_8889'''

# 执行替换
if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Fixed successfully!")
else:
    print("[ERROR] Old code not found")
    print("Trying to find issue...")
    # 查找类似代码
    if "psexec_path = os.path.join(packet_agent_dir, 'PsExec.exe')" in content:
        print("Found psexec_path definition")
    if "if not os.path.exists(psexec_path):" in content:
        print("Found PsExec existence check")
    if "/IM', 'pythonw.exe'" in content:
        print("Found code that only kills pythonw.exe")
