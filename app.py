#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用主控制器 - 协调各个模块的交互
"""

import sys
from typing import Optional
from core.models import QuestionBank


def _enable_windows_dpi_awareness():
    """Enable DPI-aware geometry on Windows before Tk is initialized."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # PROCESS_SYSTEM_DPI_AWARE keeps Tk and Win32 geometry in physical pixels.
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


_enable_windows_dpi_awareness()

import tkinter as tk
from ui.main_window import MainWindow
from ui.practice_mode import PracticeModeWindow
from ui.exam_mode import ExamModeWindow


class QuizApplication:
    """灵测 LingCe — 通用考试练习系统主控制器"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        try:
            self.root.attributes("-alpha", 0)
        except Exception:
            pass
        self.current_window = None
        self.question_bank: Optional[QuestionBank] = None
        
        # 创建主窗口
        self.main_window = MainWindow(self.root)
        self.main_window.set_callbacks(
            practice_callback=self.start_practice_mode,
            exam_callback=self.start_exam_mode
        )
        
        self.current_window = self.main_window
        self.root.after_idle(self._show_main_window)

    def _show_main_window(self):
        """Show the main window after initial layout has settled."""
        from ui.components import center_window

        self.root.deiconify()
        center_window(self.root, 1100, 750)
        self.root.after(50, self._finish_startup)

    def _finish_startup(self):
        """Finish startup after the window is centered and visible."""
        from ui.components import center_window

        center_window(self.root, 1100, 750)
        try:
            self.root.attributes("-alpha", 1)
        except Exception:
            pass
        self.root.after(100, self.main_window._try_auto_load)
    
    def start_practice_mode(self, question_bank: QuestionBank):
        """启动练习模式"""
        self.question_bank = question_bank
        
        practice_window = PracticeModeWindow(self.root, question_bank)
        practice_window.set_return_callback(self.return_to_main)
        # 设置错题记录回调
        practice_window.set_wrong_questions_callback(self.main_window.add_wrong_questions)
        
        self.current_window = practice_window
    
    def start_exam_mode(self, question_bank: QuestionBank):
        """启动考试模式"""
        self.question_bank = question_bank
        
        try:
            # 创建考试窗口实例
            exam_window = ExamModeWindow(self.root, question_bank)
            
            # 显示考试说明并确认是否开始
            if exam_window.show_exam_instructions():
                # 用户确认开始考试，创建考试界面
                if exam_window.start_exam():
                    exam_window.set_return_callback(self.return_to_main)
                    # 设置错题记录回调
                    exam_window.set_wrong_questions_callback(self.main_window.add_wrong_questions)
                    self.current_window = exam_window
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("错误", f"启动考试模式失败：{str(e)}")

    def return_to_main(self):
        """返回主界面"""
        # 保持题库状态，不需要重新加载
        if self.question_bank:
            # 重新设置题库到主窗口的文件服务中
            self.main_window.file_service.question_bank = self.question_bank
            self.main_window.file_service.current_file_path = self.question_bank.file_path
        
        self.main_window.return_to_main()
        
        # 如果有题库，重新显示题库信息
        if self.question_bank:
            self.main_window.update_question_bank_info(self.question_bank)
            self.main_window.enable_function_buttons()
        
        self.current_window = self.main_window
    
    def run(self):
        """运行应用程序"""
        self.root.mainloop()


def main():
    """程序入口"""
    app = QuizApplication()
    app.run()


if __name__ == "__main__":
    main()
