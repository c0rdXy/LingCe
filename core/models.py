#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型 - 题目和考试相关的数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class Question:
    """题目数据模型"""
    id: int
    type: str  # single, multiple, judge, short
    question: str
    options: List[str] = field(default_factory=list)
    answer: str = ""
    explanation: str = ""
    is_collected: bool = False
    
    def is_single_choice(self) -> bool:
        """是否为单选题"""
        return self.type == "single"
    
    def is_multiple_choice(self) -> bool:
        """是否为多选题"""
        return self.type == "multiple"
    
    def is_judge(self) -> bool:
        """是否为判断题"""
        return self.type == "judge"
    
    def is_short_answer(self) -> bool:
        """是否为简答题"""
        return self.type == "short"
    
    def get_correct_options(self) -> List[str]:
        """获取正确选项列表（用于多选题）"""
        if self.is_multiple_choice():
            return list(self.answer.upper())
        return [self.answer.upper()] if self.answer else []


@dataclass
class ExamAnswer:
    """考试答案数据模型"""
    question_id: int
    user_answer: str = ""
    is_correct: bool = False
    time_spent: float = 0.0  # 答题用时（秒）
    
    def set_answer(self, answer: str):
        """设置用户答案"""
        self.user_answer = answer


@dataclass
class ExamSession:
    """考试会话数据模型"""
    questions: List[Question] = field(default_factory=list)
    answers: Dict[int, ExamAnswer] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    time_limit: int = 90  # 考试时长（分钟）
    current_question_index: int = 0
    is_submitted: bool = False
    
    def get_duration(self) -> float:
        """获取考试用时（分钟）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return 0.0
    
    def get_score(self) -> float:
        """计算考试得分"""
        if not self.questions:
            return 0.0
        
        correct_count = sum(1 for answer in self.answers.values() if answer.is_correct)
        return (correct_count / len(self.questions)) * 100
    
    def get_answer_for_question(self, question_id: int) -> Optional[ExamAnswer]:
        """获取指定题目的答案"""
        return self.answers.get(question_id)
    
    def set_answer_for_question(self, question_id: int, answer: str):
        """设置指定题目的答案"""
        if question_id not in self.answers:
            self.answers[question_id] = ExamAnswer(question_id=question_id)
        self.answers[question_id].set_answer(answer)


@dataclass
class PracticeSession:
    """练习会话数据模型"""
    questions: List[Question] = field(default_factory=list)
    current_question_index: int = 0
    correct_count: int = 0
    answered_count: int = 0
    wrong_questions: List[int] = field(default_factory=list)  # 错题ID列表
    selected_type: str = "all"
    showing_answer: bool = False
    
    def get_accuracy(self) -> float:
        """获取正确率"""
        if self.answered_count == 0:
            return 0.0
        return (self.correct_count / self.answered_count) * 100
    
    def add_correct_answer(self):
        """添加正确答案"""
        self.correct_count += 1
        self.answered_count += 1
    
    def add_wrong_answer(self, question_id: int):
        """添加错误答案"""
        self.answered_count += 1
        if question_id not in self.wrong_questions:
            self.wrong_questions.append(question_id)
    
    def reset_stats(self):
        """重置统计数据"""
        self.correct_count = 0
        self.answered_count = 0
        self.wrong_questions.clear()


@dataclass
class QuestionBank:
    """题库数据模型"""
    questions: List[Question] = field(default_factory=list)
    file_path: Optional[str] = None
    
    def get_questions_by_type(self, question_type: str) -> List[Question]:
        """根据题型筛选题目"""
        if question_type == "all":
            return self.questions
        
        # 直接匹配
        questions = [q for q in self.questions if q.type == question_type]
        
        # 如果没有找到，尝试兼容性匹配
        if not questions:
            if question_type == "judge":
                # 判断题的兼容性匹配
                questions = [q for q in self.questions if q.type in ["judgement", "judge"]]
            elif question_type == "judgement":
                questions = [q for q in self.questions if q.type in ["judge", "judgement"]]
            elif question_type == "short":
                # 简答题的兼容性匹配
                questions = [q for q in self.questions if q.type in ["short", "essay", "fill"]]
            elif question_type == "fill":
                questions = [q for q in self.questions if q.type in ["fill", "short"]]
        
        return questions
    

    def get_collected_questions(self) -> List[Question]:
        # 获取已收藏的题目
        return [q for q in self.questions if q.is_collected]

    def get_questions_by_type_and_collected(self, question_type: str, collected_only: bool = False) -> List[Question]:
        # 根据题型和收藏状态筛选题目
        questions = self.get_collected_questions() if collected_only else self.questions
        if question_type == 'all':
            return questions
        filtered = [q for q in questions if q.type == question_type]
        if not filtered:
            if question_type == 'judge':
                filtered = [q for q in questions if q.type in ['judgement', 'judge']]
            elif question_type == 'judgement':
                filtered = [q for q in questions if q.type in ['judge', 'judgement']]
            elif question_type == 'short':
                filtered = [q for q in questions if q.type in ['short', 'essay', 'fill']]
            elif question_type == 'fill':
                filtered = [q for q in questions if q.type in ['fill', 'short']]
        return filtered

    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        """根据ID获取题目"""
        for question in self.questions:
            if question.id == question_id:
                return question
        return None
    
    def get_type_distribution(self) -> Dict[str, int]:
        """获取题型分布统计"""
        distribution = {}
        for question in self.questions:
            distribution[question.type] = distribution.get(question.type, 0) + 1
        return distribution
    
    def search_questions(self, keyword: str) -> List[Question]:
        """搜索题目"""
        keyword = keyword.lower()
        results = []
        for question in self.questions:
            if (keyword in question.question.lower() or 
                keyword in question.explanation.lower() or
                any(keyword in option.lower() for option in question.options)):
                results.append(question)
        return results