/**
 * 服务下发功能模块
 * 用于管理监听服务和客户端服务的代理连接、控制、状态轮询和日志管理
 */

// ========== 配置收集器 ==========
class ServiceConfig {
    /**
     * 收集监听服务配置
     * @param {string} protocol - 协议类型
     * @param {string} agentUrl - 代理地址
     * @param {string} interfaceIp - 绑定的网卡 IP
     * @returns {object} 配置对象
     */
    static collectListenerConfig(protocol, agentUrl, interfaceIp = '') {
        const baseConfig = {
            agent_url: agentUrl,
            protocol: protocol,
            action: 'start',
            interface: interfaceIp
        };

        // 获取端口
        const portInput = document.getElementById(`${protocol}_listener_port`);
        if (portInput) {
            baseConfig.port = parseInt(portInput.value);
        }

        // 协议特定配置
        if (protocol === 'ftp') {
            baseConfig.username = document.getElementById('ftp_listener_username')?.value || 'tdhx';
            baseConfig.password = document.getElementById('ftp_listener_password')?.value || 'tdhx@2017';
            // 获取目录值，如果为空或'/'则发送空字符串让后端使用默认目录 C:\packet_agent
            let dirValue = document.getElementById('ftp_listener_directory')?.value || '';
            if (dirValue === '' || dirValue === '/' || dirValue.trim() === '') {
                baseConfig.directory = '';  // 空字符串让后端使用默认目录
            } else {
                baseConfig.directory = dirValue;
            }
        } else if (protocol === 'mail') {
            baseConfig.smtp_port = parseInt(document.getElementById('mail_listener_smtp_port')?.value) || 25;
            baseConfig.imap_port = parseInt(document.getElementById('mail_listener_imap_port')?.value) || 143;
            baseConfig.pop3_port = parseInt(document.getElementById('mail_listener_pop3_port')?.value) || 110;
            baseConfig.domain = document.getElementById('mail_listener_domain')?.value || 'autotest.com';

            // 获取账户列表
            const accountsTable = document.getElementById('mail_accounts_list');
            if (accountsTable) {
                const rows = accountsTable.querySelectorAll('tr[data-account]');
                baseConfig.accounts = Array.from(rows).map(row => ({
                    username: row.dataset.username,
                    password: row.dataset.password
                }));
            }
        } else if (protocol === 'http') {
            // 获取目录值，如果为空或'/'则发送空字符串让后端使用默认目录
            let dirValue = document.getElementById('http_listener_directory')?.value || '';
            if (dirValue === '' || dirValue === '/' || dirValue.trim() === '') {
                baseConfig.directory = '';  // 空字符串让后端使用默认目录
            } else {
                baseConfig.directory = dirValue;
            }
        }

        return baseConfig;
    }

    /**
     * 收集 TCP 客户端配置
     * @returns {object} TCP 客户端配置
     */
    static collectTcpClientConfig() {
        return {
            server_ip: document.getElementById('tcp_client_server')?.value || '',
            server_port: parseInt(document.getElementById('tcp_client_port')?.value || '0', 10),
            connections: parseInt(document.getElementById('tcp_client_connections')?.value || '1', 10),
            connect_rate: parseFloat(document.getElementById('tcp_client_rate')?.value || '1'),
            send_interval: parseFloat(document.getElementById('tcp_client_interval')?.value || '1'),
            message: document.getElementById('tcp_client_message')?.value || ''
        };
    }

    /**
     * 收集 UDP 客户端配置
     * @returns {object} UDP 客户端配置
     */
    static collectUdpClientConfig() {
        return {
            server_ip: document.getElementById('udp_client_server')?.value || '',
            server_port: parseInt(document.getElementById('udp_client_port')?.value || '0', 10),
            connections: parseInt(document.getElementById('udp_client_connections')?.value || '1', 10),
            send_interval: parseFloat(document.getElementById('udp_client_interval')?.value || '1'),
            message: document.getElementById('udp_client_message')?.value || ''
        };
    }

    /**
     * 收集 FTP 客户端配置
     * @returns {object} FTP 客户端配置
     */
    static collectFtpClientConfig() {
        return {
            server_ip: document.getElementById('ftp_client_server')?.value || '',
            server_port: parseInt(document.getElementById('ftp_client_port')?.value || '21', 10),
            username: document.getElementById('ftp_client_username')?.value || 'tdhx',
            password: document.getElementById('ftp_client_password')?.value || 'tdhx@2017'
        };
    }

    /**
     * 收集 HTTP 客户端配置
     * @returns {object} HTTP 客户端配置
     */
    static collectHttpClientConfig() {
        return {
            server_ip: document.getElementById('http_client_server')?.value || '',
            server_port: parseInt(document.getElementById('http_client_port')?.value || '80', 10)
        };
    }

    /**
     * 验证地址配置
     * @param {object} config - 配置对象
     * @returns {[boolean, string]} [是否有效，错误消息]
     */
    static validateAddress(config) {
        if (!config.server_ip) {
            return [false, '请输入服务器地址'];
        }
        if (!config.server_port || config.server_port < 1 || config.server_port > 65535) {
            return [false, '服务器端口无效'];
        }
        return [true, ''];
    }
}

// ========== 统一 API 客户端 ==========
class ApiClient {
    constructor() {
        this.timeout = 30000; // 30 秒超时
    }

    /**
     * 发送 HTTP 请求
     * @param {string} url - 请求 URL
     * @param {object} options - 请求选项
     * @returns {Promise<object>} 响应数据
     */
    async request(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options, signal: controller.signal });
            clearTimeout(timeoutId);

            // 尝试解析 JSON 响应
            let data;
            try {
                data = await response.json();
            } catch (e) {
                // 如果响应不是 JSON，返回原始状态
                data = { error: `HTTP ${response.status}`, raw_status: response.status };
            }

            // 对于 400/500 错误，返回数据但不抛出异常（让调用方处理业务逻辑错误）
            // 只对网络错误或超时抛出异常
            if (!response.ok) {
                // 返回错误数据，让调用方决定是否视为异常
                return { ...data, http_status: response.status };
            }

            return data;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('请求超时');
            }
            // 网络错误才抛出异常
            throw error;
        }
    }

    /**
     * POST 请求
     * @param {string} url - 请求 URL
     * @param {object} data - 请求数据
     * @returns {Promise<object>} 响应数据
     */
    async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * GET 请求
     * @param {string} url - 请求 URL
     * @param {object} params - 查询参数
     * @returns {Promise<object>} 响应数据
     */
    async get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        return this.request(fullUrl, { method: 'GET' });
    }

    /**
     * 调用监听服务 API
     * @param {object} payload - 请求负载
     * @returns {Promise<object>} 响应数据
     */
    async callListenerService(payload) {
        return this.post('/api/services/listener/', payload);
    }

    /**
     * 调用客户端服务 API
     * @param {string} agentUrl - 代理地址
     * @param {object} payload - 请求负载
     * @returns {Promise<object>} 响应数据
     */
    async callClientService(agentUrl, payload) {
        return this.post(`${agentUrl}/api/services/client`, payload);
    }

    /**
     * 获取服务状态
     * @param {object} params - 查询参数
     * @returns {Promise<object>} 响应数据
     */
    async getServiceStatus(params = {}) {
        return this.get('/api/services/status/', params);
    }

    /**
     * 获取服务日志
     * @param {string} agentUrl - 代理地址
     * @param {number} limit - 日志条数
     * @returns {Promise<object>} 响应数据
     */
    async getServiceLogs(agentUrl, limit = 30) {
        return this.get('/api/services/logs/', { agent_url: agentUrl, limit });
    }

    /**
     * 获取网卡列表
     * @param {string} agentUrl - 代理地址
     * @returns {Promise<object>} 响应数据
     */
    async getInterfaces(agentUrl) {
        return this.get(`${agentUrl}/api/interfaces`);
    }
}

