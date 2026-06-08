#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""服务层单元测试"""

import unittest
import tempfile
import os
import json

from core.models import Question, QuestionBank
from services.exam_service import ExamService
from services.file_service import FileService
from services.user_data_service import UserDataService


class TestExamService(unittest.TestCase):
    """ExamService 测试"""

    def setUp(self):
        questions = [
            Question(id=i, type="single", question=f"Q{i}",
                     options=["A. X", "B. Y"], answer="A" if i % 2 == 0 else "B")
            for i in range(1, 61)
        ]
        self.bank = QuestionBank(questions=questions, file_path="test.json")
        self.service = ExamService()
        self.service.set_question_bank(self.bank)

    def test_start_session(self):
        session = self.service.start_exam_session(question_count=10, time_limit=60)
        self.assertEqual(len(session.questions), 10)
        self.assertIsNotNone(session.start_time)

    def test_get_current_question(self):
        self.service.start_exam_session(question_count=10)
        q = self.service.get_current_question()
        self.assertIsNotNone(q)

    def test_jump_to_question(self):
        self.service.start_exam_session(question_count=10)
        self.assertTrue(self.service.jump_to_question(5))
        q = self.service.get_current_question()
        self.assertEqual(self.service.exam_session.current_question_index, 5)

    def test_jump_out_of_range(self):
        self.service.start_exam_session(question_count=10)
        self.assertFalse(self.service.jump_to_question(99))

    def test_save_and_get_answer(self):
        self.service.start_exam_session(question_count=10)
        q = self.service.get_current_question()
        self.service.save_answer(q.id, "A")
        self.assertEqual(self.service.get_answer(q.id), "A")

    def test_answered_questions(self):
        self.service.start_exam_session(question_count=10)
        q = self.service.get_current_question()
        self.service.save_answer(q.id, "A")
        answered = self.service.get_answered_questions()
        self.assertIn(q.id, answered)

    def test_unanswered_questions(self):
        self.service.start_exam_session(question_count=10)
        unanswered = self.service.get_unanswered_questions()
        self.assertEqual(len(unanswered), 10)

    def test_submit_exam(self):
        self.service.start_exam_session(question_count=10)
        # Answer all questions
        for q in self.service.exam_session.questions:
            self.service.save_answer(q.id, "A")
        result = self.service.submit_exam()
        self.assertIn("score", result)
        self.assertIn("correct_count", result)
        self.assertIn("is_passed", result)  # submitted result has is_passed

    def test_submit_twice_fails(self):
        self.service.start_exam_session(question_count=10)
        for q in self.service.exam_session.questions:
            self.service.save_answer(q.id, "A")
        self.service.submit_exam()
        with self.assertRaises(ValueError):
            self.service.submit_exam()

    def test_get_exam_result_after_submit(self):
        self.service.start_exam_session(question_count=10)
        for q in self.service.exam_session.questions:
            self.service.save_answer(q.id, "A")
        submitted = self.service.submit_exam()
        result = self.service.get_exam_result()
        self.assertEqual(result, submitted)

    def test_get_answer_status(self):
        self.service.start_exam_session(question_count=10)
        q = self.service.get_current_question()
        self.service.save_answer(q.id, "A")
        status = self.service.get_answer_status_for_buttons()
        self.assertEqual(status[0], "answered")
        self.assertEqual(status[1], "unanswered")

    def test_exam_progress(self):
        self.service.start_exam_session(question_count=10)
        q = self.service.get_current_question()
        self.service.save_answer(q.id, "A")
        progress = self.service.get_exam_progress()
        self.assertEqual(progress["answered_count"], 1)
        self.assertEqual(progress["total_questions"], 10)

    def test_can_submit(self):
        self.service.start_exam_session(question_count=10)
        self.assertTrue(self.service.can_submit_exam())

    def test_cannot_submit_after_submit(self):
        self.service.start_exam_session(question_count=10)
        for q in self.service.exam_session.questions:
            self.service.save_answer(q.id, "A")
        self.service.submit_exam()
        self.assertFalse(self.service.can_submit_exam())

    def test_no_bank_raises(self):
        empty = ExamService()
        with self.assertRaises(ValueError):
            empty.start_exam_session()

    def test_remaining_time_positive(self):
        self.service.start_exam_session(question_count=10, time_limit=90)
        remaining = self.service.get_remaining_time()
        self.assertGreater(remaining, 0)


