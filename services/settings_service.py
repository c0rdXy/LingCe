#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统设置服务。"""

import json
import base64
import hashlib
import getpass
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.ai_presets import get_default_ai_settings
from core.default_settings import get_default_settings, merge_with_defaults


_DEFAULT_SETTINGS_FILE = Path("data") / "settings.json"

QUESTION_TYPE_ALIASES = {
    "single": ("single",),
    "multiple": ("multiple",),
    "judge": ("judge", "judgement"),
    "fill": ("fill",),
    "short": ("short", "essay"),
}

SUPPORTED_RULE_TYPES = ("single", "multiple", "judge", "fill", "short")


class SettingsService:
    """读取、校验和保存系统设置。"""

    def __init__(self, settings_file: Optional[str] = None):
        self.settings_file = Path(settings_file) if settings_file else _DEFAULT_SETTINGS_FILE
        self._settings: Dict[str, Any] = {}
        self._load()

    def _load(self):
        """加载设置文件，失败时回退到默认设置。"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    self._settings = merge_with_defaults(json.load(f))
            except (json.JSONDecodeError, OSError):
                self._settings = get_default_settings()
        else:
            self._settings = get_default_settings()
        self._settings["exam"]["rules"] = self._normalize_rules(self._settings["exam"].get("rules", []))
        self._settings["ai"] = self._normalize_ai_settings(self._settings.get("ai", {}))

    def reload(self):
        """重新加载设置。"""
        self._load()

    def has_settings_file(self) -> bool:
        """设置文件是否已经存在。"""
        return self.settings_file.exists()

    def get_settings(self) -> Dict[str, Any]:
        """返回完整设置副本。"""
        return deepcopy(self._settings)

    def get_app_settings(self) -> Dict[str, Any]:
        """返回应用基础设置。"""
        return deepcopy(self._settings.get("app", {}))

    def set_runtime_default_theme(self, theme_name: str):
        """设置运行时默认主题。"""
        self._settings.setdefault("app", {})["default_theme"] = theme_name

    def get_exam_settings(self) -> Dict[str, Any]:
        """返回考试设置。"""
        return deepcopy(self._settings.get("exam", {}))

    def get_ai_settings(self) -> Dict[str, Any]:
        """返回 AI 设置。"""
        return deepcopy(self._settings.get("ai", get_default_ai_settings()))

    def get_exam_rules(self) -> List[Dict[str, Any]]:
        """返回启用的考试规则。"""
        return [deepcopy(r) for r in self._settings.get("exam", {}).get("rules", []) if r.get("count", 0) > 0]

    def get_app_name(self) -> str:
        """返回应用名称。"""
        return self._settings.get("app", {}).get("name", "灵测 LingCe").strip() or "灵测 LingCe"

    def get_app_subtitle(self) -> str:
        """返回首页副标题。"""
        return self._settings.get("app", {}).get("subtitle", "灵测通用考试练习平台")

    def get_window_title(self, suffix: str = "") -> str:
        """返回窗口标题。"""
        title = self.get_app_name()
        if suffix:
            title = f"{title} - {suffix}"
        return title

    def should_show_version(self) -> bool:
        """首页是否显示版本号。"""
        return bool(self._settings.get("app", {}).get("show_version", True))

    def get_question_type_name(self, type_key: str) -> str:
        """返回配置中的题型显示名。"""
        for rule in self._settings.get("exam", {}).get("rules", []):
            if rule.get("type") == type_key:
                return rule.get("name", type_key)
        defaults = {
            "all": "全部题型",
            "single": "单选题",
            "multiple": "多选题",
            "judge": "判断题",
            "judgement": "判断题",
            "fill": "填空题",
            "short": "简答题",
            "essay": "简答题",
        }
        return defaults.get(type_key, type_key)

    def save_settings(self, settings: Dict[str, Any]):
        """校验并保存设置。"""
        merged = merge_with_defaults(settings)
        errors = self.validate_settings(merged)
        if errors:
            raise ValueError("\n".join(errors))
        normalized = merge_with_defaults(settings)
        normalized["exam"]["rules"] = self._normalize_rules(normalized["exam"].get("rules", []))
        normalized["ai"] = self._normalize_ai_settings(normalized.get("ai", {}))
        stored = deepcopy(normalized)
        stored["ai"] = self._encrypt_ai_keys(stored.get("ai", {}))
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(stored, f, ensure_ascii=False, indent=2)
        self._settings = normalized

    def reset_to_defaults(self):
        """恢复并保存默认设置。"""
        self.save_settings(get_default_settings())

    def export_settings(self, file_path: str):
        """导出当前设置到指定 JSON 文件。"""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        export_data = deepcopy(self._settings)
        export_data["ai"] = self._encrypt_ai_keys(export_data.get("ai", {}))
        with open(target, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    def import_settings(self, file_path: str):
        """从 JSON 文件导入设置，导入前会执行完整校验。"""
        with open(file_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        if not isinstance(settings, dict):
            raise ValueError("设置文件格式错误：根节点必须是对象")
        self.save_settings(settings)

    def validate_settings(self, settings: Optional[Dict[str, Any]] = None) -> List[str]:
        """返回设置校验错误列表。"""
        data = settings or self._settings
        errors: List[str] = []
        app = data.get("app", {})
        exam = data.get("exam", {})
        ai = data.get("ai", {})
        rules = exam.get("rules", [])

        if not str(app.get("name", "")).strip():
            errors.append("系统名称不能为空")
        time_limit = _parse_int(exam.get("time_limit"))
        pass_score = _parse_float(exam.get("pass_score"))
        if time_limit is None or time_limit <= 0:
            errors.append("考试时长必须大于 0")
        if pass_score is None or pass_score < 0:
            errors.append("及格分不能小于 0")
        parsed_counts = [_parse_int(rule.get("count")) for rule in rules]
        if not rules or all((count or 0) <= 0 for count in parsed_counts):
            errors.append("至少需要启用一种考试题型")

        for rule in rules:
            rule_type = rule.get("type")
            if rule_type not in SUPPORTED_RULE_TYPES:
                errors.append(f"不支持的题型：{rule_type}")
            count = _parse_int(rule.get("count"))
            score = _parse_float(rule.get("score"))
            if count is None or count < 0:
                errors.append(f"{rule.get('name', rule_type)} 的题数不能小于 0")
            if score is None or score < 0:
                errors.append(f"{rule.get('name', rule_type)} 的分值不能小于 0")

        if ai.get("enabled", False):
            if not str(ai.get("base_url", "")).strip():
                errors.append("启用 AI 时 Base URL 不能为空")
            if not str(ai.get("model", "")).strip():
                errors.append("启用 AI 时模型名称不能为空")
            if not str(ai.get("api_key", "")).strip():
                errors.append("启用 AI 时 API Key / Token 不能为空")
            timeout = _parse_int(ai.get("timeout"))
            max_tokens = _parse_int(ai.get("max_tokens"))
            temperature = _parse_float(ai.get("temperature"))
            if timeout is None or timeout <= 0:
                errors.append("AI 超时时间必须大于 0")
            if max_tokens is None or max_tokens <= 0:
                errors.append("AI 最大输出 Token 必须大于 0")
            if temperature is None or temperature < 0:
                errors.append("AI 温度不能小于 0")
        return errors

    @staticmethod
    def question_matches_rule(question_type: str, rule_type: str) -> bool:
        """判断题目类型是否匹配规则类型。"""
        return question_type in QUESTION_TYPE_ALIASES.get(rule_type, (rule_type,))

    @staticmethod
    def get_supported_rule_types() -> List[Dict[str, Any]]:
        """返回设置界面支持的题型定义。"""
        names = {
            "single": "单选题",
            "multiple": "多选题",
            "judge": "判断题",
            "fill": "填空题",
            "short": "简答题",
        }
        return [{"type": key, "name": names[key]} for key in SUPPORTED_RULE_TYPES]

    def _normalize_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """规范化规则，保留支持题型并补齐设置界面需要的类型。"""
        normalized_by_type: Dict[str, Dict[str, Any]] = {}
        default_by_type = {
            rule["type"]: rule for rule in get_default_settings()["exam"]["rules"]
        }
        default_names = {item["type"]: item["name"] for item in self.get_supported_rule_types()}

        for raw in rules:
            rule_type = raw.get("type")
            if rule_type not in SUPPORTED_RULE_TYPES:
                continue
            base = deepcopy(default_by_type.get(rule_type, {
                "type": rule_type,
                "name": default_names.get(rule_type, rule_type),
                "count": 0,
                "score": 0,
                "auto_score": rule_type != "short",
            }))
            base.update(raw)
            base["type"] = rule_type
            base["name"] = str(base.get("name") or default_names.get(rule_type, rule_type))
            base["count"] = max(0, _to_int(base.get("count"), 0))
            base["score"] = max(0.0, _to_float(base.get("score"), 0))
            base["auto_score"] = bool(base.get("auto_score"))
            normalized_by_type[rule_type] = base

        for item in self.get_supported_rule_types():
            rule_type = item["type"]
            if rule_type not in normalized_by_type:
                normalized_by_type[rule_type] = {
                    "type": rule_type,
                    "name": item["name"],
                    "count": 0,
                    "score": 0,
                    "auto_score": rule_type != "short",
                }

        return [normalized_by_type[rule_type] for rule_type in SUPPORTED_RULE_TYPES]

    def _normalize_ai_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """规范化 AI 设置。"""
        normalized = get_default_ai_settings()
        normalized.update(settings or {})
        normalized["enabled"] = bool(normalized.get("enabled"))
        normalized["access_mode"] = str(normalized.get("access_mode") or "api")
        normalized["provider"] = str(normalized.get("provider") or "")
        normalized["provider_name"] = str(normalized.get("provider_name") or "")
        normalized["base_url"] = str(normalized.get("base_url") or "").strip()
        normalized["model"] = str(normalized.get("model") or "").strip()
        normalized["provider_models"] = self._normalize_ai_provider_models(normalized.get("provider_models", {}))
        normalized["api_keys"] = self._normalize_ai_key_entries(normalized)
        selected_key_id = str(normalized.get("selected_key_id") or "")
        if not selected_key_id and normalized["api_keys"]:
            selected_key_id = normalized["api_keys"][0]["id"]
        normalized["selected_key_id"] = selected_key_id
        normalized["api_key"] = self._get_selected_ai_key(normalized)
        normalized["timeout"] = max(1, _to_int(normalized.get("timeout"), 60))
        normalized["max_tokens"] = max(1, _to_int(normalized.get("max_tokens"), 2000))
        normalized["temperature"] = max(0.0, _to_float(normalized.get("temperature"), 0.2))
        return normalized

    @staticmethod
    def _normalize_ai_provider_models(models: Any) -> Dict[str, str]:
        """规范化按接入方式和服务商保存的模型历史。"""
        if not isinstance(models, dict):
            return {}
        return {
            str(key): str(value).strip()
            for key, value in models.items()
            if str(key).strip() and str(value).strip()
        }

    def _normalize_ai_key_entries(self, settings: Dict[str, Any]) -> List[Dict[str, str]]:
        """规范化 AI Key 列表，并兼容旧版单 Key 字段。"""
        entries = []
        seen = set()
        for raw in settings.get("api_keys", []) or []:
            if not isinstance(raw, dict):
                continue
            key_value = self._decrypt_if_needed(str(raw.get("value") or raw.get("api_key") or ""))
            if not key_value:
                continue
            key_meta = {
                "access_mode": str(raw.get("access_mode") or settings.get("access_mode") or "api"),
                "provider": str(raw.get("provider") or settings.get("provider") or ""),
            }
            key_id = str(raw.get("id") or self._make_key_id(key_value, key_meta))
            if key_id in seen:
                continue
            seen.add(key_id)
            entries.append({
                "id": key_id,
                "name": str(raw.get("name") or self._default_key_name(key_value)),
                "value": key_value,
                "access_mode": str(raw.get("access_mode") or settings.get("access_mode") or "api"),
                "provider": str(raw.get("provider") or settings.get("provider") or ""),
                "provider_name": str(raw.get("provider_name") or settings.get("provider_name") or ""),
            })

        single_key = self._decrypt_if_needed(str(settings.get("api_key") or ""))
        if single_key:
            key_id = str(settings.get("selected_key_id") or self._make_key_id(single_key, {
                "access_mode": str(settings.get("access_mode") or "api"),
                "provider": str(settings.get("provider") or ""),
            }))
            if key_id not in seen:
                entries.append({
                    "id": key_id,
                    "name": self._default_key_name(single_key),
                    "value": single_key,
                    "access_mode": str(settings.get("access_mode") or "api"),
                    "provider": str(settings.get("provider") or ""),
                    "provider_name": str(settings.get("provider_name") or ""),
                })
        return entries

    @staticmethod
    def _get_selected_ai_key(settings: Dict[str, Any]) -> str:
        selected = str(settings.get("selected_key_id") or "")
        entries = settings.get("api_keys", [])
        for item in entries:
            if item.get("id") == selected:
                return item.get("value", "")
        return entries[0]["value"] if entries else ""

    def _encrypt_ai_keys(self, ai_settings: Dict[str, Any]) -> Dict[str, Any]:
        """加密 AI Key 后用于写入配置文件。"""
        stored = deepcopy(ai_settings)
        entries = []
        for item in stored.get("api_keys", []) or []:
            value = item.get("value", "")
            entries.append({
                "id": item.get("id", self._make_key_id(value, {
                    "access_mode": str(item.get("access_mode") or stored.get("access_mode", "api")),
                    "provider": str(item.get("provider") or stored.get("provider", "")),
                })),
                "name": item.get("name", self._default_key_name(value)),
                "value": self._encrypt_value(value),
                "access_mode": item.get("access_mode", stored.get("access_mode", "api")),
                "provider": item.get("provider", stored.get("provider", "")),
                "provider_name": item.get("provider_name", stored.get("provider_name", "")),
            })
        stored["api_keys"] = entries
        stored["api_key"] = self._encrypt_value(stored.get("api_key", ""))
        return stored

    def _encrypt_value(self, value: str) -> str:
        if not value:
            return ""
        raw = value.encode("utf-8")
        mask = self._key_stream(len(raw))
        encrypted = bytes(b ^ mask[i] for i, b in enumerate(raw))
        return "enc:" + base64.urlsafe_b64encode(encrypted).decode("ascii")

    def _decrypt_if_needed(self, value: str) -> str:
        if not value.startswith("enc:"):
            return value
        try:
            raw = base64.urlsafe_b64decode(value[4:].encode("ascii"))
            mask = self._key_stream(len(raw))
            return bytes(b ^ mask[i] for i, b in enumerate(raw)).decode("utf-8")
        except Exception:
            return ""

    def _key_stream(self, length: int) -> bytes:
        seed = f"{getpass.getuser()}|{self.settings_file.resolve()}|LingCe".encode("utf-8")
        chunks = []
        counter = 0
        while sum(len(chunk) for chunk in chunks) < length:
            chunks.append(hashlib.sha256(seed + str(counter).encode("ascii")).digest())
            counter += 1
        return b"".join(chunks)[:length]

    @staticmethod
    def _make_key_id(value: str, meta: Optional[Dict[str, Any]] = None) -> str:
        meta = meta or {}
        raw = f"{meta.get('access_mode', 'api')}|{meta.get('provider', '')}|{value}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _default_key_name(value: str) -> str:
        if len(value) <= 8:
            return "Key"
        return f"{value[:4]}...{value[-4:]}"


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