// ========== 工具函数 ==========
const Utils = {
    /**
     * 添加日志条目
     * @param {string} message - 日志消息
     * @param {string} level - 日志级别 (info, warning, error, success)
     * @param {HTMLElement} logList - 日志列表元素
     */
    addLogEntry(message, level = 'info', logList) {
        if (!logList) return;

        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';

        const badgeClass = {
            'error': 'bg-danger',
            'warning': 'bg-warning text-dark',
            'success': 'bg-success',
            'info': 'bg-secondary'
        }[level] || 'bg-secondary';

        const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });
        li.innerHTML = `<span>[${timestamp}] ${message}</span><span class="badge ${badgeClass}">${level.toUpperCase()}</span>`;

        logList.prepend(li);

        // 限制日志数量
        while (logList.children.length > 200) {
            logList.removeChild(logList.lastChild);
        }
    },

    /**
     * 显示 Toast 通知
     * @param {string} message - 通知消息
     * @param {string} type - 通知类型 (success, error, info, warning)
     */
    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        toastContainer.appendChild(toast);

        setTimeout(() => toast.remove(), 5000);
    },

    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    },

    /**
     * HTML 转义
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 获取 Cookie
     */
    getCookie(name) {
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
    },

    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Unicode 解码
     */
    decodeUnicodeString(str) {
        if (!str) return str;
        try {
            return str.replace(/\\u[\dA-F]{4}/gi, function (match) {
                return String.fromCharCode(parseInt(match.replace(/\\u/g, ''), 16));
            });
        } catch (e) {
            return str;
        }
    },

    /**
     * 生成随机 MAC 地址
     */
    generateRandomMac() {
        const hex = '0123456789ABCDEF';
        let mac = '';
        for (let i = 0; i < 6; i++) {
            if (i > 0) mac += ':';
            if (i === 0) {
                mac += hex[Math.floor(Math.random() * 16)];
                mac += hex[Math.floor(Math.random() * 8) * 2];
            } else {
                mac += hex[Math.floor(Math.random() * 16)];
                mac += hex[Math.floor(Math.random() * 16)];
            }
        }
        return mac;
    }
};

// ========== 代理连接器 ==========
class AgentConnector {
    constructor(type, config) {
        this.type = type; // 'listener' or 'client'
        this.agentUrl = '';
        this.interfacesData = [];
        this.isConnected = false;
        this.apiClient = new ApiClient();

        // DOM 元素
        this.connectBtn = config.connectBtn;
        this.agentIpInput = config.agentIpInput;
        this.agentPortInput = config.agentPortInput;
        this.interfaceSelect = config.interfaceSelect;
        this.interfaceInfo = config.interfaceInfo;
        this.testEnvSelect = config.testEnvSelect;
        this.customIpContainer = config.customIpContainer;
        this.testEnvContainer = config.testEnvContainer;

        this.logList = config.logList;

        // IP 来源 (test_env or custom)
        this.ipSource = 'test_env';

        this.bindEvents();
    }

    bindEvents() {
        // 连接按钮
        if (this.connectBtn) {
            this.connectBtn.addEventListener('click', () => this.connect());
        }

        // IP 来源切换
        const ipSourceRadios = document.querySelectorAll(`input[name="${this.type}_agent_source"]`);
        ipSourceRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.ipSource = e.target.value;
                this.toggleIpSource();
            });
        });

        // 初始化 IP 来源显示状态
        this.toggleIpSource();

        // 网卡选择变化
        if (this.interfaceSelect) {
            this.interfaceSelect.addEventListener('change', () => this.onInterfaceChange());
        }
    }

    toggleIpSource() {
        if (this.testEnvContainer) {
            this.testEnvContainer.style.display = this.ipSource === 'test_env' ? 'block' : 'none';
        }
        if (this.customIpContainer) {
            this.customIpContainer.style.display = this.ipSource === 'custom' ? 'block' : 'none';
        }
    }

    /**
     * 连接到代理程序
     */
    async connect() {
        const loadingBtn = this.connectBtn;
        const originalText = loadingBtn.innerHTML;
        loadingBtn.disabled = true;
        loadingBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 连接中...';

        try {
            let agentIp = '';
            let agentPort = '8888';

            if (this.ipSource === 'test_env') {
                const testEnvSelect = this.testEnvSelect;
                if (!testEnvSelect || !testEnvSelect.value) {
                    Utils.showToast('请选择测试环境', 'warning');
                    return;
                }
                const selectedOption = testEnvSelect.selectedOptions[0];
                agentIp = selectedOption.dataset.envIp || selectedOption.value;
                agentPort = selectedOption.dataset.port || '8888';
            } else {
                agentIp = this.agentIpInput?.value.trim();
                agentPort = this.agentPortInput?.value || '8888';
            }

            if (!agentIp) {
                Utils.showToast('请输入代理程序 IP 地址', 'warning');
                return;
            }

            this.agentUrl = `http://${agentIp}:${agentPort}`;

            // 获取网卡列表
            const data = await this.apiClient.getInterfaces(this.agentUrl);

            if (data.success) {
                this.isConnected = true;
                this.interfacesData = data.interfaces || [];
                this.populateInterfaces(this.interfacesData);
                Utils.addLogEntry(`${this.type === 'listener' ? '监听服务' : '客户端'}代理已连接：${this.agentUrl}`, 'success', this.logList);
                Utils.showToast('连接成功', 'success');

                // 触发连接成功事件
                window.dispatchEvent(new CustomEvent(`agent:connected:${this.type}`, {
                    detail: { agentUrl: this.agentUrl, interfaces: this.interfacesData }
                }));
            } else {
                throw new Error(data.error || '连接失败');
            }
        } catch (error) {
            this.isConnected = false;
            this.agentUrl = '';
            Utils.addLogEntry(`连接失败：${error.message}`, 'error', this.logList);
            Utils.showToast(`连接失败：${error.message}`, 'error');

            if (this.interfaceSelect) {
                this.interfaceSelect.innerHTML = '<option value="">连接失败</option>';
                this.interfaceSelect.disabled = true;
            }
        } finally {
            loadingBtn.disabled = false;
            loadingBtn.innerHTML = originalText;
        }
    }

    /**
     * 填充网卡下拉列表
     */
    populateInterfaces(interfaces) {
        if (!this.interfaceSelect) return;

        this.interfaceSelect.innerHTML = '';

        if (interfaces.length === 0) {
            this.interfaceSelect.innerHTML = '<option value="">未获取到网卡</option>';
            this.interfaceSelect.disabled = true;
            return;
        }

        this.interfaceSelect.disabled = false;
        this.interfaceSelect.innerHTML = '<option value="">请选择网卡</option>';

        interfaces.forEach((iface, index) => {
            // 支持多个 IP 地址：如果有 ips 数组则使用，否则使用单个 ip
            const ipList = iface.ips || (iface.ip ? [iface.ip] : []);
            const ipDisplay = ipList.join(', ') || '无 IP';
            
            const option = document.createElement('option');
            // 使用第一个 IP 作为值
            option.value = ipList[0] || '';
            option.dataset.mac = iface.mac || '';
            option.dataset.name = iface.display_name || iface.name || `接口${index + 1}`;
            option.dataset.allIps = ipList.join(',');  // 存储所有 IP
            option.textContent = `${option.dataset.name} (${ipDisplay})`;
            this.interfaceSelect.appendChild(option);
        });
    }

    /**
     * 网卡选择变化处理
     */
    onInterfaceChange() {
        if (!this.interfaceSelect || !this.interfaceInfo) return;

        const selectedOption = this.interfaceSelect.selectedOptions[0];
        if (selectedOption.value) {
            this.interfaceInfo.innerHTML = `
                <i class="fas fa-network-wired me-2"></i>
                已选择：${selectedOption.dataset.name} (${selectedOption.value})
            `;
            this.interfaceInfo.className = 'alert alert-success mb-0';
        } else {
            this.interfaceInfo.innerHTML = '未选择网卡';
            this.interfaceInfo.className = 'alert alert-info mb-0';
        }
    }

    /**
     * 断开连接
     */
    disconnect() {
        this.isConnected = false;
        this.agentUrl = '';
        this.interfacesData = [];

        if (this.interfaceSelect) {
            this.interfaceSelect.innerHTML = '<option value="">请先连接代理程序</option>';
            this.interfaceSelect.disabled = true;
        }

        if (this.interfaceInfo) {
            this.interfaceInfo.innerHTML = '未选择网卡';
            this.interfaceInfo.className = 'alert alert-info mb-0';
        }

        Utils.addLogEntry(`${this.type === 'listener' ? '监听服务' : '客户端'}代理已断开`, 'info', this.logList);

        window.dispatchEvent(new CustomEvent(`agent:disconnected:${this.type}`, {
            detail: { type: this.type }
        }));
    }

    /**
     * 获取选中的网卡 IP
     */
    getSelectedInterfaceIp() {
        return this.interfaceSelect?.value || '';
    }
}

