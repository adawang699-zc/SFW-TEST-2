# TCP 客户端重连 Pending 问题 - 诊断步骤

## 问题描述
TCP 客户端断开后重新连接，一直 pending（网络请求挂起，后端 API 没有返回）。

## 已添加的调试日志
已在 `connect_tcp_client` 函数中添加详细调试日志，包括：
- `[DEBUG] connect_tcp_client 开始执行`
- `[DEBUG] 参数解析完成`
- `[DEBUG] 准备获取锁` / `[DEBUG] 已获取锁`
- `[DEBUG] 状态已更新，准备释放锁`
- `[DEBUG] 锁已释放`
- `[DEBUG] 准备在锁外停止旧连接`
- `[DEBUG] old_manager.stop() 完成，耗时 X.XXs`
- `[DEBUG] 旧连接已停止`
- `[DEBUG] 准备创建 TCPClientManager`
- `[DEBUG] 准备调用 manager.connect()`
- `[DEBUG] manager.connect() 完成，总耗时 X.XXs`
- `[DEBUG] 准备返回结果`

## 诊断步骤

### 1. 上传文件到远程 Agent
将修复后的 `packet_agent.py` 上传到远程测试设备：
```bash
# 使用 SFTP 或 SCP 上传
scp packet_agent.py user@10.40.30.35:/packet_agent/
```

### 2. 验证文件已更新
SSH 登录远程主机，检查文件是否更新：
```bash
# 检查文件修改时间
ls -la /packet_agent/packet_agent.py

# 检查 MD5 哈希（应该与本地一致）
md5sum /packet_agent/packet_agent.py

# 检查关键调试日志行是否存在
grep -n "\[DEBUG\] connect_tcp_client 开始执行" /packet_agent/packet_agent.py
# 应该输出：4245:    add_service_log('TCP 客户端', '[DEBUG] connect_tcp_client 开始执行', 'info')
```

### 3. 重启 Agent 服务
```bash
# 停止旧进程
pkill -f packet_agent.py

# 等待几秒
sleep 2

# 启动新进程
cd /packet_agent
nohup python3 packet_agent.py > agent.log 2>&1 &

# 检查进程是否启动
ps aux | grep packet_agent
```

### 4. 测试重连场景

1. **启动 TCP 服务端**（端口 9000）
2. **客户端连接** - 观察日志：
   ```
   [DEBUG] connect_tcp_client 开始执行
   [DEBUG] 参数解析完成：server_ip=X.X.X.X, server_port=9000
   [DEBUG] 准备获取锁
   [DEBUG] 已获取锁
   [DEBUG] 状态已更新，准备释放锁
   [DEBUG] 锁已释放
   [DEBUG] 准备创建 TCPClientManager
   [DEBUG] 准备调用 manager.connect()
   [DEBUG] manager.connect() 完成，总耗时 X.XXs
   [DEBUG] 准备返回结果
   ```

3. **停止 TCP 服务端**

4. **重启 TCP 服务端**（同一端口 9000）

5. **客户端重新连接** - 观察日志：
   - 如果看到 `[DEBUG] 检测到旧连接仍在运行，old_manager=...`
   - 然后 `[DEBUG] old_manager.stop() 完成，耗时 X.XXs`
   - 最后 `[DEBUG] manager.connect() 完成，总耗时 X.XXs`
   - **说明修复生效，连接应该成功**

### 5. 分析问题

**如果日志在某一步后不再出现**，那就是问题所在：

| 日志最后出现位置 | 可能原因 |
|-----------------|----------|
| `准备获取锁` 之后没有 `已获取锁` | 锁被其他请求占用（检查是否有其他操作在进行） |
| `状态已更新，准备释放锁` 之后 | 可能在释放锁时出问题（罕见） |
| `准备在锁外停止旧连接` 之后 | `old_manager.stop()` 阻塞（死锁可能） |
| `old_manager.stop() 完成` 之后没有 `旧连接已停止` | `thread.join()` 阻塞（等待超时） |
| `准备调用 manager.connect()` 之后 | `manager.connect()` 阻塞 |
| `manager.connect() 完成` 之后没有 `准备返回结果` | 返回前处理阻塞 |
| 所有日志都出现，但请求仍 pending | API 响应返回有问题（Flask 响应问题） |

### 6. 收集日志

请将完整的 Agent 日志发送给我，包括：
- Django 页面的服务日志
- 远程 Agent 的 `agent.log` 文件内容

## 文件信息
- **本地文件:** `D:\自动化测试\SFW_CONFIG\djangoProject\packet_agent\packet_agent.py`
- **MD5 哈希:** `9785dd32f704f4421a2afd0b08ed5a7e`
- **文件大小:** ~0.42 MB
