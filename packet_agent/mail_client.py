#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件客户端测试脚本
用于发送测试邮件，验证防火墙协议解析和病毒检测能力

使用示例:
    # 发送测试邮件
    python mail_client.py send --subject "测试邮件" --to "receiver@test.local"

    # 发送带附件的邮件
    python mail_client.py send --subject "测试带附件" --to "receiver@test.local" --attachment "test.txt"

    # 查询邮件列表
    python mail_client.py list --limit 10

    # 创建 EICAR 病毒测试文件
    python mail_client.py create-eicar

    # 发送病毒测试邮件
    python mail_client.py send --subject "病毒测试" --to "receiver@test.local" --attachment "eicar_test.txt"
"""

import argparse
import smtplib
import os
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

try:
    import requests
except ImportError:
    print("请安装 requests: pip install requests")
    sys.exit(1)

# 默认配置
DEFAULT_SMTP_SERVER = '10.40.30.34'
DEFAULT_SMTP_PORT = 25
DEFAULT_SENDER = 'sender@test.local'
DEFAULT_RECEIVER = 'receiver@test.local'
DEFAULT_MAIL_API = f'http://{DEFAULT_SMTP_SERVER}:5000/api/mail/recent'


def send_email(smtp_server, smtp_port, sender, receiver, subject, body, attachment_path=None):
    """发送测试邮件"""
    print(f'正在连接到 SMTP 服务器：{smtp_server}:{smtp_port}...')

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if attachment_path:
        if not os.path.exists(attachment_path):
            print(f'错误：附件文件不存在：{attachment_path}')
            return False

        print(f'正在添加附件：{attachment_path}')
        try:
            with open(attachment_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={os.path.basename(attachment_path)}'
                )
                msg.attach(part)
            print('附件添加成功')
        except Exception as e:
            print(f'添加附件失败：{e}')
            return False

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print('正在发送邮件...')
            server.sendmail(sender, [receiver], msg.as_string())
        print('[OK] 邮件发送成功')
        return True
    except smtplib.SMTPException as e:
        print(f'[ERROR] SMTP 错误：{e}')
        return False
    except Exception as e:
        print(f'[ERROR] 发送失败：{e}')
        return False


def get_recent_mails(mail_api, limit=10):
    """获取最近邮件列表"""
    try:
        print(f'正在获取邮件列表：{mail_api}')
        resp = requests.get(mail_api, params={'limit': limit}, timeout=10)
        resp.raise_for_status()

        data = resp.json()
        if data.get('success'):
            mails = data.get('mails', [])
            print(f'[OK] 获取到 {len(mails)} 封邮件')
            return mails
        else:
            print(f'[ERROR] API 返回错误：{data.get("error", "未知错误")}')
            return []
    except requests.exceptions.RequestException as e:
        print(f'[ERROR] 请求失败：{e}')
        return []


def print_mail_list(mails):
    """打印邮件列表"""
    if not mails:
        print('暂无邮件')
        return

    print(f'\n最近邮件列表 (共{len(mails)}封):')
    print('-' * 80)
    for i, mail in enumerate(mails, 1):
        print(f"{i}. 主题：{mail.get('subject', '无主题')}")
        print(f"   来自：{mail.get('mail_from', '未知')}")
        print(f"   收件人：{mail.get('mail_to', '未知')}")
        print(f"   时间：{mail.get('received_at', '未知')}")
        print(f"   附件：{'有' if mail.get('has_attachment') else '无'}")
        print('-' * 80)


def create_eicar_test():
    """创建 EICAR 反病毒测试文件"""
    eicar_content = 'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
    filename = 'eicar_test.txt'

    try:
        with open(filename, 'w') as f:
            f.write(eicar_content)
        print(f'[OK] EICAR 测试文件已创建：{filename}')
        print(f'  文件大小：{len(eicar_content)} 字节')
        print(f'  MD5: 44D88612FEA8A8F36DE82E1278ABB02F (EICAR 标准测试文件)')
        return filename
    except Exception as e:
        print(f'[ERROR] 创建失败：{e}')
        return None


def main():
    parser = argparse.ArgumentParser(
        description='邮件客户端测试脚本 - 用于测试防火墙协议解析和病毒检测能力',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s send -s "测试" -t "receiver@test.local"
  %(prog)s send -s "病毒测试" -t "receiver@test.local" -a "eicar_test.txt"
  %(prog)s list -n 10
  %(prog)s create-eicar
        '''
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # send 命令
    send_parser = subparsers.add_parser('send', help='发送测试邮件')
    send_parser.add_argument('-s', '--server', default=DEFAULT_SMTP_SERVER,
                            help=f'SMTP 服务器地址 (默认：{DEFAULT_SMTP_SERVER})')
    send_parser.add_argument('-p', '--port', type=int, default=DEFAULT_SMTP_PORT,
                            help=f'SMTP 端口 (默认：{DEFAULT_SMTP_PORT})')
    send_parser.add_argument('-f', '--from', dest='sender', default=DEFAULT_SENDER,
                            help=f'发件人邮箱 (默认：{DEFAULT_SENDER})')
    send_parser.add_argument('-t', '--to', dest='receiver', default=DEFAULT_RECEIVER,
                            help=f'收件人邮箱 (默认：{DEFAULT_RECEIVER})')
    send_parser.add_argument('-S', '--subject', default='测试邮件',
                            help='邮件主题 (默认：测试邮件)')
    send_parser.add_argument('-b', '--body', default='这是一封测试邮件',
                            help='邮件正文 (默认：这是一封测试邮件)')
    send_parser.add_argument('-a', '--attachment', help='附件文件路径')

    # list 命令
    list_parser = subparsers.add_parser('list', help='查询邮件列表')
    list_parser.add_argument('--api', default=DEFAULT_MAIL_API,
                            help=f'邮件 API 地址 (默认：{DEFAULT_MAIL_API})')
    list_parser.add_argument('-n', '--limit', type=int, default=10,
                            help='返回邮件数量限制 (默认：10)')

    # create-eicar 命令
    eicar_parser = subparsers.add_parser('create-eicar', help='创建 EICAR 病毒测试文件')

    args = parser.parse_args()

    if args.command == 'send':
        success = send_email(
            args.server,
            args.port,
            args.sender,
            args.receiver,
            args.subject,
            args.body,
            args.attachment
        )
        sys.exit(0 if success else 1)

    elif args.command == 'list':
        mails = get_recent_mails(args.api, args.limit)
        print_mail_list(mails)

    elif args.command == 'create-eicar':
        create_eicar_test()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