// ========== 状态轮询器 ==========
class StatusPoller {
    constructor() {
        this.listenerAgentUrl = '';
        this.clientAgentUrl = '';
        this.statusInterval = null;
        this.logsInterval = null;
        this.hasActiveConnection = false;
        this.pollingInterval = 5000;
        this.apiClient = new ApiClient();

        this.logList = document.getElementById('service_log_list');
    }

    /**
     * 更新代理 URL
     */
    updateAgentUrls(listenerUrl, clientUrl) {
        const oldListenerUrl = this.listenerAgentUrl;
        const oldClientUrl = this.clientAgentUrl;

        this.listenerAgentUrl = listenerUrl;
        this.clientAgentUrl = clientUrl;

        this.hasActiveConnection = !!(listenerUrl || clientUrl);

        // 检测 URL 变化
        if (listenerUrl !== oldListenerUrl) {
            window.dispatchEvent(new CustomEvent('agent:urlchange:listener', { detail: { url: listenerUrl } }));
        }
        if (clientUrl !== oldClientUrl) {
            window.dispatchEvent(new CustomEvent('agent:urlchange:client', { detail: { url: clientUrl } }));
        }

        this.updatePolling();
    }

    /**
     * 动态调整轮询
     */
    updatePolling() {
        if (this.hasActiveConnection && !this.statusInterval) {
            this.start();
        } else if (!this.hasActiveConnection && this.statusInterval) {
            this.stop();
        }
    }

    /**
     * 开始轮询
     */
    start() {
        this.stop();
        this.fetchStatus();
        this.fetchLogs();

        this.statusInterval = setInterval(() => this.fetchStatus(), this.pollingInterval);
        this.logsInterval = setInterval(() => this.fetchLogs(), this.pollingInterval);
    }

    /**
     * 停止轮询
     */
    stop() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
            this.statusInterval = null;
        }
        if (this.logsInterval) {
            clearInterval(this.logsInterval);
            this.logsInterval = null;
        }
    }

    /**
     * 获取服务状态
     */
    async fetchStatus() {
        const params = {};
        if (this.listenerAgentUrl) {
            params.listener_agent_url = this.listenerAgentUrl;
        }
        if (this.clientAgentUrl) {
            params.client_agent_url = this.clientAgentUrl;
        }

        if (!this.listenerAgentUrl && !this.clientAgentUrl) {
            return;
        }

        try {
            const data = await this.apiClient.getServiceStatus(params);

            if (data.success) {
                window.dispatchEvent(new CustomEvent('service:statusupdate', {
                    detail: {
                        listeners: data.listeners || {},
                        clients: data.clients || {}
                    }
                }));
            }
        } catch (error) {
            // 静默处理状态获取失败
        }
    }

    /**
     * 获取服务日志
     */
    async fetchLogs() {
        const logs = [];
        const promises = [];

        if (this.listenerAgentUrl) {
            promises.push(
                this.apiClient.getServiceLogs(this.listenerAgentUrl, 30)
                    .then(data => {
                        if (data.success && data.logs) {
                            data.logs.forEach(log => {
                                log.source_tag = '监听服务';
                                log.agent_type = 'listener';
                            });
                            logs.push(...data.logs);
                        }
                    })
                    .catch(() => {})
            );
        }

        if (this.clientAgentUrl) {
            promises.push(
                this.apiClient.getServiceLogs(this.clientAgentUrl, 30)
                    .then(data => {
                        if (data.success && data.logs) {
                            data.logs.forEach(log => {
                                log.source_tag = '客户端';
                                log.agent_type = 'client';
                            });
                            logs.push(...data.logs);
                        }
                    })
                    .catch(() => {})
            );
        }

        try {
            await Promise.all(promises);

            // 按时间戳排序
            logs.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

            if (logs.length > 0) {
                window.dispatchEvent(new CustomEvent('service:logsupdate', { detail: { logs } }));
            }
        } catch (error) {
            // 静默处理日志获取失败
        }
    }
}

// ========== 监听服务管理器 ==========
class ListenerServiceManager {
    constructor(agentConnector, poller, logList) {
        this.connector = agentConnector;
        this.poller = poller;
        this.logList = logList;
        this.apiClient = new ApiClient();

        this.bindEvents();
    }

    bindEvents() {
        const buttons = document.querySelectorAll('[data-role="listener-btn"]');
        buttons.forEach(btn => {
            btn.addEventListener('click', (e) => this.handleButtonClick(e));
        });

        // 监听连接成功事件
        window.addEventListener('agent:connected:listener', (e) => {
            this.poller.updateAgentUrls(e.detail.agentUrl, this.poller.clientAgentUrl);
        });

        // 监听 URL 变化
        window.addEventListener('agent:urlchange:listener', (e) => {
            this.poller.updateAgentUrls(e.detail.url, this.poller.clientAgentUrl);
        });
    }

    async handleButtonClick(e) {
        const btn = e.currentTarget;
        const protocol = btn.dataset.protocol;
        const action = btn.dataset.action;

        if (!this.connector.agentUrl) {
            Utils.showToast('请先连接监听服务代理', 'warning');
            return;
        }

        const loadingBtn = btn;
        const originalText = loadingBtn.innerHTML;
        loadingBtn.disabled = true;
        loadingBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';

        try {
            const interfaceIp = this.connector.getSelectedInterfaceIp();
            const payload = ServiceConfig.collectListenerConfig(protocol, this.connector.agentUrl, interfaceIp);
            payload.action = action;

            const data = await this.apiClient.callListenerService(payload);

            if (data.success) {
                Utils.addLogEntry(`${protocol.toUpperCase()} ${action === 'start' ? '启动' : '停止'}成功`, 'success', this.logList);
                Utils.showToast(`${action === 'start' ? '启动' : '停止'}成功`, 'success');

                // 不立即恢复按钮状态，等待状态轮询更新
                // 这样避免按钮闪烁
                // 但是立即刷新状态（300ms 后），减少等待时间
                setTimeout(() => this.poller.fetchStatus(), 300);
            } else {
                throw new Error(data.error || '操作失败');
            }
        } catch (error) {
            Utils.addLogEntry(`${protocol.toUpperCase()} ${action === 'start' ? '启动' : '停止'}失败：${error.message}`, 'error', this.logList);
            Utils.showToast(`操作失败：${error.message}`, 'error');
            // 只在失败时恢复按钮状态
            loadingBtn.disabled = false;
            loadingBtn.innerHTML = originalText;
        }
    }
}

