# -*- coding: utf-8 -*-
"""
http_handler.py - HTTP 协议测试处理器

功能：
- HTTP 客户端：发送请求、分析响应
- HTTP 服务端：简易 HTTP 服务器
- WAF 功能：请求方法检测、文件类型识别、关键字匹配
"""

import socket
import threading
import time
import re
import logging
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, List, Tuple
from io import BytesIO
import json

logger = logging.getLogger("HTTP")

# HTTP 请求方法列表
HTTP_METHODS = [
    'HEAD', 'GET', 'PUT', 'POST', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH',
    'PROPFIND', 'PROPPATCH', 'MKCOL', 'COPY', 'MOVE', 'LOCK', 'UNLOCK',
    'VERSION-CONTROL', 'CHECKOUT', 'UNCHECKOUT', 'CHECKIN', 'UPDATE', 'LABEL',
    'REPORT', 'MKWORKSPACE', 'MKACTIVITY', 'BASELINE-CONTROL', 'MERGE'
]

# 常见文件类型扩展名
FILE_EXTENSIONS = {
    'shell': ['.sh', '.bash', '.zsh', '.ksh'],
    'script': ['.py', '.pl', '.rb', '.php', '.js', '.vbs', '.ps1'],
    'executable': ['.exe', '.dll', '.so', '.dylib', '.bin'],
    'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
    'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'],
    'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico'],
    'audio': ['.mp3', '.wav', '.ogg', '.flac', '.aac'],
    'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'],
    'config': ['.conf', '.cfg', '.ini', '.yaml', '.yml', '.json', '.xml'],
    'database': ['.db', '.sqlite', '.sql', '.mdb'],
}

# 敏感关键字（可扩展）
SENSITIVE_KEYWORDS = [
    'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'auth',
    'admin', 'root', 'user', 'login', 'session', 'cookie',
    'exec', 'eval', 'system', 'shell', 'cmd', 'command',
    'select', 'insert', 'update', 'delete', 'drop', 'union',  # SQL
    '<script', 'javascript:', 'onerror', 'onload',  # XSS
]


class HTTPAnalyzer:
    """HTTP 流量分析器"""

    @staticmethod
    def detect_file_type(url: str, content_type: str = None) -> Dict[str, Any]:
        """检测文件类型"""
        result = {
            'extension': None,
            'category': None,
            'content_type': content_type
        }

        # 从 URL 提取扩展名
        if '.' in url.split('?')[0]:
            ext = '.' + url.split('?')[0].rsplit('.', 1)[-1].lower()
            result['extension'] = ext

            # 匹配类别
            for category, extensions in FILE_EXTENSIONS.items():
                if ext in extensions:
                    result['category'] = category
                    break

        # 从 Content-Type 判断
        if content_type:
            if 'image' in content_type:
                result['category'] = 'image'
            elif 'video' in content_type:
                result['category'] = 'video'
            elif 'audio' in content_type:
                result['category'] = 'audio'
            elif 'application' in content_type:
                if 'zip' in content_type or 'compressed' in content_type:
                    result['category'] = 'archive'
                elif 'pdf' in content_type:
                    result['category'] = 'document'
                elif 'javascript' in content_type or 'json' in content_type:
                    result['category'] = 'script'

        return result

    @staticmethod
    def extract_keywords(content: str, keywords: List[str] = None) -> List[str]:
        """提取关键字"""
        if keywords is None:
            keywords = SENSITIVE_KEYWORDS

        found = []
        content_lower = content.lower()
        for kw in keywords:
            if kw.lower() in content_lower:
                found.append(kw)
        return found

    @staticmethod
    def parse_request(raw_request: bytes) -> Dict[str, Any]:
        """解析 HTTP 请求"""
        result = {
            'method': None,
            'path': None,
            'version': None,
            'headers': {},
            'body': None,
            'header_length': 0,
            'body_length': 0,
            'keywords': [],
            'upload_type': None,
        }

        try:
            # 分离头部和正文
            if b'\r\n\r\n' in raw_request:
                header_part, body = raw_request.split(b'\r\n\r\n', 1)
                result['body'] = body.decode('utf-8', errors='ignore')
                result['body_length'] = len(body)
            else:
                header_part = raw_request
                result['body'] = ''

            result['header_length'] = len(header_part)

            # 解析请求行
            lines = header_part.decode('utf-8', errors='ignore').split('\r\n')
            if lines:
                request_line = lines[0].split(' ')
                if len(request_line) >= 2:
                    result['method'] = request_line[0]
                    result['path'] = request_line[1]
                    if len(request_line) >= 3:
                        result['version'] = request_line[2]

                # 解析头部
                for line in lines[1:]:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        result['headers'][key.strip()] = value.strip()

            # 检测上传文件类型
            if result['body'] and 'Content-Type' in result['headers']:
                if 'multipart/form-data' in result['headers']['Content-Type']:
                    result['upload_type'] = 'multipart'
                elif 'application/octet-stream' in result['headers']['Content-Type']:
                    result['upload_type'] = 'binary'

            # 提取关键字
            full_content = header_part.decode('utf-8', errors='ignore') + result['body']
            result['keywords'] = HTTPAnalyzer.extract_keywords(full_content)

        except Exception as e:
            logger.error(f'解析请求失败: {e}')

        return result

    @staticmethod
    def parse_response(raw_response: bytes) -> Dict[str, Any]:
        """解析 HTTP 响应"""
        result = {
            'status_code': None,
            'status_text': None,
            'version': None,
            'headers': {},
            'body': None,
            'header_length': 0,
            'body_length': 0,
            'content_type': None,
            'keywords': [],
            'file_type': None,
        }

        try:
            # 分离头部和正文
            if b'\r\n\r\n' in raw_response:
                header_part, body = raw_response.split(b'\r\n\r\n', 1)
                result['body'] = body.decode('utf-8', errors='ignore')
                result['body_length'] = len(body)
            else:
                header_part = raw_response
                result['body'] = ''

            result['header_length'] = len(header_part)

            # 解析状态行
            lines = header_part.decode('utf-8', errors='ignore').split('\r\n')
            if lines:
                status_line = lines[0].split(' ', 2)
                if len(status_line) >= 2:
                    result['version'] = status_line[0]
                    result['status_code'] = int(status_line[1])
                    if len(status_line) >= 3:
                        result['status_text'] = status_line[2]

                # 解析头部
                for line in lines[1:]:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        result['headers'][key.strip()] = value.strip()
                        if key.strip().lower() == 'content-type':
                            result['content_type'] = value.strip()

            # 提取关键字
            full_content = header_part.decode('utf-8', errors='ignore') + result['body']
            result['keywords'] = HTTPAnalyzer.extract_keywords(full_content)

        except Exception as e:
            logger.error(f'解析响应失败: {e}')

        return result


