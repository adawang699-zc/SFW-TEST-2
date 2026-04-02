document.addEventListener('DOMContentLoaded', function() {
(() => {
    // 监听服务代理相关
    const listenerConnectBtn = document.getElementById('listener_connect_btn');
    const listenerAgentIpInput = document.getElementById('listener_agent_ip');
    const listenerAgentPortInput = document.getElementById('listener_agent_port');
    const listenerInterfaceSelect = document.getElementById('listener_interface');
    const listenerInterfaceInfo = document.getElementById('listener_interface_info');
    
    // 客户端代理相关
    const clientConnectBtn = document.getElementById('client_connect_btn');
    const clientAgentIpInput = document.getElementById('client_agent_ip');
    const clientAgentPortInput = document.getElementById('client_agent_port');
    const clientInterfaceSelect = document.getElementById('client_interface');
    const clientInterfaceInfo = document.getElementById('client_interface_info');
    
    const logList = document.getElementById('service_log_list');
    const listenerButtons = document.querySelectorAll('[data-role="listener-btn"]');
    const clearLogsBtn = document.getElementById('clear_logs_btn');

    let listenerAgentUrl = '';
    let clientAgentUrl = '';
    let listenerInterfacesData = [];
    let clientInterfacesData = [];
    let statusInterval = null;
    let logsInterval = null;

    function addLogEntry(message, level = 'info') {
        if (!logList) return;
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        const badgeClass = level === 'error' ? 'bg-danger' : level === 'warning' ? 'bg-warning text-dark' : level === 'success' ? 'bg-success' : 'bg-secondary';
        const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });
        li.innerHTML = `<span>[${timestamp}] ${message}</span><span class="badge ${badgeClass}">${level.toUpperCase()}</span>`;
        logList.prepend(li);
        while (logList.children.length > 200) {
            logList.removeChild(logList.lastChild);
        }
    }

    function updateAgentStatus(connected) {
        if (!agentStatusBadge) return;
        if (connected) {
            agentStatusBadge.className = 'badge bg-success';
            agentStatusBadge.textContent = '已连接';
        } else {
            agentStatusBadge.className = 'badge bg-secondary';
            agentStatusBadge.textContent = '未连接';
        }
    }

    function populateInterfaces(interfaces = [], isListener = true) {
        const select = isListener ? listenerInterfaceSelect : clientInterfaceSelect;
        const data = isListener ? listenerInterfacesData : clientInterfacesData;
        
        if (isListener) {
            listenerInterfacesData = interfaces;
        } else {
            clientInterfacesData = interfaces;
        }
        
        if (!select) return;
        
        select.innerHTML = '';
        if (interfaces.length === 0) {
            select.innerHTML = '<option value="">未获取到网卡</option>';
            select.disabled = true;
            return;
        }
        select.disabled = false;
        select.innerHTML = '<option value="">请选择网卡</option>';
        interfaces.forEach((iface, index) => {
            const option = document.createElement('option');
            option.value = iface.ip || '';
            option.dataset.mac = iface.mac || '';
            option.dataset.name = iface.display_name || iface.name || `接口${index + 1}`;
            option.textContent = `${option.dataset.name} (${iface.ip || '无IP'})`;
            select.appendChild(option);
        });
    }

    function getSelectedInterfaceIp(isListener = true) {
        const select = isListener ? listenerInterfaceSelect : clientInterfaceSelect;
        return select ? select.value : '';
    }

    function startPolling() {
        stopPolling();
        fetchStatus();
        fetchLogs();
        statusInterval = setInterval(fetchStatus, 5000);
        logsInterval = setInterval(fetchLogs, 5000);
    }

    function stopPolling() {
        if (statusInterval) clearInterval(statusInterval);
        if (logsInterval) clearInterval(logsInterval);
        statusInterval = null;
        logsInterval = null;
    }

    function fetchStatus() {
        // 构建查询参数
        const params = new URLSearchParams();
        if (listenerAgentUrl) {
            params.append('listener_agent_url', listenerAgentUrl);
        }
        if (clientAgentUrl) {
            params.append('client_agent_url', clientAgentUrl);
        }
        
        // 如果没有任何URL，直接返回
        if (!listenerAgentUrl && !clientAgentUrl) {
            return;
        }
        
        // 一次性获取所有状态
        fetch(`/api/services/status/?${params.toString()}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // 更新监听服务状态
                    if (data.listeners) {
                        updateListenerStatus(data.listeners);
                    }
                    // 更新客户端状态
                    if (data.clients) {
                        updateClientStatus(data.clients);
                    }
                } else {
                    console.error('获取状态失败:', data.error);
                }
            })
            .catch(err => {
                console.error('获取状态失败:', err);
                addLogEntry(`获取状态失败: ${err.message}`, 'error');
            });
    }

    function fetchLogs() {
        // 合并两个代理的日志
        const logs = [];
        const promises = [];
        
        if (listenerAgentUrl) {
            promises.push(
                fetch(`/api/services/logs/?agent_url=${encodeURIComponent(listenerAgentUrl)}&limit=30`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.success && data.logs) {
                            // 标记日志来源
                            data.logs.forEach(log => {
                                log.source_tag = '监听服务';
                                log.agent_type = 'listener';
                            });
                            logs.push(...data.logs);
                        }
                    })
                    .catch(err => {
                        console.error('获取监听服务日志失败:', err);
                    })
            );
        }
        
        if (clientAgentUrl) {
            promises.push(
                fetch(`/api/services/logs/?agent_url=${encodeURIComponent(clientAgentUrl)}&limit=30`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.success && data.logs) {
                            // 标记日志来源
                            data.logs.forEach(log => {
                                log.source_tag = '客户端';
                                log.agent_type = 'client';
                            });
                            logs.push(...data.logs);
                        }
                    })
                    .catch(err => {
                        console.error('获取客户端日志失败:', err);
                    })
            );
        }
        
        Promise.all(promises).then(() => {
            if (logs.length > 0) {
                // 按时间戳排序（最新的在前）
                logs.sort((a, b) => {
                    const tsA = a.timestamp || '';
                    const tsB = b.timestamp || '';
                    return tsB.localeCompare(tsA);
                });
                displayLogs(logs);
            } else if (logList) {
                // 如果没有日志，显示提示
                if (logList.children.length === 0 || (logList.children.length === 1 && logList.children[0].textContent.includes('暂无'))) {
                    logList.innerHTML = '<li class="list-group-item text-muted text-center">暂无日志</li>';
                }
            }
        }).catch(err => {
            console.error('获取日志失败:', err);
            addLogEntry(`获取日志失败: ${err.message}`, 'error');
        });
    }

    function displayLogs(logs) {
        if (!logList) return;
        
        // 保留已有的日志，只添加新的
        const existingTimestamps = new Set();
        Array.from(logList.children).forEach(li => {
            const timestampMatch = li.textContent.match(/\[(\d{2}:\d{2}:\d{2})\]/);
            if (timestampMatch) {
                existingTimestamps.add(timestampMatch[1]);
            }
        });
        
        // 添加新日志
        logs.forEach(log => {
            const timestamp = log.timestamp || new Date().toLocaleTimeString('zh-CN', { hour12: false });
            const timeOnly = timestamp.split(' ')[0] || timestamp;
            
            // 如果日志已存在，跳过
            if (existingTimestamps.has(timeOnly) && logList.querySelector(`[data-log-id="${log.timestamp || ''}"]`)) {
                return;
            }
            
            const li = document.createElement('li');
            const level = (log.level || 'info').toLowerCase();
            const badgeClass = level === 'error' ? 'bg-danger' : 
                             level === 'warning' ? 'bg-warning text-dark' : 
                             level === 'success' ? 'bg-success' : 'bg-secondary';
            
            // 根据代理类型设置不同的图标和颜色
            const sourceTag = log.source_tag || log.source || '服务';
            const sourceIcon = log.agent_type === 'listener' ? 'fa-broadcast-tower' : 
                              log.agent_type === 'client' ? 'fa-desktop' : 'fa-server';
            const sourceColor = log.agent_type === 'listener' ? 'text-primary' : 
                              log.agent_type === 'client' ? 'text-success' : 'text-secondary';
            
            li.className = 'list-group-item d-flex justify-content-between align-items-start';
            li.setAttribute('data-log-id', log.timestamp || '');
            li.innerHTML = `
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-1">
                        <i class="fas ${sourceIcon} ${sourceColor} me-2"></i>
                        <small class="text-muted me-2">[${timestamp}]</small>
                        <span class="badge bg-light text-dark me-2">${sourceTag}</span>
                    </div>
                    <div class="text-break">${escapeHtml(log.message || '')}</div>
                </div>
                <span class="badge ${badgeClass} ms-2">${(log.level || 'INFO').toUpperCase()}</span>
            `;
            
            // 插入到列表顶部
            if (logList.firstChild) {
                logList.insertBefore(li, logList.firstChild);
            } else {
                logList.appendChild(li);
            }
        });
        
        // 限制日志数量（最多保留200条）
        while (logList.children.length > 200) {
            logList.removeChild(logList.lastChild);
        }
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function updateListenerStatus(listeners) {
        const tcpStatus = listeners.tcp || { running: false };
        const udpStatus = listeners.udp || { running: false };
        const ftpStatus = listeners.ftp || { running: false };
        const httpStatus = listeners.http || { running: false };
        const mailStatus = listeners.mail || { running: false };
        // 统一处理所有监听服务状态，确保一致性
        updateBadge('tcp_listener_status', tcpStatus.running === true);
        updateBadge('udp_listener_status', udpStatus.running === true);
        updateBadge('ftp_listener_status', ftpStatus.running === true);
        updateBadge('http_listener_status', httpStatus.running === true);
        updateBadge('mail_listener_status', mailStatus.running === true);
        
        // 更新HTTP服务访问地址
        if (httpStatus.running) {
            const port = document.getElementById('http_listener_port')?.value || '80';
            const interfaceIp = getSelectedInterfaceIp(true) || '0.0.0.0';
            const httpUrl = `http://${interfaceIp === '0.0.0.0' ? 'localhost' : interfaceIp}:${port}`;
            const urlSpan = document.getElementById('http_listener_url');
            if (urlSpan) {
                urlSpan.innerHTML = `<a href="${httpUrl}" target="_blank">${httpUrl}</a>`;
            }
        } else {
            const urlSpan = document.getElementById('http_listener_url');
            if (urlSpan) {
                urlSpan.textContent = '-';
            }
        }
        
        // 更新邮件服务信息
        if (mailStatus.running) {
            // 优先使用后端返回的实际端口信息，如果没有则使用前端配置
            const smtpPort = mailStatus.smtp_port || document.getElementById('mail_listener_smtp_port')?.value || '25';
            const imapPort = mailStatus.imap_port || document.getElementById('mail_listener_imap_port')?.value || '143';
            const pop3Port = mailStatus.pop3_port || document.getElementById('mail_listener_pop3_port')?.value || '110';
            const domain = mailStatus.domain || document.getElementById('mail_listener_domain')?.value || 'autotest.com';
            const interfaceIp = getSelectedInterfaceIp(true) || '0.0.0.0';
            const serverIp = interfaceIp === '0.0.0.0' ? (mailStatus.host || domain) : interfaceIp;
            
            const smtpUrlSpan = document.getElementById('mail_listener_smtp_url');
            if (smtpUrlSpan) {
                smtpUrlSpan.textContent = `smtp://${serverIp}:${smtpPort}`;
            }
            
            const imapUrlSpan = document.getElementById('mail_listener_imap_url');
            if (imapUrlSpan) {
                imapUrlSpan.textContent = `imap://${serverIp}:${imapPort}`;
            }
            
            const pop3UrlSpan = document.getElementById('mail_listener_pop3_url');
            if (pop3UrlSpan) {
                pop3UrlSpan.textContent = `pop3://${serverIp}:${pop3Port}`;
            }
            
            const domainSpan = document.getElementById('mail_listener_domain_info');
            if (domainSpan) {
                domainSpan.textContent = domain;
            }
            
            const connectionsSpan = document.getElementById('mail_listener_connections');
            if (connectionsSpan) {
                const conns = mailStatus.connections || {};
                connectionsSpan.textContent = Object.keys(conns).length;
            }
        } else {
            const smtpUrlSpan = document.getElementById('mail_listener_smtp_url');
            if (smtpUrlSpan) {
                smtpUrlSpan.textContent = '-';
            }
            
            const imapUrlSpan = document.getElementById('mail_listener_imap_url');
            if (imapUrlSpan) {
                imapUrlSpan.textContent = '-';
            }
            
            const pop3UrlSpan = document.getElementById('mail_listener_pop3_url');
            if (pop3UrlSpan) {
                pop3UrlSpan.textContent = '-';
            }
            
            const domainSpan = document.getElementById('mail_listener_domain_info');
            if (domainSpan) {
                domainSpan.textContent = '-';
            }
            
            const connectionsSpan = document.getElementById('mail_listener_connections');
            if (connectionsSpan) {
                connectionsSpan.textContent = '0';
            }
        }

        const tcpList = document.getElementById('tcp_listener_connections');
        if (tcpList) {
            tcpList.innerHTML = '';
            const conns = tcpStatus.connections || [];
            if (!conns.length) {
                tcpList.innerHTML = '<li class="list-group-item text-muted">暂无连接</li>';
            } else {
                conns.forEach(conn => {
                    const li = document.createElement('li');
                    li.className = 'list-group-item d-flex justify-content-between align-items-center';
                    li.innerHTML = `<span>${conn.address}</span><span class="badge bg-light text-dark">${conn.bytes_received || 0} bytes</span>`;
                    tcpList.appendChild(li);
                });
            }
        }

        const udpPackets = document.getElementById('udp_listener_packets');
        if (udpPackets) udpPackets.textContent = udpStatus.packets || 0;

        const ftpList = document.getElementById('ftp_listener_connections');
        if (ftpList) {
            ftpList.innerHTML = '';
            const sessions = ftpStatus.connections || [];
            if (!sessions.length) {
                ftpList.innerHTML = '<li class="list-group-item text-muted">暂无会话</li>';
            } else {
                sessions.forEach(conn => {
                    const li = document.createElement('li');
                    li.className = 'list-group-item d-flex justify-content-between align-items-center';
                    li.innerHTML = `<span>${conn.address}</span><span class="badge bg-light text-dark">${conn.commands || 0} commands</span>`;
                    ftpList.appendChild(li);
                });
            }
        }
    }

    function updateClientStatus(clients) {
        const tcp = clients.tcp || { running: false };
        const udp = clients.udp || { running: false };
        const ftp = clients.ftp || { running: false };
        const http = clients.http || { running: false };

        // 更新TCP客户端状态和按钮
        const tcpRunning = tcp.running === true;
        updateBadge('tcp_client_status', tcpRunning ? '已连接' : '未连接', tcpRunning);
        if (tcpRunning) {
            document.getElementById('tcp_client_connect')?.setAttribute('disabled', 'disabled');
            document.getElementById('tcp_client_start')?.removeAttribute('disabled');
            document.getElementById('tcp_client_stop_send')?.removeAttribute('disabled');
            document.getElementById('tcp_client_disconnect')?.removeAttribute('disabled');
        } else {
            document.getElementById('tcp_client_connect')?.removeAttribute('disabled');
            document.getElementById('tcp_client_start')?.setAttribute('disabled', 'disabled');
            document.getElementById('tcp_client_stop_send')?.setAttribute('disabled', 'disabled');
            document.getElementById('tcp_client_disconnect')?.setAttribute('disabled', 'disabled');
        }
        
        // 更新TCP客户端连接列表
        const table = document.getElementById('tcp_connection_table');
        if (table) {
            const tbody = table.querySelector('tbody');
            if (tbody) {
                tbody.innerHTML = '';
                const conns = tcp.connections || [];
                console.log('TCP客户端连接列表:', conns);
                if (!conns.length) {
                    tbody.innerHTML = '<tr><td colspan="5" class="text-muted">暂无连接</td></tr>';
                } else {
                    conns.forEach(conn => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${conn.id || '-'}</td>
                            <td>${conn.address || '-'}</td>
                            <td>${conn.bytes_sent || 0} bytes</td>
                            <td>${conn.status || 'unknown'}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-danger" data-action="disconnect" data-conn="${conn.id}">断开</button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            }
        }
        
        updateBadge('udp_client_status', udp.running === true);
        
        // 更新HTTP客户端状态
        const httpRunning = http.running === true;
        updateBadge('http_client_status', httpRunning ? '已连接' : '未连接', httpRunning);
        if (httpRunning) {
            document.getElementById('http_client_connect')?.setAttribute('disabled', 'disabled');
            document.getElementById('http_client_disconnect')?.removeAttribute('disabled');
            document.getElementById('http_client_refresh_file_list')?.removeAttribute('disabled');
            document.getElementById('http_client_download_btn')?.removeAttribute('disabled');
            if (http.file_list && document.getElementById('http_client_file_list').innerHTML.includes('未连接')) {
                refreshHttpFileList();
            }
        } else {
            document.getElementById('http_client_connect')?.removeAttribute('disabled');
            document.getElementById('http_client_disconnect')?.setAttribute('disabled', 'disabled');
            document.getElementById('http_client_refresh_file_list')?.setAttribute('disabled', 'disabled');
            document.getElementById('http_client_download_btn')?.setAttribute('disabled', 'disabled');
        }
        
        // 更新FTP客户端状态和按钮（不自动连接，只更新状态显示）
        const ftpRunning = ftp.running === true;
        const connectBtn = document.getElementById('ftp_client_connect');
        const isManuallyConnecting = connectBtn && connectBtn.innerHTML.includes('连接中');
        
        // 更新状态徽章（无论是否正在连接）
        // 统一处理FTP客户端状态，确保一致性
        updateBadge('ftp_client_status', ftpRunning ? '已连接' : '未连接', ftpRunning);
        
        // 无论是否正在手动连接，都要更新按钮状态（但正在连接时只更新状态徽章）
        if (ftpRunning) {
            // 如果已经连接，更新按钮状态和内容
            if (connectBtn && !connectBtn.disabled) {
                // 如果连接按钮未禁用，说明是刚连接成功，更新状态
                connectBtn.disabled = true;
                connectBtn.innerHTML = '<i class="fas fa-link me-1"></i>连接';
                document.getElementById('ftp_client_disconnect')?.removeAttribute('disabled');
                document.getElementById('ftp_client_refresh_dir')?.removeAttribute('disabled');
                document.getElementById('ftp_client_refresh_file_list')?.removeAttribute('disabled');
                document.getElementById('ftp_client_refresh_local_files')?.removeAttribute('disabled');
                document.getElementById('ftp_client_upload_btn')?.removeAttribute('disabled');
                document.getElementById('ftp_client_download_btn')?.removeAttribute('disabled');
                // 刷新文件列表
                setTimeout(() => {
                    refreshFtpFileList();
                    refreshLocalFileList();
                }, 500);
            } else if (connectBtn && connectBtn.disabled && !isManuallyConnecting) {
                // 如果已经连接且按钮已禁用（不是正在连接），确保所有按钮都启用
                document.getElementById('ftp_client_disconnect')?.removeAttribute('disabled');
                document.getElementById('ftp_client_refresh_dir')?.removeAttribute('disabled');
                document.getElementById('ftp_client_refresh_file_list')?.removeAttribute('disabled');
                document.getElementById('ftp_client_refresh_local_files')?.removeAttribute('disabled');
                document.getElementById('ftp_client_upload_btn')?.removeAttribute('disabled');
                document.getElementById('ftp_client_download_btn')?.removeAttribute('disabled');
                // 更新当前目录
                if (ftp.current_dir) {
                    document.getElementById('ftp_client_current_dir').value = ftp.current_dir;
                }
                // 更新文件列表（仅在状态更新时，不自动刷新）
                if (ftp.file_list && document.getElementById('ftp_client_file_list').innerHTML.includes('未连接')) {
                    refreshFtpFileList();
                }
                // 如果本地文件列表为空，刷新它
                const localFileList = document.getElementById('ftp_client_local_file_list');
                if (localFileList && (localFileList.innerHTML.includes('未连接') || localFileList.innerHTML.includes('目录为空'))) {
                    refreshLocalFileList();
                }
            }
        } else {
            // 未连接状态：确保按钮状态正确（但不要覆盖正在连接的状态）
            if (connectBtn && connectBtn.disabled && !isManuallyConnecting) {
                // 如果连接按钮被禁用但状态显示未连接，恢复按钮状态
                connectBtn.removeAttribute('disabled');
                connectBtn.innerHTML = '<i class="fas fa-link me-1"></i>连接';
                document.getElementById('ftp_client_disconnect')?.setAttribute('disabled', 'disabled');
                document.getElementById('ftp_client_refresh_dir')?.setAttribute('disabled', 'disabled');
                document.getElementById('ftp_client_refresh_file_list')?.setAttribute('disabled', 'disabled');
                document.getElementById('ftp_client_refresh_local_files')?.setAttribute('disabled', 'disabled');
                document.getElementById('ftp_client_upload_btn')?.setAttribute('disabled', 'disabled');
                document.getElementById('ftp_client_download_btn')?.setAttribute('disabled', 'disabled');
            }
        }
    }

    function updateBadge(id, text, running) {
        const badge = document.getElementById(id);
        if (!badge) return;
        
        // 如果text是boolean，则running = text
        if (typeof text === 'boolean') {
            running = text;
            text = running ? '运行中' : '已停止';
        }
        
        if (text !== undefined) {
            badge.textContent = text;
        } else {
            badge.textContent = running ? '运行中' : '已停止';
        }
        
        // 监听服务状态：运行中显示绿色，已停止显示灰色
        if (id === 'tcp_listener_status' || id === 'udp_listener_status' || id === 'ftp_listener_status' || id === 'http_listener_status') {
            badge.className = running ? 'badge bg-success' : 'badge bg-secondary';
        }
        // 客户端状态：已连接/运行中显示绿色，未连接/已停止显示灰色
        else if (id === 'ftp_client_status' || id === 'tcp_client_status' || id === 'udp_client_status') {
            badge.className = running ? 'badge bg-success' : 'badge bg-secondary';
        } else {
            badge.className = running ? 'badge bg-success' : 'badge bg-secondary';
        }
    }

    function startLocalMailService() {
        addLogEntry('正在启动本地邮件服务（使用PsExec远程执行）...', 'info');
        
        const btn = document.getElementById('start_local_mail_service_btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>启动中...';
        }
        
        // 从监听服务代理程序URL中提取IP地址
        let remoteIp = '';
        if (listenerAgentUrl) {
            try {
                const urlObj = new URL(listenerAgentUrl);
                remoteIp = urlObj.hostname;
            } catch (e) {
                console.error('无法解析监听服务代理程序URL:', e);
            }
        }
        
        // 如果无法从listenerAgentUrl获取，提示用户输入
        if (!remoteIp) {
            addLogEntry('无法获取远程IP地址，请先连接监听服务代理程序', 'warning');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-server me-1"></i>启动本地邮件服务';
            }
            return;
        }
        
        // 尝试从测试环境配置中获取用户名和密码
        let remoteUsername = 'tdhx';  // 默认值
        let remotePassword = 'tdhx@2017';  // 默认值
        
        const matchedEnv = testEnvironments.find(env => env.ip === remoteIp);
        if (matchedEnv && (matchedEnv.user || matchedEnv.username)) {
            remoteUsername = matchedEnv.user || matchedEnv.username;
            addLogEntry(`从测试环境配置获取用户名: ${remoteUsername}`, 'info');
        }
        if (matchedEnv && matchedEnv.password) {
            remotePassword = matchedEnv.password;
            addLogEntry(`从测试环境配置获取密码`, 'info');
        }
        
        addLogEntry(`准备远程执行: ${remoteIp} (用户: ${remoteUsername})`, 'info');
        
        // 调用Django后端的API，在Django服务器本地执行PsExec命令
        fetch('/api/services/local-mail/start/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                remote_ip: remoteIp,
                username: remoteUsername,
                password: remotePassword
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                addLogEntry(`本地邮件服务启动成功: ${data.message || ''}`, 'success');
            } else {
                addLogEntry(`本地邮件服务启动失败: ${data.error || '未知错误'}`, 'error');
                if (data.stderr) {
                    addLogEntry(`错误详情: ${data.stderr}`, 'error');
                }
            }
        })
        .catch(err => {
            addLogEntry(`启动本地邮件服务时发生错误: ${err.message}`, 'error');
        })
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-server me-1"></i>启动本地邮件服务';
            }
        });
    }

    function sendListenerCommand(protocol, action) {
        console.log('*** 发送监听命令:', protocol, action, '***');
        console.log('*** 函数开始时mailAccounts长度:', mailAccounts.length);
        addLogEntry(`正在执行${protocol}服务${action === 'start' ? '启动' : '停止'}...`, 'info');
        
        if (!listenerAgentUrl) {
            addLogEntry('请先连接监听服务代理程序', 'warning');
            return;
        }
        
        let port = 0;
        if (protocol === 'mail') {
            // 邮件协议需要验证三个端口
            const smtpPortInput = document.getElementById('mail_listener_smtp_port');
            const imapPortInput = document.getElementById('mail_listener_imap_port');
            const pop3PortInput = document.getElementById('mail_listener_pop3_port');
            const smtpPort = parseInt(smtpPortInput ? smtpPortInput.value : '0', 10);
            const imapPort = parseInt(imapPortInput ? imapPortInput.value : '0', 10);
            const pop3Port = parseInt(pop3PortInput ? pop3PortInput.value : '0', 10);
            
            if (action === 'start') {
                if ((!smtpPort || smtpPort < 1 || smtpPort > 65535) || 
                    (!imapPort || imapPort < 1 || imapPort > 65535) || 
                    (!pop3Port || pop3Port < 1 || pop3Port > 65535)) {
                    addLogEntry('SMTP、IMAP或POP3端口无效', 'warning');
                    return;
                }
            }
            port = smtpPort; // 使用SMTP端口作为主端口
        } else {
            const portInput = document.getElementById(`${protocol}_listener_port`);
            port = parseInt(portInput ? portInput.value : '0', 10);
            if (action === 'start' && (!port || port < 1 || port > 65535)) {
                addLogEntry('端口无效', 'warning');
                return;
            }
        }
        const payload = {
            agent_url: listenerAgentUrl,  // 确保使用监听服务代理URL
            protocol,
            action,
            port,
            host: getSelectedInterfaceIp(true) || '0.0.0.0'
        };
        // FTP服务器特殊配置
        if (protocol === 'ftp' && action === 'start') {
            const usernameInput = document.getElementById('ftp_listener_username');
            const passwordInput = document.getElementById('ftp_listener_password');
            const directoryInput = document.getElementById('ftp_listener_directory');
            if (usernameInput) payload.username = usernameInput.value.trim() || 'tdhx';
            if (passwordInput) payload.password = passwordInput.value.trim() || 'tdhx@2017';
            if (directoryInput) {
                const dir = directoryInput.value.trim();
                if (dir) payload.directory = dir;
            }
        }
        // HTTP服务器特殊配置
        if (protocol === 'http' && action === 'start') {
            const directoryInput = document.getElementById('http_listener_directory');
            if (directoryInput) {
                const dir = directoryInput.value.trim();
                if (dir) payload.directory = dir;
            }
        }
        // 邮件服务器特殊配置
        if (protocol === 'mail' && action === 'start') {
            const smtpPortInput = document.getElementById('mail_listener_smtp_port');
            const imapPortInput = document.getElementById('mail_listener_imap_port');
            const pop3PortInput = document.getElementById('mail_listener_pop3_port');
            const domainInput = document.getElementById('mail_listener_domain');
            payload.smtp_port = parseInt(smtpPortInput ? smtpPortInput.value : '25', 10);
            payload.imap_port = parseInt(imapPortInput ? imapPortInput.value : '143', 10);
            payload.pop3_port = parseInt(pop3PortInput ? pop3PortInput.value : '110', 10);
            payload.domain = domainInput ? domainInput.value.trim() || 'autotest.com' : 'autotest.com';
            payload.ssl_enabled = false; // 不支持SSL
            
            // 使用内存中存储的账户信息（包含实际密码）
            console.log('*** 发送前检查mailAccounts:', mailAccounts);
            console.log('*** mailAccounts长度:', mailAccounts.length);
            console.log('*** mailAccounts内容:', JSON.stringify(mailAccounts));
            payload.accounts = mailAccounts;
        }
        fetch('/api/services/listener/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(payload)
        })
            .then(res => {
                const contentType = res.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return res.json();
                } else {
                    return res.text().then(text => {
                        try {
                            return JSON.parse(text);
                        } catch (e) {
                            throw new Error(`响应不是有效的JSON: ${text.substring(0, 100)}`);
                        }
                    });
                }
            })
            .then(data => {
                if (data.success) {
                    addLogEntry(data.message || `${protocol.toUpperCase()}监听${action === 'start' ? '已启动' : '已停止'}`, 'success');
                    // 等待后端返回结果后，立即更新状态
                    // 延迟一小段时间确保后端状态已更新，然后立即获取状态
                    setTimeout(() => {
                        fetchStatus();
                    }, 300);
                    // 再次延迟更新，确保状态同步
                    setTimeout(() => {
                        fetchStatus();
                    }, 1000);
                } else {
                    addLogEntry(data.error || '操作失败', 'error');
                }
            })
            .catch(err => addLogEntry(`控制监听失败: ${err.message}`, 'error'));
    }

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
                    // 延迟一小段时间确保后端状态已更新，然后立即获取状态
                    setTimeout(() => {
                        fetchStatus();
                    }, 300);
                    // 再次延迟更新，确保状态同步
                    setTimeout(() => {
                        fetchStatus();
                    }, 1000);
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

    // 生成随机MAC地址
    function generateRandomMac() {
        const hex = '0123456789ABCDEF';
        let mac = '';
        for (let i = 0; i < 6; i++) {
            if (i > 0) mac += ':';
            // 第一个字节的第二个字符确保是偶数（本地管理地址）
            if (i === 0) {
                mac += hex[Math.floor(Math.random() * 16)];
                mac += hex[Math.floor(Math.random() * 8) * 2]; // 确保是偶数
            } else {
                mac += hex[Math.floor(Math.random() * 16)];
                mac += hex[Math.floor(Math.random() * 16)];
            }
        }
        return mac;
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
        // 保存当前选中的值
        const listenerSelect = document.getElementById('listener_test_env_select');
        const clientSelect = document.getElementById('client_test_env_select');
        const savedListenerValue = listenerSelect ? listenerSelect.value : '';
        const savedClientValue = clientSelect ? clientSelect.value : '';
        
        fetch('/api/test_env/list/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const envs = data.environments.map(env => ({
                        id: env.id.toString(),
                        name: env.name,
                        ip: env.ip,
                        type: env.type,
                        user: env.ssh_user,
                        password: env.ssh_password,
                        port: env.ssh_port
                    }));
                    testEnvironments = envs;
                    console.log('加载测试环境:', envs.length, '个');
                    
                    // 监听服务代理的测试环境选择
                    if (listenerSelect) {
                        listenerSelect.innerHTML = '<option value="">请选择测试环境</option>';
                        envs.forEach(env => {
                            const option = document.createElement('option');
                            option.value = env.id;
                            option.textContent = `${env.name} (${env.ip}) - ${env.type === 'windows' ? 'Windows' : 'Linux'}`;
                            option.dataset.env = JSON.stringify(env);
                            listenerSelect.appendChild(option);
                        });
                        // 恢复之前选中的值
                        if (savedListenerValue && envs.find(e => e.id === savedListenerValue)) {
                            listenerSelect.value = savedListenerValue;
                        }
                        console.log('监听服务代理测试环境列表已更新:', envs.length, '个');
                    }
                    
                    // 客户端代理的测试环境选择
                    if (clientSelect) {
                        clientSelect.innerHTML = '<option value="">请选择测试环境</option>';
                        envs.forEach(env => {
                            const option = document.createElement('option');
                            option.value = env.id;
                            option.textContent = `${env.name} (${env.ip}) - ${env.type === 'windows' ? 'Windows' : 'Linux'}`;
                            option.dataset.env = JSON.stringify(env);
                            clientSelect.appendChild(option);
                        });
                        // 恢复之前选中的值
                        if (savedClientValue && envs.find(e => e.id === savedClientValue)) {
                            clientSelect.value = savedClientValue;
                        }
                        console.log('客户端代理测试环境列表已更新:', envs.length, '个');
                    }
                }
            })
            .catch(err => console.error('加载测试环境失败:', err));
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
    
    // 监听服务代理连接
    if (listenerConnectBtn) {
        listenerConnectBtn.addEventListener('click', () => {
            const source = document.querySelector('input[name="listener_agent_source"]:checked')?.value || 'test_env';
            let ip = '';
            
            if (source === 'test_env') {
                const envId = document.getElementById('listener_test_env_select').value;
                if (!envId) {
                    addLogEntry('请选择测试环境', 'warning');
                    return;
                }
                const env = testEnvironments.find(e => e.id === envId);
                if (!env) {
                    addLogEntry('测试环境不存在', 'warning');
                    return;
                }
                ip = env.ip;
            } else {
                ip = listenerAgentIpInput.value.trim();
                if (!ip) {
                    addLogEntry('请输入监听服务代理程序IP地址', 'warning');
                    return;
                }
            }
            
            const port = '8888'; // 端口固定为8888
            const url = `http://${ip}:${port}`;
            
            listenerConnectBtn.disabled = true;
            listenerConnectBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>连接中...';
            fetch('/api/agent/interfaces/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ agent_url: url })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        listenerAgentUrl = url;
                        populateInterfaces(data.interfaces || [], true);
                        addLogEntry('监听服务代理程序连接成功', 'success');
                        listenerConnectBtn.classList.remove('btn-primary');
                        listenerConnectBtn.classList.add('btn-success');
                        listenerConnectBtn.innerHTML = '<i class="fas fa-check me-2"></i>已连接';
                        listenerConnectBtn.disabled = true;
                        if (!statusInterval) startPolling();
                    } else {
                        addLogEntry(data.error || '连接失败', 'error');
                        listenerConnectBtn.disabled = false;
                        listenerConnectBtn.innerHTML = '<i class="fas fa-plug me-2"></i>连接';
                    }
                })
                .catch(err => {
                    addLogEntry(`连接失败: ${err.message}`, 'error');
                    listenerConnectBtn.disabled = false;
                    listenerConnectBtn.innerHTML = '<i class="fas fa-plug me-2"></i>连接';
                });
        });
    }

    // 客户端代理连接
    if (clientConnectBtn) {
        clientConnectBtn.addEventListener('click', () => {
            const source = document.querySelector('input[name="client_agent_source"]:checked')?.value || 'test_env';
            let ip = '';
            
            if (source === 'test_env') {
                const envId = document.getElementById('client_test_env_select').value;
                if (!envId) {
                    addLogEntry('请选择测试环境', 'warning');
                    return;
                }
                const env = testEnvironments.find(e => e.id === envId);
                if (!env) {
                    addLogEntry('测试环境不存在', 'warning');
                    return;
                }
                ip = env.ip;
            } else {
                ip = clientAgentIpInput.value.trim();
                if (!ip) {
                    addLogEntry('请输入客户端代理程序IP地址', 'warning');
                    return;
                }
            }
            
            const port = '8888'; // 端口固定为8888
            const url = `http://${ip}:${port}`;
            
            clientConnectBtn.disabled = true;
            clientConnectBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>连接中...';
            fetch('/api/agent/interfaces/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ agent_url: url })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        clientAgentUrl = url;
                        populateInterfaces(data.interfaces || [], false);
                        addLogEntry('客户端代理程序连接成功', 'success');
                        clientConnectBtn.classList.remove('btn-success');
                        clientConnectBtn.classList.add('btn-success');
                        clientConnectBtn.innerHTML = '<i class="fas fa-check me-2"></i>已连接';
                        clientConnectBtn.disabled = true;
                        if (!statusInterval) startPolling();
                    } else {
                        addLogEntry(data.error || '连接失败', 'error');
                        clientConnectBtn.disabled = false;
                        clientConnectBtn.innerHTML = '<i class="fas fa-plug me-2"></i>连接';
                    }
                })
                .catch(err => {
                    addLogEntry(`连接失败: ${err.message}`, 'error');
                    clientConnectBtn.disabled = false;
                    clientConnectBtn.innerHTML = '<i class="fas fa-plug me-2"></i>连接';
                });
        });
    }

    // 监听服务网卡选择
    if (listenerInterfaceSelect) {
        listenerInterfaceSelect.addEventListener('change', () => {
            const ip = listenerInterfaceSelect.value;
            const name = listenerInterfaceSelect.selectedOptions[0]?.dataset.name || '未知';
            const mac = listenerInterfaceSelect.selectedOptions[0]?.dataset.mac || '';
            if (ip) {
                listenerInterfaceInfo.classList.remove('alert-info');
                listenerInterfaceInfo.classList.add('alert-success');
                listenerInterfaceInfo.textContent = `${name} - ${ip} ${mac ? '(' + mac + ')' : ''}`;
            } else {
                listenerInterfaceInfo.classList.remove('alert-success');
                listenerInterfaceInfo.classList.add('alert-info');
                listenerInterfaceInfo.textContent = '未选择网卡';
            }
        });
    }

    // 客户端网卡选择
    if (clientInterfaceSelect) {
        clientInterfaceSelect.addEventListener('change', () => {
            const ip = clientInterfaceSelect.value;
            const name = clientInterfaceSelect.selectedOptions[0]?.dataset.name || '未知';
            const mac = clientInterfaceSelect.selectedOptions[0]?.dataset.mac || '';
            if (ip) {
                clientInterfaceInfo.classList.remove('alert-info');
                clientInterfaceInfo.classList.add('alert-success');
                clientInterfaceInfo.textContent = `${name} - ${ip} ${mac ? '(' + mac + ')' : ''}`;
            } else {
                clientInterfaceInfo.classList.remove('alert-success');
                clientInterfaceInfo.classList.add('alert-info');
                clientInterfaceInfo.textContent = '未选择网卡';
            }
        });
    }

    listenerButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const protocol = btn.dataset.protocol;
            const action = btn.dataset.action;
            sendListenerCommand(protocol, action);
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
            fetchStatus();
            
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
                    fetchStatus();
                }, 300);
                setTimeout(() => {
                    fetchStatus();
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
                fetchStatus();
            }, 300);
            setTimeout(() => {
                fetchStatus();
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
    
    // 格式化文件大小
    function formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
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

    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
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

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
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
                fetchStatus();
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
        }).catch(err => {
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
    
    // 定期检查localStorage变化（因为storage事件只在其他窗口触发）
    // 注意：由于测试环境已存储在数据库中，不再使用localStorage，所以这个检查可以移除或延长间隔
    let lastCheckTime = Date.now();
    setInterval(function() {
        // 只在距离上次检查超过5秒时才检查，避免频繁刷新导致选择被重置
        const now = Date.now();
        if (now - lastCheckTime < 5000) {
            return;
        }
        lastCheckTime = now;
        
        const currentEnvs = JSON.stringify(testEnvironments);
        const storedEnvs = localStorage.getItem('test_environments') || '[]';
        if (currentEnvs !== storedEnvs) {
            loadTestEnvironments();
        }
    }, 5000);  // 改为5秒检查一次，减少频率
})();
});