// ========== 状态显示更新器 ==========
class StatusDisplayUpdater {
    constructor() {
        this.bindEvents();
    }

    bindEvents() {
        window.addEventListener('service:statusupdate', (e) => {
            this.updateListenerStatus(e.detail.listeners);
            this.updateClientStatus(e.detail.clients);
        });
    }

    updateBadge(id, text, running) {
        const badge = document.getElementById(id);
        if (!badge) return;

        if (typeof text === 'boolean') {
            running = text;
            text = running ? '运行中' : '已停止';
        }

        if (text !== undefined) {
            badge.textContent = text;
        } else {
            badge.textContent = running ? '运行中' : '已停止';
        }

        badge.className = running ? 'badge bg-success' : 'badge bg-secondary';
    }

    /**
     * 更新监听服务按钮状态
     * @param {string} protocol - 协议类型 (tcp, udp, ftp, http, mail)
     * @param {boolean} isRunning - 是否运行中
     */
    updateListenerButtonState(protocol, isRunning) {
        const startBtn = document.querySelector(`button[data-role="listener-btn"][data-protocol="${protocol}"][data-action="start"]`);
        const stopBtn = document.querySelector(`button[data-role="listener-btn"][data-protocol="${protocol}"][data-action="stop"]`);

        if (isRunning) {
            // 运行中：启动按钮显示"运行中"（置灰），停止按钮显示"停止"（红色可用）
            if (startBtn) {
                startBtn.disabled = true;
                startBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i>运行中';
                startBtn.classList.add('btn-outline-success');
                startBtn.classList.remove('btn-success');
            }
            if (stopBtn) {
                stopBtn.disabled = false;
                stopBtn.innerHTML = '<i class="fas fa-stop me-1"></i>停止';
                stopBtn.classList.remove('btn-outline-danger');
                stopBtn.classList.add('btn-danger');
            }
        } else {
            // 已停止：启动按钮显示"启动"（绿色可用），停止按钮显示"已停止"（置灰）
            if (startBtn) {
                startBtn.disabled = false;
                startBtn.innerHTML = '<i class="fas fa-play me-1"></i>启动';
                startBtn.classList.remove('btn-outline-success');
                startBtn.classList.add('btn-success');
            }
            if (stopBtn) {
                stopBtn.disabled = true;
                stopBtn.innerHTML = '<i class="fas fa-stop me-1"></i>已停止';
                stopBtn.classList.add('btn-outline-danger');
                stopBtn.classList.remove('btn-danger');
            }
        }
    }

    updateListenerStatus(listeners) {
        const tcpStatus = listeners.tcp || { running: false };
        const udpStatus = listeners.udp || { running: false };
        const ftpStatus = listeners.ftp || { running: false };
        const httpStatus = listeners.http || { running: false };
        const mailStatus = listeners.mail || { running: false };

        this.updateBadge('tcp_listener_status', tcpStatus.running === true);
        this.updateBadge('udp_listener_status', udpStatus.running === true);
        this.updateBadge('ftp_listener_status', ftpStatus.running === true);
        this.updateBadge('http_listener_status', httpStatus.running === true);
        this.updateBadge('mail_listener_status', mailStatus.running === true);

        // 更新按钮状态：运行中时启动按钮置灰，停止时停止按钮置灰
        this.updateListenerButtonState('tcp', tcpStatus.running === true);
        this.updateListenerButtonState('udp', udpStatus.running === true);
        this.updateListenerButtonState('ftp', ftpStatus.running === true);
        this.updateListenerButtonState('http', httpStatus.running === true);
        this.updateListenerButtonState('mail', mailStatus.running === true);

        // 更新 HTTP 服务访问地址
        if (httpStatus.running) {
            const port = httpStatus.port || document.getElementById('http_listener_port')?.value || '80';
            // 优先使用后端返回的 host，其次使用前端选择的网卡 IP
            const interfaceIp = httpStatus.host || this.getSelectedInterfaceIp(true) || '0.0.0.0';
            const displayIp = interfaceIp === '0.0.0.0' ? 'localhost' : interfaceIp;
            const httpUrl = `http://${displayIp}:${port}`;
            const urlSpan = document.getElementById('http_listener_url');
            if (urlSpan) {
                urlSpan.innerHTML = `<a href="${httpUrl}" target="_blank">${httpUrl}</a>`;
            }
        } else {
            const urlSpan = document.getElementById('http_listener_url');
            if (urlSpan) urlSpan.textContent = '-';
        }

        // 更新 TCP 连接列表
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

        // 更新 UDP 包计数
        const udpPackets = document.getElementById('udp_listener_packets');
        if (udpPackets) udpPackets.textContent = udpStatus.packets || 0;

        // 更新 FTP 连接列表
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

        // 更新邮件服务信息
        this.updateMailStatus(mailStatus);
    }

    updateMailStatus(mailStatus) {
        if (mailStatus.running) {
            const smtpPort = mailStatus.smtp_port || document.getElementById('mail_listener_smtp_port')?.value || '25';
            const imapPort = mailStatus.imap_port || document.getElementById('mail_listener_imap_port')?.value || '143';
            const pop3Port = mailStatus.pop3_port || document.getElementById('mail_listener_pop3_port')?.value || '110';
            const domain = mailStatus.domain || document.getElementById('mail_listener_domain')?.value || 'autotest.com';
            const interfaceIp = this.getSelectedInterfaceIp(true) || '0.0.0.0';
            const serverIp = interfaceIp === '0.0.0.0' ? (mailStatus.host || domain) : interfaceIp;

            const smtpUrlSpan = document.getElementById('mail_listener_smtp_url');
            if (smtpUrlSpan) smtpUrlSpan.textContent = `smtp://${serverIp}:${smtpPort}`;

            const imapUrlSpan = document.getElementById('mail_listener_imap_url');
            if (imapUrlSpan) imapUrlSpan.textContent = `imap://${serverIp}:${imapPort}`;

            const pop3UrlSpan = document.getElementById('mail_listener_pop3_url');
            if (pop3UrlSpan) pop3UrlSpan.textContent = `pop3://${serverIp}:${pop3Port}`;

            const domainSpan = document.getElementById('mail_listener_domain_info');
            if (domainSpan) domainSpan.textContent = domain;

            const connectionsSpan = document.getElementById('mail_listener_connections');
            if (connectionsSpan) {
                const conns = mailStatus.connections || {};
                connectionsSpan.textContent = Object.keys(conns).length;
            }
        } else {
            ['mail_listener_smtp_url', 'mail_listener_imap_url', 'mail_listener_pop3_url', 'mail_listener_domain_info'].forEach(id => {
                const span = document.getElementById(id);
                if (span) span.textContent = '-';
            });
            const connectionsSpan = document.getElementById('mail_listener_connections');
            if (connectionsSpan) connectionsSpan.textContent = '0';
        }
    }

