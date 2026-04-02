#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备监测后台任务模块
用于后台监测设备coredump文件和资源使用情况，并发送告警邮件
"""

import threading
import time
import json
import os
import logging
from datetime import datetime
from .device_utils import get_coredump_files, get_cpu_info, get_memory_info
from .email_utils import send_alert_email, format_alert_email_content

logger = logging.getLogger(__name__)

# 全局监测状态
monitor_tasks = {}  # {device_id: {'enabled': bool, 'thread': Thread, 'last_files': set, 'last_alert_time': dict}}
monitor_lock = threading.Lock()

# 告警配置（从文件读取）
alert_config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'alert_config.json')
alert_config = {
    'smtp_server': 'smtp.example.com',
    'smtp_port': 587,
    'sender_email': '',
    'sender_password': '',
    'use_tls': True,
    'recipients': [],
    'check_interval': 300,  # 默认5分钟检查一次
    'cpu_threshold': 80,  # CPU告警阈值（%）
    'memory_threshold': 80  # 内存告警阈值（%）
}


def load_alert_config():
    """从文件加载告警配置"""
    global alert_config
    try:
        if os.path.exists(alert_config_file):
            with open(alert_config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                alert_config.update(loaded_config)
                logger.info('告警配置加载成功')
        else:
            # 如果文件不存在，创建默认配置
            save_alert_config()
    except Exception as e:
        logger.error(f'加载告警配置失败: {e}')


def save_alert_config():
    """保存告警配置到文件"""
    try:
        with open(alert_config_file, 'w', encoding='utf-8') as f:
            json.dump(alert_config, f, indent=2, ensure_ascii=False)
        logger.info('告警配置保存成功')
        return True
    except Exception as e:
        logger.error(f'保存告警配置失败: {e}')
        return False


def get_alert_config():
    """获取告警配置"""
    return alert_config.copy()


def update_alert_config(new_config):
    """更新告警配置"""
    global alert_config
    # 如果新配置中密码为空或未提供，保留原有密码
    if not new_config.get('sender_password') or new_config.get('sender_password') == '***':
        if 'sender_password' in new_config:
            del new_config['sender_password']  # 删除空密码，保留原有密码
    alert_config.update(new_config)
    return save_alert_config()


def monitor_device_worker(device_id, device_info):
    """
    设备监测工作线程
    
    Args:
        device_id: 设备ID
        device_info: 设备信息字典，包含name, ip, type, user, password等
    """
    last_files = set()
    last_alert_time = {
        'coredump': 0,
        'resource': 0
    }
    alert_cooldown = 300  # 相同告警5分钟内不重复发送
    
    while True:
        with monitor_lock:
            task = monitor_tasks.get(device_id)
            if not task or not task.get('enabled', False):
                logger.info(f'设备 {device_id} 监测已停止')
                break
        
        try:
            # 获取设备类型
            device_type = device_info.get('type', '')
            
            # 获取当前系统资源信息
            cpu_info = get_cpu_info(device_info['ip'], device_info.get('user', 'admin'), 
                                   device_info.get('password', 'tdhx@2017'), device_type=device_type)
            memory_info = get_memory_info(device_info['ip'], device_info.get('user', 'admin'),
                                         device_info.get('password', 'tdhx@2017'), device_type=device_type)
            
            resource_info = {
                'cpu_usage': cpu_info if isinstance(cpu_info, (int, float)) else 0,
                'memory_usage': memory_info.get('usage', 0) if isinstance(memory_info, dict) else 0,
                'memory_total': memory_info.get('total', 0) if isinstance(memory_info, dict) else 0,
                'memory_used': memory_info.get('used', 0) if isinstance(memory_info, dict) else 0,
                'memory_free': memory_info.get('free', 0) if isinstance(memory_info, dict) else 0
            }
            
            # 检查资源使用率告警
            current_time = time.time()
            cpu_usage = resource_info['cpu_usage']
            memory_usage = resource_info['memory_usage']
            
            # 从配置中获取阈值
            cpu_threshold = alert_config.get('cpu_threshold', 80)
            memory_threshold = alert_config.get('memory_threshold', 80)
            
            if (cpu_usage > cpu_threshold or memory_usage > memory_threshold) and \
               (current_time - last_alert_time['resource']) > alert_cooldown:
                # 发送资源告警
                alert_details = {
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory_usage,
                    'memory_total': resource_info['memory_total'],
                    'memory_used': resource_info['memory_used'],
                    'memory_free': resource_info['memory_free'],
                    'resource_info': resource_info,
                    'cpu_threshold': cpu_threshold,
                    'memory_threshold': memory_threshold
                }
                
                content = format_alert_email_content(device_info, 'resource', alert_details)
                threshold_text = f'CPU>{cpu_threshold}%或内存>{memory_threshold}%'
                subject = f'[设备告警] {device_info.get("name", "未知设备")} - 资源使用率超过阈值({threshold_text})'
                
                try:
                    if send_alert_email(alert_config, subject, content, alert_config.get('recipients', [])):
                        last_alert_time['resource'] = current_time
                        logger.info(f'设备 {device_id} 资源告警邮件已发送')
                except Exception as e:
                    logger.error(f'设备 {device_id} 资源告警邮件发送失败: {e}')
            
            # 检查coredump文件
            coredump_files = get_coredump_files(device_info['ip'], device_info.get('user', 'admin'),
                                                device_info.get('password', 'tdhx@2017'), device_type=device_type)
            current_files = {f['name'] for f in coredump_files}
            
            # 检测新文件
            new_files = current_files - last_files
            if new_files and (current_time - last_alert_time['coredump']) > alert_cooldown:
                # 发送coredump告警
                new_file_list = [f for f in coredump_files if f['name'] in new_files]
                alert_details = {
                    'file_count': len(new_files),
                    'files': new_file_list,
                    'resource_info': resource_info
                }
                
                content = format_alert_email_content(device_info, 'coredump', alert_details)
                subject = f'[设备告警] {device_info.get("name", "未知设备")} - 检测到新的Coredump文件'
                
                try:
                    if send_alert_email(alert_config, subject, content, alert_config.get('recipients', [])):
                        last_alert_time['coredump'] = current_time
                        logger.info(f'设备 {device_id} coredump告警邮件已发送')
                except Exception as e:
                    logger.error(f'设备 {device_id} coredump告警邮件发送失败: {e}')
            
            last_files = current_files
            
        except Exception as e:
            logger.error(f'设备 {device_id} 监测出错: {e}')
        
        # 等待检查间隔
        check_interval = alert_config.get('check_interval', 300)
        time.sleep(check_interval)


def start_device_monitoring(device_id, device_info):
    """
    启动设备监测
    
    Args:
        device_id: 设备ID
        device_info: 设备信息字典
    """
    with monitor_lock:
        if device_id in monitor_tasks:
            # 如果已经在监测，先停止
            stop_device_monitoring(device_id)
        
        monitor_tasks[device_id] = {
            'enabled': True,
            'thread': None,
            'last_files': set(),
            'last_alert_time': {}
        }
        
        thread = threading.Thread(
            target=monitor_device_worker,
            args=(device_id, device_info),
            daemon=True
        )
        thread.start()
        
        monitor_tasks[device_id]['thread'] = thread
        logger.info(f'设备 {device_id} 监测已启动')


def stop_device_monitoring(device_id):
    """
    停止设备监测
    
    Args:
        device_id: 设备ID
    """
    with monitor_lock:
        if device_id in monitor_tasks:
            monitor_tasks[device_id]['enabled'] = False
            thread = monitor_tasks[device_id].get('thread')
            if thread and thread.is_alive():
                thread.join(timeout=5)
            del monitor_tasks[device_id]
            logger.info(f'设备 {device_id} 监测已停止')


def is_device_monitoring(device_id):
    """
    检查设备是否正在监测
    
    Args:
        device_id: 设备ID
    
    Returns:
        bool: 是否正在监测
    """
    with monitor_lock:
        task = monitor_tasks.get(device_id)
        return task is not None and task.get('enabled', False)


def get_monitoring_status():
    """
    获取所有设备的监测状态
    
    Returns:
        dict: {device_id: enabled}
    """
    with monitor_lock:
        return {device_id: task.get('enabled', False) 
                for device_id, task in monitor_tasks.items()}


# 初始化时加载配置
load_alert_config()

