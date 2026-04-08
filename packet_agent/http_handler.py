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

# 常见文件类型扩展名映射（扩展名 -> 中文类型名）
FILE_TYPE_MAP = {
    # 图像
    '.png': 'PNG图像文件',
    '.jpg': 'JPEG图像文件',
    '.jpeg': 'JPEG图像文件',
    '.gif': 'GIF图像文件',
    '.bmp': 'BMP图像文件',
    '.svg': 'SVG图像文件',
    '.ico': 'ICO图标文件',
    '.webp': 'WebP图像文件',
    '.tiff': 'TIFF图像文件',
    '.tif': 'TIFF图像文件',
    # 音频
    '.mp3': 'MP3音频文件',
    '.wav': 'WAV音频文件',
    '.ogg': 'OGG音频文件',
    '.flac': 'FLAC音频文件',
    '.aac': 'AAC音频文件',
    '.wma': 'WMA音频文件',
    '.m4a': 'M4A音频文件',
    # 视频
    '.mp4': 'MP4视频文件',
    '.avi': 'AVI视频文件',
    '.mkv': 'MKV视频文件',
    '.mov': 'MOV视频文件',
    '.wmv': 'WMV视频文件',
    '.flv': 'FLV视频文件',
    '.webm': 'WebM视频文件',
    '.m4v': 'M4V视频文件',
    # 压缩
    '.zip': 'ZIP压缩文件',
    '.rar': 'RAR压缩文件',
    '.7z': '7Z压缩文件',
    '.tar': 'TAR压缩文件',
    '.gz': 'GZ压缩文件',
    '.bz2': 'BZ2压缩文件',
    '.xz': 'XZ压缩文件',
    # 文档
    '.pdf': 'PDF文件',
    '.doc': 'Word文档文件',
    '.docx': 'Word文档文件',
    '.xls': 'Excel文档文件',
    '.xlsx': 'Excel文档文件',
    '.ppt': 'PPT文档文件',
    '.pptx': 'PPT文档文件',
    '.txt': '文本文件',
    '.md': 'Markdown文件',
    '.csv': 'CSV文件',
    '.rtf': 'RTF文档文件',
    # 网络数据
    '.pcap': 'PCAP抓包文件',
    '.pcapng': 'PCAPNG抓包文件',
    '.cap': '抓包文件',
    # 脚本
    '.py': 'Python脚本文件',
    '.sh': 'Shell脚本文件',
    '.bash': 'Shell脚本文件',
    '.pl': 'Perl脚本文件',
    '.rb': 'Ruby脚本文件',
    '.php': 'PHP脚本文件',
    '.js': 'JavaScript脚本文件',
    '.ts': 'TypeScript脚本文件',
    '.vbs': 'VBScript脚本文件',
    '.ps1': 'PowerShell脚本文件',
    '.lua': 'Lua脚本文件',
    # 可执行
    '.exe': 'EXE可执行文件',
    '.dll': 'DLL动态库文件',
    '.so': 'SO动态库文件',
    '.bat': '批处理文件',
    '.cmd': '命令脚本文件',
    '.msi': 'MSI安装包',
    # 配置
    '.xml': 'XML文件',
    '.json': 'JSON文件',
    '.yaml': 'YAML配置文件',
    '.yml': 'YAML配置文件',
    '.ini': 'INI配置文件',
    '.conf': '配置文件',
    '.cfg': '配置文件',
    '.toml': 'TOML配置文件',
    # 数据库
    '.db': 'SQLite数据库文件',
    '.sqlite': 'SQLite数据库文件',
    '.sql': 'SQL脚本文件',
    '.mdb': 'Access数据库文件',
    # 网页
    '.html': 'HTML网页文件',
    '.htm': 'HTML网页文件',
    '.css': 'CSS样式文件',
    '.asp': 'ASP网页文件',
    '.aspx': 'ASP.NET网页文件',
    '.jsp': 'JSP网页文件',
    # 字体
    '.ttf': 'TTF字体文件',
    '.otf': 'OTF字体文件',
    '.woff': 'Web字体文件',
    '.woff2': 'Web字体文件',
    # 其他
    '.log': '日志文件',
    '.tmp': '临时文件',
    '.bak': '备份文件',
    '.jar': 'Java归档文件',
    '.war': 'Java Web归档文件',
    '.class': 'Java类文件',
}

