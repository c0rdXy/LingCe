#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块 - 通用工具和辅助函数
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .models import Question, QuestionBank


def load_questions_from_file(file_path: str) -> QuestionBank:
    """从文件加载题目"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions = []
        for item in data:
            question = Question(
                id=item.get('id', 0),
                type=item.get('type', 'single'),
                question=item.get('question', ''),
                options=item.get('options', []),
                answer=item.get('answer', ''),
                explanation=item.get('explanation', ''),
                is_collected=item.get('is_collected', False)
            )
            questions.append(question)
        
        return QuestionBank(questions=questions, file_path=file_path)
    
    except Exception as e:
        raise Exception(f"加载题库文件失败: {str(e)}")


def save_questions_to_file(question_bank: QuestionBank, file_path: str):
    """保存题目到文件"""
    try:
        data = []
        for question in question_bank.questions:
            data.append({
                'id': question.id,
                'type': question.type,
                'question': question.question,
                'options': question.options,
                'answer': question.answer,
                'explanation': question.explanation,
                'is_collected': question.is_collected
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    except Exception as e:
        raise Exception(f"保存题库文件失败: {str(e)}")


def shuffle_questions(questions: List[Question]) -> List[Question]:
    """随机打乱题目顺序"""
    shuffled = questions.copy()
    random.shuffle(shuffled)
    return shuffled


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}分{secs}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}小时{minutes}分"


def format_datetime(dt: datetime) -> str:
    """格式化日期时间"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def calculate_remaining_time(start_time: datetime, time_limit_minutes: int) -> int:
    """计算剩余时间（秒）"""
    elapsed = datetime.now() - start_time
    total_seconds = time_limit_minutes * 60
    remaining = total_seconds - elapsed.total_seconds()
    return max(0, int(remaining))


def format_remaining_time(remaining_seconds: int) -> str:
    """格式化剩余时间显示"""
    if remaining_seconds <= 0:
        return "00:00"
    
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def validate_answer(question: Question, user_answer: str) -> bool:
    """验证答案是否正确"""
    if not user_answer:
        return False
    
    correct_answer = question.answer.upper().strip()
    user_answer = user_answer.upper().strip()
    
    if question.is_multiple_choice():
        # 多选题：排序后比较
        correct_options = sorted(list(correct_answer))
        user_options = sorted(list(user_answer))
        return correct_options == user_options
    elif question.type in ['judge', 'judgement']:
        return normalize_judge_answer(correct_answer) == normalize_judge_answer(user_answer)
    else:
        # 单选题、简答题：直接比较
        return correct_answer == user_answer


def normalize_judge_answer(answer: str) -> str:
    """将判断题答案统一为 A/B，无法识别时返回清理后的原值。"""
    value = str(answer or "").strip().upper()
    if value in {"A", "TRUE", "T", "√", "✓", "对", "正确", "YES", "Y", "1"}:
        return "A"
    if value in {"B", "FALSE", "F", "×", "✗", "错", "错误", "NO", "N", "0"}:
        return "B"
    return value


def format_judge_answer(answer: str) -> str:
    """将判断题内部答案显示为用户可读文本。"""
    normalized = normalize_judge_answer(answer)
    if normalized == "A":
        return "正确"
    if normalized == "B":
        return "错误"
    return str(answer or "")


def get_question_type_name(question_type: str) -> str:
    """获取题型中文名称"""
    type_names = {
        "single": "单选题",
        "multiple": "多选题", 
        "judge": "判断题",
        "judgement": "判断题",
        "short": "简答题",
        "fill": "填空题",
        "essay": "简答题"
    }
    return type_names.get(question_type, question_type)


def generate_exam_questions(question_bank: QuestionBank, count: int = 50) -> List[Question]:
    """生成考试题目"""
    if len(question_bank.questions) <= count:
        return shuffle_questions(question_bank.questions)
    
    # 按题型比例分配
    type_distribution = question_bank.get_type_distribution()
    total_questions = len(question_bank.questions)
    
    selected_questions = []
    remaining_count = count
    
    for question_type, type_count in type_distribution.items():
        if remaining_count <= 0:
            break
        
        # 计算该题型应选择的题目数量
        proportion = type_count / total_questions
        type_select_count = min(int(count * proportion), type_count, remaining_count)
        
        if type_select_count > 0:
            type_questions = question_bank.get_questions_by_type(question_type)
            selected = random.sample(type_questions, type_select_count)
            selected_questions.extend(selected)
            remaining_count -= type_select_count
    
    # 如果还有剩余名额，随机补充
    if remaining_count > 0:
        all_ids = {q.id for q in selected_questions}
        remaining_questions = [q for q in question_bank.questions if q.id not in all_ids]
        if remaining_questions:
            additional = random.sample(remaining_questions, min(remaining_count, len(remaining_questions)))
            selected_questions.extend(additional)
    
    return shuffle_questions(selected_questions)


def search_questions_by_id(question_bank: QuestionBank, question_id: int) -> Optional[Question]:
    """根据ID搜索题目"""
    return question_bank.get_question_by_id(question_id)


def get_statistics_summary(correct_count: int, total_count: int, wrong_questions: List[int]) -> Dict[str, Any]:
    """获取统计摘要"""
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
    
    return {
        "total_answered": total_count,
        "correct_count": correct_count,
        "wrong_count": len(wrong_questions),
        "accuracy": round(accuracy, 1),
        "wrong_question_ids": wrong_questions
    }


def export_wrong_questions(question_bank: QuestionBank, wrong_question_ids: List[int], file_path: str):
    """导出错题集"""
    wrong_questions = [q for q in question_bank.questions if q.id in wrong_question_ids]
    wrong_bank = QuestionBank(questions=wrong_questions)
    save_questions_to_file(wrong_bank, file_path)
