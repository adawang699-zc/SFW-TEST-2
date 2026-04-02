# Agent 文件自动同步功能

## 功能说明

监控本地 `packet_agent/` 目录下的必要文件变化，自动上传到远程主机并重启 Agent 服务。

## 同步的文件列表

只同步以下 **12 个必要文件**：

| 本地文件 | 远程路径 | 说明 |
|----------|----------|------|
| `packet_agent.py` | `C:/packet_agent/packet_agent.py` | 主 Agent |
| `industrial_protocol_agent.py` | `C:/packet_agent/industrial_protocol_agent.py` | 工业协议 Agent |
| `goose_sv_api.py` | `C:/packet_agent/goose_sv_api.py` | GOOSE/SV API |
| `mail_client.py` | `C:/packet_agent/mail_client.py` | 邮件客户端 |
| `agent/__init__.py` | `C:/packet_agent/agent/__init__.py` | Agent 模块初始化 |
| `agent/capture.py` | `C:/packet_agent/agent/capture.py` | 报文捕获模块 |
| `agent/command_executor.py` | `C:/packet_agent/agent/command_executor.py` | 命令执行模块 |
| `agent/file_transfer.py` | `C:/packet_agent/agent/file_transfer.py` | 文件传输模块 |
| `agent/listeners.py` | `C:/packet_agent/agent/listeners.py` | 监听器模块 |
| `agent/packet_sender.py` | `C:/packet_agent/agent/packet_sender.py` | 报文发送模块 |
| `agent/replay.py` | `C:/packet_agent/agent/replay.py` | 报文回放模块 |
| `agent/scanner.py` | `C:/packet_agent/agent/scanner.py` | 端口扫描模块 |

## 不同步的文件

以下文件**不会**被同步：

- ❌ 构建工具：`build/`, `dist/`, `*.spec`, `build_exe.py`, `*.bat`
- ❌ 可执行文件：`PsExec.exe`, `*.exe`
- ❌ 日志文件：`*.log`
- ❌ 缓存文件：`__pycache__/`, `*.pyc`, `*.pyo`
- ❌ 运行时数据：`mail_storage/`, `*.db`, `*.json`
- ❌ 测试数据：`http/`
- ❌ 文档：`README*`, `requirements.txt`

## 启用方式

### 方式 1：环境变量（推荐）

启动 Django 前设置环境变量：

```bash
# Windows PowerShell
$env:AGENT_AUTO_SYNC="true"
$env:AGENT_REMOTE_HOSTS="10.40.30.35,10.40.30.34"
$env:AGENT_SSH_USER="tdhx"
$env:AGENT_SSH_PASSWORD="tdhx@2017"
python manage.py runserver 0.0.0.0:8000

# Windows CMD
set AGENT_AUTO_SYNC=true
set AGENT_REMOTE_HOSTS=10.40.30.35,10.40.30.34
set AGENT_SSH_USER=tdhx
set AGENT_SSH_PASSWORD=tdhx@2017
python manage.py runserver 0.0.0.0:8000
```

### 方式 2：Web 界面

访问 `http://localhost:8000/agent-sync/` 手动启动同步服务。

### 方式 3：API 调用

```bash
# 启动同步
curl -X POST http://localhost:8000/api/agent-sync/start/ \
  -H "Content-Type: application/json" \
  -d '{
    "remote_hosts": ["10.40.30.35", "10.40.30.34"],
    "user": "tdhx",
    "password": "tdhx@2017",
    "port": 22
  }'

# 查看状态
curl http://localhost:8000/api/agent-sync/status/

# 停止同步
curl -X POST http://localhost:8000/api/agent-sync/stop/
```

## 工作原理

1. **文件监控**：每秒检查一次 `packet_agent/` 目录下的 `.py` 文件
2. **防抖处理**：检测到文件变化后等待 3 秒（防止编辑过程中频繁触发）
3. **自动上传**：使用 SFTP 上传文件到远程主机（临时文件 + 原子重命名）
4. **重启 Agent**：依次重启 packet_agent (8888) 和 industrial_protocol_agent (8889)

## 监控的文件

- `packet_agent/packet_agent.py` → `C:/packet_agent/packet_agent.py`
- `packet_agent/industrial_protocol_agent.py` → `C:/packet_agent/industrial_protocol_agent.py`

## 日志输出

同步日志输出到 Django 日志系统：

```
[INFO] 检测到文件变化：packet_agent.py
[INFO] 开始同步 1 个文件到远程主机...
[INFO] [10.40.30.35] 正在连接...
[INFO] [10.40.30.35] ✅ packet_agent.py 上传成功
[INFO] [10.40.30.35] 正在重启 Agent...
[INFO] [10.40.30.35] ✅ Agent 重启完成
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/agent-sync/status/` | GET | 获取同步状态 |
| `/api/agent-sync/start/` | POST | 启动同步 |
| `/api/agent-sync/stop/` | POST | 停止同步 |
| `/agent-sync/` | GET | 管理页面 |

## 状态字段

```json
{
  "running": false,      // 是否正在运行
  "enabled": true,       // 是否启用
  "watch_dir": "...",    // 监控目录
  "remote_hosts": [],    // 远程主机列表
  "pending_files": [],   // 待上传文件
  "uploading": false     // 是否正在上传
}
```

## 注意事项

1. **首次启用建议手动测试**：先手动上传一次确保 SSH 连接正常
2. **生产环境谨慎使用**：自动重启 Agent 可能导致测试中断
3. **文件锁定问题**：Windows 下确保文件未被其他进程占用
4. **冷却时间**：文件修改后 3 秒才上传，避免编辑过程中触发

## 关闭自动同步

### 临时关闭
访问 Web 界面点击"停止同步"按钮，或调用 API。

### 永久关闭
移除 `AGENT_AUTO_SYNC` 环境变量或设置为 `false`。

## 故障排除

### 连接失败
检查 SSH 凭据是否正确，远程主机是否可达。

### 上传失败
检查远程目录权限，确保 tdxh 用户有写入权限。

### Agent 重启失败
检查远程主机上是否已有 Agent 在运行，端口是否被占用。
