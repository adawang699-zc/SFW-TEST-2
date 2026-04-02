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
    password = models.CharField(max_length=200, default='', blank=True, verbose_name="密码", help_text="建议使用环境变量 DEVICE_DEFAULT_PASSWORD 统一管理，或在设备实例中单独设置")
    description = models.TextField(blank=True, null=True, verbose_name="描述信息")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "测试设备"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.ip})"