    updateClientStatus(clients) {
        const tcp = clients.tcp || { running: false };
        const udp = clients.udp || { running: false };
        const ftp = clients.ftp || { running: false };
        const http = clients.http || { running: false };

        // 更新 TCP 客户端
        const tcpRunning = tcp.running === true;
        const tcpSending = tcp.sending === true;  // 新增：检查是否在发送数据
        this.updateBadge('tcp_client_status', tcpRunning ? '已连接' : '未连接', tcpRunning);
        this.updateClientButtonState('tcp', tcpRunning, tcpSending);

        // 更新 TCP 连接表格
        const table = document.getElementById('tcp_connection_table');
        if (table) {
            const tbody = table.querySelector('tbody');
            if (tbody) {
                tbody.innerHTML = '';
                const conns = tcp.connections || [];
                if (!conns.length) {
                    tbody.innerHTML = '<tr><td colspan="5" class="text-muted">暂无连接</td></tr>';
                } else {
                    conns.forEach(conn => {
                        const connId = conn.id || '';
                        const hasValidId = connId && connId.trim() !== '';
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${connId || '(加载中...)'}</td>
                            <td>${conn.address || '-'}</td>
                            <td>${conn.bytes_sent || 0} bytes</td>
                            <td>${conn.status || 'unknown'}</td>
                            <td>
                                ${hasValidId
                                    ? `<button class="btn btn-sm btn-outline-danger" data-action="disconnect" data-conn-id="${connId}">断开</button>`
                                    : `<span class="text-muted small">等待ID分配...</span>`
                                }
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            }
        }

        // 更新 UDP 客户端
        this.updateBadge('udp_client_status', udp.running === true);

        // 更新 HTTP 客户端
        const httpRunning = http.running === true;
        this.updateBadge('http_client_status', httpRunning ? '已连接' : '未连接', httpRunning);
        this.updateClientButtonState('http', httpRunning);

        // 更新 FTP 客户端
        const ftpRunning = ftp.running === true;
        this.updateBadge('ftp_client_status', ftpRunning ? '已连接' : '未连接', ftpRunning);
        this.updateClientButtonState('ftp', ftpRunning);
    }

    updateClientButtonState(protocol, connected, sending = false) {
        const connectBtn = document.getElementById(`${protocol}_client_connect`);
        const disconnectBtn = document.getElementById(`${protocol}_client_disconnect`);
        const startSendBtn = document.getElementById(`${protocol}_client_start`);
        const stopSendBtn = document.getElementById(`${protocol}_client_stop_send`);

        // 连接/断开按钮状态
        if (connected) {
            if (connectBtn) {
                connectBtn.disabled = true;
                connectBtn.innerHTML = '<i class="fas fa-link me-1"></i>连接';
            }
            if (disconnectBtn) disconnectBtn.disabled = false;
        } else {
            if (connectBtn) {
                connectBtn.disabled = false;
                connectBtn.innerHTML = '<i class="fas fa-link me-1"></i>连接';
            }
            if (disconnectBtn) disconnectBtn.disabled = true;
        }

        // 开始发送/停止发送按钮状态 (仅 TCP)
        if (protocol === 'tcp') {
            if (connected) {
                // 已连接时，根据发送状态控制按钮
                if (sending) {
                    // 发送中：开始发送按钮置灰，停止发送按钮可用
                    if (startSendBtn) {
                        startSendBtn.disabled = true;
                        startSendBtn.classList.add('btn-outline-success');
                        startSendBtn.classList.remove('btn-success');
                    }
                    if (stopSendBtn) {
                        stopSendBtn.disabled = false;
                        stopSendBtn.classList.remove('btn-outline-warning');
                        stopSendBtn.classList.add('btn-warning');
                    }
                } else {
                    // 未发送：开始发送按钮可用，停止发送按钮置灰
                    if (startSendBtn) {
                        startSendBtn.disabled = false;
                        startSendBtn.classList.remove('btn-outline-success');
                        startSendBtn.classList.add('btn-success');
                    }
                    if (stopSendBtn) {
                        stopSendBtn.disabled = true;
                        stopSendBtn.classList.add('btn-outline-warning');
                        stopSendBtn.classList.remove('btn-warning');
                    }
                }
            } else {
                // 未连接时，两个发送按钮都置灰
                if (startSendBtn) {
                    startSendBtn.disabled = true;
                }
                if (stopSendBtn) {
                    stopSendBtn.disabled = true;
                }
            }
        }
    }

    getSelectedInterfaceIp(isListener) {
        const select = isListener ? document.getElementById('listener_interface') : document.getElementById('client_interface');
        return select ? select.value : '';
    }
}

// ========== 日志管理器 ==========
class LogManager {
    constructor(logList) {
        this.logList = logList;
        this.bindEvents();
    }

    bindEvents() {
        window.addEventListener('service:logsupdate', (e) => {
            this.displayLogs(e.detail.logs);
        });

        const clearBtn = document.getElementById('clear_logs_btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clear());
        }
    }

    displayLogs(logs) {
        if (!this.logList) return;

        logs.forEach(log => {
            const timestamp = log.timestamp || new Date().toLocaleTimeString('zh-CN', { hour12: false });
            const level = (log.level || 'info').toLowerCase();
            const badgeClass = level === 'error' ? 'bg-danger' :
                level === 'warning' ? 'bg-warning text-dark' :
                    level === 'success' ? 'bg-success' : 'bg-secondary';

            const sourceTag = log.source_tag || log.source || '服务';
            const sourceIcon = log.agent_type === 'listener' ? 'fa-broadcast-tower' :
                log.agent_type === 'client' ? 'fa-desktop' : 'fa-server';
            const sourceColor = log.agent_type === 'listener' ? 'text-primary' :
                log.agent_type === 'client' ? 'text-success' : 'text-secondary';

            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-start';
            li.setAttribute('data-log-id', log.timestamp || '');
            li.innerHTML = `
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-1">
                        <i class="fas ${sourceIcon} ${sourceColor} me-2"></i>
                        <small class="text-muted me-2">[${timestamp}]</small>
                        <span class="badge bg-light text-dark me-2">${sourceTag}</span>
                    </div>
                    <div class="text-break">${Utils.escapeHtml(log.message || '')}</div>
                </div>
                <span class="badge ${badgeClass} ms-2">${(log.level || 'INFO').toUpperCase()}</span>
            `;

            if (this.logList.firstChild) {
                this.logList.insertBefore(li, this.logList.firstChild);
            } else {
                this.logList.appendChild(li);
            }
        });

        // 限制日志数量
        while (this.logList.children.length > 200) {
            this.logList.removeChild(this.logList.lastChild);
        }
    }

    clear() {
        if (this.logList) {
            this.logList.innerHTML = '<li class="list-group-item text-muted text-center" style="background: transparent; border: none;">暂无日志</li>';
        }
    }
}

// ========== 客户端服务管理器 ==========
class ClientServiceManager {
    constructor(agentConnector, poller, logList) {
        this.connector = agentConnector;
        this.poller = poller;
        this.logList = logList;
        this.clientAgentUrl = '';
        this.apiClient = new ApiClient();

        this.bindEvents();
    }

    bindEvents() {
        // 监听客户端代理 URL 变化
        window.addEventListener('agent:connected:client', (e) => {
            this.clientAgentUrl = e.detail.agentUrl;
            this.poller.updateAgentUrls(this.poller.listenerAgentUrl, this.clientAgentUrl);
        });

        window.addEventListener('agent:disconnected:client', () => {
            this.clientAgentUrl = '';
            this.poller.updateAgentUrls(this.poller.listenerAgentUrl, this.clientAgentUrl);
        });

        // TCP 客户端按钮事件
        document.getElementById('tcp_client_connect')?.addEventListener('click', () => {
            const config = ServiceConfig.collectTcpClientConfig();
            const [valid, error] = ServiceConfig.validateAddress(config);
            if (valid) {
                this.sendClientCommand('tcp', 'connect', config);
            } else {
                Utils.showToast(error, 'warning');
            }
        });

        document.getElementById('tcp_client_start')?.addEventListener('click', () => {
            const config = ServiceConfig.collectTcpClientConfig();
            this.sendClientCommand('tcp', 'start_send', config);
        });

        document.getElementById('tcp_client_stop_send')?.addEventListener('click', () => {
            this.sendClientCommand('tcp', 'stop_send');
        });

        document.getElementById('tcp_client_disconnect')?.addEventListener('click', () => {
            this.sendClientCommand('tcp', 'disconnect');
        });

        // TCP 连接表格中断开按钮的事件委托
        document.getElementById('tcp_connection_table')?.addEventListener('click', (e) => {
            const disconnectBtn = e.target.closest('button[data-action="disconnect"]');
            if (disconnectBtn) {
                const connId = disconnectBtn.dataset.connId;
                if (connId && connId.trim() !== '') {
                    this.sendClientCommand('tcp', 'disconnect', { connection_id: connId });
                } else {
                    Utils.showToast('无法断开：连接ID无效，请刷新状态后重试', 'warning');
                    Utils.addLogEntry('断开连接失败：连接ID为空', 'warning', this.logList);
                    setTimeout(() => this.poller.fetchStatus(), 500);
                }
            }
        });

        // UDP 客户端按钮事件
        document.getElementById('udp_client_start')?.addEventListener('click', () => {
            const config = ServiceConfig.collectUdpClientConfig();
            const [valid, error] = ServiceConfig.validateAddress(config);
            if (valid) {
                this.sendClientCommand('udp', 'start', config);
            } else {
                Utils.showToast(error, 'warning');
            }
        });

        document.getElementById('udp_client_stop')?.addEventListener('click', () => {
            this.sendClientCommand('udp', 'stop');
        });

        // FTP 客户端按钮事件
        document.getElementById('ftp_client_connect')?.addEventListener('click', async () => {
            const config = ServiceConfig.collectFtpClientConfig();
            const [valid, error] = ServiceConfig.validateAddress(config);
            if (valid) {
                const result = await this.sendClientCommand('ftp', 'connect', config);
                // 连接成功后启用操作按钮并刷新文件列表
                if (result && result.success) {
                    // 启用断开、上级目录、刷新、上传按钮
                    document.getElementById('ftp_client_disconnect').disabled = false;
                    document.getElementById('ftp_client_go_up').disabled = false;
                    document.getElementById('ftp_client_refresh_file_list').disabled = false;
                    document.getElementById('ftp_client_upload_btn').disabled = false;
                    document.getElementById('ftp_client_download_btn').disabled = false;

                    setTimeout(() => {
                        this.sendClientCommand('ftp', 'list');
                    }, 1500);
                }
            } else {
                Utils.showToast(error, 'warning');
            }
        });

        document.getElementById('ftp_client_disconnect')?.addEventListener('click', async () => {
            const result = await this.sendClientCommand('ftp', 'disconnect');
            if (result && result.success) {
                // 断开成功后禁用操作按钮并清空文件列表
                document.getElementById('ftp_client_disconnect').disabled = true;
                document.getElementById('ftp_client_go_up').disabled = true;
                document.getElementById('ftp_client_refresh_file_list').disabled = true;
                document.getElementById('ftp_client_upload_btn').disabled = true;
                document.getElementById('ftp_client_download_btn').disabled = true;

                const fileList = document.getElementById('ftp_client_file_list');
                if (fileList) {
                    fileList.innerHTML = '<div class="text-muted text-center">未连接</div>';
                }
            }
        });

        document.getElementById('ftp_client_go_up')?.addEventListener('click', () => {
            this.changeFtpDirectory('..');
        });

        document.getElementById('ftp_client_refresh_file_list')?.addEventListener('click', () => {
            this.sendClientCommand('ftp', 'list');
        });

        document.getElementById('ftp_client_upload_btn')?.addEventListener('click', () => {
            const fileInput = document.getElementById('ftp_client_upload_file');
            if (fileInput && fileInput.files.length > 0) {
                const file = fileInput.files[0];
                const reader = new FileReader();
                reader.onload = (e) => {
                    const content = e.target.result;
                    // 将文件内容转换为 Base64 以便传输
                    const base64Content = btoa(unescape(encodeURIComponent(content)));
                    this.sendClientCommand('ftp', 'upload', {
                        filename: file.name,
                        content: base64Content,
                        is_binary: !file.type.startsWith('text/')
                    });
                };
                reader.onerror = () => {
                    Utils.showToast('文件读取失败', 'error');
                };
                if (file.type.startsWith('text/')) {
                    reader.readAsText(file);
                } else {
                    reader.readAsBinaryString(file);
                }
            } else {
                Utils.showToast('请选择要上传的文件', 'warning');
            }
        });

        document.getElementById('ftp_client_download_btn')?.addEventListener('click', () => {
            const filename = document.getElementById('ftp_client_download_file')?.value;
            if (filename) {
                this.sendClientCommand('ftp', 'download', { filename });
            } else {
                Utils.showToast('请输入要下载的文件名', 'warning');
            }
        });

        // HTTP 客户端按钮事件
        document.getElementById('http_client_connect')?.addEventListener('click', async () => {
            const config = ServiceConfig.collectHttpClientConfig();
            const [valid, error] = ServiceConfig.validateAddress(config);
            if (valid) {
                const result = await this.sendClientCommand('http', 'connect', config);
                // 连接成功后启用操作按钮并刷新文件列表
                if (result && result.success) {
                    // 启用断开、上级目录、刷新、上传、下载按钮
                    document.getElementById('http_client_disconnect').disabled = false;
                    document.getElementById('http_client_go_up').disabled = false;
                    document.getElementById('http_client_refresh_file_list').disabled = false;
                    document.getElementById('http_client_upload_btn').disabled = false;
                    document.getElementById('http_client_download_btn').disabled = false;

                    setTimeout(() => {
                        this.sendClientCommand('http', 'list');
                    }, 1500);
                }
            } else {
                Utils.showToast(error, 'warning');
            }
        });

        document.getElementById('http_client_disconnect')?.addEventListener('click', async () => {
            const result = await this.sendClientCommand('http', 'disconnect');
            if (result && result.success) {
                // 断开成功后禁用操作按钮并清空文件列表
                document.getElementById('http_client_disconnect').disabled = true;
                document.getElementById('http_client_go_up').disabled = true;
                document.getElementById('http_client_refresh_file_list').disabled = true;
                document.getElementById('http_client_upload_btn').disabled = true;
                document.getElementById('http_client_download_btn').disabled = true;

                const fileList = document.getElementById('http_client_file_list');
                if (fileList) {
                    fileList.innerHTML = '<div class="text-muted text-center">未连接</div>';
                }
            }
        });

        document.getElementById('http_client_go_up')?.addEventListener('click', () => {
            this.changeHttpDirectory('..');
        });

        document.getElementById('http_client_refresh_file_list')?.addEventListener('click', () => {
            this.sendClientCommand('http', 'list');
        });

        document.getElementById('http_client_upload_btn')?.addEventListener('click', () => {
            const fileInput = document.getElementById('http_client_upload_file');
            if (fileInput && fileInput.files.length > 0) {
                const file = fileInput.files[0];
                const reader = new FileReader();
                reader.onload = (e) => {
                    const content = e.target.result;
                    // 将文件内容转换为 Base64 以便传输
                    const base64Content = btoa(unescape(encodeURIComponent(content)));
                    this.sendClientCommand('http', 'upload', {
                        filename: file.name,
                        content: base64Content,
                        is_binary: !file.type.startsWith('text/')
                    });
                };
                reader.onerror = () => {
                    Utils.showToast('文件读取失败', 'error');
                };
                if (file.type.startsWith('text/')) {
                    reader.readAsText(file);
                } else {
                    reader.readAsBinaryString(file);
                }
            } else {
                Utils.showToast('请选择要上传的文件', 'warning');
            }
        });

        // HTTP 文件选择器 change 事件，显示预览
        document.getElementById('http_client_upload_file')?.addEventListener('change', (e) => {
            const file = e.target.files[0];
            const previewDiv = document.getElementById('http_client_upload_content');
            if (file && previewDiv) {
                previewDiv.innerHTML = `<div class="text-success"><i class="fas fa-file me-1"></i>已选择：${file.name} (${this.formatFileSize(file.size)})</div>`;
            }
        });

        document.getElementById('http_client_download_btn')?.addEventListener('click', () => {
            const filename = document.getElementById('http_client_download_file')?.value;
            if (filename) {
                this.sendClientCommand('http', 'download', { filename });
            } else {
                Utils.showToast('请选择要下载的文件', 'warning');
            }
        });
    }

    async sendClientCommand(protocol, action, extra = {}) {
        if (!this.clientAgentUrl) {
            Utils.addLogEntry('请先连接客户端代理程序', 'warning', this.logList);
            return;
        }

        // 将 extra 参数包装在 config 键中（后端期望的格式）
        const payload = {
            protocol,
            action,
            config: extra
        };

        Utils.addLogEntry(`发送${protocol.toUpperCase()}命令：${action}`, 'info', this.logList);

        try {
            const data = await this.apiClient.callClientService(this.clientAgentUrl, payload);

            // 检查 HTTP 状态码（400/500 表示业务逻辑错误）
            if (data.http_status && data.http_status >= 400) {
                Utils.addLogEntry(`${protocol.toUpperCase()} ${action} 失败：${data.error || 'HTTP ' + data.http_status}`, 'error', this.logList);
                // 不抛出异常，保持连接
                return data;
            }

            if (data.success) {
                Utils.addLogEntry(`${protocol.toUpperCase()} ${action} 成功`, 'success', this.logList);

                // 处理特定操作的响应显示
                if (protocol === 'ftp') {
                    if (action === 'list' && data.files) {
                        this.displayFtpFileList(data.files, data.current_dir);
                    } else if (action === 'cd' && data.current_dir) {
                        // 切换目录成功后刷新列表
                        this.displayFtpFileList([], data.current_dir);
                        setTimeout(() => this.sendClientCommand('ftp', 'list'), 100);
                    } else if (action === 'download' && data.content) {
                        this.displayFtpDownloadContent(data.content);
                    } else if (action === 'upload' && data.upload_path) {
                        // 显示上传目标位置
                        Utils.addLogEntry(`文件已上传到：${data.upload_path}/${data.filename}`, 'success', this.logList);
                    }
                } else if (protocol === 'http') {
                    if (action === 'list' && data.files) {
                        this.displayHttpFileList(data.files, data.current_dir);
                    } else if (action === 'cd' && data.current_dir) {
                        // 切换目录成功后刷新列表
                        this.displayHttpFileList([], data.current_dir);
                        setTimeout(() => this.sendClientCommand('http', 'list'), 100);
                    } else if (action === 'download' && data.content) {
                        this.displayHttpDownloadContent(data.content);
                    } else if (action === 'upload' && data.message) {
                        // 显示上传结果
                        Utils.addLogEntry(data.message, 'success', this.logList);
                        // 刷新文件列表
                        setTimeout(() => this.sendClientCommand('http', 'list'), 100);
                    }
                }

                // 刷新状态
                setTimeout(() => this.poller.fetchStatus(), 500);

                return data;
            } else {
                Utils.addLogEntry(`${protocol.toUpperCase()} ${action} 失败：${data.error || '未知错误'}`, 'error', this.logList);
                return data;
            }
        } catch (error) {
            Utils.addLogEntry(`${protocol.toUpperCase()} ${action} 异常：${error.message}`, 'error', this.logList);
            throw error;
        }
    }

    /**
     * 显示 FTP 文件列表
     */
    displayFtpFileList(files, currentDir) {
        const fileList = document.getElementById('ftp_client_file_list');
        const dirInput = document.getElementById('ftp_client_current_dir');

        // 更新当前目录显示
        if (currentDir && dirInput) {
            dirInput.value = currentDir;
        }

        if (!fileList) return;

        // 处理结构化数据（后端返回的数组格式）
        if (Array.isArray(files)) {
            if (files.length === 0) {
                fileList.innerHTML = '<div class="text-muted text-center">目录为空</div>';
                return;
            }

            fileList.innerHTML = '<ul class="ftp-file-list list-group list-group-flush"></ul>';
            const ul = fileList.querySelector('ul');

            files.forEach(file => {
                const li = document.createElement('li');
                li.className = 'list-group-item list-group-item-action ftp-file-item';
                li.dataset.filename = file.name;
                li.dataset.isDir = file.is_dir;

                // 构建显示内容
                let icon = file.is_dir ? 'fa-folder' : 'fa-file';
                let colorClass = file.is_dir ? 'text-warning' : 'text-secondary';
                let sizeInfo = file.is_dir ? '' : this.formatFileSize(file.size || 0);

                li.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <i class="fas ${icon} ${colorClass} me-2"></i>
                            <span class="file-name">${file.name}</span>
                        </div>
                        ${!file.is_dir ? `<small class="text-muted file-size">${sizeInfo}</small>` : ''}
                    </div>
                `;

                li.onclick = () => {
                    if (file.is_dir) {
                        // 点击进入目录
                        this.changeFtpDirectory(file.name);
                    } else {
                        // 选中文件，准备下载
                        document.getElementById('ftp_client_download_file').value = file.name;
                        // 清除其他选中
                        ul.querySelectorAll('.ftp-file-item').forEach(item => {
                            item.classList.remove('active');
                        });
                        li.classList.add('active');
                    }
                };

                ul.appendChild(li);
            });
        } else if (typeof files === 'string') {
            // 兼容旧的字符串格式（后端可能返回原始FTP LIST）
            const lines = files.split('\n').filter(line => line.trim());
            if (lines.length === 0) {
                fileList.innerHTML = '<div class="text-muted text-center">目录为空</div>';
                return;
            }
            fileList.innerHTML = '<ul class="list-unstyled mb-0" style="font-family: monospace; font-size: 12px;"></ul>';
            const ul = fileList.querySelector('ul');
            lines.forEach(line => {
                const li = document.createElement('li');
                li.style.cursor = 'pointer';
                li.style.padding = '2px 0';

                // 解析FTP LIST行
                const isDir = line.startsWith('d');
                const parts = line.trim().split(/\s+/);
                const filename = parts[parts.length - 1];

                // 添加图标指示
                const iconClass = isDir ? 'fa-folder text-warning' : 'fa-file text-secondary';
                li.innerHTML = `<i class="fas ${iconClass} me-2"></i>${line}`;

                li.onclick = () => {
                    if (isDir && filename) {
                        // 点击目录，进入下级目录
                        this.changeFtpDirectory(filename);
                    } else if (filename) {
                        // 点击文件，设置下载文件名
                        document.getElementById('ftp_client_download_file').value = filename;
                        // 清除其他选中
                        ul.querySelectorAll('li').forEach(item => {
                            item.classList.remove('active');
                        });
                        li.classList.add('active');
                    }
                };
                ul.appendChild(li);
            });
        } else {
            fileList.innerHTML = '<div class="text-muted text-center">无法解析文件列表</div>';
        }
    }

    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * 切换 FTP 目录
     */
    changeFtpDirectory(dirname) {
        this.sendClientCommand('ftp', 'cd', { dirname });
    }

    /**
     * 显示 FTP 下载内容
     */
    displayFtpDownloadContent(content) {
        const contentDiv = document.getElementById('ftp_client_download_content');
        if (!contentDiv) return;
        contentDiv.textContent = typeof content === 'string' ? content : JSON.stringify(content);
    }

    /**
     * 显示 HTTP 文件列表
     */
    displayHttpFileList(files, currentDir) {
        const fileList = document.getElementById('http_client_file_list');
        const dirInput = document.getElementById('http_client_current_dir');

        // 更新当前目录显示
        if (currentDir && dirInput) {
            dirInput.value = currentDir;
        }

        if (!fileList) return;

        // 处理结构化数据（后端返回的数组格式）
        if (Array.isArray(files)) {
            if (files.length === 0) {
                fileList.innerHTML = '<div class="text-muted text-center">目录为空</div>';
                return;
            }

            fileList.innerHTML = '<ul class="ftp-file-list list-group list-group-flush"></ul>';
            const ul = fileList.querySelector('ul');

            files.forEach(file => {
                const li = document.createElement('li');
                li.className = 'list-group-item list-group-item-action ftp-file-item';
                li.dataset.filename = file.name;
                li.dataset.isDir = file.is_dir;

                // 构建显示内容
                let icon = file.is_dir ? 'fa-folder' : 'fa-file';
                let colorClass = file.is_dir ? 'text-warning' : 'text-secondary';
                let sizeInfo = file.is_dir ? '' : this.formatFileSize(file.size || 0);

                li.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <i class="fas ${icon} ${colorClass} me-2"></i>
                            <span class="file-name">${file.name}</span>
                        </div>
                        ${!file.is_dir ? `<small class="text-muted file-size">${sizeInfo}</small>` : ''}
                    </div>
                `;

                li.onclick = () => {
                    if (file.is_dir) {
                        // 点击进入目录
                        this.changeHttpDirectory(file.name);
                    } else {
                        // 选中文件，准备下载
                        document.getElementById('http_client_download_file').value = file.name;
                        // 清除其他选中
                        ul.querySelectorAll('.ftp-file-item').forEach(item => {
                            item.classList.remove('active');
                        });
                        li.classList.add('active');
                    }
                };

                ul.appendChild(li);
            });
        } else if (typeof files === 'string') {
            // 兼容旧的字符串格式
            const lines = files.split('\n').filter(line => line.trim());
            if (lines.length === 0) {
                fileList.innerHTML = '<div class="text-muted text-center">目录为空</div>';
                return;
            }
            fileList.innerHTML = '<ul class="list-unstyled mb-0" style="font-family: monospace; font-size: 12px;"></ul>';
            const ul = fileList.querySelector('ul');
            lines.forEach(line => {
                const li = document.createElement('li');
                li.textContent = line;
                li.style.cursor = 'pointer';
                li.style.padding = '2px 0';
                li.onclick = () => {
                    const parts = line.trim().split(/\s+/);
                    const filename = parts[parts.length - 1];
                    if (filename && !line.startsWith('d')) {
                        document.getElementById('http_client_download_file').value = filename;
                    }
                };
                ul.appendChild(li);
            });
        } else {
            fileList.innerHTML = '<div class="text-muted text-center">无法解析文件列表</div>';
        }
    }

    /**
     * 显示 HTTP 下载内容
     */
    displayHttpDownloadContent(content) {
        const contentDiv = document.getElementById('http_client_download_content');
        if (!contentDiv) return;
        contentDiv.textContent = typeof content === 'string' ? content : JSON.stringify(content);
    }

    /**
     * 切换 HTTP 目录
     */
    changeHttpDirectory(dirname) {
        this.sendClientCommand('http', 'cd', { dirname });
    }
}

// ========== 邮件用户管理 ==========

class MailUserManager {
    constructor() {
        this.agentUrl = ''; // 监听服务代理的 URL
        this.mailServerRunning = false; // 邮件服务器运行状态
        this.init();
    }

    init() {
        // 监听监听服务代理连接事件
        window.addEventListener('agent:connected:listener', (e) => {
            this.agentUrl = e.detail.agentUrl;
            this.checkMailServerAndLoadUsers();
        });

        // 监听服务状态更新事件（当邮件服务器启动时）
        window.addEventListener('service:statusupdate', () => {
            // 延迟检查，确保状态已更新
            setTimeout(() => this.checkMailServerAndLoadUsers(), 500);
        });

        // 创建用户按钮
        document.getElementById('create_user_btn')?.addEventListener('click', () => {
            this.createUser();
        });

        // 页面加载后检查邮件服务器状态
        this.checkMailServerAndLoadUsers();
    }

    checkMailServerAndLoadUsers() {
        // 检查邮件服务器是否运行
        const mailStatusSpan = document.getElementById('mail_listener_status');
        if (mailStatusSpan) {
            this.mailServerRunning = mailStatusSpan.classList.contains('bg-success');
        }

        if (this.agentUrl && this.mailServerRunning) {
            this.loadUsers();
        }
    }

    async loadUsers() {
        const tbody = document.getElementById('user_list');
        if (!tbody) return;

        // 检查是否有 agentUrl
        if (!this.agentUrl) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">请先连接监听服务代理</td></tr>';
            return;
        }

        // 检查邮件服务器是否运行
        if (!this.mailServerRunning) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">请先启动邮件服务器</td></tr>';
            return;
        }

        try {
            const resp = await fetch(`${this.agentUrl}/api/mail/users`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await resp.json();

            if (data.success && data.users) {
                if (data.users.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无用户</td></tr>';
                } else {
                    let html = '';
                    data.users.forEach(user => {
                        html += `<tr>
                            <td>${user.username}</td>
                            <td>${user.email}</td>
                            <td>${user.created || '-'}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-danger" onclick="window.mailUserManager.deleteUser('${user.username}')">
                                    <i class="fas fa-trash"></i> 删除
                                </button>
                            </td>
                        </tr>`;
                    });
                    tbody.innerHTML = html;
                }
            } else {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">' + (data.error || '加载失败') + '</td></tr>';
            }
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">加载失败：' + error.message + '</td></tr>';
        }
    }

    async createUser() {
        const username = document.getElementById('new_username')?.value?.trim();
        const password = document.getElementById('new_password')?.value?.trim();
        const email = document.getElementById('new_email')?.value?.trim();

        if (!username) {
            alert('请输入用户名');
            return;
        }
        if (!password || password.length < 4) {
            alert('密码至少需要 4 位');
            return;
        }

        // 检查是否有 agentUrl
        if (!this.agentUrl) {
            alert('请先连接监听服务代理');
            return;
        }

        // 检查邮件服务器是否运行
        if (!this.mailServerRunning) {
            alert('请先启动邮件服务器');
            return;
        }

        try {
            const resp = await fetch(`${this.agentUrl}/api/mail/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, email: email || '' })
            });

            const data = await resp.json();

            if (data.success) {
                alert('用户创建成功');
                // 清空输入框
                document.getElementById('new_username').value = '';
                document.getElementById('new_password').value = '';
                document.getElementById('new_email').value = '';
                // 刷新用户列表
                this.loadUsers();
            } else {
                alert('创建失败：' + (data.error || '未知错误'));
            }
        } catch (error) {
            alert('创建失败：' + error.message);
        }
    }

    async deleteUser(username) {
        if (!confirm(`确定要删除用户 "${username}" 吗？`)) {
            return;
        }

        // 检查是否有 agentUrl
        if (!this.agentUrl) {
            alert('请先连接监听服务代理');
            return;
        }

        // 检查邮件服务器是否运行
        if (!this.mailServerRunning) {
            alert('请先启动邮件服务器');
            return;
        }

        try {
            const resp = await fetch(`${this.agentUrl}/api/mail/users/${username}`, {
                method: 'DELETE'
            });

            const data = await resp.json();

            if (data.success) {
                alert('用户删除成功');
                this.loadUsers();
            } else {
                alert('删除失败：' + (data.error || '未知错误'));
            }
        } catch (error) {
            alert('删除失败：' + error.message);
        }
    }
}

// 初始化邮件用户管理（当页面加载时）
document.addEventListener('DOMContentLoaded', () => {
    window.mailUserManager = new MailUserManager();
});

// ========== 导出全局对象 ==========
window.ServiceDeploy = {
    Utils,
    ServiceConfig,
    ApiClient,
    AgentConnector,
    StatusPoller,
    ListenerServiceManager,
    StatusDisplayUpdater,
    LogManager,
    ClientServiceManager
};
