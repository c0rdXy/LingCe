#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 复核服务。"""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from core.ai_presets import get_default_ai_settings
from core.models import Question
from core.utils import format_judge_answer, get_question_type_name
from services.settings_service import SettingsService


class AIServiceError(RuntimeError):
    """AI 服务调用失败。"""


class AIService:
    """调用 OpenAI 兼容接口完成题目复核和追问。"""

    def __init__(self, settings_service: Optional[SettingsService] = None):
        self.settings_service = settings_service or SettingsService()

    def get_ai_settings(self) -> Dict[str, Any]:
        """返回 AI 设置。"""
        settings = self.settings_service.get_settings().get("ai", {})
        default = get_default_ai_settings()
        default.update(settings or {})
        return default

    def test_connection(self, settings: Optional[Dict[str, Any]] = None) -> str:
        """测试 AI 连接。"""
        ai_settings = settings or self.get_ai_settings()
        messages = [
            {"role": "system", "content": "你是 LingCe 的 AI 连接测试助手。"},
            {"role": "user", "content": "请只回复：连接成功"},
        ]
        return self._chat(messages, ai_settings, max_tokens=32)

    def review_question(
        self,
        question: Question,
        user_answer: str = "",
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """复核当前题目。"""
        prompt = self._build_review_prompt(question, user_answer)
        return self._chat(self._build_messages(prompt, history), self.get_ai_settings())

    def ask_followup(
        self,
        question: Question,
        user_answer: str,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """围绕当前题目继续追问。"""
        prompt = self._build_followup_prompt(question, user_answer, user_message)
        return self._chat(self._build_messages(prompt, history), self.get_ai_settings())

    def generate_answer_and_explanation(self, question: Question) -> Dict[str, str]:
        """为题目生成答案和解析。"""
        prompt = self._build_generate_answer_prompt(question)
        response = self._chat(self._build_messages(prompt, []), self.get_ai_settings())
        return self._parse_answer_json(response)

    def _chat(
        self,
        messages: List[Dict[str, str]],
        settings: Dict[str, Any],
        max_tokens: Optional[int] = None,
    ) -> str:
        if not settings.get("enabled", False):
            raise AIServiceError("AI 功能未启用，请先在系统设置中开启")
        base_url = str(settings.get("base_url") or "").strip().rstrip("/")
        model = str(settings.get("model") or "").strip()
        api_key = str(settings.get("api_key") or "").strip()
        if not base_url:
            raise AIServiceError("Base URL 不能为空")
        if not model or model in {"需手动填写", "自定义模型", "需填写方舟 Endpoint ID"}:
            raise AIServiceError("模型名称不能为空")
        if not api_key:
            raise AIServiceError("API Key / Token 不能为空")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": float(settings.get("temperature", 0.2)),
            "max_tokens": int(max_tokens or settings.get("max_tokens", 2000)),
        }
        url = f"{base_url}/chat/completions"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=int(settings.get("timeout", 60)),
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise AIServiceError(f"AI 请求失败：HTTP {exc.code} {detail[:300]}") from exc
        except urllib.error.URLError as exc:
            raise AIServiceError(f"AI 连接失败：{exc.reason}") from exc
        except (TimeoutError, ValueError, OSError) as exc:
            raise AIServiceError(f"AI 调用失败：{exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIServiceError("AI 返回格式无法识别") from exc
        return str(content).strip()

    def _build_messages(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 LingCe 的题库复核助手。你的任务是独立判断题目、答案和解析是否可靠。"
                    "不要默认题库答案正确；不确定时必须说明需要人工确认。"
                ),
            }
        ]
        for item in (history or [])[-8:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _build_review_prompt(self, question: Question, user_answer: str) -> str:
        options = "\n".join(question.options) if question.options else "无"
        correct_answer = question.answer
        if question.type in ("judge", "judgement"):
            correct_answer = format_judge_answer(question.answer)
            user_answer = format_judge_answer(user_answer) if user_answer else ""
        return f"""请复核下面这道题。

要求：
1. 先独立判断正确答案，不要默认题库答案正确。
2. 再对比题库答案和题库解析。
3. 检查题干、选项、答案、解析是否存在错误、歧义或信息不足。
4. 如果无法确定，请明确写“需要人工确认”。
5. 请按固定结构输出：复核结论、题库答案、AI 建议答案、置信度、问题分析、建议修改。

题型：{get_question_type_name(question.type)}
题干：{question.question}
选项：
{options}
题库答案：{correct_answer}
用户答案：{user_answer or "未提供"}
题库解析：{question.explanation or "无"}
"""

    def _build_followup_prompt(self, question: Question, user_answer: str, user_message: str) -> str:
        options = "\n".join(question.options) if question.options else "无"
        correct_answer = question.answer
        if question.type in ("judge", "judgement"):
            correct_answer = format_judge_answer(question.answer)
            user_answer = format_judge_answer(user_answer) if user_answer else ""
        return f"""请继续围绕当前题目回答用户追问。

回答要求：
1. 只讨论当前题目和相关知识点。
2. 不要默认题库答案正确。
3. 如果追问涉及改答案或改解析，请给出理由，并提示需要人工确认。

题型：{get_question_type_name(question.type)}
题干：{question.question}
选项：
{options}
题库答案：{correct_answer}
用户答案：{user_answer or "未提供"}
题库解析：{question.explanation or "无"}

用户追问：{user_message}
"""

    def _build_generate_answer_prompt(self, question: Question) -> str:
        options = "\n".join(question.options) if question.options else "无"
        answer_rule = {
            "single": "答案只返回一个选项字母，如 A。",
            "multiple": "答案返回多个选项字母并按字母顺序排列，如 ABC。",
            "judgement": "答案只返回“正确”或“错误”。",
            "judge": "答案只返回“正确”或“错误”。",
            "fill": "答案返回填空题标准答案。",
            "short": "答案返回简答题参考答案。",
            "essay": "答案返回简答题参考答案。",
        }.get(question.type, "答案返回标准答案。")
        return f"""请为下面这道题生成标准答案和解析。

要求：
1. 请独立判断答案，不要迎合已有空白答案。
2. 如果题目信息不足，请在解析中说明需要人工确认。
3. {answer_rule}
4. 只返回 JSON，不要返回 Markdown，不要添加额外说明。

JSON 格式：
{{"answer":"...","explanation":"..."}}

题型：{get_question_type_name(question.type)}
题干：{question.question}
选项：
{options}
"""

    @staticmethod
    def _parse_answer_json(content: str) -> Dict[str, str]:
        """解析 AI 生成的答案 JSON。"""
        text = (content or "").strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIServiceError("AI 返回的答案解析不是有效 JSON") from exc
        answer = str(data.get("answer", "")).strip()
        explanation = str(data.get("explanation", "")).strip()
        if not answer and not explanation:
            raise AIServiceError("AI 未返回答案或解析")
        return {"answer": answer, "explanation": explanation}
