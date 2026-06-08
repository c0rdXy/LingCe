#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口模块 - 应用程序主界面
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any
from core.config import (
    WINDOW_TITLE, DEFAULT_WINDOW_SIZE, QUESTION_TYPES, get_font,
    DEFAULT_FONT, BOLD_FONT, TITLE_FONT, COLORS,
    get_theme, set_theme, get_theme_colors, THEMES,
)
from services.file_service import FileService
from services.user_data_service import UserDataService
from services.exam_db import init_db
from ui.components import show_message_dialog, center_window
from ui.exam_stats import show_exam_stats


class MainWindow:
    """主窗口类"""

    def __init__(self, root: tk.Tk):
        self.root = root
        init_db()
        self.file_service = FileService()
        self.user_data = UserDataService()
        self.current_mode = None

        # 错题记录
        self.wrong_questions_history = []

        # 回调函数
        self.on_practice_mode = None
        self.on_exam_mode = None

        # 恢复主题
        set_theme(self.user_data.get_theme())

        self.setup_window()
        self.create_main_interface()

        # 尝试自动加载上次题库
    def _try_auto_load(self):
        """自动加载上次打开的题库"""
        last_file = self.user_data.get_last_file()
        if last_file:
            from pathlib import Path
            if Path(last_file).exists():
                try:
                    self.file_service.load_question_bank(last_file, show_messages=False)
                    self.update_question_bank_info(self.file_service.question_bank)
                    self.enable_function_buttons()
                except Exception:
                    pass

    def setup_window(self):
        """设置窗口属性"""
        self.root.title(WINDOW_TITLE)
        self.root.geometry(DEFAULT_WINDOW_SIZE)
        center_window(self.root, 1100, 750)
        self._apply_theme()

    def _apply_theme(self):
        """应用当前主题到窗口"""
        tc = get_theme_colors()
        self.root.configure(bg=tc["bg"])
        self.DEFAULT_BG_COLOR = tc["bg"]

    # ------------------------------------------------------------------ #
    #  主界面
    # ------------------------------------------------------------------ #

    def create_main_interface(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        tc = get_theme_colors()
        bg = tc["bg"]

        outer = tk.Frame(self.root, bg=bg)
        outer.pack(fill="both", expand=True)

        main = tk.Frame(outer, bg=bg)
        main.place(relx=0.5, rely=0.45, anchor="center")

        self._create_menu_bar()
        self._create_title(main, tc)
        self._create_bank_info(main, tc)
        self._create_buttons(main, tc)
        self._create_footer(outer, tc)

    def _create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="选择题库", command=self.load_question_bank)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # 主题菜单
        theme_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="主题", menu=theme_menu)
        for theme_name in THEMES:
            theme_menu.add_command(
                label="浅色模式" if theme_name == "light" else "深色模式",
                command=lambda t=theme_name: self._switch_theme(t),
            )

    def _switch_theme(self, theme_name: str):
        """切换主题"""
        set_theme(theme_name)
        self.user_data.set_theme(theme_name)
        self._apply_theme()
        self.create_main_interface()
        if self.file_service.question_bank:
            self.update_question_bank_info(self.file_service.question_bank)
            self.enable_function_buttons()

    def _create_title(self, parent, tc):
        frame = tk.Frame(parent, bg=tc["bg"])
        frame.pack(fill="x", pady=(0, 30))
        tk.Label(frame, text=WINDOW_TITLE, font=TITLE_FONT,
                 bg=tc["bg"], fg=tc["primary"]).pack()
        tk.Label(frame, text="通用考试练习平台",
                 font=DEFAULT_FONT, bg=tc["bg"], fg=tc["text_secondary"]).pack(pady=(5, 0))

    def _create_bank_info(self, parent, tc):
        info = tk.LabelFrame(parent, text="题库信息", font=BOLD_FONT,
                             bg=tc["bg"], fg=tc["text"])
        info.pack(fill="x", pady=(0, 20))

        file_frame = tk.Frame(info, bg=tc["bg"])
        file_frame.pack(fill="x", padx=15, pady=10)
        ttk.Button(file_frame, text="选择题库文件",
                   command=self.load_question_bank).pack(side="left")

        self.file_info_label = tk.Label(file_frame, text="未选择题库文件",
                                        font=DEFAULT_FONT, bg=tc["bg"],
                                        fg=tc["text_secondary"])
        self.file_info_label.pack(side="left", padx=(10, 0))

        self.stats_frame = tk.Frame(info, bg=tc["bg"])
        self.stats_frame.pack(fill="x", padx=15, pady=(0, 10))
        self.stats_frame.pack_forget()

    def _create_buttons(self, parent, tc):
        frame = tk.Frame(parent, bg=tc["bg"])
        frame.pack(fill="x", pady=20)

        btns = tk.Frame(frame, bg=tc["bg"])
        btns.pack()

        self.practice_btn = tk.Button(
            btns, text="练习模式", font=BOLD_FONT, width=15, height=2,
            bg=COLORS["success"], fg="white", command=self.start_practice_mode,
            state="disabled",
        )
        self.practice_btn.pack(side="left", padx=10)

        self.exam_btn = tk.Button(
            btns, text="考试模式", font=BOLD_FONT, width=15, height=2,
            bg=COLORS["primary"], fg="white", command=self.start_exam_mode,
            state="disabled",
        )
        self.exam_btn.pack(side="left", padx=10)

        self.wrong_btn = tk.Button(
            btns, text="导出错题集", font=BOLD_FONT, width=15, height=2,
            bg=COLORS["danger"], fg="white", command=self.export_wrong_questions,
        )
        self.wrong_btn.pack(side="left", padx=10)

    def _create_footer(self, parent, tc):
        footer = tk.Frame(parent, bg=tc["header_bg"], height=40)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        btns = tk.Frame(footer, bg=tc["header_bg"])
        btns.pack(expand=True)

        for text, cmd in [("使用说明", self.show_help),
                          ("统计面板", self.show_stats_panel),
                          ("切换主题", self._toggle_theme)]:
            tk.Button(btns, text=text, font=get_font(9),
                      bg=tc["header_bg"], fg=tc["header_fg"],
                      relief="flat", command=cmd, cursor="hand2",
                      ).pack(side="left", padx=15)

    def _toggle_theme(self):
        current = get_theme()
        self._switch_theme("dark" if current == "light" else "light")

    # ------------------------------------------------------------------ #
    #  题库加载
    # ------------------------------------------------------------------ #

    def load_question_bank(self):
        question_bank = self.file_service.load_question_bank()
        if question_bank:
            self.user_data.set_last_file(self.file_service.current_file_path or "")
            self.update_question_bank_info(question_bank)
            self.enable_function_buttons()

    def update_question_bank_info(self, question_bank):
        file_info = self.file_service.get_file_info()
        if not file_info:
            return

        tc = get_theme_colors()
        self.file_info_label.config(
            text=f"已加载: {file_info['file_name']} ({file_info['question_count']}题)",
            fg=tc["success"],
        )
        self._show_type_distribution(file_info["type_distribution"], tc)
        self.stats_frame.pack(fill="x", padx=15, pady=(0, 10))

    def _show_type_distribution(self, dist: Dict[str, int], tc: dict):
        for w in self.stats_frame.winfo_children():
            w.destroy()

        tk.Label(self.stats_frame, text="题型分布:", font=BOLD_FONT,
                 bg=tc["bg"]).pack(anchor="w")

        container = tk.Frame(self.stats_frame, bg=tc["bg"])
        container.pack(fill="x", pady=5)

        total = sum(dist.values())
        for qtype, count in dist.items():
            name = QUESTION_TYPES.get(qtype, qtype)
            pct = (count / total * 100) if total > 0 else 0
            f = tk.Frame(container, bg=tc["bg"])
            f.pack(side="left", padx=(0, 20))
            tk.Label(f, text=name, font=DEFAULT_FONT, bg=tc["bg"]).pack()
            tk.Label(f, text=f"{count}题 ({pct:.1f}%)", font=get_font(9),
                     bg=tc["bg"], fg=tc["primary"]).pack()

    def enable_function_buttons(self):
        self.practice_btn.config(state="normal")
        self.exam_btn.config(state="normal")

    def disable_function_buttons(self):
        self.practice_btn.config(state="disabled")
        self.exam_btn.config(state="disabled")

    # ------------------------------------------------------------------ #
    #  模式启动
    # ------------------------------------------------------------------ #

    def start_practice_mode(self):
        if self.on_practice_mode:
            self.current_mode = "practice"
            self.on_practice_mode(self.file_service.question_bank)

    def start_exam_mode(self):
        if self.on_exam_mode:
            self.current_mode = "exam"
            self.on_exam_mode(self.file_service.question_bank)

    # ------------------------------------------------------------------ #
    #  错题管理
    # ------------------------------------------------------------------ #

    def add_wrong_questions(self, question_ids):
        for item in question_ids:
            if isinstance(item, list):
                for qid in item:
                    if qid not in self.wrong_questions_history:
                        self.wrong_questions_history.append(qid)
            else:
                if item not in self.wrong_questions_history:
                    self.wrong_questions_history.append(item)

        # 持久化
        if self.file_service.current_file_path:
            self.user_data.add_wrong_questions(
                self.file_service.current_file_path, self.wrong_questions_history
            )

    def export_wrong_questions(self):
        if not self.file_service.question_bank:
            show_message_dialog("提示", "请先加载题库文件", "warning")
            return
        if not self.wrong_questions_history:
            show_message_dialog("提示", "请先进行练习或考试，产生错题后再导出", "info")
            return
        self.file_service.export_wrong_questions(
            self.file_service.question_bank, self.wrong_questions_history
        )

    # ------------------------------------------------------------------ #
    #  统计面板
    # ------------------------------------------------------------------ #

    def show_stats_panel(self):
        """显示统计面板（图表）"""
        show_exam_stats(self.root)
        return
    def show_help(self):
        help_text = """
灵测 LingCe 使用说明

═══════════════════════════════════════

1. 题库文件格式
   • 支持JSON格式
   • 题型: 单选/多选/判断/填空/简答

2. 练习模式
   • 按题型筛选练习
   • 实时反馈，错题自动记录
   • 支持收藏、标签

3. 考试模式
   • 20单选(2分) + 20多选(3分) + 4简答
   • 限时90分钟，自动评分

4. 快捷键
   • ←/→ 上下题  R 随机题
   • Enter 提交  Space 显示答案

5. 数据持久化
   • 练习进度自动保存
   • 错题历史、收藏自动保存
   • 主题偏好保存
"""
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("600x500")
        center_window(help_window, 600, 500)
        text_widget = tk.Text(help_window, wrap=tk.WORD, font=DEFAULT_FONT)
        text_widget.pack(fill="both", expand=True, padx=20, pady=20)
        text_widget.insert("1.0", help_text)
        text_widget.config(state="disabled")
        ttk.Button(help_window, text="关闭", command=help_window.destroy).pack(pady=10)

    # ------------------------------------------------------------------ #
    #  导航
    # ------------------------------------------------------------------ #

    def return_to_main(self):
        self.root.title(WINDOW_TITLE)
        self.current_mode = None
        self.create_main_interface()

    def get_question_bank(self):
        return self.file_service.question_bank

    def set_callbacks(self, practice_callback=None, exam_callback=None):
        self.on_practice_mode = practice_callback
        self.on_exam_mode = exam_callback
