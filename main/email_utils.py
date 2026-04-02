#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送工具模块
用于发送设备告警邮件
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime

logger = logging.getLogger(__name__)


def send_alert_email(email_config, subject, content, recipients):
    """
    发送告警邮件
    
    Args:
        email_config: 邮件配置字典，包含：
            - smtp_server: SMTP服务器地址
            - smtp_port: SMTP端口
            - sender_email: 发件人邮箱
            - sender_password: 发件人密码
            - use_tls: 是否使用TLS（默认True）
            - use_ssl: 是否使用SSL（默认False，如果端口是465通常需要SSL）
        subject: 邮件主题
        content: 邮件内容（HTML格式）
        recipients: 收件人列表（可以是字符串或列表）
    
    Returns:
        bool: 发送是否成功
    """
    try:
        # 确保recipients是列表
        if isinstance(recipients, str):
            recipients = [recipients]
        
        # 创建邮件对象
        msg = MIMEMultipart('alternative')
        msg['From'] = Header(email_config['sender_email'], 'utf-8')
        msg['To'] = Header(','.join(recipients), 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        
        # 添加HTML内容
        html_content = MIMEText(content, 'html', 'utf-8')
        msg.attach(html_content)
        
        # 判断使用SSL还是TLS
        use_ssl = email_config.get('use_ssl', False)
        use_tls = email_config.get('use_tls', True)
        smtp_port = email_config['smtp_port']
        
        # 如果端口是465，通常需要使用SSL
        if smtp_port == 465:
            use_ssl = True
            use_tls = False
        
        # 连接SMTP服务器并发送
        if use_ssl:
            # 使用SSL连接
            smtp = smtplib.SMTP_SSL(email_config['smtp_server'], smtp_port, timeout=30)
        else:
            # 使用普通连接，然后可能启用TLS
            smtp = smtplib.SMTP(email_config['smtp_server'], smtp_port, timeout=30)
            smtp.set_debuglevel(0)  # 设置为0关闭调试输出，1开启
            
            # 如果支持TLS，启用它
            if use_tls:
                try:
                    smtp.starttls()
                except smtplib.SMTPException as e:
                    logger.warning(f'启用TLS失败，尝试不使用TLS: {e}')
                    # 某些服务器可能不支持TLS，继续尝试
        
        # 登录
        smtp.login(email_config['sender_email'], email_config['sender_password'])
        
        # 发送邮件
        smtp.sendmail(email_config['sender_email'], recipients, msg.as_string())
        smtp.quit()
        
        logger.info(f'告警邮件发送成功: {subject} -> {recipients}')
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f'SMTP认证失败: {e}')
        raise Exception(f'SMTP认证失败: 请检查邮箱地址和密码（授权码）是否正确。错误详情: {str(e)}')
    except smtplib.SMTPConnectError as e:
        logger.error(f'SMTP连接失败: {e}')
        raise Exception(f'SMTP连接失败: 请检查SMTP服务器地址和端口是否正确。错误详情: {str(e)}')
    except smtplib.SMTPServerDisconnected as e:
        logger.error(f'SMTP服务器断开连接: {e}')
        raise Exception(f'SMTP服务器断开连接: 可能是服务器配置不正确或需要使用SSL连接。错误详情: {str(e)}')
    except smtplib.SMTPException as e:
        logger.error(f'SMTP错误: {e}')
        raise Exception(f'SMTP错误: {str(e)}')
    except Exception as e:
        logger.error(f'发送告警邮件失败: {e}')
        raise Exception(f'发送邮件失败: {str(e)}')


