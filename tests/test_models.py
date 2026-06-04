#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据模型单元测试"""

import unittest
from core.models import (
    Question, QuestionBank, ExamAnswer, ExamSession,
    PracticeSession,
)


class TestQuestion(unittest.TestCase):
    """Question 数据模型测试"""

    def setUp(self):
        self.single = Question(id=1, type="single", question="Test?",
                               options=["A. Yes", "B. No"], answer="A")
        self.multiple = Question(id=2, type="multiple", question="Pick?",
                                 options=["A. X", "B. Y", "C. Z"], answer="AB")
        self.judge = Question(id=3, type="judge", question="True?",
                              options=[], answer="A")
        self.short = Question(id=4, type="short", question="Explain?",
                              options=[], answer="Because...")

    def test_is_single_choice(self):
        self.assertTrue(self.single.is_single_choice())
        self.assertFalse(self.multiple.is_single_choice())

    def test_is_multiple_choice(self):
        self.assertTrue(self.multiple.is_multiple_choice())
        self.assertFalse(self.single.is_multiple_choice())

    def test_is_judge(self):
        self.assertTrue(self.judge.is_judge())
        self.assertFalse(self.single.is_judge())

    def test_is_short_answer(self):
        self.assertTrue(self.short.is_short_answer())
        self.assertFalse(self.single.is_short_answer())

    def test_get_correct_options_single(self):
        self.assertEqual(self.single.get_correct_options(), ["A"])

    def test_get_correct_options_multiple(self):
        result = self.multiple.get_correct_options()
        self.assertEqual(sorted(result), ["A", "B"])

    def test_get_correct_options_empty(self):
        q = Question(id=99, type="single", question="?", answer="")
        self.assertEqual(q.get_correct_options(), [])


class TestQuestionBank(unittest.TestCase):
    """QuestionBank 数据模型测试"""

    def setUp(self):
        questions = [
            Question(id=1, type="single", question="Q1", answer="A"),
            Question(id=2, type="multiple", question="Q2", answer="AB"),
            Question(id=3, type="single", question="Q3", answer="B"),
            Question(id=4, type="judgement", question="Q4", answer="A"),
            Question(id=5, type="short", question="Q5", answer="X"),
        ]
        self.bank = QuestionBank(questions=questions, file_path="test.json")

    def test_total_questions(self):
        self.assertEqual(len(self.bank.questions), 5)

    def test_get_by_type_single(self):
        result = self.bank.get_questions_by_type("single")
        self.assertEqual(len(result), 2)

    def test_get_by_type_multiple(self):
        result = self.bank.get_questions_by_type("multiple")
        self.assertEqual(len(result), 1)

    def test_get_by_type_all(self):
        result = self.bank.get_questions_by_type("all")
        self.assertEqual(len(result), 5)

    def test_get_by_type_judge_compatibility(self):
        # "judge" should match "judgement" via compatibility
        result = self.bank.get_questions_by_type("judge")
        self.assertEqual(len(result), 1)

    def test_get_by_id(self):
        q = self.bank.get_question_by_id(3)
        self.assertIsNotNone(q)
        self.assertEqual(q.question, "Q3")

    def test_get_by_id_not_found(self):
        q = self.bank.get_question_by_id(999)
        self.assertIsNone(q)

    def test_type_distribution(self):
        dist = self.bank.get_type_distribution()
        self.assertEqual(dist["single"], 2)
        self.assertEqual(dist["multiple"], 1)
        self.assertEqual(dist["judgement"], 1)
        self.assertEqual(dist["short"], 1)

    def test_search(self):
        results = self.bank.search_questions("Q1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, 1)

    def test_search_empty(self):
        results = self.bank.search_questions("NONEXISTENT")
        self.assertEqual(len(results), 0)


class TestExamAnswer(unittest.TestCase):
    """ExamAnswer 测试"""

    def test_set_answer(self):
        ea = ExamAnswer(question_id=1)
        ea.set_answer("A")
        self.assertEqual(ea.user_answer, "A")

    def test_default_values(self):
        ea = ExamAnswer(question_id=1)
        self.assertEqual(ea.user_answer, "")
        self.assertFalse(ea.is_correct)
        self.assertEqual(ea.time_spent, 0.0)


class TestExamSession(unittest.TestCase):
    """ExamSession 测试"""

    def setUp(self):
        questions = [
            Question(id=1, type="single", question="Q1", answer="A"),
            Question(id=2, type="single", question="Q2", answer="B"),
        ]
        self.session = ExamSession(questions=questions, time_limit=90)

    def test_get_score_empty(self):
        self.assertEqual(self.session.get_score(), 0.0)

    def test_get_score_all_correct(self):
        self.session.answers[1] = ExamAnswer(question_id=1, is_correct=True)
        self.session.answers[2] = ExamAnswer(question_id=2, is_correct=True)
        self.assertEqual(self.session.get_score(), 100.0)

    def test_get_score_half(self):
        self.session.answers[1] = ExamAnswer(question_id=1, is_correct=True)
        self.session.answers[2] = ExamAnswer(question_id=2, is_correct=False)
        self.assertEqual(self.session.get_score(), 50.0)

    def test_set_answer(self):
        self.session.set_answer_for_question(1, "A")
        self.assertEqual(self.session.get_answer_for_question(1).user_answer, "A")

    def test_update_existing_answer(self):
        self.session.set_answer_for_question(1, "A")
        self.session.set_answer_for_question(1, "B")
        self.assertEqual(self.session.get_answer_for_question(1).user_answer, "B")


class TestPracticeSession(unittest.TestCase):
    """PracticeSession 测试"""

    def setUp(self):
        self.session = PracticeSession(
            questions=[Question(id=i, type="single", question=f"Q{i}", answer="A")
                       for i in range(1, 6)]
        )

    def test_initial_state(self):
        self.assertEqual(self.session.current_question_index, 0)
        self.assertEqual(self.session.correct_count, 0)
        self.assertEqual(self.session.answered_count, 0)

    def test_accuracy_zero(self):
        self.assertEqual(self.session.get_accuracy(), 0.0)

    def test_add_correct(self):
        self.session.add_correct_answer()
        self.assertEqual(self.session.correct_count, 1)
        self.assertEqual(self.session.answered_count, 1)
        self.assertEqual(self.session.get_accuracy(), 100.0)

    def test_add_wrong(self):
        self.session.add_wrong_answer(1)
        self.assertEqual(self.session.answered_count, 1)
        self.assertEqual(self.session.correct_count, 0)
        self.assertEqual(len(self.session.wrong_questions), 1)

    def test_accuracy_mixed(self):
        self.session.add_correct_answer()
        self.session.add_wrong_answer(2)
        self.assertEqual(self.session.get_accuracy(), 50.0)

    def test_wrong_dedup(self):
        self.session.add_wrong_answer(1)
        self.session.add_wrong_answer(1)
        self.assertEqual(len(self.session.wrong_questions), 1)

    def test_reset(self):
        self.session.add_correct_answer()
        self.session.add_wrong_answer(2)
        self.session.reset_stats()
        self.assertEqual(self.session.correct_count, 0)
        self.assertEqual(self.session.answered_count, 0)
        self.assertEqual(len(self.session.wrong_questions), 0)


if __name__ == "__main__":
    unittest.main()
