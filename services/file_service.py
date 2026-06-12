#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件服务模块 - 处理文件导入导出相关功能
"""

import json
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, Dict, Any, List
from core.models import QuestionBank, Question
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
    
    def validate_question_data(self, data: List[Dict[str, Any]]) -> List[str]:
        """验证题目数据格式"""
        errors = []
        
        for i, item in enumerate(data):
            question_num = i + 1
            
            # 检查必需字段
            if 'question' not in item or not item['question'].strip():
                errors.append(f"第{question_num}题：缺少题目内容")
            
            if 'type' not in item:
                errors.append(f"第{question_num}题：缺少题目类型")
            elif item['type'] not in ['single', 'multiple', 'judge', 'judgement', 'fill', 'short', 'essay']:
                errors.append(f"第{question_num}题：题目类型无效")
            
            if 'answer' not in item or not item['answer'].strip():
                errors.append(f"第{question_num}题：缺少答案")
            
            # 检查选择题选项
            if item.get('type') in ['single', 'multiple']:
                if 'options' not in item or not item['options']:
                    errors.append(f"第{question_num}题：选择题缺少选项")
                elif len(item['options']) < 2:
                    errors.append(f"第{question_num}题：选择题选项不足")
        
        return errors
    
    def import_questions_from_json(self, file_path: str) -> Optional[QuestionBank]:
        """从JSON文件导入题目"""
        try:
            with open(file_path, 'r', encoding=FILE_CONFIG["encoding"]) as f:
                data = json.load(f)
            
            # 验证数据格式
            if not isinstance(data, list):
                raise ValueError("JSON文件格式错误：应为题目数组")
            
            errors = self.validate_question_data(data)
            if errors:
                error_msg = "数据验证失败：\n" + "\n".join(errors[:10])  # 只显示前10个错误
                if len(errors) > 10:
                    error_msg += f"\n... 还有 {len(errors) - 10} 个错误"
                raise ValueError(error_msg)
            
            # 转换为Question对象
            questions = []
            for i, item in enumerate(data):
                question = Question(
                    id=item.get('id', i + 1),
                    type=item['type'],
                    question=item['question'],
                    options=item.get('options', []),
                    answer=item['answer'],
                    explanation=item.get('explanation', '')
                )
                questions.append(question)
            
            return QuestionBank(questions=questions, file_path=file_path)
            
        except Exception as e:
            raise Exception(f"导入失败：{str(e)}")
    
    def create_sample_question_file(self, file_path: str):
        """创建示例题目文件"""
        sample_questions = [
            {
                "id": 1,
                "type": "single",
                "question": "以下哪个选项是通用的考试练习模式？",
                "options": ["A. 练习模式", "B. 考试模式", "C. 错题复习", "D. 以上都是"],
                "answer": "D",
                "explanation": "灵测支持练习模式、考试模式、错题复习等多种学习方式。"
            },
            {
                "id": 2,
                "type": "multiple",
                "question": "以下哪些是灵测支持的功能？",
                "options": ["A. 练习模式", "B. 考试模式", "C. 错题集", "D. 统计图表"],
                "answer": "ABCD",
                "explanation": "灵测支持练习模式、考试模式、错题集管理、统计图表等功能。"
            },
            {
                "id": 3,
                "type": "judgement",
                "question": "灵测支持单选、多选、判断、填空、简答等多种题型。",
                "options": ["A. 正确", "B. 错误"],
                "answer": "A",
                "explanation": "灵测支持单选、多选、判断、填空、简答等多种题型，覆盖常见考试场景。"
            },
            {
                "id": 4,
                "type": "fill",
                "question": "灵测的项目英文名是：______。",
                "options": [],
                "answer": "LingCe",
                "explanation": "灵测的英文名称为 LingCe，取自「灵」（灵活）和「测」（测试）的组合。"
            },
            {
                "id": 5,
                "type": "short",
                "question": "请简述灵测的主要功能。",
                "options": [],
                "answer": "灵测主要功能包括：题库管理、练习模式、考试模式、错题集管理、学习统计等，支持导入自定义题库。",
                "explanation": "灵测是一个通用的考试练习系统，适用于各类考试场景。"
            }
        ]
        
        try:
            with open(file_path, 'w', encoding=FILE_CONFIG["encoding"]) as f:
                json.dump(sample_questions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise Exception(f"创建示例文件失败：{str(e)}")
