"""
报文代理程序客户端
用于与运行在远程主机上的代理程序通信
"""
import requests
import logging

logger = logging.getLogger(__name__)


class PacketAgentClient:
    """报文代理程序客户端"""
    
    def __init__(self, agent_url):
        """
        初始化客户端
        :param agent_url: 代理程序URL，例如: http://192.168.1.100:8888
        """
        self.agent_url = agent_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
    
    def get_interfaces(self):
        """
        获取网卡列表
        :return: (success, data)
        """
        try:
            response = self.session.get(f"{self.agent_url}/api/interfaces")
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"获取网卡列表失败: {e}")
            return False, {'error': str(e)}
    
    def send_packet(self, interface, packet_config, send_config):
        """
        发送报文
        :param interface: 网卡名称
        :param packet_config: 报文配置
        :param send_config: 发送配置
        :return: (success, data)
        """
        try:
            payload = {
                'interface': interface,
                'packet_config': packet_config,
                'send_config': send_config
            }
            response = self.session.post(
                f"{self.agent_url}/api/send_packet",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"发送报文失败: {e}")
            return False, {'error': str(e)}
    
    def get_statistics(self):
        """
        获取发送统计
        :return: (success, data)
        """
        try:
            response = self.session.get(f"{self.agent_url}/api/statistics")
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"获取统计失败: {e}")
            return False, {'error': str(e)}
    
    def stop_sending(self):
        """
        停止发送
        :return: (success, data)
        """
        try:
            response = self.session.post(f"{self.agent_url}/api/stop")
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"停止发送失败: {e}")
            return False, {'error': str(e)}
    
    def health_check(self):
        """
        健康检查
        :return: (success, data)
        """
        try:
            response = self.session.get(f"{self.agent_url}/api/health", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"健康检查失败: {e}")
            return False, {'error': str(e)}
    
    def port_scan(self, target_ip, ports, timeout=1, scan_type='tcp_syn', interface=None, threads=200, scan_rate=0, port_delay=0):
        """
        端口扫描
        :param target_ip: 目标IP地址
        :param ports: 端口列表
        :param timeout: 超时时间（秒）
        :param scan_type: 扫描类型 (tcp_syn, tcp_fin, tcp_rst, tcp_null, tcp_xmas, tcp_ack, etc.)
        :param interface: 网卡名称（可选）
        :param threads: 并发线程数
        :return: (success, data)
        """
        try:
            payload = {
                'target_ip': target_ip,
                'ports': ports,
                'timeout': timeout,
                'scan_type': scan_type,
                'threads': threads,
                'scan_rate': scan_rate,
                'port_delay': port_delay
            }
            if interface:
                payload['interface'] = interface
            
            response = self.session.post(
                f"{self.agent_url}/api/port_scan",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"端口扫描失败: {e}")
            return False, {'error': str(e)}
    
    def port_scan_progress(self, scan_id):
        """
        获取端口扫描进度
        :param scan_id: 扫描会话ID
        :return: (success, data)
        """
        try:
            response = self.session.get(
                f"{self.agent_url}/api/port_scan/progress",
                params={'scan_id': scan_id},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"获取端口扫描进度失败: {e}")
            return False, {'error': str(e)}
    
    def port_scan_stop(self, scan_id):
        """
        停止端口扫描
        :param scan_id: 扫描会话ID
        :return: (success, data)
        """
        try:
            response = self.session.post(
                f"{self.agent_url}/api/port_scan/stop",
                json={'scan_id': scan_id},
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"停止端口扫描失败: {e}")
            return False, {'error': str(e)}

    def service_listener(self, payload):
        """控制监听服务"""
        try:
            # FTP 服务器启动可能需要更长时间（创建目录、权限检查等）
            protocol = payload.get('protocol', '').lower()
            action = payload.get('action', '').lower()
            if protocol == 'ftp' and action == 'start':
                timeout = 30  # FTP 启动需要更长时间
            else:
                timeout = 15

            response = self.session.post(
                f"{self.agent_url}/api/services/listener",
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"控制监听服务失败: {e}")
            return False, {'success': False, 'error': str(e)}

    def service_client(self, payload):
        """控制客户端服务"""
        try:
            # FTP连接优化：使用较短的超时时间，因为后端已经优化了连接速度
            # 如果后端连接成功但响应慢，前端会通过状态轮询检测到
            # FTP下载需要更长的超时时间，因为可能需要传输大文件
            action = payload.get('action', '')
            protocol = payload.get('protocol', '').lower()
            
            if action == 'connect' and protocol == 'ftp':
                timeout = 15
            elif action == 'download' and protocol == 'ftp':
                timeout = 60  # 下载操作需要更长的超时时间
            else:
                timeout = 10
            
            response = self.session.post(
                f"{self.agent_url}/api/services/client",
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"控制客户端服务失败: {e}")
            return False, {'success': False, 'error': str(e)}

    def service_status(self):
        """获取服务状态"""
        try:
            response = self.session.get(
                f"{self.agent_url}/api/services/status",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"获取服务状态失败: {e}")
            return False, {'success': False, 'error': str(e)}

    def service_logs(self, limit=100):
        """获取服务日志"""
        try:
            response = self.session.get(
                f"{self.agent_url}/api/services/logs",
                params={'limit': limit},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get('success', False), data
        except requests.exceptions.RequestException as e:
            logger.error(f"获取服务日志失败: {e}")
            return False, {'success': False, 'error': str(e)}

