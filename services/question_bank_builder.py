#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手工题库创建服务。"""

from dataclasses import dataclass, field
from typing import List

from core.models import Question, QuestionBank
from core.utils import normalize_judge_answer


QUESTION_TYPE_LABELS = {
    "single": "单选题",
    "multiple": "多选题",
    "judgement": "判断题",
    "fill": "填空题",
    "short": "简答题",
}

CHOICE_TYPES = {"single", "multiple"}


@dataclass
class QuestionDraft:
    """题库编辑器中的题目草稿。"""

    type: str = "single"
    question: str = ""
    options: List[str] = field(default_factory=lambda: ["", "", "", ""])
    answer: str = ""
    explanation: str = ""


class QuestionBankBuilder:
    """校验题目草稿并生成标准题库。"""

    @staticmethod
    def new_draft(question_type: str = "single") -> QuestionDraft:
        """创建新的空白题目草稿。"""
        draft = QuestionDraft(type=question_type)
        if question_type == "judgement":
            draft.options = []
        elif question_type not in CHOICE_TYPES:
            draft.options = []
        return draft

    @staticmethod
    def duplicate_draft(draft: QuestionDraft) -> QuestionDraft:
        """复制题目草稿。"""
        return QuestionDraft(
            type=draft.type,
            question=draft.question,
            options=list(draft.options),
            answer=draft.answer,
            explanation=draft.explanation,
        )

    @staticmethod
    def question_summary(draft: QuestionDraft) -> str:
        """生成题目列表中的摘要文本。"""
        title = (draft.question or "").strip().replace("\n", " ")
        if not title:
            title = "未填写题干"
        if len(title) > 28:
            title = title[:28] + "…"
        return f"[{QUESTION_TYPE_LABELS.get(draft.type, draft.type)}] {title}"

    @classmethod
    def build_question(cls, draft: QuestionDraft, question_id: int) -> Question:
        """将草稿转换成标准 Question。"""
        errors = cls.validate_draft(draft)
        if errors:
            raise ValueError("\n".join(errors))

        qtype = draft.type
        options = cls.normalize_options(qtype, draft.options)
        answer = cls.normalize_answer(qtype, draft.answer)
        return Question(
            id=question_id,
            type=qtype,
            question=draft.question.strip(),
            options=options,
            answer=answer,
            explanation=draft.explanation.strip(),
        )

    @classmethod
    def build_question_bank(cls, drafts: List[QuestionDraft], file_path: str = "") -> QuestionBank:
        """将草稿列表转换成标准题库。"""
        if not drafts:
            raise ValueError("题库至少需要包含一道题目")

        questions = []
        all_errors = []
        for index, draft in enumerate(drafts, start=1):
            errors = cls.validate_draft(draft)
            if errors:
                all_errors.extend(f"第{index}题：{error}" for error in errors)
                continue
            questions.append(cls.build_question(draft, index))

        if all_errors:
            raise ValueError("\n".join(all_errors[:20]))

        return QuestionBank(questions=questions, file_path=file_path or None)

    @classmethod
    def validate_draft(cls, draft: QuestionDraft) -> List[str]:
        """校验题目草稿。"""
        errors = []
        qtype = draft.type
        if qtype not in QUESTION_TYPE_LABELS:
            errors.append("题型无效")
        if not draft.question.strip():
            errors.append("题干不能为空")

        answer = draft.answer.strip()
        if qtype in CHOICE_TYPES:
            options = cls.normalize_options(qtype, draft.options)
            if len(options) < 2:
                errors.append("选择题至少需要两个选项")
            option_letters = {option.split(".", 1)[0].strip().upper() for option in options if "." in option}
            answer_letters = set(answer.upper().replace(" ", ""))
            if qtype == "single" and len(answer_letters) != 1:
                errors.append("单选题答案只能填写一个选项字母")
            if qtype == "multiple" and not answer_letters:
                errors.append("多选题答案至少填写一个选项字母")
            if answer_letters and not answer_letters.issubset(option_letters):
                errors.append("答案选项必须存在于选项列表中")
        elif qtype == "judgement":
            if normalize_judge_answer(answer) not in {"A", "B"}:
                errors.append("判断题答案必须是正确或错误")
        elif not answer:
            errors.append("答案不能为空")

        return errors

    @staticmethod
    def normalize_options(question_type: str, options: List[str]) -> List[str]:
        """规范化选项文本。"""
        if question_type == "judgement":
            return ["A. 正确", "B. 错误"]
        if question_type not in CHOICE_TYPES:
            return []

        normalized = []
        next_letter = ord("A")
        for raw in options:
            text = str(raw or "").strip()
            if not text:
                next_letter += 1
                continue
            if len(text) >= 2 and text[0].isalpha() and text[1] in {".", "、", "．", " "}: 
                letter = text[0].upper()
                body = text[2:].strip()
            else:
                letter = chr(next_letter)
                body = text
            normalized.append(f"{letter}. {body}")
            next_letter = ord(letter) + 1
        return normalized

    @staticmethod
    def normalize_answer(question_type: str, answer: str) -> str:
        """规范化答案。"""
        value = str(answer or "").strip()
        if question_type in CHOICE_TYPES:
            letters = [ch for ch in value.upper() if ch.isalpha()]
            if question_type == "single":
                return letters[0] if letters else ""
            return "".join(dict.fromkeys(letters))
        if question_type == "judgement":
            return normalize_judge_answer(value)
        return value
