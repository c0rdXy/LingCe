#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编辑功能模块 - 题目编辑相关功能
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from pathlib import Path
from ui.components import show_message_dialog
from core.config import get_font


def create_edit_interface(parent_window, current_question, type_var_callback, format_label_callback):
    """创建编辑界面"""
    if not current_question:
        return None, None, None, None, None, None, None, None
    
    # 创建独立的编辑窗口
    edit_window = tk.Toplevel(parent_window)
    edit_window.title("编辑题目")
    edit_window.geometry("800x700")
    edit_window.transient(parent_window)
    edit_window.grab_set()
    
    # 创建滚动框架
    canvas = tk.Canvas(edit_window)
    scrollbar = ttk.Scrollbar(edit_window, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    q = current_question
    
    # 题目ID显示
    id_frame = ttk.Frame(scrollable_frame)
    id_frame.pack(fill='x', padx=10, pady=5)
    ttk.Label(id_frame, text=f"题目ID: {q.id}", font=get_font(10)).pack(side='left')
    
    # 题目类型选择
    type_frame = ttk.Frame(scrollable_frame)
    type_frame.pack(fill='x', padx=10, pady=5)
    ttk.Label(type_frame, text="题目类型:", font=get_font(12, "bold")).pack(side='left')
    
    # 题目类型映射
    type_mapping = {
        'single': '单选题',
        'multiple': '多选题', 
        'judge': '判断题',
        'fill': '填空题',
        'short': '简答题'
    }
    
    reverse_type_mapping = {v: k for k, v in type_mapping.items()}
    
    # 显示中文类型
    current_type_chinese = type_mapping.get(q.type, q.type)
    type_var = tk.StringVar(value=current_type_chinese)
    type_combo = ttk.Combobox(type_frame, textvariable=type_var, 
                             values=list(type_mapping.values()),
                             state='readonly', width=15)
    type_combo.pack(side='left', padx=10)
    
    # 答案格式提示
    format_label = ttk.Label(scrollable_frame, text="", font=get_font(10), foreground='blue')
    format_label.pack(fill='x', padx=10, pady=5)
    format_label_callback(format_label, type_var.get())
    
    def on_type_change_wrapper(event=None):
        type_var_callback(format_label, type_var.get())
    
    type_combo.bind('<<ComboboxSelected>>', on_type_change_wrapper)
    
    # 题目内容编辑
    ttk.Label(scrollable_frame, text="题目内容:", font=get_font(12, "bold")).pack(anchor='w', padx=10, pady=5)
    question_edit = scrolledtext.ScrolledText(scrollable_frame, height=6, font=get_font(11))
    question_edit.pack(fill='x', padx=10, pady=5)
    question_edit.insert('1.0', q.question)
    
    # 选项编辑
    ttk.Label(scrollable_frame, text="选项 (每行一个选项，格式：A. 选项内容):", font=get_font(12, "bold")).pack(anchor='w', padx=10, pady=5)
    options_edit = scrolledtext.ScrolledText(scrollable_frame, height=8, font=get_font(11))
    options_edit.pack(fill='x', padx=10, pady=5)
    
    if q.options:
        options_text = '\n'.join(q.options)
        options_edit.insert('1.0', options_text)
    
    # 答案编辑
    ttk.Label(scrollable_frame, text="答案:", font=get_font(12, "bold")).pack(anchor='w', padx=10, pady=5)
    answer_edit = tk.Entry(scrollable_frame, font=get_font(11))
    answer_edit.pack(fill='x', padx=10, pady=5)
    answer_edit.insert(0, str(q.answer))
    
    # 解析编辑
    ttk.Label(scrollable_frame, text="解析:", font=get_font(12, "bold")).pack(anchor='w', padx=10, pady=5)
    explanation_edit = scrolledtext.ScrolledText(scrollable_frame, height=6, font=get_font(11))
    explanation_edit.pack(fill='x', padx=10, pady=5)
    explanation_edit.insert('1.0', q.explanation)
    
    # 按钮区域
    button_frame = ttk.Frame(scrollable_frame)
    button_frame.pack(fill='x', padx=10, pady=20)
    
    return edit_window, type_var, question_edit, options_edit, answer_edit, explanation_edit, button_frame, format_label


def update_answer_format_hint(format_label, question_type):
    """更新答案格式提示"""
    # 支持中文和英文类型
    type_hints = {
        'single': '答案格式：单个字母，如：A',
        'multiple': '答案格式：多个字母，如：ABC',
        'judge': '答案格式：√ 或 ×',
        'fill': '答案格式：填空内容，如：网络安全',
        'short': '答案格式：简答内容或要点',
        '单选题': '答案格式：单个字母，如：A',
        '多选题': '答案格式：多个字母，如：ABC',
        '判断题': '答案格式：√ 或 ×',
        '填空题': '答案格式：填空内容，如：网络安全',
        '简答题': '答案格式：简答内容或要点'
    }
    
    hint_text = type_hints.get(question_type, '')
    format_label.config(text=hint_text)


def save_edit_changes(current_question, type_var, question_edit, options_edit, answer_edit, explanation_edit):
    """保存编辑修改"""
    if not current_question:
        return False
    
    try:
        # 题目类型映射（中文转英文）
        reverse_type_mapping = {
            '单选题': 'single',
            '多选题': 'multiple', 
            '判断题': 'judge',
            '填空题': 'fill',
            '简答题': 'short'
        }
        
        # 保存编辑内容
        chinese_type = type_var.get()
        current_question.type = reverse_type_mapping.get(chinese_type, chinese_type)
        current_question.question = question_edit.get('1.0', 'end-1c')
        
        options_text = options_edit.get('1.0', 'end-1c')
        current_question.options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
        
        current_question.answer = answer_edit.get()
        current_question.explanation = explanation_edit.get('1.0', 'end-1c')
        
        return True
    except Exception as e:
        show_message_dialog("错误", f"保存修改失败：{str(e)}", "error")
        return False


def save_question_bank_to_file(question_bank, force_dialog=False):
    """保存题库到文件"""
    try:
        from services.file_service import FileService
        
        if not question_bank:
            show_message_dialog("错误", "没有加载的题库", "error")
            return False
        
        file_service = FileService()
        
        # 如果有原始文件路径且不强制显示对话框，直接保存到原文件
        if not force_dialog and hasattr(question_bank, 'file_path') and question_bank.file_path:
            try:
                if file_service.save_question_bank(question_bank, question_bank.file_path):
                    show_message_dialog("成功", f"题库已保存到原文件: {question_bank.file_path}", "info")
                    return True
            except Exception as e:
                show_message_dialog("警告", f"保存到原文件失败: {str(e)}，将提示选择新文件", "warning")
        
        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            title="保存题库文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialdir="题库文件" if Path("题库文件").exists() else "."
        )
        
        if file_path:
            if file_service.save_question_bank(question_bank, file_path):
                show_message_dialog("成功", f"题库已保存到: {file_path}", "info")
                return True
        return False
    except Exception as e:
        show_message_dialog("错误", f"保存题库失败: {str(e)}", "error")
        return False