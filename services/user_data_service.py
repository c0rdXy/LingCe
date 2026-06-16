#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据持久化服务 — JSON 文件存储
管理练习进度、错题历史、收藏、统计等用户数据
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


# 默认数据文件路径
_DEFAULT_DATA_DIR = Path("data")
_DEFAULT_DATA_FILE = _DEFAULT_DATA_DIR / "user_data.json"


class UserDataService:
    """用户数据持久化服务"""

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = Path(data_file) if data_file else _DEFAULT_DATA_FILE
        self._data: Dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------ #
    #  内部加载 / 保存
    # ------------------------------------------------------------------ #

    def _load(self):
        """从 JSON 文件加载数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = self._default_data()
        else:
            self._data = self._default_data()

    def _save(self):
        """保存数据到 JSON 文件"""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self._data["last_updated"] = datetime.now().isoformat()
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def reload(self):
        """重新从磁盘加载用户数据。"""
        self._load()

    @staticmethod
    def _default_data() -> Dict[str, Any]:
        """返回新的默认用户数据结构。"""
        return {
            "version": "0.0.8",
            "last_file": "",
            "progress": {},
            "wrong_history": [],
            "favorites": [],
            "tags": {},
            "stats": {
                "total_answered": 0,
                "total_correct": 0,
                "daily": {},
            },
        }

    # ------------------------------------------------------------------ #
    #  最近文件
    # ------------------------------------------------------------------ #

    def get_last_file(self) -> str:
        """获取最近一次打开的题库文件路径。"""
        return self._data.get("last_file", "")

    def set_last_file(self, file_path: str):
        """保存最近一次打开的题库文件路径。"""
        self._data["last_file"] = str(file_path)
        self._save()

    # ------------------------------------------------------------------ #
    #  主题
    # ------------------------------------------------------------------ #

    def get_theme(self) -> str:
        """读取旧版本保存在用户数据中的主题名称。"""
        return self._data.get("theme", "light")

    def set_theme(self, theme: str):
        """兼容旧版本主题写入；新版本默认主题保存在 settings.json。"""
        self._data["theme"] = theme
        self._save()

    # ------------------------------------------------------------------ #
    #  练习进度
    # ------------------------------------------------------------------ #

    def get_progress(self, file_path: str) -> Dict[str, Any]:
        """获取指定题库的练习进度"""
        return self._get_path_map_value("progress", file_path, {})

    def save_progress(self, file_path: str, progress: Dict[str, Any]):
        """保存练习进度"""
        if "progress" not in self._data:
            self._data["progress"] = {}
        self._data["progress"][self._path_key(file_path)] = progress
        self._save()

    def clear_progress(self, file_path: str):
        """清除指定题库的进度"""
        for key in self._get_path_map_keys("progress", file_path):
            self._data.get("progress", {}).pop(key, None)
        self._save()

    # ------------------------------------------------------------------ #
    #  错题历史
    # ------------------------------------------------------------------ #

    def get_wrong_history(self, file_path: str) -> List[int]:
        """获取指定题库的错题 ID 列表"""
        values = self._get_path_map_values("wrong_history_full", file_path)
        merged = set()
        for item in values:
            if isinstance(item, list):
                merged.update(item)
        return sorted(merged)

    def add_wrong_questions(self, file_path: str, question_ids: List[int]):
        """追加错题到历史"""
        if "wrong_history_full" not in self._data:
            self._data["wrong_history_full"] = {}
        key = self._path_key(file_path)
        existing = set(self.get_wrong_history(file_path))
        existing.update(question_ids)
        self._data["wrong_history_full"][key] = sorted(existing)
        self._save()

    def clear_wrong_history(self, file_path: str):
        """清除指定题库的错题历史"""
        for key in self._get_path_map_keys("wrong_history_full", file_path):
            self._data.get("wrong_history_full", {}).pop(key, None)
        self._save()

    # ------------------------------------------------------------------ #
    #  收藏
    # ------------------------------------------------------------------ #

    def get_favorites(self, file_path: str) -> List[int]:
        """获取收藏的题目 ID 列表"""
        values = self._get_path_map_values("favorites_full", file_path)
        merged = set()
        for item in values:
            if isinstance(item, list):
                merged.update(item)
        return sorted(merged)

    def toggle_favorite(self, file_path: str, question_id: int) -> bool:
        """切换收藏状态，返回当前是否已收藏"""
        if "favorites_full" not in self._data:
            self._data["favorites_full"] = {}
        key = self._path_key(file_path)
        favs = self.get_favorites(file_path)
        if question_id in favs:
            favs.remove(question_id)
            is_fav = False
        else:
            favs.append(question_id)
            is_fav = True
        self._data["favorites_full"][key] = sorted(favs)
        self._save()
        return is_fav

    def is_favorite(self, file_path: str, question_id: int) -> bool:
        """检查是否已收藏"""
        return question_id in self.get_favorites(file_path)

    # ------------------------------------------------------------------ #
    #  标签
    # ------------------------------------------------------------------ #

    def get_tags(self, file_path: str, question_id: int) -> List[str]:
        """获取指定题目的标签"""
        tags_map = self.get_all_tags(file_path)
        return tags_map.get(str(question_id), [])

    def set_tags(self, file_path: str, question_id: int, tags: List[str]):
        """设置指定题目的标签"""
        if "tags" not in self._data:
            self._data["tags"] = {}
        key = self._path_key(file_path)
        if key not in self._data["tags"]:
            self._data["tags"][key] = {}
        self._data["tags"][key][str(question_id)] = tags
        self._save()

    def get_all_tags(self, file_path: str) -> Dict[str, List[str]]:
        """获取指定题库的所有标签映射"""
        merged: Dict[str, List[str]] = {}
        for value in self._get_path_map_values("tags", file_path):
            if isinstance(value, dict):
                merged.update(value)
        return merged

    def _get_path_map_value(self, section: str, file_path: str, default: Any) -> Any:
        values = self._get_path_map_values(section, file_path)
        return values[0] if values else default

    def _get_path_map_values(self, section: str, file_path: str) -> List[Any]:
        data = self._data.get(section, {})
        if not isinstance(data, dict):
            return []
        return [data[key] for key in self._get_path_map_keys(section, file_path)]

    def _get_path_map_keys(self, section: str, file_path: str) -> List[str]:
        data = self._data.get(section, {})
        if not isinstance(data, dict):
            return []
        aliases = set(self._path_aliases(file_path))
        requested_name = Path(str(file_path or "")).name
        return [
            key
            for key in data
            if key in aliases
            or self._path_key(key) in aliases
            or (requested_name and Path(str(key)).name == requested_name)
        ]

    @classmethod
    def _path_aliases(cls, file_path: str) -> List[str]:
        raw = str(file_path or "")
        if not raw:
            return [""]

        aliases = {raw, raw.replace("\\", "/"), raw.replace("/", "\\")}
        canonical = cls._path_key(raw)
        aliases.add(canonical)
        aliases.add(canonical.replace("\\", "/"))
        aliases.add(canonical.replace("/", "\\"))
        return list(aliases)

    @staticmethod
    def _path_key(file_path: str) -> str:
        raw = str(file_path or "")
        if not raw:
            return ""
        try:
            return str(Path(raw).expanduser().resolve())
        except OSError:
            return raw

    # ------------------------------------------------------------------ #
    #  统计
    # ------------------------------------------------------------------ #

    def get_stats(self) -> Dict[str, Any]:
        """获取累计统计数据"""
        return self._data.get("stats", {
            "total_answered": 0,
            "total_correct": 0,
            "daily": {},
        })

    def update_stats(self, answered: int, correct: int, mode: str = "practice"):
        """更新累计统计，支持按模式分别记录"""
        stats = self.get_stats()
        stats["total_answered"] = stats.get("total_answered", 0) + answered
        stats["total_correct"] = stats.get("total_correct", 0) + correct

        # 按模式统计
        mode_stats = stats.get("by_mode", {})
        mode_data = mode_stats.get(mode, {"answered": 0, "correct": 0})
        mode_data["answered"] = mode_data.get("answered", 0) + answered
        mode_data["correct"] = mode_data.get("correct", 0) + correct
        mode_stats[mode] = mode_data
        stats["by_mode"] = mode_stats

        # 按日统计
        today = datetime.now().strftime("%Y-%m-%d")
        daily = stats.get("daily", {})
        day_data = daily.get(today, {"answered": 0, "correct": 0})
        day_data["answered"] += answered
        day_data["correct"] += correct
        daily[today] = day_data
        stats["daily"] = daily

        self._data["stats"] = stats
        self._save()

    def get_daily_stats(self, days: int = 30) -> Dict[str, Dict[str, int]]:
        """获取最近 N 天的每日统计"""
        stats = self.get_stats()
        daily = stats.get("daily", {})
        # 按日期排序，取最近 N 天
        sorted_days = sorted(daily.keys(), reverse=True)[:days]
        return {d: daily[d] for d in reversed(sorted_days)}

    # ------------------------------------------------------------------ #
    #  导出
    # ------------------------------------------------------------------ #

    def export_data(self) -> Dict[str, Any]:
        """导出全部用户数据"""
        return dict(self._data)