# 文件类别映射
FILE_CATEGORY_MAP = {
    'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico', '.webp', '.tiff', '.tif'],
    'audio': ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma', '.m4a'],
    'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
    'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
    'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md', '.csv', '.rtf', '.html', '.htm', '.xml', '.json'],
    'script': ['.py', '.sh', '.bash', '.pl', '.rb', '.php', '.js', '.ts', '.vbs', '.ps1', '.lua', '.sql'],
    'executable': ['.exe', '.dll', '.so', '.bat', '.cmd', '.msi'],
    'config': ['.yaml', '.yml', '.ini', '.conf', '.cfg', '.toml'],
    'network': ['.pcap', '.pcapng', '.cap'],
    'database': ['.db', '.sqlite', '.mdb'],
    'font': ['.ttf', '.otf', '.woff', '.woff2'],
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
        """检测文件类型（基于URL扩展名）"""
        result = {
            'extension': None,
            'detected_type': '未知文件类型',
            'category': None,
            'content_type': content_type
        }

        # 从 URL 提取扩展名
        path = url.split('?')[0]  # 去掉查询参数
        if '.' in path:
            ext = '.' + path.rsplit('.', 1)[-1].lower()
            result['extension'] = ext

            # 查找文件类型
            if ext in FILE_TYPE_MAP:
                result['detected_type'] = FILE_TYPE_MAP[ext]
            else:
                result['detected_type'] = f'{ext[1:].upper()}文件'

            # 查找类别
            for category, extensions in FILE_CATEGORY_MAP.items():
                if ext in extensions:
                    result['category'] = category
                    break

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

            # 检测文件类型（基于URL扩展名）
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

            # 处理文件请求 /files/<filename>
            if self.path.startswith('/files/'):
                filename = self.path[7:]  # 去掉 /files/
                # 安全检查：防止路径遍历
                if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
                    self.send_response(403)
                    self.end_headers()
                    return

                file_path = os.path.join(file_manager.base_dir, filename)

                if method == 'GET':
                    # 下载文件
                    success, content, msg = file_manager.get_file(filename)
                    if success:
                        # 检测文件类型
                        type_info = detect_file_type_by_content(file_path)
                        content_type = 'application/octet-stream'
                        # 根据检测类型设置 Content-Type
                        if '图像' in type_info.get('detected_type', ''):
                            content_type = 'image/' + type_info.get('raw_type', 'png').split()[0].lower()
                        elif '文本' in type_info.get('detected_type', '') or 'JSON' in type_info.get('detected_type', ''):
                            content_type = 'text/plain'

                        self.send_response(200)
                        self.send_header('Content-Type', content_type)
                        self.send_header('Content-Length', len(content))
                        self.send_header('X-File-Type', type_info.get('detected_type', '未知'))
                        self.end_headers()
                        self.wfile.write(content)
                    else:
                        self.send_response(404)
                        self.send_header('Content-Type', 'application/json')
                        error_body = json.dumps({'error': msg})
                        self.send_header('Content-Length', len(error_body))
                        self.end_headers()
                        self.wfile.write(error_body.encode())
                    return

                elif method == 'PUT' or method == 'POST':
                    # 上传文件
                    success, type_info, msg = file_manager.save_file(filename, body)
                    if success:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        response_body = json.dumps({
                            'success': True,
                            'filename': filename,
                            'size': len(body),
                            'type': type_info.get('detected_type', '未知'),
                            'message': msg
                        })
                        self.send_header('Content-Length', len(response_body))
                        self.end_headers()
                        self.wfile.write(response_body.encode())
                    else:
                        self.send_response(500)
                        self.send_header('Content-Type', 'application/json')
                        error_body = json.dumps({'success': False, 'error': msg})
                        self.send_header('Content-Length', len(error_body))
                        self.end_headers()
                        self.wfile.write(error_body.encode())
                    return

                elif method == 'DELETE':
                    # 删除文件
                    success, msg = file_manager.delete_file(filename)
                    if success:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        response_body = json.dumps({'success': True, 'message': msg})
                        self.send_header('Content-Length', len(response_body))
                        self.end_headers()
                        self.wfile.write(response_body.encode())
                    else:
                        self.send_response(404)
                        self.send_header('Content-Type', 'application/json')
                        error_body = json.dumps({'success': False, 'error': msg})
                        self.send_header('Content-Length', len(error_body))
                        self.end_headers()
                        self.wfile.write(error_body.encode())
                    return

            # 默认响应（非文件请求）
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
        self.port = 80
        self.host = '0.0.0.0'

    def start(self, port: int = 80, host: str = '0.0.0.0') -> Tuple[bool, str]:
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


# ==================== 文件类型检测 ====================

import subprocess
import os
import platform

def detect_file_type_by_content(file_path: str) -> Dict[str, Any]:
    """
    检测文件类型（基于文件扩展名）

    Args:
        file_path: 文件路径

    Returns:
        dict: {
            'detected_type': '中文类型名',
            'extension': '扩展名',
            'category': '类别',
            'success': True/False
        }
    """
    result = {
        'detected_type': '未知文件类型',
        'extension': None,
        'category': None,
        'success': True
    }

    if not os.path.exists(file_path):
        result['success'] = False
        result['error'] = f'文件不存在: {file_path}'
        return result

    # 提取扩展名
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    result['extension'] = ext

    if ext in FILE_TYPE_MAP:
        result['detected_type'] = FILE_TYPE_MAP[ext]
    elif ext:
        result['detected_type'] = f'{ext[1:].upper()}文件'

    # 查找类别
    for category, extensions in FILE_CATEGORY_MAP.items():
        if ext in extensions:
            result['category'] = category
            break

    return result


