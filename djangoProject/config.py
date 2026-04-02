"""
配置文件 - 用于管理应用配置
支持从环境变量读取配置，提供默认值
"""
import os
from pathlib import Path

# ===== 防火墙设备登录配置 =====
FIREWALL_LOGIN_USER = os.getenv('FIREWALL_LOGIN_USER', 'secadmin')
FIREWALL_LOGIN_PASSWORD = os.getenv('FIREWALL_LOGIN_PASSWORD', 'secAdmin#123456')
FIREWALL_LOGIN_PIN = os.getenv('FIREWALL_LOGIN_PIN', '')

# ===== Cookie 缓存配置 =====
COOKIE_CACHE_EXPIRY_MINUTES = int(os.getenv('COOKIE_CACHE_EXPIRY_MINUTES', '30'))

# ===== 请求配置 =====
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))  # 秒
# SSL 验证：生产环境应设为 True，开发环境可设为 False
SSL_VERIFY = os.getenv('SSL_VERIFY', 'False').lower() == 'true'

# ===== User-Agent 配置 =====
USER_AGENT = os.getenv('USER_AGENT',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

# ===== 日志配置 =====
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
