# 报文发送代理程序 (Packet Agent)

## 概述

这是一个运行在远程主机上的代理程序集合，通过HTTP API与Django后端通信，负责构造和发送原始网络报文，以及实现工控协议（Modbus、S7、GOOSE/SV）的客户端和服务器功能。

## 模块说明

### 1. packet_agent.py
**功能**: 通用报文发送代理程序
- **主要功能**:
  - 通过HTTP API接收报文配置并发送原始网络报文（TCP、UDP、ICMP等）
  - 支持报文变体（variations）功能，可自动生成多个变体报文
  - 提供网络接口列表查询功能
  - 支持TCP/UDP监听器、FTP服务器、HTTP服务器、邮件服务器等功能
  - 提供TCP/UDP客户端连接和发送功能
  - 实时统计发送速率和带宽
- **监听端口**: 默认 8888
- **依赖库**: flask, flask-cors, scapy, psutil

### 2. industrial_protocol_agent.py
**功能**: 工控协议代理程序
- **主要功能**:
  - **Modbus协议**:
    - Modbus TCP客户端：连接、读取、写入功能码（1-6, 15, 16）
    - Modbus TCP服务器：监听连接、处理读写请求、数据存储
    - 支持所有标准Modbus功能码
  - **S7协议**:
    - S7服务器：模拟Siemens S7 PLC，支持DB块、M区、I区、Q区数据访问
    - 支持多DB块（DB1、DB2、DB3）数据管理
    - 支持数据读写和实时更新
  - **GOOSE/SV协议**:
    - 集成GOOSE/SV API，提供网络接口查询功能
    - 作为GOOSE/SV服务的备用路由
- **监听端口**: 默认 8889
- **依赖库**: flask, flask-cors, pymodbus, python-snap7, psutil

### 3. goose_sv_api.py
**功能**: GOOSE/SV协议API模块（Flask Blueprint）
- **主要功能**:
  - GOOSE服务管理：启动、停止、状态查询
  - SV服务管理：启动、停止、状态查询
  - 网络接口列表查询
  - 报文计数统计
  - CORS支持
- **依赖库**: flask, goose_sender, sv_sender（来自apps/goose_sv目录）

### 4. 辅助模块

#### apps/goose_sv/goose_sender.py
**功能**: GOOSE报文发送服务
- 基于Scapy实现GOOSE报文构造和发送
- 支持ASN.1编码
- 报文计数功能

#### apps/goose_sv/sv_sender.py
**功能**: SV报文发送服务
- 基于Scapy实现SV报文构造和发送
- 支持ASN.1编码
- 报文计数功能

## 环境搭建

### Windows 环境

#### 1. 安装系统依赖

**安装 Npcap（必需）**:
- 下载地址: https://nmap.org/npcap/
- 安装时选择 "Install Npcap in WinPcap API-compatible Mode"
- 注意：Npcap是WinPcap的替代品，Scapy需要它来发送原始报文

#### 2. 安装 Python 环境

- **Python版本**: Python 3.7 或更高版本
- 下载地址: https://www.python.org/downloads/
- 安装时勾选 "Add Python to PATH"

#### 3. 安装 Python 依赖库

进入 `packet_agent` 目录，执行以下命令：

```bash
# 基础依赖（必需）
pip install flask>=2.0.0
pip install flask-cors>=3.0.0
pip install scapy>=2.4.5
pip install psutil>=5.8.0

# 工控协议依赖（可选，根据需要使用）
# Modbus协议支持
pip install pymodbus>=3.0.0

# S7协议支持
pip install python-snap7>=1.3
# 注意：python-snap7还需要安装底层snap7库
# Windows: 从 https://sourceforge.net/projects/snap7/files/ 下载并安装
# 将snap7.dll放到Python安装目录或系统PATH路径中

# 或使用requirements.txt一键安装
pip install -r requirements.txt
```

#### 4. 安装底层库（S7协议需要）

