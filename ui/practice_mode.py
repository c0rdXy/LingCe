#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
练习模式界面模块
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, Dict, Any, Callable
from core.config import DEFAULT_FONT, BOLD_FONT, COLORS, QUESTION_TYPES, get_theme_colors
from core.models import QuestionBank, Question
from core.utils import format_judge_answer
from services.question_service import QuestionService
from services.settings_service import SettingsService
from ui.components import QuestionDisplay, show_message_dialog, center_window
from ui.ai_review_window import show_ai_review_window
from ui.widgets import get_question_type_name
from services.user_data_service import UserDataService
from ui.edit_functions import create_edit_interface, update_answer_format_hint, save_edit_changes, save_question_bank_to_file


class PracticeModeWindow:
    """练习模式窗口类"""
    
    def __init__(self, root: tk.Tk, question_bank: QuestionBank):
        self.root = root
        self.question_service = QuestionService()
        self.question_service.set_question_bank(question_bank)
        self.settings_service = SettingsService()
        
        # 界面组件
        self.question_display = None
        self.current_question_frame = None
        self.answer_frame = None
        
        # 编辑相关
        self.is_editing = False
        self.edit_window = None
        
        # 回调函数
        self.on_return_to_main = None
        self.on_wrong_questions = None  # 错题记录回调
        
        # 持久化 & 收藏
        self.user_data = UserDataService()
        self.file_path = question_bank.file_path or ""
        self._is_fav = False
        self._collected_only = False  # 是否只练习收藏题目
        self._practice_range = "all"
        self._selected_question_type = "all"
        self.range_var = tk.StringVar(value=self._practice_range)
        self.ai_histories: Dict[int, list] = {}

        self.create_practice_interface()
        self.bind_keyboard_shortcuts()
        self._start_initial_practice_session()
    
    def create_practice_interface(self):
        """创建练习界面"""
        tc = get_theme_colors()
        # 设置窗口标题
        self.root.title(self.settings_service.get_window_title("练习模式"))
        self.root.configure(bg=tc["bg"])
        
        # 清空窗口
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 主容器
        main_frame = tk.Frame(self.root, bg=tc["bg"])
        main_frame.pack(fill='both', expand=True)

        # 右侧面板 - 固定宽度，先 pack 确保不被挤压
        right_frame = tk.Frame(main_frame, width=280, bg=tc["bg"])
        right_frame.pack(side='right', fill='y', padx=(0, 10), pady=10)
        right_frame.pack_propagate(False)

        self.create_range_area(right_frame)
        self.create_statistics_area(right_frame)
        self.create_search_area(right_frame)

        # 左侧内容区域 - 填充剩余空间
        left_frame = tk.Frame(main_frame, bg=tc["bg"])
        left_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        # 题型选择区域
        self.create_type_selection_area(left_frame)

        # 题目显示区域
        self.create_question_area(left_frame)

        # 控制按钮区域
        self.create_control_buttons_area(left_frame)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        tc = get_theme_colors()
        menu_opts = {
            "bg": tc["bg_secondary"],
            "fg": tc["text"],
            "activebackground": tc["primary"],
            "activeforeground": "#ffffff",
        }
        menubar = tk.Menu(self.root, **menu_opts)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0, **menu_opts)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="返回主界面", command=self.return_to_main)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0, **menu_opts)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        self.edit_menu_label = edit_menu
        edit_menu.add_command(label="编辑题目", command=self.toggle_edit_mode)
        edit_menu.add_command(label="保存到原文件", command=self.save_question_edit)
        edit_menu.add_command(label="另存为…", command=self.save_question_edit_as)
        
        # 练习菜单
        practice_menu = tk.Menu(menubar, tearoff=0, **menu_opts)
        menubar.add_cascade(label="练习", menu=practice_menu)
        practice_menu.add_command(label="重置统计", command=self.reset_statistics)
        practice_menu.add_command(label="错题复习", command=self.review_wrong_questions)
        practice_menu.add_command(label="随机打乱", command=self.shuffle_questions)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0, **menu_opts)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="按ID搜索", command=self.search_by_id)
        tools_menu.add_command(label="关键词搜索", command=self.search_by_keyword)
    def create_type_selection_area(self, parent):
        """创建题型选择区域"""
        tc = get_theme_colors()
        type_frame = tk.LabelFrame(parent, text="题型选择", font=BOLD_FONT,
                                   bg=tc["bg"], fg=tc["text"])
        type_frame.pack(fill='x', pady=(0, 10))
        
        # 题型选择按钮
        buttons_frame = tk.Frame(type_frame, bg=tc["bg"])
        buttons_frame.pack(padx=10, pady=10)
        
        # 定义唯一的题型显示顺序，避免重复
        unique_types = [
            ("all", "全部题型"),
            ("single", "单选题"),
            ("multiple", "多选题"),
            ("judge", "判断题"),
            ("fill", "填空题"),
            ("short", "简答题")
        ]
        
        for type_key, type_name in unique_types:
            btn = ttk.Button(buttons_frame, text=type_name,
                           command=lambda t=type_key: self.change_question_type(t))
            btn.pack(side='left', padx=5)
    
    def create_question_area(self, parent):
        """创建题目显示区域（含右上角收藏按钮）"""
        tc = get_theme_colors()
        self.question_area_wrapper = tk.Frame(parent, bg=tc["bg"])
        self.question_area_wrapper.pack(fill='both', expand=True, pady=(0, 10))

        # 题目容器（内容会被反复清空重建）
        self.question_container = tk.Frame(self.question_area_wrapper, bg=tc["bg"])
        self.question_container.pack(fill='both', expand=True)

        # 初始提示
        self.show_loading_message()

    def create_control_buttons_area(self, parent):
        """创建底部控制按钮区域 — 单行两端对齐"""
        tc = get_theme_colors()
        control_frame = tk.Frame(parent, bg=tc["bg"])
        control_frame.pack(fill='x')
        
        # 左侧：导航按钮
        nav_frame = tk.Frame(control_frame, bg=tc["bg"])
        nav_frame.pack(side='left')
        
        self.prev_btn = ttk.Button(nav_frame, text="上一题",
                                   command=self.prev_question)
        self.prev_btn.pack(side='left', padx=5)
        
        self.next_btn = ttk.Button(nav_frame, text="下一题",
                                   command=self.next_question)
        self.next_btn.pack(side='left', padx=5)
        
        self.random_btn = ttk.Button(nav_frame, text="随机题",
                                     command=self.random_question)
        self.random_btn.pack(side='left', padx=5)
        
        # 中间弹性空间
        tk.Frame(control_frame, bg=tc["bg"]).pack(side='left', fill='x', expand=True)
        
        # 右侧：答题按钮
        answer_frame = tk.Frame(control_frame, bg=tc["bg"])
        answer_frame.pack(side='right')
        
        self.show_answer_btn = ttk.Button(answer_frame, text="显示答案",
                                          command=self.toggle_answer_display)
        self.show_answer_btn.pack(side='left', padx=5)
        
        # 提交答案 — 主按钮样式
        self.submit_btn = tk.Button(
            answer_frame, text="提交答案",
            font=BOLD_FONT, fg="white", bg="#007bff",
            activeforeground="white", activebackground="#0056b3",
            bd=0, padx=16, pady=4, cursor="hand2",
            command=self.submit_answer,
        )
        self.submit_btn.pack(side='left', padx=5)

    def create_range_area(self, parent):
        """创建练习范围选择区域"""
        tc = get_theme_colors()
        range_frame = tk.LabelFrame(parent, text="练习范围", font=BOLD_FONT,
                                    bg=tc["bg"], fg=tc["text"])
        range_frame.pack(fill='x', pady=(0, 10))

        range_container = tk.Frame(range_frame, bg=tc["bg"])
        range_container.pack(fill='x', padx=10, pady=10)

        options = [
            ("continue", "继续上次"),
            ("all", "全部题目"),
            ("collected", "仅收藏"),
            ("wrong", "错题复习"),
        ]

        for value, text in options:
            rb = ttk.Radiobutton(
                range_container,
                text=text,
                value=value,
                variable=self.range_var,
                command=lambda v=value: self.change_practice_range(v),
            )
            rb.pack(anchor='w', pady=2)

    def create_statistics_area(self, parent):
        """创建统计区域"""
        tc = get_theme_colors()
        stats_frame = tk.LabelFrame(parent, text="练习统计", font=BOLD_FONT,
                                    bg=tc["bg"], fg=tc["text"])
        stats_frame.pack(fill='x', pady=(0, 10))
        
        self.stats_container = tk.Frame(stats_frame, bg=tc["bg"])
        self.stats_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 初始化统计显示
        self.update_statistics_display()
    
    def create_search_area(self, parent):
        """创建搜索区域"""
        tc = get_theme_colors()
        search_frame = tk.LabelFrame(parent, text="题目搜索", font=BOLD_FONT,
                                     bg=tc["bg"], fg=tc["text"])
        search_frame.pack(fill='x', pady=(0, 10))
        
        search_container = tk.Frame(search_frame, bg=tc["bg"])
        search_container.pack(fill='x', padx=10, pady=10)
        
        # ID搜索
        id_frame = tk.Frame(search_container, bg=tc["bg"])
        id_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(id_frame, text="题目ID:").pack(side='left')
        self.id_entry = ttk.Entry(id_frame, width=10)
        self.id_entry.pack(side='left', padx=(5, 0))
        self.id_entry.bind('<Return>', lambda e: self.search_by_id())
        
        ttk.Button(id_frame, text="跳转", 
                  command=self.search_by_id).pack(side='right')
        
        # 关键词搜索
        keyword_frame = tk.Frame(search_container, bg=tc["bg"])
        keyword_frame.pack(fill='x', pady=(5, 0))
        
        ttk.Label(keyword_frame, text="关键词:").pack(anchor='w')
        self.keyword_entry = ttk.Entry(keyword_frame)
        self.keyword_entry.pack(fill='x', pady=(2, 0))
        self.keyword_entry.bind('<Return>', lambda e: self.search_by_keyword())
        
        ttk.Button(keyword_frame, text="搜索",
                  command=self.search_by_keyword).pack(pady=(2, 0))
    
    def show_loading_message(self):
        """显示加载提示"""
        for widget in self.question_container.winfo_children():
            widget.destroy()
        
        loading_label = tk.Label(self.question_container, 
                                text="正在加载题目...",
                                font=DEFAULT_FONT,
                                bg=get_theme_colors()["bg"],
                                fg=get_theme_colors()["text"])
        loading_label.pack(expand=True)
    
    def _start_initial_practice_session(self):
        """进入练习模式时直接开始，不再弹出范围选择窗口。"""
        progress = self.user_data.get_progress(self.file_path) if self.file_path else {}
        saved_range = progress.get("practice_range") or ("continue" if progress else "all")

        if saved_range == "continue" and self._continue_from_progress(progress):
            return
        if saved_range == "collected":
            self._practice_range = "collected"
            self.range_var.set("collected")
            self._collected_only = True
            self._selected_question_type = progress.get("selected_type", "all")
            if self.start_practice_session(self._selected_question_type, restore_progress=False):
                return
        if saved_range == "wrong":
            if self.review_wrong_questions(show_tip=False, restore_progress=False):
                return
        if saved_range == "all":
            self._practice_range = "all"
            self.range_var.set("all")
            self._collected_only = False
            self._selected_question_type = progress.get("selected_type", "all")
            if self.start_practice_session(self._selected_question_type, restore_progress=False):
                return

        self._practice_range = "all"
        self.range_var.set("all")
        self._collected_only = False
        self._selected_question_type = "all"
        self.start_practice_session("all", restore_progress=False)

    def _continue_from_progress(self, progress: Dict[str, Any]) -> bool:
        """按保存的题型、范围和题号继续上次练习。"""
        if not progress:
            return False

        self._practice_range = "continue"
        self.range_var.set("continue")
        self._collected_only = progress.get("collected_only", False)
        self._selected_question_type = progress.get("selected_type", "all")

        if self._selected_question_type == "wrong":
            return self.review_wrong_questions(
                show_tip=False,
                restore_progress=True,
                practice_range="continue",
            )
        return self.start_practice_session(self._selected_question_type, restore_progress=True)

    def change_practice_range(self, range_key: str):
        """切换练习范围。"""
        previous_range = self._practice_range
        previous_collected = self._collected_only
        previous_type = self._selected_question_type

        try:
            if range_key == "continue":
                progress = self.user_data.get_progress(self.file_path) if self.file_path else {}
                if not progress:
                    show_message_dialog("提示", "暂无上次练习进度", "info")
                    raise ValueError("no_progress")
                self._practice_range = "continue"
                self._collected_only = progress.get("collected_only", False)
                self._selected_question_type = progress.get("selected_type", "all")
                if not self._continue_from_progress(progress):
                    raise ValueError("start_failed")
                self._save_progress()
            elif range_key == "all":
                self._practice_range = "all"
                self._collected_only = False
                question_type = "all" if self._selected_question_type == "wrong" else self._selected_question_type
                if not self.start_practice_session(question_type, restore_progress=False):
                    raise ValueError("start_failed")
                self._save_progress()
            elif range_key == "collected":
                collected = (
                    len(self.question_service.question_bank.get_collected_questions())
                    if self.question_service.question_bank else 0
                )
                if collected == 0:
                    show_message_dialog("提示", "当前没有收藏的题目", "info")
                    raise ValueError("no_collected")
                self._practice_range = "collected"
                self._collected_only = True
                question_type = "all" if self._selected_question_type == "wrong" else self._selected_question_type
                if not self.start_practice_session(question_type, restore_progress=False):
                    raise ValueError("start_failed")
                self._save_progress()
            elif range_key == "wrong":
                if not self.review_wrong_questions(show_tip=True, restore_progress=False):
                    raise ValueError("no_wrong")
            else:
                return
        except ValueError:
            self._practice_range = previous_range
            self._collected_only = previous_collected
            self._selected_question_type = previous_type
            self.range_var.set(previous_range)

    def start_practice_session(self, question_type: str, restore_progress: bool = True) -> bool:
        """开始练习会话"""
        previous_type = self._selected_question_type
        try:
            self.question_service.start_practice_session(question_type, self._collected_only)
            self._selected_question_type = question_type
            if restore_progress:
                self._restore_progress(question_type)
            self.show_current_question()
    
            self._update_fav_button()
            self.range_var.set(self._practice_range)
            self.update_statistics_display()
            self.update_button_states()
            return True
        except Exception as e:
            self._selected_question_type = previous_type
            show_message_dialog("错误", f"启动练习失败：{str(e)}", "error")
            return False
    
    def show_current_question(self):
        """显示当前题目"""
        current_question = self.question_service.get_current_question()
        if not current_question:
            self.show_no_question_message()
            return
        
        # 清空题目显示区域
        for widget in self.question_container.winfo_children():
            widget.destroy()
        
        # 获取练习统计信息
        stats = self.question_service.get_practice_statistics()
        
        # 准备题目数据
        question_data = {
            'id': current_question.id,
            'type': current_question.type,
            'type_name': get_question_type_name(current_question.type),
            'question': current_question.question,
            'options': current_question.options,
            'answer': current_question.answer,
            'explanation': current_question.explanation,
            'index': stats.get('current_index', 1),
            'show_id': True  # 练习模式显示题目ID
        }
        
        # 创建题目显示组件
        self.question_display = QuestionDisplay(
            self.question_container,
            question_data,
            title_action=self._create_fav_button,
        )
        question_frame = self.question_display.create_question_frame()
        
        # 如果正在显示答案，压缩题目区域，增大答案区域
        if stats.get('showing_answer', False):
            question_frame.pack(fill='x', expand=False)
            self.show_answer_info(current_question)
        else:
            question_frame.pack(fill='both', expand=True)
    
    def show_answer_with_result(self, user_answer: str, result: dict):
        """显示答案和结果，保持用户选择状态"""
        current_question = self.question_service.get_current_question()
        if not current_question:
            return
        
        # 清空题目显示区域
        for widget in self.question_container.winfo_children():
            widget.destroy()
        
        # 获取练习统计信息
        stats = self.question_service.get_practice_statistics()
        
        # 准备题目数据
        question_data = {
            'id': current_question.id,
            'type': current_question.type,
            'type_name': get_question_type_name(current_question.type),
            'question': current_question.question,
            'options': current_question.options,
            'answer': current_question.answer,
            'explanation': current_question.explanation,
            'index': stats.get('current_index', 1),
            'show_id': True  # 练习模式显示题目ID
        }
        
        # 创建题目显示组件
        self.question_display = QuestionDisplay(
            self.question_container,
            question_data,
            title_action=self._create_fav_button,
        )
        question_frame = self.question_display.create_question_frame()
        
        # 压缩题目区域，为答案区域留出更多空间
        question_frame.pack(fill='x', expand=False)
        
        # 恢复用户的选择状态
        self.question_display.set_user_answer(user_answer)
        
        # 显示答案信息和结果
        self.show_answer_info_with_result(current_question, result, user_answer)
    
    def show_no_question_message(self):
        """显示无题目提示"""
        for widget in self.question_container.winfo_children():
            widget.destroy()
        
        no_question_label = tk.Label(self.question_container,
                                    text="没有找到符合条件的题目",
                                    font=DEFAULT_FONT,
                                    bg=get_theme_colors()["bg"],
                                    fg=get_theme_colors()["text"])
        no_question_label.pack(expand=True)
    
    def show_answer_info(self, question: Question):
        """显示答案信息"""
        tc = get_theme_colors()
        answer_bg = tc["answer_bg"]
        answer_frame = tk.Frame(self.question_container, bg=answer_bg, 
                               relief='solid', bd=1)
        answer_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        # 正确答案标题
        answer_title = tk.Label(answer_frame, text="正确答案：",
                               font=BOLD_FONT, bg=answer_bg, fg=tc["correct_fg"])
        answer_title.pack(anchor='w', padx=10, pady=(5, 0))
        
        # 增大答案显示区域高度（最小4行，最大10行）
        newline_count = question.answer.count(chr(10))
        char_lines = len(question.answer) // 80
        answer_lines = newline_count + char_lines + 1
        answer_height = max(4, min(10, answer_lines))
        
        # 正确答案内容 - 使用ScrolledText组件支持换行和滚动
        from tkinter import scrolledtext
        answer_text = scrolledtext.ScrolledText(answer_frame, height=answer_height, 
                                               wrap=tk.WORD, font=DEFAULT_FONT, 
                                               bg=answer_bg, fg=tc["correct_fg"],
                                               insertbackground=tc["text"],
                                               relief='flat', bd=0)
        answer_text.pack(fill='x', padx=10, pady=(0, 5))
        
        # 转换判断题正确答案显示
        display_correct_answer = self.convert_judge_answer_display(question, question.answer)
        answer_text.insert('1.0', display_correct_answer)
        answer_text.config(state='disabled')
        
        # 解析
        if question.explanation:
            # 解析标题
            explanation_title = tk.Label(answer_frame, text="解析：",
                                       font=BOLD_FONT, bg=answer_bg, fg=tc["primary"])
            explanation_title.pack(anchor='w', padx=10, pady=(5, 0))
            
            # 增大解析显示区域高度（最小4行，最大8行）
            explanation_newlines = question.explanation.count(chr(10))
            explanation_char_lines = len(question.explanation) // 80
            explanation_lines = explanation_newlines + explanation_char_lines + 1
            explanation_height = max(4, min(8, explanation_lines))
            
            # 解析内容 - 使用ScrolledText组件支持换行和滚动
            from tkinter import scrolledtext
            explanation_text = scrolledtext.ScrolledText(answer_frame, height=explanation_height,
                                                       wrap=tk.WORD, font=DEFAULT_FONT,
                                                       bg=answer_bg, fg=tc["text"],
                                                       insertbackground=tc["text"],
                                                       relief='flat', bd=0)
            explanation_text.pack(fill='both', expand=True, padx=10, pady=(0, 5))
            explanation_text.insert('1.0', question.explanation)
            explanation_text.config(state='disabled')
        self._create_ai_review_entry(answer_frame, question, "")
    
    def show_answer_info_with_result(self, question: Question, result: dict, user_answer: str):
        """显示答案信息和答题结果"""
        tc = get_theme_colors()
        # 根据答题结果选择背景色
        bg_color = tc["answer_bg"]
        if result['is_correct']:
            result_text = "✓ 回答正确！"
            result_color = tc["correct_fg"]
        else:
            result_text = "✗ 回答错误！"
            result_color = tc["wrong_fg"]
        
        answer_frame = tk.Frame(self.question_container, bg=bg_color, 
                               relief='solid', bd=2)
        answer_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        # 答题结果标题
        result_title = tk.Label(answer_frame, text=result_text,
                               font=BOLD_FONT, bg=bg_color, fg=result_color)
        result_title.pack(anchor='w', padx=10, pady=(5, 0))
        
        # 用户答案（如果答错）
        if not result['is_correct']:
            user_answer_title = tk.Label(answer_frame, text="你的答案：",
                                       font=BOLD_FONT, bg=bg_color, fg=tc["wrong_fg"])
            user_answer_title.pack(anchor='w', padx=10, pady=(5, 0))
            
            # 转换判断题答案显示
            display_user_answer = self.convert_judge_answer_display(question, user_answer)
            
            user_answer_text = tk.Label(answer_frame, text=display_user_answer,
                                      font=DEFAULT_FONT, bg=bg_color, fg=tc["wrong_fg"],
                                      wraplength=600, justify='left')
            user_answer_text.pack(anchor='w', padx=10, pady=(0, 5))
        
        # 正确答案标题
        answer_title = tk.Label(answer_frame, text="正确答案：",
                               font=BOLD_FONT, bg=bg_color, fg=tc["correct_fg"])
        answer_title.pack(anchor='w', padx=10, pady=(5, 0))
        
        # 增大答案显示区域高度（最小4行，最大10行）
        newline_count = question.answer.count(chr(10))
        char_lines = len(question.answer) // 80
        answer_lines = newline_count + char_lines + 1
        answer_height = max(4, min(10, answer_lines))
        
        # 正确答案内容 - 使用ScrolledText组件支持换行和滚动
        from tkinter import scrolledtext
        answer_text = scrolledtext.ScrolledText(answer_frame, height=answer_height, 
                                               wrap=tk.WORD, font=DEFAULT_FONT, 
                                               bg=bg_color, fg=tc["correct_fg"],
                                               insertbackground=tc["text"],
                                               relief='flat', bd=0)
        answer_text.pack(fill='x', padx=10, pady=(0, 5))
        
        # 转换判断题正确答案显示
        display_correct_answer = self.convert_judge_answer_display(question, question.answer)
        answer_text.insert('1.0', display_correct_answer)
        answer_text.config(state='disabled')
        
        # 解析
        if question.explanation:
            # 解析标题
            explanation_title = tk.Label(answer_frame, text="解析：",
                                       font=BOLD_FONT, bg=bg_color, fg=tc["primary"])
            explanation_title.pack(anchor='w', padx=10, pady=(5, 0))
            
            # 增大解析显示区域高度（最小4行，最大8行）
            explanation_newlines = question.explanation.count(chr(10))
            explanation_char_lines = len(question.explanation) // 80
            explanation_lines = explanation_newlines + explanation_char_lines + 1
            explanation_height = max(4, min(8, explanation_lines))
            
            # 解析内容 - 使用ScrolledText组件支持换行和滚动
            from tkinter import scrolledtext
            explanation_text = scrolledtext.ScrolledText(answer_frame, height=explanation_height,
                                                       wrap=tk.WORD, font=DEFAULT_FONT,
                                                       bg=bg_color, fg=tc["text"],
                                                       insertbackground=tc["text"],
                                                       relief='flat', bd=0)
            explanation_text.pack(fill='both', expand=True, padx=10, pady=(0, 5))
            explanation_text.insert('1.0', question.explanation)
            explanation_text.config(state='disabled')
        self._create_ai_review_entry(answer_frame, question, user_answer)

    def _create_ai_review_entry(self, parent, question: Question, user_answer: str):
        """创建 AI 复核入口。"""
        tc = get_theme_colors()
        row = tk.Frame(parent, bg=parent.cget("bg"))
        row.pack(fill="x", padx=10, pady=(8, 10))
        ttk.Button(
            row,
            text="AI 复核本题",
            command=lambda: self._open_ai_review(question, user_answer),
        ).pack(side="left")
        tk.Label(
            row,
            text="可继续追问题目、答案或解析是否可靠",
            bg=parent.cget("bg"),
            fg=tc["text_secondary"],
            font=DEFAULT_FONT,
        ).pack(side="left", padx=(10, 0))

    def _open_ai_review(self, question: Question, user_answer: str):
        """打开当前题 AI 复核窗口。"""
        history = self.ai_histories.setdefault(question.id, [])
        show_ai_review_window(self.root, question, user_answer, history)
    
    def convert_judge_answer_display(self, question: Question, user_answer: str) -> str:
        """转换判断题答案显示"""
        if question.type in ['judge', 'judgement']:
            return format_judge_answer(user_answer)
        return user_answer
    
    def get_type_name(self, question_type: str) -> str:
        """获取题型中文名称"""
        return QUESTION_TYPES.get(question_type, question_type)
    
    def change_question_type(self, question_type: str):
        """切换题型"""
        if self._practice_range in ("wrong", "continue"):
            self._practice_range = "all"
            self._collected_only = False
            self.range_var.set("all")
        if self.start_practice_session(question_type, restore_progress=False):
            self._save_progress()
    
    def prev_question(self):
        """上一题"""
        if self.question_service.prev_question():
            self.show_current_question()
            self.update_statistics_display()
            self.update_button_states()
            self._update_fav_button()
            self._save_progress()
    
    def next_question(self):
        """下一题"""
        if self.question_service.next_question():
            self.show_current_question()
            self.update_statistics_display()
            self.update_button_states()
            self._update_fav_button()
            self._save_progress()
    
    def random_question(self):
        """随机题目"""
        if self.question_service.random_question():
            self.show_current_question()
            self.update_statistics_display()
            self.update_button_states()
            self._update_fav_button()
            self._save_progress()
    
    def submit_answer(self):
        """提交答案"""
        if not self.question_display:
            return
        
        user_answer = self.question_display.get_user_answer()
        if not user_answer.strip():
            show_message_dialog("提示", "请先选择或输入答案", "warning")
            return
        
        try:
            result = self.question_service.submit_answer(user_answer)
            
            # 记录错题（如果答错）
            if not result['is_correct']:
                self.record_wrong_answer()

            # 更新累计统计
            self.user_data.update_stats(1, 1 if result.get('is_correct') else 0, "practice")

            # 更新统计显示
            self.update_statistics_display()
            
            # 自动显示答案和结果，但保持用户选择状态
            self.question_service.toggle_answer_display()
            self.show_answer_with_result(user_answer, result)
            self._save_progress()
            
        except Exception as e:
            show_message_dialog("错误", f"提交答案失败：{str(e)}", "error")
    
    def toggle_answer_display(self):
        """切换答案显示"""
        self.question_service.toggle_answer_display()
        self.show_current_question()
        
        # 更新按钮文本
        stats = self.question_service.get_practice_statistics()
        if stats.get('showing_answer', False):
            self.show_answer_btn.config(text="隐藏答案")
        else:
            self.show_answer_btn.config(text="显示答案")
    
    def update_statistics_display(self):
        """更新统计显示"""
        stats = self.question_service.get_practice_statistics()
        
        # 清空统计信息
        for widget in self.stats_container.winfo_children():
            widget.destroy()
        
        # 显示统计信息
        filtered = stats.get('total_questions', 0)
        bank_total = stats.get('bank_total', filtered)
        total_text = f"{filtered}/{bank_total}" if filtered != bank_total else str(filtered)
        
        info_items = [
            ("筛选题数", total_text),
            ("当前题号", f"{stats.get('current_index', 1)}/{filtered}"),
            ("已答题数", stats.get('answered_count', 0)),
            ("正确数", stats.get('correct_count', 0)),
            ("错误数", stats.get('wrong_count', 0)),
            ("正确率", f"{stats.get('accuracy', 0):.1f}%")
        ]
        
        for label, value in info_items:
            tc = get_theme_colors()
            item_frame = tk.Frame(self.stats_container, bg=tc["bg"])
            item_frame.pack(fill='x', pady=2)
            
            tk.Label(item_frame, text=f"{label}:", font=DEFAULT_FONT,
                     bg=tc["bg"], fg=tc["text"]).pack(side='left')
            tk.Label(item_frame, text=str(value), font=BOLD_FONT, 
                    bg=tc["bg"], fg=tc["primary"]).pack(side='right')
    
    def update_button_states(self):
        """更新按钮状态"""
        stats = self.question_service.get_practice_statistics()
        current_index = stats.get('current_index', 1)
        total_questions = stats.get('total_questions', 0)
        
        # 导航按钮状态
        self.prev_btn.config(state='normal' if current_index > 1 else 'disabled')
        self.next_btn.config(state='normal' if current_index < total_questions else 'disabled')
        self.random_btn.config(state='normal' if total_questions > 1 else 'disabled')
        
        # 显示答案按钮状态
        if hasattr(self, 'show_answer_btn'):
            if stats.get('showing_answer', False):
                self.show_answer_btn.config(text="隐藏答案")
            else:
                self.show_answer_btn.config(text="显示答案")
    
    def search_by_id(self):
        """按ID搜索题目"""
        try:
            id_text = self.id_entry.get().strip()
            if not id_text:
                show_message_dialog("提示", "请输入题目ID", "warning")
                return
            
            question_id = int(id_text)
            if self.question_service.jump_to_question_by_id(question_id):
                self.show_current_question()
                self.update_statistics_display()
                self.update_button_states()
                self._save_progress()
                self.id_entry.delete(0, tk.END)
            else:
                show_message_dialog("提示", f"未找到ID为{question_id}的题目", "warning")
                
        except ValueError:
            show_message_dialog("错误", "请输入有效的数字ID", "error")
        except Exception as e:
            show_message_dialog("错误", f"搜索失败：{str(e)}", "error")
    
    def search_by_keyword(self):
        """按关键词搜索题目"""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            show_message_dialog("提示", "请输入搜索关键词", "warning")
            return
        
        try:
            results = self.question_service.search_questions(keyword)
            if results:
                self.show_search_results(results, keyword)
            else:
                show_message_dialog("提示", f"未找到包含'{keyword}'的题目", "info")
        except Exception as e:
            show_message_dialog("错误", f"搜索失败：{str(e)}", "error")
    
    def show_search_results(self, results: list, keyword: str):
        """显示搜索结果"""
        tc = get_theme_colors()
        result_window = tk.Toplevel(self.root)
        result_window.title(f"搜索结果 - '{keyword}'")
        result_window.configure(bg=tc["bg"])
        center_window(result_window, 800, 600)
        
        # 结果列表
        frame = tk.Frame(result_window, bg=tc["bg"])
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(frame, text=f"找到 {len(results)} 道相关题目：", 
                font=BOLD_FONT, bg=tc["bg"], fg=tc["text"]).pack(anchor='w', pady=(0, 10))
        
        # 创建列表框
        listbox_frame = tk.Frame(frame, bg=tc["bg"])
        listbox_frame.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side='right', fill='y')
        
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, font=DEFAULT_FONT,
                             bg=tc["bg_secondary"], fg=tc["text"],
                             selectbackground=tc["primary"], selectforeground="#ffffff")
        listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=listbox.yview)
        
        # 添加搜索结果
        for question in results:
            type_name = get_question_type_name(question.type)
            item_text = f"ID:{question.id} [{type_name}] {question.question[:50]}..."
            listbox.insert(tk.END, item_text)
        
        # 双击跳转
        def on_double_click(event):
            selection = listbox.curselection()
            if selection:
                selected_question = results[selection[0]]
                if self.question_service.jump_to_question_by_id(selected_question.id):
                    self.show_current_question()
                    self.update_statistics_display()
                    self.update_button_states()
                    self._save_progress()
                    result_window.destroy()
        
        listbox.bind('<Double-1>', on_double_click)
        
        # 按钮
        button_frame = tk.Frame(frame, bg=tc["bg"])
        button_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(button_frame, text="跳转到选中题目",
                  command=lambda: on_double_click(None) if listbox.curselection() else None).pack(side='left')
        
        ttk.Button(button_frame, text="关闭",
                  command=result_window.destroy).pack(side='right')
    
    def reset_statistics(self):
        """重置统计"""
        if show_message_dialog("确认", "确定要重置练习统计吗？", "question"):
            self.question_service.reset_practice_statistics()
            self.update_statistics_display()
    
    def review_wrong_questions(
        self,
        show_tip: bool = True,
        restore_progress: bool = False,
        practice_range: str = "wrong",
    ) -> bool:
        """复习错题"""
        wrong_questions = self._get_wrong_review_questions()
        if self.question_service.start_review_session(wrong_questions, "wrong"):
            self._practice_range = practice_range
            self.range_var.set(practice_range)
            self._collected_only = False
            self._selected_question_type = "wrong"
            if restore_progress:
                self._restore_progress("wrong")
            self.show_current_question()
            self.update_statistics_display()
            self.update_button_states()
            self._save_progress()
            if show_tip:
                show_message_dialog("提示", "已切换到错题复习模式", "info")
            return True
        else:
            self.range_var.set(self._practice_range)
            if show_tip:
                show_message_dialog("提示", "暂无错题可复习", "info")
            return False

    def _get_wrong_review_questions(self):
        """合并当前会话错题和历史错题，作为错题复习范围。"""
        questions_by_id = {}
        for question in self.question_service.get_wrong_questions():
            questions_by_id[question.id] = question
        if self.file_path and self.question_service.question_bank:
            for question_id in self.user_data.get_wrong_history(self.file_path):
                question = self.question_service.question_bank.get_question_by_id(question_id)
                if question:
                    questions_by_id[question.id] = question
        return list(questions_by_id.values())
    
    def shuffle_questions(self):
        """打乱题目顺序"""
        self.question_service.shuffle_current_questions()
        self.show_current_question()
        self.update_statistics_display()
        self._save_progress()
        show_message_dialog("提示", "题目顺序已打乱", "info")
    
    def bind_keyboard_shortcuts(self):
        """绑定键盘快捷键"""
        self.root.bind('<Left>', lambda e: self.prev_question())
        self.root.bind('<Right>', lambda e: self.next_question())
        self.root.bind('<r>', lambda e: self.random_question())
        self.root.bind('<R>', lambda e: self.random_question())
        self.root.bind('<Return>', lambda e: self.submit_answer())
        self.root.bind('<space>', lambda e: self.toggle_answer_display())
    
    def return_to_main(self):
        """返回主界面"""
        self._save_progress()
        if self.on_return_to_main:
            self.on_return_to_main()
    
    def set_return_callback(self, callback: Callable):
        """设置返回主界面回调"""
        self.on_return_to_main = callback
    
    def toggle_edit_mode(self):
        """切换编辑模式"""
        current_question = self.question_service.get_current_question()
        if not current_question:
            show_message_dialog("提示", "没有当前题目可编辑", "warning")
            return
        
        self.is_editing = not self.is_editing
        
        if self.is_editing:
            self.edit_menu_label.entryconfig(0, label="取消编辑")
            self.create_edit_interface()
        else:
            self.edit_menu_label.entryconfig(0, label="编辑题目")
            if self.edit_window:
                self.edit_window.destroy()
                self.edit_window = None
    
    def create_edit_interface(self):
        """创建编辑界面"""
        current_question = self.question_service.get_current_question()
        if not current_question:
            return
        
        # 创建编辑界面组件
        result = create_edit_interface(
            self.root, 
            current_question,
            update_answer_format_hint,
            update_answer_format_hint
        )
        
        if result[0]:  # edit_window
            self.edit_window = result[0]
            self.type_var = result[1]
            self.question_edit = result[2]
            self.options_edit = result[3]
            self.answer_edit = result[4]
            self.explanation_edit = result[5]
            button_frame = result[6]
            self.format_label = result[7]
            
            # 添加按钮
            ttk.Button(button_frame, text="保存修改", command=self.save_edit_window).pack(side='left', padx=5)
            ttk.Button(button_frame, text="取消", command=self.cancel_edit_window).pack(side='left', padx=5)
    
    def on_type_change(self, format_label, question_type):
        """题目类型改变时更新答案格式提示"""
        update_answer_format_hint(format_label, question_type)
    
    def save_edit_window(self):
        """保存编辑窗口内容"""
        current_question = self.question_service.get_current_question()
        if not current_question:
            return
        
        # 保存编辑内容
        if save_edit_changes(current_question, self.type_var, self.question_edit, 
                           self.options_edit, self.answer_edit, self.explanation_edit):
            # 关闭编辑窗口
            self.edit_window.destroy()
            self.edit_window = None
            
            # 退出编辑模式并刷新显示
            self.is_editing = False
            self.edit_menu_label.entryconfig(0, label="编辑题目")
            self.show_current_question()
            
            show_message_dialog("成功", "题目已保存到当前题库，如需写入文件请使用保存功能", "info")
    
    def cancel_edit_window(self):
        """取消编辑窗口"""
        if self.edit_window:
            self.edit_window.destroy()
            self.edit_window = None
        self.is_editing = False
        self.edit_menu_label.entryconfig(0, label="编辑题目")
    
    def save_question_edit(self):
        """保存题目编辑到原文件"""
        question_bank = self.question_service.question_bank
        save_question_bank_to_file(question_bank, force_dialog=False)
    
    def save_question_edit_as(self):
        """另存为题库文件"""
        question_bank = self.question_service.question_bank
        save_question_bank_to_file(question_bank, force_dialog=True)
    
    def set_wrong_questions_callback(self, callback):
        """设置错题记录回调函数"""
        self.on_wrong_questions = callback
    
    def toggle_favorite(self):
        """切换收藏状态"""
        current = self.question_service.get_current_question()
        if not current:
            return
        current.is_collected = not current.is_collected
        self._is_fav = current.is_collected
        self._update_fav_button()
        # 自动保存收藏状态到题库文件
        if self.file_path:
            from core.utils import save_questions_to_file
            save_questions_to_file(self.question_service.question_bank, self.file_path)

    def _create_fav_button(self, parent):
        """在题目标题栏右侧创建收藏按钮。"""
        tc = get_theme_colors()
        self.fav_btn = tk.Button(
            parent,
            text="☆ 收藏",
            font=DEFAULT_FONT,
            bd=1,
            relief="groove",
            cursor="hand2",
            bg=tc["bg_secondary"],
            fg=tc["text"],
            activebackground=tc["card_bg"],
            activeforeground=tc["text"],
            command=self.toggle_favorite,
        )
        self.fav_btn.pack(side='right', padx=10, pady=6)
        self._update_fav_button()

    def _update_fav_button(self):
        """更新收藏按钮状态"""
        if not hasattr(self, "fav_btn") or not self.fav_btn.winfo_exists():
            return
        current = self.question_service.get_current_question()
        if not current:
            tc = get_theme_colors()
            self.fav_btn.config(text="☆ 收藏", bg=tc["bg_secondary"], fg=tc["text"])
            return
        self._is_fav = current.is_collected
        if self._is_fav:
            self.fav_btn.config(text="★ 已收藏", fg="#e74c3c", font=BOLD_FONT)
        else:
            tc = get_theme_colors()
            self.fav_btn.config(text="☆ 收藏", bg=tc["bg_secondary"], fg=tc["text"], font=DEFAULT_FONT)

    def _save_progress(self):
        """保存练习进度"""
        if not self.file_path:
            return
        stats = self.question_service.get_practice_statistics()
        self.user_data.save_progress(self.file_path, {
            "practice_range": self._practice_range,
            "current_index": stats.get("current_index", 1) - 1,
            "selected_type": stats.get("selected_type", "all"),
            "collected_only": self._collected_only,
            "correct_count": stats.get("correct_count", 0),
            "answered_count": stats.get("answered_count", 0),
        })

    def _restore_progress(self, question_type: str):
        """恢复练习进度"""
        if not self.file_path:
            return
        progress = self.user_data.get_progress(self.file_path)
        if progress:
            if progress.get("selected_type", "all") != question_type:
                return
            if progress.get("collected_only", False) != self._collected_only:
                return
            # 恢复统计
            session = self.question_service.practice_session
            if session:
                session.correct_count = progress.get("correct_count", 0)
                session.answered_count = progress.get("answered_count", 0)
                idx = progress.get("current_index", 0)
                if 0 <= idx < len(session.questions):
                    session.current_question_index = idx

    def record_wrong_answer(self):
        """记录错题"""
        if self.on_wrong_questions:
            current_question = self.question_service.get_current_question()
            if current_question:
                # 直接传递题目ID而不是索引
                self.on_wrong_questions([current_question.id])
