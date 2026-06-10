#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统设置服务。"""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import APP_VERSION
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
        """仅在内存中设置默认主题，用于兼容旧用户主题数据。"""
        self._settings.setdefault("app", {})["default_theme"] = theme_name

    def get_exam_settings(self) -> Dict[str, Any]:
        """返回考试设置。"""
        return deepcopy(self._settings.get("exam", {}))

    def get_exam_rules(self) -> List[Dict[str, Any]]:
        """返回启用的考试规则。"""
        return [deepcopy(r) for r in self._settings.get("exam", {}).get("rules", []) if r.get("count", 0) > 0]

    def get_app_name(self) -> str:
        """返回应用名称。"""
        return self._settings.get("app", {}).get("name", "灵测 LingCe").strip() or "灵测 LingCe"

    def get_app_subtitle(self) -> str:
        """返回首页副标题。"""
        return self._settings.get("app", {}).get("subtitle", "通用考试练习平台")

    def get_window_title(self, suffix: str = "") -> str:
        """返回窗口标题。"""
        app = self._settings.get("app", {})
        title = self.get_app_name()
        if app.get("show_version", True):
            title = f"{title} {APP_VERSION}"
        if suffix:
            title = f"{title} - {suffix}"
        return title

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
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        self._settings = normalized

    def reset_to_defaults(self):
        """恢复并保存默认设置。"""
        self.save_settings(get_default_settings())

    def export_settings(self, file_path: str):
        """导出当前设置到指定 JSON 文件。"""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, ensure_ascii=False, indent=2)

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
