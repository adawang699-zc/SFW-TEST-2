from django.urls import path
from . import views_with_cache

app_name = 'main'

urlpatterns = [
    path('', views_with_cache.home, name='home'),
    path('firewall/', views_with_cache.firewall_policy, name='firewall_policy'),
    path('packet-send/', views_with_cache.packet_send, name='packet_send'),
    path('api/get_cookie/', views_with_cache.get_cookie, name='get_cookie'),
    path('api/send_custom_service/', views_with_cache.send_custom_service, name='send_custom_service'),
    path('api/send_custom_service_batch/', views_with_cache.send_custom_service_batch, name='send_custom_service_batch'),
    path('api/send_service_group/', views_with_cache.send_service_group, name='send_service_group'),
    path('api/send_l2_custom_service/', views_with_cache.send_l2_custom_service, name='send_l2_custom_service'),
    # 对象管理 - 服务测试用例
    path('api/service_test_case/list/', views_with_cache.service_test_case_list, name='service_test_case_list'),
    path('api/service_test_case/add/', views_with_cache.service_test_case_add, name='service_test_case_add'),
    path('api/service_test_case/update/', views_with_cache.service_test_case_update, name='service_test_case_update'),
    path('api/service_test_case/apply/', views_with_cache.service_test_case_apply, name='service_test_case_apply'),
    path('api/service_test_case/delete/', views_with_cache.service_test_case_delete, name='service_test_case_delete'),
    path('api/service_test_case/test/', views_with_cache.service_test_case_test, name='service_test_case_test'),
    path('api/service_test_case/batch_test/', views_with_cache.service_test_case_batch_test, name='service_test_case_batch_test'),
    path('api/service_test_case/create_defaults/', views_with_cache.service_test_case_create_defaults, name='service_test_case_create_defaults'),
    path('api/send_addrlist/', views_with_cache.send_addrlist, name='send_addrlist'),
    path('api/send_addrgroup/', views_with_cache.send_addrgroup, name='send_addrgroup'),
    path('api/send_l2_addrlist/', views_with_cache.send_l2_addrlist, name='send_l2_addrlist'),
    path('api/send_l2_addrgroup/', views_with_cache.send_l2_addrgroup, name='send_l2_addrgroup'),
    path('api/send_packet_filter/', views_with_cache.send_packet_filter, name='send_packet_filter'),
    path('api/send_deep_check/', views_with_cache.send_deep_check, name='send_deep_check'),
    path('api/send_ipsecvpn/', views_with_cache.send_ipsecvpn, name='send_ipsecvpn'),
    path('api/send_bridge_info/', views_with_cache.send_bridge_info, name='send_bridge_info'),
    path('api/get_interfaces/', views_with_cache.get_interfaces, name='get_interfaces'),
    path('api/send_packet/', views_with_cache.send_packet, name='send_packet'),
    # 代理程序相关API
    path('api/agent/interfaces/', views_with_cache.get_agent_interfaces, name='get_agent_interfaces'),
    path('api/agent/send_packet/', views_with_cache.send_packet_via_agent, name='send_packet_via_agent'),
    path('api/agent/statistics/', views_with_cache.get_agent_statistics, name='get_agent_statistics'),
    path('api/agent/stop_sending/', views_with_cache.stop_agent_sending, name='stop_agent_sending'),
    # 端口扫描
    path('port-scan/', views_with_cache.port_scan, name='port_scan'),
    path('api/port_scan/', views_with_cache.port_scan_api, name='port_scan_api'),
    path('api/port_scan/progress/', views_with_cache.port_scan_progress, name='port_scan_progress'),
    path('api/port_scan/stop/', views_with_cache.port_scan_stop, name='port_scan_stop'),
    # DHCP客户端
    path('dhcp-client/', views_with_cache.dhcp_client, name='dhcp_client'),
    # 服务下发
    path('service-deploy/', views_with_cache.service_deploy, name='service_deploy'),
    # 工控协议
    path('industrial-protocol/', views_with_cache.industrial_protocol, name='industrial_protocol'),
    # 知识库管理
    path('knowledge-base/', views_with_cache.knowledge_base, name='knowledge_base'),
    path('api/knowledge/create/', views_with_cache.knowledge_create, name='knowledge_create'),
    path('api/knowledge/upgrade/', views_with_cache.knowledge_upgrade, name='knowledge_upgrade'),
    path('api/knowledge/templates/', views_with_cache.knowledge_templates_list, name='knowledge_templates_list'),
    path('api/knowledge/templates/save/', views_with_cache.knowledge_templates_save, name='knowledge_templates_save'),
    path('api/knowledge/templates/delete/', views_with_cache.knowledge_templates_delete, name='knowledge_templates_delete'),
    path('api/knowledge/templates/<str:name>/', views_with_cache.knowledge_templates_get, name='knowledge_templates_get'),
    # 漏洞库
    path('api/knowledge/vul/create/', views_with_cache.vul_create, name='vul_create'),
    path('api/knowledge/vul/upgrade/', views_with_cache.vul_upgrade, name='vul_upgrade'),
    path('api/knowledge/vul/templates/', views_with_cache.vul_templates_list, name='vul_templates_list'),
    path('api/knowledge/vul/templates/save/', views_with_cache.vul_templates_save, name='vul_templates_save'),
    path('api/knowledge/vul/templates/delete/', views_with_cache.vul_templates_delete, name='vul_templates_delete'),
    path('api/knowledge/vul/templates/<str:name>/', views_with_cache.vul_templates_get, name='vul_templates_get'),
    # 病毒库
    path('api/knowledge/virus/create/', views_with_cache.virus_create, name='virus_create'),
    path('api/knowledge/virus/upgrade/', views_with_cache.virus_upgrade, name='virus_upgrade'),
    path('api/knowledge/virus/templates/', views_with_cache.virus_templates_list, name='virus_templates_list'),
    path('api/knowledge/virus/templates/save/', views_with_cache.virus_templates_save, name='virus_templates_save'),
    path('api/knowledge/virus/templates/delete/', views_with_cache.virus_templates_delete, name='virus_templates_delete'),
    path('api/knowledge/virus/templates/<str:name>/', views_with_cache.virus_templates_get, name='virus_templates_get'),
    # 授权管理
    path('license-management/', views_with_cache.license_management, name='license_management'),
    path('api/services/listener/', views_with_cache.service_listener_control, name='service_listener_control'),
    path('api/services/client/', views_with_cache.service_client_control, name='service_client_control'),
    path('api/services/local-mail/start/', views_with_cache.start_local_mail_service, name='start_local_mail_service'),
    
    # 授权管理API
    path('api/license/knowledge/generate/', views_with_cache.generate_knowledge_license, name='generate_knowledge_license'),
    path('api/license/knowledge/decrypt/', views_with_cache.decrypt_knowledge_license, name='decrypt_knowledge_license'),
    path('api/license/device/test_connection/', views_with_cache.test_device_license_connection, name='test_device_license_connection'),
    path('api/license/device/generate/', views_with_cache.generate_device_license, name='generate_device_license'),
    path('api/license/device/download/', views_with_cache.download_device_license, name='download_device_license'),
    path('api/services/status/', views_with_cache.service_status_api, name='service_status_api'),
    path('api/services/logs/', views_with_cache.service_logs_api, name='service_logs_api'),
    # 测试设备
    path('device-monitor/', views_with_cache.device_monitor, name='device_monitor'),
    path('api/device/list/', views_with_cache.device_list, name='device_list'),
    path('api/device/add/', views_with_cache.device_add, name='device_add'),
    path('api/device/update/', views_with_cache.device_update, name='device_update'),
    path('api/device/delete/', views_with_cache.device_delete, name='device_delete'),
    path('api/device/test_connection/', views_with_cache.device_test_connection, name='device_test_connection'),
    path('api/device/monitor_data/', views_with_cache.device_monitor_data, name='device_monitor_data'),
    path('api/device/disk_data/', views_with_cache.device_disk_data, name='device_disk_data'),
    path('api/device/coredump/', views_with_cache.device_coredump_list, name='device_coredump_list'),
    path('api/device/execute/', views_with_cache.device_execute_command, name='device_execute_command'),
    # 设备监测和告警
    path('api/device/monitoring/toggle/', views_with_cache.device_monitoring_toggle, name='device_monitoring_toggle'),
    path('api/device/monitoring/status/', views_with_cache.device_monitoring_status, name='device_monitoring_status'),
    path('api/device/alert_config/', views_with_cache.device_alert_config, name='device_alert_config'),
    path('api/device/alert_config/test/', views_with_cache.device_alert_config_test, name='device_alert_config_test'),
    path('api/device/alert_status/', views_with_cache.device_alert_status, name='device_alert_status'),
    path('api/device/alert_ignore/', views_with_cache.device_alert_ignore, name='device_alert_ignore'),
    # 测试环境
    path('test-env/', views_with_cache.test_env, name='test_env'),
    path('api/test_env/list/', views_with_cache.test_env_list, name='test_env_list'),
    path('api/test_env/add/', views_with_cache.test_env_add, name='test_env_add'),
    path('api/test_env/update/', views_with_cache.test_env_update, name='test_env_update'),
    path('api/test_env/delete/', views_with_cache.test_env_delete, name='test_env_delete'),
    path('api/test_env/test_connection/', views_with_cache.test_env_test_connection, name='test_env_test_connection'),
    path('api/test_env/agent_control/', views_with_cache.test_env_agent_control, name='test_env_agent_control'),
    path('api/test_env/agent_status/', views_with_cache.test_env_agent_status, name='test_env_agent_status'),
    path('api/test_env/execute_command/', views_with_cache.test_env_execute_command, name='test_env_execute_command'),
    path('api/test_env/batch_agent_control/', views_with_cache.test_env_batch_agent_control, name='test_env_batch_agent_control'),
    path('api/test_env/agent_version_check/', views_with_cache.test_env_agent_version_check, name='test_env_agent_version_check'),
    # syslog日志接收
    path('syslog-receiver/', views_with_cache.syslog_receiver, name='syslog_receiver'),
    path('api/syslog/control/', views_with_cache.syslog_control, name='syslog_control'),
    path('api/syslog/status/', views_with_cache.syslog_status, name='syslog_status'),
    path('api/syslog/logs/', views_with_cache.syslog_logs, name='syslog_logs'),
    path('api/syslog/clear/', views_with_cache.syslog_clear, name='syslog_clear'),
    path('api/syslog/filter/', views_with_cache.syslog_filter, name='syslog_filter'),
    # Agent exe下载
    path('download/agent-exe/', views_with_cache.download_agent_exe, name='download_agent_exe'),
    # SNMP
    path('snmp/', views_with_cache.snmp, name='snmp'),
    path('api/snmp/get/', views_with_cache.snmp_get_api, name='snmp_get_api'),
    path('api/snmp/trap/control/', views_with_cache.snmp_trap_control, name='snmp_trap_control'),
    path('api/snmp/trap/status/', views_with_cache.snmp_trap_status, name='snmp_trap_status'),
    path('api/snmp/trap/traps/', views_with_cache.snmp_trap_traps, name='snmp_trap_traps'),
    path('api/snmp/trap/clear/', views_with_cache.snmp_trap_clear, name='snmp_trap_clear'),
    # 自定义协议
    path('api/get_protocol_files/', views_with_cache.get_protocol_files, name='get_protocol_files'),
    path('api/send_custom_protocol/', views_with_cache.send_custom_protocol, name='send_custom_protocol'),
    # 报文回放
    path('packet-replay/', views_with_cache.packet_replay, name='packet_replay'),
    path('api/packet_replay/connect/', views_with_cache.packet_replay_connect, name='packet_replay_connect'),
    path('api/packet_replay/interfaces/', views_with_cache.packet_replay_interfaces, name='packet_replay_interfaces'),
    path('api/packet_replay/files/', views_with_cache.packet_replay_files, name='packet_replay_files'),
    path('api/packet_replay/start/', views_with_cache.packet_replay_start, name='packet_replay_start'),
    path('api/packet_replay/stop/', views_with_cache.packet_replay_stop, name='packet_replay_stop'),
    path('api/packet_replay/status/', views_with_cache.packet_replay_status, name='packet_replay_status'),
    
    # Agent管理
    path('api/agent/connect/', views_with_cache.agent_connect, name='agent_connect'),
    path('api/agent/disconnect/', views_with_cache.agent_disconnect, name='agent_disconnect'),
    path('api/agent/test_network/', views_with_cache.agent_test_network, name='agent_test_network'),
    path('api/agent/upload/', views_with_cache.agent_upload, name='agent_upload'),
    path('api/agent/check_file/', views_with_cache.agent_check_file, name='agent_check_file'),
    path('api/agent/start/', views_with_cache.agent_start, name='agent_start'),
    path('api/agent/stop/', views_with_cache.agent_stop, name='agent_stop'),
    path('api/agent/status/', views_with_cache.agent_status, name='agent_status'),
    path('api/agent/logs/', views_with_cache.agent_logs, name='agent_logs'),

    # Agent 自动同步 API
    path('api/agent-sync/status/', views_with_cache.agent_sync_status, name='agent_sync_status'),
    path('api/agent-sync/start/', views_with_cache.agent_sync_start, name='agent_sync_start'),
    path('api/agent-sync/stop/', views_with_cache.agent_sync_stop, name='agent_sync_stop'),

    # Agent 自动同步页面
    path('agent-sync/', views_with_cache.agent_sync_page, name='agent_sync_page'),

    # 数据恢复工具
    # 设备预留 API（Redis 分布式锁）
    path('api/device/reserve/', views_with_cache.reserve_device, name='reserve_device'),
    path('api/device/release/', views_with_cache.release_device, name='release_device'),
    path('api/device/status/', views_with_cache.check_device_status, name='check_device_status'),
    path('api/device/extend/', views_with_cache.extend_device_lock, name='extend_device_lock'),

    # 数据恢复工具
    path('restore-data/', views_with_cache.restore_data, name='restore_data'),
]
