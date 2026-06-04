#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
考试服务模块 - 处理考试相关的业务逻辑
"""

import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
from core.models import Question, QuestionBank, ExamSession, ExamAnswer
from core.utils import validate_answer, generate_exam_questions, calculate_remaining_time
from core.config import EXAM_CONFIG


class ExamService:
    """考试服务类"""
    
    def __init__(self):
        self.question_bank: Optional[QuestionBank] = None
        self.exam_session: Optional[ExamSession] = None
    
    def set_question_bank(self, question_bank: QuestionBank):
        """设置题库"""
        self.question_bank = question_bank
    
    def start_exam_session(self, question_count: int = None, time_limit: int = None) -> ExamSession:
        """开始考试会话"""
        if not self.question_bank:
            raise ValueError("未加载题库")
        
        question_count = question_count or EXAM_CONFIG["questions_per_exam"]
        time_limit = time_limit or EXAM_CONFIG["default_time_limit"]
        
        # 生成考试题目
        exam_questions = generate_exam_questions(self.question_bank, question_count)
        if not exam_questions:
            raise ValueError("无法生成考试题目")
        
        # 创建考试会话
        self.exam_session = ExamSession(
            questions=exam_questions,
            start_time=datetime.now(),
            time_limit=time_limit
        )
        
        # 初始化答案记录
        for question in exam_questions:
            self.exam_session.answers[question.id] = ExamAnswer(question_id=question.id)
        
        return self.exam_session
    
    def get_current_question(self) -> Optional[Question]:
        """获取当前题目"""
        if not self.exam_session or not self.exam_session.questions:
            return None
        
        if 0 <= self.exam_session.current_question_index < len(self.exam_session.questions):
            return self.exam_session.questions[self.exam_session.current_question_index]
        return None
    
    def jump_to_question(self, index: int) -> bool:
        """跳转到指定题目"""
        if not self.exam_session:
            return False
        
        if 0 <= index < len(self.exam_session.questions):
            self.exam_session.current_question_index = index
            return True
        return False
    
    def save_answer(self, question_id: int, user_answer: str):
        """保存答案"""
        if not self.exam_session:
            raise ValueError("未开始考试会话")
        
        if question_id in self.exam_session.answers:
            self.exam_session.answers[question_id].set_answer(user_answer)
    
    def get_answer(self, question_id: int) -> Optional[str]:
        """获取已保存的答案"""
        if not self.exam_session:
            return None
        
        answer = self.exam_session.answers.get(question_id)
        return answer.user_answer if answer else None
    
    def get_remaining_time(self) -> int:
        """获取剩余时间（秒）"""
        if not self.exam_session or not self.exam_session.start_time:
            return 0
        
        return calculate_remaining_time(self.exam_session.start_time, self.exam_session.time_limit)
    
    def is_time_up(self) -> bool:
        """检查是否超时"""
        return self.get_remaining_time() <= 0
    
    def get_answered_questions(self) -> Set[int]:
        """获取已答题目ID集合"""
        if not self.exam_session:
            return set()
        
        answered = set()
        for question_id, answer in self.exam_session.answers.items():
            if answer.user_answer.strip():
                answered.add(question_id)
        return answered
    
    def get_unanswered_questions(self) -> Set[int]:
        """获取未答题目ID集合"""
        if not self.exam_session:
            return set()
        
        all_questions = {q.id for q in self.exam_session.questions}
        answered = self.get_answered_questions()
        return all_questions - answered
    
    def submit_exam(self) -> Dict[str, Any]:
        """提交考试"""
        if not self.exam_session:
            raise ValueError("未开始考试会话")
        
        if self.exam_session.is_submitted:
            raise ValueError("考试已提交")
        
        # 设置结束时间
        self.exam_session.end_time = datetime.now()
        self.exam_session.is_submitted = True
        
        # 计算答案正确性
        correct_count = 0
        wrong_questions = []
        
        for question in self.exam_session.questions:
            answer = self.exam_session.answers.get(question.id)
            if answer:
                is_correct = validate_answer(question, answer.user_answer)
                answer.is_correct = is_correct
                
                if is_correct:
                    correct_count += 1
                else:
                    wrong_questions.append(question.id)
        
        # 计算得分
        total_questions = len(self.exam_session.questions)
        score = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        return {
            "score": round(score, 1),
            "correct_count": correct_count,
            "total_questions": total_questions,
            "wrong_questions": wrong_questions,
            "duration": self.exam_session.get_duration(),
            "pass_score": EXAM_CONFIG["pass_score"],
            "is_passed": score >= EXAM_CONFIG["pass_score"]
        }
    
    def get_exam_result(self) -> Optional[Dict[str, Any]]:
        """获取考试结果"""
        if not self.exam_session or not self.exam_session.is_submitted:
            return None
        
        return self.submit_exam()
    
    def get_question_result(self, question_id: int) -> Optional[Dict[str, Any]]:
        """获取单题结果"""
        if not self.exam_session or not self.exam_session.is_submitted:
            return None
        
        question = None
        for q in self.exam_session.questions:
            if q.id == question_id:
                question = q
                break
        
        if not question:
            return None
        
        answer = self.exam_session.answers.get(question_id)
        if not answer:
            return None
        
        return {
            "question": question,
            "user_answer": answer.user_answer,
            "correct_answer": question.answer,
            "is_correct": answer.is_correct,
            "explanation": question.explanation
        }
    
    def get_all_question_results(self) -> List[Dict[str, Any]]:
        """获取所有题目结果"""
        if not self.exam_session or not self.exam_session.is_submitted:
            return []
        
        results = []
        for question in self.exam_session.questions:
            result = self.get_question_result(question.id)
            if result:
                results.append(result)
        
        return results
    
    def get_exam_statistics(self) -> Dict[str, Any]:
        """获取考试统计信息"""
        if not self.exam_session:
            return {}
        
        answered_count = len(self.get_answered_questions())
        unanswered_count = len(self.get_unanswered_questions())
        
        stats = {
            "total_questions": len(self.exam_session.questions),
            "current_index": self.exam_session.current_question_index + 1,
            "answered_count": answered_count,
            "unanswered_count": unanswered_count,
            "time_limit": self.exam_session.time_limit,
            "remaining_time": self.get_remaining_time(),
            "is_submitted": self.exam_session.is_submitted
        }
        
        if self.exam_session.start_time:
            stats["start_time"] = self.exam_session.start_time
        
        if self.exam_session.end_time:
            stats["end_time"] = self.exam_session.end_time
            stats["duration"] = self.exam_session.get_duration()
        
        return stats
    
    def get_answer_status_for_buttons(self) -> Dict[int, str]:
        """获取答题状态（用于状态按钮显示）"""
        if not self.exam_session:
            return {}
        
        status = {}
        answered_questions = self.get_answered_questions()
        
        for i, question in enumerate(self.exam_session.questions):
            if self.exam_session.is_submitted:
                # 考试已提交，显示正确/错误状态
                answer = self.exam_session.answers.get(question.id)
                if answer and answer.is_correct:
                    status[i] = "correct"
                else:
                    status[i] = "wrong"
            else:
                # 考试进行中，显示已答/未答状态
                if question.id in answered_questions:
                    status[i] = "answered"
                else:
                    status[i] = "unanswered"
        
        return status
    
    def can_submit_exam(self) -> bool:
        """检查是否可以提交考试"""
        if not self.exam_session:
            return False
        
        return not self.exam_session.is_submitted
    
    def force_submit_exam(self) -> Dict[str, Any]:
        """强制提交考试（时间到）"""
        if not self.exam_session:
            raise ValueError("未开始考试会话")
        
        return self.submit_exam()
    
    def get_exam_progress(self) -> Dict[str, Any]:
        """获取考试进度"""
        if not self.exam_session:
            return {}
        
        answered_count = len(self.get_answered_questions())
        total_questions = len(self.exam_session.questions)
        progress_percent = (answered_count / total_questions * 100) if total_questions > 0 else 0
        
        return {
            "answered_count": answered_count,
            "total_questions": total_questions,
            "progress_percent": round(progress_percent, 1),
            "current_question": self.exam_session.current_question_index + 1
        }