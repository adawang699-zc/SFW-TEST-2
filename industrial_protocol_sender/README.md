# 工控协议报文发送器

独立可运行的工控二层协议报文发送工具，支持 GOOSE、SV、EtherCAT、POWERLINK、PNRT-DCP 五种协议。提供统一 GUI，可打包为 exe 在 Win7/Win10 上运行。

---

## 一、功能概述

- **网卡选择**：下拉选择发送网卡，支持刷新列表（兼容 Win7/Win10 网卡名称）
- **协议切换**：单选框切换五种协议，协议选项区域随协议动态切换
- **循环发送**：点击「开始发送」后按配置循环发送报文，点击「停止发送」停止
- **日志**：实时显示发送状态与错误信息

---

## 二、目录结构

| 文件 | 说明 |
|------|------|
| `main_gui.py` | 统一 GUI 入口，网卡/协议/选项/发送控制 |
| `asn1_encoder.py` | IEC 61850 GOOSE/SV 的 ASN.1 BER 编码 |
| `network_utils.py` | 网卡枚举与校验（psutil + scapy，兼容 Win7/Win10） |
| `goose_sender.py` | GOOSE 发送逻辑 |
| `sv_sender.py` | SV 发送逻辑 |
| `ethercat_sender.py` | EtherCAT 发送逻辑 |
| `powerlink_sender.py` | POWERLINK 发送逻辑 |
| `dcp_sender.py` | PROFINET DCP 发送逻辑 |
| `requirements.txt` | 依赖列表 |
| `build_exe.py` | PyInstaller 打包脚本 |
| `build_exe.bat` | 一键打包 exe |
| `run_gui.bat` | 直接运行 GUI（不打包） |

---

## 三、支持的协议及发送报文

### 1. GOOSE（IEC 61850-8-1）

| 项目 | 说明 |
|------|------|
| 目的 MAC | `01:0C:CD:01:00:01`（GOOSE 组播） |
| EtherType | `0x88B8` |
| 报文内容 | APPID + Length + Reserved + GOOSE PDU（gocbRef, datSet, stNum, sqNum, allData 等） |
| 可配置项 | AppID、GOCB 参考、数据集、数据（JSON，如 `{"Switch_1": true, "Switch_2": false}`） |
| 发送间隔 | 0.5 秒 |

### 2. SV（IEC 61850-9-2 采样值）

| 项目 | 说明 |
|------|------|
| 目的 MAC | `01:0C:CD:04:00:01`（SV 组播） |
| EtherType | `0x88BA` |
| 报文内容 | APPID + Length + Reserved + SV PDU（noASDU, seqASDU：svID, smpCnt, confRev, smpSynch, seqData） |
| 可配置项 | AppID（16384~32767）、svID、采样值（JSON，如 `{"Voltage_A": 220.1, "Current_A": 10.2}`） |
| 发送间隔 | 0.5 秒 |

### 3. EtherCAT

| 项目 | 说明 |
|------|------|
| EtherType | `0x88A4` |
| 报文内容 | EtherCAT 帧头 + 数据报（cmd, dlen, adp, ado, data, wkc） |
| 支持命令 | NOP、APRD、APWR、APRW、FPRD、FPWR、FPRW、BRD、BWR、LRD、LWR、LRW、LRMW、ARMW、FRMW |
| 可配置项 | 命令码（可多选，循环发送）、目标 MAC |
| 发送间隔 | 0.1 秒 |

### 4. POWERLINK

| 项目 | 说明 |
|------|------|
| EtherType | `0x88AB` |
| 报文内容 | SID + DA + SA + 各服务类型对应负载（SyncCounter、PDOData、Data 等） |
| 支持服务 | SoC、Preq、Pres、SoA、ASnd、AMNI |
| 可配置项 | 服务类型（可多选）、SA、DA（0–255） |
| 发送间隔 | 0.05 秒 |

### 5. PNRT-DCP（PROFINET 设备发现与配置）

