"""
ASN.1 BER 解码器 - 用于 IEC 61850 GOOSE/SV 协议
简化实现，支持基本的 ASN.1 类型解码
"""
import struct
from datetime import datetime


class ASN1Decoder:
    """ASN.1 BER 解码器"""
    
    @staticmethod
    def decode_tag(data, offset=0):
        """解码标签字段"""
        if offset >= len(data):
            return None, offset
        tag = data[offset]
        offset += 1
        return tag, offset
    
    @staticmethod
    def decode_length(data, offset=0):
        """解码长度字段"""
        if offset >= len(data):
            return None, offset
        length_byte = data[offset]
        offset += 1
        
        if length_byte < 128:
            return length_byte, offset
        else:
            # 长格式
            length_len = length_byte & 0x7F
            if length_len == 0:
                return None, offset  # 不定长（不支持）
            length = 0
            for _ in range(length_len):
                if offset >= len(data):
                    return None, offset
                length = (length << 8) | data[offset]
                offset += 1
            return length, offset
    
    @staticmethod
    def decode_boolean(data, offset=0):
        """解码布尔值"""
        tag, offset = ASN1Decoder.decode_tag(data, offset)
        length, offset = ASN1Decoder.decode_length(data, offset)
        if length != 1 or offset >= len(data):
            return None, offset
        value = data[offset] != 0
        offset += 1
        return value, offset
    
    @staticmethod
    def decode_integer(data, offset=0):
        """解码整数"""
        tag, offset = ASN1Decoder.decode_tag(data, offset)
        length, offset = ASN1Decoder.decode_length(data, offset)
        if length is None or offset + length > len(data):
            return None, offset
        value_bytes = data[offset:offset+length]
        offset += length
        
        if not value_bytes:
            return 0, offset
        
        # 处理有符号整数
        if len(value_bytes) == 1:
            value = struct.unpack('>b', value_bytes)[0]
        elif len(value_bytes) == 2:
            value = struct.unpack('>h', value_bytes)[0]
        elif len(value_bytes) == 4:
            value = struct.unpack('>i', value_bytes)[0]
        else:
            # 长整数（简化处理）
            value = int.from_bytes(value_bytes, byteorder='big', signed=True)
        
        return value, offset
    
    @staticmethod
    def decode_octet_string(data, offset=0):
        """解码八位字节串"""
        tag, offset = ASN1Decoder.decode_tag(data, offset)
        length, offset = ASN1Decoder.decode_length(data, offset)
        if length is None or offset + length > len(data):
            return None, offset
        value = data[offset:offset+length]
        offset += length
        return value, offset
    
    @staticmethod
    def decode_utf8_string(data, offset=0):
        """解码 UTF-8 字符串"""
        tag, offset = ASN1Decoder.decode_tag(data, offset)
        length, offset = ASN1Decoder.decode_length(data, offset)
        if length is None or offset + length > len(data):
            return None, offset
        value = data[offset:offset+length].decode('utf-8', errors='ignore')
        offset += length
        return value, offset
    
    @staticmethod
    def decode_sequence(data, offset=0):
        """解码序列"""
        tag, offset = ASN1Decoder.decode_tag(data, offset)
        length, offset = ASN1Decoder.decode_length(data, offset)
        if length is None or offset + length > len(data):
            return None, offset
        end_offset = offset + length
        elements = []
        while offset < end_offset:
            # 尝试解码下一个元素（简化实现）
            element_tag, _ = ASN1Decoder.decode_tag(data, offset)
            if element_tag is None:
                break
            # 根据标签类型解码
            if element_tag == 0x01:  # BOOLEAN
                value, offset = ASN1Decoder.decode_boolean(data, offset)
            elif element_tag == 0x02:  # INTEGER
                value, offset = ASN1Decoder.decode_integer(data, offset)
            elif element_tag == 0x04:  # OCTET STRING
                value, offset = ASN1Decoder.decode_octet_string(data, offset)
            elif element_tag == 0x0C:  # UTF8String
                value, offset = ASN1Decoder.decode_utf8_string(data, offset)
            elif element_tag == 0x30:  # SEQUENCE
                value, offset = ASN1Decoder.decode_sequence(data, offset)
            else:
                # 未知类型，跳过
                _, offset = ASN1Decoder.decode_length(data, offset)
                length, _ = ASN1Decoder.decode_length(data, offset)
                if length is not None:
                    offset += length
                else:
                    break
                continue
            if value is not None:
                elements.append(value)
        return elements, offset


class GOOSEDecoder:
    """GOOSE 报文解码器"""
    
    @staticmethod
    def decode_goose_pdu(data):
        """解码 GOOSE PDU"""
        try:
            elements, _ = ASN1Decoder.decode_sequence(data)
            if not elements or len(elements) < 6:
                return None
            
            result = {}
            idx = 0
            
            # gocbRef
            if idx < len(elements) and isinstance(elements[idx], str):
                result['gocb_ref'] = elements[idx]
                idx += 1
            
            # timeAllowedToLive
            if idx < len(elements) and isinstance(elements[idx], int):
                result['timeallowedtolive'] = elements[idx]
                idx += 1
            
            # datSet
            if idx < len(elements) and isinstance(elements[idx], str):
                result['datset'] = elements[idx]
                idx += 1
            
            # t (时间) - 跳过
            idx += 1
            
            # stNum
            if idx < len(elements) and isinstance(elements[idx], int):
                result['stnum'] = elements[idx]
                idx += 1
            
            # sqNum
            if idx < len(elements) and isinstance(elements[idx], int):
                result['sqnum'] = elements[idx]
                idx += 1
            
            # 跳过 test, confRev, ndsCom
            idx += 3
            
            # numDatSetEntries
            if idx < len(elements) and isinstance(elements[idx], int):
                num_entries = elements[idx]
                idx += 1
                
                # allData
                if idx < len(elements):
                    data_list = elements[idx]
                    if isinstance(data_list, list):
                        result['data'] = {}
                        # 简化处理：将数据列表转换为字典
                        for i, val in enumerate(data_list):
                            result['data'][f'Data_{i}'] = val
            
            return result
        except Exception as e:
            return None


class SVDecoder:
    """SV 报文解码器"""
    
    @staticmethod
    def decode_sv_pdu(data):
        """解码 SV PDU"""
        try:
            elements, _ = ASN1Decoder.decode_sequence(data)
            if not elements or len(elements) < 3:
                return None
            
            result = {}
            idx = 0
            
            # svID
            if idx < len(elements) and isinstance(elements[idx], str):
                result['svid'] = elements[idx]
                idx += 1
            
            # smpCnt
            if idx < len(elements) and isinstance(elements[idx], int):
                result['smpcnt'] = elements[idx]
                idx += 1
            
            # confRev - 跳过
            idx += 1
            
            # smpSynch - 跳过
            idx += 1
            
            # smpRate
            if idx < len(elements) and isinstance(elements[idx], int):
                result['smprate'] = elements[idx]
                idx += 1
            
            # numDatSetEntries
            if idx < len(elements) and isinstance(elements[idx], int):
                num_entries = elements[idx]
                idx += 1
                
                # data
                if idx < len(elements):
                    data_list = elements[idx]
                    if isinstance(data_list, list):
                        result['samples'] = {}
                        # 简化处理：将数据列表转换为字典
                        for i, val in enumerate(data_list):
                            if isinstance(val, int):
                                # 恢复浮点数（之前放大了1000倍）
                                result['samples'][f'Sample_{i}'] = val / 1000.0
                            else:
                                result['samples'][f'Sample_{i}'] = val
            
            return result
        except Exception as e:
            return None

