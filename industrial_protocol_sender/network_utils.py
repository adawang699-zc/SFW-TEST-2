"""
网络工具函数 - 处理 Windows 网卡名称问题
使用 psutil 获取友好的网卡名称
"""
import platform
import sys

def get_windows_interfaces():
    """获取 Windows 系统上的网卡列表（友好名称）- 优化版本，快速获取"""
    interfaces = []
    interface_map = {}  # 友好名称 -> scapy 接口名称的映射
    
    if platform.system() != 'Windows':
        return interfaces
    
    try:
        from scapy.all import get_if_list
        # 获取 scapy 识别的网卡列表（通常是 GUID 格式）
        if_list = get_if_list()
    except Exception:
        if_list = []
    
    # 使用 psutil 获取友好的网卡名称（快速方法）
    try:
        import psutil
        # 获取所有网络接口（这个操作很快）
        net_if_addrs = psutil.net_if_addrs()
        
        # 先收集所有友好名称（不进行 MAC 匹配，这样更快）
        friendly_names = []
        for friendly_name, addrs in net_if_addrs.items():
            # 跳过虚拟网卡和回环接口
            if 'Loopback' in friendly_name or '本地连接*' in friendly_name or '\\Device\\' in friendly_name:
                continue
            
            # 快速检查是否有 MAC 地址
            has_mac = False
            for addr in addrs:
                try:
                    if hasattr(addr, 'family'):
                        if addr.family == psutil.AF_LINK:
                            mac = addr.address
                            if mac and mac != "00:00:00:00:00:00":
                                has_mac = True
                                break
                    elif hasattr(addr, 'familyname'):
                        if addr.familyname == 'AF_LINK':
                            mac = addr.address
                            if mac and mac != "00:00:00:00:00:00":
                                has_mac = True
                                break
                except Exception:
                    continue
            
            if has_mac:
                friendly_names.append(friendly_name)
        
        # 快速匹配：只对前几个网卡进行详细匹配，其他的使用名称匹配
        for friendly_name in friendly_names[:10]:  # 最多处理前10个
            scapy_iface = None
            
            # 方法1: 通过 MAC 地址快速匹配（只尝试前几个 scapy 接口）
            try:
                import psutil
                net_addrs = psutil.net_if_addrs()
                addrs = net_addrs.get(friendly_name, [])
                mac = None
                for addr in addrs:
                    if hasattr(addr, 'family') and addr.family == psutil.AF_LINK:
                        mac = addr.address
                        break
                
                if mac:
                    # 只检查前20个 scapy 接口（通常不会有很多）
                    for iface in if_list[:20]:
                        try:
                            from scapy.all import get_if_hwaddr
                            iface_mac = get_if_hwaddr(iface)
                            if iface_mac and iface_mac.upper() == mac.upper():
                                scapy_iface = iface
                                break
                        except Exception:
                            continue
            except Exception:
                pass
            
            # 方法2: 如果 MAC 匹配失败，使用名称匹配（快速）
            if not scapy_iface:
                friendly_lower = friendly_name.lower()
                for iface in if_list[:20]:  # 只检查前20个
                    iface_lower = iface.lower()
                    if friendly_lower in iface_lower or iface_lower in friendly_lower:
                        scapy_iface = iface
                        break
            
            # 添加友好名称到列表
            if friendly_name not in interfaces:
                interfaces.append(friendly_name)
                if scapy_iface:
                    interface_map[friendly_name] = scapy_iface
                else:
                    # 如果找不到匹配的，先使用友好名称本身
                    interface_map[friendly_name] = friendly_name
        
        # 对于剩余的网卡，直接添加（不进行详细匹配，加快速度）
        for friendly_name in friendly_names[10:]:
            if friendly_name not in interfaces:
                interfaces.append(friendly_name)
                interface_map[friendly_name] = friendly_name
        
    except ImportError:
        # 如果 psutil 不可用，回退到 wmic 方法
        try:
            import subprocess
            # 使用 wmic 获取网卡信息
            wmic_cmd = 'wmic path win32_networkadapter get Name,GUID /format:csv'
            wmic_result = subprocess.run(
                wmic_cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='replace',
                timeout=10
            )
            
            if wmic_result.returncode == 0 and wmic_result.stdout:
                lines = wmic_result.stdout.strip().split('\n')
                wmic_data = {}
                for line in lines:
                    if not line.strip() or line.startswith('Node') or ',' not in line:
                        continue
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 3:
                        wmic_name = parts[1].strip()
                        wmic_guid = parts[2].strip()
                        if wmic_name and wmic_guid and wmic_name != 'Name':
                            guid_upper = wmic_guid.replace('{', '').replace('}', '').upper()
                            wmic_data[guid_upper] = wmic_name
                
                # 使用 wmic 数据
                for guid_key, friendly_name in wmic_data.items():
                    if friendly_name not in interfaces:
                        interfaces.append(friendly_name)
                        # 查找对应的 scapy 接口
                        scapy_iface = None
                        for iface in if_list:
                            iface_clean = iface.replace('{', '').replace('}', '').upper()
                            if guid_key in iface_clean or iface_clean in guid_key:
                                scapy_iface = iface
                                break
                        if scapy_iface:
                            interface_map[friendly_name] = scapy_iface
                        else:
                            interface_map[friendly_name] = friendly_name
        except Exception:
            pass
    
    # 如果还是没有，尝试使用 scapy 的接口列表（过滤掉明显不是友好名称的）
    if not interfaces and if_list:
        for iface in if_list:
            # 跳过明显不是友好名称的（包含 GUID 格式或设备路径的）
            if '{' not in iface and '\\Device\\' not in iface and len(iface) < 50:
                if iface not in interfaces:
                    interfaces.append(iface)
                    interface_map[iface] = iface
    
    # 存储映射到模块级别，供后续使用
    get_windows_interfaces.interface_map = interface_map
    
    return interfaces


