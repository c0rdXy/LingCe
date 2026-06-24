#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口模块 - 应用程序主界面
"""

import tkinter as tk
import webbrowser
import sys
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any
from core.config import (
    DEFAULT_WINDOW_SIZE, get_font,
    DEFAULT_FONT, BOLD_FONT, TITLE_FONT, COLORS,
    get_theme, set_theme, get_theme_colors, THEMES,
    DEFAULT_QUESTION_BANK_PATH,
)
from services.file_service import FileService
from services.user_data_service import UserDataService
from services.settings_service import SettingsService
from services.exam_db import init_db
from ui.components import show_message_dialog, center_window
from ui.exam_stats import show_exam_stats
from ui.settings_window import show_settings_window
from ui.question_bank_builder_window import show_question_bank_builder_window
from ui.app_icon import apply_app_icon


GITHUB_URL = "https://github.com/c0rdXy/LingCe"
GITHUB_ICON_PATH = Path("assets") / "github-fluidicon.png"


class MainWindow:
    """主窗口类"""

    def __init__(self, root: tk.Tk):
        self.root = root
        init_db()
        self.file_service = FileService()
        self.user_data = UserDataService()
        self.settings_service = SettingsService()
        self.current_mode = None
        self.github_tooltip = None

        # 错题记录
        self.wrong_questions_history = []

        # 回调函数
        self.on_practice_mode = None
        self.on_exam_mode = None

        # 恢复主题
        if self.settings_service.has_settings_file():
            set_theme(self.settings_service.get_app_settings().get("default_theme", "light"))
        else:
            # 兼容旧版本写在用户数据里的主题，新版本统一保存到 settings.json。
            saved_theme = self.user_data.get_theme()
            set_theme(saved_theme)
            self.settings_service.set_runtime_default_theme(saved_theme)

        self.setup_window()
        self.create_main_interface()

        # 尝试自动加载上次题库
    def _try_auto_load(self):
        """自动加载上次打开的题库"""
        from pathlib import Path

        last_file = self.user_data.get_last_file()
        if last_file and Path(last_file).exists():
            if self._load_question_bank_path(last_file):
                return

        for sample_file in (DEFAULT_QUESTION_BANK_PATH, Path("data") / "题库.json"):
            if sample_file.exists():
                self._load_question_bank_path(str(sample_file))
                return

    def _load_question_bank_path(self, file_path: str) -> bool:
        """加载指定题库路径，成功后刷新主界面状态。"""
        try:
            question_bank = self.file_service.load_question_bank(file_path, show_messages=False)
        except Exception:
            return False
        if not question_bank:
            return False
        self._on_question_bank_loaded(self.file_service.current_file_path or file_path)
        return True

    def setup_window(self):
        """设置窗口属性"""
        self.root.title(self.settings_service.get_window_title())
        apply_app_icon(self.root)
        self.root.geometry(DEFAULT_WINDOW_SIZE)
        center_window(self.root, 1100, 750)
        self._apply_theme()

    def _apply_theme(self):
        """应用当前主题到窗口"""
        tc = get_theme_colors()
        self.root.configure(bg=tc["bg"])
        self.DEFAULT_BG_COLOR = tc["bg"]

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=tc["bg"])
        style.configure("TLabel", background=tc["bg"], foreground=tc["text"])
        style.configure("TLabelframe", background=tc["bg"], foreground=tc["text"])
        style.configure("TLabelframe.Label", background=tc["bg"], foreground=tc["text"])
        style.configure("TRadiobutton", background=tc["card_bg"], foreground=tc["text"])
        style.configure("TCheckbutton", background=tc["card_bg"], foreground=tc["text"])
        style.map(
            "TRadiobutton",
            background=[("active", tc["card_bg"]), ("disabled", tc["card_bg"])],
            foreground=[("disabled", tc["text_secondary"])],
        )
        style.map(
            "TCheckbutton",
            background=[("active", tc["card_bg"]), ("disabled", tc["card_bg"])],
            foreground=[("disabled", tc["text_secondary"])],
        )
        style.configure(
            "TButton",
            background=tc["bg_secondary"],
            foreground=tc["text"],
            bordercolor=tc["card_border"],
            lightcolor=tc["bg_secondary"],
            darkcolor=tc["card_border"],
        )
        style.map(
            "TButton",
            background=[("active", tc["card_bg"]), ("disabled", tc["bg_secondary"])],
            foreground=[("disabled", tc["text_secondary"])],
        )
        style.configure(
            "TEntry",
            fieldbackground=tc["bg_secondary"],
            foreground=tc["text"],
            insertcolor=tc["text"],
        )

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
        self._create_github_link(outer, tc)

        main = tk.Frame(outer, bg=bg)
        main.place(relx=0.5, rely=0.45, anchor="center")

        self._create_menu_bar()
        self._create_title(main, tc)
        self._create_bank_info(main, tc)
        self._create_buttons(main, tc)
        self._create_footer(outer, tc)

    def _create_github_link(self, parent, tc):
        try:
            image = tk.PhotoImage(file=str(self._resource_path(GITHUB_ICON_PATH)))
            scale = max(1, round(image.width() / 32))
            self.github_icon_image = image.subsample(scale, scale)
            icon = tk.Label(
                parent,
                image=self.github_icon_image,
                bg=tc["bg"],
                cursor="hand2",
            )
        except tk.TclError:
            icon = tk.Label(
                parent,
                text="GitHub",
                font=get_font(9, "bold"),
                bg=tc["bg"],
                fg=tc["text"],
                cursor="hand2",
            )
        icon.place(relx=1.0, x=-20, y=18, anchor="ne")
        icon.bind("<Button-1>", lambda _event: self._open_github())
        icon.bind("<Enter>", lambda event: self._show_github_tooltip(event, icon, tc))
        icon.bind("<Leave>", lambda _event: self._hide_github_tooltip(icon, tc))

    @staticmethod
    def _resource_path(relative_path: Path) -> Path:
        """返回开发环境或 PyInstaller 环境中的资源路径。"""
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        return base / relative_path

    def _show_github_tooltip(self, event, widget, tc):
        widget.configure(bg=tc["bg_secondary"])
        self._hide_github_tooltip()

        tooltip = tk.Toplevel(self.root)
        tooltip.wm_overrideredirect(True)
        tooltip.configure(bg=tc["card_border"])

        body = tk.Frame(tooltip, bg=tc["card_bg"], padx=12, pady=8)
        body.pack(padx=1, pady=1)
        tk.Label(
            body,
            text="如果这个系统对您有帮助，请为我点个 Star",
            font=get_font(9),
            bg=tc["card_bg"],
            fg=tc["text"],
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            body,
            text=GITHUB_URL,
            font=get_font(8),
            bg=tc["card_bg"],
            fg=tc["primary"],
            anchor="w",
        ).pack(anchor="w", pady=(3, 0))

        tooltip.update_idletasks()
        x = max(0, event.x_root - tooltip.winfo_reqwidth() + 20)
        y = event.y_root + 22
        tooltip.wm_geometry(f"+{x}+{y}")
        self.github_tooltip = tooltip

    def _hide_github_tooltip(self, widget=None, tc=None):
        if widget is not None and tc is not None:
            widget.configure(bg=tc["bg"])
        if self.github_tooltip is not None:
            try:
                self.github_tooltip.destroy()
            except tk.TclError:
                pass
            self.github_tooltip = None

    def _open_github(self):
        """在系统默认浏览器中打开项目仓库。"""
        webbrowser.open_new_tab(GITHUB_URL)

    def _create_menu_bar(self):
        tc = get_theme_colors()
        menubar = tk.Menu(
            self.root,
            bg=tc["bg_secondary"],
            fg=tc["text"],
            activebackground=tc["primary"],
            activeforeground="#ffffff",
        )
        self.root.config(menu=menubar)

        file_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=tc["bg_secondary"],
            fg=tc["text"],
            activebackground=tc["primary"],
            activeforeground="#ffffff",
        )
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="选择题库", command=self.load_question_bank)
        file_menu.add_command(label="生成题库", command=self.show_question_bank_builder)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # 主题菜单
        theme_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=tc["bg_secondary"],
            fg=tc["text"],
            activebackground=tc["primary"],
            activeforeground="#ffffff",
        )
        menubar.add_cascade(label="主题", menu=theme_menu)
        for theme_name in THEMES:
            theme_menu.add_command(
                label="浅色模式" if theme_name == "light" else "深色模式",
                command=lambda t=theme_name: self._switch_theme(t),
            )

        settings_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=tc["bg_secondary"],
            fg=tc["text"],
            activebackground=tc["primary"],
            activeforeground="#ffffff",
        )
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="系统设置", command=self.show_settings)

    def _switch_theme(self, theme_name: str):
        """切换主题"""
        set_theme(theme_name)
        self._save_default_theme(theme_name)
        self._apply_theme()
        self.create_main_interface()
        if self.file_service.question_bank:
            self.update_question_bank_info(self.file_service.question_bank)
            self.enable_function_buttons()

    def _save_default_theme(self, theme_name: str):
        """同步保存默认主题设置。"""
        try:
            settings = self.settings_service.get_settings()
            settings["app"]["default_theme"] = theme_name
            self.settings_service.save_settings(settings)
        except ValueError:
            pass

    def _create_title(self, parent, tc):
        frame = tk.Frame(parent, bg=tc["bg"])
        frame.pack(fill="x", pady=(0, 30))
        tk.Label(frame, text=self.settings_service.get_window_title(), font=TITLE_FONT,
                 bg=tc["bg"], fg=tc["primary"]).pack()
        tk.Label(frame, text=self.settings_service.get_app_subtitle(),
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

        primary_row = tk.Frame(frame, bg=tc["bg"])
        primary_row.pack()

        self.practice_btn = tk.Button(
            primary_row, text="练习模式", font=get_font(11, "bold"), width=18, height=2,
            bg=COLORS["success"], fg="white", command=self.start_practice_mode,
            state="disabled", cursor="hand2",
        )
        self.practice_btn.pack(side="left", padx=12)

        self.exam_btn = tk.Button(
            primary_row, text="考试模式", font=get_font(11, "bold"), width=18, height=2,
            bg=COLORS["primary"], fg="white", command=self.start_exam_mode,
            state="disabled", cursor="hand2",
        )
        self.exam_btn.pack(side="left", padx=12)

        tool_row = tk.Frame(frame, bg=tc["bg"])
        tool_row.pack(pady=(16, 0))

        self.builder_btn = tk.Button(
            tool_row, text="生成题库", font=DEFAULT_FONT, width=15, height=1,
            bg=tc["bg_secondary"], fg=tc["text"], activebackground=tc["card_bg"],
            activeforeground=tc["text"], relief="groove", bd=1,
            command=self.show_question_bank_builder, cursor="hand2",
        )
        self.builder_btn.pack(side="left", padx=10)

        self.wrong_btn = tk.Button(
            tool_row, text="导出错题集", font=DEFAULT_FONT, width=15, height=1,
            bg=tc["bg_secondary"], fg=tc["text"], activebackground=tc["card_bg"],
            activeforeground=tc["text"], relief="groove", bd=1,
            command=self.export_wrong_questions, cursor="hand2",
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
                          ("系统设置", self.show_settings),
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
            self._on_question_bank_loaded(self.file_service.current_file_path or "")

    def show_question_bank_builder(self):
        """打开手工题库创建窗口。"""
        show_question_bank_builder_window(self.root, self._load_generated_question_bank)

    def _load_generated_question_bank(self, file_path: str):
        """加载刚生成的题库。"""
        question_bank = self.file_service.load_question_bank(file_path, show_messages=False)
        if not question_bank:
            show_message_dialog("错误", "生成的题库加载失败", "error")
            return
        self._on_question_bank_loaded(file_path)
        show_message_dialog("成功", "题库已生成并加载", "info")

    def _on_question_bank_loaded(self, file_path: str):
        """题库加载后的统一状态刷新。"""
        self.user_data.set_last_file(file_path)
        self._load_wrong_history_for_current_bank()
        self.update_question_bank_info(self.file_service.question_bank)
        self.enable_function_buttons()

    def update_question_bank_info(self, question_bank):
        file_info = self.file_service.get_file_info()
        if not file_info:
            return

        tc = get_theme_colors()
        self.file_info_label.config(
            text=f"已加载: {file_info['file_name']} ({file_info['question_count']}题)",
            bg=tc["bg"],
            fg=tc["success"],
        )
        self._show_type_distribution(file_info["type_distribution"], tc)
        self.stats_frame.pack(fill="x", padx=15, pady=(0, 10))

    def _show_type_distribution(self, dist: Dict[str, int], tc: dict):
        for w in self.stats_frame.winfo_children():
            w.destroy()

        tk.Label(self.stats_frame, text="题型分布:", font=BOLD_FONT,
                 bg=tc["bg"], fg=tc["text"]).pack(anchor="w")

        container = tk.Frame(self.stats_frame, bg=tc["bg"])
        container.pack(fill="x", pady=5)

        total = sum(dist.values())
        for qtype, count in dist.items():
            name = self.settings_service.get_question_type_name(qtype)
            pct = (count / total * 100) if total > 0 else 0
            f = tk.Frame(container, bg=tc["bg"])
            f.pack(side="left", padx=(0, 20))
            tk.Label(f, text=name, font=DEFAULT_FONT, bg=tc["bg"], fg=tc["text"]).pack()
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
        added_ids = []
        for item in question_ids:
            if isinstance(item, list):
                for qid in item:
                    if qid not in self.wrong_questions_history:
                        self.wrong_questions_history.append(qid)
                    added_ids.append(qid)
            else:
                if item not in self.wrong_questions_history:
                    self.wrong_questions_history.append(item)
                added_ids.append(item)

        # 持久化
        if self.file_service.current_file_path and added_ids:
            self.user_data.add_wrong_questions(
                self.file_service.current_file_path, added_ids
            )

    def _load_wrong_history_for_current_bank(self):
        """从用户数据中恢复当前题库的错题历史。"""
        file_path = self.file_service.current_file_path
        question_bank = self.file_service.question_bank
        if not file_path or not question_bank:
            self.wrong_questions_history = []
            return
        valid_ids = {question.id for question in question_bank.questions}
        self.wrong_questions_history = [
            question_id
            for question_id in self.user_data.get_wrong_history(file_path)
            if question_id in valid_ids
        ]

    def clear_wrong_questions(self):
        """清空当前题库的错题历史。"""
        self.wrong_questions_history = []
        if self.file_service.current_file_path:
            self.user_data.clear_wrong_history(self.file_service.current_file_path)

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

    def show_settings(self):
        """显示系统设置窗口。"""
        show_settings_window(self.root, self.settings_service, self._on_settings_saved)

    def _on_settings_saved(self):
        """设置保存后刷新主界面。"""
        self.settings_service.reload()
        default_theme = self.settings_service.get_app_settings().get("default_theme")
        if default_theme in THEMES:
            set_theme(default_theme)
        self._apply_theme()
        self.create_main_interface()
        if self.file_service.question_bank:
            self.update_question_bank_info(self.file_service.question_bank)
            self.enable_function_buttons()

    def show_help(self):
        app_name = self.settings_service.get_app_name()
        exam = self.settings_service.get_exam_settings()
        rule_lines = self._build_help_exam_rule_lines()
        help_text = f"""
{app_name} 使用说明

