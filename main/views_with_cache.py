from django.shortcuts import render
import json
import requests
import logging
import socket
import threading
import time
import uuid
import subprocess
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import TestEnvironment, TestDevice, ServiceTestCase
from djangoProject.config import (
    FIREWALL_LOGIN_USER, FIREWALL_LOGIN_PASSWORD, FIREWALL_LOGIN_PIN,
    REQUEST_TIMEOUT, SSL_VERIFY, USER_AGENT
)
from .cookie_utils import get_cached_cookie, save_cookie_to_cache
from .device_utils import (
    execute, execute_in_vtysh, execute_in_backend,
    get_cpu_info, get_memory_info, get_network_info, get_coredump_files,
    test_connection, DEFAULT_USER, DEFAULT_PASSWORD
)
try:
    from .test_env_utils import (
        test_ssh_connection, upload_files_via_sftp,
        start_agent, stop_agent, check_agent_status
    )
except ImportError as e:
    logger.warning(f"测试环境模块导入失败: {e}")
    def test_ssh_connection(*args, **kwargs): return False
    def upload_files_via_sftp(*args, **kwargs): return False, '模块未加载', []
    def start_agent(*args, **kwargs): return False, '模块未加载'
    def stop_agent(*args, **kwargs): return False, '模块未加载'
    def check_agent_status(*args, **kwargs): return False
try:
    from .syslog_server import (
        start_syslog_server, stop_syslog_server, get_syslog_status,
        get_syslog_logs, clear_syslog_logs, set_syslog_filter_ip
    )
except ImportError as e:
    logger.warning(f"Syslog服务器模块导入失败: {e}")
    def start_syslog_server(*args, **kwargs): return False, '模块未加载'
    def stop_syslog_server(*args, **kwargs): return False, '模块未加载'
    def get_syslog_status(*args, **kwargs): return {}
    def get_syslog_logs(*args, **kwargs): return []
    def clear_syslog_logs(*args, **kwargs): return False, '模块未加载'
    def set_syslog_filter_ip(*args, **kwargs): return False, '模块未加载'
try:
    from .snmp_utils import (
        snmp_get, snmp_walk,
        start_trap_receiver, stop_trap_receiver, get_trap_receiver_status,
        get_trap_receiver_traps, clear_trap_receiver_traps, PYSNMP_AVAILABLE
    )
    if not PYSNMP_AVAILABLE:
        logger.warning("SNMP模块导入成功，但pysnmp不可用")
except ImportError as e:
    logger.warning(f"SNMP模块导入失败: {e}")
    import traceback
    logger.debug(traceback.format_exc())
    PYSNMP_AVAILABLE = False
except Exception as e:
    logger.warning(f"SNMP模块导入时发生异常: {e}")
    import traceback
    logger.debug(traceback.format_exc())
    PYSNMP_AVAILABLE = False

if not PYSNMP_AVAILABLE:
    def snmp_get(*args, **kwargs): return False, 'pysnmp未安装或导入失败，请检查pysnmp是否正确安装: pip install pysnmp'
    def snmp_walk(*args, **kwargs): return False, 'pysnmp未安装或导入失败，请检查pysnmp是否正确安装: pip install pysnmp'
    def start_trap_receiver(*args, **kwargs): return False, 'pysnmp未安装或导入失败，请检查pysnmp是否正确安装: pip install pysnmp'
    def stop_trap_receiver(*args, **kwargs): return False, 'pysnmp未安装或导入失败，请检查pysnmp是否正确安装: pip install pysnmp'
    def get_trap_receiver_status(*args, **kwargs): return {}
    def get_trap_receiver_traps(*args, **kwargs): return []
    def clear_trap_receiver_traps(*args, **kwargs): return False, 'pysnmp未安装或导入失败，请检查pysnmp是否正确安装: pip install pysnmp'
from .packet_agent_client import PacketAgentClient
try:
    from .device_monitor_task import (
        start_device_monitoring, stop_device_monitoring, is_device_monitoring,
        get_monitoring_status, get_alert_config, update_alert_config
    )
    from .email_utils import send_alert_email, format_alert_email_content
except ImportError as e:
    logger.warning(f"设备监测模块导入失败: {e}")
    # 提供占位函数避免错误
    def start_device_monitoring(*args, **kwargs): pass
    def stop_device_monitoring(*args, **kwargs): pass
    def is_device_monitoring(*args, **kwargs): return False
    def get_monitoring_status(*args, **kwargs): return {}
    def get_alert_config(*args, **kwargs): return {}
    def update_alert_config(*args, **kwargs): return False
    def send_alert_email(*args, **kwargs): return False
    def format_alert_email_content(*args, **kwargs): return ""
from .device_monitor_task import (
    start_device_monitoring, stop_device_monitoring, is_device_monitoring,
    get_monitoring_status, get_alert_config, update_alert_config
)
from .email_utils import send_alert_email, format_alert_email_content

# 配置日志

# ========== 统一的错误响应工具函数 ==========
class APIError(Exception):
    """API 错误异常"""
    def __init__(self, message, code=None):
        self.message = message
        self.code = code
        super().__init__(self.message)

def error_response(message, code=None, status=400):
    """统一错误响应格式"""
    response = {
        'success': False,
        'error': {
            'message': message,
            'code': code if code else 'INVALID_REQUEST'
        }
    }
    return JsonResponse(response, status=status)

def success_response(data=None, message='操作成功'):
    """统一成功响应格式"""
    response = {
        'success': True,
        'message': message,
        'data': data if data else {}
    }
    return JsonResponse(response)

logger = logging.getLogger(__name__)


