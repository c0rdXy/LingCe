#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统设置窗口。"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
from typing import Callable, Dict, Any

from core.ai_presets import (
    get_access_mode_names,
    get_provider,
    get_providers,
    mode_key_from_name,
    mode_name_from_key,
    provider_id_from_name,
    provider_name_from_id,
)
from core.config import DEFAULT_FONT, BOLD_FONT, get_font, get_theme_colors, THEMES
from core.default_settings import DEFAULT_SETTINGS
from services.ai_service import AIService, AIServiceError
from services.settings_service import SettingsService
from ui.components import center_window


def show_settings_window(parent: tk.Tk, settings_service: SettingsService,
                         on_saved: Callable[[], None] = None):
    """显示系统设置窗口。"""
    SettingsWindow(parent, settings_service, on_saved)


class SettingsWindow:
    """系统设置编辑窗口。"""

    def __init__(self, parent: tk.Tk, settings_service: SettingsService,
                 on_saved: Callable[[], None] = None):
        self.parent = parent
        self.settings_service = settings_service
        self.on_saved = on_saved
        self.settings = settings_service.get_settings()
        self.rule_vars: Dict[str, Dict[str, Any]] = {}
        self.tc = get_theme_colors()

        self.window = tk.Toplevel(parent)
        self.window.title("系统设置")
        self.window.configure(bg=self.tc["bg"])
        self.window.transient(parent)
        self.window.grab_set()
        center_window(self.window, 800, 680)

        self._create_vars()
        self._create_ui()

    def _create_vars(self):
        app = self.settings["app"]
        exam = self.settings["exam"]
        self.app_name_var = tk.StringVar(value=app.get("name", ""))
        self.subtitle_var = tk.StringVar(value=app.get("subtitle", ""))
        self.show_version_var = tk.BooleanVar(value=app.get("show_version", True))
        self.theme_var = tk.StringVar(value=app.get("default_theme", "light"))
        self.time_limit_var = tk.StringVar(value=str(exam.get("time_limit", 90)))
        self.pass_score_var = tk.StringVar(value=str(exam.get("pass_score", 60)))
        self.allow_unanswered_var = tk.BooleanVar(
            value=exam.get("allow_submit_with_unanswered", True)
        )
        self.auto_submit_var = tk.BooleanVar(
            value=exam.get("auto_submit_when_time_up", False)
        )
        ai = self.settings.get("ai", {})
        access_mode = ai.get("access_mode", "api")
        provider = ai.get("provider", "deepseek")
        self.ai_enabled_var = tk.BooleanVar(value=ai.get("enabled", False))
        self.ai_access_mode_var = tk.StringVar(value=mode_name_from_key(access_mode))
        self.ai_provider_var = tk.StringVar(value=provider_name_from_id(access_mode, provider))
        self.ai_model_var = tk.StringVar(value=ai.get("model", ""))
        self.ai_base_url_var = tk.StringVar(value=ai.get("base_url", ""))
        self.ai_key_var = tk.StringVar(value=ai.get("api_key", ""))
        self.ai_key_entries = [dict(item) for item in ai.get("api_keys", [])]
        self.ai_selected_key_id = ai.get("selected_key_id", "")
        self.ai_key_select_var = tk.StringVar()
        self.ai_key_count_var = tk.StringVar(value="当前厂商已保存 Key：0 个")
        self._ai_key_context_meta = {
            "access_mode": access_mode,
            "provider": provider,
            "provider_name": provider_name_from_id(access_mode, provider),
        }
        self.ai_timeout_var = tk.StringVar(value=str(ai.get("timeout", 60)))
        self.ai_temperature_var = tk.StringVar(value=str(ai.get("temperature", 0.2)))
        self.ai_max_tokens_var = tk.StringVar(value=str(ai.get("max_tokens", 2000)))
        self.ai_key_visible_var = tk.BooleanVar(value=False)
        self._syncing_ai_controls = False

    def _create_ui(self):
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill="both", expand=True, padx=15, pady=15)

        app_tab = tk.Frame(notebook, bg=self.tc["bg"])
        exam_tab = tk.Frame(notebook, bg=self.tc["bg"])
        ai_tab = tk.Frame(notebook, bg=self.tc["bg"])
        notebook.add(app_tab, text="基础设置")
        notebook.add(exam_tab, text="考试设置")
        notebook.add(ai_tab, text="AI 设置")

        self._create_app_tab(app_tab)
        self._create_exam_tab(exam_tab)
        self._create_ai_tab(ai_tab)

        footer = tk.Frame(self.window, bg=self.tc["bg"])
        footer.pack(fill="x", padx=15, pady=(0, 15))
        ttk.Button(footer, text="恢复默认", command=self._reset_defaults).pack(side="left")
        ttk.Button(footer, text="导入设置", command=self._import_settings).pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="导出设置", command=self._export_settings).pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="保存", command=self._save).pack(side="right", padx=(8, 0))
        ttk.Button(footer, text="取消", command=self.window.destroy).pack(side="right")

    def _create_app_tab(self, parent):
        form = tk.Frame(parent, bg=self.tc["bg"])
        form.pack(fill="x", padx=20, pady=20)

        self._add_labeled_entry(form, "系统名称", self.app_name_var, 0)
        self._add_labeled_entry(form, "首页副标题", self.subtitle_var, 1)

        tk.Label(form, text="默认主题", font=DEFAULT_FONT,
                 bg=self.tc["bg"], fg=self.tc["text"]).grid(row=2, column=0, sticky="w", pady=8)
        theme_box = ttk.Combobox(
            form,
            textvariable=self.theme_var,
            values=list(THEMES.keys()),
            state="readonly",
            width=18,
        )
        theme_box.grid(row=2, column=1, sticky="w", pady=8)

        ttk.Checkbutton(form, text="窗口标题显示版本号",
                        variable=self.show_version_var).grid(
            row=3, column=1, sticky="w", pady=8
        )

    def _create_exam_tab(self, parent):
        top = tk.Frame(parent, bg=self.tc["bg"])
        top.pack(fill="x", padx=20, pady=(20, 10))

        self._add_labeled_entry(top, "考试时长（分钟）", self.time_limit_var, 0)
        self._add_labeled_entry(top, "及格分", self.pass_score_var, 1)

        ttk.Checkbutton(top, text="允许未答题时提交",
                        variable=self.allow_unanswered_var).grid(
            row=2, column=1, sticky="w", pady=8
        )
        ttk.Checkbutton(top, text="时间到后自动提交",
                        variable=self.auto_submit_var).grid(
            row=3, column=1, sticky="w", pady=8
        )

        rules_frame = tk.LabelFrame(parent, text="题型与分值", font=BOLD_FONT,
                                    bg=self.tc["bg"], fg=self.tc["text"])
        rules_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        header = tk.Frame(rules_frame, bg=self.tc["bg"])
        header.pack(fill="x", padx=10, pady=(10, 4))
        for text, width in [("启用", 6), ("题型", 12), ("题数", 10), ("每题分值", 10), ("自动评分", 10)]:
            tk.Label(header, text=text, width=width, font=get_font(9, "bold"),
                     bg=self.tc["bg"], fg=self.tc["text"]).pack(side="left")

        existing = {rule["type"]: rule for rule in self.settings_service.get_exam_settings()["rules"]}
        for item in self.settings_service.get_supported_rule_types():
            rule = existing.get(item["type"], {
                "type": item["type"], "name": item["name"], "count": 0,
                "score": 0, "auto_score": item["type"] != "short",
            })
            self._add_rule_row(rules_frame, rule)

    def _create_ai_tab(self, parent):
        form = tk.Frame(parent, bg=self.tc["bg"])
        form.pack(fill="x", padx=20, pady=20)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=0)

        ttk.Checkbutton(form, text="启用 AI 复核",
                        variable=self.ai_enabled_var).grid(
            row=0, column=1, sticky="w", pady=(0, 10)
        )

        tk.Label(form, text="接入方式", font=DEFAULT_FONT,
                 bg=self.tc["bg"], fg=self.tc["text"]).grid(row=1, column=0, sticky="w", pady=8)
        self.ai_access_box = ttk.Combobox(
            form,
            textvariable=self.ai_access_mode_var,
            values=get_access_mode_names(),
            state="readonly",
            width=24,
        )
        self.ai_access_box.grid(row=1, column=1, sticky="w", pady=8, padx=(10, 0))
        self.ai_access_box.bind("<<ComboboxSelected>>", self._on_ai_access_mode_changed)

        tk.Label(form, text="服务商", font=DEFAULT_FONT,
                 bg=self.tc["bg"], fg=self.tc["text"]).grid(row=2, column=0, sticky="w", pady=8)
        self.ai_provider_box = ttk.Combobox(
            form,
            textvariable=self.ai_provider_var,
            state="readonly",
            width=30,
        )
        self.ai_provider_box.grid(row=2, column=1, sticky="w", pady=8, padx=(10, 0))
        self.ai_provider_box.bind("<<ComboboxSelected>>", self._on_ai_provider_changed)

        self._add_labeled_entry(form, "Base URL", self.ai_base_url_var, 3, width=62, sticky="we")
        self._add_key_entry(form, 4)

        tk.Label(form, text="模型", font=DEFAULT_FONT,
                 bg=self.tc["bg"], fg=self.tc["text"]).grid(row=7, column=0, sticky="w", pady=8)
        model_row = tk.Frame(form, bg=self.tc["bg"])
        model_row.grid(row=7, column=1, sticky="we", pady=8, padx=(10, 0))
        model_row.columnconfigure(0, weight=1)
        self.ai_model_box = ttk.Combobox(
            model_row,
            textvariable=self.ai_model_var,
            width=42,
        )
        self.ai_model_box.grid(row=0, column=0, sticky="we")
        self.fetch_models_btn = ttk.Button(model_row, text="获取可用模型", command=self._fetch_ai_models)
        self.fetch_models_btn.grid(row=0, column=1, padx=(8, 0))

        self._add_labeled_entry(form, "超时时间（秒）", self.ai_timeout_var, 8, width=12)
        self._add_labeled_entry(form, "温度", self.ai_temperature_var, 9, width=12)
        self._add_labeled_entry(form, "最大输出 Token", self.ai_max_tokens_var, 10, width=12)

        action_row = tk.Frame(form, bg=self.tc["bg"])
        action_row.grid(row=11, column=1, sticky="w", pady=(12, 0), padx=(10, 0))
        ttk.Button(action_row, text="测试连接", command=self._test_ai_connection).pack(side="left")

        self.ai_access_mode_var.trace_add("write", lambda *_: self._on_ai_access_mode_changed())
        self.ai_provider_var.trace_add("write", lambda *_: self._on_ai_provider_changed())
        self._refresh_ai_provider_options(keep_current=True)
        self._refresh_key_selector()

    def _add_labeled_entry(self, parent, label, variable, row, width=30, sticky="w"):
        tk.Label(parent, text=label, font=DEFAULT_FONT,
                 bg=self.tc["bg"], fg=self.tc["text"]).grid(row=row, column=0, sticky="w", pady=8)
        ttk.Entry(parent, textvariable=variable, width=width).grid(
            row=row, column=1, sticky=sticky, pady=8, padx=(10, 0)
        )

    def _add_key_entry(self, parent, row):
        tk.Label(parent, text="API Key / Token", font=DEFAULT_FONT,
                 bg=self.tc["bg"], fg=self.tc["text"]).grid(row=row, column=0, sticky="w", pady=8)
        key_row = tk.Frame(parent, bg=self.tc["bg"])
        key_row.grid(row=row, column=1, sticky="we", pady=8, padx=(10, 0))
        key_row.columnconfigure(0, weight=1)
        self.ai_key_entry = ttk.Entry(key_row, textvariable=self.ai_key_var, width=62, show="*")
        self.ai_key_entry.grid(row=0, column=0, sticky="we")
        self.ai_key_toggle_btn = ttk.Button(key_row, text="显示", width=6, command=self._toggle_ai_key_visibility)
        self.ai_key_toggle_btn.grid(row=0, column=1, padx=(8, 0))
        tk.Label(
            parent,
            textvariable=self.ai_key_count_var,
            font=DEFAULT_FONT,
            bg=self.tc["bg"],
            fg=self.tc.get("text_secondary", self.tc["text"]),
        ).grid(row=row + 1, column=1, sticky="w", pady=(0, 4), padx=(10, 0))
        key_manage_row = tk.Frame(parent, bg=self.tc["bg"])
        key_manage_row.grid(row=row + 2, column=1, sticky="we", pady=(0, 6), padx=(10, 0))
        key_manage_row.columnconfigure(0, weight=1)
        self.ai_key_select_box = ttk.Combobox(
            key_manage_row,
            textvariable=self.ai_key_select_var,
            state="readonly",
            width=42,
        )
        self.ai_key_select_box.grid(row=0, column=0, sticky="we")
        self.ai_key_select_box.bind("<<ComboboxSelected>>", self._on_saved_key_selected)
        ttk.Button(key_manage_row, text="保存当前 Key", command=self._save_current_ai_key).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(key_manage_row, text="删除", command=self._delete_current_ai_key).grid(row=0, column=2, padx=(8, 0))

    def _toggle_ai_key_visibility(self):
        visible = not self.ai_key_visible_var.get()
        self.ai_key_visible_var.set(visible)
        self.ai_key_entry.config(show="" if visible else "*")
        self.ai_key_toggle_btn.config(text="隐藏" if visible else "显示")

    def _add_rule_row(self, parent, rule):
        row = tk.Frame(parent, bg=self.tc["bg"])
        row.pack(fill="x", padx=10, pady=3)
        enabled = tk.BooleanVar(value=rule.get("count", 0) > 0)
        count_var = tk.StringVar(value=str(rule.get("count", 0)))
        score_var = tk.StringVar(value=str(rule.get("score", 0)))
        auto_score = tk.BooleanVar(value=rule.get("auto_score", True))

        ttk.Checkbutton(row, variable=enabled).pack(side="left", padx=(8, 18))
        tk.Label(row, text=rule.get("name", rule["type"]), width=12,
                 bg=self.tc["bg"], fg=self.tc["text"], anchor="w").pack(side="left")
        ttk.Entry(row, textvariable=count_var, width=8).pack(side="left", padx=(8, 22))
        ttk.Entry(row, textvariable=score_var, width=8).pack(side="left", padx=(0, 28))
        ttk.Checkbutton(row, variable=auto_score).pack(side="left")

        self.rule_vars[rule["type"]] = {
            "enabled": enabled,
            "name": rule.get("name", rule["type"]),
            "count": count_var,
            "score": score_var,
            "auto_score": auto_score,
        }

    def _save(self):
        try:
            settings = self._collect_settings()
            self.settings_service.save_settings(settings)
        except (TypeError, ValueError) as exc:
            messagebox.showerror("设置错误", str(exc), parent=self.window)
            return

        messagebox.showinfo("设置", "设置已保存", parent=self.window)
        self.window.destroy()
        if self.on_saved:
            self.on_saved()

    def _reset_defaults(self):
        if not messagebox.askyesno(
            "恢复默认",
            "确定要恢复默认系统设置吗？当前设置会被覆盖。",
            parent=self.window,
        ):
            return
        try:
            self.settings_service.reset_to_defaults()
        except ValueError as exc:
            messagebox.showerror("设置错误", str(exc), parent=self.window)
            return
        messagebox.showinfo("设置", "已恢复默认设置", parent=self.window)
        self.window.destroy()
        if self.on_saved:
            self.on_saved()

    def _export_settings(self):
        file_path = filedialog.asksaveasfilename(
            parent=self.window,
            title="导出设置",
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            initialfile="lingce-settings.json",
        )
        if not file_path:
            return
        try:
            self.settings_service.export_settings(file_path)
        except OSError as exc:
            messagebox.showerror("导出失败", str(exc), parent=self.window)
            return
        messagebox.showinfo("导出设置", "设置已导出", parent=self.window)

    def _import_settings(self):
        file_path = filedialog.askopenfilename(
            parent=self.window,
            title="导入设置",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if not file_path:
            return
        try:
            self.settings_service.import_settings(file_path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("导入失败", str(exc), parent=self.window)
            return
        messagebox.showinfo("导入设置", "设置已导入", parent=self.window)
        self.window.destroy()
        if self.on_saved:
            self.on_saved()

    def _collect_settings(self) -> Dict[str, Any]:
        rules = []
        for rule_type, vars_ in self.rule_vars.items():
            count = vars_["count"].get() or "0" if vars_["enabled"].get() else 0
            rules.append({
                "type": rule_type,
                "name": vars_["name"],
                "count": count,
                "score": vars_["score"].get() or "0",
                "auto_score": vars_["auto_score"].get(),
            })

        return {
            "version": DEFAULT_SETTINGS["version"],
            "app": {
                "name": self.app_name_var.get().strip(),
                "subtitle": self.subtitle_var.get().strip(),
                "show_version": self.show_version_var.get(),
                "default_theme": self.theme_var.get(),
            },
            "exam": {
                "name": "默认考试",
                "time_limit": self.time_limit_var.get() or "0",
                "pass_score": self.pass_score_var.get() or "0",
                "allow_submit_with_unanswered": self.allow_unanswered_var.get(),
                "auto_submit_when_time_up": self.auto_submit_var.get(),
                "rules": rules,
            },
            "ai": self._collect_ai_settings(),
        }

    def _collect_ai_settings(self) -> Dict[str, Any]:
        access_mode = mode_key_from_name(self.ai_access_mode_var.get())
        provider_id = provider_id_from_name(access_mode, self.ai_provider_var.get())
        self._sync_current_key_entry()
        current_key = self._find_key_entry(self.ai_selected_key_id)
        return {
            "enabled": self.ai_enabled_var.get(),
            "access_mode": access_mode,
            "provider": provider_id,
            "provider_name": self.ai_provider_var.get(),
            "base_url": self.ai_base_url_var.get().strip(),
            "model": self.ai_model_var.get().strip(),
            "api_key": current_key.get("value", "") if current_key else self.ai_key_var.get(),
            "api_keys": self.ai_key_entries,
            "selected_key_id": self.ai_selected_key_id,
            "timeout": self.ai_timeout_var.get() or "60",
            "temperature": self.ai_temperature_var.get() or "0.2",
            "max_tokens": self.ai_max_tokens_var.get() or "2000",
        }

    def _on_ai_access_mode_changed(self, _event=None):
        if self._syncing_ai_controls:
            return
        self._sync_current_key_entry(self._ai_key_context_meta)
        self._refresh_ai_provider_options(keep_current=False)

    def _on_ai_provider_changed(self, _event=None):
        if self._syncing_ai_controls:
            return
        self._sync_current_key_entry(self._ai_key_context_meta)
        self._apply_ai_provider_preset()

    def _refresh_ai_provider_options(self, keep_current: bool):
        access_mode = mode_key_from_name(self.ai_access_mode_var.get())
        providers = get_providers(access_mode)
        names = [provider["name"] for provider in providers]
        self.ai_provider_box.configure(values=names)
        if not keep_current or self.ai_provider_var.get() not in names:
            self._syncing_ai_controls = True
            self.ai_provider_var.set(names[0])
            self._syncing_ai_controls = False
            self._apply_ai_provider_preset()
        else:
            self._apply_ai_provider_preset(keep_model=True)

    def _apply_ai_provider_preset(self, keep_model: bool = False):
        access_mode = mode_key_from_name(self.ai_access_mode_var.get())
        provider_id = provider_id_from_name(access_mode, self.ai_provider_var.get())
        provider = get_provider(access_mode, provider_id)
        self._syncing_ai_controls = True
        self.ai_base_url_var.set(provider.get("base_url", ""))
        models = provider.get("models", [])
        self.ai_model_box.configure(values=models)
        if keep_model and self.ai_model_var.get() in models:
            pass
        elif models:
            self.ai_model_var.set(models[0])
        else:
            self.ai_model_var.set("")
        self._syncing_ai_controls = False
        self._refresh_key_selector()
        self._ai_key_context_meta = self._current_provider_key_meta()

    def _refresh_key_selector(self):
        entries = self._current_provider_key_entries()
        names = [item.get("name", "Key") for item in entries]
        self.ai_key_select_box.configure(values=names)
        self.ai_key_count_var.set(f"当前厂商已保存 Key：{len(entries)} 个")
        selected = self._find_key_entry(self.ai_selected_key_id)
        if selected and not self._is_current_provider_key(selected):
            selected = None
        if selected:
            self.ai_key_select_var.set(selected.get("name", "Key"))
            self.ai_key_var.set(selected.get("value", ""))
        elif entries:
            self.ai_selected_key_id = entries[0]["id"]
            self.ai_key_select_var.set(entries[0].get("name", "Key"))
            self.ai_key_var.set(entries[0].get("value", ""))
        else:
            self.ai_selected_key_id = ""
            self.ai_key_select_var.set("")
            self.ai_key_var.set("")

    def _on_saved_key_selected(self, _event=None):
        name = self.ai_key_select_var.get()
        for item in self._current_provider_key_entries():
            if item.get("name") == name:
                self.ai_selected_key_id = item.get("id", "")
                self.ai_key_var.set(item.get("value", ""))
                return

    def _save_current_ai_key(self):
        value = self.ai_key_var.get().strip()
        if not value:
            messagebox.showwarning("保存 Key", "请先输入 API Key / Token", parent=self.window)
            return
        key_id = self._make_key_id(value)
        name = self._default_key_name(value)
        existing = self._find_key_entry(key_id)
        if existing:
            existing["value"] = value
            existing["name"] = existing.get("name") or name
            existing.update(self._current_provider_key_meta())
        else:
            self.ai_key_entries.append({
                "id": key_id,
                "name": name,
                "value": value,
                **self._current_provider_key_meta(),
            })
        self.ai_selected_key_id = key_id
        self._refresh_key_selector()
        messagebox.showinfo("保存 Key", "当前 Key 已加入列表，点击保存后写入配置", parent=self.window)

    def _delete_current_ai_key(self):
        if not self.ai_selected_key_id:
            return
        self.ai_key_entries = [item for item in self.ai_key_entries if item.get("id") != self.ai_selected_key_id]
        current_entries = self._current_provider_key_entries()
        self.ai_selected_key_id = current_entries[0]["id"] if current_entries else ""
        self.ai_key_var.set("")
        self._refresh_key_selector()

    def _sync_current_key_entry(self, meta: Dict[str, str] = None):
        value = self.ai_key_var.get().strip()
        if not value:
            return
        meta = meta or self._current_provider_key_meta()
        key_id = self.ai_selected_key_id or self._make_key_id(value, meta)
        entry = self._find_key_entry(key_id)
        if entry:
            entry["value"] = value
            entry.update(meta)
        else:
            self.ai_key_entries.append({
                "id": key_id,
                "name": self._default_key_name(value),
                "value": value,
                **meta,
            })
        self.ai_selected_key_id = key_id

    def _select_first_saved_key(self):
        entries = self._current_provider_key_entries()
        if entries:
            self.ai_selected_key_id = entries[0]["id"]
            self.ai_key_var.set(entries[0].get("value", ""))
            self.ai_key_select_var.set(entries[0].get("name", "Key"))
        else:
            self.ai_selected_key_id = ""
            self.ai_key_var.set("")
            self.ai_key_select_var.set("")

    def _find_key_entry(self, key_id: str):
        for item in self.ai_key_entries:
            if item.get("id") == key_id:
                return item
        return None

    def _current_provider_key_meta(self) -> Dict[str, str]:
        access_mode = mode_key_from_name(self.ai_access_mode_var.get())
        provider_id = provider_id_from_name(access_mode, self.ai_provider_var.get())
        return {
            "access_mode": access_mode,
            "provider": provider_id,
            "provider_name": self.ai_provider_var.get(),
        }

    def _is_current_provider_key(self, item: Dict[str, str]) -> bool:
        meta = self._current_provider_key_meta()
        return (
            item.get("access_mode") == meta["access_mode"]
            and item.get("provider") == meta["provider"]
        )

    def _current_provider_key_entries(self):
        meta = self._current_provider_key_meta()
        for item in self.ai_key_entries:
            item.setdefault("access_mode", meta["access_mode"])
            item.setdefault("provider", meta["provider"])
            item.setdefault("provider_name", meta["provider_name"])
        return [item for item in self.ai_key_entries if self._is_current_provider_key(item)]

    def _make_key_id(self, value: str, meta: Dict[str, str] = None) -> str:
        import hashlib
        meta = meta or self._current_provider_key_meta()
        raw = f"{meta['access_mode']}|{meta['provider']}|{value}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _default_key_name(value: str) -> str:
        return f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "Key"

    def _refresh_ai_model_options(self):
        access_mode = mode_key_from_name(self.ai_access_mode_var.get())
        provider_id = provider_id_from_name(access_mode, self.ai_provider_var.get())
        provider = get_provider(access_mode, provider_id)
        self.ai_model_box.configure(values=provider.get("models", []))

    def _fetch_ai_models(self):
        settings = self._collect_ai_settings()
        settings["enabled"] = True
        self._models_before_fetch = list(self.ai_model_box.cget("values"))
        self._model_before_fetch = self.ai_model_var.get()
        self.fetch_models_btn.config(state="disabled")
        self.ai_model_box.configure(values=["正在获取..."])
        self.ai_model_var.set("正在获取...")

        def worker():
            try:
                models = AIService(self.settings_service).list_models(settings)
                self.window.after(0, lambda loaded_models=models: self._on_ai_models_loaded(loaded_models))
            except AIServiceError as exc:
                message = str(exc)
                self.window.after(0, lambda error_message=message: self._on_ai_models_error(error_message))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ai_models_loaded(self, models):
        self.ai_model_box.configure(values=models)
        if models:
            self.ai_model_var.set(models[0])
        self.fetch_models_btn.config(state="normal")
        messagebox.showinfo("获取可用模型", f"已获取 {len(models)} 个模型", parent=self.window)

    def _on_ai_models_error(self, message: str):
        self.fetch_models_btn.config(state="normal")
        self.ai_model_box.configure(values=getattr(self, "_models_before_fetch", []))
        self.ai_model_var.set(getattr(self, "_model_before_fetch", ""))
        messagebox.showerror("获取可用模型失败", message, parent=self.window)

    def _test_ai_connection(self):
        settings = self._collect_ai_settings()
        settings["enabled"] = True
        start = time.perf_counter()
        try:
            AIService(self.settings_service).test_connection(settings)
        except AIServiceError as exc:
            elapsed = time.perf_counter() - start
            messagebox.showerror("AI 连接失败", f"{exc}\n\n耗时：{elapsed:.2f} 秒", parent=self.window)
            return
        elapsed = time.perf_counter() - start
        messagebox.showinfo("AI 连接", f"连接成功\n耗时：{elapsed:.2f} 秒", parent=self.window)
