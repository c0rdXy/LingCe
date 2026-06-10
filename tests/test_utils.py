#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具函数单元测试"""

import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta

from core.models import Question, QuestionBank
from core.utils import (
    load_questions_from_file,
    save_questions_to_file,
    shuffle_questions,
    format_time,
    calculate_remaining_time,
    format_remaining_time,
    validate_answer,
    normalize_judge_answer,
    format_judge_answer,
    get_question_type_name,
    generate_exam_questions,
    get_statistics_summary,
)


class TestLoadSaveQuestions(unittest.TestCase):
    """题目文件加载/保存测试"""

    def setUp(self):
        self.questions = [
            {"id": 1, "type": "single", "question": "Q1",
             "options": ["A. X", "B. Y"], "answer": "A", "explanation": "E1"},
            {"id": 2, "type": "multiple", "question": "Q2",
             "options": ["A. X", "B. Y"], "answer": "AB", "explanation": "E2"},
        ]

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w",
                                         encoding="utf-8") as f:
            json.dump(self.questions, f, ensure_ascii=False)
            path = f.name

        try:
            bank = load_questions_from_file(path)
            self.assertEqual(len(bank.questions), 2)
            self.assertEqual(bank.questions[0].type, "single")
            self.assertEqual(bank.questions[1].answer, "AB")
            self.assertEqual(bank.file_path, path)
        finally:
            os.unlink(path)

    def test_save_questions(self):
        questions = [Question(id=1, type="single", question="Test?",
                              options=["A. X"], answer="A", explanation="")]
        bank = QuestionBank(questions=questions)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            save_questions_to_file(bank, path)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["answer"], "A")
        finally:
            os.unlink(path)

    def test_load_invalid_file(self):
        with self.assertRaises(Exception):
            load_questions_from_file("/nonexistent/path.json")


class TestValidateAnswer(unittest.TestCase):
    """答案验证测试"""

    def test_single_correct(self):
        q = Question(id=1, type="single", question="?", answer="A")
        self.assertTrue(validate_answer(q, "A"))
        self.assertTrue(validate_answer(q, "a"))

    def test_single_wrong(self):
        q = Question(id=1, type="single", question="?", answer="A")
        self.assertFalse(validate_answer(q, "B"))

    def test_single_empty(self):
        q = Question(id=1, type="single", question="?", answer="A")
        self.assertFalse(validate_answer(q, ""))

    def test_multiple_correct(self):
        q = Question(id=1, type="multiple", question="?", answer="AB")
        self.assertTrue(validate_answer(q, "BA"))
        self.assertTrue(validate_answer(q, "ab"))

    def test_multiple_wrong(self):
        q = Question(id=1, type="multiple", question="?", answer="ABC")
        self.assertFalse(validate_answer(q, "AB"))

    def test_judge_correct(self):
        q = Question(id=1, type="judge", question="?", answer="A")
        self.assertTrue(validate_answer(q, "A"))

    def test_judge_chinese_answer_matches_option_b(self):
        q = Question(id=1, type="judge", question="?", answer="错误")
        self.assertTrue(validate_answer(q, "B"))

    def test_judge_answer_helpers(self):
        self.assertEqual(normalize_judge_answer("错误"), "B")
        self.assertEqual(normalize_judge_answer("正确"), "A")
        self.assertEqual(format_judge_answer("B"), "错误")
        self.assertEqual(format_judge_answer("A"), "正确")


class TestFormatTime(unittest.TestCase):
    """时间格式化测试"""

    def test_seconds(self):
        self.assertIn("秒", format_time(30))

    def test_minutes(self):
        result = format_time(90)
        self.assertIn("分", result)

    def test_hours(self):
        result = format_time(3700)
        self.assertIn("小时", result)


class TestFormatRemainingTime(unittest.TestCase):
    """剩余时间格式化测试"""

    def test_zero(self):
        self.assertEqual(format_remaining_time(0), "00:00")

    def test_negative(self):
        self.assertEqual(format_remaining_time(-10), "00:00")

    def test_normal(self):
        self.assertEqual(format_remaining_time(90), "01:30")

    def test_one_hour(self):
        self.assertEqual(format_remaining_time(3600), "60:00")


class TestShuffleQuestions(unittest.TestCase):
    """题目随机排序测试"""

    def test_same_elements(self):
        questions = [Question(id=i, type="single", question=f"Q{i}", answer="A")
                     for i in range(20)]
        shuffled = shuffle_questions(questions)
        self.assertEqual(len(shuffled), 20)
        ids = sorted(q.id for q in shuffled)
        self.assertEqual(ids, list(range(20)))

    def test_original_unchanged(self):
        questions = [Question(id=i, type="single", question=f"Q{i}", answer="A")
                     for i in range(10)]
        original_ids = [q.id for q in questions]
        shuffle_questions(questions)
        self.assertEqual([q.id for q in questions], original_ids)


class TestGetQuestionTypeName(unittest.TestCase):
    """题型名称映射测试"""

    def test_single(self):
        self.assertEqual(get_question_type_name("single"), "单选题")

    def test_multiple(self):
        self.assertEqual(get_question_type_name("multiple"), "多选题")

    def test_judge(self):
        self.assertEqual(get_question_type_name("judge"), "判断题")

    def test_judgement(self):
        self.assertEqual(get_question_type_name("judgement"), "判断题")

    def test_short(self):
        self.assertEqual(get_question_type_name("short"), "简答题")

    def test_fill(self):
        self.assertEqual(get_question_type_name("fill"), "填空题")

    def test_unknown(self):
        self.assertEqual(get_question_type_name("unknown"), "unknown")


class TestGenerateExamQuestions(unittest.TestCase):
    """考试题目生成测试"""

    def setUp(self):
        questions = [
            Question(id=i, type="single" if i < 30 else "multiple",
                     question=f"Q{i}", answer="A")
            for i in range(50)
        ]
        self.bank = QuestionBank(questions=questions)

    def test_generate_count(self):
        result = generate_exam_questions(self.bank, count=20)
        self.assertEqual(len(result), 20)

    def test_generate_all_if_insufficient(self):
        small_bank = QuestionBank(
            questions=[Question(id=1, type="single", question="Q", answer="A")]
        )
        result = generate_exam_questions(small_bank, count=50)
        self.assertEqual(len(result), 1)

    def test_generate_deterministic_count(self):
        result = generate_exam_questions(self.bank, count=30)
        self.assertEqual(len(result), 30)


class TestGetStatisticsSummary(unittest.TestCase):
    """统计摘要测试"""

    def test_normal(self):
        result = get_statistics_summary(7, 10, [1, 3])
        self.assertEqual(result["total_answered"], 10)
        self.assertEqual(result["correct_count"], 7)
        self.assertEqual(result["wrong_count"], 2)
        self.assertAlmostEqual(result["accuracy"], 70.0)

    def test_zero_total(self):
        result = get_statistics_summary(0, 0, [])
        self.assertEqual(result["accuracy"], 0.0)


if __name__ == "__main__":
    unittest.main()
