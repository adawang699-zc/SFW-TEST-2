from django.contrib import admin
from .models import S7ServerDBData, TestEnvironment, ServiceTestCase, TestDevice, DeviceAlertStatus, AlertConfig

# Register your models here.

@admin.register(S7ServerDBData)
class S7ServerDBDataAdmin(admin.ModelAdmin):
    list_display = ['server_id', 'db_number', 'updated_at', 'created_at']
    list_filter = ['server_id']
    search_fields = ['server_id', 'db_number']
    readonly_fields = ['updated_at', 'created_at']


@admin.register(TestEnvironment)
class TestEnvironmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'ip', 'type', 'ssh_user', 'ssh_port', 'created_at']
    list_filter = ['type']
    search_fields = ['name', 'ip', 'ssh_user']


@admin.register(ServiceTestCase)
class ServiceTestCaseAdmin(admin.ModelAdmin):
    list_display = ['service_type', 'operation_type', 'name', 'enabled', 'last_test_result', 'last_test_time']
    list_filter = ['service_type', 'operation_type', 'enabled', 'last_test_result']
    search_fields = ['name', 'desc']
    readonly_fields = ['last_test_time']


@admin.register(TestDevice)
class TestDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'ip', 'port', 'user', 'is_long_running', 'created_at']
    list_filter = ['type', 'is_long_running']
    search_fields = ['name', 'ip', 'description']


@admin.register(DeviceAlertStatus)
class DeviceAlertStatusAdmin(admin.ModelAdmin):
    list_display = ['device_id', 'device_name', 'alert_type', 'alert_value', 'has_alert', 'is_ignored', 'alert_time']
    list_filter = ['alert_type', 'has_alert', 'is_ignored']
    search_fields = ['device_id', 'device_name']
    readonly_fields = ['alert_time']


@admin.register(AlertConfig)
class AlertConfigAdmin(admin.ModelAdmin):
    list_display = ['smtp_server', 'smtp_port', 'sender_email', 'check_interval', 'cpu_threshold', 'memory_threshold', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']