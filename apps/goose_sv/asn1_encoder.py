"""
ASN.1 BER 编码器 - 用于 IEC 61850 GOOSE/SV 协议
简化实现，支持基本的 ASN.1 类型编码
"""
import struct
from datetime import datetime


class ASN1Encoder:
    """ASN.1 BER 编码器"""
    
    # ASN.1 标签类型
    TAG_BOOLEAN = 0x01
    TAG_INTEGER = 0x02
    TAG_BIT_STRING = 0x03
    TAG_OCTET_STRING = 0x04
    TAG_NULL = 0x05
    TAG_OBJECT_IDENTIFIER = 0x06
    TAG_UTF8String = 0x0C
    TAG_VISIBLE_STRING = 0x1A  # IEC 61850 GOOSE 使用 VisibleString
    TAG_UTCTIME = 0x17  # UTC Time - IEC 61850 GOOSE 使用此类型
    TAG_REAL = 0x09  # REAL (浮点数) - ASN.1 类型
    TAG_SEQUENCE = 0x30  # 通用序列
    TAG_APPLICATION_SEQUENCE = 0x61  # 应用层序列 - IEC 61850 GOOSE PDU 使用此类型
    TAG_SEQUENCE_OF = 0x30
    TAG_SET = 0x31
    
    @staticmethod
    def encode_length(length, force_long_format=False):
        """编码长度字段 - ASN.1 BER 格式
        
        短格式（< 128）：直接使用长度值
        长格式（>= 128）：0x80 | 长度字节数 + 长度字节（大端序）
        
        注意：对于 IEC 61850 GOOSE，强制长格式时：
        - 长度 ≤ 255：使用 0x81（后续1字节）
        - 长度 ≤ 65535：使用 0x82（后续2字节）
        
        Args:
            length: 长度值
            force_long_format: 是否强制使用长格式（即使长度 < 128）
                            对于 GOOSE allData (0xAB)，必须使用长格式以确保兼容性
        """
        if force_long_format or length >= 128:
            # 长格式：根据长度值选择合适的字节数
            if length <= 255:
                # 长度 ≤ 255：使用 0x81（后续1字节）
                return bytes([0x81, length & 0xFF])
            elif length <= 0xFFFF:
                # 长度 ≤ 65535：使用 0x82（后续2字节）
                return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
            else:
                # 超过 2 字节，使用实际需要的字节数
                length_bytes = []
                temp = length
                while temp > 0:
                    length_bytes.insert(0, temp & 0xFF)
                    temp >>= 8
                return bytes([0x80 | len(length_bytes)] + length_bytes)
        else:
            # 短格式（< 128）
            return bytes([length])
    
    @staticmethod
    def encode_tag(tag, constructed=False, context_specific=False, context_tag=None):
        """编码标签字段
        
        Args:
            tag: 标签值（通用标签）
            constructed: 是否为构造类型
            context_specific: 是否使用上下文特定标签
            context_tag: 上下文特定标签编号（0-30）
        """
        if context_specific and context_tag is not None:
            # 上下文特定标签：0x80 | (0x20 if constructed) | context_tag
            # 但 context_tag 在 0-30 范围内时，直接编码
            if context_tag < 31:
                return bytes([0x80 | (0x20 if constructed else 0x00) | context_tag])
            else:
                # 长标签格式（简化实现，不支持）
                return bytes([0x80 | (0x20 if constructed else 0x00)])
        else:
            # 通用标签
            if tag < 31:
                return bytes([tag | (0x20 if constructed else 0x00)])
            else:
                # 长标签格式（简化实现，不支持）
                return bytes([tag])
    
    @staticmethod
    def encode_boolean(value, context_tag=None):
        """编码布尔值
        
        Args:
            value: 布尔值
            context_tag: 上下文特定标签编号（如果为 None，使用通用标签）
        """
        if context_tag is not None:
            # 使用上下文特定标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_BOOLEAN, context_specific=True, context_tag=context_tag)
        else:
            # 使用通用标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_BOOLEAN)
        length = ASN1Encoder.encode_length(1)
        content = b'\xFF' if value else b'\x00'
        return tag + length + content
    
    @staticmethod
    def encode_integer(value, context_tag=None):
        """编码整数 - ASN.1 BER 格式
        
        Args:
            value: 整数值
            context_tag: 上下文特定标签编号（如果为 None，使用通用标签）
        """
        if value is None:
            raise ValueError("Cannot encode None as integer")
        if context_tag is not None:
            # 使用上下文特定标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_INTEGER, context_specific=True, context_tag=context_tag)
        else:
            # 使用通用标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_INTEGER)
        
        if value == 0:
            content = b'\x00'
        elif value < 0:
            # 负数：使用补码表示
            if value >= -128:
                content = struct.pack('>b', value)
            elif value >= -32768:
                content = struct.pack('>h', value)
            else:
                content = struct.pack('>i', value)
            # 移除前导 0xFF（如果最高位是 1，且前一个字节也是 0xFF）
            while len(content) > 1 and content[0] == 0xFF and (content[1] & 0x80) != 0:
                content = content[1:]
        else:
            # 正数：使用最小字节数
            if value < 128:
                content = struct.pack('>B', value)
            elif value < 32768:
                content = struct.pack('>H', value)
            else:
                content = struct.pack('>I', value)
            # 移除前导零（但确保至少一个字节）
            while len(content) > 1 and content[0] == 0x00 and (content[1] & 0x80) == 0:
                content = content[1:]
        
        # 确保 content 不为空
        if len(content) == 0:
            raise ValueError(f"Integer encoding resulted in empty content for value {value}")
        
        length = ASN1Encoder.encode_length(len(content))
        result = tag + length + content
        if len(result) < 3:  # tag(1) + length(1) + content(至少1)
            raise ValueError(f"Encoded integer result is too short: {len(result)} bytes")
        return result
    
    @staticmethod
    def encode_integer_fixed(value, context_tag=None, fixed_bytes=3):
        """编码整数 - 使用固定字节数格式（用于 IEC 61850 GOOSE allData）
        
        IEC 61850 GOOSE allData 中的整数通常使用固定3字节格式，即使值很小也使用3字节。
        这样可以确保所有整数数据项的长度一致，便于解析。
        
        Args:
            value: 整数值
            context_tag: 上下文特定标签编号（如果为 None，使用通用标签）
            fixed_bytes: 固定字节数（通常为3，用于 GOOSE allData）
        """
        if value is None:
            raise ValueError("Cannot encode None as integer")
        if context_tag is not None:
            # 使用上下文特定标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_INTEGER, context_specific=True, context_tag=context_tag)
        else:
            # 使用通用标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_INTEGER)
        
        # 使用固定字节数编码（大端序）
        if fixed_bytes == 1:
            if value < 0:
                # 有符号1字节
                content = struct.pack('>b', value)
            else:
                # 无符号1字节
                content = struct.pack('>B', value & 0xFF)
        elif fixed_bytes == 2:
            if value < 0:
                # 有符号2字节
                content = struct.pack('>h', value)
            else:
                # 无符号2字节
                content = struct.pack('>H', value & 0xFFFF)
        elif fixed_bytes == 3:
            # 3字节：使用最高3字节（大端序）
            if value < 0:
                # 负数：扩展到3字节（符号扩展）
                # 对于负数，使用4字节打包后取后3字节
                packed = struct.pack('>i', value)
                content = packed[1:]  # 取后3字节（去掉符号字节）
            else:
                # 正数：使用3字节，高位补0
                # 对于正数，使用4字节打包后取后3字节
                packed = struct.pack('>I', value & 0xFFFFFF)
                content = packed[1:]  # 取后3字节
        elif fixed_bytes == 4:
            if value < 0:
                # 有符号4字节
                content = struct.pack('>i', value)
            else:
                # 无符号4字节
                content = struct.pack('>I', value & 0xFFFFFFFF)
        elif fixed_bytes == 8:
            if value < 0:
                # 有符号8字节
                content = struct.pack('>q', value)
            else:
                # 无符号8字节
                content = struct.pack('>Q', value & 0xFFFFFFFFFFFFFFFF)
        else:
            raise ValueError(f"Unsupported fixed_bytes: {fixed_bytes}")
        
        length = ASN1Encoder.encode_length(len(content))
        result = tag + length + content
        if len(result) < 3:
            raise ValueError(f"Encoded integer result is too short: {len(result)} bytes")
        return result
    
    @staticmethod
    def encode_octet_string(value):
        """编码八位字节串"""
        if isinstance(value, str):
            value = value.encode('utf-8')
        tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_OCTET_STRING)
        length = ASN1Encoder.encode_length(len(value))
        return tag + length + value
    
    @staticmethod
    def encode_utf8_string(value):
        """编码 UTF-8 字符串"""
        if value is None:
            raise ValueError("Cannot encode None as UTF-8 string")
        if isinstance(value, str):
            value = value.encode('utf-8')
        if len(value) == 0:
            # 空字符串是允许的，但至少要有 tag + length
            pass
        tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_UTF8String)
        length = ASN1Encoder.encode_length(len(value))
        result = tag + length + value
        if len(result) < 2:
            raise ValueError("Encoded UTF-8 string result is too short")
        return result
    
    @staticmethod
    def encode_visible_string(value, context_tag=None):
        """编码 VisibleString - IEC 61850 GOOSE 使用此类型
        
        Args:
            value: 字符串值
            context_tag: 上下文特定标签编号（如果为 None，使用通用标签）
        """
        if value is None:
            raise ValueError("Cannot encode None as VisibleString")
        if isinstance(value, str):
            value = value.encode('utf-8')
        if len(value) == 0:
            # 空字符串是允许的，但至少要有 tag + length
            pass
        if context_tag is not None:
            # 使用上下文特定标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_VISIBLE_STRING, context_specific=True, context_tag=context_tag)
        else:
            # 使用通用标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_VISIBLE_STRING)
        length = ASN1Encoder.encode_length(len(value))
        result = tag + length + value
        if len(result) < 2:
            raise ValueError("Encoded VisibleString result is too short")
        return result
    
    @staticmethod
    def encode_sequence(elements, context_tag=None, force_long_length=False):
        """编码序列
        
        Args:
            elements: 序列元素列表
            context_tag: 上下文特定标签编号（如果为 None，使用通用标签）
            force_long_length: 是否强制使用长格式长度编码
                             对于 GOOSE allData (0xAB)，必须使用长格式以确保兼容性
        """
        # 确保所有元素都是 bytes
        content_parts = []
        for idx, elem in enumerate(elements):
            if isinstance(elem, bytes):
                if len(elem) == 0:
                    raise ValueError(f"Sequence element {idx} is empty bytes")
                content_parts.append(elem)
            elif isinstance(elem, str):
                encoded = elem.encode('utf-8')
                if len(encoded) == 0:
                    raise ValueError(f"Sequence element {idx} (string) encoded to empty bytes")
                content_parts.append(encoded)
            else:
                encoded = bytes(elem)
                if len(encoded) == 0:
                    raise ValueError(f"Sequence element {idx} converted to empty bytes")
                content_parts.append(encoded)
        content = b''.join(content_parts)
        if context_tag is not None:
            # 使用上下文特定标签（constructed）
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_SEQUENCE, constructed=True, context_specific=True, context_tag=context_tag)
        else:
            # 使用通用标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_SEQUENCE, constructed=True)
        length = ASN1Encoder.encode_length(len(content), force_long_format=force_long_length)
        result = tag + length + content
        # 验证结果不为空（至少要有 tag + length，即使 content 为空）
        if len(result) < 2:
            raise ValueError("Encoded sequence result is too short (less than 2 bytes)")
        return result
    
    @staticmethod
    def encode_utc_time(dt=None, context_tag=None, use_binary_format=True):
        """编码 UTC 时间 - IEC 61850 GOOSE 使用 UTCTime
        
        IEC 61850 GOOSE 的 UTCTime 使用8字节二进制格式（BCD编码）：
        - 前6字节：YYMMDDHHMMSS (BCD编码)
        - 后2字节：毫秒（大端序，2字节）
        
        Args:
            dt: 日期时间对象（如果为 None，使用当前 UTC 时间）
            context_tag: 上下文特定标签编号（如果为 None，使用通用标签）
            use_binary_format: 是否使用二进制格式（默认True，8字节BCD格式）
        """
        if dt is None:
            dt = datetime.utcnow()
        
        # 使用8字节二进制格式（BCD编码）
        # 前6字节：YYMMDDHHMMSS (BCD编码)
        year_bcd = ((dt.year % 100) // 10 << 4) | (dt.year % 10)
        month_bcd = ((dt.month // 10) << 4) | (dt.month % 10)
        day_bcd = ((dt.day // 10) << 4) | (dt.day % 10)
        hour_bcd = ((dt.hour // 10) << 4) | (dt.hour % 10)
        minute_bcd = ((dt.minute // 10) << 4) | (dt.minute % 10)
        second_bcd = ((dt.second // 10) << 4) | (dt.second % 10)
        
        # 后2字节：毫秒（大端序）
        milliseconds = dt.microsecond // 1000
        ms_high = (milliseconds >> 8) & 0xFF
        ms_low = milliseconds & 0xFF
        
        time_bytes = bytes([year_bcd, month_bcd, day_bcd, hour_bcd, minute_bcd, second_bcd, ms_high, ms_low])
        
        # 验证长度（必须是8字节）
        if len(time_bytes) != 8:
            raise ValueError(f"UTCTime encoding length mismatch: expected 8 bytes, got {len(time_bytes)}")
        
        if context_tag is not None:
            # 使用上下文特定标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_UTCTIME, context_specific=True, context_tag=context_tag)
        else:
            # 使用通用标签
            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_UTCTIME)
        length = ASN1Encoder.encode_length(len(time_bytes))
        result = tag + length + time_bytes
        if len(result) < 2:
            raise ValueError("Encoded UTCTime result is too short")
        return result


class GOOSEEncoder:
    """GOOSE 报文编码器"""
    
    @staticmethod
    def encode_goose_pdu(config):
        """编码 GOOSE PDU - 符合 IEC 61850-8-1 标准"""
        # GOOSE PDU 结构（ASN.1 SEQUENCE）:
        # gocbRef, timeAllowedToLive, datSet, [goID], t, stNum, sqNum, 
        # test, confRev, ndsCom, numDatSetEntries, allData
        
        if config is None:
            raise ValueError("GOOSE config cannot be None")
        
        elements = []
        element_names = []  # 用于调试
        
        try:
            # IEC 61850 GOOSE PDU 使用上下文特定标签（Context-Specific Tags）
            # 1. gocbRef (VisibleString) - 上下文标签 0 (0x80)
            gocb_ref = config.get('gocb_ref', 'IED1/LLN0$GO$GSE1')
            if not gocb_ref:
                gocb_ref = 'IED1/LLN0$GO$GSE1'  # 确保有默认值
            encoded = ASN1Encoder.encode_visible_string(gocb_ref, context_tag=0)  # 上下文标签 0
            if len(encoded) == 0:
                raise ValueError("gocbRef encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("gocbRef")
            
            # 2. timeAllowedToLive (INTEGER) - 上下文标签 1 (0x81)
            time_allowed = config.get('timeallowedtolive', 2000)
            if time_allowed is None:
                time_allowed = 2000
            encoded = ASN1Encoder.encode_integer(time_allowed, context_tag=1)  # 上下文标签 1
            if len(encoded) == 0:
                raise ValueError("timeAllowedToLive encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("timeAllowedToLive")
            
            # 3. datSet (VisibleString) - 上下文标签 2 (0x82)
            datset = config.get('datset', 'IED1/LLN0$DataSet1')
            if not datset:
                datset = 'IED1/LLN0$DataSet1'  # 确保有默认值
            encoded = ASN1Encoder.encode_visible_string(datset, context_tag=2)  # 上下文标签 2
            if len(encoded) == 0:
                raise ValueError("datSet encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("datSet")
            
            # 4. goID (VisibleString) - 上下文标签 3 (0x83) - 可选但建议包含
            # 注意：虽然 goID 是可选的，但为了符合完整规约，建议包含此字段
            go_id = config.get('go_id', '')
            # 如果没有提供 goID，使用 gocb_ref 作为默认值（符合 IEC 61850 常见实践）
            if not go_id:
                go_id = config.get('gocb_ref', 'IED1/LLN0$GO$GSE1')
            # 总是包含 goID 字段（符合完整规约）
            encoded = ASN1Encoder.encode_visible_string(go_id, context_tag=3)  # 上下文标签 3
            if len(encoded) == 0:
                raise ValueError("goID encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("goID")
            
            # 5. t (UtcTime) - 上下文标签 4 (0x84)
            # 使用8字节二进制格式（BCD编码）
            encoded = ASN1Encoder.encode_utc_time(context_tag=4, use_binary_format=True)  # 上下文标签 4
            if len(encoded) == 0:
                raise ValueError("t (UtcTime) encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("t")
            
            # 6. stNum (INTEGER) - 上下文标签 5 (0x85)
            stnum = config.get('stnum', 1)
            if stnum is None:
                stnum = 1
            encoded = ASN1Encoder.encode_integer(stnum, context_tag=5)  # 上下文标签 5
            if len(encoded) == 0:
                raise ValueError("stNum encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("stNum")
            
            # 7. sqNum (INTEGER) - 上下文标签 6 (0x86)
            sqnum = config.get('sqnum', 0)
            if sqnum is None:
                sqnum = 0
            encoded = ASN1Encoder.encode_integer(sqnum, context_tag=6)  # 上下文标签 6
            if len(encoded) == 0:
                raise ValueError("sqNum encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("sqNum")
            
            # 8. test (BOOLEAN) - 上下文标签 7 (0x87)
            test = config.get('test', False)
            if test is None:
                test = False
            encoded = ASN1Encoder.encode_boolean(test, context_tag=7)  # 上下文标签 7
            if len(encoded) == 0:
                raise ValueError("test encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("test")
            
            # 9. confRev (INTEGER) - 上下文标签 8 (0x88)
            conf_rev = config.get('confrev', 1)
            if conf_rev is None:
                conf_rev = 1
            encoded = ASN1Encoder.encode_integer(conf_rev, context_tag=8)  # 上下文标签 8
            if len(encoded) == 0:
                raise ValueError("confRev encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("confRev")
            
            # 10. ndsCom (BOOLEAN) - 上下文标签 9 (0x89)
            nds_com = config.get('ndscom', False)
            if nds_com is None:
                nds_com = False
            encoded = ASN1Encoder.encode_boolean(nds_com, context_tag=9)  # 上下文标签 9
            if len(encoded) == 0:
                raise ValueError("ndsCom encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("ndsCom")
            
            # 11. numDatSetEntries (INTEGER) - 上下文标签 10 (0x8A)
            data = config.get('data', {})
            if data is None:
                data = {}
            num_entries = len(data) if data else 0
            encoded = ASN1Encoder.encode_integer(num_entries, context_tag=10)  # 上下文标签 10
            if len(encoded) == 0:
                raise ValueError("numDatSetEntries encoding resulted in empty bytes")
            elements.append(encoded)
            element_names.append("numDatSetEntries")
            
            # 12. allData (SEQUENCE OF Data) - 上下文标签 11 (0xAB, constructed) - 必需
            # IEC 61850 GOOSE allData 中的数据项使用上下文特定标签，根据数据类型选择：
            # - BOOLEAN: 0x83 (3字节：标签1 + 长度1 + 值1)
            # - INT8: 0x84 (3字节：标签1 + 长度1 + 值1)
            # - INT16: 0x85 (4字节：标签1 + 长度1 + 值2)
            # - INT32: 0x86 (6字节：标签1 + 长度1 + 值4)
            # - INT64: 0x87 (10字节：标签1 + 长度1 + 值8)
            # - INT8U: 0x88 (3字节：标签1 + 长度1 + 值1)
            # - INT16U: 0x89 (4字节：标签1 + 长度1 + 值2)
            # - INT32U: 0x8A (6字节：标签1 + 长度1 + 值4)
            # - FLOAT32: 0x8B (6字节：标签1 + 长度1 + 值4)
            # - FLOAT64: 0x8C (10字节：标签1 + 长度1 + 值8)
            # - VisibleString: 0x8D (变长)
            # - OctetString: 0x8E (变长)
            # - BitString: 0x8F (变长)
            # - UtcTime: 0x91 (10字节：标签1 + 长度1 + 值8)
            data_elements = []
            if data:
                for key, value in data.items():
                    try:
                        # 处理 None 值：如果是时间相关字段且值为 None，转换为空字符串
                        if value is None:
                            key_lower = key.lower()
                            if 'time' in key_lower or 'timestamp' in key_lower:
                                # 时间字段为 None，转换为空字符串（使用 VisibleString）
                                value = ""
                            else:
                                # 非时间字段的 None 值，跳过
                                continue
                        
                        # 根据数据类型编码（allData 中的元素使用上下文特定标签）
                        if isinstance(value, bool):
                            # BOOLEAN: 上下文标签 0x83 (3字节)
                            encoded_elem = ASN1Encoder.encode_boolean(value, context_tag=3)
                        elif isinstance(value, int):
                            # 整数：根据值范围自动选择合适的类型
                            if value >= 0:
                                # 无符号整数
                                if value <= 255:
                                    # INT8U: 上下文标签 0x88 (3字节)
                                    encoded_elem = ASN1Encoder.encode_integer_fixed(value, context_tag=0x88-0x80, fixed_bytes=1)
                                elif value <= 65535:
                                    # INT16U: 上下文标签 0x89 (4字节)
                                    encoded_elem = ASN1Encoder.encode_integer_fixed(value, context_tag=0x89-0x80, fixed_bytes=2)
                                elif value <= 4294967295:
                                    # INT32U: 上下文标签 0x8A (6字节)
                                    encoded_elem = ASN1Encoder.encode_integer_fixed(value, context_tag=0x8A-0x80, fixed_bytes=4)
                                else:
                                    # INT64: 上下文标签 0x87 (10字节)
                                    encoded_elem = ASN1Encoder.encode_integer_fixed(value, context_tag=0x87-0x80, fixed_bytes=8)
                            else:
                                # 有符号整数
                                if value >= -128 and value <= 127:
                                    # INT8: 上下文标签 0x84 (3字节)
                                    encoded_elem = ASN1Encoder.encode_integer_fixed(value, context_tag=0x84-0x80, fixed_bytes=1)
                                elif value >= -32768 and value <= 32767:
                                    # INT16: 上下文标签 0x85 (4字节)
                                    encoded_elem = ASN1Encoder.encode_integer_fixed(value, context_tag=0x85-0x80, fixed_bytes=2)
                                elif value >= -2147483648 and value <= 2147483647:
                                    # INT32: 上下文标签 0x86 (6字节)
                                    encoded_elem = ASN1Encoder.encode_integer_fixed(value, context_tag=0x86-0x80, fixed_bytes=4)
                                else:
                                    # INT64: 上下文标签 0x87 (10字节)
                                    encoded_elem = ASN1Encoder.encode_integer_fixed(value, context_tag=0x87-0x80, fixed_bytes=8)
                        elif isinstance(value, float):
                            # 浮点数：默认使用 FLOAT32 (0x8B)，如果需要更高精度可以使用 FLOAT64 (0x8C)
                            # FLOAT32: 上下文标签 0x8B (6字节：标签1 + 长度1 + 值4)
                            # 注意：IEC 61850 GOOSE allData 中的浮点数使用 REAL 类型，但标签是上下文特定的
                            float_bytes = struct.pack('>f', value)
                            tag = ASN1Encoder.encode_tag(ASN1Encoder.TAG_REAL, context_specific=True, context_tag=0x8B-0x80)
                            length = ASN1Encoder.encode_length(4)
                            encoded_elem = tag + length + float_bytes
                        elif isinstance(value, str):
                            # 所有字符串都作为 VisibleString 处理（不使用 UtcTime）
                            # VisibleString: 上下文标签 0x8D (变长)
                            # 注意：0x8D 是完整的标签值，不是上下文标签编号
                            # 上下文标签编号 = 0x8D - 0x80 = 13 (0x0D)
                            encoded_elem = ASN1Encoder.encode_visible_string(value, context_tag=13)
                        elif isinstance(value, datetime):
                            # 直接是 datetime 对象，转换为字符串格式
                            # 格式化为字符串，使用 VisibleString
                            time_str = value.strftime("%Y-%m-%d %H:%M:%S")
                            encoded_elem = ASN1Encoder.encode_visible_string(time_str, context_tag=13)
                        elif value is None:
                            # None 值：转换为空字符串，使用 VisibleString
                            encoded_elem = ASN1Encoder.encode_visible_string("", context_tag=13)
                        else:
                            # 其他类型转为字符串
                            encoded_elem = ASN1Encoder.encode_visible_string(str(value), context_tag=13)
                        
                        if len(encoded_elem) == 0:
                            raise ValueError(f"Data element '{key}' encoding resulted in empty bytes")
                        data_elements.append(encoded_elem)
                    except Exception as e:
                        raise ValueError(f"Failed to encode data element '{key}': {str(e)}")
            
            # 验证数据项数量与 numDataSetEntries 一致
            if len(data_elements) != num_entries:
                raise ValueError(f"Data elements count mismatch: numDataSetEntries={num_entries}, actual data elements={len(data_elements)}")
            
            # allData 必须是 SEQUENCE，使用上下文标签 11 (0xAB, constructed)
            # 强制使用长格式长度编码以确保 GOOSE 兼容性（即使长度 < 128）
            all_data = ASN1Encoder.encode_sequence(data_elements, context_tag=11, force_long_length=True)
            if len(all_data) == 0:
                raise ValueError("allData sequence encoding resulted in empty bytes")
            elements.append(all_data)
            element_names.append("allData")
            
            # 验证所有元素都已添加
            if len(elements) < 11:  # 至少要有11个必需元素（不包括可选的 goID）
                raise ValueError(f"GOOSE PDU has insufficient elements: {len(elements)} (expected at least 11)")
            
            # 验证每个元素的长度
            for idx, (elem, name) in enumerate(zip(elements, element_names)):
                if len(elem) == 0:
                    raise ValueError(f"GOOSE PDU element {idx} ({name}) is empty")
            
            # 构建完整的 GOOSE PDU（最外层使用应用层序列标签 0x61）
            # GOOSE PDU 使用应用层序列（Application Sequence），不是通用序列
            content = b''.join(elements)
            content_length = len(content)
            # 使用应用层序列标签 0x61（constructed）
            tag = bytes([0x61])  # 应用层序列，constructed
            # 根序列的长度编码必须使用长格式（0x81 或 0x82），确保 GOOSE 兼容性
            length = ASN1Encoder.encode_length(content_length, force_long_format=True)
            goose_pdu = tag + length + content
            
            # 验证长度字段与实际内容长度匹配
            if len(length) == 2:  # 0x81 + 1字节
                declared_length = length[1]
                if declared_length != content_length:
                    raise ValueError(f"Root sequence length mismatch: declared {declared_length}, actual {content_length}")
            elif len(length) == 3:  # 0x82 + 2字节
                declared_length = (length[1] << 8) | length[2]
                if declared_length != content_length:
                    raise ValueError(f"Root sequence length mismatch: declared {declared_length}, actual {content_length}")
            
            # 验证 PDU 不为空
            if len(goose_pdu) == 0:
                raise ValueError("GOOSE PDU encoding resulted in zero bytes")
            
            # 验证 PDU 长度合理（至少要有一些数据）
            if len(goose_pdu) < 20:  # 至少要有基本的头部和几个字段
                raise ValueError(f"GOOSE PDU is too short: {len(goose_pdu)} bytes (expected at least 20)")
            
            return goose_pdu
            
        except Exception as e:
            # 提供详细的错误信息
            error_msg = f"GOOSE PDU encoding failed: {str(e)}\n"
            error_msg += f"Elements encoded so far: {len(elements)}/{len(element_names)}\n"
            if element_names:
                error_msg += f"Last element: {element_names[-1] if element_names else 'N/A'}"
            raise ValueError(error_msg) from e


class SVEncoder:
    """SV 报文编码器"""
    
    @staticmethod
    def encode_sv_pdu(config):
        """编码 SV PDU - 符合 IEC 61850-9-2 标准
        
        根据标准表格和Wireshark解析要求，SV PDU 结构（ASN.1 BER编码）:
        根Sequence (Tag 0x60, constructed):
          1. noASDU (Tag 0x80, INTEGER) - ASDU个数
          2. security (Tag 0x81, 可选) - 跳过
          3. seqASDU (Tag 0xA2, SEQUENCE OF) - ASDU序列
             - ASDU (Tag 0x30, SEQUENCE) 仅包含:
               - svID (Tag 0x80) - SV数据流标识，前端传入
               - smpCnt (Tag 0x82) - 采样计数器
               - confRev (Tag 0x83) - 配置版本号，默认 00000001(1)
               - smpSynch (Tag 0x85) - 同步标志，默认 1
               - seqData (Tag 0x87) - 采样数据块
        """
        
        if config is None:
            raise ValueError("SV config cannot be None")
        
        try:
            # ===== 构建 ASDU 内的字段 =====
            asdu_elements = []
            asdu_element_names = []
            
            # 1. svID (Tag 0x80, VisibleString, ≤65字节)
            svid = config.get('svid', 'ML2201BMU/LLN0$SV$MSVCB01')
            if not svid:
                svid = 'ML2201BMU/LLN0$SV$MSVCB01'  # 确保有默认值（ASCII字符串）
            # 验证是否为ASCII字符串
            try:
                svid.encode('ascii')
            except UnicodeEncodeError:
                raise ValueError(f"svID must be ASCII string, got non-ASCII characters: {svid}")
            if len(svid) > 65:
                raise ValueError(f"svID length ({len(svid)}) exceeds maximum (65 bytes)")
            encoded = ASN1Encoder.encode_visible_string(svid, context_tag=0)  # 上下文标签0 (0x80)
            if len(encoded) == 0:
                raise ValueError("svID encoding resulted in empty bytes")
            asdu_elements.append(encoded)
            asdu_element_names.append("svID")
            
            # 2. datset (Tag 0x81, 可选) - 现有pcap包无该字段，跳过
            
            # 3. smpCnt (Tag 0x82, INTEGER) - 采样计数器
            smpcnt = config.get('smpcnt', 0)
            if smpcnt is None:
                smpcnt = 0
            # 使用固定2字节编码（SV 格式：Tag 0x82, length 0x02, 2 bytes）
            encoded = ASN1Encoder.encode_integer_fixed(smpcnt, context_tag=2, fixed_bytes=2)  # 上下文标签2 (0x82)
            if len(encoded) == 0:
                raise ValueError("smpCnt encoding resulted in empty bytes")
            asdu_elements.append(encoded)
            asdu_element_names.append("smpCnt")
            
            # 4. confRev (Tag 0x83, INTEGER) - 配置版本号，默认 00000001(1)
            conf_rev = config.get('confrev', 1)
            if conf_rev is None:
                conf_rev = 1
            if conf_rev < 0 or conf_rev > 0xFFFFFFFF:
                conf_rev = conf_rev & 0xFFFFFFFF
            encoded = ASN1Encoder.encode_integer_fixed(conf_rev, context_tag=3, fixed_bytes=4)  # 上下文标签3 (0x83)，4字节
            if len(encoded) == 0:
                raise ValueError("confRev encoding resulted in empty bytes")
            asdu_elements.append(encoded)
            asdu_element_names.append("confRev")
            
            # 5. smpSynch (Tag 0x85, BOOLEAN) - 同步标志，默认 1
            smp_synch = config.get('smpsynch', True)
            if smp_synch is None:
                smp_synch = True
            if isinstance(smp_synch, int):
                smp_synch = (smp_synch == 1)
            # 使用上下文标签0x85编码BOOLEAN值
            tag = bytes([0x85])  # 直接使用0x85标签
            length = bytes([0x01])  # 长度1字节
            content = bytes([0x01 if smp_synch else 0x00])  # BOOLEAN值 (TRUE=0x01)
            encoded = tag + length + content
            if len(encoded) == 0:
                raise ValueError("smpSynch encoding resulted in empty bytes")
            asdu_elements.append(encoded)
            asdu_element_names.append("smpSynch")
            
            # 7. smpRate (Tag 0x86, 可选) - 现有pcap包无该字段，跳过
            
            # 8. seqData (Tag 0x87, OCTET STRING) - 采样数据块
            # 根据IEC 61850-9-2标准：每个采样值条目是5字节（4字节FLOAT32数值 + 1字节品质位）
            samples = config.get('samples', {})
            if samples is None:
                samples = {}
            data_bytes = []
            if samples:
                for key, value in samples.items():
                    try:
                        if isinstance(value, (int, float)):
                            float_value = float(value)
                            # 编码为FLOAT32字节（大端序）
                            float_bytes = struct.pack('>f', float_value)
                            
                            # 品质位（Quality）：1字节
                            quality = config.get('quality', {}).get(key, 0x00)
                            if not isinstance(quality, int) or quality < 0 or quality > 255:
                                quality = 0x00
                            quality_byte = bytes([quality & 0xFF])
                            
                            # 每个采样值条目：4字节数值 + 1字节品质位 = 5字节
                            data_bytes.append(float_bytes + quality_byte)
                        else:
                            # 其他类型转换为浮点数
                            try:
                                float_value = float(value)
                                float_bytes = struct.pack('>f', float_value)
                                quality = config.get('quality', {}).get(key, 0x00)
                                if not isinstance(quality, int) or quality < 0 or quality > 255:
                                    quality = 0x00
                                quality_byte = bytes([quality & 0xFF])
                                data_bytes.append(float_bytes + quality_byte)
                            except (ValueError, TypeError):
                                raise ValueError(f"Cannot encode sample '{key}' as float")
                    except Exception as e:
                        raise ValueError(f"Failed to encode sample element '{key}': {str(e)}")
            
            # seqData 使用上下文标签0x87 (OCTET STRING)：0x8710 + seqData(16)，固定16字节
            seq_data_content = b''.join(data_bytes)
            SEQ_DATA_LEN = 16
            if len(seq_data_content) < SEQ_DATA_LEN:
                seq_data_content = seq_data_content + bytes(SEQ_DATA_LEN - len(seq_data_content))
            elif len(seq_data_content) > SEQ_DATA_LEN:
                seq_data_content = seq_data_content[:SEQ_DATA_LEN]
            tag = bytes([0x87])  # 直接使用0x87标签
            length = bytes([SEQ_DATA_LEN])  # 单字节长度 0x10 (16)
            seq_data = tag + length + seq_data_content
            if len(seq_data) == 0:
                raise ValueError("seqData encoding resulted in empty bytes")
            asdu_elements.append(seq_data)
            asdu_element_names.append("seqData")
            
            # ===== 构建 ASDU (Tag 0x30, SEQUENCE) =====
            asdu_sequence = ASN1Encoder.encode_sequence(asdu_elements)  # ASDU Sequence (Tag 0x30)
            if len(asdu_sequence) == 0:
                raise ValueError("ASDU sequence encoding resulted in empty bytes")
            
            # ===== 构建 seqASDU (Tag 0xA2, SEQUENCE OF) =====
            # seqASDU使用上下文标签2 (0xA2, constructed)，这就是sacpdu
            # 根据IEC 61850-9-2标准，seqASDU本身就是使用上下文标签2的SEQUENCE OF
            # 0xA2 = 0x80 | 0x20 | 0x02 (上下文特定，constructed，标签2)
            # seqASDU包含1个ASDU，长度使用短格式（如 0xA2 0x52 ...）
            seq_asdu = ASN1Encoder.encode_sequence([asdu_sequence], context_tag=2)  # seqASDU (Tag 0xA2)
            if len(seq_asdu) == 0:
                raise ValueError("seqASDU encoding resulted in empty bytes")
            
            # ===== 构建根Sequence =====
            root_elements = []
            root_element_names = []
            
            # 1. noASDU (Tag 0x80, length 0x01, 1 byte) - ASDU个数，通常为1
            no_asdu = config.get('noASDU', 1)
            if no_asdu < 1 or no_asdu > 255:
                no_asdu = 1
            encoded = ASN1Encoder.encode_integer_fixed(no_asdu, context_tag=0, fixed_bytes=1)  # 上下文标签0 (0x80), 1字节
            if len(encoded) == 0:
                raise ValueError("noASDU encoding resulted in empty bytes")
            root_elements.append(encoded)
            root_element_names.append("noASDU")
            
            # 2. security (Tag 0x81, 可选) - 现有pcap包无该字段，跳过
            
            # 3. seqASDU (Tag 0xA2) - 这就是sacpdu，使用上下文标签2
            root_elements.append(seq_asdu)
            root_element_names.append("seqASDU")
            
            # ===== 构建完整的 SV PDU（根Sequence，Tag 0x60） =====
            root_content = b''.join(root_elements)
            # 根Sequence使用应用层序列标签 0x60 (constructed)，长度使用短格式（如 0x60 0x57 ...）
            root_tag = bytes([0x60])  # 应用层序列，constructed
            root_length = ASN1Encoder.encode_length(len(root_content))
            sv_pdu = root_tag + root_length + root_content
            
            # 验证 PDU 不为空
            if len(sv_pdu) == 0:
                raise ValueError("SV PDU encoding resulted in zero bytes")
            
            # 验证 PDU 长度合理
            if len(sv_pdu) < 15:
                raise ValueError(f"SV PDU is too short: {len(sv_pdu)} bytes (expected at least 15)")
            
            return sv_pdu
            
        except Exception as e:
            # 提供详细的错误信息
            error_msg = f"SV PDU encoding failed: {str(e)}"
            raise ValueError(error_msg) from e


class IEC61850Encoder:
    """IEC 61850 报文编码器 - 包含头部和 PDU"""
    
    @staticmethod
    def encode_goose_packet(config):
        """编码完整的 GOOSE 报文（包含头部和 PDU）"""
        # 编码 ASN.1 PDU
        goose_pdu = GOOSEEncoder.encode_goose_pdu(config)
        
        # 验证 PDU 不为空
        if not goose_pdu or len(goose_pdu) == 0:
            raise ValueError("GOOSE PDU is empty, cannot create packet")
        
        # GOOSE 报文头部结构（8字节）:
        # APPID (2 bytes) - 应用标识
        # Length (2 bytes) - 从 Reserved1 开始到 PDU 结束的总长度（包括头部剩余部分和 PDU）
        # Reserved1 (2 bytes) - 通常为 0x0000
        # Reserved2 (2 bytes) - 通常为 0x0000
        
        appid = config.get('appid', 0x100)
        reserved1 = 0x0000
        reserved2 = 0x0000
        
        # Length = Reserved1(2) + Reserved2(2) + PDU长度
        pdu_length = len(goose_pdu)
        length = 4 + pdu_length  # 4 = Reserved1(2) + Reserved2(2)
        
        # 验证长度字段不会溢出（2字节最大 65535）
        if length > 65535:
            raise ValueError(f"GOOSE packet length ({length}) exceeds maximum (65535)")
        
        # 构建头部
        header = struct.pack('>HHHH', appid, length, reserved1, reserved2)
        
        # 完整的 GOOSE 报文 = 头部 + PDU
        packet = header + goose_pdu
        
        # 最终验证
        if len(packet) != 8 + pdu_length:
            raise ValueError(f"GOOSE packet length mismatch: expected {8 + pdu_length}, got {len(packet)}")
        
        return packet
    
    @staticmethod
    def encode_sv_packet(config):
        """编码完整的 SV 报文（包含头部和 PDU）"""
        # 编码 ASN.1 PDU
        sv_pdu = SVEncoder.encode_sv_pdu(config)
        
        # 验证 PDU 不为空
        if not sv_pdu or len(sv_pdu) == 0:
            raise ValueError("SV PDU is empty, cannot create packet")
        
        # SV 报文头部结构（8字节）:
        # APPID (2 bytes) - 应用标识
        # Length (2 bytes) - 从 Reserved1 开始到 PDU 结束的总长度（包括头部剩余部分和 PDU）
        # Reserved1 (2 bytes) - 通常为 "SV" (0x5356)
        # Reserved2 (2 bytes) - 通常为其他值（如 0x0000 或特定值）
        
        # APPID范围：0x4000~0x7FFF（IEC 61850-9-2标准）
        appid = config.get('appid', 0x4019)
        if appid < 0x4000 or appid > 0x7FFF:
            raise ValueError(f"APPID must be in range 0x4000~0x7FFF, got 0x{appid:04X}")
        reserved1 = 0x5356  # "SV" in ASCII
        reserved2 = 0x0000  # 可以根据需要设置
        
        # Length = Reserved1(2) + Reserved2(2) + PDU长度
        pdu_length = len(sv_pdu)
        length = 4 + pdu_length  # 4 = Reserved1(2) + Reserved2(2)
        
        # 验证长度字段不会溢出（2字节最大 65535）
        if length > 65535:
            raise ValueError(f"SV packet length ({length}) exceeds maximum (65535)")
        
        # 构建头部
        header = struct.pack('>HHHH', appid, length, reserved1, reserved2)
        
        # 完整的 SV 报文 = 头部 + PDU
        packet = header + sv_pdu
        
        # 最终验证
        if len(packet) != 8 + pdu_length:
            raise ValueError(f"SV packet length mismatch: expected {8 + pdu_length}, got {len(packet)}")
        
        return packet

