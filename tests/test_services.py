#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""服务层单元测试"""

import unittest
import tempfile
import os
import json
import zipfile
from pathlib import Path

from core.models import Question, QuestionBank
from services.exam_service import ExamService
from services.question_service import QuestionService
from services.question_bank_builder import QuestionBankBuilder, QuestionDraft
from services.user_data_service import UserDataService
from services.settings_service import SettingsService
from services.ai_service import AIService, AIServiceError
from services.document_import_service import DocumentImportService
from core.ai_presets import get_providers
import services.exam_db as exam_db
from ui.practice_mode import PracticeModeWindow
from ui.exam_mode import ExamModeWindow


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


class TestUserDataService(unittest.TestCase):
    """UserDataService 测试"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpfile = os.path.join(self.tmpdir.name, "test_user_data.json")
        self.ud = UserDataService(self.tmpfile)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_default_data(self):
        self.assertEqual(self.ud.get_theme(), "light")
        self.assertEqual(self.ud.get_last_file(), "")
        self.assertNotIn("theme", self.ud.export_data())

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

    def test_wrong_history_matches_equivalent_paths(self):
        bank_path = os.path.abspath("tmp-test-bank.json")
        self.ud.add_wrong_questions(bank_path, [1, 2])

        relative_path = os.path.relpath(bank_path, os.getcwd())

        self.assertEqual(self.ud.get_wrong_history(relative_path), [1, 2])

    def test_wrong_history_matches_slash_variants(self):
        self.ud.add_wrong_questions(r"question_banks\bank.json", [3, 4])

        self.assertEqual(self.ud.get_wrong_history("question_banks/bank.json"), [3, 4])

    def test_wrong_history_matches_same_file_name(self):
        self.ud.add_wrong_questions(r"question_banks\bank.json", [5, 6])

        self.assertEqual(self.ud.get_wrong_history("D:/other/path/bank.json"), [5, 6])

    def test_clear_wrong_history(self):
        self.ud.add_wrong_questions("bank.json", [1, 2])
        self.ud.clear_wrong_history("bank.json")
        self.assertEqual(self.ud.get_wrong_history("bank.json"), [])

    def test_clear_wrong_history_removes_same_file_name_aliases(self):
        self.ud.add_wrong_questions(r"old_path\bank.json", [1, 2])
        self.assertEqual(self.ud.get_wrong_history("new_path/bank.json"), [1, 2])

        self.ud.clear_wrong_history("new_path/bank.json")

        self.assertEqual(self.ud.get_wrong_history("new_path/bank.json"), [])

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


class TestSettingsService(unittest.TestCase):
    """SettingsService 测试"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.tmpdir.name, "settings.json")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_default_settings_when_file_missing(self):
        service = SettingsService(self.settings_file)
        self.assertEqual(service.get_app_name(), "灵测 LingCe")
        rules = service.get_exam_rules()
        self.assertEqual([r["type"] for r in rules], ["single", "multiple", "short"])
        self.assertFalse(service.get_ai_settings()["enabled"])
        self.assertEqual(service.get_ai_settings()["access_mode"], "api")

    def test_save_and_reload_settings(self):
        service = SettingsService(self.settings_file)
        settings = service.get_settings()
        settings["app"]["name"] = "自定义系统"
        settings["exam"]["time_limit"] = 45
        settings["exam"]["rules"] = [
            {"type": "single", "name": "单选题", "count": 5, "score": 4, "auto_score": True}
        ]
        service.save_settings(settings)

        reloaded = SettingsService(self.settings_file)
        self.assertEqual(reloaded.get_app_name(), "自定义系统")
        self.assertEqual(reloaded.get_exam_settings()["time_limit"], 45)
        self.assertEqual(reloaded.get_exam_rules()[0]["count"], 5)

    def test_invalid_json_falls_back_to_defaults(self):
        with open(self.settings_file, "w", encoding="utf-8") as f:
            f.write("{invalid json")

        service = SettingsService(self.settings_file)
        self.assertEqual(service.get_app_subtitle(), "通用考试练习平台")

    def test_validation_rejects_empty_app_name(self):
        service = SettingsService(self.settings_file)
        settings = service.get_settings()
        settings["app"]["name"] = ""
        with self.assertRaises(ValueError):
            service.save_settings(settings)

    def test_validation_rejects_negative_rule_count(self):
        service = SettingsService(self.settings_file)
        settings = service.get_settings()
        settings["exam"]["rules"][0]["count"] = -1
        with self.assertRaises(ValueError):
            service.save_settings(settings)

    def test_validation_rejects_non_numeric_score(self):
        service = SettingsService(self.settings_file)
        settings = service.get_settings()
        settings["exam"]["rules"][0]["score"] = "abc"
        with self.assertRaises(ValueError):
            service.save_settings(settings)

    def test_question_type_alias_matching(self):
        self.assertTrue(SettingsService.question_matches_rule("judgement", "judge"))
        self.assertTrue(SettingsService.question_matches_rule("essay", "short"))
        self.assertFalse(SettingsService.question_matches_rule("multiple", "single"))

    def test_reset_to_defaults_persists_default_settings(self):
        service = SettingsService(self.settings_file)
        settings = service.get_settings()
        settings["app"]["name"] = "自定义系统"
        service.save_settings(settings)

        service.reset_to_defaults()

        reloaded = SettingsService(self.settings_file)
        self.assertEqual(reloaded.get_app_name(), "灵测 LingCe")

    def test_export_and_import_settings(self):
        service = SettingsService(self.settings_file)
        settings = service.get_settings()
        settings["app"]["name"] = "导入导出测试"
        service.save_settings(settings)

        export_file = os.path.join(self.tmpdir.name, "exported-settings.json")
        service.export_settings(export_file)

        imported_file = os.path.join(self.tmpdir.name, "imported-settings.json")
        imported = SettingsService(imported_file)
        imported.import_settings(export_file)

        self.assertEqual(imported.get_app_name(), "导入导出测试")

    def test_ai_settings_require_connection_fields_when_enabled(self):
        service = SettingsService(self.settings_file)
        settings = service.get_settings()
        settings["ai"]["enabled"] = True
        settings["ai"]["api_key"] = ""

        with self.assertRaises(ValueError):
            service.save_settings(settings)

    def test_ai_provider_presets_separate_modes(self):
        coding_names = [item["name"] for item in get_providers("coding_plan")]
        api_names = [item["name"] for item in get_providers("api")]

        self.assertIn("智谱 GLM Coding Plan（国内）", coding_names)
        self.assertIn("DeepSeek", api_names)
        self.assertNotIn("DeepSeek", coding_names)

    def test_ai_keys_are_encrypted_on_disk_and_decrypted_on_load(self):
        service = SettingsService(self.settings_file)
        settings = service.get_settings()
        settings["ai"]["api_key"] = "sk-test-secret"
        settings["ai"]["api_keys"] = [
            {"id": "main", "name": "主 Key", "value": "sk-test-secret"}
        ]
        settings["ai"]["selected_key_id"] = "main"
        service.save_settings(settings)

        raw_text = Path(self.settings_file).read_text(encoding="utf-8")
        self.assertNotIn("sk-test-secret", raw_text)
        raw = json.loads(raw_text)
        self.assertTrue(raw["ai"]["api_key"].startswith("enc:"))
        self.assertTrue(raw["ai"]["api_keys"][0]["value"].startswith("enc:"))

        reloaded = SettingsService(self.settings_file)
        ai = reloaded.get_ai_settings()
        self.assertEqual(ai["api_key"], "sk-test-secret")
        self.assertEqual(ai["api_keys"][0]["value"], "sk-test-secret")
        self.assertEqual(ai["api_keys"][0]["access_mode"], "api")
        self.assertEqual(ai["api_keys"][0]["provider"], "deepseek")

    def test_legacy_single_ai_key_migrates_to_key_list(self):
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump({
                "app": {"name": "灵测 LingCe"},
                "exam": {"rules": [{"type": "single", "name": "单选题", "count": 1, "score": 1}]},
                "ai": {"api_key": "legacy-key"},
            }, f)

        service = SettingsService(self.settings_file)
        ai = service.get_ai_settings()

        self.assertEqual(ai["api_key"], "legacy-key")
        self.assertEqual(ai["api_keys"][0]["value"], "legacy-key")
        self.assertEqual(ai["api_keys"][0]["access_mode"], "api")

    def test_ai_keys_keep_provider_scope(self):
        service = SettingsService(self.settings_file)
        settings = service.get_settings()
        settings["ai"].update({
            "access_mode": "api",
            "provider": "deepseek",
            "provider_name": "DeepSeek",
            "api_key": "deepseek-key",
            "selected_key_id": "deepseek-main",
            "api_keys": [
                {
                    "id": "deepseek-main",
                    "name": "DeepSeek Key",
                    "value": "deepseek-key",
                    "access_mode": "api",
                    "provider": "deepseek",
                    "provider_name": "DeepSeek",
                },
                {
                    "id": "kimi-main",
                    "name": "Kimi Key",
                    "value": "kimi-key",
                    "access_mode": "api",
                    "provider": "kimi",
                    "provider_name": "Moonshot AI / Kimi",
                },
            ],
        })

        service.save_settings(settings)
        reloaded = SettingsService(self.settings_file)
        keys = reloaded.get_ai_settings()["api_keys"]

        self.assertEqual({item["provider"] for item in keys}, {"deepseek", "kimi"})
        self.assertEqual(reloaded.get_ai_settings()["api_key"], "deepseek-key")

    def test_ai_provider_model_history_is_preserved(self):
        service = SettingsService(self.settings_file)
        settings = service.get_settings()
        settings["ai"]["provider_models"] = {
            "api|deepseek": "deepseek-reasoner",
            "api|kimi": "moonshot-v1-32k",
        }
        service.save_settings(settings)

        reloaded = SettingsService(self.settings_file)
        history = reloaded.get_ai_settings()["provider_models"]

        self.assertEqual(history["api|deepseek"], "deepseek-reasoner")
        self.assertEqual(history["api|kimi"], "moonshot-v1-32k")


