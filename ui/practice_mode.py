#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
练习模式界面模块
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, Dict, Any, Callable
from core.config import DEFAULT_FONT, BOLD_FONT, COLORS, QUESTION_TYPES
from core.models import QuestionBank, Question
from services.question_service import QuestionService
from ui.components import QuestionDisplay, StatisticsDisplay, show_message_dialog, center_window
from ui.widgets import get_question_type_name
from services.user_data_service import UserDataService
from ui.edit_functions import create_edit_interface, update_answer_format_hint, save_edit_changes, save_question_bank_to_file


class PracticeModeWindow:
    """练习模式窗口类"""
    
    def __init__(self, root: tk.Tk, question_bank: QuestionBank):
        self.root = root
        self.question_service = QuestionService()
        self.question_service.set_question_bank(question_bank)
        
        # 界面组件
        self.question_display = None
        self.stats_display = None
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

        self.create_practice_interface()
        self.bind_keyboard_shortcuts()
        
        # 显示练习范围选择
        self._show_practice_range_dialog()
    
    def create_practice_interface(self):
        """创建练习界面"""
        # 设置窗口标题
        self.root.title("灵测 LingCe - 练习模式")
        
        # 清空窗口
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 主容器
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True)

        # 右侧面板 - 固定宽度，先 pack 确保不被挤压
        right_frame = tk.Frame(main_frame, width=280)
        right_frame.pack(side='right', fill='y', padx=(0, 10), pady=10)
        right_frame.pack_propagate(False)

        self.create_statistics_area(right_frame)
        self.create_search_area(right_frame)

        # 左侧内容区域 - 填充剩余空间
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        # 题型选择区域
        self.create_type_selection_area(left_frame)

        # 题目显示区域
        self.create_question_area(left_frame)

        # 控制按钮区域
        self.create_control_buttons_area(left_frame)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="返回主界面", command=self.return_to_main)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        self.edit_menu_label = edit_menu
        edit_menu.add_command(label="编辑题目", command=self.toggle_edit_mode)
        edit_menu.add_command(label="保存到原文件", command=self.save_question_edit)
        edit_menu.add_command(label="另存为…", command=self.save_question_edit_as)
        
        # 练习菜单
        practice_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="练习", menu=practice_menu)
        practice_menu.add_command(label="重置统计", command=self.reset_statistics)
        practice_menu.add_command(label="错题复习", command=self.review_wrong_questions)
        practice_menu.add_command(label="随机打乱", command=self.shuffle_questions)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="按ID搜索", command=self.search_by_id)
        tools_menu.add_command(label="关键词搜索", command=self.search_by_keyword)
    def create_type_selection_area(self, parent):
        """创建题型选择区域"""
        type_frame = tk.LabelFrame(parent, text="题型选择", font=BOLD_FONT)
        type_frame.pack(fill='x', pady=(0, 10))
        
        # 题型选择按钮
        buttons_frame = tk.Frame(type_frame)
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
        # 外层包装：收藏按钮独立于 question_container
        self.question_area_wrapper = tk.Frame(parent)
        self.question_area_wrapper.pack(fill='both', expand=True, pady=(0, 10))

        # 顶部工具栏（只放收藏按钮）
        toolbar = tk.Frame(self.question_area_wrapper)
        toolbar.pack(fill='x')

        self.fav_btn = tk.Button(
            toolbar, text="☆ 收藏",
            font=DEFAULT_FONT, bd=1, relief="groove", cursor="hand2",
            command=self.toggle_favorite,
        )
        self.fav_btn.pack(side='right', padx=10, pady=2)

        # 题目容器（内容会被反复清空重建，不影响收藏按钮）
        self.question_container = tk.Frame(self.question_area_wrapper)
        self.question_container.pack(fill='both', expand=True)

        # 初始提示
        self.show_loading_message()

    def create_control_buttons_area(self, parent):
        """创建底部控制按钮区域 — 单行两端对齐"""
        control_frame = tk.Frame(parent)
        control_frame.pack(fill='x')
        
        # 左侧：导航按钮
        nav_frame = tk.Frame(control_frame)
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
        tk.Frame(control_frame).pack(side='left', fill='x', expand=True)
        
        # 右侧：答题按钮
        answer_frame = tk.Frame(control_frame)
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
    def create_statistics_area(self, parent):
        """创建统计区域"""
        stats_frame = tk.LabelFrame(parent, text="练习统计", font=BOLD_FONT)
        stats_frame.pack(fill='x', pady=(0, 10))
        
        self.stats_container = tk.Frame(stats_frame)
        self.stats_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 初始化统计显示
        self.update_statistics_display()
    
    def create_search_area(self, parent):
        """创建搜索区域"""
        search_frame = tk.LabelFrame(parent, text="题目搜索", font=BOLD_FONT)
        search_frame.pack(fill='x', pady=(0, 10))
        
        search_container = tk.Frame(search_frame)
        search_container.pack(fill='x', padx=10, pady=10)
        
        # ID搜索
        id_frame = tk.Frame(search_container)
        id_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(id_frame, text="题目ID:").pack(side='left')
        self.id_entry = ttk.Entry(id_frame, width=10)
        self.id_entry.pack(side='left', padx=(5, 0))
        self.id_entry.bind('<Return>', lambda e: self.search_by_id())
        
        ttk.Button(id_frame, text="跳转", 
                  command=self.search_by_id).pack(side='right')
        
        # 关键词搜索
        keyword_frame = tk.Frame(search_container)
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
                                font=DEFAULT_FONT)
        loading_label.pack(expand=True)
    
    def _show_practice_range_dialog(self):
        """显示练习范围选择对话框"""
        total = len(self.question_service.question_bank.questions) if self.question_service.question_bank else 0
        collected = len(self.question_service.question_bank.get_collected_questions()) if self.question_service.question_bank else 0
        
        dialog = tk.Toplevel(self.root)
        dialog.title("选择练习范围")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中
        dw, dh = 400, 220
        dialog.geometry(f"{dw}x{dh}")
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dw) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dh) // 2
        dialog.geometry(f"{dw}x{dh}+{x}+{y}")
        
        tk.Label(dialog, text="选择练习范围", font=BOLD_FONT).pack(pady=(20, 15))
        tk.Label(dialog, text=f"题库总量: {total} 题，已收藏: {collected} 题",
                 font=DEFAULT_FONT).pack(pady=(0, 15))
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def choose_all():
            self._collected_only = False
            dialog.destroy()
            self.start_practice_session("all")
        
        def choose_collected():
            if collected == 0:
                from tkinter import messagebox
                messagebox.showwarning("提示", "当前没有收藏的题目", parent=dialog)
                return
            self._collected_only = True
            dialog.destroy()
            self.start_practice_session("all")
        
        tk.Button(btn_frame, text="练习全部题目", font=DEFAULT_FONT,
                  width=16, command=choose_all).pack(side='left', padx=15)
        tk.Button(btn_frame, text=f"只练收藏题 ({collected})", font=DEFAULT_FONT,
                  width=16, command=choose_collected).pack(side='left', padx=15)
        
        dialog.protocol("WM_DELETE_WINDOW", choose_all)

    def start_practice_session(self, question_type: str):
        """开始练习会话"""
        try:
            self.question_service.start_practice_session(question_type, self._collected_only)
            self._restore_progress(question_type)
            self.show_current_question()
    
            self._update_fav_button()
            self.update_statistics_display()
            self.update_button_states()
        except Exception as e:
            show_message_dialog("错误", f"启动练习失败：{str(e)}", "error")
    
    def show_current_question(self):
        """显示当前题目"""
        current_question = self.question_service.get_current_question()
        if not current_question:
            self.show_no_question_message()
            return
        
        # 清除旧的题目显示
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
        self.question_display = QuestionDisplay(self.question_container, question_data)
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
        
        # 清除旧的题目显示
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
        self.question_display = QuestionDisplay(self.question_container, question_data)
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
                                    font=DEFAULT_FONT)
        no_question_label.pack(expand=True)
    
    def show_answer_info(self, question: Question):
        """显示答案信息"""
        answer_frame = tk.Frame(self.question_container, bg='lightyellow', 
                               relief='solid', bd=1)
        answer_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        # 正确答案标题
        answer_title = tk.Label(answer_frame, text="正确答案：",
                               font=BOLD_FONT, bg='lightyellow', fg='green')
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
                                               bg='lightyellow', fg='green',
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
                                       font=BOLD_FONT, bg='lightyellow', fg='blue')
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
                                                       bg='lightyellow', fg='blue',
                                                       relief='flat', bd=0)
            explanation_text.pack(fill='both', expand=True, padx=10, pady=(0, 5))
            explanation_text.insert('1.0', question.explanation)
            explanation_text.config(state='disabled')
    
    def show_answer_info_with_result(self, question: Question, result: dict, user_answer: str):
        """显示答案信息和答题结果"""
        # 根据答题结果选择背景色
        if result['is_correct']:
            bg_color = 'lightgreen'
            result_text = "✓ 回答正确！"
            result_color = 'darkgreen'
        else:
            bg_color = 'lightcoral'
            result_text = "✗ 回答错误！"
            result_color = 'darkred'
        
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
                                       font=BOLD_FONT, bg=bg_color, fg='darkred')
            user_answer_title.pack(anchor='w', padx=10, pady=(5, 0))
            
            # 转换判断题答案显示
            display_user_answer = self.convert_judge_answer_display(question, user_answer)
            
            user_answer_text = tk.Label(answer_frame, text=display_user_answer,
                                      font=DEFAULT_FONT, bg=bg_color, fg='darkred',
                                      wraplength=600, justify='left')
            user_answer_text.pack(anchor='w', padx=10, pady=(0, 5))
        
        # 正确答案标题
        answer_title = tk.Label(answer_frame, text="正确答案：",
                               font=BOLD_FONT, bg=bg_color, fg='darkgreen')
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
                                               bg=bg_color, fg='darkgreen',
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
                                       font=BOLD_FONT, bg=bg_color, fg='blue')
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
                                                       bg=bg_color, fg='blue',
                                                       relief='flat', bd=0)
            explanation_text.pack(fill='both', expand=True, padx=10, pady=(0, 5))
            explanation_text.insert('1.0', question.explanation)
            explanation_text.config(state='disabled')
    
    def convert_judge_answer_display(self, question: Question, user_answer: str) -> str:
        """转换判断题答案显示"""
        if question.type in ['judge', 'judgement']:
            # 标准化答案
            answer = user_answer.strip().upper()
            
            # A选项或正确相关的答案
            if answer in ['A', '√', '正确', 'TRUE', 'T', '对']:
                return '正确'
            # B选项或错误相关的答案
            elif answer in ['B', '×', '错误', 'FALSE', 'F', '错']:
                return '错误'
        return user_answer
    
    def get_type_name(self, question_type: str) -> str:
        """获取题型中文名称"""
        return QUESTION_TYPES.get(question_type, question_type)
    
    def change_question_type(self, question_type: str):
        """切换题型"""
        self.start_practice_session(question_type)
    
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
        
        # 清除旧的统计信息
        for widget in self.stats_container.winfo_children():
            widget.destroy()
        
        # 显示统计信息
        filtered = stats.get('total_questions', 0)
        bank_total = stats.get('bank_total', filtered)
        total_text = f"{filtered}/{bank_total}" if filtered != bank_total else str(filtered)
        range_label = "收藏题" if self._collected_only else "全部题目"
        
        info_items = [
            ("练习范围", range_label),
            ("筛选题数", total_text),
            ("当前题号", f"{stats.get('current_index', 1)}/{filtered}"),
            ("已答题数", stats.get('answered_count', 0)),
            ("正确数", stats.get('correct_count', 0)),
            ("错误数", stats.get('wrong_count', 0)),
            ("正确率", f"{stats.get('accuracy', 0):.1f}%")
        ]
        
        for label, value in info_items:
            item_frame = tk.Frame(self.stats_container)
            item_frame.pack(fill='x', pady=2)
            
            tk.Label(item_frame, text=f"{label}:", font=DEFAULT_FONT).pack(side='left')
            tk.Label(item_frame, text=str(value), font=BOLD_FONT, 
                    fg=COLORS['primary']).pack(side='right')
    
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
        result_window = tk.Toplevel(self.root)
        result_window.title(f"搜索结果 - '{keyword}'")
        center_window(result_window, 800, 600)
        
        # 结果列表
        frame = tk.Frame(result_window)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(frame, text=f"找到 {len(results)} 道相关题目：", 
                font=BOLD_FONT).pack(anchor='w', pady=(0, 10))
        
        # 创建列表框
        listbox_frame = tk.Frame(frame)
        listbox_frame.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side='right', fill='y')
        
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, font=DEFAULT_FONT)
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
                    result_window.destroy()
        
        listbox.bind('<Double-1>', on_double_click)
        
        # 按钮
        button_frame = tk.Frame(frame)
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
    
    def review_wrong_questions(self):
        """复习错题"""
        if self.question_service.start_wrong_question_review():
            self.show_current_question()
            self.update_statistics_display()
            self.update_button_states()
            self._save_progress()
            show_message_dialog("提示", "已切换到错题复习模式", "info")
        else:
            show_message_dialog("提示", "暂无错题可复习", "info")
    
    def shuffle_questions(self):
        """打乱题目顺序"""
        self.question_service.shuffle_current_questions()
        self.show_current_question()
        self.update_statistics_display()
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
        """保存编辑窗口的修改"""
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
            
            show_message_dialog("成功", "题目修改已保存到内存中，如需永久保存请使用保存功能", "info")
    
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

    def _update_fav_button(self):
        """更新收藏按钮状态"""
        current = self.question_service.get_current_question()
        if not current:
            self.fav_btn.config(text="☆ 收藏", fg="black")
            return
        self._is_fav = current.is_collected
        if self._is_fav:
            self.fav_btn.config(text="★ 已收藏", fg="#e74c3c", font=BOLD_FONT)
        else:
            self.fav_btn.config(text="☆ 收藏", fg="black", font=DEFAULT_FONT)

    def _save_progress(self):
        """保存练习进度"""
        if not self.file_path:
            return
        stats = self.question_service.get_practice_statistics()
        self.user_data.save_progress(self.file_path, {
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
