# 培训PPT生成器实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个Python脚本，自动生成25页活泼风格的工业防火墙自动化测试平台培训PPT

**Architecture:** 使用python-pptx库，采用模块化设计：颜色配置 → 辅助函数 → 各部分页面生成 → 主函数整合

**Tech Stack:** Python 3.x, python-pptx, 无需测试框架（视觉验证）

---

## 文件结构

```
D:\自动化测试\SFW_CONFIG\djangoProject\
├── generate_training_ppt_v2.py    # 主脚本文件（创建）
└── docs\superpowers\plans\       # 本计划文件
```

---

## Task 1: 创建脚本骨架和颜色配置

**Files:**
- Create: `D:\自动化测试\SFW_CONFIG\djangoProject\generate_training_ppt_v2.py`

- [ ] **Step 1: 创建脚本文件并添加文件头和导入**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工业防火墙自动化测试平台培训PPT生成器
版本: 2.0
风格: 活泼现代，彩色卡片，图标丰富
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

# ==================== 配置 ====================
```

- [ ] **Step 2: 添加颜色配置**

```python
# 颜色方案（活泼配色）
COLORS = {
    'primary': RGBColor(0, 112, 192),      # 蓝色 #0070C0 - 专业、可信
    'secondary': RGBColor(0, 176, 80),      # 绿色 #00B050 - 改进、成功
    'accent': RGBColor(255, 102, 0),        # 橙色 #FF6600 - 强调、活力
    'purple': RGBColor(112, 48, 160),       # 紫色 #7030A0 - 创意、特别
    'teal': RGBColor(0, 128, 128),          # 青色 #008080 - 技术、清新
    'dark': RGBColor(51, 51, 51),           # 深灰 - 正文
    'light': RGBColor(242, 242, 242),       # 浅灰 - 背景
    'white': RGBColor(255, 255, 255),       # 白色
    'red': RGBColor(192, 0, 0),             # 红色 - 警告
    'gray': RGBColor(128, 128, 128),        # 灰色 - 改进前数据
}

# PPT尺寸（16:9宽屏）
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)
```

- [ ] **Step 3: 创建Presentation对象初始化**

```python
def create_presentation():
    """创建并配置演示文稿"""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    return prs

# ==================== 辅助函数 ====================
```

- [ ] **Step 4: 验证脚本可运行**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
python -c "from generate_training_ppt_v2 import COLORS, create_presentation; print('OK')"
```
Expected: `OK`

---

## Task 2: 创建基础辅助函数

**Files:**
- Modify: `D:\自动化测试\SFW_CONFIG\djangoProject\generate_training_ppt_v2.py`

- [ ] **Step 1: 添加标题幻灯片函数**

```python
def add_title_slide(prs, title, subtitle=""):
    """添加标题幻灯片（用于封面和章节标题）"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # 空白布局
    
    # 背景色块
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, Inches(2.5), SLIDE_WIDTH, Inches(2.5)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLORS['primary']
    shape.line.fill.background()
    
    # 标题
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(3), Inches(12.333), Inches(1.2))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = COLORS['white']
    p.alignment = PP_ALIGN.CENTER
    
    # 副标题
    if subtitle:
        sub_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.3), Inches(12.333), Inches(0.8))
        tf = sub_box.text_frame
        p = tf.paragraphs[0]
        p.text = subtitle
        p.font.size = Pt(24)
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
    
    # 装饰圆点
    for i, color in enumerate([COLORS['secondary'], COLORS['accent'], COLORS['purple']]):
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(11 + i * 0.6), Inches(0.5 + i * 0.3), Inches(0.5), Inches(0.5)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = color
        circle.line.fill.background()
    
    return slide
```

- [ ] **Step 2: 添加章节标题幻灯片函数**

```python
def add_section_slide(prs, title, icon, color=None):
    """添加章节标题幻灯片"""
    if color is None:
        color = COLORS['secondary']
    
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # 左侧色块
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, Inches(4), Inches(7.5)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    
    # 图标
    icon_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(2), Inches(1.5))
    tf = icon_box.text_frame
    p = tf.paragraphs[0]
    p.text = icon
    p.font.size = Pt(72)
    p.alignment = PP_ALIGN.CENTER
    
    # 标题
    title_box = slide.shapes.add_textbox(Inches(4.5), Inches(2.8), Inches(8), Inches(1.5))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(48)
    p.font.bold = True
    p.font.color.rgb = COLORS['dark']
    
    return slide
```

- [ ] **Step 3: 添加内容幻灯片函数（带标题栏）**

```python
def add_content_slide(prs, title):
    """添加带标题栏的内容幻灯片，返回slide对象"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # 顶部标题栏
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, Inches(1.2)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLORS['primary']
    shape.line.fill.background()
    
    # 标题文字
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.333), Inches(0.8))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = COLORS['white']
    
    return slide
```

- [ ] **Step 4: 添加列表项函数**

