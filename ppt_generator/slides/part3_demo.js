/**
 * Part 3: 演示环节（8页）
 */

const { COLORS } = require('../utils/colors');

/**
 * 生成Part3演示环节的所有幻灯片
 * @param {PptxGenJS} pptx - PPT实例
 */
function generatePart3(pptx) {
  // 页面14: 章节标题页
  addDemoSectionSlide(pptx);

  // 页面15: 操作流程总览
  addOperationFlowSlide(pptx);

  // 页面16: 环境管理演示
  addEnvManagementSlide(pptx);

  // 页面17: Agent部署演示
  addAgentDeploySlide(pptx);

  // 页面18: 报文发送演示
  addPacketSendSlide(pptx);

  // 页面19: 工控协议演示
  addIndustrialProtocolSlide(pptx);

  // 页面20: DDoS测试流程
  addDDoSTestSlide(pptx);

  // 页面21: 结果验证
  addResultVerificationSlide(pptx);
}

/**
 * 页面14: 章节标题页
 */
function addDemoSectionSlide(pptx) {
  let slide = pptx.addSlide();

  // 橙色背景
  slide.background = { color: COLORS.accent };

  // 装饰圆形
  addDecorCircles(slide);

  // 大图标
  slide.addText('💻', {
    x: 4, y: 0.8, w: 2, h: 1,
    fontSize: 60,
    align: 'center',
  });

  // 大标题
  slide.addText('核心操作演示', {
    x: 0.5, y: 2, w: 9, h: 1,
    fontSize: 48,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });

  // 底部概要
  slide.addText('1. 环境配置与Agent部署\n2. 报文发送与工控协议测试\n3. DDoS压力测试完整流程', {
    x: 1, y: 3.5, w: 8, h: 1.5,
    fontSize: 18,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
    valign: 'middle',
  });
}

/**
 * 页面15: 操作流程总览
 */
function addOperationFlowSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('从部署到测试，5步搞定', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 说明
  slide.addText('整个测试流程简单明了，从配置到出报告只需5步', {
    x: 0.5, y: 1, w: 9, h: 0.4,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });

  // 5步流程
  const steps = [
    { num: '1', title: '配置环境', desc: '添加测试设备信息\nIP、账号、系统类型', time: '5分钟', icon: '⚙️', color: COLORS.primary },
    { num: '2', title: '部署Agent', desc: '一键同步部署\n自动上传启动', time: '2分钟', icon: '📤', color: COLORS.teal },
    { num: '3', title: '执行测试', desc: '选择测试类型\n配置参数运行', time: '按需', icon: '▶️', color: COLORS.accent },
    { num: '4', title: '验证结果', desc: '实时查看输出\n日志自动记录', time: '实时', icon: '✅', color: COLORS.purple },
    { num: '5', title: '生成报告', desc: '自动汇总结果\n导出测试报告', time: '自动', icon: '📊', color: COLORS.secondary },
  ];

  const stepWidth = 1.8;
  const stepHeight = 2.8;
  const startX = 0.4;
  const startY = 1.5;

  steps.forEach((step, i) => {
    const x = startX + i * (stepWidth + 0.1);

    // 步骤卡片
    slide.addShape('roundRect', {
      x: x, y: startY, w: stepWidth, h: stepHeight,
      fill: { color: step.color },
      radius: 0.1,
    });

    // 编号
    slide.addText(step.num, {
      x: x + 0.1, y: startY + 0.1, w: stepWidth - 0.2, h: 0.4,
      fontSize: 22,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });

    // 图标
    slide.addText(step.icon, {
      x: x + 0.1, y: startY + 0.5, w: stepWidth - 0.2, h: 0.5,
      fontSize: 28,
      align: 'center',
    });

    // 标题
    slide.addText(step.title, {
      x: x + 0.1, y: startY + 1.05, w: stepWidth - 0.2, h: 0.35,
      fontSize: 14,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });

    // 描述
    slide.addText(step.desc, {
      x: x + 0.1, y: startY + 1.45, w: stepWidth - 0.2, h: 0.8,
      fontSize: 10,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
    });

    // 时间
    slide.addText(step.time, {
      x: x + 0.1, y: startY + 2.35, w: stepWidth - 0.2, h: 0.35,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });
  });

  // 底部总结
  slide.addShape('roundRect', {
    x: 0.5, y: 4.5, w: 9, h: 0.8,
    fill: { color: COLORS.primary },
    radius: 0.05,
  });
  slide.addText('💡 首次配置后，后续测试只需步骤3-4，整个过程更快捷', {
    x: 0.7, y: 4.6, w: 8.6, h: 0.6,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });
}

