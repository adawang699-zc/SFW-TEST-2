/**
 * 布局模板 - 常用布局定义
 */

// PPT标准尺寸 (16:9)
const LAYOUT = {
  width: 10,    // 英寸
  height: 5.625, // 英寸
  margin: 0.5,
};

// 常用位置坐标
const POSITIONS = {
  // 标题区域
  title: { x: 0.5, y: 0.3, w: 9, h: 0.8 },
  subtitle: { x: 0.5, y: 1.2, w: 9, h: 0.5 },

  // 内容区域
  contentLeft: { x: 0.5, y: 1.8, w: 4.5, h: 3.5 },
  contentRight: { x: 5, y: 1.8, w: 4.5, h: 3.5 },
  contentCenter: { x: 1, y: 1.8, w: 8, h: 3.5 },
  contentFull: { x: 0.5, y: 1.5, w: 9, h: 4 },

  // 卡片位置（4卡片布局）
  cardTL: { x: 0.5, y: 1.8, w: 4.2, h: 1.5 },     // 左上
  cardTR: { x: 5.3, y: 1.8, w: 4.2, h: 1.5 },     // 右上
  cardBL: { x: 0.5, y: 3.5, w: 4.2, h: 1.5 },     // 左下
  cardBR: { x: 5.3, y: 3.5, w: 4.2, h: 1.5 },     // 右下

  // 卡片位置（2卡片布局）
  cardLeft: { x: 0.5, y: 1.8, w: 4.2, h: 3.2 },
  cardRight: { x: 5.3, y: 1.8, w: 4.2, h: 3.2 },

  // 流程图位置（5步）
  step1: { x: 0.3, y: 2.5, w: 1.8, h: 2 },
  step2: { x: 2.1, y: 2.5, w: 1.8, h: 2 },
  step3: { x: 3.9, y: 2.5, w: 1.8, h: 2 },
  step4: { x: 5.7, y: 2.5, w: 1.8, h: 2 },
  step5: { x: 7.5, y: 2.5, w: 1.8, h: 2 },

  // 截图占位框位置
  screenshotLeft: { x: 0.5, y: 1.5, w: 5, h: 3.5 },
  screenshotRight: { x: 5.5, y: 1.5, w: 4, h: 3.5 },
  screenshotFull: { x: 0.5, y: 1.2, w: 9, h: 4 },

  // 四宫格位置
  quadTL: { x: 0.3, y: 1.5, w: 4.5, h: 1.8 },
  quadTR: { x: 5.2, y: 1.5, w: 4.5, h: 1.8 },
  quadBL: { x: 0.3, y: 3.5, w: 4.5, h: 1.8 },
  quadBR: { x: 5.2, y: 3.5, w: 4.5, h: 1.8 },

  // 底部提示区域
  footer: { x: 0.5, y: 4.8, w: 9, h: 0.6 },

  // 装饰圆形位置
  decorCircle1: { x: -0.5, y: -0.5, w: 2, h: 2 },
  decorCircle2: { x: 8.5, y: -0.5, w: 2, h: 2 },
  decorCircle3: { x: -0.5, y: 3.5, w: 2, h: 2 },
  decorCircle4: { x: 8.5, y: 3.5, w: 2, h: 2 },
};

// 文字样式
const TEXT_STYLES = {
  // 标题样式
  titleLarge: {
    fontSize: 44,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  },
  titleMedium: {
    fontSize: 32,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  },
  titleSection: {
    fontSize: 36,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  },

  // 内容样式
  contentTitle: {
    fontSize: 24,
    fontFace: 'Microsoft YaHei',
    color: '333333',
    bold: true,
  },
  contentBody: {
    fontSize: 16,
    fontFace: 'Microsoft YaHei',
    color: '444444',
  },
  contentSmall: {
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: '666666',
  },

  // 卡片样式
  cardTitle: {
    fontSize: 18,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    bold: true,
    align: 'center',
  },
  cardContent: {
    fontSize: 14,
    fontFace: 'Microsoft YaHei',
    color: 'FFFFFF',
    align: 'center',
  },

  // 高亮样式
  highlight: {
    fontSize: 28,
    fontFace: 'Microsoft YaHei',
    color: '00B050',
    bold: true,
  },
};

// 形状样式
const SHAPE_STYLES = {
  // 卡片形状
  card: {
    shapeType: 'roundRect',
    radius: 0.1,
  },
  // 圆形装饰
  circle: {
    shapeType: 'ellipse',
  },
  // 矩形
  rect: {
    shapeType: 'rect',
  },
};

module.exports = { LAYOUT, POSITIONS, TEXT_STYLES, SHAPE_STYLES };