# 项目路线图

**项目:** 工业防火墙自动化测试平台
**创建日期:** 2026-03-27
**粒度:** Coarse (3-5 阶段)

---

## Phases

- [ ] **Phase 1: Agent 基础设施 + 核心设备功能** - Agent 远程部署、控制、文件传输，基础网络设备功能
- [ ] **Phase 2: 核心工控协议 + 防火墙测试** - Modbus/S7 协议模拟，防火墙连通性/日志/监控测试
- [ ] **Phase 3: 多用户并发支持** - 测试组管理，用户隔离，资源预留，并发控制
- [ ] **Phase 4: Web 管理增强** - 设备列表展示，测试任务执行，测试结果展示

---

## Phase Details

### Phase 1: Agent 基础设施 + 核心设备功能
**Goal:** 实现 Agent 远程管理和基础网络设备测试能力
**Depends on:** 现有 Django 代码基础
**Requirements:** AGENT-01, AGENT-02, AGENT-03, AGENT-04, AGENT-05, DEVICE-01, DEVICE-02, DEVICE-03, DEVICE-04, DEVICE-05, DEVICE-08
**Success Criteria** (what must be TRUE):
  1. 用户可从 Web 页面一键推送 Agent 到测试设备并显示部署状态
  2. 用户可从 Web 页面启动/停止 Agent 并实时查看在线/离线状态
  3. 用户可从 Web 页面发送文件到测试设备并确认传输完成
  4. 用户可从 Web 页面远程执行命令并查看输出
  5. 测试设备可监听端口、发送报文、回放流量、执行端口扫描、捕获流量
**Plans:** 4 plans
**UI hint**: yes

Plans:
- [x] 01-agent-01-PLAN.md — Agent 部署和控制功能（AGENT-01, AGENT-02, AGENT-05）
- [x] 01-agent-02-PLAN.md — 文件传输和命令执行（AGENT-03, AGENT-04）
- [x] 01-agent-03-PLAN.md — 设备网络功能模块（DEVICE-01, DEVICE-02, DEVICE-03, DEVICE-04, DEVICE-08）
- [x] 01-agent-04-PLAN.md — Redis 分布式锁和设备预留（DEVICE-05, D-06, D-07, D-08）

### Phase 2: 核心工控协议 + 防火墙测试
**Goal:** 支持核心工控协议模拟和防火墙基础测试功能
**Depends on:** Phase 1 (Agent 和设备基础功能)
**Requirements:** DEVICE-06, DEVICE-07, FW-01, FW-02, FW-03, FW-04, PROTO-01, PROTO-02, PROTO-03, PROTO-04, PROTO-05
**Success Criteria** (what must be TRUE):
  1. 测试设备可作为 Modbus TCP Master/Slave 发送和响应协议报文
  2. 测试设备可与 Siemens PLC 建立 S7comm 连接并读写数据
  3. 用户可执行防火墙接口 ping 测试并查看连通性结果
  4. 用户可接收并查看防火墙 Syslog 日志
  5. 用户可通过 SNMP 获取防火墙状态信息并接收 SNMP Trap 告警
  6. 测试设备可作为 ENIP Scanner/Adapter 发送和响应 EtherNet/IP 报文
  7. 测试设备可作为 DNP3 Master/Outstation 发送和响应 DNP3 报文
  8. 测试设备可作为 BACnet Client/Device 发送和响应 BACnet 报文
  9. 测试设备可作为 MMS Client/Server 进行 IEC 61850 通信
**Plans:** 4 plans (protocol extension)

### Phase 3: 多用户并发支持
**Goal:** 支持多用户并发测试，测试环境隔离
**Depends on:** Phase 2 (核心功能可用)
**Requirements:** USER-01, USER-02, USER-03, USER-04
**Success Criteria** (what must be TRUE):
  1. 用户可创建测试组并分配独立的测试设备
  2. 不同用户的操作互不干扰，测试流量不泄漏到其他组
  3. 测试设备被预留后，其他用户无法占用
  4. 系统可同时支持至少 3 组独立并发测试环境
**Plans:** TBD
**UI hint**: yes

### Phase 4: Web 管理增强
**Goal:** 完善 Web 管理界面，支持测试场景执行和结果展示
**Depends on:** Phase 3 (多用户支持)
**Requirements:** WEB-01, WEB-02, WEB-03
**Success Criteria** (what must be TRUE):
  1. 用户可查看设备列表及各设备实时状态
  2. 用户可选择并执行预设测试场景
  3. 用户可查看测试执行输出和日志记录
**Plans:** TBD
**UI hint**: yes

---

## Requirement Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| AGENT-01 | Phase 1 | Planned |
| AGENT-02 | Phase 1 | Planned |
| AGENT-03 | Phase 1 | Planned |
| AGENT-04 | Phase 1 | Planned |
| AGENT-05 | Phase 1 | Planned |
| DEVICE-01 | Phase 1 | Planned |
| DEVICE-02 | Phase 1 | Planned |
| DEVICE-03 | Phase 1 | Planned |
| DEVICE-04 | Phase 1 | Planned |
| DEVICE-05 | Phase 1 | Planned |
| DEVICE-06 | Phase 2 | Pending |
| DEVICE-07 | Phase 2 | Pending |
| DEVICE-08 | Phase 1 | Planned |
| FW-01 | Phase 2 | Pending |
| FW-02 | Phase 2 | Pending |
| FW-03 | Phase 2 | Pending |
| FW-04 | Phase 2 | Pending |
| PROTO-01 | Phase 2 | Planned (ENIP) |
| PROTO-02 | Phase 2 | Planned (GOOSE/SV - Done) |
| PROTO-03 | Phase 2 | Planned (DNP3) |
| PROTO-04 | Phase 2 | Planned (BACnet) |
| PROTO-05 | Phase 2 | Planned (MMS) |
| USER-01 | Phase 3 | Pending |
| USER-02 | Phase 3 | Pending |
| USER-03 | Phase 3 | Pending |
| USER-04 | Phase 3 | Pending |
| WEB-01 | Phase 4 | Pending |
| WEB-02 | Phase 4 | Pending |
| WEB-03 | Phase 4 | Pending |

**Coverage:** 25/25 requirements mapped

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Agent 基础设施 + 核心设备功能 | 4/4 | Complete | 01-agent-01, 01-agent-02, 01-agent-03, 01-agent-04 |
| 2. 核心工控协议 + 防火墙测试 | 2/4 | In Progress | 02-enip, 02-bacnet |
| 3. 多用户并发支持 | 0/4 | Not started | - |
| 4. Web 管理增强 | 0/3 | Not started | - |

---

*Last updated: 2026-04-07*
