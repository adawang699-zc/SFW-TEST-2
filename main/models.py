from django.db import models
import base64

# Create your models here.

class S7ServerDBData(models.Model):
    """S7服务器DB块数据持久化模型"""
    server_id = models.CharField(max_length=100, default='default', verbose_name="服务器ID")
    db_number = models.IntegerField(verbose_name="DB块号")
    data = models.BinaryField(verbose_name="DB数据（二进制）")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "S7服务器DB数据"
        verbose_name_plural = verbose_name
        unique_together = [['server_id', 'db_number']]
        ordering = ['server_id', 'db_number']
        indexes = [
            models.Index(fields=['server_id', 'db_number']),
        ]
    
    def __str__(self):
        return f"S7-{self.server_id}-DB{self.db_number} ({len(self.data)} bytes)"
    
    def get_bytearray(self):
        """将数据库中的二进制数据转换为bytearray"""
        if self.data:
            return bytearray(self.data)
        return bytearray(65536)  # 默认64KB
    
    def set_bytearray(self, data):
        """将bytearray数据保存到数据库"""
        if isinstance(data, bytearray):
            self.data = bytes(data)
        elif isinstance(data, bytes):
            self.data = data
        else:
            self.data = bytes(bytearray(data))

class TestEnvironment(models.Model):
    name = models.CharField(max_length=100, verbose_name="环境名称")
    ip = models.GenericIPAddressField(verbose_name="IP地址")
    type = models.CharField(max_length=20, choices=[('linux', 'Linux'), ('windows', 'Windows')], default='linux', verbose_name="系统类型")
    ssh_user = models.CharField(max_length=100, verbose_name="SSH用户名")
    ssh_password = models.CharField(max_length=200, verbose_name="SSH密码")
    ssh_port = models.IntegerField(default=22, verbose_name="SSH端口")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "测试环境"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.ip})"

class ServiceTestCase(models.Model):
    """服务测试用例模型（自定义服务和二层自定义服务）"""
    SERVICE_TYPES = [
        ('custom_service', '自定义服务'),
        ('l2_custom_service', '二层自定义服务'),
    ]
    
    OPERATION_TYPES = [
        ('add', '新增'),
        ('edit', '编辑'),
        ('delete', '删除'),
    ]
    
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES, verbose_name="服务类型")
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name="操作类型")
    name = models.CharField(max_length=32, verbose_name="名称", help_text="仅支持字母、数字、中文和下划线，最长32字节")
    desc = models.CharField(max_length=64, blank=True, verbose_name="描述", help_text="最长64字节")
    content = models.TextField(verbose_name="内容", help_text="TCP/UDP: 协议类型;端口号;0;0 | ICMP: icmp;0,类型;编码 | 其他: 协议号;0;0;0;")
    
    # 期望结果（用于验证接口返回）
    expected_success = models.BooleanField(default=True, verbose_name="期望成功")
    expected_response = models.TextField(blank=True, verbose_name="期望响应内容", help_text="可选的期望响应内容，用于对比验证")
    expected_status_code = models.IntegerField(default=200, verbose_name="期望状态码")
    
    # 测试结果
    last_test_result = models.BooleanField(null=True, blank=True, verbose_name="最后测试结果")
    last_test_response = models.TextField(blank=True, verbose_name="最后测试响应")
    last_test_status_code = models.IntegerField(null=True, blank=True, verbose_name="最后测试状态码")
    last_test_time = models.DateTimeField(null=True, blank=True, verbose_name="最后测试时间")
    
    # 其他字段
    is_default = models.BooleanField(default=False, verbose_name="是否默认用例", help_text="默认用例不能删除")
    enabled = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "服务测试用例"
        verbose_name_plural = "服务测试用例"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['service_type', 'operation_type']),
            models.Index(fields=['enabled']),
        ]
    
    def __str__(self):
        return f"{self.get_service_type_display()}-{self.get_operation_type_display()}-{self.name}"

