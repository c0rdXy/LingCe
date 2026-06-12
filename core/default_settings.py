#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""默认系统设置。"""

from copy import deepcopy
from typing import Any, Dict


DEFAULT_SETTINGS: Dict[str, Any] = {
    "version": "0.0.10",
    "app": {
        "name": "灵测 LingCe",
        "subtitle": "通用考试练习平台",
        "show_version": True,
        "default_theme": "light",
    },
    "exam": {
        "name": "默认考试",
        "time_limit": 90,
        "pass_score": 60,
        "allow_submit_with_unanswered": True,
        "auto_submit_when_time_up": False,
        "rules": [
            {
                "type": "single",
                "name": "单选题",
                "count": 20,
                "score": 2,
                "auto_score": True,
            },
            {
                "type": "multiple",
                "name": "多选题",
                "count": 20,
                "score": 3,
                "auto_score": True,
            },
            {
                "type": "short",
                "name": "简答题",
                "count": 4,
                "score": 0,
                "auto_score": False,
            },
        ],
    },
}


def get_default_settings() -> Dict[str, Any]:
    """返回默认设置副本。"""
    return deepcopy(DEFAULT_SETTINGS)


def merge_with_defaults(settings: Dict[str, Any]) -> Dict[str, Any]:
    """用默认设置补齐缺失字段。"""
    merged = get_default_settings()
    _deep_update(merged, settings or {})
    return merged


def _deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """递归更新字典，列表字段按整体替换处理。"""
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = deepcopy(value)
