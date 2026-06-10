#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 组件模块 — 通用 UI 组件和工具函数
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import List, Dict, Any, Callable, Optional
from core.config import DEFAULT_FONT, BOLD_FONT, COLORS, LAYOUT, get_theme_colors


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


class AnswerStatusPanel:
    """答题状态面板组件"""
    
    def __init__(self, parent, total_questions: int = 0):
        self.parent = parent
        self.total_questions = total_questions
        self.buttons = []
    
    def create_panel(self) -> tk.Frame:
        """创建状态面板"""
        tc = get_theme_colors()
        frame = tk.Frame(self.parent, bg=tc["card_bg"], relief='solid', bd=1,
                         highlightbackground=tc["card_border"])
        
        # 标题
        title_label = tk.Label(frame, text="答题状态", font=BOLD_FONT,
                               bg=tc["card_bg"], fg=tc["text"])
        title_label.pack(pady=5)
        
        # 创建状态按钮
        self.create_status_buttons(frame)
        
        return frame
    
    def create_status_buttons(self, parent):
        """创建状态按钮"""
        tc = get_theme_colors()
        buttons_frame = tk.Frame(parent, bg=tc["card_bg"])
        buttons_frame.pack(fill='x', padx=5, pady=5)
        
        # 计算每行按钮数量
        buttons_per_row = 10
        current_row = None
        
        for i in range(self.total_questions):
            if i % buttons_per_row == 0:
                current_row = tk.Frame(buttons_frame, bg=tc["card_bg"])
                current_row.pack(fill='x', pady=1)
            
            btn = tk.Button(current_row, text=str(i + 1), width=3, height=1,
                          font=('Arial', 8), relief='raised')
            btn.pack(side='left', padx=1)
            self.buttons.append(btn)
    
    def update_button_status(self, answered: List[bool], correct: List[bool]):
        """更新按钮状态"""
        for i, btn in enumerate(self.buttons):
            if i < len(answered) and answered[i]:
                if i < len(correct) and correct[i]:
                    btn.config(bg='green', fg='white')
                else:
                    btn.config(bg='red', fg='white')
            else:
                tc = get_theme_colors()
                btn.config(bg=tc["bg_secondary"], fg=tc["text"])


class TimerDisplay:
    """计时器显示组件"""
    
    def __init__(self, parent):
        self.parent = parent
        self.remaining_seconds = 0
        self.time_label = None
        
    def create_timer(self) -> tk.Frame:
        """创建计时器"""
        tc = get_theme_colors()
        frame = tk.Frame(self.parent, bg=tc["card_bg"], relief='solid', bd=1,
                         highlightbackground=tc["card_border"])
        
        tk.Label(frame, text="剩余时间:", font=BOLD_FONT,
                 bg=tc["card_bg"], fg=tc["text"]).pack(pady=5)
        self.time_label = tk.Label(frame, text="00:00", font=('Arial', 24, 'bold'),
                                   bg=tc["card_bg"], fg=tc["success"])
        self.time_label.pack(pady=5)
        
        return frame
    
    def update_time(self, remaining_seconds: int):
        """更新时间显示"""
        self.remaining_seconds = remaining_seconds
        
        if remaining_seconds <= 0:
            time_text = "00:00"
            color = get_theme_colors()["danger"]
        else:
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            time_text = f"{minutes:02d}:{seconds:02d}"
            
            if remaining_seconds <= 300:  # 5分钟内显示红色
                color = get_theme_colors()["danger"]
            elif remaining_seconds <= 600:  # 10分钟内显示橙色
                color = get_theme_colors()["warning"]
            else:
                color = get_theme_colors()["success"]
        
        if self.time_label:
            self.time_label.config(text=time_text, fg=color)
    
    def is_time_up(self) -> bool:
        """检查时间是否已到"""
        return self.remaining_seconds <= 0


class StatisticsDisplay:
    """统计信息显示组件"""
    
    def __init__(self, parent):
        self.parent = parent
        self.stats_labels = {}
        
    def create_stats_panel(self) -> tk.Frame:
        """创建统计面板"""
        tc = get_theme_colors()
        frame = tk.Frame(self.parent, bg=tc["card_bg"], relief='solid', bd=1,
                         highlightbackground=tc["card_border"])
        
        tk.Label(frame, text="统计信息", font=BOLD_FONT,
                 bg=tc["card_bg"], fg=tc["text"]).pack(pady=5)
        
        # 统计信息容器
        stats_container = tk.Frame(frame, bg=tc["card_bg"])
        stats_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        return frame
    
    def update_stats(self, stats: Dict[str, Any]):
        """更新统计信息"""
        # 清除旧的标签
        for label in self.stats_labels.values():
            label.destroy()
        self.stats_labels.clear()
        
        # 创建新的统计标签
        row = 0
        for key, value in stats.items():
            if key in ['total_questions', 'answered_count', 'correct_count', 'accuracy']:
                label_text = self.get_stats_label_text(key, value)
                tc = get_theme_colors()
                label = tk.Label(self.parent, text=label_text, font=DEFAULT_FONT,
                                 bg=tc["card_bg"], fg=tc["text"])
                label.pack(anchor='w', padx=10, pady=2)
                self.stats_labels[key] = label
                row += 1
    
    def get_stats_label_text(self, key: str, value: Any) -> str:
        """获取统计标签文本"""
        label_map = {
            'total_questions': f"总题数: {value}",
            'answered_count': f"已答题: {value}",
            'correct_count': f"正确数: {value}",
            'accuracy': f"正确率: {value:.1f}%"
        }
        return label_map.get(key, f"{key}: {value}")


def create_button_group(parent, buttons_config: List[Dict[str, Any]]) -> tk.Frame:
    """创建按钮组"""
    frame = tk.Frame(parent, bg=get_theme_colors()["bg"])
    
    for config in buttons_config:
        btn = ttk.Button(frame, 
                        text=config.get('text', ''),
                        command=config.get('command'),
                        width=config.get('width', LAYOUT['button_width']))
        
        if config.get('pack_side'):
            btn.pack(side=config['pack_side'], padx=LAYOUT['small_padding'])
        else:
            btn.pack(pady=LAYOUT['small_padding'])
    
    return frame


def create_info_panel(parent, title: str, content: str) -> tk.Frame:
    """创建信息面板"""
    tc = get_theme_colors()
    frame = tk.Frame(parent, bg=tc["card_bg"], relief='solid', bd=1,
                     highlightbackground=tc["card_border"])
    
    # 标题
    title_label = tk.Label(frame, text=title, font=BOLD_FONT,
                           bg=tc["card_bg"], fg=tc["text"])
    title_label.pack(pady=5)
    
    # 内容
    content_label = tk.Label(frame, text=content, font=DEFAULT_FONT, wraplength=300,
                             bg=tc["card_bg"], fg=tc["text"])
    content_label.pack(padx=10, pady=5)
    
    return frame


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
