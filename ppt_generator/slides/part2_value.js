/**
 * Part 2: 价值展示（8页）
 */

const { COLORS, FUNCTION_COLORS } = require('../utils/colors');
const { POSITIONS, TEXT_STYLES, SHAPE_STYLES } = require('../utils/layouts');

/**
 * 生成Part2价值展示的所有幻灯片
 * @param {PptxGenJS} pptx - PPT实例
 */
function generatePart2(pptx) {
  // 页面6: 章节标题页
  addSectionTitleSlide(pptx, '核心功能亮点', COLORS.secondary, [
    '统一管理，一站式操作',
    '自动化测试，效率倍增',
    '30+工控协议支持'
  ]);

  // 页面7: 统一管理详细页
  addUnifiedManagementSlide(pptx);

  // 页面8: 自动化流程
  addAutomationFlowSlide(pptx);

  // 页面9: 工控协议墙
  addProtocolWallSlide(pptx);

  // 页面10: 并发协作
  addConcurrencySlide(pptx);

  // 页面11: 真实案例
  addRealCaseSlide(pptx);

  // 页面12: 用户反馈
  addUserFeedbackSlide(pptx);

  // 页面13: 系统架构
  addArchitectureSlide(pptx);
}

/**
 * 添加章节标题幻灯片
 */
function addSectionTitleSlide(pptx, title, bgColor, highlights) {
  let slide = pptx.addSlide();

  // 渐变背景
  slide.background = { color: bgColor };

  // 添加装饰圆形
  addDecorCircles(slide, bgColor);

  // 大标题
  slide.addText(title, {
    x: 0.5, y: 2, w: 9, h: 1,
    fontSize: 48,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });

  // 大图标 (使用emoji作为图标)
  slide.addText('🎯', {
    x: 4, y: 0.8, w: 2, h: 1,
    fontSize: 60,
    align: 'center',
  });

  // 底部概要
  if (highlights && highlights.length > 0) {
    let summaryText = highlights.map((h, i) => `${i + 1}. ${h}`).join('\n');
    slide.addText(summaryText, {
      x: 1, y: 3.5, w: 8, h: 1.5,
      fontSize: 18,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
      valign: 'middle',
    });
  }
}

/**
 * 页面7: 统一管理详细页
 */
