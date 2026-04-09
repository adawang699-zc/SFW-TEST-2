/**
 * Part 4: 收尾部分（4页）
 */

const { COLORS } = require('../utils/colors');

/**
 * 生成Part4收尾的所有幻灯片
 * @param {PptxGenJS} pptx - PPT实例
 */
function generatePart4(pptx) {
  // 页面22: 章节标题页
  addClosingSectionSlide(pptx);

  // 页面23: 使用门槛
  addRequirementsSlide(pptx);

  // 页面24: 下一步行动
  addNextStepsSlide(pptx);

  // 页面25: 结束页
  addEndSlide(pptx);
}

/**
 * 页面22: 章节标题页
 */
function addClosingSectionSlide(pptx) {
  let slide = pptx.addSlide();

  // 紫色背景
  slide.background = { color: COLORS.purple };

  // 装饰圆形
  addDecorCircles(slide);

  // 大图标
  slide.addText('🚀', {
    x: 4, y: 0.8, w: 2, h: 1,
    fontSize: 60,
    align: 'center',
  });

  // 大标题
  slide.addText('快速上手', {
    x: 0.5, y: 2, w: 9, h: 1,
    fontSize: 48,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });

  // 底部概要
  slide.addText('了解使用门槛 → 开始第一次测试 → 获取技术支持', {
    x: 1, y: 3.5, w: 8, h: 0.8,
    fontSize: 18,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
    valign: 'middle',
  });
}

/**
 * 页面23: 使用门槛
 */
function addRequirementsSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('使用门槛很低', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 说明
  slide.addText('无需安装客户端，打开浏览器即可使用', {
    x: 0.5, y: 1, w: 9, h: 0.4,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });

  // 4个门槛卡片
  const requirements = [
    {
      icon: '🌐',
      title: '浏览器',
      desc: 'Chrome浏览器（推荐）',
      detail: '兼容性最佳，建议使用最新版本',
      color: COLORS.primary
    },
    {
      icon: '🔐',
      title: '权限',
      desc: '测试设备SSH账号',
      detail: '用于Agent部署和管理',
      color: COLORS.secondary
    },
    {
      icon: '💻',
      title: '测试设备',
      desc: 'Windows 7+ 或 Linux',
      detail: 'Agent运行环境',
      color: COLORS.accent
    },
    {
      icon: '⏱️',
      title: '学习成本',
      desc: '约30分钟熟悉',
      detail: '操作简单，界面直观',
      color: COLORS.purple
    },
  ];

  const reqY = 1.5;
  const reqWidth = 2.1;
  const reqHeight = 2.5;

  requirements.forEach((req, i) => {
    const x = 0.5 + i * (reqWidth + 0.25);

    // 门槛卡片
    slide.addShape('roundRect', {
      x: x, y: reqY, w: reqWidth, h: reqHeight,
      fill: { color: req.color },
      radius: 0.1,
    });

    // 图标
    slide.addText(req.icon, {
      x: x + 0.1, y: reqY + 0.15, w: reqWidth - 0.2, h: 0.5,
      fontSize: 32,
      align: 'center',
    });

    // 标题
    slide.addText(req.title, {
      x: x + 0.1, y: reqY + 0.7, w: reqWidth - 0.2, h: 0.35,
      fontSize: 16,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
      align: 'center',
    });

    // 描述
    slide.addText(req.desc, {
      x: x + 0.1, y: reqY + 1.1, w: reqWidth - 0.2, h: 0.4,
      fontSize: 12,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
    });

    // 详细说明
    slide.addText(req.detail, {
      x: x + 0.1, y: reqY + 1.6, w: reqWidth - 0.2, h: 0.7,
      fontSize: 10,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'center',
    });
  });

  // 底部强调卡片
  slide.addShape('roundRect', {
    x: 0.5, y: 4.3, w: 9, h: 0.8,
    fill: { color: COLORS.secondary },
    radius: 0.08,
  });
  slide.addText('✅ 无需安装客户端，打开浏览器即可使用\n✅ 界面简洁直观，新用户30分钟上手', {
    x: 0.7, y: 4.35, w: 8.6, h: 0.7,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });
}

/**
 * 页面24: 下一步行动
 */
