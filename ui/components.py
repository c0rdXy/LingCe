#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 组件模块 — 通用 UI 组件和工具函数
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Callable, Optional
from core.config import DEFAULT_FONT, BOLD_FONT, get_theme_colors


class QuestionDisplay:
    """题目显示组件"""
    
    def __init__(self, parent, question_data: Dict[str, Any], title_action: Optional[Callable[[tk.Frame], None]] = None):
        self.parent = parent
        self.question_data = question_data
        self.title_action = title_action
        self.answer_var = tk.StringVar()
        self.multi_vars = []
        self.short_text_widget = None
        
    def create_question_frame(self) -> tk.Frame:
        """创建题目显示框架"""
        tc = get_theme_colors()
        frame = tk.Frame(self.parent, bg=tc["card_bg"], relief='solid', bd=1,
                         highlightbackground=tc["card_border"])
        
        # 题目标题
        title_frame = tk.Frame(frame, bg=tc["header_bg"], height=40)
        title_frame.pack(fill='x', padx=2, pady=2)
        title_frame.pack_propagate(False)
        
        title_text = f"第{self.question_data.get('index', 1)}题 ({self.question_data.get('type_name', '未知')})"
        if self.question_data.get('show_id', False):
            title_text += f" [ID: {self.question_data.get('id', 0)}]"
        
        tk.Label(title_frame, text=title_text, font=BOLD_FONT,
                 background=tc["header_bg"], foreground=tc["header_fg"]).pack(side='left', padx=10, pady=8)

        if self.title_action:
            self.title_action(title_frame)
        
        # 题目内容
        content_frame = tk.Frame(frame, bg=tc["card_bg"])
        content_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 题目文本
        question_text = tk.Text(content_frame, height=3, wrap=tk.WORD, font=DEFAULT_FONT,
                               relief='flat', bd=0, bg=tc["card_bg"], fg=tc["text"],
                               insertbackground=tc["text"])
        question_text.pack(fill='x', pady=(0, 10))
        question_text.insert('1.0', self.question_data.get('question', ''))
        question_text.config(state='disabled')
        
        # 选项区域
        self.create_options(content_frame)
        
        return frame
    
    def create_options(self, parent):
        """创建选项区域"""
        question_type = self.question_data.get('type', 'single')
        options = self.question_data.get('options', [])
        
        if question_type == 'single':
            self.create_single_choice_options(parent, options)
        elif question_type in ['judge', 'judgement']:
            self.create_judge_options(parent)
        elif question_type == 'multiple':
            self.create_multiple_choice_options(parent, options)
        elif question_type == 'short':
            self.create_short_answer_input(parent)
        elif question_type == 'fill':
            self.create_fill_blank_input(parent)
    
    def create_single_choice_options(self, parent, options: List[str]):
        """创建单选选项"""
        tc = get_theme_colors()
        options_frame = tk.Frame(parent, bg=tc["card_bg"])
        options_frame.pack(fill='x', pady=5)
        
        for option in options:
            option_letter = option[0] if option else ''
            option_text = option[3:] if len(option) > 3 else option
            
            # 创建选项容器，支持文本换行
            option_container = tk.Frame(options_frame, bg=tc["card_bg"])
            option_container.pack(fill='x', pady=2)
            
            # 单选按钮（显示选项字母）
            rb = ttk.Radiobutton(option_container, text=f"{option_letter}.", 
                               variable=self.answer_var, value=option_letter)
            rb.pack(side='left', anchor='n')
            
            # 选项文本（支持换行，只显示选项内容）
            option_label = tk.Label(option_container, text=option_text,
                                  font=DEFAULT_FONT, bg=tc["card_bg"], fg=tc["text"], anchor='w', justify='left',
                                  wraplength=650)
            option_label.pack(side='left', fill='x', expand=True, padx=(5, 0))
            
            # 点击文本也能选中选项
            option_label.bind("<Button-1>", lambda e, val=option_letter: self.answer_var.set(val))
    
    def create_judge_options(self, parent):
        """创建判断题选项"""
        tc = get_theme_colors()
        options_frame = tk.Frame(parent, bg=tc["card_bg"])
        options_frame.pack(fill='x', pady=5)
        
        # 正确选项
        rb_true = ttk.Radiobutton(options_frame, text="正确",
                                 variable=self.answer_var, value="A")
        rb_true.pack(anchor='w', pady=2)
        
        # 错误选项
        rb_false = ttk.Radiobutton(options_frame, text="错误",
                                  variable=self.answer_var, value="B")
        rb_false.pack(anchor='w', pady=2)
    
    def create_multiple_choice_options(self, parent, options: List[str]):
        """创建多选选项"""
        tc = get_theme_colors()
        options_frame = tk.Frame(parent, bg=tc["card_bg"])
        options_frame.pack(fill='x', pady=5)
        
        for option in options:
            option_letter = option[0] if option else ''
            option_text = option[3:] if len(option) > 3 else option
            
            # 创建选项容器，支持文本换行
            option_container = tk.Frame(options_frame, bg=tc["card_bg"])
            option_container.pack(fill='x', pady=2)
            
            # 复选框（显示选项字母）
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(option_container, text=f"{option_letter}.",
                               variable=var)
            cb.pack(side='left', anchor='n')
            self.multi_vars.append((option_letter, var))
            
            # 选项文本（支持换行，只显示选项内容）
            option_label = tk.Label(option_container, text=option_text,
                                  font=DEFAULT_FONT, bg=tc["card_bg"], fg=tc["text"], anchor='w', justify='left',
                                  wraplength=650)
            option_label.pack(side='left', fill='x', expand=True, padx=(5, 0))
            
            # 点击文本也能选中选项
            option_label.bind("<Button-1>", lambda e, v=var: v.set(not v.get()))
    
    def create_short_answer_input(self, parent):
        """创建简答题输入框"""
        tc = get_theme_colors()
        input_frame = tk.Frame(parent, bg=tc["card_bg"])
        input_frame.pack(fill='x', pady=5)
        
        tk.Label(input_frame, text="请输入答案：", font=BOLD_FONT,
                 bg=tc["card_bg"], fg=tc["text"]).pack(anchor='w')
        self.short_text_widget = tk.Text(input_frame, height=4, wrap=tk.WORD, font=DEFAULT_FONT,
                                         bg=tc["bg_secondary"], fg=tc["text"],
                                         insertbackground=tc["text"])
        self.short_text_widget.pack(fill='x', pady=5)
    
    def create_fill_blank_input(self, parent):
        """创建填空题输入框"""
        tc = get_theme_colors()
        input_frame = tk.Frame(parent, bg=tc["card_bg"])
        input_frame.pack(fill='x', pady=5)
        
        tk.Label(input_frame, text="请填入答案：", font=BOLD_FONT,
                 bg=tc["card_bg"], fg=tc["text"]).pack(anchor='w')
        # 创建单行输入框
        self.fill_entry = tk.Entry(input_frame, font=DEFAULT_FONT,
                                   bg=tc["bg_secondary"], fg=tc["text"],
                                   insertbackground=tc["text"])
        self.fill_entry.pack(fill='x', pady=5)
    
    def get_user_answer(self) -> str:
        """获取用户答案"""
        question_type = self.question_data.get('type', 'single')
        
        if question_type == 'single' or question_type in ['judge', 'judgement']:
            return self.answer_var.get()
        elif question_type == 'multiple':
            selected = []
            for letter, var in self.multi_vars:
                if var.get():
                    selected.append(letter)
            return ''.join(sorted(selected))
        elif question_type == 'short':
            if self.short_text_widget:
                return self.short_text_widget.get('1.0', tk.END).strip()
        elif question_type == 'fill':
            if hasattr(self, 'fill_entry'):
                return self.fill_entry.get().strip()
        
        return ''
    
    def set_user_answer(self, answer: str):
        """设置用户答案"""
        question_type = self.question_data.get('type', 'single')
        
        if question_type == 'single' or question_type in ['judge', 'judgement']:
            self.answer_var.set(answer)
        elif question_type == 'multiple':
            # 清除所有选择
            for letter, var in self.multi_vars:
                var.set(letter in answer)
        elif question_type == 'short':
            if self.short_text_widget:
                self.short_text_widget.delete('1.0', tk.END)
                self.short_text_widget.insert('1.0', answer)
        elif question_type == 'fill':
            if hasattr(self, 'fill_entry'):
                self.fill_entry.delete(0, tk.END)
                self.fill_entry.insert(0, answer)
    
    def clear_answer(self):
        """清除答案"""
        self.answer_var.set('')
        for _, var in self.multi_vars:
            var.set(False)
        if self.short_text_widget:
            self.short_text_widget.delete('1.0', tk.END)
        if hasattr(self, 'fill_entry'):
            self.fill_entry.delete(0, tk.END)