def format_alert_email_content(device_info, alert_type, alert_details):
    """
    格式化告警邮件内容
    
    Args:
        device_info: 设备信息字典，包含name, ip, type等
        alert_type: 告警类型（'coredump' 或 'resource'）
        alert_details: 告警详情字典
    
    Returns:
        str: HTML格式的邮件内容
    """
    # 格式化时间为中文格式
    current_time = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
    
    # 设备类型中文映射
    device_type_map = {
        'security_device': '安全设备',
        'ic_firewall': '工控防火墙',
        'ic_audit': '工控审计',
        'ids': 'IDS',
        'other': '其他'
    }
    device_type = device_type_map.get(device_info.get('type', ''), device_info.get('type', '未知'))
    
    if alert_type == 'coredump':
        title = 'Coredump文件告警'
        description = f'检测到设备 {device_info.get("name", "未知")} 的 /data/coredump 目录下存在新的coredump文件。'
        details_html = f"""
        <h3>告警详情</h3>
        <ul>
            <li><strong>设备名称:</strong> {device_info.get('name', '未知')}</li>
            <li><strong>设备IP:</strong> {device_info.get('ip', '未知')}</li>
            <li><strong>设备类型:</strong> {device_type}</li>
            <li><strong>文件数量:</strong> {alert_details.get('file_count', 0)}</li>
            <li><strong>文件列表:</strong></li>
        </ul>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
            <tr style="background-color: #f0f0f0;">
                <th>文件名</th>
                <th>大小</th>
                <th>修改时间</th>
            </tr>
        """
        for file_info in alert_details.get('files', []):
            # 格式化文件大小，确保有单位
            size_str = file_info.get('size_str', '0')
            if size_str and not any(unit in size_str for unit in ['B', 'K', 'M', 'G', 'T']):
                # 如果没有单位，添加B
                size_str = f"{size_str} B"
            
            # 格式化时间（如果是英文格式，尝试转换）
            mtime = file_info.get('mtime', '')
            # 如果时间格式是 "Nov 19 18:19" 这样的，保持原样（已经是可读格式）
            # 如果是其他格式，可以进一步处理
            
            details_html += f"""
            <tr>
                <td>{file_info.get('name', '')}</td>
                <td>{size_str}</td>
                <td>{mtime}</td>
            </tr>
            """
        details_html += "</table>"
        
    elif alert_type == 'resource':
        title = '资源使用率告警'
        cpu_threshold = alert_details.get('cpu_threshold', 80)
        memory_threshold = alert_details.get('memory_threshold', 80)
        cpu_usage = alert_details.get('cpu_usage', 0)
        memory_usage = alert_details.get('memory_usage', 0)
        description = f'设备 {device_info.get("name", "未知")} 的CPU或内存使用率超过阈值（CPU>{cpu_threshold}% 或 内存>{memory_threshold}%）。'
        details_html = f"""
        <h3>告警详情</h3>
        <ul>
            <li><strong>设备名称:</strong> {device_info.get('name', '未知')}</li>
            <li><strong>设备IP:</strong> {device_info.get('ip', '未知')}</li>
            <li><strong>设备类型:</strong> {device_type}</li>
            <li><strong>CPU使用率:</strong> <span style="color: {'red' if cpu_usage > cpu_threshold else 'black'}">{cpu_usage:.2f}%</span> (阈值: {cpu_threshold}%)</li>
            <li><strong>内存使用率:</strong> <span style="color: {'red' if memory_usage > memory_threshold else 'black'}">{memory_usage:.2f}%</span> (阈值: {memory_threshold}%)</li>
            <li><strong>内存详情:</strong></li>
            <ul>
                <li>总内存: {alert_details.get('memory_total', 0)} MB</li>
                <li>已用内存: {alert_details.get('memory_used', 0)} MB</li>
                <li>可用内存: {alert_details.get('memory_free', 0)} MB</li>
            </ul>
        </ul>
        """
    else:
        title = '设备告警'
        description = '设备出现异常情况。'
        details_html = '<p>未知告警类型</p>'
    
    # 添加系统资源信息
    resource_info = alert_details.get('resource_info', {})
    if resource_info:
        details_html += f"""
        <h3>当前系统资源状态</h3>
        <ul>
            <li><strong>CPU使用率:</strong> {resource_info.get('cpu_usage', 0):.2f}%</li>
            <li><strong>内存使用率:</strong> {resource_info.get('memory_usage', 0):.2f}%</li>
            <li><strong>内存详情:</strong> 总{resource_info.get('memory_total', 0)}MB / 已用{resource_info.get('memory_used', 0)}MB / 可用{resource_info.get('memory_free', 0)}MB</li>
        </ul>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f44336; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
            .footer {{ background-color: #e0e0e0; padding: 10px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px; }}
            table {{ width: 100%; margin-top: 10px; }}
            th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>{title}</h2>
            </div>
            <div class="content">
                <p><strong>告警时间:</strong> {current_time}</p>
                <p>{description}</p>
                {details_html}
            </div>
            <div class="footer">
                <p>此邮件由测试设备监控系统自动发送，请勿回复。</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