**安装 snap7 库（仅使用S7功能时需要）**:
1. 访问 https://sourceforge.net/projects/snap7/files/
2. 下载对应Windows版本的snap7库
3. 解压后将 `snap7.dll` 复制到：
   - Python安装目录（如 `C:\Python39\`）
   - 或系统PATH路径中的任意目录
   - 或与 `industrial_protocol_agent.py` 同目录

#### 5. 运行代理程序

**启动报文发送代理（端口8888）**:
```bash
python packet_agent.py --host 0.0.0.0 --port 8888
```

**启动工控协议代理（端口8889）**:
```bash
python industrial_protocol_agent.py 8889
```

**或使用批处理脚本（Windows）**:
```bash
# 启动所有服务
start_agent.bat

# 或简单启动
start_agent_simple.bat
```

### Linux 环境

#### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-pip python3-dev
sudo apt-get install libpcap-dev  # Scapy需要

# CentOS/RHEL
sudo yum install python3-pip python3-devel
sudo yum install libpcap-devel
```

#### 2. 安装 Python 依赖库

```bash
# 基础依赖
pip3 install flask>=2.0.0
pip3 install flask-cors>=3.0.0
pip3 install scapy>=2.4.5
pip3 install psutil>=5.8.0

# 工控协议依赖（可选）
pip3 install pymodbus>=3.0.0
pip3 install python-snap7>=1.3

# 或使用requirements.txt
pip3 install -r requirements.txt
```

#### 3. 安装底层库（S7协议需要）

**安装 snap7 库（仅使用S7功能时需要）**:
```bash
# 下载并编译snap7
wget https://sourceforge.net/projects/snap7/files/1.4.2/snap7-full-1.4.2.tar.gz
tar -xzf snap7-full-1.4.2.tar.gz
cd snap7-full-1.4.2/build/unix
make -f x86_64_linux.mk
sudo make -f x86_64_linux.mk install
sudo ldconfig
```

#### 4. 运行代理程序

**需要root权限或CAP_NET_RAW能力**:

```bash
# 启动报文发送代理（端口8888）
sudo python3 packet_agent.py --host 0.0.0.0 --port 8888

# 启动工控协议代理（端口8889）
sudo python3 industrial_protocol_agent.py 8889
```

**或设置CAP_NET_RAW能力（推荐，无需root）**:
```bash
sudo setcap cap_net_raw=eip /usr/bin/python3
python3 packet_agent.py --host 0.0.0.0 --port 8888
python3 industrial_protocol_agent.py 8889
```

## 依赖库说明

### 必需依赖

| 库名 | 版本要求 | 用途 |
|------|---------|------|
| flask | >=2.0.0 | HTTP API服务器框架 |
| flask-cors | >=3.0.0 | 跨域资源共享支持 |
| scapy | >=2.4.5 | 网络报文构造和发送 |
| psutil | >=5.8.0 | 系统信息获取（网卡列表等） |

### 可选依赖（工控协议）

| 库名 | 版本要求 | 用途 | 模块 |
|------|---------|------|------|
| pymodbus | >=3.0.0 | Modbus协议支持 | industrial_protocol_agent.py |
| python-snap7 | >=1.3 | S7协议支持 | industrial_protocol_agent.py |

### GOOSE/SV依赖

GOOSE/SV功能需要 `apps/goose_sv` 目录下的模块：
- `goose_sender.py`: GOOSE发送服务
- `sv_sender.py`: SV发送服务
- `asn1_encoder.py`: ASN.1编码器
- `asn1_decoder.py`: ASN.1解码器
- `network_utils.py`: 网络工具函数

这些模块会在Agent启动时自动上传到远程服务器。

## API接口

### packet_agent.py (端口8888)

#### 1. 获取网卡列表
```
GET /api/interfaces
Response: {
    "success": true,
    "interfaces": [
        {
            "name": "eth0",
            "display_name": "以太网",
            "ip": "192.168.1.100",
            "mac": "00:11:22:33:44:55",
            "status": "已启用",
            "mtu": 1500,
            "speed": 1000
        }
    ]
}
```

#### 2. 发送报文
```
POST /api/send_packet
Request Body: {
    "interface": "eth0",
    "packet_config": {
        "src_mac": "08:00:27:5A:9B:29",
        "dst_mac": "C4:A5:59:36:87:46",
        "src_ip": "4.4.4.34",
        "dst_ip": "4.4.4.34",
        "src_port": 3333,
        "dst_port": 9992,
        "protocol": "tcp",
        "data": "00 11 22 33 44 55"
    },
    "send_config": {
        "count": 1,
        "interval": 0,
        "continuous": false
    }
}
```