def show_message_dialog(title: str, message: str, dialog_type: str = "info"):
    """显示消息对话框"""
    from tkinter import messagebox
    
    if dialog_type == "info":
        messagebox.showinfo(title, message)
    elif dialog_type == "warning":
        messagebox.showwarning(title, message)
    elif dialog_type == "error":
        messagebox.showerror(title, message)
    elif dialog_type == "question":
        return messagebox.askyesno(title, message)


def _center_window_now(window, width, height):
    import sys
    scaled_width = width
    scaled_height = height

    work_x = 0
    work_y = 0
    work_w = window.winfo_screenwidth()
    work_h = window.winfo_screenheight()
    outer_w = scaled_width
    outer_h = scaled_height

    # Windows: center the decorated outer window, not just Tk's client area.
    if sys.platform == "win32":
        try:
            import ctypes

            class RECT(ctypes.Structure):
                _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                            ("r", ctypes.c_long), ("b", ctypes.c_long)]

            work_rect = RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(work_rect), 0)
            work_x = work_rect.l
            work_y = work_rect.t
            work_w = work_rect.r - work_rect.l
            work_h = work_rect.b - work_rect.t

            hwnd = window.winfo_id()
            try:
                dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            except Exception:
                dpi = ctypes.windll.user32.GetDpiForSystem()
            scale = dpi / 96
            scaled_width = int(round(width * scale))
            scaled_height = int(round(height * scale))
            max_width = max(width, work_w - 40)
            max_height = max(height, work_h - 40)
            scaled_width = min(scaled_width, max_width)
            scaled_height = min(scaled_height, max_height)

            window.geometry(f"{scaled_width}x{scaled_height}")
            window.update_idletasks()

            hwnd = window.winfo_id()
            frame_hwnd = ctypes.windll.user32.GetParent(hwnd) or hwnd
            frame_rect = RECT()
            ctypes.windll.user32.GetWindowRect(frame_hwnd, ctypes.byref(frame_rect))
            outer_w = frame_rect.r - frame_rect.l
            outer_h = frame_rect.b - frame_rect.t
        except Exception:
            window.geometry(f"{scaled_width}x{scaled_height}")
            window.update_idletasks()
    else:
        window.geometry(f"{scaled_width}x{scaled_height}")
        window.update_idletasks()

    x = work_x + max(0, (work_w - outer_w) // 2)
    y = work_y + max(0, (work_h - outer_h) // 2)
    window.geometry(f"{scaled_width}x{scaled_height}+{x}+{y}")


def center_window(window, width, height):
    """按 DPI 缩放后的实际窗口尺寸居中显示窗口。"""
    _center_window_now(window, width, height)

    try:
        window.after_idle(lambda: _center_window_now(window, width, height))
    except Exception:
        pass
