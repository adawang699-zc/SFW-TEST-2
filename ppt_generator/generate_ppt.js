/**
 * 工业防火墙自动化测试平台培训PPT生成器
 *
 * 使用 PptxGenJS 生成内容丰富、视觉效果好的培训PPT
 *
 * 功能特点:
 * - 渐变背景和装饰形状
 * - 彩色卡片布局
 * - 内置图表支持
 * - 丰富的emoji图标
 * - 左右分栏、多列布局
 *
 * 运行方式: node generate_ppt.js
 * 输出文件: output/培训PPT_工业防火墙自动化测试平台.pptx
 */

const pptxgen = require('pptxgenjs');
const { generatePart1 } = require('./slides/part1_opening');
const { generatePart2 } = require('./slides/part2_value');
const { generatePart3 } = require('./slides/part3_demo');
const { generatePart4 } = require('./slides/part4_closing');

/**
 * 主函数 - 生成完整PPT
 */
async function main() {
  console.log('开始生成培训PPT...\n');

  // 创建PPT实例
  const pptx = new pptxgen();

  // 设置PPT属性
  pptx.layout = 'LAYOUT_16x9';  // 16:9 宽屏
  pptx.title = '工业防火墙自动化测试平台培训';
  pptx.subject = '系统培训演示';
  pptx.author = '自动化测试团队';
  pptx.company = '工业防火墙测试项目组';

  // 定义幻灯片母版（可选）
  pptx.defineSlideMaster({
    title: 'CONTENT_SLIDE',
    background: { color: 'FFFFFF' },
    objects: [
      // 页脚
      { text: { text: '工业防火墙自动化测试平台', options: { x: 0.3, y: 5.2, w: 3, h: 0.3, fontSize: 8, color: '999999' } } },
    ]
  });

  console.log('生成第一部分：开场（5页）...');
  generatePart1(pptx);
  console.log('  ✓ 封面页');
  console.log('  ✓ 痛点故事页');
  console.log('  ✓ 解决方案页');
  console.log('  ✓ 效益数据页');
  console.log('  ✓ 培训议程页');

  console.log('\n生成第二部分：价值展示（8页）...');
  generatePart2(pptx);
  console.log('  ✓ 章节标题页');
  console.log('  ✓ 统一管理详细页');
  console.log('  ✓ 自动化流程页');
  console.log('  ✓ 工控协议墙页');
  console.log('  ✓ 并发协作页');
  console.log('  ✓ 真实案例页');
  console.log('  ✓ 用户反馈页');
  console.log('  ✓ 系统架构页');

  console.log('\n生成第三部分：演示环节（8页）...');
  generatePart3(pptx);
  console.log('  ✓ 章节标题页');
  console.log('  ✓ 操作流程总览页');
  console.log('  ✓ 环境管理演示页');
  console.log('  ✓ Agent部署演示页');
  console.log('  ✓ 报文发送演示页');
  console.log('  ✓ 工控协议演示页');
  console.log('  ✓ DDoS测试流程页');
  console.log('  ✓ 结果验证页');

  console.log('\n生成第四部分：收尾（4页）...');
  generatePart4(pptx);
  console.log('  ✓ 章节标题页');
  console.log('  ✓ 使用门槛页');
  console.log('  ✓ 下一步行动页');
  console.log('  ✓ 结束页');

  // 保存PPT
  const outputPath = './output/培训PPT_工业防火墙自动化测试平台.pptx';

  console.log('\n正在保存PPT文件...');
  await pptx.writeFile({ fileName: outputPath });

  console.log('\n========================================');
  console.log('PPT生成完成!');
  console.log(`文件路径: ${outputPath}`);
  console.log(`总页数: ${pptx.slides.length} 页`);
  console.log('========================================');

  // 打印页面清单
  console.log('\n页面清单:');
  const pageNames = [
    '封面', '痛点故事', '解决方案概览', '效益数据', '培训议程',
    '章节标题-核心功能', '统一管理详细', '自动化流程', '工控协议墙', '并发协作',
    '真实案例', '用户反馈', '系统架构',
    '章节标题-演示', '操作流程总览', '环境管理演示', 'Agent部署演示', '报文发送演示',
    '工控协议演示', 'DDoS测试流程', '结果验证',
    '章节标题-收尾', '使用门槛', '下一步行动', '结束页'
  ];

  pageNames.forEach((name, i) => {
    console.log(`  第${(i + 1).toString().padStart(2, '0')}页: ${name}`);
  });

  return outputPath;
}

// 运行主函数
main().catch(err => {
  console.error('生成PPT时发生错误:', err);
  process.exit(1);
});