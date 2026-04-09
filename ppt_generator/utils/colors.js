/**
 * 配色方案 - 活泼现代风格
 */

// 主色调
const COLORS = {
  // 基础色
  primary: '0070C0',      // 蓝色 - 专业可信
  secondary: '00B050',    // 绿色 - 改进成功
  accent: 'FF6600',       // 橙色 - 强调活力
  purple: '7030A0',       // 紫色 - 创意特别
  teal: '008080',         // 青色 - 技术清新

  // 状态色
  success: '00B050',
  warning: 'FF9900',
  error: 'FF0000',

  // 灰度
  white: 'FFFFFF',
  black: '000000',
  gray100: 'F5F5F5',
  gray200: 'EEEEEE',
  gray300: 'DDDDDD',
  gray400: 'CCCCCC',
  gray500: '999999',
  gray600: '666666',
  gray700: '444444',
  gray800: '333333',

  // 渐变起点色（用于背景）
  gradientBlue: '1E90FF',
  gradientGreen: '32CD32',
  gradientOrange: 'FF8C00',
  gradientPurple: '9370DB',
};

// 功能色映射
const FUNCTION_COLORS = {
  opening: COLORS.primary,
  value: COLORS.secondary,
  demo: COLORS.accent,
  closing: COLORS.purple,
};

// 卡片配色
const CARD_COLORS = [
  COLORS.primary,
  COLORS.secondary,
  COLORS.accent,
  COLORS.purple,
  COLORS.teal,
];

module.exports = { COLORS, FUNCTION_COLORS, CARD_COLORS };