function addUnifiedManagementSlide(pptx) {
  let slide = pptx.addSlide();

  // 白色背景
  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('统一管理，一站式操作', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 核心价值说明
  slide.addText('核心价值: 一个Web界面搞定所有测试', {
    x: 0.5, y: 1, w: 9, h: 0.4,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });

  // 左侧卡片：改进前
  slide.addShape('roundRect', {
    x: 0.5, y: 1.5, w: 4.3, h: 3,
    fill: { color: COLORS.gray200 },
    line: { color: COLORS.gray400, width: 1 },
    radius: 0.1,
  });

  slide.addText('改进前', {
    x: 0.7, y: 1.6, w: 4, h: 0.4,
    fontSize: 18,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray700,
    bold: true,
  });

  const beforeItems = [
    '❌ 不同测试环境切换电脑操作麻烦',
    '❌ 需要多个测试工具分散使用',
    '❌ 工具功能有限，无法满足需求',
    '❌ 测试结果手工记录难追溯'
  ];

  slide.addText(beforeItems.join('\n'), {
    x: 0.7, y: 2.1, w: 4, h: 2.2,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
    valign: 'top',
  });

  // 右侧卡片：改进后
  slide.addShape('roundRect', {
    x: 5.2, y: 1.5, w: 4.3, h: 3,
    fill: { color: COLORS.secondary },
    radius: 0.1,
  });

  slide.addText('改进后', {
    x: 5.4, y: 1.6, w: 4, h: 0.4,
    fontSize: 18,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
  });

  const afterItems = [
    '✅ 全部在Web界面操作，无需切换',
    '✅ 所有工具集成在Agent上',
    '✅ 新开发多种测试工具，能力增强',
    '✅ 测试结果自动记录，可追溯'
  ];

  slide.addText(afterItems.join('\n'), {
    x: 5.4, y: 2.1, w: 4, h: 2.2,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    valign: 'top',
  });

  // 底部工具列表
  slide.addShape('roundRect', {
    x: 0.5, y: 4.7, w: 9, h: 0.7,
    fill: { color: COLORS.primary },
    radius: 0.05,
  });

  slide.addText('集成工具: 报文发送 | 端口扫描 | 协议测试 | 日志接收 | DDoS压力测试 | 工控协议模拟 | 批量验证', {
    x: 0.7, y: 4.8, w: 8.6, h: 0.5,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });
}

/**
 * 页面8: 自动化流程
 */
function addAutomationFlowSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('自动化测试，效率倍增', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 流程说明
  slide.addText('简化测试流程，从配置到报告一键完成', {
    x: 0.5, y: 1, w: 9, h: 0.4,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });

  // 5步流程图
  const steps = [
    { num: '1', title: '配置环境', desc: '设置测试设备参数', time: '5分钟', color: COLORS.primary },
    { num: '2', title: '部署Agent', desc: '一键同步到测试设备', time: '2分钟', color: COLORS.teal },
    { num: '3', title: '执行测试', desc: '选择测试类型并运行', time: '按需', color: COLORS.accent },
    { num: '4', title: '验证结果', desc: '实时查看测试输出', time: '实时', color: COLORS.purple },
    { num: '5', title: '生成报告', desc: '自动汇总测试结果', time: '自动', color: COLORS.secondary },
  ];

  const stepWidth = 1.7;
  const stepHeight = 2.2;
  const startX = 0.5;
  const startY = 1.6;
  const gap = 0.3;

  steps.forEach((step, i) => {
    const x = startX + i * (stepWidth + gap);

    // 步骤卡片
    slide.addShape('roundRect', {
      x: x, y: startY, w: stepWidth, h: stepHeight,
      fill: { color: step.color },
      radius: 0.1,
    });

    // 步骤编号
    slide.addText(step.num, {
      x: x + 0.1, y: startY + 0.1, w: stepWidth - 0.2, h: 0.5,
      fontSize: 24,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });

    // 步骤标题
    slide.addText(step.title, {
      x: x + 0.1, y: startY + 0.6, w: stepWidth - 0.2, h: 0.4,
      fontSize: 14,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });

    // 步骤描述
    slide.addText(step.desc, {
      x: x + 0.1, y: startY + 1.1, w: stepWidth - 0.2, h: 0.6,
      fontSize: 11,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
    });

    // 时间标注
    slide.addText(step.time, {
      x: x + 0.1, y: startY + 1.8, w: stepWidth - 0.2, h: 0.3,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
    });

    // 箭头（除最后一个）
    if (i < steps.length - 1) {
      slide.addShape('rightArrow', {
        x: x + stepWidth, y: startY + 0.8, w: gap, h: 0.3,
        fill: { color: COLORS.gray400 },
      });
    }
  });

  // 底部强调
  slide.addText('💡 所有测试过程自动记录，结果可追溯、可复盘', {
    x: 0.5, y: 4.2, w: 9, h: 0.5,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: COLORS.accent,
    align: 'center',
  });
}

/**
 * 页面9: 工控协议墙
 */
function addProtocolWallSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('30+工控协议支持', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 统计卡片
  slide.addShape('roundRect', {
    x: 7.5, y: 0.3, w: 2, h: 0.6,
    fill: { color: COLORS.secondary },
    radius: 0.05,
  });
  slide.addText('30+ 协议', {
    x: 7.5, y: 0.35, w: 2, h: 0.5,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });

  // 核心协议（顶部大图标）
  const coreProtocols = [
    { name: 'Modbus', icon: '🔌', color: COLORS.primary },
    { name: 'S7', icon: '⚡', color: COLORS.accent },
    { name: 'GOOSE', icon: '📡', color: COLORS.purple },
    { name: 'SV', icon: '📊', color: COLORS.teal },
  ];

  const coreStartX = 0.5;
  const coreY = 1.1;
  const coreWidth = 2.2;
  const coreHeight = 0.8;

  coreProtocols.forEach((p, i) => {
    const x = coreStartX + i * (coreWidth + 0.3);
    slide.addShape('roundRect', {
      x: x, y: coreY, w: coreWidth, h: coreHeight,
      fill: { color: p.color },
      radius: 0.08,
    });
    slide.addText(`${p.icon} ${p.name}`, {
      x: x, y: coreY + 0.2, w: coreWidth, h: 0.4,
      fontSize: 16,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });
  });

  // 其他协议网格
  const otherProtocols = [
    'EtherCAT', 'PROFINET', 'DNP3', 'BACnet',
    'OPC UA', 'IEC104', 'CIP', 'FINS',
    'HART', 'LonWorks', 'KNX', 'Melsec',
    'Profibus', 'CANopen', 'DeviceNet', 'CC-Link',
    'AS-i', 'Interbus', 'Sercos', 'EtherNet/IP',
    'Modbus TCP', 'Modbus RTU', 'S7Comm', 'MQTT',
    'HTTP', 'CoAP', 'SNMP', 'Syslog'
  ];

  const gridStartX = 0.5;
  const gridStartY = 2;
  const cellWidth = 1.6;
  const cellHeight = 0.5;
  const cols = 7;
  const rows = 4;

  otherProtocols.slice(0, 28).forEach((p, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = gridStartX + col * (cellWidth + 0.2);
    const y = gridStartY + row * (cellHeight + 0.15);

    // 交替颜色
    const bgColor = i % 2 === 0 ? COLORS.gray200 : COLORS.gray300;

    slide.addShape('roundRect', {
      x: x, y: y, w: cellWidth, h: cellHeight,
      fill: { color: bgColor },
      radius: 0.05,
    });

    slide.addText(p, {
      x: x, y: y + 0.1, w: cellWidth, h: 0.3,
      fontSize: 11,
      fontFace: 'Microsoft YaHei',
      color: COLORS.gray700,
      align: 'center',
    });
  });

  // 行业分类标签
  const categories = [
    { name: '电力行业', protocols: 'GOOSE, SV, IEC104, DNP3', color: COLORS.primary },
    { name: '石油化工', protocols: 'Modbus, HART, Profibus', color: COLORS.accent },
    { name: '交通轨道', protocols: 'CANopen, LonWorks, KNX', color: COLORS.purple },
    { name: '智能制造', protocols: 'PROFINET, EtherCAT, OPC UA', color: COLORS.teal },
  ];

  const catY = 4.3;
  const catWidth = 2.2;

  categories.forEach((cat, i) => {
    const x = 0.5 + i * (catWidth + 0.3);
    slide.addShape('roundRect', {
      x: x, y: catY, w: catWidth, h: 1,
      fill: { color: cat.color },
      radius: 0.08,
    });
    slide.addText(cat.name, {
      x: x, y: catY + 0.1, w: catWidth, h: 0.3,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });
    slide.addText(cat.protocols, {
      x: x, y: catY + 0.5, w: catWidth, h: 0.4,
      fontSize: 10,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
    });
  });
}

/**
 * 页面10: 并发协作
 */
function addConcurrencySlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('多组并发，互不干扰', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 说明
  slide.addText('支持多组独立测试环境，资源隔离，不会冲突', {
    x: 0.5, y: 1, w: 9, h: 0.4,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });

  // 三个测试组图示
  const groups = [
    { name: '测试组 A', devices: '防火墙A + AgentA', color: COLORS.primary },
    { name: '测试组 B', devices: '防火墙B + AgentB', color: COLORS.secondary },
    { name: '测试组 C', devices: '防火墙C + AgentC', color: COLORS.accent },
  ];

  const groupY = 1.6;
  const groupWidth = 2.8;
  const groupHeight = 1.5;

  groups.forEach((g, i) => {
    const x = 0.5 + i * (groupWidth + 0.5);

    // 组卡片
    slide.addShape('roundRect', {
      x: x, y: groupY, w: groupWidth, h: groupHeight,
      fill: { color: g.color },
      radius: 0.1,
    });

    // 组名称
    slide.addText(g.name, {
      x: x + 0.2, y: groupY + 0.2, w: groupWidth - 0.4, h: 0.4,
      fontSize: 18,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });

    // 设备说明
    slide.addText(g.devices, {
      x: x + 0.2, y: groupY + 0.7, w: groupWidth - 0.4, h: 0.5,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
    });

    // 图标
    slide.addText('🔒', {
      x: x + 0.2, y: groupY + 1.1, w: groupWidth - 0.4, h: 0.3,
      fontSize: 20,
      align: 'center',
    });
  });

  // 管理平台连接示意
  slide.addShape('roundRect', {
    x: 0.5, y: 3.3, w: 9, h: 0.6,
    fill: { color: COLORS.gray200 },
    radius: 0.05,
  });
  slide.addText('🌐 统一管理平台 (Web界面)', {
    x: 0.5, y: 3.35, w: 9, h: 0.5,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray700,
    bold: true,
    align: 'center',
  });

  // 对比表格
  slide.addText('对比优势', {
    x: 0.5, y: 4.1, w: 9, h: 0.4,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 表格数据
  const tableData = [
    [{ text: '特性', options: { bold: true, fill: COLORS.primary, color: 'FFFFFF' } },
     { text: '单组测试', options: { bold: true, fill: COLORS.gray300 } },
     { text: '多组并发', options: { bold: true, fill: COLORS.secondary, color: 'FFFFFF' } }],
    [{ text: '资源利用', options: { fill: COLORS.gray200 } },
     { text: '低', options: { fill: COLORS.gray200 } },
     { text: '高 (3倍)', options: { fill: COLORS.gray100, color: COLORS.secondary, bold: true } }],
    [{ text: '等待时间', options: { fill: COLORS.gray200 } },
     { text: '长', options: { fill: COLORS.gray200 } },
     { text: '短', options: { fill: COLORS.gray100, color: COLORS.secondary, bold: true } }],
    [{ text: '团队协作', options: { fill: COLORS.gray200 } },
     { text: '难', options: { fill: COLORS.gray200 } },
     { text: '易', options: { fill: COLORS.gray100, color: COLORS.secondary, bold: true } }],
  ];

  slide.addTable(tableData, {
    x: 0.5, y: 4.5, w: 9, h: 1,
    fontFace: 'Microsoft YaHei',
    fontSize: 11,
    align: 'center',
    valign: 'middle',
  });
}

/**
 * 页面11: 真实案例
 */
function addRealCaseSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('实际应用案例', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 案例标题
  slide.addText('案例: 某防火墙功能验证测试', {
    x: 0.5, y: 1, w: 9, h: 0.4,
    fontSize: 18,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray700,
    bold: true,
  });

  // 数据对比图表
  const chartData = [
    { name: '改进前', labels: ['测试时间', '人力投入', '问题发现'], values: [8, 4, 20] },
    { name: '改进后', labels: ['测试时间', '人力投入', '问题发现'], values: [6, 4, 25] },
  ];

  slide.addChart('bar', chartData, {
    x: 0.5, y: 1.5, w: 6, h: 3,
    barDir: 'bar',
    barGrouping: 'clustered',
    showTitle: false,
    showLegend: true,
    legendPos: 'b',
    chartColors: [COLORS.gray500, COLORS.secondary],
    valAxisMaxVal: 30,
    catAxisLabelFontSize: 11,
    valAxisLabelFontSize: 10,
    showValue: true,
  });

  // 图表标签说明
  slide.addText('单位: 小时 | 人 | 个', {
    x: 0.5, y: 4.6, w: 6, h: 0.3,
    fontSize: 10,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
    align: 'center',
  });

  // 右侧关键发现卡片
  slide.addShape('roundRect', {
    x: 6.8, y: 1.5, w: 2.7, h: 3.5,
    fill: { color: COLORS.accent },
    radius: 0.1,
  });

  slide.addText('关键发现', {
    x: 7, y: 1.6, w: 2.5, h: 0.4,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });

  const findings = [
    '✅ 测试时间减少25%',
    '✅ 问题发现率提升25%',
    '✅ 测试流程标准化',
    '✅ 结果可追溯可复盘',
    '✅ 团队协作效率提升',
  ];

  slide.addText(findings.join('\n\n'), {
    x: 7, y: 2.1, w: 2.5, h: 2.8,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    valign: 'top',
  });
}

/**
 * 页面12: 用户反馈
 */
function addUserFeedbackSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('用户怎么说', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 用户反馈卡片
  const feedbacks = [
    {
      user: '测试工程师 A',
      content: '"以前测试要跑好几个工具，现在一个界面全搞定，太方便了！"',
      rating: 5,
      color: COLORS.primary
    },
    {
      user: '测试工程师 B',
      content: '"工控协议测试以前是最头疼的，现在点点按钮就行。"',
      rating: 5,
      color: COLORS.secondary
    },
    {
      user: '测试组长',
      content: '"测试结果自动记录，再也不用担心漏记录了。"',
      rating: 4,
      color: COLORS.accent
    },
    {
      user: '项目经理',
      content: '"团队测试效率提升明显，值得推广使用。"',
      rating: 5,
      color: COLORS.purple
    },
  ];

  const cardY = 1.1;
  const cardWidth = 4.3;
  const cardHeight = 1.8;

  feedbacks.forEach((f, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * (cardWidth + 0.4);
    const y = cardY + row * (cardHeight + 0.3);

    // 反馈卡片
    slide.addShape('roundRect', {
      x: x, y: y, w: cardWidth, h: cardHeight,
      fill: { color: f.color },
      radius: 0.1,
    });

    // 用户名
    slide.addText(f.user, {
      x: x + 0.2, y: y + 0.2, w: cardWidth - 0.4, h: 0.3,
      fontSize: 14,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
    });

    // 反馈内容
    slide.addText(f.content, {
      x: x + 0.2, y: y + 0.6, w: cardWidth - 0.4, h: 0.8,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
    });

    // 评分星星
    const stars = '★'.repeat(f.rating) + '☆'.repeat(5 - f.rating);
    slide.addText(stars, {
      x: x + 0.2, y: y + 1.4, w: cardWidth - 0.4, h: 0.3,
      fontSize: 14,
      color: 'FFFFFF',
      align: 'right',
    });
  });
}

/**
 * 页面13: 系统架构
 */
function addArchitectureSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('简单明了的架构', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 三层架构
  const layers = [
    {
      name: '操作者层',
      desc: '测试工程师通过浏览器访问',
      items: ['Chrome浏览器', 'Web界面操作', '无需安装客户端'],
      color: COLORS.primary,
      y: 1.2
    },
    {
      name: '管理平台层',
      desc: 'Django Web服务器，统一调度',
      items: ['测试环境管理', 'Agent同步部署', '测试任务调度', '结果汇总记录'],
      color: COLORS.secondary,
      y: 2.4
    },
    {
      name: '测试设备层',
      desc: 'Agent程序运行在测试设备上',
      items: ['Packet Agent (8888)', '工控协议Agent (8889)', '报文发送/端口扫描', '协议模拟测试'],
      color: COLORS.accent,
      y: 3.6
    },
  ];

  layers.forEach((layer) => {
    // 层卡片
    slide.addShape('roundRect', {
      x: 0.5, y: layer.y, w: 9, h: 1,
      fill: { color: layer.color },
      radius: 0.08,
    });

    // 层名称
    slide.addText(layer.name, {
      x: 0.7, y: layer.y + 0.1, w: 2, h: 0.3,
      fontSize: 16,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
    });

    // 层描述
    slide.addText(layer.desc, {
      x: 0.7, y: layer.y + 0.4, w: 2, h: 0.3,
      fontSize: 11,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
    });

    // 层内容
    const itemsText = layer.items.join(' | ');
    slide.addText(itemsText, {
      x: 2.8, y: layer.y + 0.25, w: 6.5, h: 0.5,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'left',
    });
  });

  // 连接箭头
  slide.addShape('downArrow', {
    x: 4.5, y: 2.2, w: 1, h: 0.2,
    fill: { color: COLORS.gray400 },
  });
  slide.addShape('downArrow', {
    x: 4.5, y: 3.4, w: 1, h: 0.2,
    fill: { color: COLORS.gray400 },
  });

  // 数据流说明
  slide.addText('数据流: HTTP请求 → 任务调度 → Agent执行 → 结果返回', {
    x: 0.5, y: 4.8, w: 9, h: 0.5,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
    align: 'center',
  });
}

/**
 * 添加装饰圆形
 */
function addDecorCircles(slide, baseColor) {
  // 左上角圆形
  slide.addShape('ellipse', {
    x: -0.5, y: -0.5, w: 1.5, h: 1.5,
    fill: { color: 'FFFFFF', transparency: 80 },
  });

  // 右上角圆形
  slide.addShape('ellipse', {
    x: 8.5, y: -0.5, w: 1.5, h: 1.5,
    fill: { color: 'FFFFFF', transparency: 80 },
  });

  // 左下角圆形
  slide.addShape('ellipse', {
    x: -0.5, y: 4, w: 1.5, h: 1.5,
    fill: { color: 'FFFFFF', transparency: 60 },
  });

  // 右下角圆形
  slide.addShape('ellipse', {
    x: 8.5, y: 4, w: 1.5, h: 1.5,
    fill: { color: 'FFFFFF', transparency: 60 },
  });
}

module.exports = { generatePart2 };