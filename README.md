# 防火墙自动化测试系统

这是一个基于Django的防火墙设备自动化测试系统，用于与防火墙设备API交互并执行测试任务。

## 功能特性

- 🔐 Cookie缓存机制（30分钟有效期，可配置）
- 🔄 批量请求发送
- 📊 实时日志显示
- ⚙️ 灵活的配置管理
- 🛡️ 完善的错误处理

## 项目结构

```
djangoProject/
├── djangoProject/          # 项目主配置
│   ├── settings.py         # Django配置
│   ├── config.py           # 应用配置（从环境变量读取）
│   └── urls.py             # 主URL路由
├── main/                   # 主应用
│   ├── views_with_cache.py # 带缓存的视图
│   ├── cookie_utils.py     # Cookie缓存工具
│   └── urls_with_cache.py  # URL配置
├── templates/              # 前端模板
│   ├── base.html
│   ├── home.html
│   └── firewall_policy.html
└── cookie_cache/           # Cookie缓存目录
```

## 安装和配置

### 1. 安装依赖

```bash
pip install django requests
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置以下配置：

- `DJANGO_SECRET_KEY`: Django密钥（生产环境必须修改）
- `FIREWALL_LOGIN_USER`: 防火墙登录用户名
- `FIREWALL_LOGIN_PASSWORD`: 防火墙登录密码
- `COOKIE_CACHE_EXPIRY_MINUTES`: Cookie缓存过期时间（分钟）
- `SSL_VERIFY`: SSL证书验证（生产环境建议设为True）

### 3. 运行项目

```bash
# 监听所有地址（推荐）
python manage.py runserver 0.0.0.0:8000

# 或者使用启动脚本
# Windows:
start_django.bat

# Linux/Mac:
chmod +x start_django.sh
./start_django.sh
```

访问 http://localhost:8000 或 http://[你的IP]:8000

## API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 首页 |
| `/firewall/` | GET | 防火墙策略页面 |
| `/api/get_cookie/` | POST | 获取Cookie（带缓存） |
| `/api/send_custom_service/` | POST | 发送单个自定义服务请求 |
| `/api/send_custom_service_batch/` | POST | 批量发送自定义服务请求 |

## 使用说明

### 获取Cookie

```json
POST /api/get_cookie/
{
    "ip_address": "192.168.1.1"
}
```

### 发送自定义服务请求

```json
POST /api/send_custom_service/
{
    "ip_address": "192.168.1.1",
    "cookie": "your-cookie-here",
    "request_data": {
        "id": "1",
        "loginuser": "secadmin",
        "name": "service0",
        "desc": "desc",
        "content": "tcp;40000;0;0"
    }
}
```

### 批量发送请求

```json
POST /api/send_custom_service_batch/
{
    "ip_address": "192.168.1.1",
    "cookie": "your-cookie-here",
    "requests": [
        {
            "id": "1",
            "loginuser": "secadmin",
            "name": "service0",
            "desc": "desc",
            "content": "tcp;40000;0;0"
        },
        {
            "id": "2",
            "loginuser": "secadmin",
            "name": "service1",
            "desc": "desc",
            "content": "tcp;40001;0;0"
        }
    ]
}
```

## 安全注意事项

⚠️ **重要**：
- 生产环境必须修改 `SECRET_KEY`
- 生产环境建议启用 `SSL_VERIFY=True`
- 不要将 `.env` 文件提交到版本控制系统
- 使用环境变量管理敏感信息

## 优化内容

本次优化包括：

1. ✅ 配置管理：将硬编码的凭据移到环境变量
2. ✅ 批量请求API：实现了缺失的批量请求功能
3. ✅ 错误处理：改进了异常处理和日志记录
4. ✅ 代码清理：移除了前端未使用的代码
5. ✅ 日志系统：添加了完善的日志记录

## 开发

### 运行开发服务器

```bash
# 监听所有地址
python manage.py runserver 0.0.0.0:8000

# 或者使用启动脚本
start_django.bat  # Windows
./start_django.sh # Linux/Mac
```

### 数据库迁移

```bash
python manage.py makemigrations
python manage.py migrate
```

## 许可证

MIT License