class TestFileService(unittest.TestCase):
    """FileService 娴嬭瘯"""

    def test_validate_accepts_supported_question_types(self):
        service = FileService()
        data = [
            {"type": "single", "question": "Q1", "options": ["A. X", "B. Y"], "answer": "A"},
            {"type": "multiple", "question": "Q2", "options": ["A. X", "B. Y"], "answer": "AB"},
            {"type": "judge", "question": "Q3", "answer": "A"},
            {"type": "judgement", "question": "Q4", "answer": "A"},
            {"type": "fill", "question": "Q5", "answer": "X"},
            {"type": "short", "question": "Q6", "answer": "X"},
            {"type": "essay", "question": "Q7", "answer": "X"},
        ]

        self.assertEqual(service.validate_question_data(data), [])


class TestUserDataService(unittest.TestCase):
    """UserDataService 测试"""

    def setUp(self):
        self.tmpfile = os.path.join(tempfile.gettempdir(), "test_user_data.json")
        # Clean up from previous runs
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)
        self.ud = UserDataService(self.tmpfile)

    def tearDown(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_default_data(self):
        self.assertEqual(self.ud.get_theme(), "light")
        self.assertEqual(self.ud.get_last_file(), "")

    def test_set_and_get_theme(self):
        self.ud.set_theme("dark")
        self.assertEqual(self.ud.get_theme(), "dark")
        # Reload from file
        ud2 = UserDataService(self.tmpfile)
        self.assertEqual(ud2.get_theme(), "dark")

    def test_last_file(self):
        self.ud.set_last_file("/path/to/bank.json")
        self.assertEqual(self.ud.get_last_file(), "/path/to/bank.json")

    def test_favorites(self):
        self.assertFalse(self.ud.is_favorite("bank.json", 1))
        self.ud.toggle_favorite("bank.json", 1)
        self.assertTrue(self.ud.is_favorite("bank.json", 1))
        self.ud.toggle_favorite("bank.json", 1)
        self.assertFalse(self.ud.is_favorite("bank.json", 1))

    def test_favorites_sorted(self):
        self.ud.toggle_favorite("bank.json", 5)
        self.ud.toggle_favorite("bank.json", 2)
        self.ud.toggle_favorite("bank.json", 8)
        favs = self.ud.get_favorites("bank.json")
        self.assertEqual(favs, [2, 5, 8])

    def test_wrong_history(self):
        self.ud.add_wrong_questions("bank.json", [10, 20, 30])
        self.assertEqual(self.ud.get_wrong_history("bank.json"), [10, 20, 30])

    def test_wrong_history_dedup(self):
        self.ud.add_wrong_questions("bank.json", [1, 2])
        self.ud.add_wrong_questions("bank.json", [2, 3])
        self.assertEqual(self.ud.get_wrong_history("bank.json"), [1, 2, 3])

    def test_clear_wrong_history(self):
        self.ud.add_wrong_questions("bank.json", [1, 2])
        self.ud.clear_wrong_history("bank.json")
        self.assertEqual(self.ud.get_wrong_history("bank.json"), [])

    def test_progress(self):
        self.ud.save_progress("bank.json", {"current_index": 42, "type": "single"})
        progress = self.ud.get_progress("bank.json")
        self.assertEqual(progress["current_index"], 42)

    def test_progress_missing_file(self):
        progress = self.ud.get_progress("nonexistent.json")
        self.assertEqual(progress, {})

    def test_stats_update(self):
        self.ud.update_stats(10, 7)
        stats = self.ud.get_stats()
        self.assertEqual(stats["total_answered"], 10)
        self.assertEqual(stats["total_correct"], 7)

    def test_daily_stats(self):
        self.ud.update_stats(5, 3)
        daily = self.ud.get_daily_stats()
        self.assertEqual(len(daily), 1)
        today = list(daily.values())[0]
        self.assertEqual(today["answered"], 5)
        self.assertEqual(today["correct"], 3)

    def test_tags(self):
        self.ud.set_tags("bank.json", 1, ["重点", "难点"])
        tags = self.ud.get_tags("bank.json", 1)
        self.assertEqual(tags, ["重点", "难点"])

    def test_all_tags(self):
        self.ud.set_tags("bank.json", 1, ["A"])
        self.ud.set_tags("bank.json", 2, ["B"])
        all_tags = self.ud.get_all_tags("bank.json")
        self.assertEqual(len(all_tags), 2)

    def test_export_data(self):
        self.ud.set_theme("dark")
        data = self.ud.export_data()
        self.assertEqual(data["theme"], "dark")

    def test_persistence_across_instances(self):
        self.ud.set_theme("dark")
        self.ud.toggle_favorite("bank.json", 42)
        self.ud.update_stats(5, 3)

        # Create new instance from same file
        ud2 = UserDataService(self.tmpfile)
        self.assertEqual(ud2.get_theme(), "dark")
        self.assertTrue(ud2.is_favorite("bank.json", 42))
        stats = ud2.get_stats()
        self.assertEqual(stats["total_answered"], 5)


if __name__ == "__main__":
    unittest.main()