class TestDevice(models.Model):
    DEVICE_TYPES = [
        ('security_device', '安全设备'),
        ('ic_firewall', '工控防火墙'),
        ('ic_audit', '工控审计'),
        ('ids', 'IDS'),
        ('other', '其他')
    ]
    name = models.CharField(max_length=100, verbose_name="设备名称")
    type = models.CharField(max_length=30, choices=DEVICE_TYPES, verbose_name="设备类型")
    ip = models.GenericIPAddressField(verbose_name="IP地址")
    port = models.IntegerField(default=22, verbose_name="管理端口")
    user = models.CharField(max_length=100, default='admin', verbose_name="用户名")
    password = models.CharField(max_length=200, default='', blank=True, verbose_name="SSH密码", help_text="SSH登录密码")
    backend_password = models.CharField(max_length=200, default='', blank=True, verbose_name="后台密码", help_text="后台root密码，留空则使用设备类型默认密码")
    is_long_running = models.BooleanField(default=False, verbose_name="长跑环境", help_text="长跑环境默认启动监测")
    description = models.TextField(blank=True, null=True, verbose_name="描述信息")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "测试设备"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.ip})"


class DeviceAlertStatus(models.Model):
    """设备告警状态模型 - 用于跟踪设备告警和忽略状态"""
    ALERT_TYPES = [
        ('cpu', 'CPU告警'),
        ('memory', '内存告警'),
        ('coredump', 'Coredump告警'),
    ]

    device_id = models.IntegerField(verbose_name="设备ID")
    device_name = models.CharField(max_length=100, verbose_name="设备名称")
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, verbose_name="告警类型")
    alert_value = models.FloatField(verbose_name="告警值", help_text="CPU/内存使用率或coredump文件数量")
    has_alert = models.BooleanField(default=True, verbose_name="是否告警")
    is_ignored = models.BooleanField(default=False, verbose_name="是否已忽略")
    ignore_until = models.DateTimeField(null=True, blank=True, verbose_name="忽略截止时间", help_text="忽略后一周内不再提醒")
    alert_time = models.DateTimeField(auto_now_add=True, verbose_name="告警时间")
    last_email_time = models.DateTimeField(null=True, blank=True, verbose_name="最后发送邮件时间")
    email_sent = models.BooleanField(default=False, verbose_name="已发送邮件")

    class Meta:
        verbose_name = "设备告警状态"
        verbose_name_plural = verbose_name
        ordering = ['-alert_time']
        indexes = [
            models.Index(fields=['device_id', 'alert_type']),
            models.Index(fields=['has_alert', 'is_ignored']),
        ]

    def __str__(self):
        return f"{self.device_name} - {self.get_alert_type_display()} ({self.alert_value})"

    def is_ignore_active(self):
        """检查忽略状态是否仍然有效"""
        if not self.is_ignored or not self.ignore_until:
            return False
        from django.utils import timezone
        return timezone.now() < self.ignore_until


class AlertConfig(models.Model):
    """告警配置模型 - 用于存储邮件告警配置"""
    smtp_server = models.CharField(max_length=100, verbose_name="SMTP服务器")
    smtp_port = models.IntegerField(default=587, verbose_name="SMTP端口")
    sender_email = models.CharField(max_length=100, verbose_name="发件人邮箱")
    sender_password = models.CharField(max_length=200, verbose_name="发件人密码")
    use_tls = models.BooleanField(default=True, verbose_name="使用TLS")
    use_ssl = models.BooleanField(default=False, verbose_name="使用SSL")
    recipients = models.TextField(verbose_name="收件人邮箱", help_text="多个邮箱用换行分隔")
    check_interval = models.IntegerField(default=300, verbose_name="监测频率（秒）")
    cpu_threshold = models.IntegerField(default=80, verbose_name="CPU告警阈值（%）")
    memory_threshold = models.IntegerField(default=80, verbose_name="内存告警阈值（%）")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "告警配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"告警配置 - {self.smtp_server}"

    def get_recipients_list(self):
        """获取收件人列表"""
        return [r.strip() for r in self.recipients.split('\n') if r.strip() and '@' in r]