# ==================== 文件管理器 ====================

class HTTPFileManager:
    """HTTP 文件管理器 - 管理上传/下载文件"""

    def __init__(self):
        # 默认文件目录
        self.base_dir = self._get_default_dir()
        self._ensure_dir()

    def _get_default_dir(self) -> str:
        """获取默认文件目录"""
        system = platform.system()
        if system == 'Windows':
            return r'C:\packet_agent\http'
        else:
            return '/opt/packet_agent/http'

    def _ensure_dir(self):
        """确保目录存在"""
        if not os.path.exists(self.base_dir):
            try:
                os.makedirs(self.base_dir, exist_ok=True)
                logger.info(f'创建 HTTP 文件目录: {self.base_dir}')
            except Exception as e:
                logger.error(f'创建目录失败: {e}')

    def set_base_dir(self, path: str):
        """设置基础目录"""
        self.base_dir = path
        self._ensure_dir()

    def list_files(self) -> List[Dict[str, Any]]:
        """列出所有文件"""
        files = []
        try:
            if not os.path.exists(self.base_dir):
                return files

            for filename in os.listdir(self.base_dir):
                file_path = os.path.join(self.base_dir, filename)
                if os.path.isfile(file_path):
                    # 获取文件信息
                    stat = os.stat(file_path)
                    # 检测文件类型
                    type_info = detect_file_type_by_content(file_path)

                    files.append({
                        'name': filename,
                        'path': file_path,
                        'size': stat.st_size,
                        'size_str': self._format_size(stat.st_size),
                        'modified': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime)),
                        'type': type_info['detected_type'],
                        'raw_type': type_info['raw_type'],
                    })
        except Exception as e:
            logger.error(f'列出文件失败: {e}')

        return files

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    def get_file(self, filename: str) -> Tuple[bool, bytes, str]:
        """
        获取文件内容（用于下载）

        Returns:
            (success, content, message)
        """
        file_path = os.path.join(self.base_dir, filename)

        if not os.path.exists(file_path):
            return (False, b'', f'文件不存在: {filename}')

        # 安全检查：防止路径遍历
        if not os.path.abspath(file_path).startswith(os.path.abspath(self.base_dir)):
            return (False, b'', '非法路径')

        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return (True, content, f'文件读取成功: {filename}')
        except Exception as e:
            return (False, b'', str(e))

    def save_file(self, filename: str, content: bytes) -> Tuple[bool, Dict[str, Any], str]:
        """
        保存文件（用于上传）

        Returns:
            (success, type_info, message)
        """
        file_path = os.path.join(self.base_dir, filename)

        # 安全检查：防止路径遍历
        if not os.path.abspath(file_path).startswith(os.path.abspath(self.base_dir)):
            return (False, {}, '非法路径')

        try:
            with open(file_path, 'wb') as f:
                f.write(content)

            # 检测文件类型
            type_info = detect_file_type_by_content(file_path)

            logger.info(f'文件保存成功: {file_path}, 类型: {type_info["detected_type"]}')
            return (True, type_info, f'文件上传成功: {filename}')
        except Exception as e:
            return (False, {}, str(e))

    def delete_file(self, filename: str) -> Tuple[bool, str]:
        """删除文件"""
        file_path = os.path.join(self.base_dir, filename)

        if not os.path.exists(file_path):
            return (False, f'文件不存在: {filename}')

        # 安全检查
        if not os.path.abspath(file_path).startswith(os.path.abspath(self.base_dir)):
            return (False, '非法路径')

        try:
            os.remove(file_path)
            return (True, f'文件删除成功: {filename}')
        except Exception as e:
            return (False, str(e))

    def analyze_file(self, filename: str) -> Dict[str, Any]:
        """分析文件"""
        file_path = os.path.join(self.base_dir, filename)

        if not os.path.exists(file_path):
            return {'success': False, 'error': f'文件不存在: {filename}'}

        result = {
            'success': True,
            'filename': filename,
            'path': file_path,
        }

        # 文件基本信息
        stat = os.stat(file_path)
        result['size'] = stat.st_size
        result['size_str'] = self._format_size(stat.st_size)
        result['modified'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))

        # 文件类型检测
        type_info = detect_file_type_by_content(file_path)
        result['type'] = type_info

        # 读取文件头部内容（用于关键字检测）
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4096)
            result['header_hex'] = header[:64].hex()

            # 尝试检测关键字
            try:
                text = header.decode('utf-8', errors='ignore')
                result['keywords'] = HTTPAnalyzer.extract_keywords(text)
            except:
                result['keywords'] = []
        except Exception as e:
            result['read_error'] = str(e)

        return result


# 全局文件管理器实例
file_manager = HTTPFileManager()