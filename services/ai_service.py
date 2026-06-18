#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 复核服务。"""

import json
import urllib.error
import urllib.request
from urllib.parse import urlencode
from typing import Any, Dict, List, Optional

from core.ai_presets import get_default_ai_settings
from core.models import Question
from core.utils import format_judge_answer, get_question_type_name
from services.question_bank_builder import QuestionDraft
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

    def list_models(self, settings: Optional[Dict[str, Any]] = None) -> List[str]:
        """获取当前接入地址可用模型列表。"""
        ai_settings = settings or self.get_ai_settings()
        base_url = str(ai_settings.get("base_url") or "").strip().rstrip("/")
        api_key = str(ai_settings.get("api_key") or "").strip()
        if not base_url:
            raise AIServiceError("Base URL 不能为空")
        if not api_key:
            raise AIServiceError("API Key / Token 不能为空")

        try:
            return self._list_openai_compatible_models(base_url, api_key, int(ai_settings.get("timeout", 60)))
        except AIServiceError as first_error:
            if "generativelanguage.googleapis.com" in base_url:
                try:
                    return self._list_gemini_native_models(api_key, int(ai_settings.get("timeout", 60)))
                except AIServiceError:
                    pass
            raise first_error

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

    def generate_questions_from_text(
        self,
        source_text: str,
        question_count: str = "auto",
        question_types: Optional[List[str]] = None,
        include_explanation: bool = True,
        difficulty: str = "auto",
    ) -> List[QuestionDraft]:
        """将资料文本解析为题目草稿。"""
        chunks = self._split_source_text(source_text)
        if not chunks:
            raise AIServiceError("请先提供可解析的资料内容")

        all_drafts = []
        for index, chunk in enumerate(chunks, start=1):
            prompt = self._build_question_import_prompt(
                chunk,
                question_count,
                question_types or [],
                include_explanation,
                difficulty,
                index,
                len(chunks),
            )
            response = self._chat(
                self._build_messages(prompt, []),
                self.get_ai_settings(),
                max_tokens=3500,
            )
            all_drafts.extend(self._parse_question_drafts_with_repair(response, prompt))

        unique = []
        seen_questions = set()
        for draft in all_drafts:
            key = draft.question.strip()
            if key and key not in seen_questions:
                seen_questions.add(key)
                unique.append(draft)
        if not unique:
            raise AIServiceError("AI 未生成有效题目")
        return unique

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

    def _list_openai_compatible_models(self, base_url: str, api_key: str, timeout: int) -> List[str]:
        """通过 OpenAI 兼容接口获取模型列表。"""
        request = urllib.request.Request(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise AIServiceError(f"获取模型失败：HTTP {exc.code} {detail[:300]}") from exc
        except urllib.error.URLError as exc:
            raise AIServiceError(f"获取模型失败：{exc.reason}") from exc
        except (TimeoutError, ValueError, OSError) as exc:
            raise AIServiceError(f"获取模型失败：{exc}") from exc
        return self._parse_model_list(data)

    def _list_gemini_native_models(self, api_key: str, timeout: int) -> List[str]:
        """通过 Gemini 原生接口获取模型列表。"""
        query = urlencode({"key": api_key})
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models?{query}",
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise AIServiceError(f"获取 Gemini 模型失败：HTTP {exc.code} {detail[:300]}") from exc
        except urllib.error.URLError as exc:
            raise AIServiceError(f"获取 Gemini 模型失败：{exc.reason}") from exc
        except (TimeoutError, ValueError, OSError) as exc:
            raise AIServiceError(f"获取 Gemini 模型失败：{exc}") from exc
        return self._parse_model_list(data)

    @staticmethod
    def _parse_model_list(data: Dict[str, Any]) -> List[str]:
        """解析不同接口返回的模型列表。"""
        raw_models = data.get("data")
        if raw_models is None:
            raw_models = data.get("models")
        if not isinstance(raw_models, list):
            raise AIServiceError("模型列表返回格式无法识别")

        models = []
        for item in raw_models:
            if isinstance(item, str):
                model_id = item
            elif isinstance(item, dict):
                model_id = item.get("id") or item.get("name") or item.get("model")
                methods = item.get("supportedGenerationMethods")
                if methods and "generateContent" not in methods:
                    continue
            else:
                continue
            if not model_id:
                continue
            model_id = str(model_id)
            if model_id.startswith("models/"):
                model_id = model_id.split("/", 1)[1]
            models.append(model_id)

        unique = sorted(dict.fromkeys(models))
        if not unique:
            raise AIServiceError("没有获取到可用模型")
        return unique

    def _build_messages(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        messages = [
            {"role": "system", "content": self._system_prompt()}
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

    def _parse_question_drafts_with_repair(self, response: str, original_prompt: str) -> List[QuestionDraft]:
        """解析题库 JSON，失败时让 AI 自动修复一次格式。"""
        try:
            return self._parse_question_drafts_json(response)
        except AIServiceError as first_error:
            repair_prompt = self._build_json_repair_prompt(response)
            try:
                repaired = self._chat(
                    self._build_messages(repair_prompt, [{"role": "user", "content": original_prompt}]),
                    self.get_ai_settings(),
                    max_tokens=3500,
                )
                return self._parse_question_drafts_json(repaired)
            except AIServiceError as second_error:
                raise AIServiceError(f"{first_error}；自动修复失败：{second_error}") from second_error

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是 LingCe 的题库助手。需要复核题目时，必须独立判断题目、答案和解析是否可靠，"
            "不要默认题库答案正确；不确定时必须说明需要人工确认。"
            "需要生成或修复题库 JSON 时，必须只输出可被 json.loads 解析的 JSON，"
            "不要输出 Markdown 代码块、解释、前后缀或注释。"
        )

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

    def _build_question_import_prompt(
        self,
        source_text: str,
        question_count: str,
        question_types: List[str],
        include_explanation: bool,
        difficulty: str,
        chunk_index: int,
        chunk_count: int,
    ) -> str:
        type_names = {
            "single": "单选题",
            "multiple": "多选题",
            "judgement": "判断题",
            "fill": "填空题",
            "short": "简答题",
        }
        requested_types = "、".join(type_names.get(item, item) for item in question_types) or "自动选择合适题型"
        explanation_rule = "每题都生成解析" if include_explanation else "解析可为空"
        count_rule = "自动生成适量题目" if question_count == "auto" else f"尽量生成 {question_count} 道题"
        difficulty_rule = {
            "easy": "简单",
            "normal": "普通",
            "hard": "困难",
        }.get(difficulty, "自动判断")
        return f"""请把下面资料转换为 LingCe 本地题库题目。

要求：
1. 只根据资料内容出题，不要编造资料中没有依据的事实。
2. {count_rule}，当前为第 {chunk_index}/{chunk_count} 段资料。
3. 题型范围：{requested_types}。
4. 难度：{difficulty_rule}。
5. {explanation_rule}。
6. 单选题 type 为 single，答案为一个选项字母，如 A。
7. 多选题 type 为 multiple，答案为多个选项字母并按字母顺序排列，如 ABC。
8. 判断题 type 为 judgement，答案只写“正确”或“错误”。
9. 填空题 type 为 fill，简答题 type 为 short。
10. 选择题 options 只写选项内容，不要带 A./B./C. 前缀。
11. 只返回 JSON 数组，不要返回 Markdown，不要添加额外说明。
12. 输出必须以 [ 开头，以 ] 结尾。

JSON 数组格式：
[
  {{"type":"single","question":"题干","options":["选项一","选项二","选项三","选项四"],"answer":"A","explanation":"解析"}},
  {{"type":"judgement","question":"题干","options":[],"answer":"正确","explanation":"解析"}}
]

资料内容：
{source_text}
"""

    @staticmethod
    def _build_json_repair_prompt(raw_response: str) -> str:
        return f"""下面内容本应是 LingCe 题库 JSON 数组，但格式无法解析。

请把它修复为严格 JSON 数组，只返回 JSON，不要返回 Markdown，不要解释。

字段要求：
- type 只能是 single、multiple、judgement、fill、short
- question 必须是字符串
- options 必须是字符串数组；非选择题可为空数组
- answer 必须是字符串
- explanation 必须是字符串

需要修复的内容：
{raw_response}
"""

    @staticmethod
    def _split_source_text(source_text: str, max_chars: int = 6000) -> List[str]:
        """按段落把长文本切成适合模型处理的片段。"""
        paragraphs = [line.strip() for line in str(source_text or "").splitlines() if line.strip()]
        chunks = []
        current = []
        current_length = 0
        for paragraph in paragraphs:
            if current and current_length + len(paragraph) + 1 > max_chars:
                chunks.append("\n".join(current))
                current = []
                current_length = 0
            current.append(paragraph)
            current_length += len(paragraph) + 1
        if current:
            chunks.append("\n".join(current))
        return chunks

    @classmethod
    def _parse_question_drafts_json(cls, content: str) -> List[QuestionDraft]:
        """解析 AI 返回的题目草稿 JSON。"""
        data = cls._load_json_from_ai_response(content)
        if isinstance(data, dict):
            data = data.get("questions", [])
        if not isinstance(data, list):
            raise AIServiceError("AI 返回的题库不是 JSON 数组")

        drafts = []
        aliases = {
            "judge": "judgement",
            "essay": "short",
        }
        valid_types = {"single", "multiple", "judgement", "fill", "short"}
        for item in data:
            if not isinstance(item, dict):
                continue
            qtype = aliases.get(str(item.get("type", "single")).strip(), str(item.get("type", "single")).strip())
            if qtype not in valid_types:
                qtype = "single"
            raw_options = item.get("options", [])
            if not isinstance(raw_options, list):
                raw_options = []
            options = [cls._strip_option_prefix(str(option)) for option in raw_options if str(option).strip()]
            if qtype not in {"single", "multiple"}:
                options = []
            drafts.append(QuestionDraft(
                type=qtype,
                question=str(item.get("question", "")).strip(),
                options=options,
                answer=str(item.get("answer", "")).strip(),
                explanation=str(item.get("explanation", "")).strip(),
            ))

        if not drafts:
            raise AIServiceError("AI 未返回有效题目")
        return drafts

    @staticmethod
    def _strip_option_prefix(option: str) -> str:
        text = option.strip()
        if len(text) >= 2 and text[0].isalpha() and text[1] in {".", "、", "．", " "}:
            return text[2:].strip()
        return text

    @staticmethod
    def _load_json_from_ai_response(content: str) -> Any:
        """从 AI 响应中提取 JSON 对象或数组。"""
        text = (content or "").strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        starts = [index for index in (text.find("["), text.find("{")) if index != -1]
        if starts:
            start = min(starts)
            end = max(text.rfind("]"), text.rfind("}"))
            if end > start:
                text = text[start:end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIServiceError("AI 返回内容不是有效 JSON") from exc

    @staticmethod
    def _parse_answer_json(content: str) -> Dict[str, str]:
        """解析 AI 生成的答案 JSON。"""
        data = AIService._load_json_from_ai_response(content)
        if not isinstance(data, dict):
            raise AIServiceError("AI 返回的答案解析不是有效 JSON")
        answer = str(data.get("answer", "")).strip()
        explanation = str(data.get("explanation", "")).strip()
        if not answer and not explanation:
            raise AIServiceError("AI 未返回答案或解析")
        return {"answer": answer, "explanation": explanation}