function addNextStepsSlide(pptx) {
  let slide = pptx.addSlide();

  slide.background = { color: 'FFFFFF' };

  // 标题
  slide.addText('开始你的第一次测试', {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });

  // 行动清单
  const actionItems = [
    {
      num: '1',
      title: '获取系统访问账号',
      desc: '联系管理员获取登录账号和密码',
      contact: '联系管理员',
      color: COLORS.primary
    },
    {
      num: '2',
      title: '完成首次环境配置',
      desc: '添加测试设备信息，配置SSH连接',
      contact: '参考操作手册',
      color: COLORS.secondary
    },
    {
      num: '3',
      title: '尝试第一个测试任务',
      desc: '建议从报文发送功能开始体验',
      contact: '建议: 报文发送',
      color: COLORS.accent
    },
    {
      num: '4',
      title: '加入技术支持群',
      desc: '遇到问题随时提问，获取帮助',
      contact: '扫码加入',
      color: COLORS.purple
    },
  ];

  const actionY = 1;
  const actionWidth = 4.3;
  const actionHeight = 1.2;

  actionItems.forEach((item, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * (actionWidth + 0.4);
    const y = actionY + row * (actionHeight + 0.3);

    // 行动卡片
    slide.addShape('roundRect', {
      x: x, y: y, w: actionWidth, h: actionHeight,
      fill: { color: item.color },
      radius: 0.1,
    });

    // 编号
    slide.addText(item.num, {
      x: x + 0.2, y: y + 0.2, w: 0.5, h: 0.5,
      fontSize: 22,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
    });

    // 标题
    slide.addText(item.title, {
      x: x + 0.8, y: y + 0.2, w: actionWidth - 1, h: 0.4,
      fontSize: 14,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      bold: true,
    });

    // 描述
    slide.addText(item.desc, {
      x: x + 0.2, y: y + 0.65, w: actionWidth - 0.4, h: 0.3,
      fontSize: 11,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
    });

    // 联系方式
    slide.addText(item.contact, {
      x: x + 0.2, y: y + 0.95, w: actionWidth - 0.4, h: 0.2,
      fontSize: 10,
      fontFace: 'Microsoft YaHei',
      color: 'FFFFFF',
      align: 'right',
    });
  });

  // 技术支持群二维码占位框
  slide.addShape('roundRect', {
    x: 6.2, y: 3.8, w: 1.8, h: 1.8,
    fill: { color: COLORS.gray200 },
    line: { color: COLORS.gray400, width: 1, dashType: 'dash' },
    radius: 0.05,
  });
  slide.addText('📸 技术支持群\n二维码', {
    x: 6.2, y: 4.3, w: 1.8, h: 0.8,
    fontSize: 10,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray500,
    align: 'center',
  });

  // 右侧提示
  slide.addText('遇到问题？', {
    x: 8.2, y: 3.9, w: 1.3, h: 0.4,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: COLORS.primary,
    bold: true,
  });
  slide.addText('随时在群里提问\n或者联系管理员', {
    x: 8.2, y: 4.3, w: 1.3, h: 0.8,
    fontSize: 10,
    fontFace: 'Microsoft YaHei',
    color: COLORS.gray600,
  });

  // 底部鼓励
  slide.addText('💪 开始你的第一次测试，体验自动化带来的效率提升！', {
    x: 0.5, y: 5.3, w: 6, h: 0.3,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: COLORS.accent,
    bold: true,
  });
}

/**
 * 页面25: 结束页
 */
function addEndSlide(pptx) {
  let slide = pptx.addSlide();

  // 渐变背景 (蓝色)
  slide.background = { color: COLORS.primary };

  // 装饰圆形
  addDecorCircles(slide);

  // 装饰小圆点
  const dotPositions = [
    { x: 1, y: 1.5 }, { x: 2, y: 0.8 }, { x: 8, y: 1.2 },
    { x: 7, y: 0.6 }, { x: 1.5, y: 4.5 }, { x: 8.5, y: 4.2 }
  ];

  dotPositions.forEach(pos => {
    slide.addShape('ellipse', {
      x: pos.x, y: pos.y, w: 0.3, h: 0.3,
      fill: { color: 'FFFFFF', transparency: 50 },
    });
  });

  // 大标题
  slide.addText('感谢聆听', {
    x: 0.5, y: 1.8, w: 9, h: 1,
    fontSize: 52,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });

  // 副标题
  slide.addText('如有疑问，欢迎随时提问', {
    x: 0.5, y: 2.9, w: 9, h: 0.6,
    fontSize: 20,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });

  // 联系方式卡片
  slide.addShape('roundRect', {
    x: 2.5, y: 3.6, w: 5, h: 1.2,
    fill: { color: 'FFFFFF', transparency: 20 },
    radius: 0.1,
  });

  slide.addText('📞 联系方式', {
    x: 2.5, y: 3.7, w: 5, h: 0.4,
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  });

  slide.addText('技术支持群 | 管理员邮箱 | 操作文档', {
    x: 2.5, y: 4.2, w: 5, h: 0.5,
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  });

  // 底部装饰文字
  slide.addText('工业防火墙自动化测试平台 | 让测试变得简单高效', {
    x: 0.5, y: 5, w: 9, h: 0.4,
    fontSize: 12,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
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

module.exports = { generatePart4 };