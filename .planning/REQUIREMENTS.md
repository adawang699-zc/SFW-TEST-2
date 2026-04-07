# 需求规格说明书

**创建日期:** 2026-03-27
**状态:** Active
**关联:** PROJECT.md

---

## v1 需求 (当前里程碑)

### Agent 管理

- [ ] **AGENT-01**: Agent 远程部署 - Web 页面一键推送 Agent 到测试设备
- [ ] **AGENT-02**: Agent 启停控制 - Web 页面远程启动/停止 Agent 进程
- [ ] **AGENT-03**: 文件传输 - Web 页面发送文件到测试设备
- [ ] **AGENT-04**: 命令执行 - Web 页面远程在测试设备上执行命令
- [ ] **AGENT-05**: Agent 状态监控 - 实时显示 Agent 在线/离线状态

### 测试设备功能

- [ ] **DEVICE-01**: 端口服务监听 - 监听 TCP/UDP 端口，检测服务可用性
- [ ] **DEVICE-02**: 报文发送 - 发送预设报文（TCP/UDP/ICMP）
- [ ] **DEVICE-03**: 报文回放 - 回放捕获的报文流量
- [ ] **DEVICE-04**: 端口扫描 - 对目标进行端口扫描检测
- [ ] **DEVICE-05**: DHCP 客户端 - 模拟 DHCP 客户端获取 IP
- [ ] **DEVICE-06**: Modbus TCP 协议模拟 - 作为 Master 或 Slave 进行通信测试
- [ ] **DEVICE-07**: S7comm 协议模拟 - 与 Siemens PLC 通信测试
- [ ] **DEVICE-08**: 报文捕获 - 捕获网络流量并保存

### 防火墙测试功能

- [ ] **FW-01**: 接口连通性测试 - 测试防火墙接口的 ping/响应
- [ ] **FW-02**: Syslog 日志接收 - 接收和解析防火墙 syslog 日志
- [ ] **FW-03**: SNMP 监控 - 通过 SNMP 获取防火墙状态信息
- [ ] **FW-04**: SNMP Trap 接收 - 接收和处理 SNMP Trap 告警

### 协议扩展 (Phase 2)

- [x] **PROTO-06**: GOOSE/SV 协议模拟 - IEC 61850 GOOSE/SV 报文发送（已完成）
- [ ] **PROTO-03**: EtherNet/IP 协议模拟 - ENIP Scanner/Adapter 通信
- [ ] **PROTO-01**: DNP3 协议模拟 - DNP3 Master/Outstation 通信
- [x] **PROTO-04**: BACnet 协议模拟 - BACnet Client/Device 通信
- [ ] **PROTO-08**: MMS/IEC 61850 协议模拟 - MMS Client/Server 通信

### 多用户并发支持

- [ ] **USER-01**: 测试组管理 - 创建和管理独立的测试环境组
- [ ] **USER-02**: 用户隔离 - 不同用户操作互不干扰
- [ ] **USER-03**: 资源预留 - 测试设备预留机制，避免冲突
- [ ] **USER-04**: 并发控制 - 支持约 3 组并发测试环境

### Web 管理功能

- [ ] **WEB-01**: 设备列表展示 - 展示所有测试设备及其状态
- [ ] **WEB-02**: 测试任务执行 - 执行预设测试场景
- [ ] **WEB-03**: 测试结果展示 - 显示测试输出和日志

---

## v2 需求 (后续里程碑)

### 协议扩展 (后续)

- [ ] **PROTO-02**: IEC 60870-5-104 协议模拟
- [ ] **PROTO-05**: OPC UA 协议模拟
- [ ] **PROTO-07**: 协议模糊测试引擎

### 高级功能

- [ ] **ADV-01**: 协议状态机测试
- [ ] **ADV-02**: 虚拟 PLC 仿真
- [ ] **ADV-03**: 攻击场景库 (MITRE ATT&CK for ICS)
- [ ] **ADV-04**: IEC 62443 合规性自动检查
- [ ] **ADV-05**: 自动化测试报告生成
- [ ] **ADV-06**: 流量基线学习

---

## 范围外 (Out of Scope)

| 排除项 | 原因 |
|--------|------|
| 完整 RBAC 权限系统 | 仅需简单权限，用户隔离测试组即可 |
| 大规模设备管理 (>10 组) | 当前需求约 3 组 |
| 全新 Web UI 设计 | 基于现有 Django 界面最小改动 |
| Profinet RT/IRT支持 | 需要专用网卡和内核驱动，过于复杂 |
| 真实攻击载荷执行 | 安全风险，仅模拟测试流量 |

---

## 可追溯性

| 来源 | 需求 |
|------|------|
| PROJECT.md 核心价值 | AGENT-01~05, DEVICE-01~08, FW-01~04, USER-01~04 |
| 研究 - FEATURED.md | DEVICE-06~08, PROTO-01~07, ADV-01~06 |
| 研究 - PITFALLS.md | USER-03~04 (并发隔离) |

## Phase 映射

| Requirement | Phase | Status |
|-------------|-------|--------|
| AGENT-01 | Phase 1 | Pending |
| AGENT-02 | Phase 1 | Pending |
| AGENT-03 | Phase 1 | Pending |
| AGENT-04 | Phase 1 | Pending |
| AGENT-05 | Phase 1 | Pending |
| DEVICE-01 | Phase 1 | Pending |
| DEVICE-02 | Phase 1 | Pending |
| DEVICE-03 | Phase 1 | Pending |
| DEVICE-04 | Phase 1 | Pending |
| DEVICE-05 | Phase 1 | Pending |
| DEVICE-06 | Phase 2 | Pending |
| DEVICE-07 | Phase 2 | Pending |
| DEVICE-08 | Phase 1 | Pending |
| FW-01 | Phase 2 | Pending |
| FW-02 | Phase 2 | Pending |
| FW-03 | Phase 2 | Pending |
| FW-04 | Phase 2 | Pending |
| PROTO-06 | Phase 2 | Done |
| PROTO-03 | Phase 2 | Planned |
| PROTO-01 | Phase 2 | Planned |
| PROTO-04 | Phase 2 | Planned |
| PROTO-08 | Phase 2 | Planned |
| USER-01 | Phase 3 | Pending |
| USER-02 | Phase 3 | Pending |
| USER-03 | Phase 3 | Pending |
| USER-04 | Phase 3 | Pending |
| WEB-01 | Phase 4 | Pending |
| WEB-02 | Phase 4 | Pending |
| WEB-03 | Phase 4 | Pending |

**Coverage:** 25/25 v1 requirements mapped (100%)

---

## 演化记录

| 日期 | 变更 | 原因 |
|------|------|------|
| 2026-03-27 | 初始创建 | 项目初始化 |
| 2026-03-27 | 添加 Phase 映射 | Roadmap 创建 |
| 2026-04-07 | PROTO-01/03/04/06/08 移至 v1 | Phase 2 协议扩展规划 |

---

*Last updated: 2026-04-07*
