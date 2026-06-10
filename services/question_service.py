#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题目服务模块 - 处理题目相关的业务逻辑
"""

import random
from typing import List, Optional, Dict, Any
from core.models import Question, QuestionBank, PracticeSession
from core.utils import validate_answer, get_question_type_name, shuffle_questions


class QuestionService:
    """题目服务类"""
    
    def __init__(self):
        self.question_bank: Optional[QuestionBank] = None
        self.practice_session: Optional[PracticeSession] = None
    
    def set_question_bank(self, question_bank: QuestionBank):
        """设置题库"""
        self.question_bank = question_bank
    
    def start_practice_session(self, question_type: str = "all", collected_only: bool = False) -> PracticeSession:
        """开始练习会话"""
        if not self.question_bank:
            raise ValueError("未加载题库")
        
        questions = self.question_bank.get_questions_by_type_and_collected(question_type, collected_only)
        if not questions:
            if question_type == "judge":
                questions = self.question_bank.get_questions_by_type_and_collected("judgement", collected_only)
            elif question_type == "short":
                questions = self.question_bank.get_questions_by_type_and_collected("essay", collected_only)
                if not questions:
                    questions = self.question_bank.get_questions_by_type_and_collected("fill", collected_only)
        
        if not questions:
            raise ValueError(f"没有找到{get_question_type_name(question_type)}题目")
        
        self.practice_session = PracticeSession(
            questions=questions,
            selected_type=question_type
        )
        return self.practice_session
    
    def get_current_question(self) -> Optional[Question]:
        """获取当前题目"""
        if not self.practice_session or not self.practice_session.questions:
            return None
        
        if 0 <= self.practice_session.current_question_index < len(self.practice_session.questions):
            return self.practice_session.questions[self.practice_session.current_question_index]
        return None
    
    def get_current_question_index(self) -> int:
        """获取当前题目在原题库中的索引"""
        if not self.practice_session:
            return -1
        
        current_question = self.get_current_question()
        if not current_question:
            return -1
        
        # 在原题库中查找当前题目的索引
        for i, question in enumerate(self.question_bank.questions):
            if question.id == current_question.id:
                return i
        
        return -1
    
    def submit_answer(self, user_answer: str) -> Dict[str, Any]:
        """提交答案"""
        if not self.practice_session:
            raise ValueError("未开始练习会话")
        
        current_question = self.get_current_question()
        if not current_question:
            raise ValueError("没有当前题目")
        
        is_correct = validate_answer(current_question, user_answer)
        
        if is_correct:
            self.practice_session.add_correct_answer()
        else:
            self.practice_session.add_wrong_answer(current_question.id)
        
        return {
            "is_correct": is_correct,
            "correct_answer": current_question.answer,
            "explanation": current_question.explanation,
            "question_id": current_question.id
        }
    
    def next_question(self) -> bool:
        """下一题"""
        if not self.practice_session:
            return False
        
        if self.practice_session.current_question_index < len(self.practice_session.questions) - 1:
            self.practice_session.current_question_index += 1
            self.practice_session.showing_answer = False
            return True
        return False
    
    def prev_question(self) -> bool:
        """上一题"""
        if not self.practice_session:
            return False
        
        if self.practice_session.current_question_index > 0:
            self.practice_session.current_question_index -= 1
            self.practice_session.showing_answer = False
            return True
        return False
    
    def random_question(self) -> bool:
        """随机题目"""
        if not self.practice_session or not self.practice_session.questions:
            return False
        
        current_index = self.practice_session.current_question_index
        available_indices = [i for i in range(len(self.practice_session.questions)) if i != current_index]
        
        if available_indices:
            self.practice_session.current_question_index = random.choice(available_indices)
            self.practice_session.showing_answer = False
            return True
        return False
    
    def jump_to_question(self, index: int) -> bool:
        """跳转到指定题目"""
        if not self.practice_session:
            return False
        
        if 0 <= index < len(self.practice_session.questions):
            self.practice_session.current_question_index = index
            self.practice_session.showing_answer = False
            return True
        return False
    
    def search_question_by_id(self, question_id: int) -> Optional[Question]:
        """根据ID搜索题目"""
        if not self.question_bank:
            return None
        return self.question_bank.get_question_by_id(question_id)
    
    def jump_to_question_by_id(self, question_id: int) -> bool:
        """根据ID跳转到题目"""
        if not self.practice_session:
            return False
        
        for i, question in enumerate(self.practice_session.questions):
            if question.id == question_id:
                self.practice_session.current_question_index = i
                self.practice_session.showing_answer = False
                return True
        return False
    
    def get_wrong_questions(self) -> List[Question]:
        """获取错题列表"""
        if not self.practice_session or not self.question_bank:
            return []
        
        wrong_questions = []
        for question_id in self.practice_session.wrong_questions:
            question = self.question_bank.get_question_by_id(question_id)
            if question:
                wrong_questions.append(question)
        return wrong_questions
    
    def start_wrong_question_review(self) -> bool:
        """开始错题复习"""
        wrong_questions = self.get_wrong_questions()
        return self.start_review_session(wrong_questions, "wrong")

    def start_review_session(self, questions: List[Question], selected_type: str = "wrong") -> bool:
        """使用指定题目列表开始复习会话。"""
        if not questions:
            return False

        self.practice_session = PracticeSession(
            questions=list(questions),
            selected_type=selected_type
        )
        return True
    
    def get_practice_statistics(self) -> Dict[str, Any]:
        """获取练习统计信息"""
        if not self.practice_session:
            return {}
        
        return {
            "total_questions": len(self.practice_session.questions),
            "current_index": self.practice_session.current_question_index + 1,
            "answered_count": self.practice_session.answered_count,
            "correct_count": self.practice_session.correct_count,
            "wrong_count": len(self.practice_session.wrong_questions),
            "accuracy": self.practice_session.get_accuracy(),
            "selected_type": self.practice_session.selected_type,
            "showing_answer": self.practice_session.showing_answer,
            "bank_total": len(self.question_bank.questions) if self.question_bank else 0
        }
    
    def reset_practice_statistics(self):
        """重置练习统计"""
        if self.practice_session:
            self.practice_session.reset_stats()
    
    def toggle_answer_display(self):
        """切换答案显示状态"""
        if self.practice_session:
            self.practice_session.showing_answer = not self.practice_session.showing_answer
    
    def get_question_bank_info(self) -> Dict[str, Any]:
        """获取题库信息"""
        if not self.question_bank:
            return {}
        
        type_distribution = self.question_bank.get_type_distribution()
        type_info = {}
        
        for question_type, count in type_distribution.items():
            type_info[get_question_type_name(question_type)] = count
        
        return {
            "total_questions": len(self.question_bank.questions),
            "type_distribution": type_info,
            "file_path": self.question_bank.file_path
        }
    
    def search_questions(self, keyword: str) -> List[Question]:
        """搜索题目"""
        if not self.question_bank:
            return []
        return self.question_bank.search_questions(keyword)
    
    def filter_questions_by_type(self, question_type: str) -> List[Question]:
        """按题型筛选题目"""
        if not self.question_bank:
            return []
        return self.question_bank.get_questions_by_type(question_type)
    
    def shuffle_current_questions(self):
        """打乱当前题目顺序"""
        if self.practice_session and self.practice_session.questions:
            current_question = self.get_current_question()
            self.practice_session.questions = shuffle_questions(self.practice_session.questions)
            
            # 重新定位当前题目
            if current_question:
                for i, question in enumerate(self.practice_session.questions):
                    if question.id == current_question.id:
                        self.practice_session.current_question_index = i
                        break
                else:
                    self.practice_session.current_question_index = 0
