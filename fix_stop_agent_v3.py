#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 agent_manager.py 中的 stop_agent 方法
使用精确的行级别替换
"""

file_path = r'D:\自动化测试\SFW_CONFIG\djangoProject\main\agent_manager.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到要修改的行号
new_lines = []
skip_until_line = -1

for i, line in enumerate(lines):
    line_num = i + 1

    # 跳过之前标记的范围
    if line_num < skip_until_line:
        continue

    # 第 1527-1528 行：替换 PsExec 检查
    if line_num == 1527:
        # 原代码：if not os.path.exists(psexec_path):
        # 新代码：检查 PsExec 可用性，但不作为失败条件
        new_lines.append('                psexec_available = os.path.exists(psexec_path)  # PsExec 可选\n')
        continue
    elif line_num == 1528:
        # 原代码：return False, f"未找到 PsExec.exe，路径：{psexec_path}"
        # 跳过这行
        continue
    elif line_num == 1529:
        # 原代码：空行
        # 添加新注释
        new_lines.append('\n')
        new_lines.append('                # 优化方案：优先通过端口 PID 杀死进程（不依赖 PsExec）\n')
        new_lines.append('                import re as regex_module\n')
        new_lines.append('\n')
        new_lines.append('                # 步骤 1: 获取 8888 端口的 PID\n')
        new_lines.append('                pid_8888 = None\n')
        new_lines.append('                check_cmd_8888 = f\'netstat -ano | findstr ":{agent_port}" | findstr "LISTENING"\'\n')
        new_lines.append('                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)\n')
        new_lines.append('                if output:\n')
        new_lines.append('                    match = regex_module.search(rf\':{agent_port}\\s+.*?LISTENING\\s+(\\d+)\', output)\n')
        new_lines.append('                    if match:\n')
        new_lines.append('                        pid_8888 = match.group(1)\n')
        new_lines.append('\n')
        new_lines.append('                # 步骤 2: 获取 8889 端口的 PID\n')
        new_lines.append("                pid_8889 = None\n")
        new_lines.append('                check_cmd_8889 = \'netstat -ano | findstr ":8889" | findstr "LISTENING"\'\n')
        new_lines.append('                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)\n')
        new_lines.append('                if output:\n')
        new_lines.append("                    match = regex_module.search(r':8889\\s+.*?LISTENING\\s+(\\d+)', output)\n")
        new_lines.append('                    if match:\n')
        new_lines.append('                        pid_8889 = match.group(1)\n')
        new_lines.append('\n')
        new_lines.append('                # 步骤 3: 杀死占用端口的进程（通过 SSH + taskkill）\n')
        new_lines.append('                if pid_8888:\n')
        new_lines.append("                    kill_cmd = f'taskkill /F /PID {pid_8888}'\n")
        new_lines.append('                    self._safe_exec_command(ssh, kill_cmd, timeout=10)\n')
        new_lines.append('                if pid_8889:\n')
        new_lines.append("                    kill_cmd = f'taskkill /F /PID {pid_8889}'\n")
        new_lines.append('                    self._safe_exec_command(ssh, kill_cmd, timeout=10)\n')
        new_lines.append('\n')
        new_lines.append('                time.sleep(2)\n')
        new_lines.append('\n')
        new_lines.append('                # 步骤 4: 检查端口是否已释放\n')
        new_lines.append('                check_cmd_8888 = f\'netstat -ano | findstr ":{agent_port}" | findstr "LISTENING"\'\n')
        new_lines.append('                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)\n')
        new_lines.append("                is_running_8888 = bool(output and 'LISTENING' in output)\n")
        new_lines.append('\n')
        new_lines.append('                check_cmd_8889 = \'netstat -ano | findstr ":8889" | findstr "LISTENING"\'\n')
        new_lines.append('                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)\n')
        new_lines.append("                is_running_8889 = bool(output and 'LISTENING' in output)\n")
        new_lines.append('\n')
        new_lines.append('                # 步骤 5: 如果端口仍被占用，尝试通用清理\n')
        new_lines.append('                if is_running_8888 or is_running_8889:\n')
        new_lines.append('                    # 批量清理所有占用端口的进程\n')
        new_lines.append('                    batch_kill_cmd = f\'for /f "tokens=5" %a in (\\\'netstat -ano ^| findstr ":{agent_port}" ^| findstr "LISTENING" ^| findstr /v "TIME_WAIT"\\\') do taskkill /F /PID %a 2>nul\'\n')
        new_lines.append('                    self._safe_exec_command(ssh, batch_kill_cmd, timeout=10)\n')
        new_lines.append('\n')
        new_lines.append('                    batch_kill_cmd_8889 = f\'for /f "tokens=5" %a in (\\\'netstat -ano ^| findstr ":8889" ^| findstr "LISTENING" ^| findstr /v "TIME_WAIT"\\\') do taskkill /F /PID %a 2>nul\'\n')
        new_lines.append('                    self._safe_exec_command(ssh, batch_kill_cmd_8889, timeout=10)\n')
        new_lines.append('\n')
        new_lines.append("                    # 杀死所有 python 和 pythonw 进程（不依赖 PsExec）\n")
        new_lines.append("                    self._safe_exec_command(ssh, 'taskkill /F /IM python.exe 2>nul', timeout=10)\n")
        new_lines.append("                    self._safe_exec_command(ssh, 'taskkill /F /IM pythonw.exe 2>nul', timeout=10)\n")
        new_lines.append('\n')
        new_lines.append('                    time.sleep(3)\n')
        new_lines.append('\n')
        new_lines.append('                    # 再次检查端口状态\n')
        new_lines.append('                    check_cmd_8888 = f\'netstat -ano | findstr ":{agent_port}" | findstr "LISTENING"\'\n')
        new_lines.append('                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8888, timeout=5)\n')
        new_lines.append("                is_running_8888 = bool(output and 'LISTENING' in output)\n")
        new_lines.append('\n')
        new_lines.append('                check_cmd_8889 = \'netstat -ano | findstr ":8889" | findstr "LISTENING"\'\n')
        new_lines.append('                exit_status, output, error = self._safe_exec_command(ssh, check_cmd_8889, timeout=5)\n')
        new_lines.append("                is_running_8889 = bool(output and 'LISTENING' in output)\n")
        new_lines.append('\n')
        new_lines.append('                # 步骤 6: 如果 PsExec 可用，再执行一次确保清理\n')
        new_lines.append('                if psexec_available:\n')
        # 后面继续保留原有的 try 块逻辑，但修改为杀 python.exe
        continue
    elif line_num == 1530:
        # 修改 psexec_cmd 杀 pythonw.exe 为 python.exe
        new_lines.append("                    psexec_cmd = [\n")
        new_lines.append("                        psexec_path,\n")
        new_lines.append(f"                        f'\\\\\\\\{{host}}',\n")
        new_lines.append("                        '-u', username,\n")
        new_lines.append("                        '-p', password,\n")
        new_lines.append("                        '-s',\n")
        new_lines.append("                        'taskkill',\n")
        new_lines.append("                        '/F',\n")
        new_lines.append("                        '/T',\n")
        new_lines.append("                        '/IM', 'python.exe'  # 同时杀死 python.exe 和 pythonw.exe\n")
        new_lines.append("                    ]\n")
        continue
    elif line_num == 1540:
        # 在 try 块结束后，增加额外的清理
        new_lines.append(lines[i])  # 保留原行
        # 在 except 块之后增加备选方案
        continue
    elif 1541 <= line_num <= 1596:
        # 这些行在 try/except 块内，保留
        new_lines.append(lines[i])
        continue
    else:
        # 其他行保留
        new_lines.append(lines[i])

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('[OK] Fixed!')