```python
def add_list_item(slide, text, y_pos, icon="✓", color=None):
    """添加带图标圆圈的列表项"""
    if color is None:
        color = COLORS['secondary']
    
    # 图标圆圈
    circle = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(0.5), Inches(y_pos + 0.05), Inches(0.35), Inches(0.35)
    )
    circle.fill.solid()
    circle.fill.fore_color.rgb = color
    circle.line.fill.background()
    
    # 图标文字
    icon_box = slide.shapes.add_textbox(Inches(0.5), Inches(y_pos), Inches(0.35), Inches(0.35))
    tf = icon_box.text_frame
    p = tf.paragraphs[0]
    p.text = icon
    p.font.size = Pt(14)
    p.font.color.rgb = COLORS['white']
    p.alignment = PP_ALIGN.CENTER
    
    # 文本
    text_box = slide.shapes.add_textbox(Inches(1.0), Inches(y_pos), Inches(11.5), Inches(0.5))
    tf = text_box.text_frame
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(20)
    p.font.color.rgb = COLORS['dark']
```

- [ ] **Step 5: 验证函数可调用**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
python -c "from generate_training_ppt_v2 import add_title_slide, add_section_slide, add_content_slide, add_list_item; print('Functions OK')"
```
Expected: `Functions OK`

---

## Task 3: 创建表格和卡片辅助函数

**Files:**
- Modify: `D:\自动化测试\SFW_CONFIG\djangoProject\generate_training_ppt_v2.py`

- [ ] **Step 1: 添加表格幻灯片函数**

```python
def add_table_slide(prs, title, headers, rows, title_color=None):
    """添加表格幻灯片"""
    if title_color is None:
        title_color = COLORS['primary']
    
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # 顶部标题栏
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, Inches(1.2)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = title_color
    shape.line.fill.background()
    
    # 标题
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.333), Inches(0.8))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = COLORS['white']
    
    # 创建表格
    num_rows = len(rows) + 1
    num_cols = len(headers)
    table = slide.shapes.add_table(
        num_rows, num_cols, Inches(0.5), Inches(1.5), Inches(12.333), Inches(5.5)
    ).table
    
    # 设置表头
    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = COLORS['primary']
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
    
    # 设置数据行
    for row_idx, row_data in enumerate(rows):
        for col_idx, cell_text in enumerate(row_data):
            cell = table.cell(row_idx + 1, col_idx)
            cell.text = str(cell_text)
            if row_idx % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLORS['light']
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(14)
            p.font.color.rgb = COLORS['dark']
    
    return slide
