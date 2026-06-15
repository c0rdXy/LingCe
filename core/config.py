#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 系统常量和设置
"""

import tkinter as tk
from pathlib import Path

# ---------------------------------------------------------------------------
# 跨平台字体自动检测
# ---------------------------------------------------------------------------
_FONT_CANDIDATES = [
    "Microsoft YaHei",
    "微软雅黑",
    "PingFang SC",
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    "SimHei",
    "Arial Unicode MS",
]

_detected_font = None


def _detect_system_font() -> str:
    """检测系统中可用的中文字体"""
    global _detected_font
    if _detected_font is not None:
        return _detected_font

    try:
        root = tk._default_root or tk.Tk()
        root.withdraw()
        available = set(root.tk.call("font", "families"))
        root.destroy()
    except Exception:
        available = set()

    for name in _FONT_CANDIDATES:
        if name in available:
            _detected_font = name
            return name

    _detected_font = "TkDefaultFont"
    return _detected_font


def get_font(size: int = 10, weight: str = "normal") -> tuple:
    """获取跨平台兼容字体元组"""
    font_name = _detect_system_font()
    if weight == "bold":
        return (font_name, size, "bold")
    return (font_name, size)


# ---------------------------------------------------------------------------
# 主题系统
# ---------------------------------------------------------------------------
THEMES = {
    "light": {
        "bg": "#f0f0f0",
        "bg_secondary": "#ffffff",
        "text": "#343a40",
        "text_secondary": "#6c757d",
        "primary": "#007bff",
        "success": "#28a745",
        "danger": "#dc3545",
        "warning": "#ffc107",
        "info": "#17a2b8",
        "header_bg": "#007bff",
        "header_fg": "#ffffff",
        "card_bg": "#ffffff",
        "card_border": "#dee2e6",
        "answer_bg": "#f8f9fa",
        "correct_fg": "green",
        "wrong_fg": "red",
    },
    "dark": {
        "bg": "#1e1e2e",
        "bg_secondary": "#2d2d3f",
        "text": "#cdd6f4",
        "text_secondary": "#a6adc8",
        "primary": "#89b4fa",
        "success": "#a6e3a1",
        "danger": "#f38ba8",
        "warning": "#f9e2af",
        "info": "#89dceb",
        "header_bg": "#313244",
        "header_fg": "#cdd6f4",
        "card_bg": "#2d2d3f",
        "card_border": "#45475a",
        "answer_bg": "#313244",
        "correct_fg": "#a6e3a1",
        "wrong_fg": "#f38ba8",
    },
}

_current_theme = "light"


def get_theme() -> str:
    """获取当前主题名称。"""
    return _current_theme


def set_theme(theme_name: str):
    """设置当前主题；未知主题会被忽略。"""
    global _current_theme
    if theme_name in THEMES:
        _current_theme = theme_name


def get_theme_colors() -> dict:
    """获取当前主题的颜色配置"""
    return THEMES.get(_current_theme, THEMES["light"])


# ---------------------------------------------------------------------------
# 应用信息
# ---------------------------------------------------------------------------
APP_NAME = "灵测 LingCe"
APP_VERSION = "V0.1.2"
WINDOW_TITLE = f"{APP_NAME} {APP_VERSION}"

# ---------------------------------------------------------------------------
# 窗口设置
# ---------------------------------------------------------------------------
DEFAULT_WINDOW_SIZE = "1100x750"

# ---------------------------------------------------------------------------
# 字体设置
# ---------------------------------------------------------------------------
DEFAULT_FONT = get_font(10)
BOLD_FONT = get_font(10, "bold")
LARGE_FONT = get_font(12)
TITLE_FONT = get_font(14, "bold")

# ---------------------------------------------------------------------------
# 颜色映射
# ---------------------------------------------------------------------------
COLORS = {
    "correct": "green",
    "wrong": "red",
    "primary": "#007bff",
    "secondary": "#6c757d",
    "success": "#28a745",
    "danger": "#dc3545",
    "warning": "#ffc107",
    "info": "#17a2b8",
    "light": "#f8f9fa",
    "dark": "#343a40",
}

# ---------------------------------------------------------------------------
# 题目类型
# ---------------------------------------------------------------------------
QUESTION_TYPES = {
    "all": "全部题型",
    "single": "单选题",
    "multiple": "多选题",
    "judge": "判断题",
    "judgement": "判断题",
    "short": "简答题",
    "fill": "填空题",
    "essay": "简答题",
}

# ---------------------------------------------------------------------------
# 考试设置
# ---------------------------------------------------------------------------
EXAM_CONFIG = {
    "default_time_limit": 90,
    "questions_per_exam": 50,
    "pass_score": 60,
}

# ---------------------------------------------------------------------------
# 文件设置
# ---------------------------------------------------------------------------
FILE_CONFIG = {
    "supported_formats": [("JSON文件", "*.json"), ("所有文件", "*.*")],
    "encoding": "utf-8",
    "question_bank_dir": "question_banks",
    "default_question_bank": "题库.json",
}

QUESTION_BANK_DIR = Path(FILE_CONFIG["question_bank_dir"])
DEFAULT_QUESTION_BANK_PATH = QUESTION_BANK_DIR / FILE_CONFIG["default_question_bank"]

# ---------------------------------------------------------------------------
# UI 布局设置
# ---------------------------------------------------------------------------
LAYOUT = {
    "button_width": 12,
    "button_height": 2,
    "padding": 10,
    "small_padding": 5,
}
