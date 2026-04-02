<!-- GSD:project-start source:PROJECT.md -->
## Project

**工业防火墙自动化测试平台**
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12.3 - 主要开发语言，用于后端 API、自动化测试、工控协议通信
- JavaScript - 前端交互逻辑
- HTML/CSS - 页面模板和样式
## Runtime
- Python 3.12.3
- pip - Python 包管理
- 无统一 lock 文件，使用多个 requirements.txt 分散管理
## Frameworks
- Django 5.1.2 - Web 框架，提供 API 和前端页面
- Flask 3.1.2 - 轻量级 API 服务（用于工控协议 Agent）
- Quart 0.20.0 - 异步 Web 框架
- CustomTkinter 5.2.2 - 桌面 GUI 框架
- PyQt5 5.15.11 / PyQt6 6.4.2 - 桌面应用 GUI
- Gradio 5.23.1 - 快速构建 Web UI
- Playwright 1.51.0 - 浏览器自动化测试
- Selenium 4.20.0 - Web 自动化测试
- Pytest 7.4.4 - 单元测试框架
- Robot Framework 6.0.2 - 关键字驱动测试框架
- PyInstaller 6.12.0 - Python 可执行文件打包
## Key Dependencies
- Scapy 2.5.0 - 网络报文生成和分析
- Paramiko 3.4.0 - SSH 远程管理和文件传输
- Requests 2.32.5 - HTTP 客户端
- Httpx 0.26.0 - 异步 HTTP 客户端
- PyModbus 3.7.0 - Modbus 工控协议
- Python-Snap7 2.0.2 - S7 工业以太网协议
- PySNMP 7.1.8 - SNMP 网络管理协议
- DNP3 21.6.19 - DNP3 远动协议
- BACpypes3 0.0.102 - BACnet 楼宇自控协议
- OpenOPC2 0.1.17 - OPC 工业通信协议
- PyComm3 1.2.16 - EtherNet/IP 协议
- Pandas 2.2.3 - 数据分析
- NumPy 2.2.4 - 数值计算
- OpenPyXL 3.1.5 - Excel 文件处理
- Python-Docx 1.2.0 - Word 文档处理
- Python-Pptx 1.0.2 - PowerPoint 文档处理
- ReportLab 4.4.9 - PDF 生成
- SQLAlchemy 2.0.25 - ORM 框架
- Flask-SQLAlchemy 3.0.5 - Flask ORM 集成
- AioSQLite 0.22.1 - 异步 SQLite
- psycopg2-binary 2.9.9 - PostgreSQL 驱动
- AsyncPG 0.29.0 - 异步 PostgreSQL
- LangChain 0.3.22 - LLM 应用开发框架
- LangChain-Anthropic/Google/OpenAI - 多模型支持
- Anthropic 0.49.0 - Claude API 客户端
- Google-GenerativeAI 0.8.4 - Google AI 客户端
- OpenAI 1.65.1 - OpenAI API 客户端
- Ollama 0.4.7 - 本地模型支持
- Transformers (通过 HuggingFace Hub 0.30.2)
- Browser-Use 0.1.40 - 浏览器操作封装
- WebDriver-Manager 4.0.2 - 浏览器驱动管理
- APScheduler 3.10.4 - 定时任务调度
- PyAutoGUI 0.9.54 - GUI 自动化
- PyWinAuto 0.6.9 - Windows 自动化
- PLYer 2.1.0 - 跨平台通知
- Pillow 12.1.0 - 图像处理
- OpenCV 4.11.0.86 - 计算机视觉
## Configuration
- 通过环境变量管理敏感配置
- 配置文件：`djangoProject/config.py`
- 关键配置项：
- 各子模块独立 requirements.txt：
## Platform Requirements
- Windows 11 (主要开发环境)
- Chrome 浏览器 (Playwright 测试)
- 工控设备测试环境
- 支持 Windows/Linux 部署
- 远程 Agent 支持 SSH 管理
## Database
- SQLite 3 (开发环境)
- 数据库文件：`db.sqlite3`
- PostgreSQL (生产环境，通过 psycopg2/asyncpg)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- 模块文件：`snake_case.py` - 例如 `cookie_utils.py`, `device_utils.py`, `license_utils.py`
- 视图文件：`views_with_cache.py`, `urls_with_cache.py`（带功能后缀）
- 配置文件：`settings.py`, `urls.py`, `config.py`
- 工具脚本：`build_exe.py`, `test_license_tools.py`
- 普通函数：`snake_case` - 例如 `get_cached_cookie()`, `save_cookie_to_cache()`
- 私有方法：`_snake_case` - 例如 `_decode_output()`, `_safe_exec_command()`
- 视图函数：`snake_case` - 例如 `firewall_policy()`, `packet_send()`, `port_scan()`
- API 视图：`{resource}_{action}` - 例如 `service_test_case_list()`, `device_add()`, `agent_start()`
- 局部变量：`snake_case` - 例如 `cookie_data`, `exit_status`, `ssh`
- 常量：`UPPER_SNAKE_CASE` - 例如 `COOKIE_CACHE_DIR`, `REQUEST_TIMEOUT`, `SSL_VERIFY`
- 类常量：大写字母定义列表 - 例如 `SERVICE_TYPES`, `OPERATION_TYPES`
- 类名：`PascalCase` - 例如 `RemoteAgentManager`, `PacketAgentClient`, `APIError`
- Django 模型：`PascalCase` - 例如 `S7ServerDBData`, `TestEnvironment`, `ServiceTestCase`
- Django Admin：`PascalCase` + `Config` 后缀 - 例如 `MainConfig`
- 类型注解使用 `typing` 模块：`Dict`, `List`, `Tuple`, `Optional`
## Code Style
- 行宽：无严格限制（部分文件超过 120 字符）
- 缩进：4 空格
- 引号：单引号优先 `'`，但部分文件混用
- 空行：函数间 2 行，类方法间 1 行
- 部分模块使用类型注解，主要是工具类模块
- 示例 (`main/agent_manager.py`):
## Error Handling
- 使用 `try-except` 捕获具体异常类型
- 记录日志后返回错误信息
- 自定义异常类 `APIError`:
- 统一错误响应格式:
- 常见异常处理:
## Logging
- `DEBUG`: 调试信息（如 Cookie 缓存命中）
- `INFO`: 一般操作信息（如连接成功、命令执行）
- `WARNING`: 警告（如编码尝试失败、端口占用）
- `ERROR`: 错误（如连接失败、请求异常）
- `CRITICAL`: 未使用
- `logs/django_{pid}.log` - Django 应用日志
- `logs/agent_{pid}.log` - Agent 管理日志
- 轮转配置：10MB 每文件，保留 5 个备份
## Comments
#!/usr/bin/env python3
- 中文注释，说明关键步骤
- 示例：
## Function Design
- 工具函数：20-50 行
- 视图函数：50-100 行
- 复杂业务逻辑：100-200 行（如 `agent_manager.py` 中的方法）
- 使用关键字参数默认值
- 复杂配置使用字典或单独的配置模块
- 工具函数：`Tuple[bool, str]`（成功标志 + 消息/错误）
- API 视图：`JsonResponse` 统一格式
- 查询函数：`Optional[Dict]` 或直接返回数据
## Module Design
- 模块通过 `__all__` 控制导出的较少
- 主要通过 `from module import specific_function` 导入
- 未使用 `__init__.py` 导出内容
- `main/__init__.py` 为空
## API 响应格式
## Django 模型规范
- `verbose_name`: 所有字段必须带中文名称
- `help_text`: 复杂字段提供说明
- `default`: 设置合理默认值
- `choices`: 枚举类型使用 choices
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Django monolith core for web UI and API management
- Remote agent-based packet sending via SSH/HTTP
- Industrial protocol support (GOOSE, SV, EtherCAT, PROFINET)
- Service deployment testing to firewall devices
- Real-time device monitoring with alerting
## Layers
- Purpose: User interface for all testing and management features
- Location: `templates/`
- Contains: 19 HTML templates using Bootstrap/Tailwind CSS
- Static assets: `static/css/`, `static/js/`, `static/webfonts/`
- Purpose: Core business logic, API endpoints, request handling
- Location: `main/`
- Contains: Views, models, utilities, service clients
- Key files: `main/views_with_cache.py`, `main/models.py`, `main/agent_manager.py`
- Depends on: Django framework, paramiko, requests, pysnmp
- Purpose: Packet sending, port scanning, service execution on remote hosts
- Location: `packet_agent/`
- Contains: Flask-based HTTP API servers
- Key files: `packet_agent/packet_agent.py`, `packet_agent/industrial_protocol_agent.py`
- Deployed to: Remote Linux/Windows test environments via SSH/SFTP
- Purpose: Send/receive industrial protocols (GOOSE, SV, EtherCAT, PROFINET, DCP)
- Location: `apps/goose_sv/`, `industrial_protocol_sender/`
- Contains: ASN.1 encoder/decoder, protocol senders/receivers
- Key files: `apps/goose_sv/goose_sender.py`, `apps/goose_sv/asn1_encoder.py`
- Purpose: Persistent storage for configurations, test cases, device info
- Location: `db.sqlite3` (SQLite)
- ORM: Django ORM with models in `main/models.py`
## Data Flow
## State Management
- SSH connections cached in `RemoteAgentManager.connections`
- Agent status tracked in `RemoteAgentManager.agent_status`
- Log monitoring threads in `RemoteAgentManager.log_threads`
- `S7ServerDBData`: S7 PLC DB block data
- `TestEnvironment`: Remote test environment credentials
- `TestDevice`: Device connection info
- `ServiceTestCase`: Service test configurations
## Entry Points
- Location: `manage.py`
- Triggers: CLI commands (runserver, migrate, shell)
- Responsibilities: Django management entry point
- Location: `djangoProject/wsgi.py`
- Triggers: HTTP requests from web server
- Responsibilities: WSGI callable for production deployment
- Location: `packet_agent/packet_agent.py`
- Triggers: HTTP API requests on port 8888
- Responsibilities: Packet sending, port scanning, service execution
- Location: `packet_agent/industrial_protocol_agent.py`
- Triggers: HTTP API requests on port 8889
- Responsibilities: Industrial protocol sending (GOOSE, SV, etc.)
## Error Handling
- Try-except blocks with specific exception types
- Error responses via `error_response()` helper in views
- Logging to rotating file handlers (`logs/django.log`, `logs/agent.log`)
- SSH connection cleanup on failure (`cleanup_stale_connections()`)
- Module import fallbacks with stub functions
## Cross-Cutting Concerns
- Django logging configured in `djangoProject/settings.py`
- RotatingFileHandler with 10MB limit, 5 backups
- Separate loggers for `main`, `main.agent_manager`, `django`
- Log files: `logs/django_{pid}.log`, `logs/agent_{pid}.log`
- Input validation in views before API calls
- Model field constraints (max_length, choices, null/blank)
- SSH command output validation
- Django admin authentication via `django.contrib.admin`
- Cookie caching for firewall device sessions (`main/cookie_utils.py`)
- SSH key/password authentication for remote hosts
- Environment variables via `djangoProject/config.py`
- Secrets from environment with defaults for development
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
