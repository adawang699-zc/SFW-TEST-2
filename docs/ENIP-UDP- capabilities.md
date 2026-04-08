# ENIP-UDP 功能码支持文档

## 概述

EtherNet/IP (ENIP) 支持通过 UDP 协议发送以下命令：

## UDP 端口

- **UDP 44818**: ENIP 显式消息封装
- **UDP 2222**: I/O 隐式消息（仅限连接式数据）

## UDP 44818 支持的功能码

### 1. ListServices (0x0004)

- **用途**: 获取设备支持的 ENIP 服务列表
- **CPF 载荷**: 无
- **响应**: 服务列表，包含协议版本和能力标志
- **实现位置**: `enip_handler.py:EnipClient.send_udp_command()`

### 2. ListIdentity (0x0063)

- **用途**: 获取设备标识信息（供应商 ID、设备类型、产品代码等）
- **CPF 载荷**: 无
- **响应**: Identity 结构 (36+ 字节)
- **实现位置**: `enip_handler.py:EnipClient.discover_devices()` (广播模式)
- **广播支持**: 可发送到 255.255.255.255 发现网段内所有设备

### 3. ListInterfaces (0x0064)

- **用途**: 获取网络接口列表
- **CPF 载荷**: 无
- **响应**: 接口信息结构
- **实现位置**: `enip_handler.py:EnipClient.send_udp_command()`

### 4. SendUnitData (0x0070)

- **用途**: 通过 UDP 发送 CIP 请求（非连接式或连接式）
- **CPF 载荷**: 
  - Null (0x0000) + Unconnected_Message (0x00B2) - 非连接式
  - Connection_Based (0x00A1) + Connected_Data (0x00B1) - 连接式
- **支持的 CIP 服务**: 所有 21 种 CIP 服务
  - 0x00: No_Operation (心跳)
  - 0x01: Get_Attribute_All
  - 0x02: Set_Attribute_All
  - 0x03: Get_Attribute_List
  - 0x04: Set_Attribute_List
  - 0x05: Reset
  - 0x06: Start
  - 0x07: Stop
  - 0x08: Create
  - 0x09: Delete
  - 0x0A: Multiple_Service_Packet
  - 0x0D: Apply_Attributes
  - 0x0E: Get_Attribute_Single
  - 0x10: Set_Attribute_Single
  - 0x11: Find_Next_Object
  - 0x15: Restore
  - 0x16: Save
  - 0x18: Get_Member
  - 0x19: Set_Member
  - 0x1A: Insert_Member
- **实现位置**: `enip_handler.py:EnipClient.send_udp_command()`

## UDP 2222 I/O 通信

### I/O 报文格式

- **CPF 项**: Sequenced_Address_Item (0x8002) + Connected_Data_Type (0x00B1)
- **用途**: 高速隐式 I/O 消息（周期型数据交换）
- **数据结构**:
  ```
  Item Count (2 字节)
  Sequenced_Address_Item:
    - Type: 0x8002
    - Length: 8
    - Connection ID (4 字节)
    - Sequence Number (4 字节)
  Connected_Data_Type:
    - Type: 0x00B1
    - Length: N
    - I/O Data (N 字节)
  ```
- **实现位置**: `enip_handler.py:EnipClient.send_io_data()`

## 代码示例

### UDP 命令发送

```python
from enip_handler import EnipClient

client = EnipClient()

# 发送 ListIdentity
success, result, message = client.send_udp_command(
    host="192.168.1.100",
    command=0x0063,  # ListIdentity
    port=44818,
    timeout=5.0
)

# 发送 SendUnitData (CIP Get_Attribute_Single)
cip_request = bytes([0x0E, 0x03, 0x20, 0x01, 0x24, 0x01])  # Get_Attribute_Single, Class 1, Instance 1
success, result, message = client.send_udp_command(
    host="192.168.1.100",
    command=0x0070,  # SendUnitData
    port=44818,
    payload=cpf_data,  # CPF 封装后的数据
    timeout=5.0
)
```

### I/O 数据发送

```python
# 发送 I/O 数据
io_data = bytes([0x01, 0x02, 0x03, 0x04])
success, result, message = client.send_io_data(
    host="192.168.1.100",
    io_data=io_data,
    connection_id=0x02730a85,
    port=2222,
    timeout=3.0
)
```

## 注意事项

1. **UDP 不可靠**: UDP 不保证数据到达，需要应用层处理超时和重传
2. **无会话要求**: UDP 命令不需要 RegisterSession（会话句柄可设为 0）
3. **广播限制**: 只有 ListIdentity 支持广播发现，其他命令必须单播
4. **MTU 限制**: UDP 数据包不应超过 512 字节，避免分片
5. **连接式数据**: I/O 通信需要预先建立连接（通过 SendRRData 配置）

## 相关文件

- `packet_agent/enip_handler.py`: ENIP 处理器（包含 UDP 客户端实现）
- `packet_agent/industrial_protocol_agent.py`: HTTP API 路由
- `apps/ENIP/enip_client_entry.py`: 参考实现
- `apps/ENIP/enip_common.py`: 公共常量和解析函数
