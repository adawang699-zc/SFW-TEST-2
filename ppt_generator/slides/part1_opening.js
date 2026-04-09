/**
 * Part 1: 开场部分（5页）
 */

const { COLORS, FUNCTION_COLORS } = require('../utils/colors');

/**
 * 生成Part1开场的所有幻灯片
 * @param {PptxGenJS} pptx - PPT实例
 */
function generatePart1(pptx) {
  // 页面1: 封面
  addCoverSlide(pptx);

  // 页面2: 痛点故事
  addPainPointsSlide(pptx);

  // 页面3: 解决方案概览
  addSolutionOverviewSlide(pptx);

  // 页面4: 效益数据
  addBenefitsDataSlide(pptx);

  // 页面5: 培训议程
  addAgendaSlide(pptx);
}

/**
 * 页面1: 封面
 */
function addCoverSlide(pptx) {
  let slide = pptx.addSlide();

  // 渐变背景 (蓝色)
  slide.background = { color: COLORS.primary };

  // 添加装饰圆形
  addDecorCircles(slide);

  // 项目图标区域
  slide.addText('🛡️', {
    x: 3.5, y: 0.5, w: 3, h: 1,
    fontSize: 60,
    align: 'center',
  });

  // 大标题
  slide.addText('工业防火墙自动化测试平台', {
    x: 0.5, y: 1.6, w: 9, h: 1,
    fontSize: 44,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });

  // 副标题
  slide.addText('让测试变得简单高效', {
    x: 0.5, y: 2.7, w: 9, h: 0.6,
    fontSize: 24,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });

  // 关键特性卡片
  const features = [
    { icon: '🌐', text: 'Web统一管理' },
    { icon: '⚡', text: '自动化测试' },
    { icon: '🔌', text: '30+工控协议' },
    { icon: '📊', text: '结果可追溯' },
  ];

  const featureY = 3.5;
  const featureWidth = 2.2;

  features.forEach((f, i) => {
    const x = 0.5 + i * (featureWidth + 0.2);

    slide.addShape('roundRect', {
      x: x, y: featureY, w: featureWidth, h: 0.8,
      fill: { color: 'FFFFFF', transparency: 20 },
      radius: 0.08,
    });

    slide.addText(`${f.icon} ${f.text}`, {
      x: x + 0.1, y: featureY + 0.15, w: featureWidth - 0.2, h: 0.5,
      fontSize: 14,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });
  });

  // 底部信息
  slide.addText('培训演示 | 2026年4月', {
    x: 0.5, y: 4.8, w: 9, h: 0.4,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });
}

/**
 * 页面2: 痛点故事
 */
