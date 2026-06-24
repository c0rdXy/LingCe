#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件服务模块 - 处理文件导入导出相关功能
"""

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, Dict, Any, List
from core.models import QuestionBank
from core.utils import load_questions_from_file, save_questions_to_file
from core.config import FILE_CONFIG, QUESTION_BANK_DIR


class FileService:
    """文件服务类"""
    
    def __init__(self):
        self.current_file_path: Optional[str] = None
        self.question_bank: Optional[QuestionBank] = None

    @staticmethod
    def _question_bank_dir() -> Path:
        QUESTION_BANK_DIR.mkdir(parents=True, exist_ok=True)
        return QUESTION_BANK_DIR
    
    def load_question_bank(self, file_path: Optional[str] = None, show_messages: bool = True) -> Optional[QuestionBank]:
        """加载题库文件"""
        try:
            if not file_path:
                file_path = filedialog.askopenfilename(
                    title="选择题库文件",
                    filetypes=FILE_CONFIG["supported_formats"],
                    initialdir=str(self._question_bank_dir()),
                )
            
            if not file_path:
                return None
            
            self.question_bank = load_questions_from_file(file_path)
            self.current_file_path = file_path
            
            if show_messages:
                messagebox.showinfo("成功", f"成功加载 {len(self.question_bank.questions)} 道题目")
            return self.question_bank
            
        except Exception as e:
            if show_messages:
                messagebox.showerror("错误", f"加载题库失败：{str(e)}")
            return None
    
    def save_question_bank(self, question_bank: QuestionBank, file_path: Optional[str] = None) -> bool:
        """保存题库文件"""
        try:
            if not file_path:
                file_path = filedialog.asksaveasfilename(
                    title="保存题库文件",
                    defaultextension=".json",
                    filetypes=FILE_CONFIG["supported_formats"],
                    initialdir=str(self._question_bank_dir()),
                )
            
            if not file_path:
                return False
            
            save_questions_to_file(question_bank, file_path)
            messagebox.showinfo("成功", "题库保存成功")
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"保存题库失败：{str(e)}")
            return False
    
    def export_wrong_questions(self, question_bank: QuestionBank, wrong_question_ids: List[int]) -> bool:
        """导出错题集"""
        try:
            if not wrong_question_ids:
                messagebox.showwarning("提示", "没有错题可导出")
                return False
            
            file_path = filedialog.asksaveasfilename(
                title="导出错题集",
                defaultextension=".json",
                filetypes=FILE_CONFIG["supported_formats"],
                initialfile="错题集.json",
                initialdir=str(self._question_bank_dir()),
            )
            
            if not file_path:
                return False
            
            wrong_questions = [q for q in question_bank.questions if q.id in wrong_question_ids]
            wrong_bank = QuestionBank(questions=wrong_questions)
            save_questions_to_file(wrong_bank, file_path)
            
            messagebox.showinfo("成功", f"成功导出 {len(wrong_questions)} 道错题")
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"导出错题集失败：{str(e)}")
            return False
    
    def get_file_info(self) -> Dict[str, Any]:
        """获取当前文件信息"""
        if not self.current_file_path or not self.question_bank:
            return {}
        
        return {
            "file_path": self.current_file_path,
            "file_name": Path(self.current_file_path).name,
            "question_count": len(self.question_bank.questions),
            "type_distribution": self.question_bank.get_type_distribution()
        }
