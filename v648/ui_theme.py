# -*- coding: utf-8 -*-
"""v648 汉化工具界面样式 —— Premium Minimal / 浅色中性。

设计原则（与 GameView Pro 的 DESIGN.md 一致）：
  - 结构先于装饰：用对齐与留白建立层级，不用组底板、角标、状态胶囊。
  - 单一低饱和强调色只用于主操作与焦点；中性灰承载大面积表面。
  - 统一组件状态机 normal -> hover -> active，另有 focus / disabled。
  - 所有视觉值集中在此，界面代码不写死颜色与尺寸。

所有值以十六进制字符串提供，便于 tkinter 直接使用。
"""
from typing import Dict

# -- 表面 ------------------------------------------------------------------
SURFACE: str = '#FAFAFA'       # 窗口底色（近白中性灰）
SURFACE_ALT: str = '#FFFFFF'   # 抬升面（日志/输入区）
BORDER: str = '#E6E7E9'        # 常规描边
BORDER_STRONG: str = '#D5D7DA' # 强调描边/焦点

# -- 文本 ------------------------------------------------------------------
TEXT: str = '#23272B'          # 主信息
TEXT_2: str = '#5C636A'        # 次级信息
TEXT_DIM: str = '#8A9096'      # 标签/辅助（保持可读对比）

# -- 强调与语义（低饱和）----------------------------------------------------
ACCENT: str = '#5B6E7A'        # 单一低饱和灰蓝强调色
ACCENT_HOVER: str = '#4C5E69'
ACCENT_ACTIVE: str = '#3F4F58'
ACCENT_SOFT: str = '#EDF0F2'   # 极淡强调底（hover/focus）
OK: str = '#4F7A5B'            # 成功
WARN: str = '#9A7A3F'          # 警告
ERROR: str = '#A65353'         # 错误

# -- 组件状态 --------------------------------------------------------------
BTN_BG: str = SURFACE_ALT
BTN_BG_HOVER: str = '#F0F2F4'
BTN_BG_ACTIVE: str = '#E7EAEC'
BTN_DISABLED_TEXT: str = '#AEB3B8'

# -- 字体 ------------------------------------------------------------------
FONT_UI: str = 'Microsoft YaHei UI'
FONT_FALLBACK: str = 'Microsoft YaHei'
FONT_MONO: str = 'Consolas'
FS: Dict[str, int] = {
    'brand': 17,      # 品牌标题
    'subtitle': 10,   # 副标题
    'section': 10,    # 分区标题（大写感/加粗）
    'body': 11,       # 正文
    'status': 11,     # 状态行
    'log': 10,        # 日志
    'button': 11,     # 按钮
}

# -- 间距 / 尺寸 -----------------------------------------------------------
SP: Dict[str, int] = {'xs': 4, 'sm': 8, 'md': 14, 'lg': 22, 'xl': 28}
WIN_W: int = 760
WIN_H: int = 600
MIN_W: int = 640
MIN_H: int = 500
PAD_X: int = 26               # 左右留白
HEADER_H: int = 84            # 顶部标题区高度
STATUS_ROW_H: int = 40        # 状态行高度
BTN_H: int = 38               # 主按钮高度
TOOL_BTN_PADX: int = 12
TOOL_BTN_PADY: int = 6

# 状态语义色映射
STATUS_COLOR: Dict[str, str] = {
    'ok': OK, 'warn': WARN, 'error': ERROR, 'info': TEXT_2, 'idle': TEXT_DIM,
}

__all__ = [name for name in globals() if not name.startswith('_')]
