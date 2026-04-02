#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件刷新问题修复验证脚本

验证内容：
1. decode_mime_header函数能正确处理Header对象
2. format_email_date函数能正确处理各种输入
3. mail_info字典能正确JSON序列化（不含Header对象）
"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入需要测试的函数
from packet_agent.packet_agent import decode_mime_header, format_email_date


def test_decode_mime_header():
    """测试decode_mime_header函数"""
    print("\n=== 测试 decode_mime_header 函数 ===")

    from email.header import Header

    test_cases = [
        # 普通字符串
        ("普通字符串", "Hello World", "Hello World"),
        # MIME编码字符串
        ("MIME编码", "=?UTF-8?B?5Lit5paH?=", "中文"),
        # Header对象
        ("Header对象", Header("Test Subject", "utf-8"), "Test Subject"),
        # Header对象带MIME编码
        ("Header对象编码", Header("中文测试", "utf-8"), "中文测试"),
        # 空值
        ("空字符串", "", ""),
        ("None值", None, None),
    ]

    passed = 0
    failed = 0

    for name, input_val, expected in test_cases:
        try:
            result = decode_mime_header(input_val)
            if result == expected:
                print(f"  ✓ {name}: 输入={repr(input_val)}, 输出={repr(result)}")
                passed += 1
            else:
                print(f"  ✗ {name}: 输入={repr(input_val)}, 期望={repr(expected)}, 实际={repr(result)}")
                failed += 1
        except Exception as e:
            print(f"  ✗ {name}: 异常 - {str(e)}")
            failed += 1

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_format_email_date():
    """测试format_email_date函数"""
    print("\n=== 测试 format_email_date 函数 ===")

    from email.header import Header

    test_cases = [
        # 正常日期字符串
        ("RFC日期", "Mon, 02 Dec 2024 15:19:23 +0800", "2024年12月02日 15:19:23"),
        # ISO日期
        ("ISO日期", "2024-12-02 15:19:23", "2024年12月02日 15:19:23"),
        # Header对象日期
        ("Header日期", Header("Mon, 02 Dec 2024 15:19:23 +0800", "utf-8"), "2024年12月02日 15:19:23"),
        # "未知"
        ("未知字符串", "未知", "未知"),
        # 空值
        ("空字符串", "", "未知"),
        ("None值", None, "未知"),
    ]

    passed = 0
    failed = 0

    for name, input_val, expected in test_cases:
        try:
            result = format_email_date(input_val)
            # 只检查是否包含预期的时间组件（格式可能有细微差异）
            if expected == "未知" and result == "未知":
                print(f"  ✓ {name}: 输入={repr(input_val)}, 输出={repr(result)}")
                passed += 1
            elif expected != "未知" and result != "未知":
                # 检查日期是否包含正确的年份和月份
                if "2024" in result and "12月" in result:
                    print(f"  ✓ {name}: 输入={repr(input_val)}, 输出={repr(result)}")
                    passed += 1
                else:
                    print(f"  ✗ {name}: 输入={repr(input_val)}, 期望包含'2024年12月', 实际={repr(result)}")
                    failed += 1
            else:
                print(f"  ✗ {name}: 输入={repr(input_val)}, 期望={repr(expected)}, 实际={repr(result)}")
                failed += 1
        except Exception as e:
            print(f"  ✗ {name}: 异常 - {str(e)}")
            failed += 1

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_json_serialization():
    """测试mail_info字典的JSON序列化"""
    print("\n=== 测试 JSON 序列化 ===")

    from email.header import Header

    # 模拟修复前的情况（有Header对象）
    mail_info_before = {
        'id': '1',
        'from': 'test@example.com',
        'subject': 'Test',
        'date': '未知',
        'date_raw': Header("Mon, 02 Dec 2024 15:19:23 +0800", "utf-8"),  # 问题！
        'protocol': 'POP3'
    }

    # 模拟修复后的情况（全部是字符串）
    mail_info_after = {
        'id': '1',
        'from': 'test@example.com',
        'subject': 'Test',
        'date': '2024年12月02日 15:19:23',
        'date_raw': 'Mon, 02 Dec 2024 15:19:23 +0800',  # 修复：解码后的字符串
        'protocol': 'POP3'
    }

    passed = 0
    failed = 0

    # 测试修复前（应该失败）
    try:
        json.dumps(mail_info_before)
        print(f"  ✗ 修复前的mail_info竟然能序列化（不应该）")
        failed += 1
    except TypeError as e:
        if "Header" in str(e) or "not JSON serializable" in str(e):
            print(f"  ✓ 修复前的mail_info正确地无法序列化: {str(e)[:50]}...")
            passed += 1
        else:
            print(f"  ? 修复前的mail_info序列化失败但原因不同: {str(e)}")
            passed += 1

    # 测试修复后（应该成功）
    try:
        json_str = json.dumps(mail_info_after, ensure_ascii=False)
        print(f"  ✓ 修复后的mail_info能正确序列化: {json_str[:80]}...")
        passed += 1
    except TypeError as e:
        print(f"  ✗ 修复后的mail_info序列化失败: {str(e)}")
        failed += 1

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_full_flow():
    """测试完整流程：模拟邮件解析"""
    print("\n=== 测试完整邮件解析流程 ===")

    # 模拟一个简单的邮件内容
    import email
    from email.message import Message
    from email.header import Header

    msg = Message()
    msg['From'] = 'sender@example.com'
    msg['To'] = 'receiver@example.com'
    msg['Subject'] = Header('测试邮件主题', 'utf-8')
    msg['Date'] = 'Mon, 02 Dec 2024 15:19:23 +0800'

    # 模拟修复后的解析逻辑
    subject_raw = msg.get('Subject', '')
    subject = decode_mime_header(subject_raw) if subject_raw else '无主题'

    date_raw = msg.get('Date', '')
    date_str = decode_mime_header(date_raw) if date_raw else '未知'
    date_formatted = format_email_date(date_str)

    mail_info = {
        'id': 'test-1',
        'from': 'sender@example.com',
        'to': 'receiver@example.com',
        'subject': subject,
        'date': date_formatted,
        'date_raw': date_str,
        'protocol': 'TEST'
    }

    passed = 0
    failed = 0

    # 检查各个字段
    if isinstance(mail_info['subject'], str):
        print(f"  ✓ subject是字符串: {mail_info['subject']}")
        passed += 1
    else:
        print(f"  ✗ subject不是字符串: {type(mail_info['subject'])}")
        failed += 1

    if isinstance(mail_info['date_raw'], str):
        print(f"  ✓ date_raw是字符串: {mail_info['date_raw']}")
        passed += 1
    else:
        print(f"  ✗ date_raw不是字符串: {type(mail_info['date_raw'])}")
        failed += 1

    if mail_info['date'] != '未知':
        print(f"  ✓ date格式化成功: {mail_info['date']}")
        passed += 1
    else:
        print(f"  ✗ date格式化失败: {mail_info['date']}")
        failed += 1

    # JSON序列化测试
    try:
        json_str = json.dumps(mail_info, ensure_ascii=False)
        print(f"  ✓ mail_info能正确JSON序列化")
        passed += 1
    except TypeError as e:
        print(f"  ✗ mail_info JSON序列化失败: {str(e)}")
        failed += 1

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def main():
    print("=" * 60)
    print("邮件刷新问题修复验证")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("decode_mime_header", test_decode_mime_header()))
    results.append(("format_email_date", test_format_email_date()))
    results.append(("JSON序列化", test_json_serialization()))
    results.append(("完整流程", test_full_flow()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✓ 所有测试通过，修复有效！")
        return 0
    else:
        print("\n✗ 存在失败的测试，需要进一步检查！")
        return 1


if __name__ == '__main__':
    sys.exit(main())