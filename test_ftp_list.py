#!/usr/bin/env python3
import sys
import time
sys.path.insert(0, 'C:/Users/administrator/Desktop')

from packet_agent import _get_client_manager, connect_ftp_client, list_ftp_files, disconnect_ftp_client

# 连接 FTP
config = {
    'server_ip': '10.40.30.35',
    'server_port': 21,
    'username': 'tdhx',
    'password': 'tdhx@2017'
}

print('Connecting to FTP...', flush=True)
result = connect_ftp_client(config)
print(f'Connect result: {result}', flush=True)
print(f'Return type: {type(result)}', flush=True)

time.sleep(2)

print('', flush=True)
print('Getting file list...', flush=True)
result = list_ftp_files()
print(f'list_ftp_files returns: {result}', flush=True)
print(f'Return type: {type(result)}', flush=True)

if isinstance(result, tuple) and len(result) == 2:
    print(f'  success: {result[0]}', flush=True)
    print(f'  data: {result[1]}', flush=True)

print('', flush=True)
print('Disconnecting FTP...', flush=True)
result = disconnect_ftp_client()
print(f'Disconnect result: {result}', flush=True)