def find_interface_by_name(name):
    """根据友好名称查找可用的网卡接口（返回 scapy 可识别的接口名）
    兼容 Win7/Win10：Win10 下 Scapy 常返回 \\Device\\NPF_{GUID}，需通过 MAC 或 GUID 匹配。
    """
    if not name:
        return None
    
    try:
        from scapy.all import get_if_list, get_if_hwaddr
        
        # Windows：先构建映射表（避免依赖"先调过 /interfaces"），并做基于 MAC 的解析
        if platform.system() == 'Windows':
            get_windows_interfaces()
            if hasattr(get_windows_interfaces, 'interface_map'):
                interface_map = get_windows_interfaces.interface_map
                if name in interface_map:
                    scapy_iface = interface_map[name]
                    # 若映射到自身（未找到 Scapy 名），不要直接返回，继续用 MAC 解析
                    if scapy_iface and scapy_iface != name:
                        try:
                            get_if_hwaddr(scapy_iface)
                            return scapy_iface
                        except Exception:
                            pass
            # 通过 MAC 直接解析（与 get_interfaces 逻辑一致，避免 Win10 名称差异）
            try:
                import psutil
                net_addrs = psutil.net_if_addrs()
                if name in net_addrs:
                    mac = None
                    for addr in net_addrs[name]:
                        if hasattr(addr, 'family') and addr.family == psutil.AF_LINK:
                            mac = (addr.address or '').replace('-', ':').upper()
                            break
                    if mac and mac != '00:00:00:00:00:00':
                        if_list = get_if_list()
                        for iface in if_list:
                            try:
                                iface_mac = get_if_hwaddr(iface)
                                if iface_mac and iface_mac.replace('-', ':').upper() == mac:
                                    return iface
                            except Exception:
                                continue
            except Exception:
                pass
        
        # 非 Windows 或上面未命中：使用原有映射表
        if hasattr(get_windows_interfaces, 'interface_map'):
            interface_map = get_windows_interfaces.interface_map
            if name in interface_map:
                scapy_iface = interface_map[name]
                try:
                    get_if_hwaddr(scapy_iface)
                    return scapy_iface
                except Exception:
                    pass
        
        # 获取 scapy 接口列表
        if_list = get_if_list()
        
        # 精确匹配
        if name in if_list:
            try:
                get_if_hwaddr(name)
                return name
            except Exception:
                pass
        
        # 部分匹配（不区分大小写）
        name_lower = name.lower()
        for iface in if_list:
            if iface.lower() == name_lower or iface.lower().startswith(name_lower):
                try:
                    get_if_hwaddr(iface)
                    return iface
                except Exception:
                    continue
        
        # 在 Windows 上，尝试通过 PowerShell 查找友好名称对应的 GUID
        if platform.system() == 'Windows':
            try:
                import subprocess
                ps_cmd = f'$adapter = Get-NetAdapter -Name "{name}" -ErrorAction SilentlyContinue; if ($adapter) {{ $adapter.InterfaceGuid }}'
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    guid = result.stdout.strip()
                    guid_clean = guid.replace('{', '').replace('}', '').upper()
                    for iface in if_list:
                        iface_clean = iface.replace('{', '').replace('}', '').upper()
                        if guid_clean in iface_clean or iface_clean in guid_clean:
                            try:
                                get_if_hwaddr(iface)
                                return iface
                            except Exception:
                                continue
            except Exception:
                pass
        
        return None
    except Exception:
        return None


def get_interface_name_hint():
    """获取网卡名称提示"""
    hints = []
    
    try:
        import psutil
        net_if_addrs = psutil.net_if_addrs()
        if net_if_addrs:
            hints.append("可用网卡:")
            for name in list(net_if_addrs.keys())[:5]:
                if 'Loopback' not in name and '本地连接*' not in name:
                    hints.append(f"  - {name}")
            if len(net_if_addrs) > 5:
                hints.append(f"  ... 共 {len(net_if_addrs)} 个网卡")
    except ImportError:
        try:
            from scapy.all import get_if_list
            if_list = get_if_list()
            if if_list:
                hints.append("可用网卡:")
                for iface in if_list[:5]:
                    hints.append(f"  - {iface}")
                if len(if_list) > 5:
                    hints.append(f"  ... 共 {len(if_list)} 个网卡")
        except Exception:
            hints.append("无法获取网卡列表")
    except Exception:
        hints.append("无法获取网卡列表")
    
    return "\n".join(hints)


def validate_interface(iface_name):
    """验证网卡是否可用（接受友好名称，返回 scapy 可识别的接口名）"""
    if not iface_name:
        return False, "网卡名称为空"
    
    try:
        from scapy.all import get_if_hwaddr
        
        # 首先尝试将友好名称转换为 scapy 接口名
        scapy_iface = find_interface_by_name(iface_name)
        if scapy_iface:
            # 验证 scapy 接口是否可用
            mac = get_if_hwaddr(scapy_iface)
            if mac and mac != "00:00:00:00:00:00":
                return True, f"网卡可用，MAC: {mac}"
            else:
                return False, "网卡 MAC 地址无效"
        else:
            # 如果找不到，尝试直接使用（可能是 scapy 接口名）
            try:
                mac = get_if_hwaddr(iface_name)
                if mac and mac != "00:00:00:00:00:00":
                    return True, f"网卡可用，MAC: {mac}"
                else:
                    return False, "网卡 MAC 地址无效"
            except Exception as e:
                return False, f"网卡验证失败: {str(e)}"
    except Exception as e:
        return False, f"网卡验证失败: {str(e)}"