class HTTPClient:
    """HTTP 客户端"""

    def __init__(self):
        self.socket = None
        self.connected = False
        self.host = ''
        self.port = 80
        self.request_count = 0
        self.start_time = None
        self.log = []

    def send_request(self, host: str, port: int, method: str, path: str,
                     headers: Dict[str, str] = None, body: str = None,
                     timeout: float = 10.0) -> Tuple[bool, Dict[str, Any], str]:
        """发送 HTTP 请求"""
        try:
            # 记录请求开始时间
            if self.start_time is None:
                self.start_time = time.time()

            # 构建 HTTP 请求
            request_lines = [f"{method} {path} HTTP/1.1"]
            request_lines.append(f"Host: {host}")

            if headers:
                for key, value in headers.items():
                    request_lines.append(f"{key}: {value}")

            if body:
                request_lines.append(f"Content-Length: {len(body.encode('utf-8'))}")

            request_lines.append("Connection: close")
            request_lines.append("")

            if body:
                request_lines.append(body)
            else:
                request_lines.append("")

            raw_request = "\r\n".join(request_lines).encode('utf-8')

            # 解析请求
            request_info = HTTPAnalyzer.parse_request(raw_request)

            # 发送请求
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.sendall(raw_request)

            # 接收响应
            response_data = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk

            sock.close()

            # 解析响应
            response_info = HTTPAnalyzer.parse_response(response_data)

            # 更新统计
            self.request_count += 1
            elapsed = time.time() - self.start_time
            request_rate = self.request_count / elapsed if elapsed > 0 else 0

            # 检测文件类型
            file_type = HTTPAnalyzer.detect_file_type(path, response_info.get('content_type'))

            # 记录日志
            log_entry = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'method': method,
                'path': path,
                'status_code': response_info.get('status_code'),
                'request_header_length': request_info['header_length'],
                'request_body_length': request_info['body_length'],
                'response_header_length': response_info['header_length'],
                'response_body_length': response_info['body_length'],
                'keywords': request_info['keywords'] + response_info['keywords'],
                'file_type': file_type,
            }
            self.log.append(log_entry)

            result = {
                'request': request_info,
                'response': response_info,
                'file_type': file_type,
                'request_rate': request_rate,
                'total_requests': self.request_count,
            }

            return (True, result, "请求成功")

        except socket.timeout:
            return (False, {}, "请求超时")
        except socket.error as e:
            return (False, {}, f"连接错误: {e}")
        except Exception as e:
            logger.error(f'发送请求异常: {e}')
            return (False, {}, str(e))

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'total_requests': self.request_count,
            'elapsed_time': elapsed,
            'request_rate': self.request_count / elapsed if elapsed > 0 else 0,
            'log': self.log[-100:],  # 最近100条
        }

    def reset_stats(self):
        """重置统计"""
        self.request_count = 0
        self.start_time = None
        self.log = []


