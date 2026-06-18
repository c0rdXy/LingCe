#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手工创建题库窗口。"""

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import Callable, Optional

from core.config import (
    DEFAULT_FONT,
    BOLD_FONT,
    COLORS,
    QUESTION_BANK_DIR,
    get_font,
    get_theme_colors,
)
from core.models import Question
from core.utils import format_judge_answer, normalize_judge_answer, save_questions_to_file
from services.question_bank_builder import (
    QUESTION_TYPE_LABELS,
    CHOICE_TYPES,
    QuestionBankBuilder,
    QuestionDraft,
)
from services.ai_service import AIService, AIServiceError
from services.document_import_service import DocumentImportError, DocumentImportService
from ui.ai_review_window import show_ai_review_window
from ui.components import center_window


LABEL_TO_TYPE = {label: qtype for qtype, label in QUESTION_TYPE_LABELS.items()}


def show_question_bank_builder_window(
    parent: tk.Tk,
    on_saved: Optional[Callable[[str], None]] = None,
):
    """显示手工创建题库窗口。"""
    QuestionBankBuilderWindow(parent, on_saved)


class QuestionBankBuilderWindow:
    """手工创建题库编辑器。"""

    def __init__(self, parent: tk.Tk, on_saved: Optional[Callable[[str], None]] = None):
        self.parent = parent
        self.on_saved = on_saved
        self.tc = get_theme_colors()
        self.builder = QuestionBankBuilder()
        self.drafts = [self.builder.new_draft()]
        self.current_index = 0
        self._auto_save_job = None
        self._suspend_list_events = False
        self._dirty = False
        self._loading_draft = False
        self.ai_histories = {}
        self.import_service = DocumentImportService()
        self.import_source_path = ""

        self.window = tk.Toplevel(parent)
        self.window.title("生成题库")
        self.window.configure(bg=self.tc["bg"])
        self.window.transient(parent)
        center_window(self.window, 980, 700)
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

        self._create_vars()
        self._create_ui()
        self._bind_change_events()
        self._load_current_draft()
        self._refresh_list()
        self._dirty = False

    def _create_vars(self):
        self.type_var = tk.StringVar()
        self.answer_text_var = tk.StringVar()
        self.answer_choice_var = tk.StringVar(value="")
        self.answer_check_vars = [tk.BooleanVar(value=False) for _ in range(6)]
        self.option_vars = [tk.StringVar() for _ in range(6)]
        self.option_rows = []
        self.option_entries = []
        self.visible_option_count = 4
        self.answer_focus_widgets = []
        self.import_count_var = tk.StringVar(value="auto")
        self.import_difficulty_var = tk.StringVar(value="auto")
        self.import_explanation_var = tk.BooleanVar(value=True)
        self.import_type_vars = {
            qtype: tk.BooleanVar(value=True)
            for qtype in QUESTION_TYPE_LABELS
        }
        self.import_status_var = tk.StringVar(value="请选择文件或粘贴文本。")

    def _create_ui(self):
        toolbar = tk.Frame(self.window, bg=self.tc["bg"])
        toolbar.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(
            toolbar,
            text="生成题库",
            font=get_font(16, "bold"),
            bg=self.tc["bg"],
            fg=self.tc["primary"],
        ).pack(side="left")
        ttk.Button(toolbar, text="题目模板", command=self.apply_template).pack(side="left", padx=(16, 0))
        ttk.Button(toolbar, text="保存题库", command=self.save_question_bank).pack(side="right")
        ttk.Button(toolbar, text="清除题库", command=self.clear_question_bank).pack(side="right", padx=(0, 8))

        notebook = ttk.Notebook(self.window)
        notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        manual_tab = tk.Frame(notebook, bg=self.tc["bg"])
        import_tab = tk.Frame(notebook, bg=self.tc["bg"])
        notebook.add(manual_tab, text="手工创建")
        notebook.add(import_tab, text="AI 解析导入")

        body = tk.Frame(manual_tab, bg=self.tc["bg"])
        body.pack(fill="both", expand=True)

        self._create_list_panel(body)
        self._create_editor_panel(body)
        self._create_import_tab(import_tab)

    def _create_import_tab(self, parent):
        top = tk.Frame(parent, bg=self.tc["bg"])
        top.pack(fill="x", pady=(8, 10))

        ttk.Button(top, text="选择文件", command=self.select_import_file).pack(side="left")
        ttk.Button(top, text="清空内容", command=self.clear_import_text).pack(side="left", padx=(8, 0))
        ttk.Button(top, text="使用当前编辑题目", command=self.focus_manual_tab).pack(side="right")

        self.import_file_label = tk.Label(
            parent,
            text="支持 TXT / Markdown / CSV / Word(.docx) / Excel(.xlsx) / PDF",
            font=get_font(9),
            bg=self.tc["bg"],
            fg=self.tc["text_secondary"],
            anchor="w",
        )
        self.import_file_label.pack(fill="x", pady=(0, 6))

        preview_frame = tk.LabelFrame(
            parent,
            text="来源内容预览",
            font=BOLD_FONT,
            bg=self.tc["bg"],
            fg=self.tc["text"],
        )
        preview_frame.pack(fill="both", expand=True)
        self.import_text = scrolledtext.ScrolledText(
            preview_frame,
            height=14,
            wrap=tk.WORD,
            font=DEFAULT_FONT,
            bg=self.tc["bg_secondary"],
            fg=self.tc["text"],
            insertbackground=self.tc["text"],
        )
        self.import_text.pack(fill="both", expand=True, padx=10, pady=10)

        settings = tk.LabelFrame(
            parent,
            text="解析设置",
            font=BOLD_FONT,
            bg=self.tc["bg"],
            fg=self.tc["text"],
        )
        settings.pack(fill="x", pady=(10, 8))

        first_row = tk.Frame(settings, bg=self.tc["bg"])
        first_row.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(first_row, text="题目数量", bg=self.tc["bg"], fg=self.tc["text"]).pack(side="left")
        ttk.Combobox(
            first_row,
            textvariable=self.import_count_var,
            values=["auto", "5", "10", "20", "30", "50"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=(8, 18))
        tk.Label(first_row, text="难度", bg=self.tc["bg"], fg=self.tc["text"]).pack(side="left")
        ttk.Combobox(
            first_row,
            textvariable=self.import_difficulty_var,
            values=["auto", "easy", "normal", "hard"],
            width=10,
            state="readonly",
        ).pack(side="left", padx=(8, 18))
        ttk.Checkbutton(first_row, text="生成解析", variable=self.import_explanation_var).pack(side="left")

        type_row = tk.Frame(settings, bg=self.tc["bg"])
        type_row.pack(fill="x", padx=10, pady=(4, 8))
        tk.Label(type_row, text="题型范围", bg=self.tc["bg"], fg=self.tc["text"]).pack(side="left", padx=(0, 8))
        for qtype, label in QUESTION_TYPE_LABELS.items():
            ttk.Checkbutton(type_row, text=label, variable=self.import_type_vars[qtype]).pack(side="left", padx=(0, 10))

        footer = tk.Frame(parent, bg=self.tc["bg"])
        footer.pack(fill="x")
        tk.Label(
            footer,
            textvariable=self.import_status_var,
            bg=self.tc["bg"],
            fg=self.tc["text_secondary"],
            anchor="w",
            font=get_font(9),
        ).pack(side="left", fill="x", expand=True)
        self.ai_import_btn = ttk.Button(footer, text="AI 解析生成题库", command=self.generate_questions_from_import)
        self.ai_import_btn.pack(side="right")

    def focus_manual_tab(self):
        """占位按钮保留用户从导入页回到编辑页的直觉入口。"""
        for widget in self.window.winfo_children():
            if isinstance(widget, ttk.Notebook):
                widget.select(0)
                return

    def select_import_file(self):
        """选择资料文件并提取文本。"""
        file_path = filedialog.askopenfilename(
            parent=self.window,
            title="选择资料文件",
            filetypes=[
                ("支持的资料", "*.txt *.md *.markdown *.csv *.docx *.xlsx *.pdf"),
                ("文本文件", "*.txt *.md *.markdown"),
                ("Office 文件", "*.docx *.xlsx"),
                ("PDF 文件", "*.pdf"),
                ("所有文件", "*.*"),
            ],
        )
        if not file_path:
            return
        try:
            text = self.import_service.extract_text(file_path)
        except DocumentImportError as exc:
            messagebox.showerror("提取失败", str(exc), parent=self.window)
            return
        if not text.strip():
            messagebox.showwarning("提取结果为空", "没有从文件中提取到可用文本", parent=self.window)
            return

        self.import_source_path = file_path
        self.import_text.delete("1.0", tk.END)
        self.import_text.insert("1.0", text)
        self.import_file_label.config(text=f"已选择：{file_path}")
        self.import_status_var.set(f"已提取 {len(text)} 个字符，可开始 AI 解析。")

    def clear_import_text(self):
        """清空导入资料文本。"""
        self.import_source_path = ""
        self.import_text.delete("1.0", tk.END)
        self.import_file_label.config(text="支持 TXT / Markdown / CSV / Word(.docx) / Excel(.xlsx) / PDF")
        self.import_status_var.set("请选择文件或粘贴文本。")

    def generate_questions_from_import(self):
        """调用 AI 将资料文本解析为题目草稿。"""
        source_text = self.import_text.get("1.0", "end-1c").strip()
        if not source_text:
            messagebox.showwarning("AI 解析导入", "请先选择文件或粘贴资料文本", parent=self.window)
            return
        selected_types = [qtype for qtype, var in self.import_type_vars.items() if var.get()]
        if not selected_types:
            messagebox.showwarning("AI 解析导入", "请至少选择一种题型", parent=self.window)
            return

        self.ai_import_btn.config(state="disabled")
        self.import_status_var.set("AI 正在解析资料，请稍候...")

        def worker():
            try:
                drafts = AIService().generate_questions_from_text(
                    source_text=source_text,
                    question_count=self.import_count_var.get(),
                    question_types=selected_types,
                    include_explanation=self.import_explanation_var.get(),
                    difficulty=self.import_difficulty_var.get(),
                )
                self.window.after(0, lambda: self._apply_imported_drafts(drafts))
            except AIServiceError as exc:
                message = str(exc)
                self.window.after(0, lambda: self._on_import_error(message))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_imported_drafts(self, drafts):
        """把 AI 解析结果载入手工编辑器供人工复核。"""
        self.ai_import_btn.config(state="normal")
        if not drafts:
            self.import_status_var.set("AI 未生成题目。")
            messagebox.showwarning("AI 解析导入", "AI 未生成题目", parent=self.window)
            return

        if self._has_meaningful_drafts():
            replace = messagebox.askyesno(
                "载入解析结果",
                "当前编辑器已有题目，是否用 AI 解析结果替换？",
                parent=self.window,
            )
            if not replace:
                self.import_status_var.set("已取消载入 AI 解析结果。")
                return

        self.drafts = drafts
        self.current_index = 0
        self._dirty = True
        self.ai_histories = {}
        self._refresh_list()
        self._load_current_draft()
        self.focus_manual_tab()

        invalid_count = sum(1 for draft in drafts if self.builder.validate_draft(draft))
        if invalid_count:
            message = f"AI 已生成 {len(drafts)} 道题，其中 {invalid_count} 道需要人工补充或修正。"
        else:
            message = f"AI 已生成 {len(drafts)} 道题，请人工复核后保存。"
        self.import_status_var.set(message)
        messagebox.showinfo("AI 解析完成", message, parent=self.window)

    def _has_meaningful_drafts(self) -> bool:
        """判断当前编辑器中是否已有用户填写内容。"""
        self._store_current_draft(validate=False, show_errors=False)
        for draft in self.drafts:
            if draft.question.strip() or draft.answer.strip() or draft.explanation.strip():
                return True
            if any(str(option).strip() for option in draft.options):
                return True
        return False

    def _on_import_error(self, message: str):
        self.ai_import_btn.config(state="normal")
        self.import_status_var.set("AI 解析失败。")
        messagebox.showerror("AI 解析失败", message, parent=self.window)

    def _create_list_panel(self, parent):
        panel = tk.LabelFrame(
            parent,
            text="题目列表",
            font=BOLD_FONT,
            bg=self.tc["bg"],
            fg=self.tc["text"],
            width=280,
        )
        panel.pack(side="left", fill="y", padx=(0, 10))
        panel.pack_propagate(False)

        actions = tk.Frame(panel, bg=self.tc["bg"])
        actions.pack(fill="x", padx=8, pady=8)
        for col in range(2):
            actions.columnconfigure(col, weight=1)
        ttk.Button(actions, text="新增", command=self.add_question, width=7).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(actions, text="复制", command=self.duplicate_question, width=7).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        tk.Button(
            actions,
            text="删除当前题目",
            command=self.delete_question,
            bg=COLORS["danger"],
            fg="white",
            activebackground=COLORS["danger"],
            activeforeground="white",
            relief="flat",
            cursor="hand2",
        ).grid(row=1, column=0, columnspan=2, padx=2, pady=(6, 2), sticky="ew")

        move_actions = tk.Frame(panel, bg=self.tc["bg"])
        move_actions.pack(fill="x", padx=8, pady=(0, 8))
        for col in range(2):
            move_actions.columnconfigure(col, weight=1)
        ttk.Button(move_actions, text="上移", command=self.move_up, width=7).grid(row=0, column=0, padx=2, sticky="ew")
        ttk.Button(move_actions, text="下移", command=self.move_down, width=7).grid(row=0, column=1, padx=2, sticky="ew")

        list_frame = tk.Frame(panel, bg=self.tc["bg"])
        list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.question_list = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=get_font(10),
            bg=self.tc["bg_secondary"],
            fg=self.tc["text"],
            selectbackground=self.tc["primary"],
            selectforeground="#ffffff",
            activestyle="none",
        )
        self.question_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.question_list.yview)
        self.question_list.bind("<<ListboxSelect>>", self._on_list_select)

        self.summary_label = tk.Label(
            panel,
            text="",
            bg=self.tc["bg"],
            fg=self.tc["text_secondary"],
            font=get_font(9),
            justify="left",
        )
        self.summary_label.pack(fill="x", padx=8, pady=(0, 8))

    def _create_editor_panel(self, parent):
        panel = tk.LabelFrame(
            parent,
            text="题目编辑",
            font=BOLD_FONT,
            bg=self.tc["bg"],
            fg=self.tc["text"],
        )
        panel.pack(side="left", fill="both", expand=True)

        top = tk.Frame(panel, bg=self.tc["bg"])
        top.pack(fill="x", padx=12, pady=10)
        tk.Label(top, text="题型", font=DEFAULT_FONT, bg=self.tc["bg"], fg=self.tc["text"]).pack(side="left")
        type_box = ttk.Combobox(
            top,
            textvariable=self.type_var,
            values=list(QUESTION_TYPE_LABELS.values()),
            state="readonly",
            width=14,
        )
        type_box.pack(side="left", padx=(8, 18))
        type_box.bind("<<ComboboxSelected>>", self._on_type_change)

        self.hint_label = tk.Label(
            top,
            text="",
            font=get_font(9),
            bg=self.tc["bg"],
            fg=self.tc["text_secondary"],
        )
        self.hint_label.pack(side="left")

        tk.Label(panel, text="题干", font=BOLD_FONT, bg=self.tc["bg"], fg=self.tc["text"]).pack(
            anchor="w", padx=12
        )
        self.question_text = scrolledtext.ScrolledText(
            panel,
            height=6,
            wrap=tk.WORD,
            font=DEFAULT_FONT,
            bg=self.tc["bg_secondary"],
            fg=self.tc["text"],
            insertbackground=self.tc["text"],
        )
        self.question_text.pack(fill="x", padx=12, pady=(4, 10))

        self.options_frame = tk.LabelFrame(
            panel,
            text="选项",
            font=BOLD_FONT,
            bg=self.tc["bg"],
            fg=self.tc["text"],
        )
        self.options_frame.pack(fill="x", padx=12, pady=(0, 10))
        for index, variable in enumerate(self.option_vars):
            row = tk.Frame(self.options_frame, bg=self.tc["bg"])
            row.pack(fill="x", padx=8, pady=3)
            self.option_rows.append(row)
            tk.Label(
                row,
                text=f"{chr(ord('A') + index)}.",
                width=3,
                bg=self.tc["bg"],
                fg=self.tc["text"],
            ).pack(side="left")
            entry = ttk.Entry(row, textvariable=variable)
            entry.pack(side="left", fill="x", expand=True)
            self.option_entries.append(entry)

        self.answer_row = tk.Frame(panel, bg=self.tc["bg"])
        self.answer_row.pack(fill="x", padx=12, pady=(0, 10))
        tk.Label(self.answer_row, text="答案", font=BOLD_FONT, bg=self.tc["bg"], fg=self.tc["text"]).pack(side="left")
        self.answer_control_container = tk.Frame(self.answer_row, bg=self.tc["bg"])
        self.answer_control_container.pack(side="left", fill="x", expand=True, padx=(8, 0))

        answer_actions = tk.Frame(panel, bg=self.tc["bg"])
        answer_actions.pack(fill="x", padx=12, pady=(0, 10))
        ttk.Button(answer_actions, text="增选项", command=self.add_option).pack(side="left")
        ttk.Button(answer_actions, text="减选项", command=self.remove_option).pack(side="left")

        tk.Label(panel, text="解析", font=BOLD_FONT, bg=self.tc["bg"], fg=self.tc["text"]).pack(
            anchor="w", padx=12
        )
        self.explanation_text = scrolledtext.ScrolledText(
            panel,
            height=6,
            wrap=tk.WORD,
            font=DEFAULT_FONT,
            bg=self.tc["bg_secondary"],
            fg=self.tc["text"],
            insertbackground=self.tc["text"],
        )
        self.explanation_text.pack(fill="both", expand=True, padx=12, pady=(4, 10))

        footer = tk.Frame(panel, bg=self.tc["bg"])
        footer.pack(fill="x", padx=12, pady=(0, 12))
        self.ai_review_btn = ttk.Button(footer, text="AI 复核当前题", command=self.open_ai_review_current_question)
        self.ai_review_btn.pack(side="left")
        self.ai_generate_btn = ttk.Button(footer, text="AI 生成答案解析", command=self.generate_answer_with_ai)
        self.ai_generate_btn.pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="保存当前题", command=self.save_current_question).pack(side="right")
        ttk.Button(footer, text="保存并下一题", command=self.save_and_next_question).pack(side="right", padx=(0, 8))

    def _bind_change_events(self):
        """绑定输入变化后自动保存草稿。"""
        self.type_var.trace_add("write", lambda *_: self._queue_auto_save())
        self.question_text.bind("<KeyRelease>", lambda _event: self._queue_auto_save())
        self.explanation_text.bind("<KeyRelease>", lambda _event: self._queue_auto_save())
        for entry in self.option_entries:
            entry.bind("<KeyRelease>", lambda _event: self._queue_auto_save())

    def _on_list_select(self, _event=None):
        if self._suspend_list_events:
            return
        selection = self.question_list.curselection()
        if not selection:
            return
        new_index = selection[0]
        if new_index == self.current_index:
            return
        self._store_current_draft(validate=False)
        self.current_index = new_index
        self._load_current_draft()

    def _on_type_change(self, _event=None):
        if self._loading_draft:
            return
        qtype = LABEL_TO_TYPE.get(self.type_var.get(), "single")
        for variable in self.option_vars:
            variable.set("")
        self.visible_option_count = 4
        self._reset_answer_state(qtype)
        self._update_editor_visibility()
        self._render_answer_controls()
        self._queue_auto_save()

    def _reset_answer_state(self, qtype: str):
        """切换题型时同步清空不适用的答案状态。"""
        if qtype in ("single", "judgement"):
            self.answer_choice_var.set("")
            for var in self.answer_check_vars:
                var.set(False)
            self.answer_text_var.set("")
        elif qtype == "multiple":
            self.answer_choice_var.set("")
            self.answer_text_var.set("")
        else:
            self.answer_choice_var.set("")
            for var in self.answer_check_vars:
                var.set(False)
            self.answer_text_var.set("")

    def _update_editor_visibility(self):
        qtype = LABEL_TO_TYPE.get(self.type_var.get(), "single")
        if qtype in CHOICE_TYPES:
            self.options_frame.pack_forget()
            self.options_frame.pack(fill="x", padx=12, pady=(0, 10), before=self.answer_row)
            self._update_option_rows()
            self.hint_label.config(text="答案填写选项字母。单选如 A，多选如 ABC。")
        elif qtype == "judgement":
            self.options_frame.pack_forget()
            self.hint_label.config(text="答案填写 A/正确 或 B/错误。")
        else:
            self.options_frame.pack_forget()
            self.hint_label.config(text="答案填写标准答案或参考答案。")

    def _update_option_rows(self):
        """按当前可见数量显示选择题选项行。"""
        for index, row in enumerate(self.option_rows):
            if index < self.visible_option_count:
                if not row.winfo_ismapped():
                    row.pack(fill="x", padx=8, pady=3)
            else:
                row.pack_forget()

    def _load_current_draft(self):
        draft = self.drafts[self.current_index]
        self._suspend_list_events = True
        self._loading_draft = True
        self.type_var.set(QUESTION_TYPE_LABELS.get(draft.type, "单选题"))
        self.question_text.delete("1.0", tk.END)
        self.question_text.insert("1.0", draft.question)
        for index, variable in enumerate(self.option_vars):
            variable.set(draft.options[index] if index < len(draft.options) else "")
        if draft.type in CHOICE_TYPES:
            self.visible_option_count = max(2, min(len(self.option_vars), len(draft.options) or 4))
        else:
            self.visible_option_count = 4
        self.explanation_text.delete("1.0", tk.END)
        self.explanation_text.insert("1.0", draft.explanation)
        self._reset_answer_state(draft.type)
        self._update_editor_visibility()
        self._render_answer_controls()
        self._apply_answer_to_controls(draft)
        self.question_list.selection_clear(0, tk.END)
        self.question_list.selection_set(self.current_index)
        self.question_list.see(self.current_index)
        self._loading_draft = False
        self._suspend_list_events = False

    def _store_current_draft(self, validate: bool = False, show_errors: bool = True) -> bool:
        draft = self._collect_current_draft()
        errors = self.builder.validate_draft(draft) if validate else []
        if errors and show_errors:
            messagebox.showerror(
                "题目校验失败",
                f"第{self.current_index + 1}题：\n" + "\n".join(errors),
                parent=self.window,
            )
            return False
        self.drafts[self.current_index] = draft
        self._refresh_list()
        return not errors

    def _collect_current_draft(self) -> QuestionDraft:
        qtype = LABEL_TO_TYPE.get(self.type_var.get(), "single")
        options = [variable.get().strip() for variable in self.option_vars[: self.visible_option_count]]
        return QuestionDraft(
            type=qtype,
            question=self.question_text.get("1.0", "end-1c").strip(),
            options=options,
            answer=self._collect_answer_value(qtype),
            explanation=self.explanation_text.get("1.0", "end-1c").strip(),
        )

    def _collect_answer_value(self, qtype: str) -> str:
        """根据当前题型收集答案值。"""
        if qtype == "judgement":
            return format_judge_answer(self.answer_choice_var.get().strip())
        if qtype == "single":
            return self.answer_choice_var.get().strip()
        if qtype == "multiple":
            letters = [chr(ord("A") + i) for i in range(self.visible_option_count)]
            return "".join(letter for letter, var in zip(letters, self.answer_check_vars) if var.get())
        return self.answer_text_var.get().strip()

    def _render_answer_controls(self):
        """按题型渲染答案选择控件。"""
        for widget in self.answer_control_container.winfo_children():
            widget.destroy()
        self.answer_focus_widgets = []

        qtype = LABEL_TO_TYPE.get(self.type_var.get(), "single")
        if qtype in ("single", "multiple"):
            letters = [chr(ord("A") + i) for i in range(self.visible_option_count)]
            if qtype == "single":
                self.answer_choice_var.set(self.answer_choice_var.get() if self.answer_choice_var.get() in letters else "")
                grid = tk.Frame(self.answer_control_container, bg=self.tc["bg"])
                grid.pack(fill="x")
                for i, letter in enumerate(letters):
                    rb = tk.Radiobutton(
                        grid,
                        text=letter,
                        value=letter,
                        variable=self.answer_choice_var,
                        indicatoron=False,
                        width=4,
                        command=self._queue_auto_save,
                        bg=self.tc["bg_secondary"],
                        fg=self.tc["text"],
                        selectcolor=self.tc["primary"],
                        activebackground=self.tc["card_bg"],
                        activeforeground=self.tc["text"],
                        relief="ridge",
                    )
                    rb.grid(row=0, column=i, padx=2, pady=2, sticky="ew")
                    self.answer_focus_widgets.append(rb)
            else:
                grid = tk.Frame(self.answer_control_container, bg=self.tc["bg"])
                grid.pack(fill="x")
                for index, (letter, var) in enumerate(zip(letters, self.answer_check_vars)):
                    cb = tk.Checkbutton(
                        grid,
                        text=letter,
                        variable=var,
                        command=self._queue_auto_save,
                        bg=self.tc["bg_secondary"],
                        fg=self.tc["text"],
                        activebackground=self.tc["card_bg"],
                        activeforeground=self.tc["text"],
                        selectcolor=self.tc["primary"],
                        indicatoron=False,
                        relief="ridge",
                        width=4,
                    )
                    cb.grid(row=index // 3, column=index % 3, padx=2, pady=2, sticky="ew")
                    self.answer_focus_widgets.append(cb)
                self.answer_choice_var.set("")
        elif qtype == "judgement":
            current = format_judge_answer(self.answer_choice_var.get())
            self.answer_choice_var.set(current if current in {"正确", "错误"} else "")
            row = tk.Frame(self.answer_control_container, bg=self.tc["bg"])
            row.pack(fill="x")
            options = [("正确", "正确"), ("错误", "错误")]
            for index, (label, value) in enumerate(options):
                rb = tk.Radiobutton(
                    row,
                    text=label,
                    value=value,
                    variable=self.answer_choice_var,
                    indicatoron=False,
                    width=8,
                    command=self._queue_auto_save,
                    bg=self.tc["bg_secondary"],
                    fg=self.tc["text"],
                    selectcolor=self.tc["primary"],
                    activebackground=self.tc["card_bg"],
                    activeforeground=self.tc["text"],
                    relief="ridge",
                )
                rb.grid(row=0, column=index, padx=2, pady=2, sticky="ew")
                self.answer_focus_widgets.append(rb)
        else:
            entry = ttk.Entry(self.answer_control_container, textvariable=self.answer_text_var)
            entry.pack(fill="x")
            entry.bind("<KeyRelease>", lambda _event: self._queue_auto_save())
            self.answer_focus_widgets = [entry]

    def _apply_answer_to_controls(self, draft: QuestionDraft):
        """把草稿中的答案回填到控件。"""
        qtype = draft.type
        if qtype == "multiple":
            letters = set(str(draft.answer or "").upper())
            for i, var in enumerate(self.answer_check_vars):
                var.set(chr(ord("A") + i) in letters)
            self.answer_choice_var.set("")
            self.answer_text_var.set("")
        elif qtype == "single":
            self.answer_choice_var.set((draft.answer or "").strip().upper()[:1])
            for var in self.answer_check_vars:
                var.set(False)
            self.answer_text_var.set("")
        elif qtype == "judgement":
            value = normalize_judge_answer(draft.answer)
            if value == "A":
                self.answer_choice_var.set("正确")
            elif value == "B":
                self.answer_choice_var.set("错误")
            else:
                self.answer_choice_var.set("")
            for var in self.answer_check_vars:
                var.set(False)
            self.answer_text_var.set("")
        else:
            self.answer_text_var.set(draft.answer)
            self.answer_choice_var.set("")
            for var in self.answer_check_vars:
                var.set(False)

    def _refresh_list(self):
        if not hasattr(self, "question_list"):
            return
        self._suspend_list_events = True
        self.question_list.delete(0, tk.END)
        for index, draft in enumerate(self.drafts, start=1):
            status = "✓" if not self.builder.validate_draft(draft) else "未完成"
            self.question_list.insert(tk.END, f"{index}. [{status}] {self.builder.question_summary(draft)}")
        self._update_summary()
        self.question_list.selection_clear(0, tk.END)
        self.question_list.selection_set(self.current_index)
        self.question_list.see(self.current_index)
        self._suspend_list_events = False

    def _update_summary(self):
        counts = {key: 0 for key in QUESTION_TYPE_LABELS}
        for draft in self.drafts:
            counts[draft.type] = counts.get(draft.type, 0) + 1
        lines = [f"总题数：{len(self.drafts)}"]
        lines.extend(f"{QUESTION_TYPE_LABELS[key]}：{counts.get(key, 0)}" for key in QUESTION_TYPE_LABELS)
        self.summary_label.config(text="\n".join(lines))

    def save_current_question(self) -> bool:
        if self._store_current_draft(validate=True, show_errors=True):
            messagebox.showinfo("保存当前题", "当前题已保存", parent=self.window)
            self._queue_auto_save()
            return True
        return False

    def save_and_next_question(self) -> bool:
        if not self._store_current_draft(validate=True, show_errors=True):
            return False
        if self.current_index >= len(self.drafts) - 1:
            self.drafts.append(self.builder.new_draft())
        self.current_index += 1
        self._refresh_list()
        self._load_current_draft()
        self._queue_auto_save()
        return True

    def add_question(self):
        self._store_current_draft(validate=False, show_errors=False)
        self.drafts.append(self.builder.new_draft())
        self.current_index = len(self.drafts) - 1
        self._refresh_list()
        self._load_current_draft()

    def duplicate_question(self):
        self._store_current_draft(validate=False, show_errors=False)
        self.drafts.insert(self.current_index + 1, self.builder.duplicate_draft(self.drafts[self.current_index]))
        self.current_index += 1
        self._refresh_list()
        self._load_current_draft()

    def delete_question(self):
        if len(self.drafts) == 1:
            messagebox.showinfo("删除题目", "题库至少需要保留一道题", parent=self.window)
            return
        if not messagebox.askyesno("删除题目", "确定删除当前题吗？", parent=self.window):
            return
        self.drafts.pop(self.current_index)
        self.current_index = min(self.current_index, len(self.drafts) - 1)
        self._refresh_list()
        self._load_current_draft()
        self._queue_auto_save()

    def move_up(self):
        if self.current_index <= 0:
            return
        self._store_current_draft(validate=False, show_errors=False)
        self.drafts[self.current_index - 1], self.drafts[self.current_index] = (
            self.drafts[self.current_index],
            self.drafts[self.current_index - 1],
        )
        self.current_index -= 1
        self._refresh_list()
        self._load_current_draft()
        self._queue_auto_save()

    def move_down(self):
        if self.current_index >= len(self.drafts) - 1:
            return
        self._store_current_draft(validate=False, show_errors=False)
        self.drafts[self.current_index + 1], self.drafts[self.current_index] = (
            self.drafts[self.current_index],
            self.drafts[self.current_index + 1],
        )
        self.current_index += 1
        self._refresh_list()
        self._load_current_draft()
        self._queue_auto_save()

    def add_option(self):
        qtype = LABEL_TO_TYPE.get(self.type_var.get(), "single")
        if qtype not in CHOICE_TYPES:
            return
        if self.visible_option_count >= len(self.option_vars):
            messagebox.showinfo("提示", "选项已达上限", parent=self.window)
            return
        self.visible_option_count += 1
        self._update_option_rows()
        self._render_answer_controls()
        self.option_entries[self.visible_option_count - 1].focus_set()
        self._queue_auto_save()

    def remove_option(self):
        qtype = LABEL_TO_TYPE.get(self.type_var.get(), "single")
        if qtype not in CHOICE_TYPES:
            return
        if self.visible_option_count <= 2:
            messagebox.showinfo("提示", "选择题至少保留两个选项", parent=self.window)
            return
        last_index = self.visible_option_count - 1
        self.option_vars[last_index].set("")
        self.answer_check_vars[last_index].set(False)
        if self.answer_choice_var.get() == chr(ord("A") + last_index):
            self.answer_choice_var.set("")
        self.visible_option_count -= 1
        self._update_option_rows()
        self._render_answer_controls()
        self._queue_auto_save()

    def apply_template(self):
        """插入一个更像正式题库编辑器的示例模板。"""
        templates = [
            QuestionDraft(
                type="single",
                question="以下哪一项最适合作为单选题的测试答案？",
                options=["测试选项一", "测试选项二", "测试选项三", "测试选项四"],
                answer="B",
                explanation="这里填写单选题解析。",
            ),
            QuestionDraft(
                type="multiple",
                question="以下哪些内容适合作为多选题测试选项？",
                options=["支持多个正确答案", "可用于测试答案回显", "不需要填写题干", "可检查选项保存"],
                answer="ABD",
                explanation="这里填写多选题解析。",
            ),
            QuestionDraft(
                type="judgement",
                question="以下说法是否正确？",
                answer="正确",
                explanation="判断题答案可填写正确/错误。",
            ),
        ]
        self.drafts = templates
        self.current_index = 0
        self._refresh_list()
        self._load_current_draft()
        self._queue_auto_save()

    def clear_question_bank(self):
        """清空当前编辑器中的题库草稿。"""
        if not messagebox.askyesno(
            "清除题库",
            "确定要清除当前题库中的所有题目吗？此操作不会删除已保存的题库文件。",
            parent=self.window,
        ):
            return
        self.drafts = [self.builder.new_draft()]
        self.current_index = 0
        self.ai_histories = {}
        self._dirty = False
        self._refresh_list()
        self._load_current_draft()
        self.import_status_var.set("当前编辑器已清空。")

    def save_question_bank(self):
        if not self._store_current_draft(validate=True, show_errors=True):
            return
        try:
            question_bank = self.builder.build_question_bank(self.drafts)
        except ValueError as exc:
            messagebox.showerror("题库校验失败", str(exc), parent=self.window)
            self._select_first_invalid_draft()
            return

        QUESTION_BANK_DIR.mkdir(parents=True, exist_ok=True)
        file_path = filedialog.asksaveasfilename(
            parent=self.window,
            title="保存题库文件",
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            initialfile="新建题库.json",
            initialdir=str(QUESTION_BANK_DIR),
        )
        if not file_path:
            return

        try:
            question_bank.file_path = file_path
            save_questions_to_file(question_bank, file_path)
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc), parent=self.window)
            return

        if messagebox.askyesno("保存成功", "题库已保存，是否立即加载到首页？", parent=self.window):
            if self.on_saved:
                self.on_saved(file_path)
        self._dirty = False
        self.window.destroy()

    def open_ai_review_current_question(self):
        """打开当前草稿题目的 AI 复核窗口。"""
        self._store_current_draft(validate=False, show_errors=False)
        draft = self.drafts[self.current_index]
        if not draft.question.strip():
            messagebox.showwarning("AI 复核", "请先填写题干", parent=self.window)
            return
        question = self._draft_to_question(draft)
        history = self.ai_histories.setdefault(self.current_index, [])
        show_ai_review_window(self.window, question, draft.answer, history)

    def generate_answer_with_ai(self):
        """使用 AI 生成当前题目的答案和解析。"""
        self._store_current_draft(validate=False, show_errors=False)
        draft = self.drafts[self.current_index]
        if not draft.question.strip():
            messagebox.showwarning("AI 生成", "请先填写题干", parent=self.window)
            return
        question = self._draft_to_question(draft)
        self._set_ai_buttons_state("disabled")

        def worker():
            try:
                result = AIService().generate_answer_and_explanation(question)
                self.window.after(0, lambda: self._apply_ai_generated_answer(result))
            except AIServiceError as exc:
                self.window.after(0, lambda: self._on_ai_generate_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_ai_generated_answer(self, result):
        """将 AI 生成结果回填到答案与解析控件。"""
        answer = result.get("answer", "").strip()
        explanation = result.get("explanation", "").strip()
        qtype = LABEL_TO_TYPE.get(self.type_var.get(), "single")
        self._apply_generated_answer(qtype, answer)
        if explanation:
            self.explanation_text.delete("1.0", tk.END)
            self.explanation_text.insert("1.0", explanation)
        self._store_current_draft(validate=False, show_errors=False)
        self._queue_auto_save()
        self._set_ai_buttons_state("normal")
        messagebox.showinfo("AI 生成", "答案与解析已回填，请人工确认后保存", parent=self.window)

    def _apply_generated_answer(self, qtype: str, answer: str):
        """按题型把答案回填到对应控件。"""
        normalized = answer.strip()
        if qtype == "judgement":
            value = normalize_judge_answer(normalized)
            if value == "A":
                self.answer_choice_var.set("正确")
            elif value == "B":
                self.answer_choice_var.set("错误")
            else:
                self.answer_choice_var.set("")
            self.answer_text_var.set("")
            for var in self.answer_check_vars:
                var.set(False)
        elif qtype == "single":
            letters = [chr(ord("A") + i) for i in range(self.visible_option_count)]
            value = normalized.upper()[:1]
            self.answer_choice_var.set(value if value in letters else "")
            self.answer_text_var.set("")
            for var in self.answer_check_vars:
                var.set(False)
        elif qtype == "multiple":
            letters = [chr(ord("A") + i) for i in range(self.visible_option_count)]
            selected = set(ch for ch in normalized.upper() if ch in letters)
            for index, var in enumerate(self.answer_check_vars):
                var.set(chr(ord("A") + index) in selected)
            self.answer_choice_var.set("")
            self.answer_text_var.set("")
        else:
            self.answer_text_var.set(normalized)
            self.answer_choice_var.set("")
            for var in self.answer_check_vars:
                var.set(False)

    def _on_ai_generate_error(self, message: str):
        self._set_ai_buttons_state("normal")
        messagebox.showerror("AI 生成失败", message, parent=self.window)

    def _set_ai_buttons_state(self, state: str):
        for button in (getattr(self, "ai_review_btn", None), getattr(self, "ai_generate_btn", None)):
            if button:
                button.config(state=state)

    def _draft_to_question(self, draft: QuestionDraft) -> Question:
        """将编辑中的草稿转换为 AI 复核使用的题目对象。"""
        options = []
        if draft.type in CHOICE_TYPES:
            for index, option in enumerate(draft.options):
                option_text = option.strip()
                if option_text:
                    options.append(f"{chr(ord('A') + index)}. {option_text}")
        return Question(
            id=self.current_index + 1,
            type=draft.type,
            question=draft.question,
            options=options,
            answer=draft.answer,
            explanation=draft.explanation,
        )

    def _queue_auto_save(self):
        if self._loading_draft:
            return
        self._dirty = True
        if self._auto_save_job is not None:
            try:
                self.window.after_cancel(self._auto_save_job)
            except tk.TclError:
                pass
        self._auto_save_job = self.window.after(600, self._auto_save_draft)

    def _auto_save_draft(self):
        self._auto_save_job = None
        self._store_current_draft(validate=False, show_errors=False)

    def _select_first_invalid_draft(self):
        for index, draft in enumerate(self.drafts):
            if self.builder.validate_draft(draft):
                self.current_index = index
                self._refresh_list()
                self._load_current_draft()
                return

    def close_window(self):
        self._store_current_draft(validate=False, show_errors=False)
        if self._dirty:
            should_close = messagebox.askyesno("关闭窗口", "当前题库还有未导出的修改，确定关闭吗？", parent=self.window)
            if not should_close:
                return
        if self._auto_save_job is not None:
            try:
                self.window.after_cancel(self._auto_save_job)
            except tk.TclError:
                pass
            self._auto_save_job = None
        self.window.destroy()