class TestAIService(unittest.TestCase):
    """AIService 测试"""

    def test_disabled_ai_rejects_call(self):
        service = AIService()
        with self.assertRaises(AIServiceError):
            service._chat([], service.get_ai_settings())

    def test_review_prompt_requires_independent_judgement(self):
        service = AIService()
        question = Question(
            id=1,
            type="single",
            question="测试题",
            options=["A. 选项一", "B. 选项二"],
            answer="A",
            explanation="测试解析",
        )

        prompt = service._build_review_prompt(question, "B")

        self.assertIn("不要默认题库答案正确", prompt)
        self.assertIn("题库答案：A", prompt)
        self.assertIn("用户答案：B", prompt)

    def test_parse_generated_answer_json_from_markdown_block(self):
        content = '```json\n{"answer":"B","explanation":"解析内容"}\n```'

        result = AIService._parse_answer_json(content)

        self.assertEqual(result["answer"], "B")
        self.assertEqual(result["explanation"], "解析内容")

    def test_parse_imported_question_drafts_json(self):
        content = """```json
[
  {
    "type": "single",
    "question": "测试题干",
    "options": ["A. 测试选项一", "B. 测试选项二"],
    "answer": "B",
    "explanation": "测试解析"
  }
]
```"""

        drafts = AIService._parse_question_drafts_json(content)

        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].type, "single")
        self.assertEqual(drafts[0].options, ["测试选项一", "测试选项二"])
        self.assertEqual(drafts[0].answer, "B")

    def test_split_source_text_chunks_long_content(self):
        text = "\n".join(f"段落{i}" for i in range(20))

        chunks = AIService._split_source_text(text, max_chars=20)

        self.assertGreater(len(chunks), 1)

    def test_question_import_repairs_invalid_json_once(self):
        class RepairAIService(AIService):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def _chat(self, messages, settings, max_tokens=None):
                self.calls += 1
                if self.calls == 1:
                    return "我生成了题目，但不是 JSON"
                return '[{"type":"single","question":"修复后的题干","options":["选项一","选项二"],"answer":"A","explanation":"解析"}]'

            def get_ai_settings(self):
                return {"enabled": True, "base_url": "http://example.test", "model": "test", "api_key": "test"}

        service = RepairAIService()

        drafts = service.generate_questions_from_text("资料内容")

        self.assertEqual(service.calls, 2)
        self.assertEqual(drafts[0].question, "修复后的题干")

    def test_generate_answer_prompt_requests_json(self):
        service = AIService()
        question = Question(
            id=1,
            type="multiple",
            question="多选题",
            options=["A. 一", "B. 二", "C. 三"],
        )

        prompt = service._build_generate_answer_prompt(question)

        self.assertIn("只返回 JSON", prompt)
        self.assertIn('"answer"', prompt)
        self.assertIn("答案返回多个选项字母", prompt)

    def test_parse_openai_compatible_model_list(self):
        data = {"data": [{"id": "model-b"}, {"id": "model-a"}]}

        models = AIService._parse_model_list(data)

        self.assertEqual(models, ["model-a", "model-b"])

    def test_parse_gemini_native_model_list(self):
        data = {
            "models": [
                {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
            ]
        }

        models = AIService._parse_model_list(data)

        self.assertEqual(models, ["gemini-2.0-flash"])


class TestQuestionService(unittest.TestCase):
    """QuestionService 测试"""

    def test_start_review_session_uses_given_questions(self):
        service = QuestionService()
        questions = [
            Question(id=1, type="single", question="Q1", options=["A. X", "B. Y"], answer="A"),
            Question(id=2, type="single", question="Q2", options=["A. X", "B. Y"], answer="B"),
        ]

        self.assertTrue(service.start_review_session(questions, "wrong"))
        self.assertEqual(service.get_practice_statistics()["total_questions"], 2)
        self.assertEqual(service.get_practice_statistics()["selected_type"], "wrong")

    def test_start_review_session_rejects_empty_list(self):
        service = QuestionService()

        self.assertFalse(service.start_review_session([], "wrong"))

    def test_filter_question_list_by_type_keeps_review_scope(self):
        questions = [
            Question(id=1, type="single", question="Q1", options=["A. X", "B. Y"], answer="A"),
            Question(id=2, type="multiple", question="Q2", options=["A. X", "B. Y"], answer="AB"),
            Question(id=3, type="judge", question="Q3", options=[], answer="A"),
        ]

        filtered = QuestionService.filter_question_list_by_type(questions, "single")

        self.assertEqual([question.id for question in filtered], [1])

    def test_wrong_review_pool_survives_filtered_review_session(self):
        bank = QuestionBank(
            questions=[
                Question(id=1, type="single", question="Q1"),
                Question(id=2, type="multiple", question="Q2"),
                Question(id=3, type="judge", question="Q3"),
            ],
            file_path="bank.json",
        )
        service = QuestionService()
        service.set_question_bank(bank)
        data_file = os.path.join(tempfile.gettempdir(), "wrong_pool_test.json")
        if os.path.exists(data_file):
            os.remove(data_file)
        user_data = UserDataService(data_file)

        try:
            user_data.add_wrong_questions("bank.json", [1, 2, 3])
            window = PracticeModeWindow.__new__(PracticeModeWindow)
            window.question_service = service
            window.user_data = user_data
            window.file_path = "bank.json"
            window._last_wrong_review_ids = set()

            single_wrong = service.filter_question_list_by_type(window._get_wrong_review_questions(), "single")
            self.assertTrue(service.start_review_session(single_wrong, "single"))
            window._last_wrong_review_ids = {1, 2, 3}

            all_wrong = window._get_wrong_review_questions()
            self.assertEqual([question.id for question in all_wrong], [1, 2, 3])
        finally:
            if os.path.exists(data_file):
                os.remove(data_file)


class TestDocumentImportService(unittest.TestCase):
    """DocumentImportService 测试"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.service = DocumentImportService()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_extract_text_file(self):
        path = Path(self.tmpdir.name) / "source.txt"
        path.write_text("第一行\n第二行", encoding="utf-8")

        text = self.service.extract_text(str(path))

        self.assertIn("第一行", text)
        self.assertIn("第二行", text)

    def test_extract_csv_file(self):
        path = Path(self.tmpdir.name) / "source.csv"
        path.write_text("题干,答案\n测试题,A", encoding="utf-8")

        text = self.service.extract_text(str(path))

        self.assertIn("题干\t答案", text)
        self.assertIn("测试题\tA", text)

    def test_extract_docx_file(self):
        path = Path(self.tmpdir.name) / "source.docx"
        xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Word 测试内容</w:t></w:r></w:p>
  </w:body>
</w:document>"""
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", xml)

        text = self.service.extract_text(str(path))

        self.assertIn("Word 测试内容", text)

    def test_extract_xlsx_file(self):
        path = Path(self.tmpdir.name) / "source.xlsx"
        shared = """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <si><t>题干</t></si>
  <si><t>测试答案</t></si>
</sst>"""
        sheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row><c t="s"><v>0</v></c><c t="s"><v>1</v></c></row>
  </sheetData>
</worksheet>"""
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("xl/sharedStrings.xml", shared)
            archive.writestr("xl/worksheets/sheet1.xml", sheet)

        text = self.service.extract_text(str(path))

        self.assertIn("题干\t测试答案", text)


class TestQuestionBankBuilder(unittest.TestCase):
    """QuestionBankBuilder 测试"""

    def test_build_question_bank_from_manual_drafts(self):
        builder = QuestionBankBuilder()
        drafts = [
            QuestionDraft(
                type="single",
                question="单选题题干",
                options=["选项一", "选项二"],
                answer="A",
                explanation="解析",
            ),
            QuestionDraft(
                type="judgement",
                question="判断题题干",
                answer="正确",
            ),
            QuestionDraft(
                type="short",
                question="简答题题干",
                answer="参考答案",
            ),
        ]

        bank = builder.build_question_bank(drafts)

        self.assertEqual(len(bank.questions), 3)
        self.assertEqual(bank.questions[0].id, 1)
        self.assertEqual(bank.questions[0].options, ["A. 选项一", "B. 选项二"])
        self.assertEqual(bank.questions[1].type, "judgement")
        self.assertEqual(bank.questions[1].answer, "正确")

    def test_rejects_invalid_choice_answer(self):
        builder = QuestionBankBuilder()
        draft = QuestionDraft(
            type="single",
            question="题干",
            options=["选项一", "选项二"],
            answer="C",
        )

        with self.assertRaises(ValueError):
            builder.build_question_bank([draft])

    def test_question_summary_truncates_text(self):
        builder = QuestionBankBuilder()
        draft = QuestionDraft(type="single", question="题干" * 20)
        summary = builder.question_summary(draft)
        self.assertIn("单选题", summary)
        self.assertTrue(summary.endswith("…"))


class TestExamModeWindowLogic(unittest.TestCase):
    """ExamModeWindow 轻量逻辑测试"""

    def test_review_mode_does_not_overwrite_saved_answer(self):
        window = ExamModeWindow.__new__(ExamModeWindow)
        window.is_review_mode = True
        window.current_question = Question(id=1, type="judge", question="Q", answer="A")
        window._question_widget = object()
        window.exam_answers = {1: "B"}

        window._save_current_answer()

        self.assertEqual(window.exam_answers[1], "B")

    def test_judge_option_b_matches_chinese_wrong_answer(self):
        question = Question(id=1, type="judge", question="Q", answer="错误")
        self.assertTrue(ExamModeWindow._check_correct(question, "B", question.answer))


class TestExamDbService(unittest.TestCase):
    """考试统计数据库服务测试"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.old_db_dir = exam_db.DB_DIR
        self.old_db_file = exam_db.DB_FILE
        exam_db.DB_DIR = Path(self.tmpdir.name)
        exam_db.DB_FILE = exam_db.DB_DIR / "exam_history.db"

    def tearDown(self):
        exam_db.DB_DIR = self.old_db_dir
        exam_db.DB_FILE = self.old_db_file
        self.tmpdir.cleanup()

    def test_clear_exam_records(self):
        exam_db.init_db()
        exam_db.save_exam_record(80, 10, 8)
        self.assertEqual(len(exam_db.query_all()), 1)

        exam_db.clear_exam_records()

        self.assertEqual(exam_db.query_all(), [])


if __name__ == "__main__":
    unittest.main()