class CustomHTTPHandler(BaseHTTPRequestHandler):
    """自定义 HTTP 请求处理器"""

    # 类变量存储日志
    request_log = []
    server_instance = None

    def log_message(self, format, *args):
        """重写日志方法"""
        log_entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'client_ip': self.client_address[0],
            'method': self.command,
            'path': self.path,
            'version': self.request_version,
        }
        CustomHTTPHandler.request_log.append(log_entry)
        # 保留最近500条
        if len(CustomHTTPHandler.request_log) > 500:
            CustomHTTPHandler.request_log = CustomHTTPHandler.request_log[-500:]

    def do_GET(self):
        """处理 GET 请求"""
        self._handle_request('GET')

    def do_POST(self):
        """处理 POST 请求"""
        self._handle_request('POST')

    def do_PUT(self):
        """处理 PUT 请求"""
        self._handle_request('PUT')

    def do_DELETE(self):
        """处理 DELETE 请求"""
        self._handle_request('DELETE')

    def do_HEAD(self):
        """处理 HEAD 请求"""
        self._handle_request('HEAD', send_body=False)

    def do_OPTIONS(self):
        """处理 OPTIONS 请求"""
        self.send_response(200)
        self.send_header('Allow', 'GET, POST, PUT, DELETE, HEAD, OPTIONS')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_PATCH(self):
        """处理 PATCH 请求"""
        self._handle_request('PATCH')

    # WebDAV 方法
    def do_PROPFIND(self):
        self._handle_request('PROPFIND')

    def do_PROPPATCH(self):
        self._handle_request('PROPPATCH')

    def do_MKCOL(self):
        self._handle_request('MKCOL')

    def do_COPY(self):
        self._handle_request('COPY')

    def do_MOVE(self):
        self._handle_request('MOVE')

    def do_LOCK(self):
        self._handle_request('LOCK')

    def do_UNLOCK(self):
        self._handle_request('UNLOCK')

    def _handle_request(self, method, send_body=True):
        """统一处理请求"""
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b''

            # 解析请求
            raw_request = f"{method} {self.path} HTTP/1.1\r\n".encode()
            for key, value in self.headers.items():
                raw_request += f"{key}: {value}\r\n".encode()
            raw_request += b"\r\n"
            raw_request += body

            request_info = HTTPAnalyzer.parse_request(raw_request)

            # 构建响应
            response_body = json.dumps({
                'status': 'ok',
                'method': method,
                'path': self.path,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'request_info': {
                    'header_length': request_info['header_length'],
                    'body_length': request_info['body_length'],
                    'keywords': request_info['keywords'],
                }
            }, indent=2, ensure_ascii=False)

            response_bytes = response_body.encode('utf-8')

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(response_bytes))
            self.send_header('X-Request-Method', method)
            self.send_header('X-Header-Length', str(request_info['header_length']))
            self.end_headers()

            if send_body:
                self.wfile.write(response_bytes)

        except Exception as e:
            logger.error(f'处理请求失败: {e}')
            self.send_response(500)
            self.end_headers()


class HTTPServerWrapper:
    """HTTP 服务器包装器"""

    def __init__(self):
        self.server = None
        self.thread = None
        self.running = False
        self.port = 8080
        self.host = '0.0.0.0'

    def start(self, port: int = 8080, host: str = '0.0.0.0') -> Tuple[bool, str]:
        """启动 HTTP 服务器"""
        if self.running:
            return (False, "服务器已在运行")

        try:
            self.port = port
            self.host = host
            self.server = HTTPServer((host, port), CustomHTTPHandler)
            self.running = True

            def serve():
                logger.info(f'HTTP 服务器启动: {host}:{port}')
                while self.running:
                    self.server.handle_request()

            self.thread = threading.Thread(target=serve, daemon=True)
            self.thread.start()

            return (True, f"HTTP 服务器已启动: {host}:{port}")

        except Exception as e:
            logger.error(f'启动 HTTP 服务器失败: {e}')
            return (False, str(e))

    def stop(self) -> Tuple[bool, str]:
        """停止 HTTP 服务器"""
        if not self.running:
            return (False, "服务器未运行")

        try:
            self.running = False
            if self.server:
                self.server.shutdown()
                self.server = None
            return (True, "HTTP 服务器已停止")
        except Exception as e:
            logger.error(f'停止 HTTP 服务器失败: {e}')
            return (False, str(e))

    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        return {
            'running': self.running,
            'host': self.host,
            'port': self.port,
            'request_count': len(CustomHTTPHandler.request_log),
        }

    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取请求日志"""
        return CustomHTTPHandler.request_log[-limit:]

    def clear_logs(self):
        """清除日志"""
        CustomHTTPHandler.request_log = []