/**
 * 页面16: 环境管理演示
 */
function addEnvManagementSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('步骤1: 配置测试环境', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 左侧截图占位框
  slide.addShape('roundRect', {
    x: 0.5, y: 1, w: 5.5, h: 3.2,
    fill: { color: COLORS.gray200 },
    line: { color: COLORS.gray400, width: 2, dashType: 'dash' },
    radius: 0.1,
  });

  slide.addText('📸 测试环境列表页面截图', {
    x: 0.5, y: 2.2, w: 5.5, h: 0.5,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray500,
    align: 'center',
  });

  // 右侧操作要点
  slide.addText('配置要点', {
    x: 6.2, y: 1, w: 3.3, h: 0.4,
    fontSize: 18,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  const configItems = [
    { icon: '📝', text: '设备名称: 自定义标识' },
    { icon: '🌐', text: 'IP地址: 测试设备IP' },
    { icon: '👤', text: 'SSH账号: 登录凭证' },
    { icon: '💻', text: '系统类型: Windows/Linux' },
    { icon: '📝', text: '备注: 可选描述信息' },
  ];

  configItems.forEach((item, i) => {
    slide.addText(`${item.icon} ${item.text}`, {
      x: 6.2, y: 1.5 + i * 0.45, w: 3.3, h: 0.4,
      fontSize: 13,
      fontFace: 'Microsoft YaHei',
      color: COLORS.gray700,
    });
  });

  // 操作提示卡片
  slide.addShape('roundRect', {
    x: 6.2, y: 3.8, w: 3.3, h: 0.8,
    fill: { color: COLORS.secondary },
    radius: 0.05,
  });
  slide.addText('💡 首次配置后，后续无需重复', {
    x: 6.4, y: 3.9, w: 3, h: 0.6,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });

  // 底部说明
  slide.addText('📌 配置完成后，可在列表中查看所有测试环境，支持编辑、删除操作', {
    x: 0.5, y: 4.5, w: 9, h: 0.4,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
    align: 'center',
  });
}

/**
 * 页面17: Agent部署演示
 */
function addAgentDeploySlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('步骤2: 一键部署Agent', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 左侧截图占位框
  slide.addShape('roundRect', {
    x: 0.5, y: 1, w: 5.5, h: 3.2,
    fill: { color: COLORS.gray200 },
    line: { color: COLORS.gray400, width: 2, dashType: 'dash' },
    radius: 0.1,
  });

  slide.addText('📸 Agent同步页面截图', {
    x: 0.5, y: 2.2, w: 5.5, h: 0.5,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray500,
    align: 'center',
  });

  // 右侧部署步骤
  slide.addText('部署步骤', {
    x: 6.2, y: 1, w: 3.3, h: 0.4,
    fontSize: 18,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  const deploySteps = [
    { num: '1', text: '选择目标测试环境' },
    { num: '2', text: '点击"同步Agent"按钮' },
    { num: '3', text: '等待文件上传完成' },
    { num: '4', text: '点击"启动Agent"' },
    { num: '5', text: '确认状态变为"运行中"' },
  ];

  deploySteps.forEach((item, i) => {
    slide.addShape('roundRect', {
      x: 6.2, y: 1.5 + i * 0.55, w: 0.35, h: 0.35,
      fill: { color: COLORS.accent },
      radius: 0.05,
    });
    slide.addText(item.num, {
      x: 6.2, y: 1.5 + i * 0.55, w: 0.35, h: 0.35,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
      valign: 'middle',
    });
    slide.addText(item.text, {
      x: 6.65, y: 1.5 + i * 0.55, w: 2.85, h: 0.35,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: COLORS.gray700,
      valign: 'middle',
    });
  });

  // Agent端口说明
  slide.addShape('roundRect', {
    x: 6.2, y: 4.3, w: 3.3, h: 0.7,
    fill: { color: COLORS.primary },
    radius: 0.05,
  });
  slide.addText('Packet Agent: 8888\n工控协议Agent: 8889', {
    x: 6.4, y: 4.35, w: 3, h: 0.6,
    fontSize: 11,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });

  // 底部说明
  slide.addText('📌 Agent程序自动上传并启动，无需手动操作远程服务器', {
    x: 0.5, y: 5.1, w: 9, h: 0.3,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
    align: 'center',
  });
}

/**
 * 页面18: 报文发送演示
 */
function addPacketSendSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('步骤3: 发送测试报文', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 左侧截图占位框
  slide.addShape('roundRect', {
    x: 0.5, y: 1, w: 5.5, h: 3.2,
    fill: { color: COLORS.gray200 },
    line: { color: COLORS.gray400, width: 2, dashType: 'dash' },
    radius: 0.1,
  });

  slide.addText('📸 报文发送配置界面截图', {
    x: 0.5, y: 2.2, w: 5.5, h: 0.5,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray500,
    align: 'center',
  });

  // 右侧配置说明
  slide.addText('配置参数', {
    x: 6.2, y: 1, w: 3.3, h: 0.4,
    fontSize: 18,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  const configParams = [
    { label: '选择Agent', desc: '选择运行的测试设备' },
    { label: '协议类型', desc: 'TCP/UDP/HTTP/ICMP等' },
    { label: '目标地址', desc: '防火墙接口IP' },
    { label: '端口', desc: '目标端口号' },
    { label: '发送次数', desc: '单次或连续发送' },
  ];

  configParams.forEach((p, i) => {
    slide.addText(`${p.label}:`, {
      x: 6.2, y: 1.45 + i * 0.45, w: 1.2, h: 0.35,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: COLORS.gray700,
      bold: true,
    });
    slide.addText(p.desc, {
      x: 7.4, y: 1.45 + i * 0.45, w: 2.1, h: 0.35,
      fontSize: 11,
      fontFace: 'Microsoft YaHei',
      color: COLORS.gray600,
    });
  });

  // 支持的报文类型
  slide.addShape('roundRect', {
    x: 6.2, y: 3.8, w: 3.3, h: 1,
    fill: { color: COLORS.teal },
    radius: 0.05,
  });
  slide.addText('支持的报文类型', {
    x: 6.4, y: 3.85, w: 3, h: 0.35,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });
  slide.addText('TCP | UDP | HTTP | ICMP\nModbus | DNP3 | 自定义报文', {
    x: 6.4, y: 4.2, w: 3, h: 0.5,
    fontSize: 10,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });

  // 发送统计小窗示意
  slide.addShape('roundRect', {
    x: 4, y: 4.3, w: 2, h: 0.7,
    fill: { color: COLORS.secondary },
    radius: 0.05,
  });
  slide.addText('实时统计\n已发送: 1000', {
    x: 4, y: 4.35, w: 2, h: 0.6,
    fontSize: 10,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });
}

/**
 * 页面19: 工控协议演示
 */
function addIndustrialProtocolSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('工控协议测试', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 左侧截图占位框 - Modbus客户端
  slide.addShape('roundRect', {
    x: 0.5, y: 1, w: 4.3, h: 3.2,
    fill: { color: COLORS.gray200 },
    line: { color: COLORS.gray400, width: 2, dashType: 'dash' },
    radius: 0.1,
  });

  slide.addText('📸 Modbus客户端配置', {
    x: 0.5, y: 2.2, w: 4.3, h: 0.5,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray500,
    align: 'center',
  });

  // 右侧截图占位框 - Modbus服务器
  slide.addShape('roundRect', {
    x: 5.2, y: 1, w: 4.3, h: 3.2,
    fill: { color: COLORS.gray200 },
    line: { color: COLORS.gray400, width: 2, dashType: 'dash' },
    radius: 0.1,
  });

  slide.addText('📸 Modbus服务器状态', {
    x: 5.2, y: 2.2, w: 4.3, h: 0.5,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray500,
    align: 'center',
  });

  // 底部功能说明
  slide.addText('支持功能码', {
    x: 0.5, y: 4.4, w: 4.3, h: 0.35,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });
  slide.addText('读线圈(01) | 读输入(02) | 读保持寄存器(03)\n写单线圈(05) | 写单寄存器(06) | 报告ID(17)', {
    x: 0.5, y: 4.8, w: 4.3, h: 0.6,
    fontSize: 10,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });

  slide.addText('其他协议', {
    x: 5.2, y: 4.4, w: 4.3, h: 0.35,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });
  slide.addText('S7 | GOOSE | SV | IEC104 | DNP3\nBACnet | OPC UA | EtherNet/IP', {
    x: 5.2, y: 4.8, w: 4.3, h: 0.6,
    fontSize: 10,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });
}

/**
 * 页面20: DDoS测试流程
 */
function addDDoSTestSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('完整案例: DDoS压力测试', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 四宫格布局
  const quadSteps = [
    {
      title: '1. 配置攻击参数',
      desc: '选择协议、端口、发送次数',
      icon: '⚙️',
      color: COLORS.primary
    },
    {
      title: '2. 点击开始发送',
      desc: '实时查看发送统计',
      icon: '▶️',
      color: COLORS.teal
    },
    {
      title: '3. 查看发送统计',
      desc: '监控发送速率和成功率',
      icon: '📊',
      color: COLORS.accent
    },
    {
      title: '4. 查看防火墙日志',
      desc: '验证防火墙告警响应',
      icon: '📝',
      color: COLORS.purple
    },
  ];

  const quadY = 1.1;
  const quadWidth = 4.3;
  const quadHeight = 1.7;

  quadSteps.forEach((step, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * (quadWidth + 0.4);
    const y = quadY + row * (quadHeight + 0.3);

    // 截图占位框
    slide.addShape('roundRect', {
      x: x, y: y, w: quadWidth, h: quadHeight - 0.4,
      fill: { color: COLORS.gray200 },
      line: { color: COLORS.gray400, width: 1, dashType: 'dash' },
      radius: 0.08,
    });

    slide.addText(`📸 ${step.title}`, {
      x: x, y: y + (quadHeight - 0.4) / 2 - 0.15, w: quadWidth, h: 0.3,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: COLORS.gray500,
      align: 'center',
    });

    // 步骤标题
    slide.addShape('roundRect', {
      x: x, y: y + quadHeight - 0.35, w: quadWidth, h: 0.35,
      fill: { color: step.color },
      radius: 0.05,
    });
    slide.addText(`${step.icon} ${step.title}`, {
      x: x, y: y + quadHeight - 0.35, w: quadWidth, h: 0.35,
      fontSize: 11,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
      valign: 'middle',
    });
  });

  // 安全提示
  slide.addShape('roundRect', {
    x: 0.5, y: 4.5, w: 9, h: 0.7,
    fill: { color: COLORS.accent },
    radius: 0.05,
  });
  slide.addText('⚠️ 安全提示: DDoS测试功能仅限授权测试环境使用，禁止用于非法用途', {
    x: 0.7, y: 4.6, w: 8.6, h: 0.5,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });
}

/**
 * 页面21: 结果验证
 */
function addResultVerificationSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('步骤4-5: 验证与查看', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 左侧截图占位框
  slide.addShape('roundRect', {
    x: 0.5, y: 1, w: 5.5, h: 3.2,
    fill: { color: COLORS.gray200 },
    line: { color: COLORS.gray400, width: 2, dashType: 'dash' },
    radius: 0.1,
  });

  slide.addText('📸 Syslog日志接收页面截图', {
    x: 0.5, y: 2.2, w: 5.5, h: 0.5,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray500,
    align: 'center',
  });

  // 右侧功能说明
  slide.addText('日志功能', {
    x: 6.2, y: 1, w: 3.3, h: 0.4,
    fontSize: 18,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  const logFeatures = [
    { icon: '📥', text: '自动接收Syslog日志' },
    { icon: '🔍', text: '关键词搜索过滤' },
    { icon: '📅', text: '时间范围筛选' },
    { icon: '🏷️', text: '日志级别分类' },
    { icon: '📤', text: '导出日志文件' },
  ];

  logFeatures.forEach((f, i) => {
    slide.addText(`${f.icon} ${f.text}`, {
      x: 6.2, y: 1.5 + i * 0.45, w: 3.3, h: 0.4,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: COLORS.gray700,
    });
  });

  // 强调卡片
  slide.addShape('roundRect', {
    x: 6.2, y: 3.8, w: 3.3, h: 0.8,
    fill: { color: COLORS.secondary },
    radius: 0.05,
  });
  slide.addText('✅ 所有测试过程自动记录\n可追溯、可复盘', {
    x: 6.4, y: 3.85, w: 3, h: 0.7,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });

  // 底部说明
  slide.addText('📌 通过日志验证防火墙是否正确响应测试报文，支持多设备日志集中查看', {
    x: 0.5, y: 4.5, w: 9, h: 0.4,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
    align: 'center',
  });
}

/**
 * 添加装饰圆形
 */
function addDecorCircles(slide) {
  slide.addShape('ellipse', {
    x: -0.5, y: -0.5, w: 1.5, h: 1.5,
    fill: { color: 'FFFFFF', transparency: 80 },
  });

  slide.addShape('ellipse', {
    x: 8.5, y: -0.5, w: 1.5, h: 1.5,
    fill: { color: 'FFFFFF', transparency: 80 },
  });

  slide.addShape('ellipse', {
    x: -0.5, y: 4, w: 1.5, h: 1.5,
    fill: { color: 'FFFFFF', transparency: 60 },
  });

  slide.addShape('ellipse', {
    x: 8.5, y: 4, w: 1.5, h: 1.5,
    fill: { color: 'FFFFFF', transparency: 60 },
  });
}

module.exports = { generatePart3 };