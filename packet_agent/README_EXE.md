# packet_agent.exe 打包说明

## 概述
`packet_agent.exe` 是 `packet_agent.py` 的打包版本，可以在Windows 7和Windows 10系统上直接运行，无需安装Python环境。

## 打包方法

### 方法1: 使用批处理脚本（推荐）
1. 打开命令提示符（CMD）或PowerShell
2. 进入 `packet_agent` 目录
3. 运行 `build_exe.bat`
4. 等待打包完成，exe文件将生成在 `dist` 目录中

### 方法2: 使用Python脚本
1. 确保已安装 PyInstaller: `pip install pyinstaller`
2. 运行: `python build_exe.py`
3. exe文件将生成在 `dist` 目录中

## 使用说明

### 运行方式
1. **命令行运行（推荐）**:
   ```cmd
   packet_agent.exe --host 0.0.0.0 --port 8888
   ```

2. **直接双击运行**:
   - 使用默认配置（监听 0.0.0.0:8888）
   - 后台运行，无控制台窗口

### 参数说明
- `--host`: 监听地址，默认为 `0.0.0.0`
- `--port`: 监听端口，默认为 `8888`
- `--debug`: 启用调试模式（会显示控制台窗口）

### 功能特性
- 兼容 Windows 7 和 Windows 10
- 无需安装Python环境
- 后台运行，不显示控制台窗口
- 支持所有packet_agent.py的功能

## 注意事项
1. 首次运行可能需要Windows防火墙授权
2. 确保目标端口未被占用
3. 如果遇到问题，可以使用 `--debug` 参数查看详细日志

## 文件位置
- 打包脚本: `packet_agent/build_exe.bat`
- Python打包脚本: `packet_agent/build_exe.py`
- 生成的exe: `packet_agent/dist/packet_agent.exe`