═══════════════════════════════════════

1. 题库文件格式
   • 支持标准 JSON 题库
   • 支持题型：单选、多选、判断、填空、简答
   • 首页会优先自动加载上次使用的题库

2. 练习模式
   • 支持全部题目、仅收藏、错题复习和继续上次
   • 可按题型筛选练习，提交后即时反馈
   • 支持收藏、错题记录、清空错题和在线编辑

3. 考试模式
{rule_lines}
   • 限时{exam.get("time_limit", 90)}分钟，自动评分并支持回顾错题

4. 题库生成
   • 手工创建：新增、复制、删除、移动、模板、保存题库
   • AI解析导入：支持 TXT、Markdown、CSV、Word、Excel、PDF
   • AI生成结果会进入编辑器，需人工复核后保存

5. AI功能
   • 支持 API / Coding Plan / 自定义模型接入
   • 可保存多个 Key，并按服务商切换
   • 可用于题目复核、答案解析生成和资料解析导入

6. 快捷键
   • ←/→ 上下题  R 随机题
   • Enter 提交  Space 显示答案

7. 数据与本地运行
   • 练习进度自动保存
   • 错题历史、收藏自动保存
   • 主题、考试规则和 AI 设置保存在本地
   • 除 AI 调用和 GitHub 外链外，核心功能均可本地运行
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

    def _build_help_exam_rule_lines(self) -> str:
        """生成帮助窗口中的考试规则摘要。"""
        lines = []
        for rule in self.settings_service.get_exam_rules():
            count = rule.get("count", 0)
            score = rule.get("score", 0)
            if rule.get("auto_score", True) and score > 0:
                lines.append(f"   • {rule.get('name', rule['type'])}: {count}题 × {score:g}分")
            else:
                lines.append(f"   • {rule.get('name', rule['type'])}: {count}题，需人工评分")
        return "\n".join(lines) or "   • 暂未配置考试题型"

    # ------------------------------------------------------------------ #
    #  导航
    # ------------------------------------------------------------------ #

    def return_to_main(self):
        self.root.title(self.settings_service.get_window_title())
        self.current_mode = None
        self.create_main_interface()

    def get_question_bank(self):
        return self.file_service.question_bank

    def set_callbacks(self, practice_callback=None, exam_callback=None):
        self.on_practice_mode = practice_callback
        self.on_exam_mode = exam_callback
