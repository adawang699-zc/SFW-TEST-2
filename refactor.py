#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重构 firewall_policy.html - 删除重复的 JavaScript 函数
用一个通用函数替换所有 send*Requests 函数
"""

with open('templates/firewall_policy.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"原文件行数：{len(lines)}")

# 找到要删除的函数区域
# 从 sendServiceGroupRequests (约 1087 行) 到 simulateRequests 之前

# 找到关键行的索引
def find_line(lines, text, start=0):
    for i in range(start, len(lines)):
        if text in lines[i]:
            return i
    return -1

# 找到各个函数的位置
service_group_idx = find_line(lines, 'function sendServiceGroupRequests')
custom_service_idx = find_line(lines, 'function sendCustomServiceRequests')
simulate_idx = find_line(lines, 'function simulateRequests')
add_log_entry_idx = find_line(lines, 'function addLogEntry')

print(f"sendServiceGroupRequests: 第 {service_group_idx + 1} 行")
print(f"sendCustomServiceRequests: 第 {custom_service_idx + 1} 行")
print(f"simulateRequests: 第 {simulate_idx + 1} 行")
print(f"addLogEntry: 第 {add_log_entry_idx + 1} 行")

# 新的通用 JavaScript 代码
new_js_code = '''    // ========== 通用请求发送函数 ==========
    const API_ENDPOINTS = {
        'custom_service': '/api/send_custom_service/',
        'service_group': '/api/send_service_group/',
        'l2_custom_service': '/api/send_l2_custom_service/',
        'addrlist': '/api/send_addrlist/',
        'addrgroup': '/api/send_addrgroup/',
        'l2_addrlist': '/api/send_l2_addrlist/',
        'l2_addrgroup': '/api/send_l2_addrgroup/',
        'packet_filter': '/api/send_packet_filter/',
        'deep_check': '/api/send_deep_check/',
        'ipsecvpn': '/api/send_ipsecvpn/',
        'custom_protocol': '/api/send_custom_protocol/'
    };

    // 获取表单数据
    function getFormData(type) {
        const maps = {
            'custom_service': ['custom_service_id', 'custom_service_loginuser', 'custom_service_name', 'custom_service_desc', 'custom_service_content'],
            'service_group': ['service_group_id', 'service_group_loginuser', 'service_group_name', 'service_group_desc', 'service_group_member'],
            'l2_custom_service': ['l2_custom_service_id', 'l2_custom_service_loginuser', 'l2_custom_service_name', 'l2_custom_service_desc', 'l2_custom_service_content'],
            'addrlist': ['addrlist_id', 'addrlist_loginuser', 'addrlist_name', 'addrlist_desc', 'addrlist_iptype', 'addrlist_info'],
            'addrgroup': ['addrgroup_id', 'addrgroup_loginuser', 'addrgroup_name', 'addrgroup_desc', 'addrgroup_iptype', 'addrgroup_member'],
            'l2_addrlist': ['l2_addrlist_id', 'l2_addrlist_loginuser', 'l2_addrlist_name', 'l2_addrlist_desc', 'l2_addrlist_info'],
            'l2_addrgroup': ['l2_addrgroup_id', 'l2_addrgroup_loginuser', 'l2_addrgroup_name', 'l2_addrgroup_desc', 'l2_addrgroup_member'],
            'packet_filter': ['packet_filter_id', 'packet_filter_loginuser', 'packet_filter_name', 'packet_filter_desc', 'packet_filter_iptype', 'packet_filter_proto', 'packet_filter_action', 'packet_filter_smacflag', 'packet_filter_saddr', 'packet_filter_sflag', 'packet_filter_sip', 'packet_filter_sp', 'packet_filter_input', 'packet_filter_dmacflag', 'packet_filter_daddr', 'packet_filter_dflag', 'packet_filter_dip', 'packet_filter_dp', 'packet_filter_output', 'packet_filter_timeobj', 'packet_filter_deep_content', 'packet_filter_enable', 'packet_filter_logged'],
            'deep_check': ['deep_check_id', 'deep_check_loginuser', 'deep_check_name', 'deep_check_desc', 'deep_check_iptype', 'deep_check_proto', 'deep_check_action', 'deep_check_smacflag', 'deep_check_saddr', 'deep_check_sflag', 'deep_check_sip', 'deep_check_sp', 'deep_check_input', 'deep_check_dmacflag', 'deep_check_daddr', 'deep_check_dflag', 'deep_check_dip', 'deep_check_dp', 'deep_check_output', 'deep_check_timeobj', 'deep_check_deep_content', 'deep_check_enable', 'deep_check_logged'],
            'ipsecvpn': ['ipsecvpn_id', 'ipsecvpn_name', 'ipsecvpn_type', 'ipsecvpn_status', 'ipsecvpn_version', 'ipsecvpn_protocol', 'ipsecvpn_interface', 'ipsecvpn_remote_gateway', 'ipsecvpn_auth_method', 'ipsecvpn_local_cert', 'ipsecvpn_negotiation_mode', 'ipsecvpn_my_identifier', 'ipsecvpn_my_identifier_info', 'ipsecvpn_peer_identifier', 'ipsecvpn_peer_identifier_info', 'ipsecvpn_pre_shared_key', 'ipsecvpn_p1_encryption_alg', 'ipsecvpn_p1_hash_alg', 'ipsecvpn_p1_dh_group', 'ipsecvpn_p1_life_time', 'ipsecvpn_mode', 'ipsecvpn_local_net', 'ipsecvpn_remote_net', 'ipsecvpn_p2_protocol', 'ipsecvpn_p2_encryption_alg', 'ipsecvpn_p2_hash_alg', 'ipsecvpn_pfs_key_group', 'ipsecvpn_p2_lifetime', 'ipsecvpn_ca'],
            'custom_protocol': ['custom_protocol_loginuser', 'custom_protocol_file']
        };
        const ids = maps[type] || [];
        const data = {};
        const intFields = ['iptype', 'action', 'smacflag', 'sflag', 'sp', 'dmacflag', 'dflag', 'dp', 'timeobj', 'enable', 'logged', 'type', 'status', 'version', 'protocol', 'p1_dh_group', 'pfs_key_group'];
        ids.forEach((id, idx) => {
            const el = document.getElementById(id);
            if (el) {
                let key = id.replace(/^(custom_service|service_group|l2_custom_service|addrlist|addrgroup|l2_addrlist|l2_addrgroup|packet_filter|deep_check|ipsecvpn|custom_protocol)_/, '');
                if (key === 'iptype') key = 'iptype';
                if (intFields.includes(key) || (idx > 0 && ids[idx-1].includes('type'))) {
                    data[key] = parseInt(el.value) || 0;
                } else {
                    data[key] = el.value;
                }
            }
        });
        return data;
    }

    // 发送请求（带并发控制）
    function sendRequests(ip, type, count, cookie) {
        const url = API_ENDPOINTS[type];
        if (!url) {
            addLogEntry(`未知请求类型：${type}`, 'danger');
            return;
        }
        addLogEntry(`准备发送 ${count} 个 ${type.toUpperCase()} 请求到 ${ip}`, 'info');
        let successCount = 0, failureCount = 0, completedCount = 0, currentIndex = 0, activeRequests = 0;
        const startTimestamp = new Date().toLocaleTimeString();
        addLogEntry(`[${startTimestamp}] 开始发送 ${count} 个 ${type.toUpperCase()} 请求`, 'primary');

        function sendNext() {
            while (currentIndex < count && activeRequests < 5) {
                const reqIdx = currentIndex + 1;
                activeRequests++;
                currentIndex++;
                let data = getFormData(type);
                if (count > 1 && data.name) data.name = data.name + "_" + reqIdx;
                if (count > 1 && type === 'custom_service' && data.content) {
                    const p = data.content.split(";");
                    if (p.length >= 2) data.content = p[0] + ";" + (parseInt(p[1]) + reqIdx - 1) + ";" + (p[2]||"0") + ";" + (p[3]||"0");
                }
                const ts = new Date().toLocaleTimeString();
                const nameDisp = data.name ? ` (${data.name})` : '';
                addLogEntry(`[${ts}] 正在发送请求 #${reqIdx}/${count}${nameDisp}...`, 'info');
                fetch(url, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken')},
                    body: JSON.stringify({ip_address: ip, cookie: cookie, request_data: data})
                })
                .then(r => r.json())
                .then(d => {
                    completedCount++; activeRequests--;
                    const t = new Date().toLocaleTimeString();
                    if (d.success) {
                        successCount++;
                        addLogEntry(`[${t}] 请求 #${reqIdx} 成功${nameDisp}`, 'success');
                        if (d.response) addLogEntry(formatResponse(d.response), 'info');
                    } else {
                        failureCount++;
                        addLogEntry(`[${t}] 请求 #${reqIdx} 失败${nameDisp}: ${d.error}`, 'danger');
                    }
                    addLogEntry(`进度：${completedCount}/${count} (成功:${successCount}, 失败:${failureCount})`, 'info');
                    if (completedCount === count) {
                        const et = new Date().toLocaleTimeString();
                        addLogEntry(`[${et}] 所有请求已完成`, 'success');
                        addLogEntry(`总计：${count} 个请求，成功:${successCount} 个，失败:${failureCount} 个`, 'info');
                    } else if (currentIndex < count) sendNext();
                })
                .catch(e => {
                    completedCount++; activeRequests--; failureCount++;
                    const t = new Date().toLocaleTimeString();
                    addLogEntry(`[${t}] 请求 #${reqIdx} 出错：${e.message}`, 'danger');
                    addLogEntry(`进度：${completedCount}/${count} (成功:${successCount}, 失败:${failureCount})`, 'info');
                    if (completedCount === count) {
                        const et = new Date().toLocaleTimeString();
                        addLogEntry(`[${et}] 所有请求已完成`, 'success');
                        addLogEntry(`总计：${count} 个请求，成功:${successCount} 个，失败:${failureCount} 个`, 'info');
                    } else if (currentIndex < count) sendNext();
                });
            }
        }
        sendNext();
    }

    // 简化的 simulateRequests 函数
    function simulateRequests(ip, type, count, cookie) {
        sendRequests(ip, type, count, cookie);
    }

'''

# 找到要保留的部分
# 1. 文件开始到 sendButton 点击事件处理结束 (约 886 行)
# 2. addLogEntry 及之后的辅助函数

# 创建新文件
# 第一部分：从头到 sendButton 事件监听器结束
part1_end = find_line(lines, '// 模拟发送请求')
if part1_end == -1:
    part1_end = 875

# 第二部分：addLogEntry 函数开始
part2_start = add_log_entry_idx

# 新文件内容
new_lines = lines[:part1_end]
new_lines.append('\n')
new_lines.append(new_js_code)
new_lines.append('\n')
new_lines.extend(lines[part2_start:])

with open('templates/firewall_policy.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"新文件行数：{len(new_lines)}")
print(f"减少行数：{len(lines) - len(new_lines)}")
EOF