```

- [ ] **Step 2: 添加功能卡片幻灯片函数**

```python
def add_feature_cards_slide(prs, title, features, title_color=None):
    """添加功能卡片幻灯片（4个卡片）"""
    if title_color is None:
        title_color = COLORS['primary']
    
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # 顶部标题栏
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, Inches(1.2)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = title_color
    shape.line.fill.background()
    
    # 标题
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.333), Inches(0.8))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = COLORS['white']
    
    # 功能卡片
    colors = [COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['purple']]
    card_width = 2.8
    card_height = 2.2
    start_x = 0.5
    start_y = 1.6
    
    for i, feature in enumerate(features[:4]):
        x = start_x + (i % 4) * (card_width + 0.3)
        y = start_y + (i // 4) * (card_height + 0.3)
        
        # 卡片背景
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(card_width), Inches(card_height)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = colors[i % 4]
        card.line.fill.background()
        
        # 图标
        icon_box = slide.shapes.add_textbox(Inches(x + 0.1), Inches(y + 0.2), Inches(card_width - 0.2), Inches(0.6))
        tf = icon_box.text_frame
        p = tf.paragraphs[0]
        p.text = feature.get('icon', '📦')
        p.font.size = Pt(32)
        p.alignment = PP_ALIGN.CENTER
        
        # 标题
        feat_title = slide.shapes.add_textbox(Inches(x + 0.1), Inches(y + 0.9), Inches(card_width - 0.2), Inches(0.5))
        tf = feat_title.text_frame
        p = tf.paragraphs[0]
        p.text = feature['title']
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
        
        # 描述
        desc_box = slide.shapes.add_textbox(Inches(x + 0.1), Inches(y + 1.4), Inches(card_width - 0.2), Inches(0.7))
        tf = desc_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = feature['desc']
        p.font.size = Pt(12)
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
    
    return slide
```

- [ ] **Step 3: 添加两列对比幻灯片函数**

```python
def add_comparison_slide(prs, title, left_title, left_items, right_title, right_items):
    """添加两列对比幻灯片"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # 顶部标题栏
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, Inches(1.2)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLORS['primary']
    shape.line.fill.background()
    
    # 标题
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.333), Inches(0.8))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = COLORS['white']
    
    # 左列标题
    left_header = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(1.5), Inches(5.5), Inches(0.6)
    )
    left_header.fill.solid()
    left_header.fill.fore_color.rgb = COLORS['gray']
    left_header.line.fill.background()
    
    left_title_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.55), Inches(5.5), Inches(0.5))
    tf = left_title_box.text_frame
    p = tf.paragraphs[0]
    p.text = left_title
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = COLORS['white']
    p.alignment = PP_ALIGN.CENTER
    
    # 左列内容
    y_pos = 2.3
    for item in left_items:
        text_box = slide.shapes.add_textbox(Inches(0.7), Inches(y_pos), Inches(5.3), Inches(0.45))
        tf = text_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"• {item}"
        p.font.size = Pt(18)
        p.font.color.rgb = COLORS['dark']
        y_pos += 0.5
    
    # 右列标题
    right_header = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7), Inches(1.5), Inches(5.5), Inches(0.6)
    )
    right_header.fill.solid()
    right_header.fill.fore_color.rgb = COLORS['secondary']
    right_header.line.fill.background()
    
    right_title_box = slide.shapes.add_textbox(Inches(7), Inches(1.55), Inches(5.5), Inches(0.5))
    tf = right_title_box.text_frame
    p = tf.paragraphs[0]
    p.text = right_title
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = COLORS['white']
    p.alignment = PP_ALIGN.CENTER
    
    # 右列内容
    y_pos = 2.3
    for item in right_items:
        text_box = slide.shapes.add_textbox(Inches(7.2), Inches(y_pos), Inches(5.3), Inches(0.45))
        tf = text_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"• {item}"
        p.font.size = Pt(18)
        p.font.color.rgb = COLORS['dark']
        y_pos += 0.5
    
    return slide
```

- [ ] **Step 4: 验证新函数**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
python -c "from generate_training_ppt_v2 import add_table_slide, add_feature_cards_slide, add_comparison_slide; print('OK')"
```
Expected: `OK`

---

## Task 4: 添加截图占位符函数

**Files:**
- Modify: `D:\自动化测试\SFW_CONFIG\djangoProject\generate_training_ppt_v2.py`

- [ ] **Step 1: 添加截图占位符函数**

```python
def add_screenshot_placeholder(slide, x, y, width, height, text):
    """添加截图占位框"""
    # 占位框
    placeholder = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(width), Inches(height)
    )
    placeholder.fill.solid()
    placeholder.fill.fore_color.rgb = COLORS['light']
    placeholder.line.color.rgb = COLORS['primary']
    placeholder.line.width = Pt(2)
    
    # 提示文字
    text_box = slide.shapes.add_textbox(Inches(x), Inches(y + height/2 - 0.3), Inches(width), Inches(0.6))
    tf = text_box.text_frame
    p = tf.paragraphs[0]
    p.text = f"[截图: {text}]"
    p.font.size = Pt(16)
    p.font.color.rgb = COLORS['primary']
    p.alignment = PP_ALIGN.CENTER
```

- [ ] **Step 2: 验证函数**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
python -c "from generate_training_ppt_v2 import add_screenshot_placeholder; print('OK')"
```
Expected: `OK`

---

## Task 5: 生成第一部分 - 开场（5页）

**Files:**
- Modify: `D:\自动化测试\SFW_CONFIG\djangoProject\generate_training_ppt_v2.py`

- [ ] **Step 1: 添加第一部分生成函数**

```python
# ==================== 第一部分：开场（5页） ====================

def generate_part1_opening(prs):
    """生成开场部分（5页）"""
    
    # 页面1 - 封面
    add_title_slide(prs, "工业防火墙自动化测试平台", "让测试变得简单高效")
    
    # 页面2 - 痛点故事
    slide = add_content_slide(prs, "一个测试工程师的困境")
    problems = [
        ("不同测试环境切换电脑操作麻烦", "1", COLORS['primary']),
        ("需要多个工具分散使用", "2", COLORS['secondary']),
        ("工控协议测试复杂易出错", "3", COLORS['accent']),
        ("测试结果手工记录难追溯", "4", COLORS['purple']),
    ]
    y = 1.5
    for text, num, color in problems:
        add_list_item(slide, text, y, num, color)
        y += 0.7
    
    # 页面3 - 解决方案
    features = [
        {"icon": "🌐", "title": "Web统一管理", "desc": "浏览器操作\n无需切换设备"},
        {"icon": "🤖", "title": "自动化测试", "desc": "一键执行\n自动记录结果"},
        {"icon": "🏭", "title": "工控协议", "desc": "30+协议支持\n覆盖主流场景"},
        {"icon": "👥", "title": "并发协作", "desc": "3组独立环境\n互不干扰"},
    ]
    add_feature_cards_slide(prs, "我们带来了解决方案", features)
    
    # 页面4 - 效益数据
    slide = add_content_slide(prs, "实际效益")
    
    # 创建效益数据卡片
    benefits = [
        ("配置时间", "10分钟 → 7分钟", COLORS['secondary']),
        ("测试效率", "提升 30%", COLORS['secondary']),
        ("错误率", "降低 20%", COLORS['secondary']),
    ]
    y = 2.0
    for label, value, color in benefits:
        # 标签
        label_box = slide.shapes.add_textbox(Inches(1), Inches(y), Inches(3), Inches(0.5))
        tf = label_box.text_frame
        p = tf.paragraphs[0]
        p.text = label
        p.font.size = Pt(24)
        p.font.color.rgb = COLORS['dark']
        
        # 数值
        value_box = slide.shapes.add_textbox(Inches(4.5), Inches(y), Inches(4), Inches(0.5))
        tf = value_box.text_frame
        p = tf.paragraphs[0]
        p.text = value
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = color
        y += 1.0
    
    # 页面5 - 培训议程
    slide = add_content_slide(prs, "培训议程")
    agenda = [
        ("项目概述 - 这是什么系统？", "1", COLORS['primary']),
        ("核心功能 - 能做什么测试？", "2", COLORS['secondary']),
        ("操作演示 - 怎么使用系统？", "3", COLORS['accent']),
        ("快速上手 - 如何开始使用？", "4", COLORS['purple']),
    ]
    y = 1.5
    for text, num, color in agenda:
        add_list_item(slide, text, y, num, color)
        y += 0.7
```

- [ ] **Step 2: 验证第一部分函数**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
python -c "from generate_training_ppt_v2 import generate_part1_opening; print('Part1 OK')"
```
Expected: `Part1 OK`

---

## Task 6: 生成第二部分 - 价值展示（8页）

**Files:**
- Modify: `D:\自动化测试\SFW_CONFIG\djangoProject\generate_training_ppt_v2.py`

- [ ] **Step 1: 添加第二部分生成函数**

```python
# ==================== 第二部分：价值展示（8页） ====================

def generate_part2_value(prs):
    """生成价值展示部分（8页）"""
    
    # 页面6 - 章节标题
    add_section_slide(prs, "核心功能亮点", "⚡", COLORS['secondary'])
    
    # 页面7 - 统一管理
    slide = add_comparison_slide(prs, "统一管理，一站式操作",
        "改进前",
        ["不同测试环境切换电脑操作", "需要多个工具分散使用", "工具功能有限"],
        "改进后",
        ["全部在Web界面操作，无需切换", "所有工具集成在Agent上", "新开发多种测试工具，能力增强"]
    )
    
    # 添加底部强调
    emphasize_box = slide.shapes.add_textbox(Inches(0.5), Inches(5.5), Inches(12), Inches(1))
    tf = emphasize_box.text_frame
    p = tf.paragraphs[0]
    p.text = "✅ 集成工具：报文发送、端口扫描、协议测试、日志接收    ✅ 新增工具：DDoS压力测试、工控协议模拟、批量验证"
    p.font.size = Pt(16)
    p.font.color.rgb = COLORS['secondary']
    p.alignment = PP_ALIGN.CENTER
    
    # 页面8 - 自动化测试
    slide = add_content_slide(prs, "自动化测试，效率倍增")
    
    # 流程图
    steps = ["配置", "一键执行", "自动记录", "生成报告"]
    colors = [COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['purple']]
    x = 1.5
    for i, step in enumerate(steps):
        # 圆圈
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(x), Inches(2.5), Inches(1.5), Inches(1.5)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = colors[i]
        circle.line.fill.background()
        
        # 步骤文字
        text_box = slide.shapes.add_textbox(Inches(x), Inches(3), Inches(1.5), Inches(0.5))
        tf = text_box.text_frame
        p = tf.paragraphs[0]
        p.text = step
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
        
        # 箭头（除了最后一个）
        if i < len(steps) - 1:
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW, Inches(x + 1.6), Inches(3.1), Inches(0.8), Inches(0.4)
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = COLORS['dark']
            arrow.line.fill.background()
        
        x += 2.7
    
    # 页面9 - 工控协议
    slide = add_content_slide(prs, "30+工控协议支持")
    
    # 核心协议（大图标）
    core_protocols = [("Modbus", COLORS['primary']), ("S7", COLORS['secondary']), ("GOOSE", COLORS['accent']), ("SV", COLORS['purple'])]
    x = 1.0
    for name, color in core_protocols:
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(x), Inches(1.8), Inches(2), Inches(2)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = color
        circle.line.fill.background()
        
        text_box = slide.shapes.add_textbox(Inches(x), Inches(2.5), Inches(2), Inches(0.6))
        tf = text_box.text_frame
        p = tf.paragraphs[0]
        p.text = name
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
        x += 2.8
    
    # 其他协议（小图标）
    other_protocols = ["EtherCAT", "PROFINET", "DNP3", "BACnet", "OPC", "IEC104"]
    x = 0.8
    for name in other_protocols:
        small = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(4.2), Inches(1.8), Inches(0.6)
        )
        small.fill.solid()
        small.fill.fore_color.rgb = COLORS['teal']
        small.line.fill.background()
        
        text_box = slide.shapes.add_textbox(Inches(x), Inches(4.3), Inches(1.8), Inches(0.5))
        tf = text_box.text_frame
        p = tf.paragraphs[0]
        p.text = name
        p.font.size = Pt(14)
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
        x += 2.0
    
    # 页面10 - 并发协作
    slide = add_content_slide(prs, "多组并发，互不干扰")
    
    # 三组并行示意
    groups = [("A组", COLORS['primary']), ("B组", COLORS['secondary']), ("C组", COLORS['accent'])]
    x = 1.5
    for name, color in groups:
        rect = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(2), Inches(3), Inches(3)
        )
        rect.fill.solid()
        rect.fill.fore_color.rgb = color
        rect.line.fill.background()
        
        text_box = slide.shapes.add_textbox(Inches(x), Inches(3.2), Inches(3), Inches(0.8))
        tf = text_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"{name}\n独立环境"
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
        x += 3.5
    
    # 页面11 - 真实案例
    add_table_slide(prs, "实际应用案例：某防火墙功能验证",
        ["指标", "改进前", "改进后"],
        [
            ["测试时间", "8小时", "6小时"],
            ["人力投入", "4人", "4人"],
            ["问题发现", "20个", "25个"],
        ]
    )
    
    # 页面12 - 用户反馈
    slide = add_content_slide(prs, "用户怎么说")
    
    # 引用卡片
    quotes = [
        ("测试工程师A", "界面直观，上手很快"),
        ("测试工程师B", "工控协议测试方便多了"),
    ]
    y = 2.0
    for name, quote in quotes:
        # 引用框
        quote_box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1), Inches(y), Inches(10), Inches(1.2)
        )
        quote_box.fill.solid()
        quote_box.fill.fore_color.rgb = COLORS['light']
        quote_box.line.color.rgb = COLORS['secondary']
        
        # 引用文字
        text_box = slide.shapes.add_textbox(Inches(1.2), Inches(y + 0.2), Inches(9.6), Inches(0.8))
        tf = text_box.text_frame
        p = tf.paragraphs[0]
        p.text = f'"{quote}" — {name}'
        p.font.size = Pt(20)
        p.font.italic = True
        p.font.color.rgb = COLORS['dark']
        y += 1.8
    
    # 页面13 - 系统架构
    slide = add_content_slide(prs, "简单明了的架构")
    
    # 三层架构
    layers = [
        ("操作者", "浏览器访问", COLORS['primary']),
        ("管理平台", "Django服务器", COLORS['secondary']),
        ("测试设备", "Agent程序", COLORS['accent']),
    ]
    y = 1.8
    for name, desc, color in layers:
        rect = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2), Inches(y), Inches(9), Inches(1.2)
        )
        rect.fill.solid()
        rect.fill.fore_color.rgb = color
        rect.line.fill.background()
        
        text_box = slide.shapes.add_textbox(Inches(2.5), Inches(y + 0.3), Inches(8), Inches(0.8))
        tf = text_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"{name}: {desc}"
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
        
        # 箭头（除了最后一个）
        if y < 4:
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.DOWN_ARROW, Inches(6.2), Inches(y + 1.3), Inches(0.6), Inches(0.5)
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = COLORS['dark']
            arrow.line.fill.background()
        
        y += 1.8
```

- [ ] **Step 2: 验证第二部分函数**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
python -c "from generate_training_ppt_v2 import generate_part2_value; print('Part2 OK')"
```
Expected: `Part2 OK`

---

## Task 7: 生成第三部分 - 演示环节（8页）

**Files:**
- Modify: `D:\自动化测试\SFW_CONFIG\djangoProject\generate_training_ppt_v2.py`

- [ ] **Step 1: 添加第三部分生成函数**

```python
# ==================== 第三部分：演示环节（8页） ====================

def generate_part3_demo(prs):
    """生成演示环节部分（8页）"""
    
    # 页面14 - 章节标题
    add_section_slide(prs, "核心操作演示", "🎬", COLORS['accent'])
    
    # 页面15 - 操作流程总览
    slide = add_content_slide(prs, "从部署到测试，5步搞定")
    
    steps = [
        ("步骤1", "配置环境", "5分钟"),
        ("步骤2", "部署Agent", "2分钟"),
        ("步骤3", "执行测试", "按需"),
        ("步骤4", "验证结果", "实时"),
        ("步骤5", "查看报告", "自动生成"),
    ]
    colors = [COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['purple'], COLORS['teal']]
    x = 0.5
    for i, (step, name, time) in enumerate(steps):
        # 圆圈
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(x), Inches(2.0), Inches(2), Inches(2)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = colors[i]
        circle.line.fill.background()
        
        # 步骤编号
        step_box = slide.shapes.add_textbox(Inches(x), Inches(2.3), Inches(2), Inches(0.5))
        tf = step_box.text_frame
        p = tf.paragraphs[0]
        p.text = step
        p.font.size = Pt(16)
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
        
        # 步骤名称
        name_box = slide.shapes.add_textbox(Inches(x), Inches(2.8), Inches(2), Inches(0.5))
        tf = name_box.text_frame
        p = tf.paragraphs[0]
        p.text = name
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
        
        # 时间标注
        time_box = slide.shapes.add_textbox(Inches(x), Inches(4.3), Inches(2), Inches(0.4))
        tf = time_box.text_frame
        p = tf.paragraphs[0]
        p.text = time
        p.font.size = Pt(14)
        p.font.color.rgb = COLORS['dark']
        p.alignment = PP_ALIGN.CENTER
        
        # 箭头
        if i < len(steps) - 1:
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.1), Inches(2.8), Inches(0.4), Inches(0.3)
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = COLORS['gray']
            arrow.line.fill.background()
        
        x += 2.5
    
    # 页面16 - 测试环境管理
    slide = add_content_slide(prs, "步骤1：配置测试环境")
    add_screenshot_placeholder(slide, 0.5, 1.5, 7, 4.5, "测试环境列表页面")
    
    # 操作要点
    tips_box = slide.shapes.add_textbox(Inches(8), Inches(2), Inches(4.5), Inches(3))
    tf = tips_box.text_frame
    tips = ["设备名称", "IP地址", "SSH账号", "系统类型"]
    for i, tip in enumerate(tips):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"✓ {tip}"
        p.font.size = Pt(18)
        p.font.color.rgb = COLORS['secondary']
    
    # 提示
    hint_box = slide.shapes.add_textbox(Inches(8), Inches(5.5), Inches(4.5), Inches(0.5))
    tf = hint_box.text_frame
    p = tf.paragraphs[0]
    p.text = "首次配置后，后续无需重复"
    p.font.size = Pt(14)
    p.font.italic = True
    p.font.color.rgb = COLORS['gray']
    
    # 页面17 - Agent同步
    slide = add_content_slide(prs, "步骤2：一键部署Agent")
    add_screenshot_placeholder(slide, 0.5, 1.5, 7, 4.5, "Agent同步页面")
    
    tips_box = slide.shapes.add_textbox(Inches(8), Inches(2), Inches(4.5), Inches(3))
    tf = tips_box.text_frame
    tips = ["同步按钮", "状态指示", "启动按钮"]
    for i, tip in enumerate(tips):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"✓ {tip}"
        p.font.size = Pt(18)
        p.font.color.rgb = COLORS['secondary']
    
    hint_box = slide.shapes.add_textbox(Inches(8), Inches(5.5), Inches(4.5), Inches(0.5))
    tf = hint_box.text_frame
    p = tf.paragraphs[0]
    p.text = "一键部署，自动上传"
    p.font.size = Pt(14)
    p.font.italic = True
    p.font.color.rgb = COLORS['gray']
    
    # 页面18 - 报文发送
    slide = add_content_slide(prs, "步骤3：发送测试报文")
    add_screenshot_placeholder(slide, 0.5, 1.5, 7, 4.5, "报文发送配置界面")
    
    tips_box = slide.shapes.add_textbox(Inches(8), Inches(2), Inches(4.5), Inches(3))
    tf = tips_box.text_frame
    tips = ["Agent选择", "协议选择", "参数配置", "发送按钮"]
    for i, tip in enumerate(tips):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"✓ {tip}"
        p.font.size = Pt(18)
        p.font.color.rgb = COLORS['secondary']
    
    # 页面19 - 工控协议
    slide = add_content_slide(prs, "工控协议测试")
    add_screenshot_placeholder(slide, 0.5, 1.5, 5.5, 4.5, "Modbus客户端配置")
    add_screenshot_placeholder(slide, 7, 1.5, 5.5, 4.5, "Modbus服务器状态")
    
    # 页面20 - DDoS测试流程
    slide = add_content_slide(prs, "完整案例：DDoS压力测试")
    
    # 四宫格
    ddos_steps = [
        ("1. 配置攻击参数", "协议、端口、次数"),
        ("2. 点击开始发送", "实时发送报文"),
        ("3. 查看发送统计", "速率、总数"),
        ("4. 查看防火墙告警", "Syslog日志"),
    ]
    positions = [(0.5, 1.5), (6.5, 1.5), (0.5, 4.2), (6.5, 4.2)]
    
    for (title, desc), (x, y) in zip(ddos_steps, positions):
        box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(5.5), Inches(2.3)
        )
        box.fill.solid()
        box.fill.fore_color.rgb = COLORS['light']
        box.line.color.rgb = COLORS['accent']
        
        text_box = slide.shapes.add_textbox(Inches(x + 0.2), Inches(y + 0.5), Inches(5.1), Inches(1.5))
        tf = text_box.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = COLORS['accent']
        p = tf.add_paragraph()
        p.text = desc
        p.font.size = Pt(14)
        p.font.color.rgb = COLORS['dark']
    
    # 警告
    warning_box = slide.shapes.add_textbox(Inches(0.5), Inches(6.8), Inches(12), Inches(0.5))
    tf = warning_box.text_frame
    p = tf.paragraphs[0]
    p.text = "⚠️ DDoS测试仅限授权测试环境，禁止对生产系统测试！"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLORS['red']
    p.alignment = PP_ALIGN.CENTER
    
    # 页面21 - 结果验证
    slide = add_content_slide(prs, "步骤4-5：验证与查看")
    add_screenshot_placeholder(slide, 0.5, 1.5, 7, 4.5, "Syslog日志接收页面")
    
    tips_box = slide.shapes.add_textbox(Inches(8), Inches(2), Inches(4.5), Inches(3))
    tf = tips_box.text_frame
    tips = ["日志过滤", "关键词搜索", "时间筛选"]
    for i, tip in enumerate(tips):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"✓ {tip}"
        p.font.size = Pt(18)
        p.font.color.rgb = COLORS['secondary']
    
    hint_box = slide.shapes.add_textbox(Inches(0.5), Inches(6.3), Inches(6), Inches(0.5))
    tf = hint_box.text_frame
    p = tf.paragraphs[0]
    p.text = "所有测试过程自动记录，可追溯"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLORS['secondary']
```

- [ ] **Step 2: 验证第三部分函数**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
python -c "from generate_training_ppt_v2 import generate_part3_demo; print('Part3 OK')"
```
Expected: `Part3 OK`

---

## Task 8: 生成第四部分 - 收尾（4页）

**Files:**
- Modify: `D:\自动化测试\SFW_CONFIG\djangoProject\generate_training_ppt_v2.py`

- [ ] **Step 1: 添加第四部分生成函数**

```python
# ==================== 第四部分：收尾（4页） ====================

def generate_part4_closing(prs):
    """生成收尾部分（4页）"""
    
    # 页面22 - 章节标题
    add_section_slide(prs, "快速上手", "🚀", COLORS['purple'])
    
    # 页面23 - 使用门槛
    slide = add_content_slide(prs, "使用门槛很低")
    
    requirements = [
        ("🌐", "浏览器", "Chrome浏览器", "兼容性最佳"),
        ("🔐", "权限", "测试设备SSH账号", "用于Agent部署"),
        ("💻", "测试设备", "Windows 7+ 或 Linux", "Agent运行环境"),
        ("📚", "学习成本", "约30分钟熟悉", "操作简单直观"),
    ]
    x = 0.5
    for icon, title, req, desc in requirements:
        # 卡片
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(1.8), Inches(2.8), Inches(3)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = COLORS['light']
        card.line.color.rgb = COLORS['primary']
        
        # 图标
        icon_box = slide.shapes.add_textbox(Inches(x), Inches(2.0), Inches(2.8), Inches(0.6))
        tf = icon_box.text_frame
        p = tf.paragraphs[0]
        p.text = icon
        p.font.size = Pt(32)
        p.alignment = PP_ALIGN.CENTER
        
        # 标题
        title_box = slide.shapes.add_textbox(Inches(x), Inches(2.6), Inches(2.8), Inches(0.5))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = COLORS['primary']
        p.alignment = PP_ALIGN.CENTER
        
        # 要求
        req_box = slide.shapes.add_textbox(Inches(x), Inches(3.2), Inches(2.8), Inches(0.5))
        tf = req_box.text_frame
        p = tf.paragraphs[0]
        p.text = req
        p.font.size = Pt(16)
        p.font.color.rgb = COLORS['dark']
        p.alignment = PP_ALIGN.CENTER
        
        # 描述
        desc_box = slide.shapes.add_textbox(Inches(x), Inches(3.7), Inches(2.8), Inches(0.5))
        tf = desc_box.text_frame
        p = tf.paragraphs[0]
        p.text = desc
        p.font.size = Pt(12)
        p.font.color.rgb = COLORS['gray']
        p.alignment = PP_ALIGN.CENTER
        
        x += 3.2
    
    # 底部强调
    emphasize_box = slide.shapes.add_textbox(Inches(0.5), Inches(5.5), Inches(12), Inches(0.8))
    tf = emphasize_box.text_frame
    p = tf.paragraphs[0]
    p.text = "无需安装客户端，打开浏览器即可使用"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = COLORS['secondary']
    p.alignment = PP_ALIGN.CENTER
    
    # 页面24 - 下一步行动
    slide = add_content_slide(prs, "开始你的第一次测试")
    
    actions = [
        ("1", "获取系统访问账号", "联系管理员"),
        ("2", "完成首次环境配置", "参考操作手册"),
        ("3", "尝试第一个测试任务", "建议从报文发送开始"),
        ("4", "加入技术支持群", "遇到问题随时问"),
    ]
    colors = [COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['purple']]
    y = 1.8
    for i, (num, action, hint) in enumerate(actions):
        # 数字圆圈
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(0.8), Inches(y), Inches(0.6), Inches(0.6)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = colors[i]
        circle.line.fill.background()
        
        num_box = slide.shapes.add_textbox(Inches(0.8), Inches(y + 0.1), Inches(0.6), Inches(0.5))
        tf = num_box.text_frame
        p = tf.paragraphs[0]
        p.text = num
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = COLORS['white']
        p.alignment = PP_ALIGN.CENTER
        
        # 行动项
        action_box = slide.shapes.add_textbox(Inches(1.6), Inches(y), Inches(8), Inches(0.5))
        tf = action_box.text_frame
        p = tf.paragraphs[0]
        p.text = action
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = COLORS['dark']
        
        # 提示
        hint_box = slide.shapes.add_textbox(Inches(1.6), Inches(y + 0.5), Inches(8), Inches(0.4))
        tf = hint_box.text_frame
        p = tf.paragraphs[0]
        p.text = hint
        p.font.size = Pt(14)
        p.font.color.rgb = COLORS['gray']
        
        y += 1.2
    
    # 页面25 - 结束页
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # 背景
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, Inches(7.5)
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLORS['primary']
    bg.line.fill.background()
    
    # 主标题
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.8), Inches(12.333), Inches(1.2))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = "感谢聆听"
    p.font.size = Pt(56)
    p.font.bold = True
    p.font.color.rgb = COLORS['white']
    p.alignment = PP_ALIGN.CENTER
    
    # 副标题
    sub_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.2), Inches(12.333), Inches(0.8))
    tf = sub_box.text_frame
    p = tf.paragraphs[0]
    p.text = "如有疑问，欢迎随时提问"
    p.font.size = Pt(28)
    p.font.color.rgb = COLORS['white']
    p.alignment = PP_ALIGN.CENTER
    
    # 装饰圆点
    for i, color in enumerate([COLORS['secondary'], COLORS['accent'], COLORS['purple'], COLORS['teal']]):
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(5 + i * 1), Inches(5.5), Inches(0.6), Inches(0.6)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = color
        circle.line.fill.background()
```

- [ ] **Step 2: 验证第四部分函数**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
python -c "from generate_training_ppt_v2 import generate_part4_closing; print('Part4 OK')"
```
Expected: `Part4 OK`

---

## Task 9: 整合主函数并生成PPT

**Files:**
- Modify: `D:\自动化测试\SFW_CONFIG\djangoProject\generate_training_ppt_v2.py`

- [ ] **Step 1: 添加主函数**

```python
# ==================== 主函数 ====================

def main():
    """主函数：生成完整PPT"""
    print("开始生成培训PPT...")
    
    # 创建演示文稿
    prs = create_presentation()
    
    # 生成各部分
    print("生成第一部分：开场（5页）...")
    generate_part1_opening(prs)
    
    print("生成第二部分：价值展示（8页）...")
    generate_part2_value(prs)
    
    print("生成第三部分：演示环节（8页）...")
    generate_part3_demo(prs)
    
    print("生成第四部分：收尾（4页）...")
    generate_part4_closing(prs)
    
    # 保存文件
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "培训PPT_工业防火墙自动化测试平台.pptx")
    prs.save(output_path)
    
    print(f"PPT已生成: {output_path}")
    print(f"共 {len(prs.slides)} 页幻灯片")
    
    return output_path


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行脚本生成PPT**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
python generate_training_ppt_v2.py
```
Expected: 
```
开始生成培训PPT...
生成第一部分：开场（5页）...
生成第二部分：价值展示（8页）...
生成第三部分：演示环节（8页）...
生成第四部分：收尾（4页）...
PPT已生成: D:\自动化测试\SFW_CONFIG\djangoProject\培训PPT_工业防火墙自动化测试平台.pptx
共 25 页幻灯片
```

- [ ] **Step 3: 验证PPT文件已生成**

```bash
ls -la "D:\自动化测试\SFW_CONFIG\djangoProject\培训PPT_工业防火墙自动化测试平台.pptx"
```
Expected: 文件存在且大小合理（约100-200KB）

---

## Task 10: 提交代码

**Files:**
- Modify: `D:\自动化测试\SFW_CONFIG\djangoProject\generate_training_ppt_v2.py`

- [ ] **Step 1: 添加代码到Git暂存区**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
git add generate_training_ppt_v2.py
```

- [ ] **Step 2: 提交代码**

```bash
cd "D:\自动化测试\SFW_CONFIG\djangoProject"
git commit -m "feat: add training PPT generator v2 with colorful modern style"
```
Expected: 提交成功

---

## 完成检查清单

- [ ] PPT包含25页
- [ ] 开场部分（5页）：封面、痛点、方案、效益、议程
- [ ] 价值展示（8页）：章节标题、四大亮点、案例、架构
- [ ] 演示环节（8页）：章节标题、流程、页面演示
- [ ] 收尾部分（4页）：章节标题、门槛、行动、结束页
- [ ] 配色符合设计规范（蓝、绿、橙、紫、青）
- [ ] 截图占位符已预留
- [ ] DDoS警告已添加
- [ ] 代码已提交到Git