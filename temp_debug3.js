
document.addEventListener('DOMContentLoaded', function() {
(() => {
    // ========== 初始化服务下发模块 ==========

    // 获取 DOM 元素
    const logList = document.getElementById('service_log_list');
    const clearLogsBtn = document.getElementById('clear_logs_btn');

    // 创建代理连接器实例
    const listenerConnector = new window.ServiceDeploy.AgentConnector('listener', {
        connectBtn: document.getElementById('listener_connect_btn'),
        agentIpInput: document.getElementById('listener_agent_ip'),
        agentPortInput: document.getElementById('listener_agent_port'),
        interfaceSelect: document.getElementById('listener_interface'),
        interfaceInfo: document.getElementById('listener_interface_info'),
        testEnvSelect: document.getElementById('listener_test_env_select'),
        customIpContainer: document.getElementById('listener_custom_ip_container'),
        testEnvContainer: document.getElementById('listener_test_env_select_container'),
        logList: logList
    });

    const clientConnector = new window.ServiceDeploy.AgentConnector('client', {
        connectBtn: document.getElementById('client_connect_btn'),
        agentIpInput: document.getElementById('client_agent_ip'),
        agentPortInput: document.getElementById('client_agent_port'),
        interfaceSelect: document.getElementById('client_interface'),
        interfaceInfo: document.getElementById('client_interface_info'),
        testEnvSelect: document.getElementById('client_test_env_select'),
        customIpContainer: document.getElementById('client_custom_ip_container'),
        testEnvContainer: document.getElementById('client_test_env_select_container'),
        logList: logList
    });

    // 创建状态轮询器实例
    const poller = new window.ServiceDeploy.StatusPoller();

    // 创建监听服务管理器实例
    const listenerServiceManager = new window.ServiceDeploy.ListenerServiceManager(
        listenerConnector,
        poller,
        logList
    );

    // 创建状态显示更新器实例
    const statusUpdater = new window.ServiceDeploy.StatusDisplayUpdater();

    // 创建日志管理器实例
    const logManager = new window.ServiceDeploy.LogManager(logList);

    // 监听代理连接事件，更新轮询器 URL
    window.addEventListener('agent:connected:listener', (e) => {
        poller.updateAgentUrls(e.detail.agentUrl, poller.clientAgentUrl);
        listenerAgentUrl = e.detail.agentUrl;
    });

    window.addEventListener('agent:connected:client', (e) => {
        poller.updateAgentUrls(poller.listenerAgentUrl, e.detail.agentUrl);
        clientAgentUrl = e.detail.agentUrl;
    });

    window.addEventListener('agent:disconnected:listener', (e) => {
        poller.updateAgentUrls('', poller.clientAgentUrl);
        listenerAgentUrl = '';
    });

    window.addEventListener('agent:disconnected:client', (e) => {
        poller.updateAgentUrls(poller.listenerAgentUrl, '');
        clientAgentUrl = '';
    });

    // ========== 使用新的模块化代码 ==========
    // 以下功能已迁移到 static/js/service_deploy.js:
    // - AgentConnector (代理连接器)
    // - StatusPoller (状态轮询器)
    // - ListenerServiceManager (监听服务管理器)
    // - StatusDisplayUpdater (状态显示更新器)
    // - LogManager (日志管理器)
    // - Utils (工具函数)

    // 保留向下兼容的变量引用
    let listenerAgentUrl = '';
    let clientAgentUrl = '';

    // ========== 兼容层：让旧代码能使用新模块的函数 ==========
    const addLogEntry = window.ServiceDeploy.Utils.addLogEntry.bind(window.ServiceDeploy.Utils);
    const showToast = window.ServiceDeploy.Utils.showToast.bind(window.ServiceDeploy.Utils);
    const escapeHtml = window.ServiceDeploy.Utils.escapeHtml.bind(window.ServiceDeploy.Utils);
    const getCookie = window.ServiceDeploy.Utils.getCookie.bind(window.ServiceDeploy.Utils);
    const generateRandomMac = window.ServiceDeploy.Utils.generateRandomMac.bind(window.ServiceDeploy.Utils);

    function sendClientCommand(protocol, action, extra = {}) {
        if (!clientAgentUrl) {
            addLogEntry('请先连接客户端代理程序', 'warning');
            return Promise.resolve({ success: false, error: '未连接客户端代理' });
        }
        const payload = { 
            agent_url: clientAgentUrl,  // 确保使用客户端代理URL
            protocol, 
            action, 
            ...extra 
        };
        
        console.log(`[DEBUG] sendClientCommand: protocol=${protocol}, action=${action}`);
        console.log(`[DEBUG] clientAgentUrl: ${clientAgentUrl}`);
        console.log(`[DEBUG] payload:`, payload);
        addLogEntry(`[调试] 发送请求到: ${clientAgentUrl}/api/services/client`, 'info');
        
        // FTP连接优化：使用较短的超时时间，因为后端已经优化了连接速度
        // 如果后端连接成功但响应慢，前端会通过状态轮询检测到
        // FTP下载需要更长的超时时间，因为可能需要传输大文件
        let timeout;
        if (protocol === 'ftp' && action === 'connect') {
            timeout = 15000;
        } else if (protocol === 'ftp' && action === 'download') {
            timeout = 60000;  // 下载操作需要60秒超时
        } else {
            timeout = 10000;
        }
        
        // 创建AbortController用于超时控制
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        return fetch('/api/services/client/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(payload),
            signal: controller.signal
        })
            .then(res => {
                clearTimeout(timeoutId);
                if (!res.ok) {
                    // 检查响应内容类型
                    const contentType = res.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        return res.json().then(data => {
                            throw new Error(data.error || `HTTP ${res.status}: ${res.statusText}`);
                        });
                    } else {
                        // 如果不是JSON，尝试读取文本
                        return res.text().then(text => {
                            throw new Error(`HTTP ${res.status}: ${res.statusText} - ${text.substring(0, 100)}`);
                        });
                    }
                }
                // 检查响应内容类型
                const contentType = res.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return res.json();
                } else {
                    // 如果不是JSON，尝试解析为文本
                    return res.text().then(text => {
                        try {
                            // 尝试解析JSON
                            return JSON.parse(text);
                        } catch (e) {
                            throw new Error(`响应不是有效的JSON: ${text.substring(0, 100)}`);
                        }
                    });
                }
            })
            .then(data => {
                if (data.success) {
                    // 等待后端返回结果后，立即更新状态
                    setTimeout(() => {
                        poller.fetchStatus();
                    }, 300);
                    // 再次延迟更新，确保状态同步
                    setTimeout(() => {
                        poller.fetchStatus();
                    }, 1000);

                    // 更新客户端按钮状态
                    if (protocol === 'tcp') {
                        const tcpStartBtn = document.getElementById('tcp_client_start');
                        const tcpStopBtn = document.getElementById('tcp_client_stop_send');
                        const tcpDisconnectBtn = document.getElementById('tcp_client_disconnect');

                        if (action === 'connect') {
                            if (tcpStartBtn) tcpStartBtn.disabled = false;
                            if (tcpDisconnectBtn) tcpDisconnectBtn.disabled = false;
                            addLogEntry('TCP 客户端连接成功，可以开始发送数据', 'success');
                        } else if (action === 'start_send') {
                            if (tcpStartBtn) tcpStartBtn.disabled = true;
                            if (tcpStopBtn) tcpStopBtn.disabled = false;
                            addLogEntry('TCP 客户端已开始发送数据', 'success');
                        } else if (action === 'stop_send') {
                            if (tcpStartBtn) tcpStartBtn.disabled = false;
                            if (tcpStopBtn) tcpStopBtn.disabled = true;
                            addLogEntry('TCP 客户端已停止发送数据', 'info');
                        } else if (action === 'disconnect') {
                            if (tcpStartBtn) tcpStartBtn.disabled = true;
                            if (tcpStopBtn) tcpStopBtn.disabled = true;
                            if (tcpDisconnectBtn) tcpDisconnectBtn.disabled = true;
                            addLogEntry('TCP 客户端已断开连接', 'info');
                        }
                    }

                    // UDP 客户端按钮状态更新
                    if (protocol === 'udp') {
                        const udpStartBtn = document.getElementById('udp_client_start');
                        const udpStopBtn = document.getElementById('udp_client_stop');
                        const udpStatus = document.getElementById('udp_client_status');

                        if (action === 'start') {
                            // UDP 开始发送
                            if (udpStartBtn) udpStartBtn.disabled = true;
                            if (udpStopBtn) udpStopBtn.disabled = false;
                            if (udpStatus) {
                                udpStatus.textContent = '发送中';
                                udpStatus.className = 'badge bg-success';
                            }
                            addLogEntry('UDP 客户端已开始发送数据', 'success');
                        } else if (action === 'stop') {
                            // UDP 停止发送
                            if (udpStartBtn) udpStartBtn.disabled = false;
                            if (udpStopBtn) udpStopBtn.disabled = true;
                            if (udpStatus) {
                                udpStatus.textContent = '未运行';
                                udpStatus.className = 'badge bg-secondary';
                            }
                            addLogEntry('UDP 客户端已停止发送', 'info');
                        }
                    }

                    // FTP 客户端按钮状态更新
                    if (protocol === 'ftp') {
                        const ftpConnectBtn = document.getElementById('ftp_client_connect');
                        const ftpDisconnectBtn = document.getElementById('ftp_client_disconnect');
                        const ftpStatus = document.getElementById('ftp_client_status');
                        const ftpRefreshDir = document.getElementById('ftp_client_refresh_dir');
                        const ftpRefreshFileList = document.getElementById('ftp_client_refresh_file_list');
                        const ftpUploadBtn = document.getElementById('ftp_client_upload_btn');
                        const ftpDownloadBtn = document.getElementById('ftp_client_download_btn');

                        if (action === 'connect') {
                            if (ftpConnectBtn) ftpConnectBtn.disabled = true;
                            if (ftpDisconnectBtn) ftpDisconnectBtn.disabled = false;
                            if (ftpStatus) {
                                ftpStatus.textContent = '已连接';
                                ftpStatus.className = 'badge bg-success';
                            }
                            if (ftpRefreshDir) ftpRefreshDir.disabled = false;
                            if (ftpRefreshFileList) ftpRefreshFileList.disabled = false;
                            if (ftpUploadBtn) ftpUploadBtn.disabled = false;
                            if (ftpDownloadBtn) ftpDownloadBtn.disabled = false;
                            addLogEntry('FTP 客户端连接成功', 'success');
                        } else if (action === 'disconnect') {
                            if (ftpConnectBtn) ftpConnectBtn.disabled = false;
                            if (ftpDisconnectBtn) ftpDisconnectBtn.disabled = true;
                            if (ftpStatus) {
                                ftpStatus.textContent = '未连接';
                                ftpStatus.className = 'badge bg-secondary';
                            }
                            if (ftpRefreshDir) ftpRefreshDir.disabled = true;
                            if (ftpRefreshFileList) ftpRefreshFileList.disabled = true;
                            if (ftpUploadBtn) ftpUploadBtn.disabled = true;
                            if (ftpDownloadBtn) ftpDownloadBtn.disabled = true;
                            addLogEntry('FTP 客户端已断开连接', 'info');
                        }
                    }

                    // HTTP 客户端按钮状态更新
                    if (protocol === 'http') {
                        const httpConnectBtn = document.getElementById('http_client_connect');
                        const httpDisconnectBtn = document.getElementById('http_client_disconnect');
                        const httpStatus = document.getElementById('http_client_status');
                        const httpRefreshFileList = document.getElementById('http_client_refresh_file_list');
                        const httpDownloadBtn = document.getElementById('http_client_download_btn');

                        if (action === 'connect') {
                            if (httpConnectBtn) httpConnectBtn.disabled = true;
                            if (httpDisconnectBtn) httpDisconnectBtn.disabled = false;
                            if (httpStatus) {
                                httpStatus.textContent = '已连接';
                                httpStatus.className = 'badge bg-success';
                            }
                            if (httpRefreshFileList) httpRefreshFileList.disabled = false;
                            if (httpDownloadBtn) httpDownloadBtn.disabled = false;
                            addLogEntry('HTTP 客户端连接成功', 'success');
                        } else if (action === 'disconnect') {
                            if (httpConnectBtn) httpConnectBtn.disabled = false;
                            if (httpDisconnectBtn) httpDisconnectBtn.disabled = true;
                            if (httpStatus) {
                                httpStatus.textContent = '未连接';
                                httpStatus.className = 'badge bg-secondary';
                            }
                            if (httpRefreshFileList) httpRefreshFileList.disabled = true;
                            if (httpDownloadBtn) httpDownloadBtn.disabled = true;
                            addLogEntry('HTTP 客户端已断开连接', 'info');
                        }
                    }
                } else {
                    addLogEntry(data.error || '操作失败', 'error');
                }
                return data;
            })
            .catch(err => {
                clearTimeout(timeoutId);
                if (err.name === 'AbortError') {
                    addLogEntry(`操作超时（${timeout/1000}秒）`, 'error');
                    return { success: false, error: `操作超时（${timeout/1000}秒）` };
                } else {
                    addLogEntry(`客户端操作失败: ${err.message}`, 'error');
                    return { success: false, error: err.message };
                }
            });
    }

    function collectTcpClientConfig() {
        return {
            server_ip: document.getElementById('tcp_client_server')?.value || '',
            server_port: parseInt(document.getElementById('tcp_client_port')?.value || '0', 10),
            connections: parseInt(document.getElementById('tcp_client_connections')?.value || '1', 10),
            connect_rate: parseFloat(document.getElementById('tcp_client_rate')?.value || '1'),
            send_interval: parseFloat(document.getElementById('tcp_client_interval')?.value || '1'),
            message: document.getElementById('tcp_client_message')?.value || ''
        };
    }

    function collectUdpClientConfig() {
        return {
            server_ip: document.getElementById('udp_client_server')?.value || '',
            server_port: parseInt(document.getElementById('udp_client_port')?.value || '0', 10),
            connections: parseInt(document.getElementById('udp_client_connections')?.value || '1', 10),
            send_interval: parseFloat(document.getElementById('udp_client_interval')?.value || '1'),
            message: document.getElementById('udp_client_message')?.value || ''
        };
    }

    function collectFtpClientConfig() {
        return {
            server_ip: document.getElementById('ftp_client_server')?.value || '',
            server_port: parseInt(document.getElementById('ftp_client_port')?.value || '21', 10),
            username: document.getElementById('ftp_client_username')?.value || 'tdhx',
            password: document.getElementById('ftp_client_password')?.value || 'tdhx@2017'
        };
    }

    function collectHttpClientConfig() {
        return {
            server_ip: document.getElementById('http_client_server')?.value || '',
            server_port: parseInt(document.getElementById('http_client_port')?.value || '80', 10)
        };
    }

    function validateAddress(config) {
        if (!config.server_ip) {
            addLogEntry('请输入服务器地址', 'warning');
            return false;
        }
        if (!config.server_port || config.server_port < 1 || config.server_port > 65535) {
            addLogEntry('服务器端口无效', 'warning');
            return false;
        }
        return true;
    }

    // 测试环境列表
    let testEnvironments = [];

    // 加载测试环境列表
    function loadTestEnvironments() {
        console.log('开始加载测试环境列表...');
        fetch('/api/test_env/list/')
            .then(response => {
                console.log('API 响应状态:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('API 返回数据:', data);
                if (data.success) {
                    const envs = data.environments.map(env => ({
                        id: env.id.toString(),
                        name: env.name,
                        ip: env.ip,
                        type: env.type,
                        user: env.ssh_user,
                        password: env.ssh_password,
                        agentPort: 8888  // Agent 程序固定使用 8888 端口
                    }));
                    testEnvironments = envs;
                    console.log('加载测试环境:', envs.length, '个');

                    // 监听服务代理的测试环境选择
                    const listenerSelect = document.getElementById('listener_test_env_select');
                    if (listenerSelect) {
                        listenerSelect.innerHTML = '<option value="">请选择测试环境</option>';
                        if (envs.length === 0) {
                            listenerSelect.innerHTML += '<option value="">暂无测试环境</option>';
                        }
                        envs.forEach(env => {
                            const option = document.createElement('option');
                            option.value = env.ip;
                            option.dataset.envIp = env.ip;
                            option.dataset.port = env.agentPort;
                            option.textContent = `${env.name} (${env.ip}) - ${env.type === 'windows' ? 'Windows' : 'Linux'}`;
                            listenerSelect.appendChild(option);
                        });
                        console.log('监听服务代理测试环境列表已更新:', listenerSelect.options.length, '个选项');
                    } else {
                        console.warn('未找到 listener_test_env_select 元素');
                    }

                    // 客户端代理的测试环境选择
                    const clientSelect = document.getElementById('client_test_env_select');
                    if (clientSelect) {
                        clientSelect.innerHTML = '<option value="">请选择测试环境</option>';
                        if (envs.length === 0) {
                            clientSelect.innerHTML += '<option value="">暂无测试环境</option>';
                        }
                        envs.forEach(env => {
                            const option = document.createElement('option');
                            option.value = env.ip;
                            option.dataset.envIp = env.ip;
                            option.dataset.port = env.agentPort;
                            option.textContent = `${env.name} (${env.ip}) - ${env.type === 'windows' ? 'Windows' : 'Linux'}`;
                            clientSelect.appendChild(option);
                        });
                        console.log('客户端代理测试环境列表已更新:', clientSelect.options.length, '个选项');
                    } else {
                        console.warn('未找到 client_test_env_select 元素');
                    }
                } else {
                    console.error('加载测试环境失败：', data.error);
                    addLogEntry(`加载测试环境失败：${data.error}`, 'error');
                }
            })
            .catch(err => {
                console.error('加载测试环境网络错误:', err);
                addLogEntry(`加载测试环境网络错误：${err.message}`, 'error');
            });
    }
    
    // 监听服务代理IP来源切换
    document.querySelectorAll('input[name="listener_agent_source"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const isTestEnv = this.value === 'test_env';
            const testEnvContainer = document.getElementById('listener_test_env_select_container');
            const customIpContainer = document.getElementById('listener_custom_ip_container');
            if (testEnvContainer) testEnvContainer.style.display = isTestEnv ? 'block' : 'none';
            if (customIpContainer) customIpContainer.style.display = isTestEnv ? 'none' : 'block';
            const portContainer = document.getElementById('listener_agent_port_container');
            if (portContainer) portContainer.style.display = 'none'; // 端口始终隐藏，默认8888
        });
    });
    
    // 客户端代理IP来源切换
    document.querySelectorAll('input[name="client_agent_source"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const isTestEnv = this.value === 'test_env';
            const testEnvContainer = document.getElementById('client_test_env_select_container');
            const customIpContainer = document.getElementById('client_custom_ip_container');
            if (testEnvContainer) testEnvContainer.style.display = isTestEnv ? 'block' : 'none';
            if (customIpContainer) customIpContainer.style.display = isTestEnv ? 'none' : 'block';
            const portContainer = document.getElementById('client_agent_port_container');
            if (portContainer) portContainer.style.display = 'none'; // 端口始终隐藏，默认8888
        });
    });
    
    // 启动本地邮件服务按钮
    document.getElementById('start_local_mail_service_btn')?.addEventListener('click', () => {
        startLocalMailService();
    });

    // TCP客户端连接按钮
    document.getElementById('tcp_client_connect')?.addEventListener('click', () => {
        const config = collectTcpClientConfig();
        if (!validateAddress(config)) return;
        sendClientCommand('tcp', 'connect', config);
    });

    // TCP客户端开始发送按钮
    document.getElementById('tcp_client_start')?.addEventListener('click', () => {
        const config = collectTcpClientConfig();
        sendClientCommand('tcp', 'start_send', config);
    });

    // TCP客户端停止发送按钮
    document.getElementById('tcp_client_stop_send')?.addEventListener('click', () => {
        sendClientCommand('tcp', 'stop_send');
    });

    // TCP客户端断开连接按钮
    document.getElementById('tcp_client_disconnect')?.addEventListener('click', () => {
        sendClientCommand('tcp', 'disconnect');
    });

    document.getElementById('udp_client_start')?.addEventListener('click', () => {
        const config = collectUdpClientConfig();
        if (!validateAddress(config)) return;
        sendClientCommand('udp', 'start', config);
    });

    document.getElementById('udp_client_stop')?.addEventListener('click', () => {
        sendClientCommand('udp', 'stop');
    });

    // FTP客户端连接按钮
    document.getElementById('ftp_client_connect')?.addEventListener('click', () => {
        const config = collectFtpClientConfig();
        if (!validateAddress(config)) return;
        
        const connectBtn = document.getElementById('ftp_client_connect');
        const originalText = connectBtn.innerHTML;
        connectBtn.disabled = true;
        connectBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>连接中...';
        addLogEntry('正在连接FTP服务器...', 'info');
        
        // 标记正在连接，用于状态轮询判断
        let isConnecting = true;
        let connectionCheckCount = 0;
        const maxCheckCount = 10; // 最多检查10次（50秒）
        
        // 超时后继续检查连接状态的函数
        const checkConnectionStatus = () => {
            if (!isConnecting) return;
            connectionCheckCount++;
            if (connectionCheckCount > maxCheckCount) {
                // 超过最大检查次数，停止检查
                isConnecting = false;
                connectBtn.innerHTML = originalText;
                connectBtn.disabled = false;
                addLogEntry('连接超时，请检查网络或FTP服务器状态', 'error');
                return;
            }
            
            // 检查状态（异步，不阻塞）
            poller.poller.fetchStatus();
            
            // 等待状态更新后再检查（给fetchStatus一些时间完成）
            setTimeout(() => {
                // 检查是否已连接（直接检查状态徽章）
                const ftpStatus = document.getElementById('ftp_client_status');
                if (ftpStatus && (ftpStatus.textContent === '已连接' || ftpStatus.classList.contains('bg-success'))) {
                // 连接成功，更新UI
                isConnecting = false;
                connectBtn.innerHTML = originalText;
                connectBtn.disabled = true;
                document.getElementById('ftp_client_disconnect').disabled = false;
                document.getElementById('ftp_client_refresh_dir').disabled = false;
                document.getElementById('ftp_client_refresh_file_list').disabled = false;
                document.getElementById('ftp_client_refresh_local_files').disabled = false;
                document.getElementById('ftp_client_upload_btn').disabled = false;
                document.getElementById('ftp_client_download_btn').disabled = false;
                addLogEntry('FTP连接成功（检测到连接状态）', 'success');
                // 刷新文件列表
                setTimeout(() => {
                    refreshFtpFileList();
                    refreshLocalFileList();
                }, 500);
                } else {
                    // 继续检查
                    setTimeout(checkConnectionStatus, 3000);  // 缩短检查间隔到3秒
                }
            }, 500);  // 等待500ms让fetchStatus完成
        };
        
        sendClientCommand('ftp', 'connect', config).then(data => {
            isConnecting = false;
            connectBtn.innerHTML = originalText;
            if (data && data.success) {
                if (data.current_dir) {
                    document.getElementById('ftp_client_current_dir').value = data.current_dir;
                }
                // 等待后端返回结果后，立即更新状态
                setTimeout(() => {
                    poller.fetchStatus();
                }, 300);
                setTimeout(() => {
                    poller.fetchStatus();
                }, 1000);
                connectBtn.disabled = true;
                document.getElementById('ftp_client_disconnect').disabled = false;
                document.getElementById('ftp_client_refresh_dir').disabled = false;
                document.getElementById('ftp_client_refresh_file_list').disabled = false;
                document.getElementById('ftp_client_refresh_local_files').disabled = false;
                document.getElementById('ftp_client_upload_btn').disabled = false;
                document.getElementById('ftp_client_download_btn').disabled = false;
                addLogEntry('FTP连接成功', 'success');
                // 连接成功后自动刷新服务器文件列表和本地文件列表
                setTimeout(() => {
                    // 如果返回了文件列表，直接显示
                    if (data.file_list) {
                        displayFtpFileList(data.file_list);
                    } else {
                        refreshFtpFileList();
                    }
                    refreshLocalFileList();
                }, 300);
            } else {
                connectBtn.disabled = false;
                addLogEntry(data?.error || '连接失败', 'error');
            }
        }).catch(err => {
            // 超时后不立即恢复按钮，而是继续检查连接状态
            if (err.name === 'AbortError' || err.message.includes('超时')) {
                addLogEntry('请求超时，正在检查连接状态...', 'warning');
                // 延迟开始检查，给后端一些时间完成连接
                setTimeout(checkConnectionStatus, 2000);
            } else {
                isConnecting = false;
                connectBtn.innerHTML = originalText;
                connectBtn.disabled = false;
                addLogEntry(`连接失败: ${err.message}`, 'error');
            }
        });
    });
    
    // 显示FTP文件列表（从数据直接显示，不重新获取）
    function displayFtpFileList(fileListText) {
        const fileListDiv = document.getElementById('ftp_client_file_list');
        if (!fileListDiv) return;
        
        const files = parseFtpFileList(fileListText || '');
        if (files.length > 0) {
            fileListDiv.innerHTML = files.map((file, index) => {
                const icon = file.isDir ? 'fa-folder' : 'fa-file';
                const iconColor = file.isDir ? 'text-warning' : 'text-primary';
                return `
                    <div class="d-flex justify-content-between align-items-center mb-1 p-1 border-bottom">
                        <div class="flex-grow-1">
                            <i class="fas ${icon} ${iconColor} me-2"></i>
                            <span class="small">${escapeHtml(file.name)}</span>
                        </div>
                        ${!file.isDir ? `<button class="btn btn-sm btn-outline-success ftp-download-btn" data-filename="${escapeHtml(file.name)}" data-index="${index}">
                            <i class="fas fa-download"></i> 下载
                        </button>` : ''}
                    </div>
                `;
            }).join('');
            // 为所有下载按钮添加事件监听
            fileListDiv.querySelectorAll('.ftp-download-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const filename = btn.getAttribute('data-filename');
                    if (filename) {
                        downloadFtpFile(filename);
                    }
                });
            });
        } else {
            fileListDiv.innerHTML = '<div class="text-muted text-center">目录为空</div>';
        }
    }

    // FTP客户端断开按钮
    document.getElementById('ftp_client_disconnect')?.addEventListener('click', () => {
        sendClientCommand('ftp', 'disconnect').then(() => {
            // 等待后端返回结果后，立即更新状态
            setTimeout(() => {
                poller.fetchStatus();
            }, 300);
            setTimeout(() => {
                poller.fetchStatus();
            }, 1000);
            document.getElementById('ftp_client_connect').disabled = false;
            document.getElementById('ftp_client_disconnect').disabled = true;
            document.getElementById('ftp_client_refresh_dir').disabled = true;
            document.getElementById('ftp_client_refresh_file_list').disabled = true;
            document.getElementById('ftp_client_refresh_local_files').disabled = true;
            document.getElementById('ftp_client_upload_btn').disabled = true;
            document.getElementById('ftp_client_download_btn').disabled = true;
            document.getElementById('ftp_client_file_list').innerHTML = '<div class="text-muted text-center">未连接</div>';
            document.getElementById('ftp_client_local_file_list').innerHTML = '<div class="text-muted text-center small">未连接</div>';
        });
    });

    // 解析FTP文件列表行，提取文件名
    function parseFtpFileList(fileListText) {
        const files = [];
        const lines = fileListText.split('\n').filter(f => f.trim());
        for (const line of lines) {
            // FTP LIST格式示例: "-rw-rw-rw- 1 user user 1024 Jan 1 00:00 test.txt"
            // 或者: "drwxrwxrwx 1 user user 4096 Jan 1 00:00 directory"
            const parts = line.trim().split(/\s+/);
            if (parts.length >= 9) {
                const filename = parts.slice(8).join(' '); // 文件名可能包含空格
                const isDir = parts[0].startsWith('d');
                files.push({ name: filename, isDir: isDir, line: line });
            } else if (parts.length > 0) {
                // 如果解析失败，使用整行作为文件名
                files.push({ name: line.trim(), isDir: false, line: line });
            }
        }
        return files;
    }

    // 刷新文件列表
    function refreshFtpFileList() {
        sendClientCommand('ftp', 'list').then(data => {
            if (data && data.success && data.files !== undefined) {
                const fileListDiv = document.getElementById('ftp_client_file_list');
                if (fileListDiv) {
                    const files = parseFtpFileList(data.files || '');
                    if (files.length > 0) {
                        fileListDiv.innerHTML = files.map((file, index) => {
                            const icon = file.isDir ? 'fa-folder' : 'fa-file';
                            const iconColor = file.isDir ? 'text-warning' : 'text-primary';
                            return `
                                <div class="d-flex justify-content-between align-items-center mb-1 p-1 border-bottom">
                                    <div class="flex-grow-1">
                                        <i class="fas ${icon} ${iconColor} me-2"></i>
                                        <span class="small">${escapeHtml(file.name)}</span>
                                    </div>
                                    ${!file.isDir ? `<button class="btn btn-sm btn-outline-success ftp-download-btn" data-filename="${escapeHtml(file.name)}" data-index="${index}">
                                        <i class="fas fa-download"></i> 下载
                                    </button>` : ''}
                                </div>
                            `;
                        }).join('');
                        // 为所有下载按钮添加事件监听
                        fileListDiv.querySelectorAll('.ftp-download-btn').forEach(btn => {
                            btn.addEventListener('click', () => {
                                const filename = btn.getAttribute('data-filename');
                                if (filename) {
                                    downloadFtpFile(filename);
                                }
                            });
                        });
                    } else {
                        fileListDiv.innerHTML = '<div class="text-muted text-center">目录为空</div>';
                    }
                }
                if (data.current_dir) {
                    document.getElementById('ftp_client_current_dir').value = data.current_dir;
                }
            }
        });
    }

    // 下载FTP文件
    function downloadFtpFile(filename) {
        sendClientCommand('ftp', 'download', { filename }).then(data => {
            const downloadContentDiv = document.getElementById('ftp_client_download_content');
            if (data && data.success) {
                // 只显示文件名、文件大小和成功状态
                const fileSize = data.file_size ? ` (${formatFileSize(data.file_size)})` : '';
                const status = '<span class="text-success">✓ 下载成功</span>';
                if (downloadContentDiv) {
                    downloadContentDiv.innerHTML = `
                        <div class="mb-2">
                            <strong>文件名:</strong> ${escapeHtml(filename)}${fileSize}<br>
                            <strong>状态:</strong> ${status}
                        </div>
                    `;
                }
                // 更新下载文件名输入框
                document.getElementById('ftp_client_download_file').value = filename;
                addLogEntry(`下载成功: ${filename}${fileSize}`, 'success');
            } else {
                const status = '<span class="text-danger">✗ 下载失败</span>';
                if (downloadContentDiv) {
                    downloadContentDiv.innerHTML = `
                        <div class="mb-2">
                            <strong>文件名:</strong> ${escapeHtml(filename)}<br>
                            <strong>状态:</strong> ${status}<br>
                            <strong>错误:</strong> ${escapeHtml(data?.error || '未知错误')}
                        </div>
                    `;
                }
                addLogEntry(`下载失败: ${filename} - ${data?.error || '未知错误'}`, 'error');
            }
        }).catch(err => {
            const downloadContentDiv = document.getElementById('ftp_client_download_content');
            const status = '<span class="text-danger">✗ 下载失败</span>';
            if (downloadContentDiv) {
                downloadContentDiv.innerHTML = `
                    <div class="mb-2">
                        <strong>文件名:</strong> ${escapeHtml(filename)}<br>
                        <strong>状态:</strong> ${status}<br>
                        <strong>错误:</strong> ${escapeHtml(err.message)}
                    </div>
                `;
            }
            addLogEntry(`下载失败: ${filename} - ${err.message}`, 'error');
        });
    }
    
    // FTP客户端刷新目录按钮（刷新当前目录显示）
    document.getElementById('ftp_client_refresh_dir')?.addEventListener('click', () => {
        refreshFtpFileList();
    });

    // FTP客户端刷新文件列表按钮
    document.getElementById('ftp_client_refresh_file_list')?.addEventListener('click', () => {
        refreshFtpFileList();
    });

    // 刷新本地文件列表
    function refreshLocalFileList() {
        sendClientCommand('ftp', 'get_local_files', {}).then(data => {
            if (data && data.success && data.files) {
                const localFileListDiv = document.getElementById('ftp_client_local_file_list');
                if (localFileListDiv) {
                    const files = data.files || [];
                    if (files.length > 0) {
                        localFileListDiv.innerHTML = files.map(file => {
                            const icon = file.is_dir ? 'fa-folder' : 'fa-file';
                            const iconColor = file.is_dir ? 'text-warning' : 'text-primary';
                            const size = file.is_dir ? '' : ` (${formatFileSize(file.size)})`;
                            return `
                                <div class="d-flex justify-content-between align-items-center mb-1 p-1 border-bottom ${file.is_dir ? '' : 'local-file-item'}" 
                                     style="cursor: ${file.is_dir ? 'default' : 'pointer'};"
                                     ${!file.is_dir ? `data-filename="${escapeHtml(file.name)}"` : ''}>
                                    <div class="flex-grow-1">
                                        <i class="fas ${icon} ${iconColor} me-2"></i>
                                        <span class="small">${escapeHtml(file.name)}${size}</span>
                                    </div>
                                </div>
                            `;
                        }).join('');
                        // 为所有本地文件项添加点击事件
                        localFileListDiv.querySelectorAll('.local-file-item').forEach(item => {
                            item.addEventListener('click', function(e) {
                                const filename = this.getAttribute('data-filename');
                                if (filename) {
                                    // 高亮选中的文件
                                    document.querySelectorAll('.local-file-item').forEach(i => {
                                        i.classList.remove('active', 'bg-light');
                                    });
                                    this.classList.add('active', 'bg-light');
                                    selectLocalFile(filename);
                                }
                            });
                        });
                    } else {
                        localFileListDiv.innerHTML = '<div class="text-muted text-center small">目录为空</div>';
                    }
                }
            } else {
                const localFileListDiv = document.getElementById('ftp_client_local_file_list');
                if (localFileListDiv) {
                    localFileListDiv.innerHTML = `<div class="text-muted text-center small">${data?.error || '获取文件列表失败'}</div>`;
                }
            }
        });
    }

    // 选择本地文件
    function selectLocalFile(filename) {
        // 设置服务器文件名为本地文件名（可以修改）
        document.getElementById('ftp_client_upload_file').value = filename;
        addLogEntry(`已选择本地文件: ${filename}`, 'info');
    }

    // FTP客户端刷新本地文件列表按钮
    document.getElementById('ftp_client_refresh_local_files')?.addEventListener('click', () => {
        refreshLocalFileList();
    });

    // FTP客户端上传按钮
    document.getElementById('ftp_client_upload_btn')?.addEventListener('click', () => {
        const filename = document.getElementById('ftp_client_upload_file')?.value.trim();
        if (!filename) {
            addLogEntry('请输入服务器文件名', 'warning');
            return;
        }
        
        // 从本地文件列表获取选中的文件
        const selectedLocalFile = document.querySelector('.local-file-item.active');
        let localFilePath = '';
        if (selectedLocalFile) {
            // 提取文件名（去除图标和大小信息）
            const fileText = selectedLocalFile.textContent.trim();
            const localFileName = fileText.split('(')[0].trim();
            localFilePath = localFileName;
        }
        
        // 如果指定了本地文件路径，使用本地文件上传
        if (localFilePath) {
            const uploadBtn = document.getElementById('ftp_client_upload_btn');
            const originalText = uploadBtn.innerHTML;
            uploadBtn.disabled = true;
            uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>上传中...';
            
            sendClientCommand('ftp', 'upload', { filename, local_file_path: localFilePath }).then(data => {
                uploadBtn.innerHTML = originalText;
                uploadBtn.disabled = false;
                if (data && data.success) {
                    addLogEntry(`上传成功: ${filename}`, 'success');
                    // 上传成功后刷新文件列表
                    setTimeout(() => {
                        refreshFtpFileList();
                        refreshLocalFileList();
                    }, 500);
                } else {
                    addLogEntry(data?.error || '上传失败', 'error');
                }
            }).catch(err => {
                uploadBtn.innerHTML = originalText;
                uploadBtn.disabled = false;
                addLogEntry(`上传失败: ${err.message}`, 'error');
            });
        } else {
            // 如果没有选择本地文件，提示用户选择
            addLogEntry('请先从本地文件列表中选择要上传的文件', 'warning');
        }
    });

    // FTP客户端下载按钮
    document.getElementById('ftp_client_download_btn')?.addEventListener('click', () => {
        const filename = document.getElementById('ftp_client_download_file')?.value.trim();
        if (!filename) {
            addLogEntry('请输入文件名', 'warning');
            return;
        }
        
        const downloadBtn = document.getElementById('ftp_client_download_btn');
        const originalText = downloadBtn.innerHTML;
        downloadBtn.disabled = true;
        downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>下载中...';
        addLogEntry(`正在下载文件: ${filename}`, 'info');
        
        sendClientCommand('ftp', 'download', { filename }).then(data => {
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;
            const downloadContentDiv = document.getElementById('ftp_client_download_content');
            
            if (data && data.success) {
                // 只显示文件名、文件大小和成功状态
                const fileSize = data.file_size ? ` (${formatFileSize(data.file_size)})` : '';
                const status = '<span class="text-success">✓ 下载成功</span>';
                if (downloadContentDiv) {
                    downloadContentDiv.innerHTML = `
                        <div class="mb-2">
                            <strong>文件名:</strong> ${escapeHtml(filename)}${fileSize}<br>
                            <strong>状态:</strong> ${status}
                        </div>
                    `;
                }
                // 更新下载文件名输入框
                document.getElementById('ftp_client_download_file').value = filename;
                addLogEntry(`下载成功: ${filename}${fileSize}`, 'success');
            } else {
                const status = '<span class="text-danger">✗ 下载失败</span>';
                if (downloadContentDiv) {
                    downloadContentDiv.innerHTML = `
                        <div class="mb-2">
                            <strong>文件名:</strong> ${escapeHtml(filename)}<br>
                            <strong>状态:</strong> ${status}<br>
                            <strong>错误:</strong> ${escapeHtml(data?.error || '未知错误')}
                        </div>
                    `;
                }
                addLogEntry(`下载失败: ${filename} - ${data?.error || '未知错误'}`, 'error');
            }
        }).catch(err => {
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;
            const downloadContentDiv = document.getElementById('ftp_client_download_content');
            const status = '<span class="text-danger">✗ 下载失败</span>';
            if (downloadContentDiv) {
                downloadContentDiv.innerHTML = `
                    <div class="mb-2">
                        <strong>文件名:</strong> ${escapeHtml(filename)}<br>
                        <strong>状态:</strong> ${status}<br>
                        <strong>错误:</strong> ${escapeHtml(err.message)}
                    </div>
                `;
            }
            addLogEntry(`下载失败: ${filename} - ${err.message}`, 'error');
        });
    });

    document.getElementById('tcp_connection_table')?.addEventListener('click', (event) => {
        const target = event.target;
        if (target && target.dataset.action === 'disconnect') {
            const connId = target.dataset.conn;
            if (connId) {
                sendClientCommand('tcp', 'disconnect', { connection_id: connId });
            }
        }
    });

    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', () => {
            // 清空前端日志显示
            if (logList) {
                logList.innerHTML = '<li class="list-group-item text-muted text-center">日志已清空</li>';
            }
            // 通知后端清空日志（如果后端支持）
            // 这里只是清空前端显示，后端日志会继续记录
        });
    }

    
    // 刷新HTTP文件列表
    function refreshHttpFileList() {
        sendClientCommand('http', 'list').then(data => {
            if (data && data.success && data.files) {
                const fileListDiv = document.getElementById('http_client_file_list');
                if (fileListDiv) {
                    const files = data.files || [];
                    if (files.length > 0) {
                        fileListDiv.innerHTML = files.map((file, index) => {
                            const icon = file.is_dir ? 'fa-folder' : 'fa-file';
                            const iconColor = file.is_dir ? 'text-warning' : 'text-primary';
                            const size = file.is_dir ? '' : ` (${formatFileSize(file.size)})`;
                            return `
                                <div class="d-flex justify-content-between align-items-center mb-1 p-1 border-bottom ${file.is_dir ? '' : 'http-file-item'}" 
                                     style="cursor: ${file.is_dir ? 'default' : 'pointer'};"
                                     ${!file.is_dir ? `data-filename="${escapeHtml(file.name)}"` : ''}>
                                    <div class="flex-grow-1">
                                        <i class="fas ${icon} ${iconColor} me-2"></i>
                                        <span class="small">${escapeHtml(file.name)}${size}</span>
                                    </div>
                                    ${!file.is_dir ? `<button class="btn btn-sm btn-outline-success http-download-btn" data-filename="${escapeHtml(file.name)}">
                                        <i class="fas fa-download"></i> 下载
                                    </button>` : ''}
                                </div>
                            `;
                        }).join('');
                        // 为所有下载按钮添加事件监听
                        fileListDiv.querySelectorAll('.http-download-btn').forEach(btn => {
                            btn.addEventListener('click', () => {
                                const filename = btn.getAttribute('data-filename');
                                if (filename) {
                                    downloadHttpFile(filename);
                                }
                            });
                        });
                        // 为所有文件项添加点击事件
                        fileListDiv.querySelectorAll('.http-file-item').forEach(item => {
                            item.addEventListener('click', function() {
                                const filename = this.getAttribute('data-filename');
                                if (filename) {
                                    document.getElementById('http_client_download_file').value = filename;
                                }
                            });
                        });
                    } else {
                        fileListDiv.innerHTML = '<div class="text-muted text-center">目录为空</div>';
                    }
                }
            }
        });
    }
    
    // 下载HTTP文件
    function downloadHttpFile(filename) {
        const downloadBtn = document.getElementById('http_client_download_btn');
        const originalText = downloadBtn.innerHTML;
        downloadBtn.disabled = true;
        downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>下载中...';
        addLogEntry(`正在下载文件: ${filename}`, 'info');
        
        sendClientCommand('http', 'download', { filename }).then(data => {
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;
            const downloadContentDiv = document.getElementById('http_client_download_content');
            
            if (data && data.success) {
                const fileSize = data.file_size ? ` (${formatFileSize(data.file_size)})` : '';
                const status = '<span class="text-success">✓ 下载成功</span>';
                if (downloadContentDiv) {
                    downloadContentDiv.innerHTML = `
                        <div class="mb-2">
                            <strong>文件名:</strong> ${escapeHtml(filename)}${fileSize}<br>
                            <strong>状态:</strong> ${status}
                        </div>
                    `;
                }
                document.getElementById('http_client_download_file').value = filename;
                addLogEntry(`下载成功: ${filename}${fileSize}`, 'success');
            } else {
                const status = '<span class="text-danger">✗ 下载失败</span>';
                if (downloadContentDiv) {
                    downloadContentDiv.innerHTML = `
                        <div class="mb-2">
                            <strong>文件名:</strong> ${escapeHtml(filename)}<br>
                            <strong>状态:</strong> ${status}<br>
                            <strong>错误:</strong> ${escapeHtml(data?.error || '未知错误')}
                        </div>
                    `;
                }
                addLogEntry(`下载失败: ${filename} - ${data?.error || '未知错误'}`, 'error');
            }
        }).catch(err => {
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;
            const downloadContentDiv = document.getElementById('http_client_download_content');
            const status = '<span class="text-danger">✗ 下载失败</span>';
            if (downloadContentDiv) {
                downloadContentDiv.innerHTML = `
                    <div class="mb-2">
                        <strong>文件名:</strong> ${escapeHtml(filename)}<br>
                        <strong>状态:</strong> ${status}<br>
                        <strong>错误:</strong> ${escapeHtml(err.message)}
                    </div>
                `;
            }
            addLogEntry(`下载失败: ${filename} - ${err.message}`, 'error');
        });
    }
    
    // HTTP客户端连接按钮
    document.getElementById('http_client_connect')?.addEventListener('click', () => {
        const config = collectHttpClientConfig();
        if (!validateAddress(config)) return;
        
        const connectBtn = document.getElementById('http_client_connect');
        const originalText = connectBtn.innerHTML;
        connectBtn.disabled = true;
        connectBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>连接中...';
        addLogEntry('正在连接HTTP服务器...', 'info');
        
        console.log('[DEBUG] HTTP客户端连接配置:', config);
        addLogEntry(`尝试连接HTTP服务器: ${config.server_ip}:${config.server_port}`, 'info');
        
        sendClientCommand('http', 'connect', config).then(data => {
            connectBtn.innerHTML = originalText;
            console.log('[DEBUG] HTTP客户端连接响应:', data);
            if (data && data.success) {
                connectBtn.disabled = true;
                document.getElementById('http_client_disconnect').disabled = false;
                document.getElementById('http_client_refresh_file_list').disabled = false;
                document.getElementById('http_client_download_btn').disabled = false;
                addLogEntry('HTTP连接成功', 'success');
                setTimeout(() => {
                    refreshHttpFileList();
                }, 300);
            } else {
                connectBtn.disabled = false;
                addLogEntry(data?.error || '连接失败', 'error');
            }
        }).catch(err => {
            connectBtn.innerHTML = originalText;
            connectBtn.disabled = false;
            addLogEntry(`连接失败: ${err.message}`, 'error');
        });
    });
    
    // HTTP客户端断开按钮
    document.getElementById('http_client_disconnect')?.addEventListener('click', () => {
        sendClientCommand('http', 'disconnect').then(() => {
            setTimeout(() => {
                poller.fetchStatus();
            }, 300);
            document.getElementById('http_client_connect').disabled = false;
            document.getElementById('http_client_disconnect').disabled = true;
            document.getElementById('http_client_refresh_file_list').disabled = true;
            document.getElementById('http_client_download_btn').disabled = true;
            document.getElementById('http_client_file_list').innerHTML = '<div class="text-muted text-center">未连接</div>';
        });
    });
    
    // HTTP客户端刷新文件列表按钮
    document.getElementById('http_client_refresh_file_list')?.addEventListener('click', () => {
        refreshHttpFileList();
    });
    
    // HTTP客户端下载按钮
    document.getElementById('http_client_download_btn')?.addEventListener('click', () => {
        const filename = document.getElementById('http_client_download_file')?.value.trim();
        if (!filename) {
            addLogEntry('请输入文件名', 'warning');
            return;
        }
        downloadHttpFile(filename);
    });
    
    // 页面加载时初始化
    loadTestEnvironments();
    
    // 初始化显示状态：根据默认选中的radio设置显示
    setTimeout(function() {
        const listenerSource = document.querySelector('input[name="listener_agent_source"]:checked')?.value || 'test_env';
        const isListenerTestEnv = listenerSource === 'test_env';
        const listenerTestEnvContainer = document.getElementById('listener_test_env_select_container');
        const listenerCustomIpContainer = document.getElementById('listener_custom_ip_container');
        if (listenerTestEnvContainer) listenerTestEnvContainer.style.display = isListenerTestEnv ? 'block' : 'none';
        if (listenerCustomIpContainer) listenerCustomIpContainer.style.display = isListenerTestEnv ? 'none' : 'block';
        
        const clientSource = document.querySelector('input[name="client_agent_source"]:checked')?.value || 'test_env';
        const isClientTestEnv = clientSource === 'test_env';
        const clientTestEnvContainer = document.getElementById('client_test_env_select_container');
        const clientCustomIpContainer = document.getElementById('client_custom_ip_container');
        if (clientTestEnvContainer) clientTestEnvContainer.style.display = isClientTestEnv ? 'block' : 'none';
        if (clientCustomIpContainer) clientCustomIpContainer.style.display = isClientTestEnv ? 'none' : 'block';
    }, 100);
    
    // 监听localStorage变化，当测试环境更新时刷新列表
    window.addEventListener('storage', function(e) {
        if (e.key === 'test_environments') {
            loadTestEnvironments();
        }
    });
    
    // 设置邮件服务器默认端口
    document.getElementById('mail_listener_smtp_port').value = '25';
    document.getElementById('mail_listener_imap_port').value = '143';
    document.getElementById('mail_listener_pop3_port').value = '110';
    
    // 添加邮箱账户
    document.getElementById('add_mail_account_btn').addEventListener('click', function() {
        console.log('*** 添加账户按钮被点击 ***');
        console.log('*** 点击前mailAccounts长度:', mailAccounts.length);
        addLogEntry('正在添加邮箱账户...', 'info');
        
        const username = document.getElementById('mail_account_username').value.trim();
        const password = document.getElementById('mail_account_password').value.trim();
        const domain = document.getElementById('mail_listener_domain').value.trim() || 'autotest.com';
        
        console.log('用户名:', username, '密码:', password, '域名:', domain);
        
        if (!username || !password) {
            addLogEntry('请输入用户名和密码', 'warning');
            return;
        }
        
        const email = `${username}@${domain}`;
        addMailAccount(email, username, password);
        
        // 清空输入框
        document.getElementById('mail_account_username').value = '';
        document.getElementById('mail_account_password').value = '';
    });
    
    // 邮箱账户存储 (临时存储，实际应用中需要更安全的方式)
    let mailAccounts = [];
    console.log('*** mailAccounts初始化完成 ***');
    
    // 添加邮箱账户到列表
    function addMailAccount(email, username, password) {
        const tableBody = document.getElementById('mail_accounts_list');
        
        // 检查是否已存在
        const existingAccount = mailAccounts.find(acc => acc.email === email);
        if (existingAccount) {
            addLogEntry(`邮箱账户 ${email} 已存在`, 'warning');
            return;
        }
        
        // 添加到内存存储
        const newAccount = {
            email: email,
            username: username,
            password: password
        };
        mailAccounts.push(newAccount);
        console.log('*** 添加账户后mailAccounts:', mailAccounts);
        console.log('*** 添加的账户:', newAccount);
        
        // 如果是第一个账户，清空提示行
        if (tableBody.children.length === 1 && tableBody.children[0].children.length === 1) {
            tableBody.innerHTML = '';
        }
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${email}</td>
            <td>${username}</td>
            <td><span class="badge bg-success">活跃</span></td>
            <td>
                <button class="btn btn-outline-danger btn-sm" onclick="removeMailAccount(this, '${email}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        tableBody.appendChild(row);
        
        addLogEntry(`已添加邮箱账户: ${email}`, 'success');
    }
    
    // 删除邮箱账户
    window.removeMailAccount = function(button, email) {
        const row = button.closest('tr');
        row.remove();
        
        // 从内存存储中删除
        mailAccounts = mailAccounts.filter(acc => acc.email !== email);
        
        const tableBody = document.getElementById('mail_accounts_list');
        if (tableBody.children.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无邮箱账户</td></tr>';
        }
        
        addLogEntry(`已删除邮箱账户: ${email}`, 'info');
    };
    
    // 接收邮箱协议端口自动切换
    document.getElementById('receive_protocol').addEventListener('change', function() {
        const protocol = this.value;
        const portInput = document.getElementById('receive_port');
        const sslCheckbox = document.getElementById('receive_ssl');
        
        if (protocol === 'imap') {
            portInput.value = sslCheckbox.checked ? 993 : 143;
        } else if (protocol === 'pop3') {
            portInput.value = sslCheckbox.checked ? 995 : 110;
        }
    });
    
    document.getElementById('receive_ssl').addEventListener('change', function() {
        const protocol = document.getElementById('receive_protocol').value;
        const portInput = document.getElementById('receive_port');
        
        if (protocol === 'imap') {
            portInput.value = this.checked ? 993 : 143;
        } else if (protocol === 'pop3') {
            portInput.value = this.checked ? 995 : 110;
        }
    });
    
    // SMTP SSL端口自动切换
    document.getElementById('smtp_ssl').addEventListener('change', function() {
        const portInput = document.getElementById('smtp_port');
        if (this.checked) {
            // 启用SSL时，默认使用587端口（STARTTLS）
            portInput.value = 587;
        } else {
            // 禁用SSL时，使用25端口
            portInput.value = 25;
        }
    });
    
    // SMTP服务器地址变化时的智能提示
    document.getElementById('smtp_server').addEventListener('blur', function() {
        const server = this.value.toLowerCase();
        const portInput = document.getElementById('smtp_port');
        const sslCheckbox = document.getElementById('smtp_ssl');
        
        // 根据常见邮件服务商提供建议配置
        if (server.includes('gmail.com')) {
            portInput.value = 587;
            sslCheckbox.checked = true;
            addLogEntry('Gmail SMTP建议配置: 端口587, 启用SSL/TLS', 'info');
        } else if (server.includes('outlook.com') || server.includes('hotmail.com') || server.includes('live.com')) {
            portInput.value = 587;
            sslCheckbox.checked = true;
            addLogEntry('Outlook SMTP建议配置: 端口587, 启用SSL/TLS', 'info');
        } else if (server.includes('qq.com')) {
            portInput.value = 587;
            sslCheckbox.checked = true;
            addLogEntry('QQ邮箱SMTP建议配置: 端口587, 启用SSL/TLS', 'info');
        } else if (server.includes('163.com')) {
            portInput.value = 465;
            sslCheckbox.checked = true;
            addLogEntry('163邮箱SMTP建议配置: 端口465, 启用SSL', 'info');
        } else if (server.includes('126.com')) {
            portInput.value = 465;
            sslCheckbox.checked = true;
            addLogEntry('126邮箱SMTP建议配置: 端口465, 启用SSL', 'info');
        }
    });
    
    // 邮件配置管理
    function saveMailConfig() {
        const config = {
            smtp: {
                server: document.getElementById('smtp_server').value.trim(),
                port: parseInt(document.getElementById('smtp_port').value, 10),
                ssl: document.getElementById('smtp_ssl').checked,
                email: document.getElementById('smtp_email').value.trim(),
                password: document.getElementById('smtp_password').value.trim(),
                no_auth: document.getElementById('smtp_no_auth').checked,
                use_local_storage: document.getElementById('use_local_storage').checked
            },
            receive: {
                protocol: document.getElementById('receive_protocol').value,
                server: document.getElementById('receive_server').value.trim(),
                port: parseInt(document.getElementById('receive_port').value, 10),
                ssl: document.getElementById('receive_ssl').checked,
                email: document.getElementById('receive_email').value.trim(),
                password: document.getElementById('receive_password').value.trim()
            },
            timestamp: new Date().toISOString()
        };
        
        // 验证配置完整性
        if (!config.smtp.server || !config.smtp.email || !config.receive.server || !config.receive.email) {
            addLogEntry('请填写完整的邮件配置信息', 'warning');
            return false;
        }
        
        localStorage.setItem('mail_client_config', JSON.stringify(config));
        addLogEntry('邮件配置已保存', 'success');
        
        // 更新邮箱选择列表
        updateInboxEmailSelect();
        
        return true;
    }
    
    function updateInboxEmailSelect() {
        const select = document.getElementById('inbox_email_select');
        if (!select) return;
        
        // 收集所有可能的邮箱地址
        const emails = new Set();
        
        // 从SMTP配置获取
        const smtpEmail = document.getElementById('smtp_email').value.trim();
        if (smtpEmail) emails.add(smtpEmail);
        
        // 从接收配置获取
        const receiveEmail = document.getElementById('receive_email').value.trim();
        if (receiveEmail) emails.add(receiveEmail);
        
        // 添加默认邮箱
        emails.add('test1@test.com');
        emails.add('test2@test.com');
        
        // 清空并重新填充选项
        select.innerHTML = '';
        const emailArray = Array.from(emails).sort();
        
        emailArray.forEach(email => {
            const option = document.createElement('option');
            option.value = email;
            option.textContent = email;
            if (email === 'test2@test.com') {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }
    
    function loadMailConfig() {
        const configStr = localStorage.getItem('mail_client_config');
        if (!configStr) {
            addLogEntry('未找到已保存的邮件配置', 'info');
            return false;
        }
        
        try {
            const config = JSON.parse(configStr);
            
            // 加载SMTP配置
            if (config.smtp) {
                document.getElementById('smtp_server').value = config.smtp.server || '';
                document.getElementById('smtp_port').value = config.smtp.port || 587;
                document.getElementById('smtp_ssl').checked = config.smtp.ssl !== false;
                document.getElementById('smtp_email').value = config.smtp.email || '';
                document.getElementById('smtp_password').value = config.smtp.password || '';
                document.getElementById('smtp_no_auth').checked = config.smtp.no_auth || false;
                document.getElementById('use_local_storage').checked = config.smtp.use_local_storage || false;
            }
            
            // 加载接收配置
            if (config.receive) {
                document.getElementById('receive_protocol').value = config.receive.protocol || 'imap';
                document.getElementById('receive_server').value = config.receive.server || '';
                document.getElementById('receive_port').value = config.receive.port || 993;
                document.getElementById('receive_ssl').checked = config.receive.ssl !== false;
                document.getElementById('receive_email').value = config.receive.email || '';
                document.getElementById('receive_password').value = config.receive.password || '';
            }
            
            const timestamp = config.timestamp ? new Date(config.timestamp).toLocaleString() : '未知时间';
            addLogEntry(`邮件配置已加载 (保存时间: ${timestamp})`, 'success');
            
            // 更新邮箱选择列表
            updateInboxEmailSelect();
            
            return true;
        } catch (e) {
            addLogEntry('加载邮件配置失败: 配置文件格式错误', 'error');
            return false;
        }
    }
    
    function testMailConnection(type) {
        const config = type === 'smtp' ? {
            server: document.getElementById('smtp_server').value.trim(),
            port: parseInt(document.getElementById('smtp_port').value, 10),
            ssl: document.getElementById('smtp_ssl').checked,
            email: document.getElementById('smtp_no_auth').checked ? '' : document.getElementById('smtp_email').value.trim(),
            password: document.getElementById('smtp_no_auth').checked ? '' : document.getElementById('smtp_password').value.trim(),
            no_auth: document.getElementById('smtp_no_auth').checked
        } : {
            protocol: document.getElementById('receive_protocol').value,
            server: document.getElementById('receive_server').value.trim(),
            port: parseInt(document.getElementById('receive_port').value, 10),
            ssl: document.getElementById('receive_ssl').checked,
            email: document.getElementById('receive_email').value.trim(),
            password: document.getElementById('receive_password').value.trim()
        };
        
        // 验证配置完整性
        if (!config.server) {
            addLogEntry(`请填写${type === 'smtp' ? 'SMTP' : '接收'}服务器地址`, 'warning');
            return;
        }
        
        // 如果不是无认证模式，需要验证邮箱和密码
        if (type === 'smtp' && !config.no_auth && (!config.email || !config.password)) {
            addLogEntry('请填写完整的SMTP服务器配置（邮箱和密码）', 'warning');
            return;
        } else if (type !== 'smtp' && (!config.email || !config.password)) {
            addLogEntry('请填写完整的接收服务器配置（邮箱和密码）', 'warning');
            return;
        }
        
        const statusElement = document.getElementById(`${type === 'smtp' ? 'smtp' : 'receive'}_status`);
        const testBtn = document.getElementById(`${type === 'smtp' ? 'smtp' : 'receive'}_test_btn`);
        
        // 更新状态
        statusElement.className = 'badge bg-warning';
        statusElement.textContent = '测试中...';
        testBtn.disabled = true;
        
        addLogEntry(`正在测试${type === 'smtp' ? 'SMTP' : '接收'}服务器连接...`, 'info');
        
        // 直接发送测试请求到Agent
        if (!clientAgentUrl) {
            addLogEntry('请先连接客户端代理程序', 'warning');
            testBtn.disabled = false;
            statusElement.className = 'badge bg-danger';
            statusElement.textContent = '连接失败';
            return;
        }
        
        const payload = {
            protocol: 'mail',
            action: 'test_connection',
            type: type,
            config: config
        };
        
        addLogEntry(`[调试] 发送邮件测试请求到: ${clientAgentUrl}/api/services/client`, 'info');
        
        fetch(`${clientAgentUrl}/api/services/client`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
            .then(res => {
                if (!res.ok) {
                    return res.text().then(text => {
                        throw new Error(`HTTP ${res.status}: ${res.statusText} - ${text.substring(0, 100)}`);
                    });
                }
                return res.json();
            })
            .then(data => {
                if (data && data.success) {
                    statusElement.className = 'badge bg-success';
                    statusElement.textContent = '连接成功';
                    const successMsg = decodeUnicodeString(data?.message || '连接成功');
                    addLogEntry(`${type === 'smtp' ? 'SMTP' : '接收'}服务器连接测试成功: ${successMsg}`, 'success');
            } else {
                statusElement.className = 'badge bg-danger';
                statusElement.textContent = '连接失败';
                const errorMsg = decodeUnicodeString(data?.error || '未知错误');
                addLogEntry(`${type === 'smtp' ? 'SMTP' : '接收'}服务器连接测试失败: ${errorMsg}`, 'error');
            }
            })
            .catch(err => {
            statusElement.className = 'badge bg-danger';
            statusElement.textContent = '连接失败';
            const errorMsg = decodeUnicodeString(err.message);
            addLogEntry(`${type === 'smtp' ? 'SMTP' : '接收'}服务器连接测试失败: ${errorMsg}`, 'error');
        }).finally(() => {
            testBtn.disabled = false;
        });
    }
    
    // 邮件配置按钮事件
    document.getElementById('save_mail_config_btn').addEventListener('click', function() {
        saveMailConfig();
    });
    
    document.getElementById('load_mail_config_btn').addEventListener('click', function() {
        loadMailConfig();
    });
    
    document.getElementById('smtp_test_btn').addEventListener('click', function() {
        testMailConnection('smtp');
    });
    
    document.getElementById('smtp_ping_btn').addEventListener('click', function() {
        testNetworkConnection('smtp');
    });
    
    // 无认证选项变化时的处理
    document.getElementById('smtp_no_auth').addEventListener('change', function() {
        const noAuth = this.checked;
        const emailInput = document.getElementById('smtp_email');
        const passwordInput = document.getElementById('smtp_password');
        
        if (noAuth) {
            emailInput.disabled = true;
            passwordInput.disabled = true;
            emailInput.placeholder = '无认证模式下不需要邮箱地址';
            passwordInput.placeholder = '无认证模式下不需要密码';
        } else {
            emailInput.disabled = false;
            passwordInput.disabled = false;
            emailInput.placeholder = '例如: sender@gmail.com';
            passwordInput.placeholder = '邮箱密码或应用密码';
        }
    });
    
    function testNetworkConnection(type) {
        const targetHost = type === 'smtp' 
            ? document.getElementById('smtp_server').value.trim()
            : document.getElementById('receive_server').value.trim();
        
        if (!targetHost) {
            addLogEntry(`请填写${type === 'smtp' ? 'SMTP' : '接收'}服务器地址`, 'warning');
            return;
        }
        
        const pingBtn = document.getElementById(`${type === 'smtp' ? 'smtp' : 'receive'}_ping_btn`);
        const originalText = pingBtn.innerHTML;
        pingBtn.disabled = true;
        pingBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>测试中...';
        
        addLogEntry(`正在 Ping 测试：${targetHost}`, 'info');
        
        // 使用监听 Agent 的 /api/network_test API
        const agentUrl = listenerAgentUrl || clientAgentUrl;
        if (!agentUrl) {
            addLogEntry('请先连接代理程序', 'warning');
            pingBtn.disabled = false;
            pingBtn.innerHTML = originalText;
            return;
        }
        
        fetch(`${agentUrl}/api/network_test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                target_host: targetHost,
                count: 4,
                timeout: 2
            })
        })
            .then(res => res.json())
            .then(data => {
                if (data && data.success) {
                    const latency = data.avg_latency_ms !== null ? `${data.avg_latency_ms}ms` : 'N/A';
                    const loss = data.packet_loss || 0;
                    addLogEntry(`✓ Ping 测试成功：${targetHost}`, 'success');
                    addLogEntry(`  平均延迟：${latency}, 丢包率：${loss}%`, 'info');
                } else {
                    const errorMsg = data?.error || '未知错误';
                    addLogEntry(`✗ Ping 测试失败：${errorMsg}`, 'error');
                }
            })
            .catch(err => {
                addLogEntry(`✗ Ping 测试失败：${err.message}`, 'error');
            })
            .finally(() => {
                pingBtn.disabled = false;
                pingBtn.innerHTML = originalText;
            });
    }
    
        const config = type === 'smtp' ? {
            server: document.getElementById('smtp_server').value.trim(),
            port: parseInt(document.getElementById('smtp_port').value, 10)
        } : {
            server: document.getElementById('receive_server').value.trim(),
            port: parseInt(document.getElementById('receive_port').value, 10)
        };
        
        if (!config.server || !config.port) {
            addLogEntry(`请填写完整的${type === 'smtp' ? 'SMTP' : '接收'}服务器配置`, 'warning');
            return;
        }
        
        const pingBtn = document.getElementById(`${type === 'smtp' ? 'smtp' : 'receive'}_ping_btn`);
        const originalText = pingBtn.innerHTML;
        pingBtn.disabled = true;
        pingBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>测试中...';
        
        addLogEntry(`正在测试网络连通性: ${config.server}:${config.port}`, 'info');
        
        // 发送网络测试请求到Agent
        if (!clientAgentUrl) {
            addLogEntry('请先连接客户端代理程序', 'warning');
            pingBtn.disabled = false;
            pingBtn.innerHTML = originalText;
            return;
        }
        
        const payload = {
            protocol: 'network',
            action: 'ping',
            server: config.server,
            port: config.port
        };
        
        fetch(`${clientAgentUrl}/api/services/client`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
            .then(res => {
                if (!res.ok) {
                    return res.text().then(text => {
                        throw new Error(`HTTP ${res.status}: ${res.statusText} - ${text.substring(0, 100)}`);
                    });
                }
                return res.json();
            })
            .then(data => {
                if (data && data.success) {
                    addLogEntry(`✓ 网络连通性测试成功: ${config.server}:${config.port}`, 'success');
                } else {
                    const errorMsg = decodeUnicodeString(data?.error || '未知错误');
                    addLogEntry(`✗ 网络连通性测试失败: ${errorMsg}`, 'error');
                }
            })
            .catch(err => {
                const errorMsg = decodeUnicodeString(err.message);
                addLogEntry(`✗ 网络连通性测试失败: ${errorMsg}`, 'error');
            })
            .finally(() => {
                pingBtn.disabled = false;
                pingBtn.innerHTML = originalText;
            });
    }
    
    document.getElementById('receive_test_btn').addEventListener('click', function() {
        testMailConnection('receive');
    });
    
    // 配置检查功能
    function checkMailConfig() {
        const smtpServer = document.getElementById('smtp_server').value.trim();
        const smtpPort = parseInt(document.getElementById('smtp_port').value, 10);
        const smtpSsl = document.getElementById('smtp_ssl').checked;
        const smtpEmail = document.getElementById('smtp_email').value.trim();
        
        const receiveServer = document.getElementById('receive_server').value.trim();
        const receivePort = parseInt(document.getElementById('receive_port').value, 10);
        const receiveSsl = document.getElementById('receive_ssl').checked;
        const receiveEmail = document.getElementById('receive_email').value.trim();
        
        let issues = [];
        
        // 检查SMTP配置
        if (!smtpServer) {
            issues.push('SMTP服务器地址为空');
        } else if (smtpServer === '10.40.30.34' || smtpServer.startsWith('10.40.')) {
            issues.push('SMTP服务器使用内网地址，请确保该地址上运行了SMTP服务');
        }
        
        if (smtpPort === 465 && !smtpSsl) {
            issues.push('端口465通常需要启用SSL，建议启用SSL选项');
        } else if (smtpPort === 587 && !smtpSsl) {
            issues.push('端口587通常需要启用SSL/TLS，建议启用SSL选项');
        } else if (smtpPort === 25 && smtpSsl) {
            issues.push('端口25通常不使用SSL，建议禁用SSL或使用587/465端口');
        }
        
        if (!smtpEmail || !smtpEmail.includes('@')) {
            issues.push('SMTP邮箱地址格式不正确');
        }
        
        // 检查接收配置
        if (!receiveServer) {
            issues.push('接收服务器地址为空');
        }
        
        if (!receiveEmail || !receiveEmail.includes('@')) {
            issues.push('接收邮箱地址格式不正确');
        }
        
        // 显示检查结果
        if (issues.length === 0) {
            addLogEntry('✓ 邮件配置检查通过', 'success');
        } else {
            addLogEntry('⚠ 配置检查发现问题:', 'warning');
            issues.forEach(issue => {
                addLogEntry(`  - ${issue}`, 'warning');
            });
        }
        
        return issues.length === 0;
    }
    
    // 添加配置检查按钮事件
    document.getElementById('save_mail_config_btn').addEventListener('click', function() {
        if (checkMailConfig()) {
            saveMailConfig();
        }
    });
    
    document.getElementById('send_mail_btn').addEventListener('click', function() {
        sendMail();
    });
    
    function sendMail() {
        // 获取邮件配置
        const smtpConfig = {
            server: document.getElementById('smtp_server').value.trim(),
            port: parseInt(document.getElementById('smtp_port').value, 10),
            ssl: document.getElementById('smtp_ssl').checked,
            email: document.getElementById('smtp_email').value.trim(),
            password: document.getElementById('smtp_password').value.trim(),
            no_auth: document.getElementById('smtp_no_auth').checked,
            use_local_storage: document.getElementById('use_local_storage').checked
        };
        
        // 获取邮件内容
        const mailData = {
            from: document.getElementById('mail_from').value.trim() || 'test1@test.com',
            to: document.getElementById('mail_to').value.trim() || 'test2@test.com',
            cc: document.getElementById('mail_cc').value.trim(),
            subject: document.getElementById('mail_subject').value.trim(),
            content: document.getElementById('mail_content').value.trim(),
            content_type: 'plain' // 暂时固定为纯文本
        };
        
        // 处理附件
        const attachmentInput = document.getElementById('mail_attachment');
        const attachments = [];
        
        if (attachmentInput.files && attachmentInput.files.length > 0) {
            console.log(`发现 ${attachmentInput.files.length} 个附件`);
            
            // 使用Promise.all处理所有附件的读取
            const filePromises = Array.from(attachmentInput.files).map(file => {
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const base64Data = e.target.result.split(',')[1]; // 去掉data:xxx;base64,前缀
                        resolve({
                            filename: file.name,
                            content: base64Data,
                            size: file.size,
                            type: file.type
                        });
                    };
                    reader.onerror = reject;
                    reader.readAsDataURL(file);
                });
            });
            
            Promise.all(filePromises).then(attachmentData => {
                mailData.attachments = attachmentData;
                console.log(`附件处理完成: ${attachmentData.length} 个文件`);
                sendMailWithData(smtpConfig, mailData);
            }).catch(error => {
                addLogEntry(`附件处理失败: ${error.message}`, 'error');
            });
            
            return; // 等待附件处理完成
        }
        
        // 没有附件，直接发送
        sendMailWithData(smtpConfig, mailData);
    }
    
    function sendMailWithData(smtpConfig, mailData) {
        
        // 验证必填字段
        if (!smtpConfig.server || !smtpConfig.port) {
            addLogEntry('请先配置SMTP服务器信息', 'warning');
            return;
        }
        
        if (!smtpConfig.no_auth && (!smtpConfig.email || !smtpConfig.password)) {
            addLogEntry('请填写SMTP认证信息或启用无认证模式', 'warning');
            return;
        }
        
        if (!mailData.to || !mailData.subject || !mailData.content) {
            addLogEntry('请填写收件人、主题和邮件内容', 'warning');
            return;
        }
        
        if (!clientAgentUrl) {
            addLogEntry('请先连接客户端代理程序', 'warning');
            return;
        }
        
        const sendBtn = document.getElementById('send_mail_btn');
        const originalText = sendBtn.innerHTML;
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>发送中...';
        
        const attachmentCount = mailData.attachments ? mailData.attachments.length : 0;
        if (attachmentCount > 0) {
            addLogEntry(`正在发送邮件（包含 ${attachmentCount} 个附件）...`, 'info');
        } else {
            addLogEntry('正在发送邮件...', 'info');
        }
        
        const payload = {
            protocol: 'mail',
            action: 'send_mail',
            smtp_config: smtpConfig,
            mail_data: mailData,
            source_ip: getSelectedInterfaceIp(false) // 使用客户端选中的网卡IP作为源地址
        };
        
        fetch(`${clientAgentUrl}/api/services/client`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
            .then(res => {
                if (!res.ok) {
                    return res.text().then(text => {
                        throw new Error(`HTTP ${res.status}: ${res.statusText} - ${text.substring(0, 100)}`);
                    });
                }
                return res.json();
            })
            .then(data => {
                if (data && data.success) {
                    const successMsg = decodeUnicodeString(data?.message || '邮件发送成功');
                    addLogEntry(`✅ 邮件发送成功: ${successMsg}`, 'success');
                    
                    // 清空表单（保留默认值）
                    document.getElementById('mail_from').value = 'test1@test.com';
                    document.getElementById('mail_to').value = 'test2@test.com';
                    document.getElementById('mail_cc').value = '';
                    document.getElementById('mail_subject').value = '';
                    document.getElementById('mail_content').value = '';
                    document.getElementById('mail_attachment').value = '';
                } else {
                    const errorMsg = decodeUnicodeString(data?.error || '邮件发送失败');
                    addLogEntry(`✗ 邮件发送失败: ${errorMsg}`, 'error');
                }
            })
            .catch(err => {
                const errorMsg = decodeUnicodeString(err.message);
                addLogEntry(`✗ 邮件发送失败: ${errorMsg}`, 'error');
            })
            .finally(() => {
                sendBtn.disabled = false;
                sendBtn.innerHTML = originalText;
            });
    }
    
    document.getElementById('refresh_inbox_btn').addEventListener('click', function() {
        refreshInbox();
    });
    
    function refreshInbox() {
        // 获取选择的邮箱（默认test2@test.com）
        const selectedEmail = document.getElementById('inbox_email_select').value || 'test2@test.com';
        
        // 获取接收服务器配置
        const receiveConfig = {
            protocol: document.getElementById('receive_protocol').value,
            server: document.getElementById('receive_server').value.trim(),
            port: parseInt(document.getElementById('receive_port').value, 10),
            ssl: document.getElementById('receive_ssl').checked,
            email: selectedEmail,  // 使用选择的邮箱
            password: document.getElementById('receive_password').value.trim(),
            use_local_storage: document.getElementById('use_local_storage').checked
        };
        
        // 验证配置
        if (!receiveConfig.server || !receiveConfig.port || !receiveConfig.email || !receiveConfig.password) {
            addLogEntry('请先配置完整的接收服务器信息', 'warning');
            return;
        }
        
        if (!clientAgentUrl) {
            addLogEntry('请先连接客户端代理程序', 'warning');
            return;
        }
        
        const refreshBtn = document.getElementById('refresh_inbox_btn');
        const originalText = refreshBtn.innerHTML;
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>刷新中...';
        
        const protocol = receiveConfig.protocol.toUpperCase();
        addLogEntry(`正在获取收件箱邮件 (${protocol}, ${selectedEmail})...`, 'info');
        
        const payload = {
            protocol: 'mail',
            action: 'get_inbox',
            receive_config: receiveConfig,
            source_ip: getSelectedInterfaceIp(false) // 使用客户端选中的网卡IP作为源地址
        };
        
        fetch(`${clientAgentUrl}/api/services/client`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
            .then(res => {
                if (!res.ok) {
                    return res.text().then(text => {
                        throw new Error(`HTTP ${res.status}: ${res.statusText} - ${text.substring(0, 100)}`);
                    });
                }
                return res.json();
            })
            .then(data => {
                if (data && data.success) {
                    const mails = data.mails || [];
                    addLogEntry(`✅ 收件箱刷新成功 (${protocol}, ${selectedEmail}): 共 ${mails.length} 封邮件`, 'success');
                    
                    // 显示邮件列表
                    displayInboxList(mails);
                } else {
                    const errorMsg = decodeUnicodeString(data?.error || '获取收件箱失败');
                    addLogEntry(`✗ 收件箱刷新失败: ${errorMsg}`, 'error');
                }
            })
            .catch(err => {
                const errorMsg = decodeUnicodeString(err.message);
                addLogEntry(`✗ 收件箱刷新失败: ${errorMsg}`, 'error');
            })
            .finally(() => {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = originalText;
            });
    }
    
    function displayInboxList(mails) {
        const inboxList = document.getElementById('inbox_list');
        if (!inboxList) {
            addLogEntry('找不到收件箱列表元素', 'error');
            return;
        }
        
        if (mails.length === 0) {
            inboxList.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暂无邮件</td></tr>';
            window.currentMails = [];
            return;
        }
        
        let html = '';
        mails.forEach((mail, index) => {
            const protocol = mail.protocol || '未知';
            const protocolBadge = protocol === 'IMAP' 
                ? '<span class="badge bg-info">IMAP</span>' 
                : protocol === 'POP3' 
                ? '<span class="badge bg-success">POP3</span>' 
                : '<span class="badge bg-secondary">未知</span>';
            
            const attachmentInfo = mail.attachments && mail.attachments.length > 0 
                ? `<i class="fas fa-paperclip text-primary" title="${mail.attachments.length} 个附件"></i> ${mail.attachments.length}`
                : '<span class="text-muted">无</span>';
            
            const dateDisplay = mail.date || '未知';
            
            html += `<tr>
                <td>${protocolBadge}</td>
                <td>${mail.from || '未知'}</td>
                <td>${mail.subject || '无主题'}</td>
                <td>${dateDisplay}</td>
                <td>${formatFileSize(mail.size || 0)}</td>
                <td>${attachmentInfo}</td>
            </tr>`;
        });
        
        inboxList.innerHTML = html;
        
        // 存储邮件数据供查看使用
        window.currentMails = mails;
    }
    
    function displayMailList(mails) {
        // 兼容旧代码，调用新的displayInboxList
        displayInboxList(mails);
    }
    
    function viewMail(index) {
        const mail = window.currentMails[index];
        if (!mail) {
            addLogEntry('邮件不存在', 'error');
            return;
        }
        
        // 创建邮件查看模态框
        let modal = document.getElementById('mail_view_modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'mail_view_modal';
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">邮件详情</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" id="mail_view_content">
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        // 构建邮件内容
        let content = `
            <div class="mb-3">
                <strong>发件人:</strong> ${mail.from || '未知'}<br>
                <strong>收件人:</strong> ${mail.to || '未知'}<br>
                <strong>主题:</strong> ${mail.subject || '无主题'}<br>
                <strong>日期:</strong> ${mail.date || '未知'}<br>
                <strong>大小:</strong> ${formatFileSize(mail.size || 0)}
            </div>
        `;
        
        // 显示附件信息
        if (mail.attachments && mail.attachments.length > 0) {
            content += `
                <div class="mb-3">
                    <strong>附件 (${mail.attachments.length} 个):</strong>
                    <div class="mt-2">
            `;
            
            mail.attachments.forEach((attachment, i) => {
                content += `
                    <div class="d-flex align-items-center mb-2 p-2 border rounded">
                        <i class="fas fa-paperclip text-primary me-2"></i>
                        <div class="flex-grow-1">
                            <div class="fw-bold">${attachment.filename}</div>
                            <small class="text-muted">
                                ${formatFileSize(attachment.size)} - ${attachment.content_type || '未知类型'}
                            </small>
                        </div>
                    </div>
                `;
            });
            
            content += `
                    </div>
                </div>
            `;
        }
        
        // 显示邮件正文
        content += `
            <div class="mb-3">
                <strong>邮件内容:</strong>
                <div class="mt-2 p-3 border rounded bg-light" style="white-space: pre-wrap; max-height: 300px; overflow-y: auto;">
                    ${mail.body || '无内容'}
                </div>
            </div>
        `;
        
        document.getElementById('mail_view_content').innerHTML = content;
        
        // 显示模态框
        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();
    }
    
    function viewMail(index) {
        if (!window.currentMails || !window.currentMails[index]) {
            addLogEntry('邮件数据不存在', 'error');
            return;
        }
        
        const mail = window.currentMails[index];
        
        // 创建邮件查看模态框
        const modalHtml = `
            <div class="modal fade" id="mailViewModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">查看邮件</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <strong>发件人:</strong> ${mail.from || '未知'}
                            </div>
                            <div class="mb-3">
                                <strong>收件人:</strong> ${mail.to || '未知'}
                            </div>
                            <div class="mb-3">
                                <strong>主题:</strong> ${mail.subject || '无主题'}
                            </div>
                            <div class="mb-3">
                                <strong>日期:</strong> ${mail.date || '未知'}
                            </div>
                            <div class="mb-3">
                                <strong>内容:</strong>
                                <div class="border p-3 bg-light" style="max-height: 300px; overflow-y: auto;">
                                    <pre style="white-space: pre-wrap; font-family: inherit;">${mail.body || '无内容'}</pre>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 移除已存在的模态框
        const existingModal = document.getElementById('mailViewModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 添加新的模态框
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('mailViewModal'));
        modal.show();
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Unicode解码函数
    function decodeUnicodeString(str) {
        if (!str) return str;
        try {
            // 处理JSON中的Unicode转义序列
            return str.replace(/\\u[\dA-F]{4}/gi, function (match) {
                return String.fromCharCode(parseInt(match.replace(/\\u/g, ''), 16));
            });
        } catch (e) {
            return str; // 如果解码失败，返回原字符串
        }
    }
    
    // 页面加载时自动加载邮件配置
    setTimeout(function() {
        loadMailConfig();
        // 确保邮箱选择列表已初始化
        updateInboxEmailSelect();
    }, 1000);
    
})();
});