#### 3. 健康检查
```
GET /api/health
Response: {"status": "ok"}
```

### industrial_protocol_agent.py (端口8889)

#### 1. Modbus客户端
- `POST /api/industrial_protocol/modbus_client/connect` - 连接Modbus服务器
- `POST /api/industrial_protocol/modbus_client/disconnect` - 断开连接
- `GET /api/industrial_protocol/modbus_client/status` - 获取连接状态
- `POST /api/industrial_protocol/modbus_client/read` - 读取数据
- `POST /api/industrial_protocol/modbus_client/write` - 写入数据

#### 2. Modbus服务器
- `POST /api/industrial_protocol/modbus_server/start` - 启动Modbus服务器
- `POST /api/industrial_protocol/modbus_server/stop` - 停止服务器
- `GET /api/industrial_protocol/modbus_server/status` - 获取服务器状态
- `POST /api/industrial_protocol/modbus_server/set_data` - 设置服务器数据

#### 3. S7服务器
- `POST /api/industrial_protocol/s7_server/start` - 启动S7服务器
- `POST /api/industrial_protocol/s7_server/stop` - 停止服务器
- `GET /api/industrial_protocol/s7_server/status` - 获取服务器状态
- `POST /api/industrial_protocol/s7_server/get_data` - 读取数据
- `POST /api/industrial_protocol/s7_server/set_data` - 设置数据

#### 4. GOOSE/SV
- `GET /api/industrial_protocol/goose-sv/interfaces` - 获取网络接口列表
- `POST /api/industrial_protocol/goose-sv/goose/start` - 启动GOOSE服务
- `POST /api/industrial_protocol/goose-sv/goose/stop` - 停止GOOSE服务
- `GET /api/industrial_protocol/goose-sv/goose/status` - 获取GOOSE状态
- `POST /api/industrial_protocol/goose-sv/sv/start` - 启动SV服务
- `POST /api/industrial_protocol/goose-sv/sv/stop` - 停止SV服务
- `GET /api/industrial_protocol/goose-sv/sv/status` - 获取SV状态

## 打包为EXE（Windows）

### 使用批处理脚本（推荐）
```bash
build_exe.bat
```

### 使用Python脚本
```bash
pip install pyinstaller
python build_exe.py
```

生成的exe文件位于 `dist/packet_agent.exe`，可直接运行，无需Python环境。

详细说明请参考 `README_EXE.md`。

## 安全考虑

1. **认证**: 建议添加API密钥认证
2. **防火墙**: 只监听内网IP或使用VPN
3. **HTTPS**: 生产环境建议使用HTTPS
4. **权限**: Linux环境建议使用CAP_NET_RAW能力而非root权限

## 常见问题

### 1. Windows: Scapy无法发送报文
- 确保已安装Npcap
- 检查Npcap是否以WinPcap兼容模式安装
- 以管理员权限运行程序

### 2. Linux: Permission denied
- 使用sudo运行，或
- 设置CAP_NET_RAW能力: `sudo setcap cap_net_raw=eip /usr/bin/python3`

### 3. S7功能不可用
- 确保已安装python-snap7: `pip install python-snap7`
- 确保已安装底层snap7库（snap7.dll或libsnap7.so）
- 检查库文件路径是否正确

### 4. 网卡列表为空
- 确保已安装psutil: `pip install psutil`
- 检查网卡是否有有效IP地址（非127.0.0.1和0.0.0.0）

## 文件结构

```
packet_agent/
├── packet_agent.py              # 报文发送代理程序（端口8888）
├── industrial_protocol_agent.py # 工控协议代理程序（端口8889）
├── goose_sv_api.py              # GOOSE/SV API模块
├── requirements.txt             # Python依赖列表
├── build_exe.bat                # Windows打包脚本
├── build_exe.py                 # Python打包脚本
├── start_agent.bat              # Windows启动脚本
├── start_agent_simple.bat       # Windows简单启动脚本
├── README.md                    # 本文档
└── README_EXE.md                # EXE打包说明
```

## 版本历史

- **v1.0**: 基础报文发送功能
- **v2.0**: 添加工控协议支持（Modbus、S7）
- **v2.1**: 添加GOOSE/SV协议支持
- **v2.2**: 优化UI，添加报文计数功能