| 项目 | 说明 |
|------|------|
| EtherType | `0x8892` |
| 报文内容 | FrameID + ServiceID + ServiceType + XID + DCP 数据（Option + Suboption 块） |
| 帧类型 | HELLO、GETORSET、IDENT_REQ、IDENT_RES |
| 服务码 | GET、SET、IDENTIFY、HELLO、RESERV、MANU |
| 可配置项 | 帧类型、服务码、Option、Suboption（根据 Option 动态显示，可多选） |
| 发送间隔 | 0.1 秒 |

**Option / Suboption 示例**（Option 变更时，Suboption 列表随之变化）：

- **IP**：0x01 MAC address、0x02 IP parameter、0x03 Full IP suite
- **DEVICE**：Type of Station、Name of Station、Device ID、Device Role 等 8 项
- **DHCP**：Host name、Vendor specific、Server identifier 等 9 项
- **CONTROL**：Start Transaction、End Transaction、Signal 等 6 项
- 以及 RESERVED、DEVICEINITIATIVE、NME_PARAMS、MANUF_X80~X86、ALLSECECTOR 等

---

## 四、使用说明

### 步骤

1. 运行程序（`python main_gui.py` 或 双击 `run_gui.bat`）
2. 在「网卡」区域选择发送网卡，必要时点击「刷新」
3. 在「协议类型」中选择：GOOSE、SV、EtherCAT、POWERLINK 或 PNRT-DCP
4. 在「协议选项」中填写或勾选该协议的可配置参数
5. 点击「开始发送」开始循环发送
6. 需要停止时点击「停止发送」
7. 在「日志」区域查看发送状态和报错信息

### 各协议简要配置说明

- **GOOSE**：AppID、GOCB 参考、数据集、数据 JSON（键值对，支持 bool/int/float/str）
- **SV**：AppID 须在 16384–32767 之间，svID 为 ASCII 字符串，采样值为浮点 JSON
- **EtherCAT**：勾选一个或多个命令码，填写目标 MAC
- **POWERLINK**：勾选一个或多个服务类型，填写 SA、DA（0–255）
- **PNRT-DCP**：选择帧类型、服务码、Option；Suboption 随 Option 变化，可多选，支持「全选」「取消全选」

---

## 五、运行方式

### 方式一：直接运行（需 Python 与依赖）

```bash
cd industrial_protocol_sender
pip install -r requirements.txt
python main_gui.py
```

或双击 `run_gui.bat`。

### 方式二：打包为 exe（Win7 / Win10）

```bash
cd industrial_protocol_sender
pip install -r requirements.txt
python build_exe.py
```

或双击 `build_exe.bat`。

生成的单文件 exe 位于：`dist/IndustrialProtocolSender.exe`。  
将 exe 拷贝到 Win7 或 Win10 机器上即可直接运行，无需安装 Python。

---

## 六、依赖

- Python 3.7+（打包 exe 建议 3.8，便于 Win7 兼容）
- scapy（二层报文构造与发送）
- psutil（网卡列表）
- PyInstaller（仅打包 exe 时需要）

---

## 七、注意事项

1. **管理员权限**：发送原始二层报文通常需要管理员权限，请以管理员身份运行 exe 或 Python 脚本。
2. **网卡选择**：确保所选网卡能进行二层收发；虚拟网卡、已禁用网卡可能无法正常发送。
3. **组播地址**：GOOSE、SV 使用组播 MAC，需确保交换机/网络支持组播。
4. **协议与网络**：不同协议适用于不同设备与网络，错误配置可能导致设备异常，请在测试环境中使用。
5. **JSON 格式**：GOOSE 数据、SV 采样值需为合法 JSON，格式错误会导致编码失败。
6. **SV AppID**：必须在 0x4000~0x7FFF（16384~32767）范围内。
7. **DCP Suboption**：必须至少勾选一个 Suboption，且所选 Suboption 需与当前 Option 匹配。
8. **发送间隔**：程序内部已设置固定间隔，长时间发送时注意网卡与设备负载。