def _send_api_request(request, api_endpoint, require_cookie=True):
    """
    通用的 API 请求处理函数

    Args:
        request: Django 请求对象
        api_endpoint: 目标 API 端点（如 'custom_service', 'addrlist' 等）
        require_cookie: 是否需要 cookie（默认 True）

    Returns:
        JsonResponse: 统一的 JSON 响应对象
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持 POST 请求'})

    try:
        data = json.loads(request.body)
        ip_address = data.get('ip_address', '').strip()
        cookie = data.get('cookie', '').strip()
        request_data = data.get('request_data', {})

        # 参数验证
        if not ip_address:
            return JsonResponse({'success': False, 'error': '缺少 IP 地址参数'})

        if require_cookie and not cookie:
            cookie = get_cached_cookie(ip_address)
            if not cookie:
                return JsonResponse({'success': False, 'error': '缺少 Cookie 参数，请先登录'})

        if not request_data:
            return JsonResponse({'success': False, 'error': '缺少请求数据参数'})

        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Cookie": cookie,
            "User-Agent": USER_AGENT,
        }

        # 构建请求 URL
        url = f"https://{ip_address}/{api_endpoint}"

        # 发送请求
        try:
            response = requests.post(
                url,
                json=request_data,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
        except requests.exceptions.Timeout:
            logger.error(f"请求超时：{ip_address} -> {api_endpoint}")
            return JsonResponse({'success': False, 'error': '请求超时，请检查网络连接'})
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常：{ip_address} -> {api_endpoint}, 错误：{str(e)}")
            return JsonResponse({'success': False, 'error': f'网络请求失败：{str(e)}'})

        # 处理响应
        if response.status_code == 200:
            return JsonResponse({
                'success': True,
                'response': response.text,
                'status_code': response.status_code
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'请求失败，状态码：{response.status_code}',
                'status_code': response.status_code
            })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"发送 API 请求时出错：{api_endpoint}, 错误：{e}")
        return JsonResponse({'success': False, 'error': '服务器内部错误'})

def home(request):
    """
    首页视图
    """
    return render(request, 'home.html')

def firewall_policy(request):
    """
    防火墙策略页面
    """
    return render(request, 'firewall_policy.html')

def packet_send(request):
    """
    报文发送页面
    """
    return render(request, 'packet_send.html')

def port_scan(request):
    """
    端口扫描页面
    """
    return render(request, 'port_scan.html')

def dhcp_client(request):
    """
    DHCP客户端页面
    """
    return render(request, 'dhcp_client.html')


def service_deploy(request):
    """
    服务下发页面
    """
    return render(request, 'service_deploy.html')


def industrial_protocol(request):
    """
    工控协议页面
    """
    return render(request, 'industrial_protocol.html')


def license_management(request):
    """授权管理页面"""
    return render(request, 'license_management.html')


@csrf_exempt
def generate_knowledge_license(request):
    """生成知识库授权（生成到临时目录，返回文件内容供下载）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        machine_code = data.get('machine_code', '').strip()
        vul_expire = data.get('vul_expire', 30)
        virus_expire = data.get('virus_expire', 60)
        rules_expire = data.get('rules_expire', 50)
        # save_path 不再必需，如果提供则使用，否则生成到临时目录
        
        if not machine_code:
            return JsonResponse({'success': False, 'error': '缺少机器码参数'})
        
        from .license_utils import generate_knowledge_license as gen_license
        
        # 不传save_path，生成到临时目录并返回文件内容
        save_path = data.get('save_path', '').strip()
        if not save_path:
            save_path = None  # 生成到临时目录
        
        success, result = gen_license(machine_code, vul_expire, virus_expire, rules_expire, save_path)
        
        if success:
            return JsonResponse({
                'success': True,
                **result
            })
        else:
            return JsonResponse({'success': False, 'error': result})
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON格式'})
    except Exception as e:
        logger.exception(f"生成知识库授权异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def decrypt_knowledge_license(request):
    """解密知识库授权"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        file_path = data.get('file_path', '').strip()
        
        if not file_path:
            return JsonResponse({'success': False, 'error': '缺少文件路径参数'})
        
        if not os.path.exists(file_path):
            return JsonResponse({'success': False, 'error': '授权文件不存在'})
        
        # 查找授权工具路径
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        license_dir = os.path.join(project_root, 'license')
        
        # 可能的工具路径
        possible_paths = [
            os.path.join(license_dir, 'hx_knowledge_license_gender.exe'),
            os.path.join(license_dir, 'hx_knowledge_license_gender'),
            'hx_knowledge_license_gender.exe',
            'hx_knowledge_license_gender'
        ]
        
        tool_path = None
        for path in possible_paths:
            if os.path.exists(path):
                tool_path = path
                break
            # 如果是相对路径，也尝试在PATH中查找
            if not os.path.isabs(path):
                try:
                    subprocess.run([path, '--help'], capture_output=True, timeout=5)
                    tool_path = path
                    break
                except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
                    continue
        
        if not tool_path:
            return JsonResponse({
                'success': False, 
                'error': f'找不到 hx_knowledge_license_gender 程序。请将程序放置在 {license_dir} 目录下或确保在系统PATH中可用。'
            })
        
        # 构建命令
        cmd = [
            tool_path,
            'dec',
            '-i',
            file_path
        ]
        
        logger.info(f"执行知识库授权解密命令: {' '.join(cmd)}")
        logger.info(f"使用工具路径: {tool_path}")
        
        # 执行命令
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=license_dir if os.path.exists(license_dir) else os.path.dirname(os.path.abspath(__file__))
            )
            
            if result.returncode == 0:
                return JsonResponse({
                    'success': True,
                    'content': result.stdout.strip() if result.stdout else '解密成功'
                })
            else:
                error_msg = result.stderr.strip() if result.stderr else f'命令执行失败，返回码: {result.returncode}'
                logger.error(f"知识库授权解密失败: {error_msg}")
                return JsonResponse({'success': False, 'error': error_msg})
                
        except subprocess.TimeoutExpired:
            return JsonResponse({'success': False, 'error': '命令执行超时'})
        except FileNotFoundError:
            return JsonResponse({'success': False, 'error': '找不到 hx_knowledge_license_gender 程序'})
        except Exception as e:
            logger.exception(f"知识库授权解密异常: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON格式'})
    except Exception as e:
        logger.exception(f"解密知识库授权异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


# 存储生成的授权文件
device_license_files = {}


@csrf_exempt
def test_device_license_connection(request):
    """测试设备授权服务器连接"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from .license_utils import test_device_license_connection as test_connection
        
        success, result = test_connection()
        
        if success:
            return JsonResponse({'success': True, 'message': result})
        else:
            return JsonResponse({'success': False, 'error': result})
            
    except Exception as e:
        logger.exception(f"测试设备授权服务器连接异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def generate_device_license(request):
    """生成设备授权"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from .license_utils import generate_device_license as gen_device_license
        
        data = json.loads(request.body)
        auth_name = data.get('name', '').strip()
        machine_code = data.get('machine_code', '').strip()
        
        if not auth_name or not machine_code:
            return JsonResponse({'success': False, 'error': '缺少必要参数'})
        
        success, result = gen_device_license(auth_name, machine_code)
        
        if success:
            # 存储文件内容供下载
            device_license_files[result['filename']] = {
                'content': result['content'],
                'timestamp': time.time(),
                'machine_code': machine_code
            }
            
            return JsonResponse({
                'success': True,
                'filename': result['filename'],
                'message': result['message']
            })
        else:
            return JsonResponse({'success': False, 'error': result})
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON格式'})
    except Exception as e:
        logger.exception(f"生成设备授权异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


def download_device_license(request):
    """下载设备授权文件"""
    filename = request.GET.get('filename', '').strip()
    
    if not filename:
        return JsonResponse({'success': False, 'error': '缺少文件名参数'})
    
    if filename not in device_license_files:
        return JsonResponse({'success': False, 'error': '文件不存在或已过期'})
    
    try:
        file_info = device_license_files[filename]
        file_content = file_info['content']
        
        # 创建文件响应
        response = HttpResponse(file_content, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(file_content)
        
        logger.info(f"下载设备授权文件: {filename}")
        
        return response
        
    except Exception as e:
        logger.exception(f"下载设备授权文件异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


# ==================== Agent管理相关视图 ====================

@csrf_exempt
def agent_connect(request):
    """连接到远程主机"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from .agent_manager import agent_manager
        
        data = json.loads(request.body)
        host = data.get('host', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        port = data.get('port', 22)
        
        if not all([host, username, password]):
            missing_params = []
            if not host: missing_params.append('host')
            if not username: missing_params.append('username') 
            if not password: missing_params.append('password')
            error_msg = f'缺少必要参数: {", ".join(missing_params)}'
            return JsonResponse({'success': False, 'error': error_msg})
        
        success, message = agent_manager.connect_to_host(host, username, password, port)
        
        if success:
            # 检测系统类型
            system_type = agent_manager.detect_system_type(host, port)
            return JsonResponse({
                'success': True,
                'message': message,
                'system_type': system_type
            })
        else:
            return JsonResponse({'success': False, 'error': message})
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        return JsonResponse({'success': False, 'error': '无效的JSON格式'})
    except Exception as e:
        logger.exception(f"连接远程主机异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def agent_disconnect(request):
    """断开远程主机连接"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from .agent_manager import agent_manager
        
        data = json.loads(request.body)
        host = data.get('host', '').strip()
        port = data.get('port', 22)
        
        if not host:
            return JsonResponse({'success': False, 'error': '缺少主机参数'})
        
        success = agent_manager.disconnect_from_host(host, port)
        
        if success:
            return JsonResponse({'success': True, 'message': '断开连接成功'})
        else:
            return JsonResponse({'success': False, 'error': '断开连接失败'})
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON格式'})
    except Exception as e:
        logger.exception(f"断开远程主机连接异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def agent_upload(request):
    """上传Agent文件"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from .agent_manager import agent_manager
        
        data = json.loads(request.body)
        host = data.get('host', '').strip()
        port = data.get('port', 22)
        remote_path = data.get('remote_path', '').strip()
        force = data.get('force', False)  # 是否强制上传
        
        if not all([host, remote_path]):
            return JsonResponse({'success': False, 'error': '缺少必要参数'})
        
        # 本地Agent文件路径
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_path = os.path.join(project_root, 'packet_agent', 'packet_agent.py')
        
        if not os.path.exists(local_path):
            return JsonResponse({'success': False, 'error': '本地Agent文件不存在'})
        
        success, message = agent_manager.upload_agent(host, local_path, remote_path, port, force)
        
        if success:
            return JsonResponse({'success': True, 'message': message})
        else:
            return JsonResponse({'success': False, 'error': message})
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON格式'})
    except Exception as e:
        logger.exception(f"上传Agent文件异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def agent_check_file(request):
    """检查Agent文件一致性"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from .agent_manager import agent_manager
        
        data = json.loads(request.body)
        host = data.get('host', '').strip()
        port = data.get('port', 22)
        remote_path = data.get('remote_path', '').strip()
        
        if not all([host, remote_path]):
            return JsonResponse({'success': False, 'error': '缺少必要参数'})
        
        # 本地Agent文件路径
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_path = os.path.join(project_root, 'packet_agent', 'packet_agent.py')
        
        if not os.path.exists(local_path):
            return JsonResponse({'success': False, 'error': '本地Agent文件不存在'})
        
        is_consistent, message = agent_manager.check_file_consistency(host, local_path, remote_path, port)
        
        return JsonResponse({
            'success': True, 
            'consistent': is_consistent,
            'message': message
        })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON格式'})
    except Exception as e:
        logger.exception(f"检查Agent文件一致性异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def agent_start(request):
    """启动远程Agent"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from .agent_manager import agent_manager
        
        data = json.loads(request.body)
        host = data.get('host', '').strip()
        port = data.get('port', 22)
        agent_path = data.get('agent_path', '').strip()
        agent_port = data.get('agent_port', 8888)
        
        if not all([host, agent_path]):
            return JsonResponse({'success': False, 'error': '缺少必要参数'})
        
        logger.info(f'[API] 开始启动Agent: host={host}, port={port}, agent_path={agent_path}, agent_port={agent_port}')
        start_time = time.time()
        
        try:
            success, message = agent_manager.start_agent(host, agent_path, port, agent_port)
            elapsed_time = time.time() - start_time
            
            logger.info(f'[API] Agent启动完成: success={success}, message={message}, 耗时={elapsed_time:.2f}秒')
            
            if success:
                return JsonResponse({'success': True, 'message': message, 'elapsed_time': f'{elapsed_time:.2f}秒'})
            else:
                return JsonResponse({'success': False, 'error': message})
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f'[API] Agent启动异常: {e}, 耗时={elapsed_time:.2f}秒')
            import traceback
            logger.error(f'[API] 详细错误: {traceback.format_exc()}')
            return JsonResponse({'success': False, 'error': f'启动异常: {str(e)}'})
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON格式'})
    except Exception as e:
        logger.exception(f"启动远程Agent异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def agent_stop(request):
    """停止远程Agent"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from .agent_manager import agent_manager
        
        data = json.loads(request.body)
        host = data.get('host', '').strip()
        port = data.get('port', 22)
        agent_port = data.get('agent_port', 8888)
        
        if not host:
            return JsonResponse({'success': False, 'error': '缺少主机参数'})
        
        success, message = agent_manager.stop_agent(host, port, agent_port)
        
        if success:
            return JsonResponse({'success': True, 'message': message})
        else:
            return JsonResponse({'success': False, 'error': message})
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON格式'})
    except Exception as e:
        logger.exception(f"停止远程Agent异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def agent_status(request):
    """获取Agent状态"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        from .agent_manager import agent_manager
        
        host = request.GET.get('host', '').strip()
        port = int(request.GET.get('port', 22))
        agent_port = int(request.GET.get('agent_port', 8888))
        
        if host:
            # 获取单个主机的Agent状态
            is_running, status_msg = agent_manager.check_agent_status(host, port, agent_port)
            return JsonResponse({
                'success': True,
                'running': is_running,
                'status': status_msg
            })
        else:
            # 获取所有Agent状态
            all_status = agent_manager.get_all_agent_status()
            return JsonResponse({
                'success': True,
                'agents': all_status
            })
            
    except Exception as e:
        logger.exception(f"获取Agent状态异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def agent_logs(request):
    """获取Agent日志"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        from .agent_manager import agent_manager
        
        host = request.GET.get('host', '').strip()
        port = int(request.GET.get('port', 22))
        lines = int(request.GET.get('lines', 20))
        real_time = request.GET.get('realtime', 'false').lower() == 'true'
        
        if not host:
            return JsonResponse({'success': False, 'error': '缺少主机参数'})
        
        if real_time:
            # 获取实时日志
            recent_logs = agent_manager.get_recent_logs(host, port)
            return JsonResponse({
                'success': True,
                'logs': '\n'.join(recent_logs[-lines:]) if recent_logs else '暂无实时日志'
            })
        else:
            # 获取历史日志
            success, logs = agent_manager.get_agent_logs(host, port, lines)
            if success:
                return JsonResponse({'success': True, 'logs': logs})
            else:
                return JsonResponse({'success': False, 'error': logs})
            
    except Exception as e:
        logger.exception(f"获取Agent日志异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def agent_test_network(request):
    """测试网络连通性"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from .agent_manager import agent_manager
        
        data = json.loads(request.body)
        host = data.get('host', '').strip()
        port = data.get('port', 22)
        
        if not host:
            return JsonResponse({'success': False, 'error': '缺少主机参数'})
        
        success, message = agent_manager.test_network_connectivity(host, port)
        
        if success:
            return JsonResponse({'success': True, 'message': message})
        else:
            return JsonResponse({'success': False, 'error': message})
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        return JsonResponse({'success': False, 'error': '无效的JSON格式'})
    except Exception as e:
        logger.exception(f"测试网络连通性异常: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


def device_monitor(request):
    """
    测试设备监控页面
    """
    return render(request, 'device_monitor.html')


@csrf_exempt
def device_list(request):
    """获取所有测试设备"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        devices = TestDevice.objects.all().values()
        device_list = list(devices)
        return JsonResponse({'success': True, 'devices': device_list})
    except Exception as e:
        logger.exception(f"获取设备列表时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def device_add(request):
    """添加设备"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        device_type = data.get('type', '').strip()
        ip = data.get('ip', '').strip()
        port = int(data.get('port', 22))
        user = data.get('user', 'admin').strip()
        password = data.get('password', 'tdhx@2017')
        description = data.get('description', '').strip()

        if not name or not device_type or not ip:
            return JsonResponse({'success': False, 'error': '请填写必填项'})

        device = TestDevice.objects.create(
            name=name,
            type=device_type,
            ip=ip,
            port=port,
            user=user,
            password=password,
            description=description
        )
        return JsonResponse({'success': True, 'message': '设备已添加', 'device_id': device.id})
    except Exception as e:
        logger.exception(f"添加设备时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def device_update(request):
    """更新设备信息"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        device_id = data.get('id')
        if not device_id:
            return JsonResponse({'success': False, 'error': '设备ID不能为空'})

        device = TestDevice.objects.get(id=device_id)
        device.name = data.get('name', device.name).strip()
        device.type = data.get('type', device.type).strip()
        device.ip = data.get('ip', device.ip).strip()
        device.port = int(data.get('port', device.port))
        device.user = data.get('user', device.user).strip()
        device.password = data.get('password', device.password)
        device.description = data.get('description', device.description).strip()
        device.save()

        return JsonResponse({'success': True, 'message': '设备信息已更新'})
    except TestDevice.DoesNotExist:
        return JsonResponse({'success': False, 'error': '设备不存在'})
    except Exception as e:
        logger.exception(f"更新设备时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def device_delete(request):
    """删除设备"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        device_id = data.get('id')
        if not device_id:
            return JsonResponse({'success': False, 'error': '设备ID不能为空'})

        TestDevice.objects.filter(id=device_id).delete()
        return JsonResponse({'success': True, 'message': '设备已删除'})
    except Exception as e:
        logger.exception(f"删除设备时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def device_test_connection(request):
    """测试设备SSH连接"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        ip = data.get('ip', '').strip()
        port = int(data.get('port', 22))
        user = data.get('user', DEFAULT_USER).strip()
        password = data.get('password', DEFAULT_PASSWORD)
        
        if not ip:
            return JsonResponse({'success': False, 'error': 'IP地址不能为空'})
        
        success = test_connection(ip, user, password, port)
        
        if success:
            return JsonResponse({'success': True, 'message': '连接成功'})
        else:
            return JsonResponse({'success': False, 'error': '连接失败，请检查IP、端口、用户名和密码'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"测试连接时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def device_monitor_data(request):
    """获取设备监控数据（CPU、内存、网络）
    优化：先检测设备在线状态，不通就不继续获取其他信息
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        ip = data.get('ip', '').strip()
        port = int(data.get('port', 22))
        user = data.get('user', DEFAULT_USER).strip()
        password = data.get('password', DEFAULT_PASSWORD)
        
        if not ip:
            return JsonResponse({'success': False, 'error': 'IP地址不能为空'})
        
        # 获取设备类型
        device_type = data.get('device_type', '').strip()
        
        # 第一步：先检测设备在线状态（ping检测，使用socket连接测试，不进行SSH认证）
        from .agent_manager import agent_manager
        is_online, online_msg = agent_manager.test_network_connectivity(ip, port, timeout=3)
        
        if not is_online:
            # 设备不在线，直接返回，不获取CPU、内存、网络信息
            logger.info(f'设备 {ip}:{port} 不在线，跳过获取监控数据: {online_msg}')
            return JsonResponse({
                'success': False,
                'error': f'设备不在线: {online_msg}',
                'offline': True
            })
        
        # 设备在线，继续获取监控信息
        # 获取CPU信息
        cpu_usage = get_cpu_info(ip, user, password, device_type=device_type)
        
        # 获取内存信息
        memory_info = get_memory_info(ip, user, password, device_type=device_type)
        
        # 获取网络信息（包含速率）
        network_info = get_network_info(ip, user, password, device_type=device_type)
        
        return JsonResponse({
            'success': True,
            'cpu_usage': cpu_usage,
            'memory': memory_info,
            'network': network_info
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"获取监控数据时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def device_coredump_list(request):
    """获取coredump文件列表"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        ip = data.get('ip', '').strip()
        port = int(data.get('port', 22))
        user = data.get('user', DEFAULT_USER).strip()
        password = data.get('password', DEFAULT_PASSWORD)
        coredump_dir = data.get('coredump_dir', '/data/coredump')
        
        if not ip:
            return JsonResponse({'success': False, 'error': 'IP地址不能为空'})
        
        # 获取设备类型
        device_type = data.get('device_type', '').strip()
        
        files = get_coredump_files(ip, user, password, coredump_dir, device_type=device_type)
        
        return JsonResponse({
            'success': True,
            'files': files
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"获取coredump文件列表时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def device_execute_command(request):
    """执行设备命令"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        ip = data.get('ip', '').strip()
        port = int(data.get('port', 22))
        user = data.get('user', DEFAULT_USER).strip()
        password = data.get('password', DEFAULT_PASSWORD)
        command_type = data.get('command_type', 'normal')
        command = data.get('command', '').strip()
        device_type = data.get('device_type', '').strip()
        
        if not ip:
            return JsonResponse({'success': False, 'error': 'IP地址不能为空'})
        
        if not command:
            return JsonResponse({'success': False, 'error': '命令不能为空'})
        
        output = False
        
        if command_type == 'vtysh':
            # Vtysh命令（交互式）
            output = execute_in_vtysh(command, ip, user, password, log=True)
        elif command_type == 'backend':
            # 后台命令（需要root权限）
            output = execute_in_backend(command, ip, user, password, device_type=device_type)
        else:
            # 普通命令
            output = execute(command, ip, user, password, port)
        
        if output is False:
            return JsonResponse({'success': False, 'error': '命令执行失败，请检查连接和命令'})
        
        return JsonResponse({
            'success': True,
            'output': output
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"执行命令时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})

@csrf_exempt  # 使用装饰器免除CSRF保护，通常用于API视图
def get_cookie(request):
    """
    获取指定IP的cookie
    该视图函数处理POST请求，接收IP地址，首先检查缓存中的cookie，
    如果缓存中没有或已过期，则向目标设备发送登录请求，并获取返回的cookie
    """
    if request.method == 'POST':  # 确保只处理POST请求
        try:
            data = json.loads(request.body)  # 解析请求体中的JSON数据
            ip_address = data.get('ip_address')  # 从JSON数据中获取IP地址

            if not ip_address:  # 检查IP地址是否为空
                return JsonResponse({'success': False, 'error': 'IP地址不能为空'})

            # 首先尝试从缓存中获取cookie
            cached_cookie = get_cached_cookie(ip_address)
            if cached_cookie:
                return JsonResponse({
                    'success': True,
                    'cookie': cached_cookie,
                    'status_code': 200,
                    'from_cache': True
                })

            logger.info(f"为IP {ip_address} 获取新cookie")

            # 设置请求头，模拟浏览器访问
            headers = {
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            }

            # 准备登录所需的数据（从配置文件读取）
            login_data = {
                "loginuser": FIREWALL_LOGIN_USER,
                "pin": FIREWALL_LOGIN_PIN,
                "pw": FIREWALL_LOGIN_PASSWORD,
                "username": FIREWALL_LOGIN_USER
            }

            # 构建目标URL
            url = f"https://{ip_address}/checkUser"

            # 发送POST请求
            try:
                response = requests.post(
                    url, 
                    json=login_data, 
                    headers=headers, 
                    verify=SSL_VERIFY,
                    timeout=REQUEST_TIMEOUT
                )
            except requests.exceptions.Timeout:
                logger.error(f"请求超时: {ip_address}")
                return JsonResponse({'success': False, 'error': '请求超时，请检查网络连接'})
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {ip_address}, 错误: {str(e)}")
                return JsonResponse({'success': False, 'error': f'网络请求失败: {str(e)}'})

            # 检查响应状态码
            if response.status_code == 200:
                # 从响应头中提取cookie
                cookie_header = response.headers.get("Set-Cookie", "")

                if cookie_header:
                    cookie = cookie_header.split(";")[0]
                    # 保存cookie到缓存
                    save_cookie_to_cache(ip_address, cookie)
                else:
                    cookie = ""
                    logger.warning(f"警告: 未找到Set-Cookie头 - IP: {ip_address}")

                # 解码响应内容
                try:
                    response_text = response.content.decode("unicode_escape")
                except:
                    response_text = response.text
                
                # 返回成功响应，包含cookie和状态码
                return JsonResponse({
                    'success': True,
                    'cookie': cookie,
                    'status_code': response.status_code,
                    'from_cache': False,
                    'response_text': response_text
                })
            else:
                # 返回错误响应
                return JsonResponse({
                    'success': False,
                    'error': f'HTTP状态码: {response.status_code}',
                    'status_code': response.status_code
                })

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': '请求数据格式错误，需要有效的JSON'})
        except Exception as e:
            logger.exception(f"获取cookie时出错: {e}")
            return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})
    else:
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})


# ========== 以下函数需要从备份恢复完整实现 ==========
# ========== 防火墙策略 API 函数 ==========
# 使用通用请求处理函数 _send_api_request 简化代码

@csrf_exempt
def send_custom_service(request):
    """发送自定义服务请求"""
    return _send_api_request(request, 'custom_service', require_cookie=True)

@csrf_exempt
def send_custom_service_batch(request):
    """批量发送自定义服务请求"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})

    try:
        data = json.loads(request.body)
        ip_address = data.get('ip_address', '').strip()
        cookie = data.get('cookie', '').strip()
        requests_list = data.get('requests', [])
        
        if not ip_address:
            return JsonResponse({'success': False, 'error': '缺少IP地址参数'})
        if not cookie:
            return JsonResponse({'success': False, 'error': '缺少Cookie参数'})
        if not requests_list:
            return JsonResponse({'success': False, 'error': '缺少请求列表参数'})
        
        headers = {
            "Content-Type": "application/json",
            "Cookie": cookie,
            "User-Agent": USER_AGENT,
        }
        
        url = f"https://{ip_address}/custom_service"
        responses = []
        success_count = 0
        failure_count = 0
        
        for idx, request_data in enumerate(requests_list):
            try:
                response = requests.post(url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                if response.status_code == 200:
                    success_count += 1
                    responses.append({
                        'index': idx + 1,
                        'success': True,
                        'response': response.text
                    })
                else:
                    failure_count += 1
                    responses.append({
                        'index': idx + 1,
                        'success': False,
                        'error': f'状态码: {response.status_code}'
                    })
            except Exception as e:
                failure_count += 1
                responses.append({
                    'index': idx + 1,
                    'success': False,
                    'error': str(e)
                })
        
        return JsonResponse({
            'success': True,
            'total': len(requests_list),
            'success_count': success_count,
            'failure_count': failure_count,
            'responses': responses
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"批量发送自定义服务请求时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
@csrf_exempt
def send_service_group(request):
    """发送服务组请求"""
    return _send_api_request(request, 'service_group', require_cookie=True)



@csrf_exempt
@csrf_exempt
def send_l2_custom_service(request):
    """发送二层自定义服务请求"""
    return _send_api_request(request, 'l2_custom_service', require_cookie=True)


@csrf_exempt
def service_test_case_list(request):
    """获取服务测试用例列表"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        service_type = request.GET.get('service_type', '').strip()
        operation_type = request.GET.get('operation_type', '').strip()
        
        queryset = ServiceTestCase.objects.all().order_by('id')  # 按照ID正序排列，确保默认用例按创建顺序显示
        
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        if operation_type:
            queryset = queryset.filter(operation_type=operation_type)
        
        # 分页处理
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        try:
            page = int(request.GET.get('page', 1))
        except (ValueError, TypeError):
            page = 1
        
        try:
            page_size = int(request.GET.get('page_size', 10))
        except (ValueError, TypeError):
            page_size = 10
        
        # 确保page_size至少为1
        if page_size < 1:
            page_size = 10
        
        paginator = Paginator(queryset, page_size)
        total_pages = paginator.num_pages
        total_count = paginator.count
        
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            # 如果page不是整数，返回第一页
            page_obj = paginator.page(1)
            page = 1
        except EmptyPage:
            # 如果page超出范围，返回最后一页
            page_obj = paginator.page(paginator.num_pages)
            page = paginator.num_pages
        
        # 获取当前页的记录数
        page_obj_list = list(page_obj)
        current_page_count = len(page_obj_list)
        logger.info(f"分页信息: 当前页={page}, 每页={page_size}, 总页数={total_pages}, 总记录数={total_count}, 当前页记录数={current_page_count}")
        
        # 解码实际响应的辅助函数
        def decode_response(response_text):
            """解码Unicode转义的JSON响应"""
            if not response_text:
                return ''
            try:
                # 先尝试解码Unicode字符（处理\u670d\u52a1这样的编码）
                import re
                decoded = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), response_text)
                
                # 尝试解析JSON
                try:
                    parsed = json.loads(decoded)
                    # 提取msg字段，如果没有msg则提取message字段
                    if isinstance(parsed, dict):
                        if 'msg' in parsed:
                            return str(parsed['msg'])
                        elif 'message' in parsed:
                            return str(parsed['message'])
                        else:
                            # 如果有其他字段，返回格式化的JSON
                            return json.dumps(parsed, ensure_ascii=False)
                    else:
                        return str(parsed)
                except (json.JSONDecodeError, ValueError):
                    # 如果不是JSON，返回解码后的原始内容
                    return decoded
            except Exception as e:
                logger.warning(f"解码响应失败: {e}, 使用原始内容")
                return response_text
        
        test_cases = []
        for case in page_obj_list:
            # 解码实际响应
            decoded_response = decode_response(case.last_test_response) if case.last_test_response else ''
            
            test_cases.append({
                'id': case.id,
                'service_type': case.service_type,
                'service_type_display': case.get_service_type_display(),
                'operation_type': case.operation_type,
                'operation_type_display': case.get_operation_type_display(),
                'name': case.name,
                'desc': case.desc,
                'content': case.content,
                'expected_success': case.expected_success,
                'expected_response': case.expected_response,
                'expected_status_code': case.expected_status_code,
                'last_test_result': case.last_test_result,
                'last_test_response': case.last_test_response,  # 保留原始响应
                'last_test_response_decoded': decoded_response,  # 添加解码后的响应
                'last_test_status_code': case.last_test_status_code,
                'last_test_time': case.last_test_time.isoformat() if case.last_test_time else None,
                'enabled': case.enabled,
                'is_default': case.is_default,
                'created_at': case.created_at.isoformat(),
                'updated_at': case.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'test_cases': test_cases,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'total_count': total_count,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
            }
        })
    except Exception as e:
        logger.exception(f"获取测试用例列表时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_test_case_add(request):
    """添加服务测试用例"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        service_type = data.get('service_type', '').strip()
        operation_type = data.get('operation_type', '').strip()
        name = data.get('name', '').strip()
        desc = data.get('desc', '').strip()
        content = data.get('content', '').strip()
        expected_success = data.get('expected_success', True)
        expected_response = data.get('expected_response', '').strip()
        expected_status_code = data.get('expected_status_code', 200)
        
        # 验证必填字段
        if not service_type or service_type not in ['custom_service', 'l2_custom_service']:
            return JsonResponse({'success': False, 'error': '服务类型无效'})
        if not operation_type or operation_type not in ['add', 'edit', 'delete']:
            return JsonResponse({'success': False, 'error': '操作类型无效'})
        if not name:
            return JsonResponse({'success': False, 'error': '名称不能为空'})
        if not content:
            return JsonResponse({'success': False, 'error': '内容不能为空'})
        
        # 验证name格式（字母、数字、中文、下划线，最长32字节）
        import re
        if len(name.encode('utf-8')) > 32:
            return JsonResponse({'success': False, 'error': '名称长度不能超过32字节'})
        if not re.match(r'^[\w\u4e00-\u9fa5]+$', name):
            return JsonResponse({'success': False, 'error': '名称只能包含字母、数字、中文和下划线'})
        
        # 验证desc长度（最长64字节）
        if desc and len(desc.encode('utf-8')) > 64:
            return JsonResponse({'success': False, 'error': '描述长度不能超过64字节'})
        
        # 创建测试用例
        test_case = ServiceTestCase.objects.create(
            service_type=service_type,
            operation_type=operation_type,
            name=name,
            desc=desc,
            content=content,
            expected_success=expected_success,
            expected_response=expected_response,
            expected_status_code=expected_status_code,
        )
        
        return JsonResponse({
            'success': True,
            'message': '测试用例添加成功',
            'test_case_id': test_case.id
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"添加测试用例时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_test_case_update(request):
    """更新服务测试用例"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        test_case_id = data.get('id')
        
        if not test_case_id:
            return JsonResponse({'success': False, 'error': '缺少测试用例ID'})
        
        try:
            test_case = ServiceTestCase.objects.get(id=test_case_id)
        except ServiceTestCase.DoesNotExist:
            return JsonResponse({'success': False, 'error': '测试用例不存在'})
        
        # 更新字段
        if 'name' in data:
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({'success': False, 'error': '名称不能为空'})
            # 验证name格式
            import re
            if len(name.encode('utf-8')) > 32:
                return JsonResponse({'success': False, 'error': '名称长度不能超过32字节'})
            if not re.match(r'^[\w\u4e00-\u9fa5]+$', name):
                return JsonResponse({'success': False, 'error': '名称只能包含字母、数字、中文和下划线'})
            test_case.name = name
        
        if 'desc' in data:
            desc = data.get('desc', '').strip()
            if desc and len(desc.encode('utf-8')) > 64:
                return JsonResponse({'success': False, 'error': '描述长度不能超过64字节'})
            test_case.desc = desc
        
        if 'content' in data:
            test_case.content = data.get('content', '').strip()
        
        if 'expected_success' in data:
            test_case.expected_success = data.get('expected_success', True)
        
        if 'expected_response' in data:
            test_case.expected_response = data.get('expected_response', '').strip()
        
        if 'expected_status_code' in data:
            test_case.expected_status_code = data.get('expected_status_code', 200)
        
        if 'enabled' in data:
            test_case.enabled = data.get('enabled', True)
        
        test_case.save()
        
        return JsonResponse({'success': True, 'message': '测试用例更新成功'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"更新测试用例时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_test_case_apply(request):
    """将实际响应应用到期望响应"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        test_case_id = data.get('id')
        
        if not test_case_id:
            return JsonResponse({'success': False, 'error': '缺少测试用例ID'})
        
        try:
            test_case = ServiceTestCase.objects.get(id=test_case_id)
            
            # 检查是否有实际响应
            if not test_case.last_test_response:
                return JsonResponse({'success': False, 'error': '没有实际响应数据，请先执行测试'})
            
            # 解码实际响应并应用到期望响应
            decoded_response = ''
            if test_case.last_test_response:
                try:
                    import re
                    # 先尝试解码Unicode字符（处理\u670d\u52a1这样的编码）
                    decoded = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), test_case.last_test_response)
                    
                    # 尝试解析JSON
                    try:
                        parsed = json.loads(decoded)
                        # 提取msg字段，如果没有msg则提取message字段
                        if isinstance(parsed, dict):
                            if 'msg' in parsed:
                                decoded_response = str(parsed['msg'])
                            elif 'message' in parsed:
                                decoded_response = str(parsed['message'])
                            else:
                                # 如果有其他字段，返回格式化的JSON
                                decoded_response = json.dumps(parsed, ensure_ascii=False)
                        else:
                            decoded_response = str(parsed)
                    except (json.JSONDecodeError, ValueError):
                        # 如果不是JSON，返回解码后的原始内容
                        decoded_response = decoded
                except Exception as e:
                    logger.warning(f"解码响应失败: {e}, 使用原始内容")
                    decoded_response = test_case.last_test_response
            
            # 将解码后的实际响应应用到期望响应
            test_case.expected_response = decoded_response if decoded_response else test_case.last_test_response
            # 同时更新期望状态码
            if test_case.last_test_status_code:
                test_case.expected_status_code = test_case.last_test_status_code
            # 更新期望成功标志
            if test_case.last_test_result is not None:
                test_case.expected_success = test_case.last_test_result
            
            test_case.save()
            
            return JsonResponse({
                'success': True,
                'message': '应用成功',
                'expected_response': test_case.expected_response,
                'expected_status_code': test_case.expected_status_code,
                'expected_success': test_case.expected_success
            })
        except ServiceTestCase.DoesNotExist:
            return JsonResponse({'success': False, 'error': '测试用例不存在'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"应用实际响应时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_test_case_delete(request):
    """删除服务测试用例"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        test_case_id = data.get('id')
        
        if not test_case_id:
            return JsonResponse({'success': False, 'error': '缺少测试用例ID'})
        
        try:
            test_case = ServiceTestCase.objects.get(id=test_case_id)
            # 检查是否为默认用例
            if test_case.is_default:
                return JsonResponse({'success': False, 'error': '默认用例不能删除'})
            test_case.delete()
            return JsonResponse({'success': True, 'message': '测试用例删除成功'})
        except ServiceTestCase.DoesNotExist:
            return JsonResponse({'success': False, 'error': '测试用例不存在'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"删除测试用例时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_test_case_test(request):
    """测试单个服务测试用例"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        test_case_id = data.get('test_case_id')
        ip_address = data.get('ip_address', '').strip()
        cookie = data.get('cookie', '').strip()
        
        if not test_case_id:
            return JsonResponse({'success': False, 'error': '缺少测试用例ID'})
        if not ip_address:
            return JsonResponse({'success': False, 'error': '缺少IP地址'})
        
        try:
            test_case = ServiceTestCase.objects.get(id=test_case_id)
        except ServiceTestCase.DoesNotExist:
            return JsonResponse({'success': False, 'error': '测试用例不存在'})
        
        # 如果没有提供cookie，尝试从缓存获取
        if not cookie:
            cookie = get_cached_cookie(ip_address)
            if not cookie:
                return JsonResponse({'success': False, 'error': '缺少Cookie参数，请先登录'})
        
        # 构建请求数据（参考策略配置中的格式）
        request_data = {
            'id': '',  # 新增时可以为空，编辑/删除时需要
            'loginuser': FIREWALL_LOGIN_USER,  # 使用配置中的默认登录用户
            'name': test_case.name,
            'desc': test_case.desc,
            'content': test_case.content,
        }
        
        # 根据操作类型选择URL和方法
        if test_case.service_type == 'custom_service':
            base_url = f"https://{ip_address}/custom_service"
            service_name = "自定义服务"
        else:  # l2_custom_service
            base_url = f"https://{ip_address}/l2_custom_service"
            service_name = "二层自定义服务"
        
        # 打印发送给防火墙的请求内容（不包含cookie）
        # 格式化请求内容，参考策略配置中的格式，content字段不转义
        logger.info(f"[对象管理-{service_name}] 发送给防火墙的请求:")
        logger.info(f"  URL: {base_url}")
        logger.info(f"  操作类型: {test_case.get_operation_type_display()}")
        logger.info(f"  请求内容:")
        logger.info(f"    \"id\": \"{request_data.get('id', '')}\"")
        logger.info(f"    \"loginuser\": \"{request_data.get('loginuser', '')}\"")
        logger.info(f"    \"name\": \"{request_data.get('name', '')}\"")
        logger.info(f"    \"desc\": \"{request_data.get('desc', '')}\"")
        logger.info(f"    \"content\": '{request_data.get('content', '')}'")
        print(f"[对象管理-{service_name}] 发送给防火墙的请求:")
        print(f"  URL: {base_url}")
        print(f"  操作类型: {test_case.get_operation_type_display()}")
        print(f"  请求内容:")
        print(f"    \"id\": \"{request_data.get('id', '')}\"")
        print(f"    \"loginuser\": \"{request_data.get('loginuser', '')}\"")
        print(f"    \"name\": \"{request_data.get('name', '')}\"")
        print(f"    \"desc\": \"{request_data.get('desc', '')}\"")
        print(f"    \"content\": '{request_data.get('content', '')}'")
        
        headers = {
            "Content-Type": "application/json",
            "Cookie": cookie,
            "User-Agent": USER_AGENT,
        }
        
        # 根据操作类型发送请求
        if test_case.operation_type == 'add':
            response = requests.post(base_url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
        elif test_case.operation_type == 'edit':
            # 编辑操作，通常使用PUT方法，如果失败则尝试POST
            try:
                response = requests.put(base_url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            except:
                response = requests.post(base_url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
        else:  # delete
            # 删除操作，通常使用DELETE方法，如果失败则尝试POST
            try:
                response = requests.delete(base_url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            except:
                response = requests.post(base_url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
        
        # 保存测试结果
        from django.utils import timezone
        test_case.last_test_status_code = response.status_code
        test_case.last_test_response = response.text
        test_case.last_test_time = timezone.now()
        
        # 判断测试结果
        is_success = response.status_code == test_case.expected_status_code
        if test_case.expected_response:
            # 如果设置了期望响应，进行对比
            is_success = is_success and (test_case.expected_response in response.text or response.text == test_case.expected_response)
        
        test_case.last_test_result = is_success == test_case.expected_success
        test_case.save()
        
        return JsonResponse({
            'success': True,
            'test_result': {
                'status_code': response.status_code,
                'response': response.text,
                'expected_status_code': test_case.expected_status_code,
                'expected_response': test_case.expected_response,
                'expected_success': test_case.expected_success,
                'result_match': test_case.last_test_result,
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"测试用例执行时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_test_case_create_defaults(request):
    """创建默认测试用例"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from django.utils import timezone
        
        # 按照用户指定的排序规则组织：先新增，后编辑，再删除
        # 端口号使用40000-60000范围，避免使用常见端口
        default_cases = [
            # ========== 新增操作 - 名称验证 ==========
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'name_english', 'desc': '仅包含英文', 'content': 'tcp;40001;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': '123456', 'desc': '仅包含数字', 'content': 'tcp;40002;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': '测试服务', 'desc': '仅包含中文', 'content': 'tcp;40003;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': '___', 'desc': '仅包含下划线', 'content': 'tcp;40004;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'test123_服务', 'desc': '组合验证', 'content': 'tcp;40005;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'a' * 31, 'desc': '长度小于32', 'content': 'tcp;40006;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'a' * 33, 'desc': '长度大于32（应该失败）', 'content': 'tcp;40007;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': '', 'desc': '长度为0（应该失败）', 'content': 'tcp;40008;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'test@#$%', 'desc': '特殊字符（应该失败）', 'content': 'tcp;40009;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'test<script>alert(1)</script>', 'desc': 'css注入代码<script>（应该失败）', 'content': 'tcp;40010;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'name_duplicate_1', 'desc': '名称重复-第一个', 'content': 'tcp;40011;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'name_duplicate_1', 'desc': '名称重复-第二个（应该失败）', 'content': 'tcp;40012;0;0', 'expected_success': False, 'expected_status_code': 400},
            
            # ========== 新增操作 - 描述验证 ==========
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'desc_empty', 'desc': '', 'content': 'tcp;40013;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'desc_normal', 'desc': 'a' * 32, 'content': 'tcp;40014;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'desc_max', 'desc': 'a' * 64, 'content': 'tcp;40015;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'desc_over', 'desc': 'a' * 65, 'content': 'tcp;40016;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'desc_special', 'desc': '!@#$%^&*()_+-=[]{}|;:,.<>?/~`', 'content': 'tcp;40017;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'desc_xss', 'desc': '<script>alert(1)</script>', 'content': 'tcp;40018;0;0', 'expected_success': True, 'expected_status_code': 200},
            
            # ========== 新增操作 - TCP端口验证 ==========
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'tcp_single', 'desc': 'TCP单个端口', 'content': 'tcp;40019;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'tcp_invalid', 'desc': 'TCP不正确端口（应该失败）', 'content': 'tcp;0;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'tcp_over', 'desc': 'TCP超过范围端口（应该失败）', 'content': 'tcp;65536;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'tcp_nondigit', 'desc': 'TCP非数字（应该失败）', 'content': 'tcp;abc;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'tcp_empty', 'desc': 'TCP空（应该失败）', 'content': 'tcp;;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'tcp_multi', 'desc': 'TCP多个端口', 'content': 'tcp;40020,40021,40022;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'tcp_range', 'desc': 'TCP端口范围', 'content': 'tcp;40023~40026;0;0', 'expected_success': True, 'expected_status_code': 200},
            
            # ========== 新增操作 - UDP端口验证 ==========
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'udp_single', 'desc': 'UDP单个端口', 'content': 'udp;40027;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'udp_invalid', 'desc': 'UDP不正确端口（应该失败）', 'content': 'udp;0;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'udp_over', 'desc': 'UDP超过范围端口（应该失败）', 'content': 'udp;65536;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'udp_nondigit', 'desc': 'UDP非数字（应该失败）', 'content': 'udp;xyz;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'udp_empty', 'desc': 'UDP空（应该失败）', 'content': 'udp;;0;0', 'expected_success': False, 'expected_status_code': 400},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'udp_multi', 'desc': 'UDP多个端口', 'content': 'udp;40028,40029;0;0', 'expected_success': True, 'expected_status_code': 200},
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'udp_range', 'desc': 'UDP端口范围', 'content': 'udp;40030~40033;0;0', 'expected_success': True, 'expected_status_code': 200},
            
            # ========== 新增操作 - ICMP验证 ==========
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'icmp_test', 'desc': 'ICMP验证', 'content': 'icmp;0;3;1;', 'expected_success': True, 'expected_status_code': 200},
            
            # ========== 新增操作 - 其他协议验证 ==========
            {'service_type': 'custom_service', 'operation_type': 'add', 'name': 'other_proto', 'desc': '其他协议验证', 'content': '50;0;0;0;', 'expected_success': True, 'expected_status_code': 200},
            
            # ========== 编辑操作测试 ==========
            {'service_type': 'custom_service', 'operation_type': 'edit', 'name': 'edit_test', 'desc': '编辑操作测试', 'content': 'tcp;40034;0;0', 'expected_success': True, 'expected_status_code': 200},
            
            # ========== 删除操作测试 ==========
            {'service_type': 'custom_service', 'operation_type': 'delete', 'name': 'delete_test', 'desc': '删除操作测试', 'content': 'tcp;40035;0;0', 'expected_success': True, 'expected_status_code': 200},
        ]
        
        created_count = 0
        updated_count = 0
        deleted_count = 0
        
        # 先删除所有已存在的默认用例
        old_defaults = ServiceTestCase.objects.filter(is_default=True)
        for old_case in old_defaults:
            case_name = old_case.name
            case_id = old_case.id
            old_case.delete()
            deleted_count += 1
            logger.info(f"删除已存在的默认用例: {case_name} (ID: {case_id})")
        
        # 然后创建所有新的默认用例
        for case_data in default_cases:
            # 直接创建新的默认用例（因为已经删除了所有旧的）
            ServiceTestCase.objects.create(
                service_type=case_data['service_type'],
                operation_type=case_data['operation_type'],
                name=case_data['name'],
                desc=case_data.get('desc', ''),
                content=case_data['content'],
                expected_success=case_data.get('expected_success', True),
                expected_status_code=case_data.get('expected_status_code', 200),
                enabled=True,
                is_default=True,  # 标记为默认用例
            )
            created_count += 1
            logger.info(f"创建默认用例: {case_data['name']}, content: {case_data['content']}")
        
        return JsonResponse({
            'success': True,
            'message': f'成功删除 {deleted_count} 个旧默认用例，创建 {created_count} 个新默认测试用例',
            'created_count': created_count,
            'updated_count': 0,  # 不再有更新操作
            'deleted_count': deleted_count
        })
    except Exception as e:
        logger.exception(f"创建默认测试用例时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_test_case_batch_test(request):
    """批量测试服务测试用例"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        test_case_ids = data.get('test_case_ids', [])
        ip_address = data.get('ip_address', '').strip()
        cookie = data.get('cookie', '').strip()
        
        if not test_case_ids:
            return JsonResponse({'success': False, 'error': '缺少测试用例ID列表'})
        if not ip_address:
            return JsonResponse({'success': False, 'error': '缺少IP地址'})
        
        # 如果没有提供cookie，尝试从缓存获取
        if not cookie:
            cookie = get_cached_cookie(ip_address)
            if not cookie:
                return JsonResponse({'success': False, 'error': '缺少Cookie参数，请先登录'})
        
        results = []
        for test_case_id in test_case_ids:
            try:
                # 调用单个测试接口
                test_data = {
                    'test_case_id': test_case_id,
                    'ip_address': ip_address,
                    'cookie': cookie
                }
                # 这里简化处理，实际应该复用service_test_case_test的逻辑
                test_case = ServiceTestCase.objects.get(id=test_case_id)
                
                # 构建请求数据（参考策略配置中的格式）
                request_data = {
                    'id': '',  # 新增时可以为空，编辑/删除时需要
                    'loginuser': FIREWALL_LOGIN_USER,  # 使用配置中的默认登录用户
                    'name': test_case.name,
                    'desc': test_case.desc,
                    'content': test_case.content,
                }
                
                # 根据操作类型选择URL和方法
                if test_case.service_type == 'custom_service':
                    base_url = f"https://{ip_address}/custom_service"
                    service_name = "自定义服务"
                else:
                    base_url = f"https://{ip_address}/l2_custom_service"
                    service_name = "二层自定义服务"
                
                # 打印发送给防火墙的请求内容（不包含cookie）
                # 格式化请求内容，参考策略配置中的格式，content字段不转义
                logger.info(f"[对象管理-批量测试-{service_name}] 发送给防火墙的请求:")
                logger.info(f"  URL: {base_url}")
                logger.info(f"  操作类型: {test_case.get_operation_type_display()}")
                logger.info(f"  请求内容:")
                logger.info(f"    \"id\": \"{request_data.get('id', '')}\"")
                logger.info(f"    \"loginuser\": \"{request_data.get('loginuser', '')}\"")
                logger.info(f"    \"name\": \"{request_data.get('name', '')}\"")
                logger.info(f"    \"desc\": \"{request_data.get('desc', '')}\"")
                logger.info(f"    \"content\": '{request_data.get('content', '')}'")
                print(f"[对象管理-批量测试-{service_name}] 发送给防火墙的请求:")
                print(f"  URL: {base_url}")
                print(f"  操作类型: {test_case.get_operation_type_display()}")
                print(f"  请求内容:")
                print(f"    \"id\": \"{request_data.get('id', '')}\"")
                print(f"    \"loginuser\": \"{request_data.get('loginuser', '')}\"")
                print(f"    \"name\": \"{request_data.get('name', '')}\"")
                print(f"    \"desc\": \"{request_data.get('desc', '')}\"")
                print(f"    \"content\": '{request_data.get('content', '')}'")
                
                headers = {
                    "Content-Type": "application/json",
                    "Cookie": cookie,
                    "User-Agent": USER_AGENT,
                }
                
                # 根据操作类型发送请求
                if test_case.operation_type == 'add':
                    response = requests.post(base_url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                elif test_case.operation_type == 'edit':
                    try:
                        response = requests.put(base_url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                    except:
                        response = requests.post(base_url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                else:  # delete
                    try:
                        response = requests.delete(base_url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                    except:
                        response = requests.post(base_url, json=request_data, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                
                # 保存测试结果
                from django.utils import timezone
                test_case.last_test_status_code = response.status_code
                test_case.last_test_response = response.text
                test_case.last_test_time = timezone.now()
                
                # 判断测试结果
                is_success = response.status_code == test_case.expected_status_code
                if test_case.expected_response:
                    is_success = is_success and (test_case.expected_response in response.text or response.text == test_case.expected_response)
                
                test_case.last_test_result = is_success == test_case.expected_success
                test_case.save()
                
                results.append({
                    'test_case_id': test_case_id,
                    'name': test_case.name,
                    'result_match': test_case.last_test_result,
                    'status_code': response.status_code,
                    'expected_status_code': test_case.expected_status_code,
                    'response': response.text[:200],  # 只返回前200字符
                })
            except Exception as e:
                results.append({
                    'test_case_id': test_case_id,
                    'error': str(e),
                    'result_match': False,
                })
        
        return JsonResponse({
            'success': True,
            'results': results
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"批量测试用例执行时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def send_addrlist(request):
    """发送addrlist请求"""
    return _send_api_request(request, 'addrlist', require_cookie=True)


@csrf_exempt
def send_addrgroup(request):
    """发送addrgroup请求"""
    return _send_api_request(request, 'addrgroup', require_cookie=True)


@csrf_exempt
def send_l2_addrlist(request):
    """发送l2_addrlist请求"""
    return _send_api_request(request, 'l2_addrlist', require_cookie=True)


@csrf_exempt
def send_l2_addrgroup(request):
    """发送l2_addrgroup请求"""
    return _send_api_request(request, 'l2_addrgroup', require_cookie=True)


@csrf_exempt
def send_packet_filter(request):
    """发送packet_filter请求"""
    return _send_api_request(request, 'packet_filter', require_cookie=True)


@csrf_exempt
def send_deep_check(request):
    """发送deep_check请求"""
    return _send_api_request(request, 'deep_check', require_cookie=True)


@csrf_exempt
def send_ipsecvpn(request):
    """发送ipsecvpn请求"""
    return _send_api_request(request, 'ipsecvpn', require_cookie=True)


@csrf_exempt
def send_bridge_info(request):
    """发送bridge_info请求"""
    return _send_api_request(request, 'bridge_info', require_cookie=True)


@csrf_exempt
def get_interfaces(request):
    """获取网络接口（通过SSH）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})

    try:
        data = json.loads(request.body)
        host = data.get('host', '').strip()
        user = data.get('user', 'admin').strip()
        password = data.get('password', 'tdhx@2017')
        port = int(data.get('port', 22))
        
        if not host:
            return JsonResponse({'success': False, 'error': '缺少主机地址参数'})
        
        try:
            import paramiko
        except ImportError:
            logger.error("paramiko模块未安装，无法获取网卡信息")
            return JsonResponse({
                'success': False,
                'error': 'paramiko模块未安装，请运行: pip install paramiko'
            })
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, port, user, password, timeout=10)
            
            # 检测操作系统
            stdin, stdout, stderr = ssh.exec_command('uname -s')
            os_type = stdout.read().decode('utf-8').strip().lower()
            
            interfaces = []
            
            if 'linux' in os_type:
                # Linux系统
                stdin, stdout, stderr = ssh.exec_command("ip -o link show | awk -F': ' '{print $2}'")
                output = stdout.read().decode('utf-8')
                for line in output.strip().split('\n'):
                    if line and 'lo' not in line:
                        interfaces.append({'name': line.strip(), 'ip': '', 'mac': ''})
            else:
                # Windows系统
                stdin, stdout, stderr = ssh.exec_command('powershell -Command "Get-NetAdapter | Select-Object Name, InterfaceDescription"')
                output = stdout.read().decode('utf-8', errors='ignore')
                for line in output.strip().split('\n')[2:]:  # 跳过标题行
                    if line.strip():
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            interfaces.append({'name': ' '.join(parts[:-1]), 'ip': '', 'mac': ''})
            
            ssh.close()
            
            return JsonResponse({
                'success': True,
                'interfaces': interfaces
            })
        
        except paramiko.AuthenticationException:
            return JsonResponse({'success': False, 'error': 'SSH认证失败，请检查用户名和密码'})
        except paramiko.SSHException as e:
            return JsonResponse({'success': False, 'error': f'SSH连接失败: {str(e)}'})
        except Exception as e:
            logger.exception(f"获取网络接口时出错: {e}")
            return JsonResponse({'success': False, 'error': f'获取网络接口失败: {str(e)}'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"获取网络接口时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def send_packet(request):
    """发送报文（通过SSH）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        host = data.get('host', '').strip()
        user = data.get('user', 'admin').strip()
        password = data.get('password', 'tdhx@2017')
        port = int(data.get('port', 22))
        interface = data.get('interface', '').strip()
        packet_type = data.get('packet_type', 'icmp')
        packet_config = data.get('packet_config', {})
        
        if not host:
            return JsonResponse({'success': False, 'error': '缺少主机地址参数'})
        if not interface:
            return JsonResponse({'success': False, 'error': '缺少网卡名称参数'})
        
        try:
            import paramiko
        except ImportError:
            return JsonResponse({
                'success': False,
                'error': 'paramiko模块未安装，请运行: pip install paramiko'
            })
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, port, user, password, timeout=10)
            
            # 检测操作系统
            stdin, stdout, stderr = ssh.exec_command('uname -s')
            os_type = stdout.read().decode('utf-8').strip().lower()
            
            cmd = ''
            if 'linux' in os_type:
                if packet_type == 'icmp':
                    dst_ip = packet_config.get('dst_ip', '')
                    cmd = f"ping -c 1 -I {interface} {dst_ip}"
                elif packet_type == 'tcp':
                    dst_ip = packet_config.get('dst_ip', '')
                    dst_port = packet_config.get('dst_port', '')
                    cmd = f"nc -w 1 {dst_ip} {dst_port} < /dev/null"
            else:
                # Windows系统
                if packet_type == 'icmp':
                    dst_ip = packet_config.get('dst_ip', '')
                    cmd = f"ping -n 1 -S {interface} {dst_ip}"
                elif packet_type == 'tcp':
                    dst_ip = packet_config.get('dst_ip', '')
                    dst_port = packet_config.get('dst_port', '')
                    cmd = f"Test-NetConnection -ComputerName {dst_ip} -Port {dst_port}"
            
            if cmd:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
                output = stdout.read().decode('utf-8', errors='ignore')
                error = stderr.read().decode('utf-8', errors='ignore')
                
                ssh.close()
                
                return JsonResponse({
                    'success': True,
                    'output': output,
                    'error': error
                })
            else:
                ssh.close()
                return JsonResponse({'success': False, 'error': '不支持的报文类型或操作系统'})
        
        except paramiko.AuthenticationException:
            return JsonResponse({'success': False, 'error': 'SSH认证失败'})
        except paramiko.SSHException as e:
            return JsonResponse({'success': False, 'error': f'SSH连接失败: {str(e)}'})
        except Exception as e:
            logger.exception(f"发送报文时出错: {e}")
            return JsonResponse({'success': False, 'error': f'发送报文失败: {str(e)}'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"发送报文时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def get_agent_interfaces(request):
    """获取代理程序网络接口"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        agent_url = data.get('agent_url', '').strip()
        
        if not agent_url:
            return JsonResponse({'success': False, 'error': '缺少代理程序URL参数'})
        
        client = PacketAgentClient(agent_url)
        success, result = client.get_interfaces()
        
        if success:
            return JsonResponse({
                'success': True,
                'interfaces': result.get('interfaces', [])
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '获取网卡列表失败')
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"获取代理程序网络接口时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def send_packet_via_agent(request):
    """通过代理程序发送报文"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        agent_url = data.get('agent_url', '').strip()
        interface = data.get('interface', '').strip()
        packet_config = data.get('packet_config', {})
        send_config = data.get('send_config', {})
        
        if not agent_url:
            return JsonResponse({'success': False, 'error': '缺少代理程序URL参数'})
        if not interface:
            return JsonResponse({'success': False, 'error': '缺少网卡名称参数'})
        
        client = PacketAgentClient(agent_url)
        success, result = client.send_packet(interface, packet_config, send_config)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': result.get('message', '报文发送已启动')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '发送报文失败')
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"通过代理程序发送报文时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def get_agent_statistics(request):
    """获取代理程序统计信息"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        agent_url = data.get('agent_url', '').strip()
        
        if not agent_url:
            return JsonResponse({'success': False, 'error': '缺少代理程序URL参数'})
        
        client = PacketAgentClient(agent_url)
        success, result = client.get_statistics()
        
        if success:
            return JsonResponse({
                'success': True,
                'statistics': result.get('statistics', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '获取统计信息失败')
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"获取代理程序统计信息时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def stop_agent_sending(request):
    """停止代理程序发送"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        agent_url = data.get('agent_url', '').strip()
        
        if not agent_url:
            return JsonResponse({'success': False, 'error': '缺少代理程序URL参数'})
        
        client = PacketAgentClient(agent_url)
        success, result = client.stop_sending()
        
        if success:
            return JsonResponse({
                'success': True,
                'message': result.get('message', '发送已停止')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '停止发送失败')
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"停止代理程序发送时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


# 端口扫描会话管理
port_scan_sessions = {}
port_scan_lock = threading.Lock()

@csrf_exempt
def port_scan_api(request):
    """端口扫描API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        target_ip = data.get('target_ip', '').strip()
        ports = data.get('ports', [])
        timeout = float(data.get('timeout', 1))
        threads = int(data.get('threads', 200))
        scan_type = data.get('scan_type', 'tcp_connect')
        agent_url = data.get('agent_url', '').strip()
        interface = data.get('interface', '').strip()
        
        if not target_ip:
            return JsonResponse({'success': False, 'error': '目标IP地址不能为空'})
        if not ports or len(ports) == 0:
            return JsonResponse({'success': False, 'error': '端口列表不能为空'})
        if len(ports) > 65535:
            return JsonResponse({'success': False, 'error': '端口数量过多，最多支持65535个端口'})
        
        scan_id = str(uuid.uuid4())
        
        # 如果使用代理程序进行SYN/FIN/RST扫描
        if scan_type in ['tcp_syn', 'tcp_fin', 'tcp_rst', 'tcp_null', 'tcp_xmas', 'tcp_ack', 'tcp_fin_syn', 'tcp_syn_rst', 'tcp_fin_rst', 'tcp_psh', 'tcp_urg'] and agent_url:
            try:
                client = PacketAgentClient(agent_url)
                success, result = client.port_scan(target_ip, ports, timeout, scan_type, interface, threads)
                
                if success:
                    agent_scan_id = result.get('scan_id')
                    with port_scan_lock:
                        port_scan_sessions[scan_id] = {
                            'target_ip': target_ip,
                            'total_ports': len(ports),
                            'scanned': 0,
                            'open_ports': [],
                            'closed_ports': [],
                            'results': [],
                            'completed': False,
                            'cancelled': False,
                            'use_agent': True,
                            'agent_url': agent_url,
                            'agent_scan_id': agent_scan_id
                        }
                    
                    return JsonResponse({
                        'success': True,
                        'scan_id': scan_id,
                        'message': '扫描已启动',
                        'total_ports': len(ports)
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': result.get('error', '启动扫描失败')
                    })
            except Exception as e:
                logger.exception(f"通过代理程序启动扫描时出错: {e}")
                return JsonResponse({'success': False, 'error': f'代理程序错误: {str(e)}'})
        else:
            # 本地TCP连接扫描
            with port_scan_lock:
                port_scan_sessions[scan_id] = {
                    'target_ip': target_ip,
                    'total_ports': len(ports),
                    'scanned': 0,
                    'open_ports': [],
                    'closed_ports': [],
                    'results': [],
                    'completed': False,
                    'cancelled': False,
                    'use_agent': False
                }
            
            # 启动扫描线程
            scan_thread = threading.Thread(
                target=perform_port_scan,
                args=(scan_id, target_ip, ports, timeout, threads, scan_type)
            )
            scan_thread.daemon = True
            scan_thread.start()
            
            return JsonResponse({
                'success': True,
                'scan_id': scan_id,
                'message': '扫描已启动',
                'total_ports': len(ports)
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"启动端口扫描时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


def scan_port(target_ip, port, timeout=1):
    """扫描单个端口"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        result = sock.connect_ex((target_ip, port))
        sock.close()
        
        if result == 0:
            return {'port': port, 'status': 'open', 'service': identify_service(target_ip, port), 'response_time': None}
        else:
            return None
    except:
        return None


def identify_service(target_ip, port):
    """识别服务"""
    common_services = {
        21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
        80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS', 3306: 'MySQL',
        5432: 'PostgreSQL', 6379: 'Redis', 8080: 'HTTP-Proxy'
    }
    return common_services.get(port, 'Unknown')


def perform_port_scan(scan_id, target_ip, ports, timeout, threads, scan_type):
    """执行端口扫描"""
    try:
        open_ports = []
        closed_ports = []
        results = []
        scanned_count = 0
        last_update_time = time.time()
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_port = {executor.submit(scan_port, target_ip, port, timeout): port for port in ports}
            
            for future in as_completed(future_to_port):
                if scan_id not in port_scan_sessions:
                    break
                
                session = port_scan_sessions[scan_id]
                if session.get('cancelled', False):
                    break
                
                try:
                    result = future.result()
                    scanned_count += 1
                    
                    if result:
                        open_ports.append(result['port'])
                        results.append(result)
                    else:
                        port = future_to_port[future]
                        closed_ports.append(port)
                    
                    current_time = time.time()
                    should_update = (current_time - last_update_time >= 5) or (scanned_count % 10 == 0) or result
                    
                    with port_scan_lock:
                        if scan_id in port_scan_sessions:
                            session = port_scan_sessions[scan_id]
                            session['scanned'] = scanned_count
                            if should_update:
                                session['open_ports'] = open_ports.copy()
                                session['closed_ports'] = closed_ports.copy()
                                session['results'] = results.copy()
                                last_update_time = current_time
                except Exception as e:
                    logger.error(f"扫描端口时出错: {e}")
        
        with port_scan_lock:
            if scan_id in port_scan_sessions:
                session = port_scan_sessions[scan_id]
                session['completed'] = True
                session['scanned'] = scanned_count
                session['open_ports'] = open_ports
                session['closed_ports'] = closed_ports
                session['results'] = results
    
    except Exception as e:
        logger.exception(f"执行端口扫描时出错: {e}")
        with port_scan_lock:
            if scan_id in port_scan_sessions:
                port_scan_sessions[scan_id]['completed'] = True


@csrf_exempt
def port_scan_progress(request):
    """获取端口扫描进度"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        scan_id = request.GET.get('scan_id', '').strip()
        
        if not scan_id:
            return JsonResponse({'success': False, 'error': '缺少scan_id参数'})
        
        with port_scan_lock:
            if scan_id not in port_scan_sessions:
                return JsonResponse({'success': False, 'error': '扫描会话不存在'})
            
            session = port_scan_sessions[scan_id]
            
            # 如果使用代理程序，从代理程序获取进度
            if session.get('use_agent', False):
                try:
                    client = PacketAgentClient(session['agent_url'])
                    success, agent_data = client.port_scan_progress(session['agent_scan_id'])
                    
                    if success:
                        # 更新本地会话
                        progress_data = agent_data.get('progress', {})
                        if progress_data:
                            session['scanned'] = progress_data.get('scanned', 0)
                            session['open_ports'] = progress_data.get('open_ports', [])
                            session['closed_ports'] = progress_data.get('closed_ports', [])
                            session['results'] = progress_data.get('results', [])
                        else:
                            # 如果没有progress字段，直接从agent_data获取
                            session['scanned'] = agent_data.get('scanned', 0)
                            session['open_ports'] = agent_data.get('open_ports', [])
                            session['closed_ports'] = agent_data.get('closed_ports', [])
                            session['results'] = agent_data.get('results', [])
                        session['completed'] = agent_data.get('completed', False)
                        session['cancelled'] = agent_data.get('cancelled', False)
                    else:
                        error_msg = agent_data.get('error', '未知错误')
                        logger.warning(f"从代理程序获取扫描进度失败: {error_msg}")
                        # 如果代理程序返回"扫描会话不存在"，可能是扫描还没启动或已过期
                        # 不返回错误，而是返回当前session的状态（可能是初始状态）
                        # 这样前端可以继续轮询，直到扫描真正开始
                except Exception as e:
                    logger.warning(f"从代理程序获取扫描进度时出错: {e}")
                    # 网络错误等异常，不返回错误，返回当前session状态
            
            return JsonResponse({
                'success': True,
                'completed': session.get('completed', False),
                'cancelled': session.get('cancelled', False),
                'scanned': session.get('scanned', 0),
                'total_ports': session.get('total_ports', 0),
                'open_ports': session.get('open_ports', []),
                'closed_ports': session.get('closed_ports', []),
                'results': session.get('results', [])
            })
    
    except Exception as e:
        logger.exception(f"获取扫描进度时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def port_scan_stop(request):
    """停止端口扫描"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        scan_id = data.get('scan_id', '').strip()
        
        if not scan_id:
            return JsonResponse({'success': False, 'error': '缺少scan_id参数'})
        
        with port_scan_lock:
            if scan_id not in port_scan_sessions:
                return JsonResponse({'success': False, 'error': '扫描会话不存在'})
            
            session = port_scan_sessions[scan_id]
            
            # 如果使用代理程序，通知代理程序停止
            if session.get('use_agent', False):
                try:
                    client = PacketAgentClient(session['agent_url'])
                    client.port_scan_stop(session['agent_scan_id'])
                except Exception as e:
                    logger.warning(f"通知代理程序停止扫描失败: {e}")
            
            # 标记为已取消
            session['cancelled'] = True
            session['completed'] = True
        
        return JsonResponse({
            'success': True,
            'message': '扫描已停止'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"停止扫描时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_listener_control(request):
    """服务监听器控制"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        agent_url = data.get('agent_url', '').strip()
        protocol = data.get('protocol', 'tcp').lower()
        action = data.get('action', 'start').lower()
        port = int(data.get('port', 0))
        interface = data.get('interface', '').strip()
        
        if not agent_url:
            return JsonResponse({'success': False, 'error': '缺少代理程序URL参数'})
        # 端口验证：邮件协议使用 smtp_port/imap_port/pop3_port，其他协议使用 port
        if protocol == 'mail':
            smtp_port = int(data.get('smtp_port', 0))
            imap_port = int(data.get('imap_port', 0))
            pop3_port = int(data.get('pop3_port', 0))
            if not smtp_port or smtp_port < 1 or smtp_port > 65535:
                return JsonResponse({'success': False, 'error': 'SMTP 端口无效'})
            if not imap_port or imap_port < 1 or imap_port > 65535:
                return JsonResponse({'success': False, 'error': 'IMAP 端口无效'})
            if not pop3_port or pop3_port < 1 or pop3_port > 65535:
                return JsonResponse({'success': False, 'error': 'POP3 端口无效'})
        elif not port or port < 1 or port > 65535:
            return JsonResponse({'success': False, 'error': '端口无效'})
        
        client = PacketAgentClient(agent_url)
        payload = {
            'protocol': protocol,
            'action': action,
            'port': port,
            'host': '0.0.0.0'
        }
        
        if protocol == 'ftp':
            payload['username'] = data.get('username', 'tdhx')
            payload['password'] = data.get('password', 'tdhx@2017')
            payload['directory'] = data.get('directory', '')
        elif protocol == 'mail':
            # 邮件协议特殊参数
            payload['smtp_port'] = data.get('smtp_port', 25)
            payload['imap_port'] = data.get('imap_port', 143)
            payload['pop3_port'] = data.get('pop3_port', 110)
            payload['domain'] = data.get('domain', 'autotest.com')
            payload['ssl_enabled'] = data.get('ssl_enabled', False)
            payload['accounts'] = data.get('accounts', [])
            
            # 添加调试日志
            logger.info(f"Django API接收到邮件账户数据: {payload['accounts']}")
            logger.info(f"账户数量: {len(payload['accounts'])}")
        
        success, result = client.service_listener(payload)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': result.get('message', '操作成功')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '操作失败')
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"控制监听服务时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_client_control(request):
    """服务客户端控制"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})

    try:
        data = json.loads(request.body)
        agent_url = data.get('agent_url', '').strip()
        protocol = data.get('protocol', 'tcp').lower()
        action = data.get('action', 'start').lower()
        
        if not agent_url:
            return JsonResponse({'success': False, 'error': '缺少代理程序URL参数'})
        
        client = PacketAgentClient(agent_url)
        payload = {
            'protocol': protocol,
            'action': action,
            **{k: v for k, v in data.items() if k not in ['agent_url']}
        }
        
        success, result = client.service_client(payload)
        
        return JsonResponse({
            'success': success,
            'message': result.get('message', ''),
            'error': result.get('error', ''),
            **{k: v for k, v in result.items() if k not in ['message', 'error']}
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"控制客户端服务时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_status_api(request):
    """获取服务状态"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        listener_agent_url = request.GET.get('listener_agent_url', '').strip()
        client_agent_url = request.GET.get('client_agent_url', '').strip()
        
        result = {
            'listeners': {},
            'clients': {}
        }
        
        if listener_agent_url:
            try:
                client = PacketAgentClient(listener_agent_url)
                success, data = client.service_status()
                if success:
                    result['listeners'] = data.get('listeners', {})
            except Exception as e:
                logger.warning(f"获取监听服务状态失败: {e}")
        
        if client_agent_url:
            try:
                client = PacketAgentClient(client_agent_url)
                success, data = client.service_status()
                if success:
                    result['clients'] = data.get('clients', {})
            except Exception as e:
                logger.warning(f"获取客户端服务状态失败: {e}")
        
        return JsonResponse({
            'success': True,
            **result
        })
    
    except Exception as e:
        logger.exception(f"获取服务状态时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def service_logs_api(request):
    """获取服务日志"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        listener_agent_url = request.GET.get('listener_agent_url', '').strip()
        client_agent_url = request.GET.get('client_agent_url', '').strip()
        limit = int(request.GET.get('limit', 100))
        
        logs = []
        
        if listener_agent_url:
            try:
                client = PacketAgentClient(listener_agent_url)
                success, data = client.service_logs(limit)
                if success:
                    listener_logs = data.get('logs', [])
                    for log in listener_logs:
                        logs.append({
                            **log,
                            'source': '监听服务',
                            'agent_type': 'listener'
                        })
            except Exception as e:
                logger.warning(f"获取监听服务日志失败: {e}")
        
        if client_agent_url:
            try:
                client = PacketAgentClient(client_agent_url)
                success, data = client.service_logs(limit)
                if success:
                    client_logs = data.get('logs', [])
                    for log in client_logs:
                        logs.append({
                            **log,
                            'source': '客户端',
                            'agent_type': 'client'
                        })
            except Exception as e:
                logger.warning(f"获取客户端服务日志失败: {e}")
        
        # 按时间戳排序
        logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return JsonResponse({
            'success': True,
            'logs': logs[:limit]
        })
    
    except Exception as e:
        logger.exception(f"获取服务日志时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def device_monitoring_toggle(request):
    """开启/关闭设备监测"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id', '').strip()
        enabled = data.get('enabled', False)
        device_info = data.get('device_info', {})
        
        if not device_id:
            return JsonResponse({'success': False, 'error': '设备ID不能为空'})
        
        if not device_info:
            return JsonResponse({'success': False, 'error': '设备信息不能为空'})
        
        if enabled:
            start_device_monitoring(device_id, device_info)
        else:
            stop_device_monitoring(device_id)
        
        return JsonResponse({
            'success': True,
            'message': '监测状态已更新'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"切换设备监测状态时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def device_monitoring_status(request):
    """获取所有设备的监测状态"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        status = get_monitoring_status()
        return JsonResponse({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.exception(f"获取监测状态时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def device_alert_config(request):
    """获取或保存告警配置"""
    if request.method == 'GET':
        try:
            config = get_alert_config()
            # 返回完整配置（包括密码），前端会处理密码显示
            return JsonResponse({
                'success': True,
                'config': config
            })
        except Exception as e:
            logger.exception(f"获取告警配置时出错: {e}")
            return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            success = update_alert_config(data)
            if success:
                return JsonResponse({
                    'success': True,
                    'message': '配置保存成功'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': '配置保存失败'
                })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': '请求数据格式错误'})
        except Exception as e:
            logger.exception(f"保存告警配置时出错: {e}")
            return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})


@csrf_exempt
def device_alert_config_test(request):
    """测试邮件发送"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        
        # 创建测试邮件内容
        test_content = format_alert_email_content(
            {'name': '测试设备', 'ip': '192.168.1.100', 'type': '测试'},
            'resource',
            {
                'cpu_usage': 85.5,
                'memory_usage': 82.3,
                'memory_total': 8192,
                'memory_used': 6734,
                'memory_free': 1458,
                'resource_info': {
                    'cpu_usage': 85.5,
                    'memory_usage': 82.3,
                    'memory_total': 8192,
                    'memory_used': 6734,
                    'memory_free': 1458
                }
            }
        )
        
        try:
            success = send_alert_email(
                data,
                '[测试邮件] 设备监控系统告警测试',
                test_content,
                data.get('recipients', [])
            )
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': '测试邮件发送成功'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': '测试邮件发送失败，请检查配置'
                })
        except Exception as e:
            logger.exception(f"测试邮件发送时出错: {e}")
            return JsonResponse({
                'success': False,
                'error': f'测试邮件发送失败: {str(e)}'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"测试邮件发送时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def test_env(request):
    """测试环境管理页面"""
    return render(request, 'test_env.html')


@csrf_exempt
def test_env_list(request):
    """获取所有测试环境"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        envs = TestEnvironment.objects.all().values()
        env_list = list(envs)
        return JsonResponse({'success': True, 'environments': env_list})
    except Exception as e:
        logger.exception(f"获取环境列表时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def test_env_add(request):
    """添加测试环境"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        ip = data.get('ip', '').strip()
        env_type = data.get('type', 'linux').strip()
        user = data.get('user', '').strip()
        password = data.get('password', '')
        port = int(data.get('port', 22))

        if not name or not ip or not user or not password:
            return JsonResponse({'success': False, 'error': '请填写必填项'})

        env = TestEnvironment.objects.create(
            name=name,
            ip=ip,
            type=env_type,
            ssh_user=user,
            ssh_password=password,
            ssh_port=port
        )
        return JsonResponse({'success': True, 'message': '环境已添加', 'env_id': env.id})
    except Exception as e:
        logger.exception(f"添加环境时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def test_env_update(request):
    """更新测试环境信息"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        env_id = data.get('id')
        if not env_id:
            return JsonResponse({'success': False, 'error': '环境ID不能为空'})

        env = TestEnvironment.objects.get(id=env_id)
        env.name = data.get('name', env.name).strip()
        env.ip = data.get('ip', env.ip).strip()
        env.type = data.get('type', env.type).strip()
        env.ssh_user = data.get('user', env.ssh_user).strip()
        env.ssh_password = data.get('password', env.ssh_password)
        env.ssh_port = int(data.get('port', env.ssh_port))
        env.save()

        return JsonResponse({'success': True, 'message': '环境信息已更新'})
    except TestEnvironment.DoesNotExist:
        return JsonResponse({'success': False, 'error': '环境不存在'})
    except Exception as e:
        logger.exception(f"更新环境时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def test_env_delete(request):
    """删除测试环境"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        env_id = data.get('id')
        if not env_id:
            return JsonResponse({'success': False, 'error': '环境ID不能为空'})

        TestEnvironment.objects.filter(id=env_id).delete()
        return JsonResponse({'success': True, 'message': '环境已删除'})
    except Exception as e:
        logger.exception(f"删除环境时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def test_env_test_connection(request):
    """测试SSH连接"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        ip = data.get('ip', '').strip()
        port = int(data.get('port', 22))
        user = data.get('user', '').strip()
        password = data.get('password', '')
        
        if not ip or not user or not password:
            return JsonResponse({'success': False, 'error': '请填写完整的连接信息'})
        
        success = test_ssh_connection(ip, user, password, port)
        
        if success:
            return JsonResponse({'success': True, 'message': '连接成功'})
        else:
            return JsonResponse({'success': False, 'error': '连接失败，请检查IP、端口、用户名和密码'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"测试SSH连接时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def test_env_agent_control(request):
    """控制Agent启动/关闭"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        env_id = data.get('env_id', '').strip()
        action = data.get('action', '').strip()  # 'start' 或 'stop'
        env = data.get('env', {})
        
        if not env_id or not action or not env:
            return JsonResponse({'success': False, 'error': '参数不完整'})
        
        ip = env.get('ip', '').strip()
        port = int(env.get('port', 22))
        user = env.get('user', '').strip()
        password = env.get('password', '')
        env_type = env.get('type', 'linux')
        
        if not ip or not user or not password:
            return JsonResponse({'success': False, 'error': '环境信息不完整'})
        
        if action == 'start':
            # 先上传文件
            success, message, files = upload_files_via_sftp(ip, user, password, port, 'packet_agent', env_type)
            if not success:
                return JsonResponse({'success': False, 'error': f'文件上传失败: {message}'})
            
            # 启动Agent
            success, message = start_agent(ip, user, password, port, env_type)
            if success:
                return JsonResponse({'success': True, 'message': message, 'files_count': len(files)})
            else:
                return JsonResponse({'success': False, 'error': message})
        
        elif action == 'stop':
            success, message = stop_agent(ip, user, password, port, env_type)
            if success:
                return JsonResponse({'success': True, 'message': message})
            else:
                return JsonResponse({'success': False, 'error': message})
        
        else:
            return JsonResponse({'success': False, 'error': '无效的操作类型'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"控制Agent时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def test_env_agent_status(request):
    """获取所有环境的Agent状态"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        envs = TestEnvironment.objects.all()
        status_dict = {}
        
        # 为了效率，这里可以只检查数据库中存在的环境
        for env in envs:
            # 暂时返回未知，由前端单独触发检查，或者在这里进行异步检查
            status_dict[str(env.id)] = 'unknown'
            
        return JsonResponse({
            'success': True,
            'status': status_dict
        })
    except Exception as e:
        logger.exception(f"获取Agent状态时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def test_env_execute_command(request):
    """执行测试环境命令（支持Windows和Linux）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        host = data.get('host', '').strip()
        port = int(data.get('port', 22))
        user = data.get('user', '').strip()
        password = data.get('password', '')
        command = data.get('command', '').strip()
        env_type = data.get('env_type', 'linux')  # 'windows' 或 'linux'
        timeout = int(data.get('timeout', 30))
        
        if not host:
            return JsonResponse({'success': False, 'error': '主机地址不能为空'})
        if not user:
            return JsonResponse({'success': False, 'error': '用户名不能为空'})
        if not password:
            return JsonResponse({'success': False, 'error': '密码不能为空'})
        if not command:
            return JsonResponse({'success': False, 'error': '命令不能为空'})
        
        # 导入测试环境工具
        try:
            from .test_env_utils import execute_ssh_command
        except ImportError:
            return JsonResponse({'success': False, 'error': '测试环境工具模块未加载'})
        
        # 执行命令
        success, output, error = execute_ssh_command(
            host=host,
            user=user,
            password=password,
            port=port,
            command=command,
            env_type=env_type,
            timeout=timeout
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'output': output
            })
        else:
            return JsonResponse({
                'success': False,
                'error': error or '命令执行失败',
                'output': output  # 即使失败也返回输出
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"执行测试环境命令时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def syslog_receiver(request):
    """Syslog日志接收页面"""
    return render(request, 'syslog_receiver.html')


@csrf_exempt
def syslog_control(request):
    """Syslog服务器控制（启动/停止）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        action = data.get('action', '').strip().lower()
        port = int(data.get('port', 514))
        
        if action == 'start':
            if port < 1 or port > 65535:
                return JsonResponse({'success': False, 'error': '端口号无效（1-65535）'})
            success, message = start_syslog_server(port)
            return JsonResponse({'success': success, 'message': message})
        elif action == 'stop':
            success, message = stop_syslog_server()
            return JsonResponse({'success': success, 'message': message})
        else:
            return JsonResponse({'success': False, 'error': '无效的操作类型'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"控制syslog服务器时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def syslog_status(request):
    """获取Syslog服务器状态"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        status = get_syslog_status()
        return JsonResponse({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.exception(f"获取syslog状态时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def syslog_logs(request):
    """获取Syslog日志"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        limit = int(request.GET.get('limit', 1000))
        filter_ip = request.GET.get('filter_ip', '').strip()
        
        logs = get_syslog_logs(limit=limit, filter_ip=filter_ip)
        return JsonResponse({
            'success': True,
            'logs': logs
        })
    except Exception as e:
        logger.exception(f"获取syslog日志时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def syslog_clear(request):
    """清空Syslog日志"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        success, message = clear_syslog_logs()
        return JsonResponse({'success': success, 'message': message})
    except Exception as e:
        logger.exception(f"清空syslog日志时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def syslog_filter(request):
    """设置Syslog IP过滤"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        filter_ip = data.get('filter_ip', '').strip()
        
        success, message = set_syslog_filter_ip(filter_ip)
        return JsonResponse({'success': success, 'message': message})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"设置syslog过滤时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


def download_agent_exe(request):
    """下载Agent程序的exe文件"""
    import os
    
    # exe文件路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe_path = os.path.join(base_dir, 'packet_agent', 'dist', 'packet_agent.exe')
    
    if not os.path.exists(exe_path):
        # 如果exe不存在，返回提示信息
        return JsonResponse({
            'success': False,
            'error': 'exe文件尚未生成，请先运行打包脚本生成exe文件。打包脚本位置: packet_agent/build_exe.bat'
        }, status=404)
    
    try:
        response = FileResponse(
            open(exe_path, 'rb'),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = 'attachment; filename="packet_agent.exe"'
        response['Content-Length'] = os.path.getsize(exe_path)
        return response
    except Exception as e:
        logger.exception(f"下载exe文件时出错: {e}")
        return JsonResponse({'success': False, 'error': f'下载失败: {str(e)}'}, status=500)


@csrf_exempt
def snmp(request):
    """SNMP管理页面"""
    return render(request, 'snmp.html')


@csrf_exempt
def snmp_get_api(request):
    """SNMP GET API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        ip = data.get('ip', '').strip()
        oid = data.get('oid', '').strip()
        community = data.get('community', 'public').strip()
        version = data.get('version', '2c').strip()
        port = int(data.get('port', 161))
        walk = data.get('walk', False)  # 是否使用WALK
        
        # SNMPv3参数
        security_username = data.get('security_username', '').strip()
        security_level = data.get('security_level', 'noAuthNoPriv').strip()
        auth_protocol = data.get('auth_protocol', 'MD5').strip()
        auth_password = data.get('auth_password', '').strip()
        priv_protocol = data.get('priv_protocol', 'DES').strip()
        priv_password = data.get('priv_password', '').strip()
        
        if not ip:
            return JsonResponse({'success': False, 'error': 'IP地址不能为空'})
        if not oid:
            return JsonResponse({'success': False, 'error': 'OID不能为空'})
        
        # 执行SNMP操作
        if walk:
            success, result = snmp_walk(
                ip, oid, community, version, port,
                security_username, security_level,
                auth_protocol, auth_password,
                priv_protocol, priv_password
            )
        else:
            success, result = snmp_get(
                ip, oid, community, version, port,
                security_username, security_level,
                auth_protocol, auth_password,
                priv_protocol, priv_password
            )
        
        if success:
            return JsonResponse({
                'success': True,
                'data': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"SNMP GET操作时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def snmp_trap_control(request):
    """SNMPTRAP接收器控制"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        logger.info("收到SNMPTRAP控制请求")
        data = json.loads(request.body)
        action = data.get('action', '').strip().lower()
        port = int(data.get('port', 162))
        
        logger.info(f"SNMPTRAP控制请求: action={action}, port={port}")
        
        if action == 'start':
            if port < 1 or port > 65535:
                return JsonResponse({'success': False, 'error': '端口号无效（1-65535）'})
            
            # 获取SNMPv3配置参数
            security_username = data.get('security_username', '').strip()
            security_level = data.get('security_level', 'noAuthNoPriv').strip()
            auth_protocol = data.get('auth_protocol', 'MD5').strip()
            auth_password = data.get('auth_password', '').strip()
            priv_protocol = data.get('priv_protocol', 'DES').strip()
            priv_password = data.get('priv_password', '').strip()
            
            logger.info(f"开始启动SNMPTRAP接收器: port={port}, security_username={security_username}, security_level={security_level}")
            
            success, message = start_trap_receiver(
                port=port,
                security_username=security_username,
                security_level=security_level,
                auth_protocol=auth_protocol,
                auth_password=auth_password,
                priv_protocol=priv_protocol,
                priv_password=priv_password
            )
            
            logger.info(f"SNMPTRAP接收器启动结果: success={success}, message={message}")
            return JsonResponse({'success': success, 'message': message})
        elif action == 'stop':
            logger.info("停止SNMPTRAP接收器")
            success, message = stop_trap_receiver()
            logger.info(f"SNMPTRAP接收器停止结果: success={success}, message={message}")
            return JsonResponse({'success': success, 'message': message})
        else:
            return JsonResponse({'success': False, 'error': '无效的操作类型'})
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"控制SNMPTRAP接收器时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def snmp_trap_status(request):
    """获取SNMPTRAP接收器状态"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        status = get_trap_receiver_status()
        return JsonResponse({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.exception(f"获取SNMPTRAP状态时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def snmp_trap_traps(request):
    """获取接收到的TRAP列表"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        limit = int(request.GET.get('limit', 1000))
        traps = get_trap_receiver_traps(limit=limit)
        return JsonResponse({
            'success': True,
            'traps': traps
        })
    except Exception as e:
        logger.exception(f"获取TRAP列表时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def snmp_trap_clear(request):
    """清空TRAP列表"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        success, message = clear_trap_receiver_traps()
        return JsonResponse({'success': success, 'message': message})
    except Exception as e:
        logger.exception(f"清空TRAP列表时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def get_protocol_files(request):
    """获取cus_prot目录中的协议文件列表"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        import os
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cus_prot_dir = os.path.join(project_root, 'cus_prot')
        
        if not os.path.exists(cus_prot_dir):
            return JsonResponse({'success': False, 'error': 'cus_prot目录不存在'})
        
        # 获取所有文件
        files = []
        for filename in os.listdir(cus_prot_dir):
            file_path = os.path.join(cus_prot_dir, filename)
            if os.path.isfile(file_path):
                files.append(filename)
        
        files.sort()  # 排序
        return JsonResponse({'success': True, 'files': files})
    
    except Exception as e:
        logger.exception(f"获取协议文件列表时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def send_custom_protocol(request):
    """发送自定义协议请求（上传文件到prototree_import）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        ip_address = data.get('ip_address', '').strip()
        cookie = data.get('cookie', '').strip()
        request_data = data.get('request_data', {})
        
        if not ip_address:
            return JsonResponse({'success': False, 'error': '缺少IP地址参数'})
        if not cookie:
            return JsonResponse({'success': False, 'error': '缺少Cookie参数'})
        if not request_data:
            return JsonResponse({'success': False, 'error': '缺少请求数据参数'})
        
        loginuser = request_data.get('loginuser', '').strip()
        prototree_file = request_data.get('prototree_file', '').strip()
        
        if not loginuser:
            return JsonResponse({'success': False, 'error': '缺少登录用户参数'})
        if not prototree_file:
            return JsonResponse({'success': False, 'error': '缺少协议文件参数'})
        
        # 读取文件内容
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(project_root, 'cus_prot', prototree_file)
        
        if not os.path.exists(file_path):
            return JsonResponse({'success': False, 'error': f'文件不存在: {prototree_file}'})
        
        # 读取文件为二进制
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # 准备multipart/form-data请求
        # 注意：目标URL是固定的 https://10.40.20.13/prototree_import
        # 但根据需求，应该使用传入的ip_address
        target_url = f"https://{ip_address}/prototree_import"
        
        # 准备文件数据
        files = {
            'prototree_file': (prototree_file, file_content, 'application/octet-stream')
        }
        
        # 准备表单数据
        form_data = {
            'loginuser': loginuser
        }
        
        # 设置请求头
        headers = {
            "Cookie": cookie,
            "User-Agent": USER_AGENT,
        }
        
        # 发送POST请求（multipart/form-data）
        response = requests.post(
            target_url,
            files=files,
            data=form_data,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            return JsonResponse({
                'success': True,
                'response': response.text,
                'status_code': response.status_code
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'请求失败，状态码: {response.status_code}',
                'status_code': response.status_code,
                'response': response.text
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except FileNotFoundError as e:
        return JsonResponse({'success': False, 'error': f'文件未找到: {str(e)}'})
    except Exception as e:
        logger.exception(f"发送自定义协议请求时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


# ========== 报文回放相关API ==========

# 全局回放状态
replay_state = {
    'running': False,
    'status': 'waiting',  # 'waiting': 等待开始回放, 'running': 正在回放, 'completed': 回放已完成, 'stopped': 回放手动中断
    'device': None,
    'interface': None,
    'packet_files': [],
    'packets_sent': 0,
    'start_time': None,
    'rate': 0,
    'thread': None,
    'process': None,
    'agent_url': None  # 记录Agent URL，用于停止Agent上的回放
}
replay_lock = threading.Lock()


@csrf_exempt
def packet_replay(request):
    """报文回放页面"""
    return render(request, 'packet_replay.html')


@csrf_exempt
def packet_replay_connect(request):
    """连接设备"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        ip = data.get('ip', '').strip()
        user = data.get('user', '').strip()
        password = data.get('password', '')
        port = int(data.get('port', 22))
        device_type = data.get('type', 'linux').strip()
        
        if not ip or not user or not password:
            return JsonResponse({'success': False, 'error': '请填写完整的连接信息'})
        
        # 测试SSH连接
        success = test_ssh_connection(ip, user, password, port)
        if success:
            return JsonResponse({
                'success': True,
                'message': '连接成功',
                'device_type': device_type
            })
        else:
            return JsonResponse({'success': False, 'error': '连接失败，请检查IP、端口、用户名和密码'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"连接设备时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def packet_replay_interfaces(request):
    """获取设备网口列表"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        ip = data.get('ip', '').strip()
        user = data.get('user', '').strip()
        password = data.get('password', '')
        port = int(data.get('port', 22))
        device_type = data.get('type', 'linux').strip()
        
        if not ip:
            return JsonResponse({'success': False, 'error': '缺少IP地址参数'})
        
        try:
            import paramiko
        except ImportError:
            return JsonResponse({'success': False, 'error': 'paramiko模块未安装'})
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port, user, password, timeout=10)
            
            interfaces = []
            
            if device_type == 'windows':
                # Windows系统：通过Agent获取（如果Agent运行）或通过PowerShell
                # 先尝试通过Agent获取（Agent默认端口8888）
                try:
                    agent_url = f"http://{ip}:8888/api/interfaces"
                    response = requests.get(agent_url, timeout=5)
                    if response.status_code == 200:
                        agent_data = response.json()
                        if agent_data.get('success'):
                            agent_interfaces = agent_data.get('interfaces', [])
                            # 转换Agent返回的接口格式，包含完整信息
                            for iface in agent_interfaces:
                                interfaces.append({
                                    'name': iface.get('name', ''),
                                    'display_name': iface.get('display_name', iface.get('name', '')),
                                    'ip': iface.get('ip', ''),
                                    'mac': iface.get('mac', ''),
                                    'description': iface.get('display_name', iface.get('description', ''))
                                })
                            logger.info(f"通过Agent获取到 {len(interfaces)} 个网口")
                except Exception as e:
                    logger.warning(f"通过Agent获取网口失败: {e}，尝试使用PowerShell")
                
                # 如果Agent不可用，使用PowerShell
                if not interfaces:
                    try:
                        # 使用更简单的PowerShell命令
                        stdin, stdout, stderr = ssh.exec_command(
                            'powershell -Command "Get-NetAdapter | Where-Object {$_.Status -eq \'Up\'} | ForEach-Object { $_.Name }"'
                        )
                        output = stdout.read().decode('utf-8', errors='ignore')
                        error_output = stderr.read().decode('utf-8', errors='ignore')
                        
                        if error_output:
                            logger.warning(f"PowerShell错误: {error_output}")
                        
                        for line in output.strip().split('\n'):
                            line = line.strip()
                            if line and line.lower() not in ['name', '']:
                                interfaces.append({
                                    'name': line,
                                    'description': ''
                                })
                        
                        logger.info(f"通过PowerShell获取到 {len(interfaces)} 个网口")
                    except Exception as e:
                        logger.error(f"PowerShell获取网口失败: {e}")
                        raise
            else:
                # Linux系统：使用ip命令或ifconfig
                stdin, stdout, stderr = ssh.exec_command("ip -o link show | awk -F': ' '{print $2}'")
                output = stdout.read().decode('utf-8')
                for line in output.strip().split('\n'):
                    if line and 'lo' not in line:
                        interfaces.append({
                            'name': line.strip(),
                            'description': ''
                        })
            
            ssh.close()
            
            return JsonResponse({
                'success': True,
                'interfaces': interfaces
            })
        
        except paramiko.AuthenticationException:
            return JsonResponse({'success': False, 'error': 'SSH认证失败'})
        except paramiko.SSHException as e:
            return JsonResponse({'success': False, 'error': f'SSH连接失败: {str(e)}'})
        except Exception as e:
            logger.exception(f"获取网口列表时出错: {e}")
            return JsonResponse({'success': False, 'error': f'获取网口列表失败: {str(e)}'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"获取网口列表时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def packet_replay_files(request):
    """获取报文文件列表"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        import os
        device_type = request.GET.get('device_type', '').strip()
        
        if not device_type:
            return JsonResponse({'success': False, 'error': '缺少设备类型参数'})
        
        # 确定目录
        if device_type == 'firewall':
            packet_dir = 'SFW'
        elif device_type in ['audit', 'ids']:
            packet_dir = 'IMAP'
        else:
            return JsonResponse({'success': False, 'error': '无效的设备类型'})
        
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        packet_path = os.path.join(project_root, 'packets', packet_dir)
        
        if not os.path.exists(packet_path):
            return JsonResponse({'success': False, 'error': f'目录不存在: {packet_path}'})
        
        # 获取所有.pcap文件
        files = []
        for filename in os.listdir(packet_path):
            file_path = os.path.join(packet_path, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(('.pcap', '.cap')):
                files.append(filename)
        
        files.sort()
        return JsonResponse({'success': True, 'files': files})
    
    except Exception as e:
        logger.exception(f"获取报文文件列表时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


def packet_replay_worker(config):
    """报文回放工作线程"""
    global replay_state
    
    # 添加短暂延迟，确保前端有时间获取到 'running' 状态
    import time
    time.sleep(0.1)
    
    try:
        device = config['device']
        interface = config['interface']
        packet_files = config['packet_files']
        device_type = config['device_type']
        replay_rate = config.get('replay_rate', '1')
        replay_count = config.get('replay_count', 1)
        replay_throughput = config.get('replay_throughput')
        
        # 确定报文目录
        if device_type == 'firewall':
            packet_dir = 'SFW'
        else:
            packet_dir = 'IMAP'
        
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        packet_path = os.path.join(project_root, 'packets', packet_dir)
        
        # 处理"全部"选项
        if '__ALL__' in packet_files:
            all_files = []
            for filename in os.listdir(packet_path):
                if filename.lower().endswith(('.pcap', '.cap')):
                    all_files.append(filename)
            packet_files = all_files
        
        # 构建文件路径列表
        file_paths = [os.path.join(packet_path, f) for f in packet_files if os.path.exists(os.path.join(packet_path, f))]
        
        if not file_paths:
            logger.error("没有找到可用的报文文件")
            with replay_lock:
                replay_state['running'] = False
                replay_state['status'] = 'stopped'  # 错误停止
            return
        
        # 根据设备类型选择回放方式
        if device.get('type') == 'windows':
            # Windows: 使用Agent回放
            replay_via_agent(device, interface, file_paths, replay_rate, replay_count, replay_throughput)
        else:
            # Linux: 使用tcpreplay
            replay_via_tcpreplay(device, interface, file_paths, replay_rate, replay_count, replay_throughput)
    
    except Exception as e:
        logger.exception(f"报文回放工作线程出错: {e}")
        with replay_lock:
            replay_state['running'] = False
            replay_state['status'] = 'stopped'  # 错误停止


def replay_via_agent(device, interface, file_paths, replay_rate, replay_count, replay_throughput):
    """通过Agent回放（Windows）"""
    global replay_state
    
    try:
        import os
        import base64
        
        agent_url = f"http://{device['ip']}:8888"
        
        # 记录Agent URL到全局状态
        with replay_lock:
            replay_state['agent_url'] = agent_url
        
        # 上传pcap文件到Agent
        uploaded_files = []
        for local_file in file_paths:
            filename = os.path.basename(local_file)
            
            try:
                # 读取文件内容
                with open(local_file, 'rb') as f:
                    file_content = f.read()
                
                # 上传文件到Agent
                files = {'file': (filename, file_content, 'application/octet-stream')}
                upload_response = requests.post(
                    f'{agent_url}/api/packet_replay/upload',
                    files=files,
                    timeout=60
                )
                
                if upload_response.status_code == 200:
                    upload_data = upload_response.json()
                    if upload_data.get('success'):
                        uploaded_files.append(upload_data.get('file_path'))
                        logger.info(f"文件上传成功: {filename} -> {upload_data.get('file_path')}")
                    else:
                        logger.error(f"文件上传失败: {upload_data.get('error')}")
                else:
                    logger.error(f"文件上传失败，状态码: {upload_response.status_code}")
            
            except Exception as e:
                logger.exception(f"上传文件 {filename} 失败: {e}")
                continue
        
        if not uploaded_files:
            logger.error("没有成功上传任何文件")
            with replay_lock:
                replay_state['running'] = False
                replay_state['status'] = 'stopped'  # 错误停止
            return
        
        # 在启动新回放之前，先检查并停止Agent上可能正在运行的回放
        try:
            status_response = requests.get(
                f'{agent_url}/api/packet_replay/status',
                timeout=5
            )
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get('success') and status_data.get('running', False):
                    logger.warning("检测到Agent上已有回放在运行，先停止它")
                    stop_response = requests.post(
                        f'{agent_url}/api/packet_replay/stop',
                        timeout=5
                    )
                    if stop_response.status_code == 200:
                        logger.info("已停止Agent上的旧回放")
                        # 等待一下，确保停止完成
                        time.sleep(0.5)
                    else:
                        logger.warning(f"停止Agent上的旧回放失败，状态码: {stop_response.status_code}")
        except Exception as e:
            logger.warning(f"检查Agent回放状态失败: {e}，继续尝试启动新回放")
        
        # 启动回放
        replay_config = {
            'interface': interface,
            'pcap_files': uploaded_files,
            'replay_rate': replay_rate,
            'replay_count': replay_count,
            'replay_throughput': replay_throughput
        }
        
        logger.info(f"向Agent发送回放请求: interface={interface}, files={len(uploaded_files)}, rate={replay_rate}, count={replay_count}")
        logger.debug(f"回放配置: {replay_config}")
        
        start_response = requests.post(
            f'{agent_url}/api/packet_replay/start',
            json=replay_config,
            timeout=30
        )
        
        if start_response.status_code == 200:
            start_data = start_response.json()
            if start_data.get('success'):
                logger.info(f"Agent回放已启动: {start_data.get('message')}")
                
                # 监控回放状态
                while replay_state['running']:
                    try:
                        status_response = requests.get(
                            f'{agent_url}/api/packet_replay/status',
                            timeout=5
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            if status_data.get('success'):
                                if not status_data.get('running', False):
                                    logger.info("Agent回放已完成")
                                    # 确保状态更新为完成
                                    with replay_lock:
                                        replay_state['running'] = False
                                        replay_state['status'] = 'completed'  # 回放已完成
                                        replay_state['packets_sent'] = status_data.get('packets_sent', 0)
                                        replay_state['rate'] = status_data.get('rate', 0)
                                    break
                                
                                # 更新状态
                                with replay_lock:
                                    replay_state['packets_sent'] = status_data.get('packets_sent', 0)
                                    replay_state['rate'] = status_data.get('rate', 0)
                        
                        time.sleep(1)
                    
                    except Exception as e:
                        logger.error(f"获取回放状态失败: {e}")
                        time.sleep(1)
                
                # 循环结束后，确保状态更新为完成
                with replay_lock:
                    replay_state['running'] = False
                    replay_state['status'] = 'completed'  # 回放已完成
            else:
                error_msg = start_data.get('error', '未知错误')
                logger.error(f"启动Agent回放失败: {error_msg}")
                logger.error(f"Agent响应: {start_data}")
                with replay_lock:
                    replay_state['running'] = False
                    replay_state['status'] = 'stopped'  # 错误停止
        else:
            # 尝试获取错误详情
            try:
                error_data = start_response.json()
                error_msg = error_data.get('error', f'状态码: {start_response.status_code}')
                logger.error(f"启动Agent回放失败: {error_msg}")
                logger.error(f"Agent响应: {error_data}")
            except:
                error_msg = f'状态码: {start_response.status_code}'
                logger.error(f"启动Agent回放失败: {error_msg}")
                logger.error(f"响应内容: {start_response.text[:500]}")
            with replay_lock:
                replay_state['running'] = False
                replay_state['status'] = 'stopped'  # 错误停止
    
    except Exception as e:
        logger.exception(f"Agent回放出错: {e}")
        with replay_lock:
            replay_state['running'] = False
            replay_state['status'] = 'stopped'  # 错误停止


def replay_via_tcpreplay(device, interface, file_paths, replay_rate, replay_count, replay_throughput):
    """通过tcpreplay回放（Linux）"""
    global replay_state
    
    try:
        import paramiko
        import os
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device['ip'], device.get('port', 22), device['user'], device['password'], timeout=30)
        
        # 上传pcap文件到远程主机
        sftp = ssh.open_sftp()
        remote_dir = '/tmp/packet_replay'
        
        # 创建远程目录
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
        stdout.read()
        
        # 上传文件
        uploaded_files = []
        for local_file in file_paths:
            filename = os.path.basename(local_file)
            remote_file = f'{remote_dir}/{filename}'
            sftp.put(local_file, remote_file)
            uploaded_files.append(remote_file)
        
        sftp.close()
        
        # 构建tcpreplay命令
        # 回放速率
        if replay_rate == 'max':
            rate_option = '--topspeed'
        elif replay_rate == '1':
            rate_option = ''
        else:
            rate_option = f'--multiplier={replay_rate}'
        
        # 回放次数
        if replay_count == -1:
            loop_option = '--loop=-1'  # 无限循环
        else:
            loop_option = f'--loop={replay_count}'
        
        # 吞吐限制
        throughput_option = ''
        if replay_throughput:
            throughput_option = f'--mbps={replay_throughput}'
        
        # 执行回放
        for remote_file in uploaded_files:
            cmd = f'tcpreplay -i {interface} {rate_option} {loop_option} {throughput_option} {remote_file}'
            logger.info(f"执行回放命令: {cmd}")
            
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            # 实时读取输出
            while True:
                if not replay_state['running']:
                    break
                line = stdout.readline()
                if not line:
                    break
                logger.info(f"tcpreplay输出: {line.strip()}")
                # 解析输出更新状态
                # tcpreplay输出格式: "Actual: 1234 packets (123456 bytes) sent in 1.23s"
                if 'packets' in line.lower():
                    try:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'packets':
                                if i > 0:
                                    packets = int(parts[i-1])
                                    with replay_lock:
                                        replay_state['packets_sent'] += packets
                                break
                    except:
                        pass
        
        # 清理远程文件
        ssh.exec_command(f'rm -rf {remote_dir}')
        ssh.close()
        
        with replay_lock:
            replay_state['running'] = False
            replay_state['status'] = 'completed'  # 回放已完成
    
    except Exception as e:
        logger.exception(f"tcpreplay回放出错: {e}")
        with replay_lock:
            replay_state['running'] = False
            replay_state['status'] = 'stopped'  # 错误停止


@csrf_exempt
def packet_replay_start(request):
    """启动报文回放"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        
        with replay_lock:
            if replay_state['running']:
                return JsonResponse({'success': False, 'error': '回放已在运行中'})
            
            replay_state['running'] = True
            replay_state['status'] = 'running'  # 设置为正在回放
            replay_state['device'] = data.get('device')
            replay_state['interface'] = data.get('interface')
            replay_state['packet_files'] = data.get('packet_files', [])
            replay_state['packets_sent'] = 0
            replay_state['start_time'] = time.time()
            replay_state['rate'] = 0
            # 如果是Windows设备，记录Agent URL
            device = data.get('device', {})
            if device.get('type') == 'windows':
                replay_state['agent_url'] = f"http://{device.get('ip')}:8888"
            else:
                replay_state['agent_url'] = None
        
        # 启动工作线程
        thread = threading.Thread(target=packet_replay_worker, args=(data,), daemon=True)
        thread.start()
        with replay_lock:
            replay_state['thread'] = thread
        
        return JsonResponse({'success': True, 'message': '回放已启动'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '请求数据格式错误'})
    except Exception as e:
        logger.exception(f"启动回放时出错: {e}")
        with replay_lock:
            replay_state['running'] = False
            replay_state['status'] = 'stopped'  # 错误停止
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def packet_replay_stop(request):
    """停止报文回放"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        with replay_lock:
            if not replay_state['running']:
                # 即使后端没有运行，也尝试停止Agent上的回放
                # 检查是否有记录的Agent URL
                agent_url = replay_state.get('agent_url')
                if agent_url:
                    try:
                        stop_response = requests.post(
                            f'{agent_url}/api/packet_replay/stop',
                            timeout=5
                        )
                        if stop_response.status_code == 200:
                            logger.info("已停止Agent上的回放")
                    except Exception as e:
                        logger.warning(f"停止Agent回放失败: {e}")
                
                # 确保状态设置为停止
                replay_state['status'] = 'stopped'
                return JsonResponse({'success': True, 'message': '回放已停止（可能未运行）'})
            
            # 停止后端回放
            replay_state['running'] = False
            replay_state['status'] = 'stopped'  # 设置为手动中断
            
            # 如果通过Agent回放，也停止Agent上的回放
            agent_url = replay_state.get('agent_url')
            if agent_url:
                try:
                    stop_response = requests.post(
                        f'{agent_url}/api/packet_replay/stop',
                        timeout=5
                    )
                    if stop_response.status_code == 200:
                        logger.info("已停止Agent上的回放")
                except Exception as e:
                    logger.warning(f"停止Agent回放失败: {e}")
            
            # 如果通过SSH回放（tcpreplay），需要停止远程进程
            device = replay_state.get('device')
            if device and device.get('type') != 'windows':
                # Linux系统，需要停止tcpreplay进程
                try:
                    import paramiko
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(device['ip'], device.get('port', 22), device['user'], device['password'], timeout=10)
                    # 查找并杀死tcpreplay进程
                    ssh.exec_command("pkill -f tcpreplay")
                    ssh.close()
                    logger.info("已停止远程tcpreplay进程")
                except Exception as e:
                    logger.warning(f"停止远程tcpreplay进程失败: {e}")
        
        return JsonResponse({'success': True, 'message': '回放已停止'})
    
    except Exception as e:
        logger.exception(f"停止回放时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


@csrf_exempt
def packet_replay_status(request):
    """获取回放状态"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持GET请求'})
    
    try:
        with replay_lock:
            status = replay_state.get('status', 'waiting')
            running = replay_state['running']
            
            if not running:
                return JsonResponse({
                    'success': True,
                    'running': False,
                    'status': status
                })
            
            # 计算速率
            elapsed = time.time() - replay_state['start_time'] if replay_state['start_time'] else 0
            rate = int(replay_state['packets_sent'] / elapsed) if elapsed > 0 else 0
            replay_state['rate'] = rate
            
            return JsonResponse({
                'success': True,
                'running': True,
                'status': status,
                'packets_sent': replay_state['packets_sent'],
                'rate': rate,
                'progress': f"{replay_state['packets_sent']} packets"
            })
    
    except Exception as e:
        logger.exception(f"获取回放状态时出错: {e}")
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'})


def restore_data(request):
    """数据恢复工具页面"""
    return render(request, 'restore_data.html')


@csrf_exempt
@csrf_exempt
def start_local_mail_service(request):
    """启动本地邮件服务（执行远程 hmail_start.exe）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持 POST 请求'})
    
    try:
        data = json.loads(request.body)
        remote_ip = data.get('remote_ip', '')
        username = data.get('username', 'tdhx')
        password = data.get('password', 'tdhx@2017')
        
        if not remote_ip:
            return JsonResponse({'success': False, 'error': '远程 IP 地址不能为空'})
        
        # 获取 Django 项目根目录下的 packet_agent 目录
        django_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        packet_agent_dir = os.path.join(django_root, 'packet_agent')
        psexec_path = os.path.join(packet_agent_dir, 'PsExec.exe')
        
        if not os.path.exists(psexec_path):
            return JsonResponse({
                'success': False, 
                'error': f'未找到 PsExec.exe，路径：{psexec_path}'
            })
        
        # 使用 PsExec 远程执行 hmail_start.exe
        remote_hmail_path = r'C:\packet_agent\hmail_start.exe'
        psexec_cmd = [
            psexec_path,
            f'\\{remote_ip}',
            '-u', username,
            '-p', password,
            '-i', '1',
            '-h',
            remote_hmail_path
        ]
        
        process = subprocess.Popen(
            psexec_cmd,
            cwd=packet_agent_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        stdout, stderr = process.communicate(timeout=30)
        return_code = process.returncode
        
        if return_code == 0:
            message = f'已启动本地邮件服务（远程：{remote_ip}）'
            return JsonResponse({
                'success': True,
                'message': message
            })
        else:
            error_msg = f'启动失败（返回码：{return_code}）'
            if stderr:
                error_msg += f': {stderr}'
            return JsonResponse({
                'success': False,
                'error': error_msg,
                'stderr': stderr,
                'stdout': stdout
            })
    
    except subprocess.TimeoutExpired:
        return JsonResponse({
            'success': False,
            'error': '执行超时（30 秒）'
        })
    except Exception as e:
        logger.exception(f"启动本地邮件服务时出错：{e}")
        return JsonResponse({
            'success': False,
            'error': f'服务器内部错误：{str(e)}'
        })


# ==================== Redis 分布式锁和设备预留 API ====================

from .redis_lock import acquire_lock, release_lock, check_lock_status, get_global_lock


@csrf_exempt
@require_http_methods(["POST"])
def reserve_device(request):
    """
    预留测试设备

    POST /api/device/reserve/
    Body: {"device_id": 1, "session_id": "user123"}

    Returns:
        {"success": true, "message": "...", "lock_id": "..."}
    """
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        session_id = data.get('session_id', str(uuid.uuid4()))

        if not device_id:
            return JsonResponse({
                'success': False,
                'message': '缺少 device_id 参数'
            }, status=400)

        # 检查设备是否存在
        try:
            device = TestDevice.objects.get(id=device_id)
        except TestDevice.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'设备不存在：ID={device_id}'
            }, status=404)

        # 生成锁标识
        resource_id = f"device:{device_id}"
        lock_session = f"{session_id}:{device_id}"

        # 尝试获取锁
        success, msg = acquire_lock(resource_id, lock_session, timeout=600)  # 10 分钟

        if success:
            return JsonResponse({
                'success': True,
                'message': msg,
                'lock_id': lock_session,
                'device_name': device.name,
                'expires_in': 600
            })
        else:
            # 获取锁失败，返回当前占用者信息
            status = check_lock_status(resource_id)
            return JsonResponse({
                'success': False,
                'message': msg,
                'occupied_by': status.get('owner'),
                'ttl': status.get('ttl')
            }, status=409)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的 JSON 数据'
        }, status=400)
    except Exception as e:
        logger.exception(f"预留设备异常：{e}")
        return JsonResponse({
            'success': False,
            'message': f'服务器错误：{str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def release_device(request):
    """
    释放测试设备

    POST /api/device/release/
    Body: {"device_id": 1, "lock_id": "session:device_id"}

    Returns:
        {"success": true, "message": "..."}
    """
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        lock_id = data.get('lock_id')

        if not device_id or not lock_id:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        resource_id = f"device:{device_id}"

        # 释放锁
        success, msg = release_lock(resource_id, lock_id)

        return JsonResponse({
            'success': success,
            'message': msg
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的 JSON 数据'
        }, status=400)
    except Exception as e:
        logger.exception(f"释放设备异常：{e}")
        return JsonResponse({
            'success': False,
            'message': f'服务器错误：{str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_device_status(request):
    """
    检查设备状态（是否被占用）

    GET /api/device/status/?device_id=1

    Returns:
        {"device_id": 1, "locked": false, "owner": null}
    """
    try:
        device_id = request.GET.get('device_id')

        if not device_id:
            return JsonResponse({
                'success': False,
                'message': '缺少 device_id 参数'
            }, status=400)

        resource_id = f"device:{device_id}"
        status = check_lock_status(resource_id)

        # 获取设备信息
        try:
            device = TestDevice.objects.get(id=device_id)
            device_info = {
                'id': device.id,
                'name': device.name,
                'ip': device.ip,
                'type': device.type
            }
        except TestDevice.DoesNotExist:
            device_info = None

        return JsonResponse({
            'success': True,
            'device_id': int(device_id),
            'device_info': device_info,
            'locked': status.get('locked', False),
            'owner': status.get('owner'),
            'ttl': status.get('ttl', -1)
        })

    except Exception as e:
        logger.exception(f"检查设备状态异常：{e}")
        return JsonResponse({
            'success': False,
            'message': f'服务器错误：{str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def extend_device_lock(request):
    """
    延长设备锁的占用时间

    POST /api/device/extend/
    Body: {"device_id": 1, "lock_id": "...", "additional_time": 600}

    Returns:
        {"success": true, "message": "...", "new_ttl": 600}
    """
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        lock_id = data.get('lock_id')
        additional_time = data.get('additional_time', 600)

        if not device_id or not lock_id:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        lock = get_global_lock()

        resource_id = f"device:{device_id}"
        success, msg = lock.extend(resource_id, lock_id, additional_time)

        return JsonResponse({
            'success': success,
            'message': msg
        })

    except Exception as e:
        logger.exception(f"延长锁时间异常：{e}")
        return JsonResponse({
            'success': False,
            'message': f'服务器错误：{str(e)}'
        }, status=500)


# ============== Agent 文件自动同步 API ==============

@csrf_exempt
def agent_sync_page(request):
    """Agent 自动同步管理页面"""
    return render(request, 'agent_sync.html')


@csrf_exempt
def agent_sync_status(request):
    """获取 Agent 自动同步状态"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '仅支持 GET 请求'})

    try:
        from .agent_auto_sync import get_sync_status

        status = get_sync_status()
        return JsonResponse({
            'success': True,
            **status
        })

    except Exception as e:
        logger.exception(f"获取同步状态异常：{e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def agent_sync_start(request):
    """启动 Agent 自动同步"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持 POST 请求'})

    try:
        from .agent_auto_sync import start_agent_sync
        import json

        data = json.loads(request.body) if request.body else {}

        watch_dir = data.get('watch_dir')
        remote_hosts = data.get('remote_hosts', ['10.40.30.35', '10.40.30.34'])
        user = data.get('user', 'tdhx')
        password = data.get('password', 'tdhx@2017')
        port = int(data.get('port', 22))

        success = start_agent_sync(
            watch_dir=watch_dir,
            remote_hosts=remote_hosts,
            user=user,
            password=password,
            port=port
        )

        return JsonResponse({
            'success': success,
            'message': 'Agent 自动同步已启动' if success else 'Agent 自动同步已在运行中'
        })

    except Exception as e:
        logger.exception(f"启动同步异常：{e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def agent_sync_stop(request):
    """停止 Agent 自动同步"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持 POST 请求'})

    try:
        from .agent_auto_sync import stop_agent_sync

        success = stop_agent_sync()

        return JsonResponse({
            'success': success,
            'message': 'Agent 自动同步已停止' if success else 'Agent 自动同步未运行'
        })

    except Exception as e:
        logger.exception(f"停止同步异常：{e}")
        return JsonResponse({'success': False, 'error': str(e)})


