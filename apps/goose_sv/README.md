# IEC 61850 GOOSE/SV 客户端和服务端程序

基于 `python-iec61850` 库实现的轻量级 IEC 61850 GOOSE/SV 协议客户端和服务端程序，支持 Windows 7/10/11。

## 功能特性

- **GOOSE 协议支持**：发送和接收符合 IEC 61850-8-1 标准的 GOOSE 报文
- **SV 协议支持**：发送和接收符合 IEC 61850-9-2 标准的 SV 采样值报文
- **图形界面**：友好的 GUI 界面，方便配置和监控
- **实时监控**：实时显示发送/接收的报文内容和统计信息
- **跨平台支持**：支持 Windows 7/10/11

## 项目结构

```
.
├── client_gui.py          # 客户端 GUI（发送端）
├── server_gui.py          # 服务端 GUI（接收端）
├── goose_sender.py        # GOOSE 发送模块（基于 scapy）
├── goose_receiver.py      # GOOSE 接收模块（基于 scapy）
├── sv_sender.py           # SV 发送模块（基于 scapy）
├── sv_receiver.py         # SV 接收模块（基于 scapy）
├── asn1_encoder.py        # ASN.1 BER 编码器
├── asn1_decoder.py        # ASN.1 BER 解码器
├── requirements.txt       # Python 依赖
├── build_exe.py          # 打包脚本
├── build.bat             # Windows 打包批处理
└── README.md             # 说明文档
```

## 安装和使用

### 方式一：直接运行 Python 脚本

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **运行客户端（发送端）**
   ```bash
   python client_gui.py
   ```

3. **运行服务端（接收端）**
   ```bash
   python server_gui.py
   ```

### 方式二：打包成 exe 文件

1. **自动打包（推荐）**
   - 双击运行 `build.bat` 脚本
   - 打包完成后，exe 文件位于 `dist` 目录中

2. **手动打包**
   ```bash
   # 安装 PyInstaller
   pip install pyinstaller
   
   # 打包所有程序
   python build_exe.py all
   
   # 或单独打包
   python build_exe.py client  # 只打包客户端
   python build_exe.py server  # 只打包服务端
   ```

3. **运行 exe**
   - 客户端：运行 `dist\GOOSE_SV_Client.exe`
   - 服务端：运行 `dist\GOOSE_SV_Server.exe`

## 使用说明

### 客户端（发送端）

1. **配置网卡**
   - Windows: 输入 "以太网" 或实际网卡名称
   - Linux: 输入 "eth0" 等

2. **配置 GOOSE 发送**
   - 设置应用标识（AppID）
   - 设置 GOCB 参考和数据集
   - 编辑数据内容（JSON 格式）
   - 点击"启动 GOOSE 发送"

3. **配置 SV 发送**
   - 设置应用标识（AppID）
   - 设置 SVID
   - 设置采样率
   - 编辑采样值（JSON 格式）
   - 点击"启动 SV 发送"

### 服务端（接收端）

1. **配置网卡**
   - 必须与客户端使用相同的网卡

2. **启动接收**
   - 点击"启动 GOOSE 接收"开始监听 GOOSE 报文
   - 点击"启动 SV 接收"开始监听 SV 报文
   - 接收到的报文会实时显示在界面上

## 注意事项

### 权限要求
- **Windows**: 必须以**管理员身份**运行程序（发送/接收原始网络数据包需要管理员权限）
- **Linux/Mac**: 需要使用 `sudo` 运行

### 网络配置
- 客户端和服务端必须使用**同一个网卡**
- 确保网卡名称正确（Windows 通常是"以太网"）
- GOOSE/SV 使用组播通信，确保网络支持组播

### 数据格式
- GOOSE 数据内容和 SV 采样值必须使用**有效的 JSON 格式**
- 示例：
  ```json
  {"Switch_1": true, "Voltage_AB": 220.5, "Current_C": 12.3}
  ```

## 协议说明

### GOOSE (Generic Object Oriented Substation Events)
- **用途**: 实时事件传输（如开关跳闸、设备告警）
- **特点**: 单向组播发送，无响应机制
- **发送间隔**: 默认 0.5 秒

### SV (Sampled Values)
- **用途**: 实时采样值传输（如电流/电压采样）
- **特点**: 单向组播发送，无响应机制
- **发送间隔**: 默认 0.02 秒（50Hz 采样率）

## 常见问题

### Q: 程序无法启动，提示权限错误
**A**: 请以管理员身份运行程序（右键 -> 以管理员身份运行）

### Q: 接收端收不到报文
**A**: 
1. 检查客户端和服务端是否使用相同的网卡
2. 检查网卡名称是否正确
3. 检查防火墙设置
4. 确保客户端已启动发送

### Q: 打包后的 exe 文件很大
**A**: 这是正常的，PyInstaller 会将 Python 解释器和所有依赖打包进去。可以使用 `--onefile` 选项生成单个 exe 文件。

### Q: 支持哪些操作系统？
**A**: 主要支持 Windows 7/10/11。Linux 和 Mac 也可以运行 Python 脚本，但需要相应调整网卡名称。

## 技术栈

- **Python 3.7+**
- **scapy**: 网络数据包处理库（用于构造和发送/接收 GOOSE/SV 报文）
- **tkinter**: GUI 界面（Python 内置）
- **PyInstaller**: 打包工具

## 许可证

本项目仅供学习和测试使用。

## 联系方式

如有问题或建议，请提交 Issue。