function addPainPointsSlide(pptx) {
  let slide = pptx.addSlide();

  // 白色背景
  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('一个测试工程师的困境', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 场景描述
  slide.addText('某测试工程师的一天...', {
    x: 0.5, y: 1, w: 9, h: 0.4,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });

  // 4个痛点卡片
  const painPoints = [
    {
      icon: '💻',
      title: '环境切换麻烦',
      desc: '不同测试环境需要切换不同电脑操作，来回跑动浪费时间',
      color: COLORS.gray600
    },
    {
      icon: '🔧',
      title: '工具分散使用',
      desc: '报文发送、端口扫描、日志接收等工具分散，需要同时运行多个',
      color: COLORS.gray600
    },
    {
      icon: '⚡',
      title: '协议测试复杂',
      desc: '工控协议种类多，配置复杂，容易出错，测试效率低',
      color: COLORS.gray600
    },
    {
      icon: '📝',
      title: '记录难追溯',
      desc: '测试结果手工记录，容易遗漏，事后难以复盘追溯',
      color: COLORS.gray600
    },
  ];

  const cardY = 1.5;
  const cardWidth = 4.3;
  const cardHeight = 1.5;

  painPoints.forEach((p, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * (cardWidth + 0.4);
    const y = cardY + row * (cardHeight + 0.2);

    // 痛点卡片 (灰色调表示困境)
    slide.addShape('roundRect', {
      x: x, y: y, w: cardWidth, h: cardHeight,
      fill: { color: COLORS.gray300 },
      line: { color: COLORS.gray400, width: 1 },
      radius: 0.1,
    });

    // 图标
    slide.addText(p.icon, {
      x: x + 0.2, y: y + 0.15, w: 0.6, h: 0.6,
      fontSize: 28,
      align: 'center',
    });

    // 标题
    slide.addText(p.title, {
      x: x + 0.9, y: y + 0.2, w: cardWidth - 1.1, h: 0.4,
      fontSize: 16,
      fontFace: 'Microsoft YaHei',
      color: COLORS.gray700,
      bold: true,
    });

    // 描述
    slide.addText(p.desc, {
      x: x + 0.2, y: y + 0.8, w: cardWidth - 0.4, h: 0.6,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: COLORS.gray600,
    });
  });

  // 底部问题总结
  slide.addShape('roundRect', {
    x: 0.5, y: 4.6, w: 9, h: 0.8,
    fill: { color: COLORS.accent },
    radius: 0.05,
  });
  slide.addText('❓ 问题: 测试效率低、出错多、难追溯 → 影响项目进度和质量', {
    x: 0.7, y: 4.7, w: 8.6, h: 0.6,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });
}

/**
 * 页面3: 解决方案概览
 */
function addSolutionOverviewSlide(pptx) {
  let slide = pptx.addSlide();

  // 白色背景
  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('我们带来了解决方案', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 系统定位卡片 (中央大卡片)
  slide.addShape('roundRect', {
    x: 1.5, y: 1, w: 7, h: 1.2,
    fill: { color: COLORS.primary },
    radius: 0.1,
  });

  slide.addText('工业防火墙自动化测试平台', {
    x: 1.5, y: 1.15, w: 7, h: 0.5,
    fontSize: 20,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });

  slide.addText('一站式Web平台，集成测试工具，支持30+工控协议，自动化测试流程', {
    x: 1.5, y: 1.7, w: 7, h: 0.4,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });

  // 四大核心价值卡片
  const values = [
    {
      icon: '🌐',
      title: '统一管理',
      desc: '一个Web界面，告别环境切换烦恼',
      keywords: ['一站式', '无需切换'],
      color: COLORS.primary
    },
    {
      icon: '⚡',
      title: '自动化测试',
      desc: '配置→执行→记录→报告，一键完成',
      keywords: ['效率倍增', '流程简化'],
      color: COLORS.secondary
    },
    {
      icon: '🔌',
      title: '工控协议',
      desc: '30+工控协议支持，覆盖主流场景',
      keywords: ['Modbus', 'S7', 'GOOSE'],
      color: COLORS.accent
    },
    {
      icon: '📊',
      title: '结果追溯',
      desc: '测试过程自动记录，可复盘验证',
      keywords: ['自动记录', '可追溯'],
      color: COLORS.purple
    },
  ];

  const valueY = 2.5;
  const valueWidth = 2.1;
  const valueHeight = 2.3;

  values.forEach((v, i) => {
    const x = 0.5 + i * (valueWidth + 0.25);

    // 价值卡片
    slide.addShape('roundRect', {
      x: x, y: valueY, w: valueWidth, h: valueHeight,
      fill: { color: v.color },
      radius: 0.1,
    });

    // 图标
    slide.addText(v.icon, {
      x: x + 0.1, y: valueY + 0.2, w: valueWidth - 0.2, h: 0.5,
      fontSize: 32,
      align: 'center',
    });

    // 标题
    slide.addText(v.title, {
      x: x + 0.1, y: valueY + 0.8, w: valueWidth - 0.2, h: 0.4,
      fontSize: 16,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });

    // 描述
    slide.addText(v.desc, {
      x: x + 0.1, y: valueY + 1.3, w: valueWidth - 0.2, h: 0.5,
      fontSize: 11,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
    });

    // 关键词
    const keywordText = v.keywords.join(' | ');
    slide.addText(keywordText, {
      x: x + 0.1, y: valueY + 1.85, w: valueWidth - 0.2, h: 0.35,
      fontSize: 10,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
    });
  });

  // 底部强调
  slide.addText('💡 目标: 提升测试效率30%，降低错误率20%，让测试变得简单', {
    x: 0.5, y: 5, w: 9, h: 0.4,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: COLORS.secondary,
    align: 'center',
  });
}

/**
 * 页面4: 效益数据
 */
function addBenefitsDataSlide(pptx) {
  let slide = pptx.addSlide();

  // 白色背景
  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('实际效益', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 说明
  slide.addText('使用前后对比数据（示例）', {
    x: 0.5, y: 1, w: 9, h: 0.3,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });

  // 数据对比图表
  const chartData = [
    { name: '改进前', labels: ['配置时间', '错误率', '工作强度'], values: [10, 5, 10] },
    { name: '改进后', labels: ['配置时间', '错误率', '工作强度'], values: [7, 7, 8] },
  ];

  slide.addChart('bar', chartData, {
    x: 0.5, y: 1.4, w: 5.5, h: 3,
    barDir: 'bar',
    barGrouping: 'clustered',
    showTitle: false,
    showLegend: true,
    legendPos: 'b',
    chartColors: [COLORS.gray500, COLORS.secondary],
    valAxisMaxVal: 15,
    catAxisLabelFontSize: 11,
    valAxisLabelFontSize: 10,
    showValue: true,
  });

  // 图表说明
  slide.addText('单位: 分钟 | % | 相对值', {
    x: 0.5, y: 4.5, w: 5.5, h: 0.3,
    fontSize: 11,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
    align: 'center',
  });

  // 右侧关键数据卡片
  const keyData = [
    { label: '配置时间', before: '10分钟', after: '7分钟', change: '-30%', color: COLORS.primary },
    { label: '测试效率', before: '基准', after: '提升', change: '+30%', color: COLORS.secondary },
    { label: '错误率', before: '10%', after: '8%', change: '-20%', color: COLORS.accent },
  ];

  const dataY = 1.4;
  const dataWidth = 3.8;
  const dataHeight = 1;

  keyData.forEach((d, i) => {
    const y = dataY + i * (dataHeight + 0.2);

    // 数据卡片
    slide.addShape('roundRect', {
      x: 6.2, y: y, w: dataWidth, h: dataHeight,
      fill: { color: d.color },
      radius: 0.08,
    });

    // 标签
    slide.addText(d.label, {
      x: 6.4, y: y + 0.1, w: 1.5, h: 0.3,
      fontSize: 14,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
    });

    // 改进前后对比
    slide.addText(`${d.before} → ${d.after}`, {
      x: 6.4, y: y + 0.45, w: 2.2, h: 0.3,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
    });

    // 变化百分比
    slide.addText(d.change, {
      x: 8.6, y: y + 0.25, w: 1.2, h: 0.5,
      fontSize: 20,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });
  });

  // 底部总结
  slide.addShape('roundRect', {
    x: 6.2, y: 4.6, w: 3.8, h: 0.8,
    fill: { color: COLORS.purple },
    radius: 0.05,
  });
  slide.addText('✅ 效果: 省时、省力、更准确', {
    x: 6.4, y: 4.7, w: 3.4, h: 0.6,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });
}

/**
 * 页面5: 培训议程
 */
function addAgendaSlide(pptx) {
  let slide = pptx.addSlide();

  // 白色背景
  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('今天你将学到', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 培训时长
  slide.addText('培训时长: 约35分钟 (含答疑)', {
    x: 0.5, y: 1, w: 9, h: 0.4,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });

  // 四部分议程
  const agendaItems = [
    {
      num: '01',
      title: '开场部分',
      content: '痛点故事、解决方案、效益数据',
      duration: '5分钟',
      color: COLORS.primary
    },
    {
      num: '02',
      title: '核心功能',
      content: '统一管理、自动化、工控协议、并发',
      duration: '10分钟',
      color: COLORS.secondary
    },
    {
      num: '03',
      title: '操作演示',
      content: '环境配置、Agent部署、测试执行',
      duration: '15分钟',
      color: COLORS.accent
    },
    {
      num: '04',
      title: '快速上手',
      content: '使用门槛、下一步行动、答疑',
      duration: '5分钟',
      color: COLORS.purple
    },
  ];

  const agendaY = 1.5;
  const agendaWidth = 2.1;
  const agendaHeight = 2.8;

  agendaItems.forEach((item, i) => {
    const x = 0.5 + i * (agendaWidth + 0.25);

    // 议程卡片
    slide.addShape('roundRect', {
      x: x, y: agendaY, w: agendaWidth, h: agendaHeight,
      fill: { color: item.color },
      radius: 0.1,
    });

    // 编号
    slide.addText(item.num, {
      x: x + 0.1, y: agendaY + 0.15, w: agendaWidth - 0.2, h: 0.5,
      fontSize: 28,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });

    // 标题
    slide.addText(item.title, {
      x: x + 0.1, y: agendaY + 0.7, w: agendaWidth - 0.2, h: 0.4,
      fontSize: 16,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });

    // 内容
    slide.addText(item.content, {
      x: x + 0.1, y: agendaY + 1.2, w: agendaWidth - 0.2, h: 1,
      fontSize: 11,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
    });

    // 时长
    slide.addText(item.duration, {
      x: x + 0.1, y: agendaY + 2.3, w: agendaWidth - 0.2, h: 0.4,
      fontSize: 14,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });
  });

  // 底部提示
  slide.addText('📌 目标: 了解系统价值 → 学会基本操作 → 能够独立使用', {
    x: 0.5, y: 4.5, w: 9, h: 0.5,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
    align: 'center',
  });
}

/**
 * 添加装饰圆形
 */
function addDecorCircles(slide) {
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

module.exports = { generatePart1 };