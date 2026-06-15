#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 复核对话窗口。"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional

from core.config import DEFAULT_FONT, BOLD_FONT, get_font, get_theme_colors
from core.models import Question
from services.ai_service import AIService, AIServiceError
from ui.components import center_window


class AIReviewWindow:
    """围绕当前题目的 AI 复核与追问窗口。"""

    def __init__(
        self,
        parent: tk.Tk,
        question: Question,
        user_answer: str = "",
        history: Optional[List[Dict[str, str]]] = None,
    ):
        self.parent = parent
        self.question = question
        self.user_answer = user_answer
        self.history = history if history is not None else []
        self.ai_service = AIService()
        self.tc = get_theme_colors()

        self.window = tk.Toplevel(parent)
        self.window.title(f"AI 复核本题 - ID {question.id}")
        self.window.configure(bg=self.tc["bg"])
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self._close_window)
        center_window(self.window, 780, 620)

        self._create_ui()
        self._render_history()
        if not self.history:
            self._start_review()

    def _create_ui(self):
        header = tk.Frame(self.window, bg=self.tc["bg"])
        header.pack(fill="x", padx=15, pady=(15, 8))
        tk.Label(
            header,
            text="AI 复核助手",
            font=BOLD_FONT,
            bg=self.tc["bg"],
            fg=self.tc["text"],
        ).pack(side="left")
        ttk.Button(header, text="重新复核", command=self._restart_review).pack(side="right")
        ttk.Button(header, text="复制全部", command=self._copy_all).pack(side="right", padx=(0, 8))

        chat_outer = tk.Frame(self.window, bg=self.tc["bg_secondary"])
        chat_outer.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.chat_canvas = tk.Canvas(
            chat_outer,
            bg=self.tc["bg_secondary"],
            highlightthickness=0,
        )
        self.chat_scrollbar = ttk.Scrollbar(chat_outer, orient="vertical", command=self.chat_canvas.yview)
        self.chat_frame = tk.Frame(self.chat_canvas, bg=self.tc["bg_secondary"])
        self.chat_window = self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        self.chat_canvas.configure(yscrollcommand=self.chat_scrollbar.set)
        self.chat_canvas.pack(side="left", fill="both", expand=True)
        self.chat_scrollbar.pack(side="right", fill="y")
        self.chat_frame.bind("<Configure>", self._on_chat_frame_configure)
        self.chat_canvas.bind("<Configure>", self._on_chat_canvas_configure)
        self.chat_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.chat_width = 720

        input_frame = tk.Frame(self.window, bg=self.tc["bg"])
        input_frame.pack(fill="x", padx=15, pady=(0, 15))
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_var)
        self.input_entry.pack(side="left", fill="x", expand=True)
        self.input_entry.bind("<Return>", lambda _event: self._send_followup())
        self.send_btn = ttk.Button(input_frame, text="发送", command=self._send_followup)
        self.send_btn.pack(side="right", padx=(8, 0))

    def _append_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self._render_history()

    def _render_history(self):
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        for item in self.history:
            self._render_message(item.get("role", "assistant"), item.get("content", ""))
        self.window.after_idle(self._scroll_to_bottom)

    def _render_message(self, role: str, content: str):
        is_user = role == "user"
        row = tk.Frame(self.chat_frame, bg=self.tc["bg_secondary"])
        row.pack(fill="x", padx=12, pady=8)

        bubble_bg = self.tc["primary"] if is_user else self.tc["bg"]
        bubble_fg = "#ffffff" if is_user else self.tc["text"]
        anchor_side = "right" if is_user else "left"
        max_width = max(360, min(720, int(getattr(self, "chat_width", 720) * (0.58 if is_user else 0.92))))
        bubble = tk.Frame(
            row,
            bg=bubble_bg,
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=self.tc["card_border"] if not is_user else self.tc["primary"],
        )
        bubble.pack(side=anchor_side, padx=(260, 12) if is_user else (12, 24), anchor="e" if is_user else "w")

        title = "你" if is_user else "AI"
        tk.Label(
            bubble,
            text=title,
            font=get_font(9, "bold"),
            bg=bubble_bg,
            fg=bubble_fg,
        ).pack(anchor="e" if is_user else "w", padx=12, pady=(9, 2))

        self._render_markdown_text(bubble, content, bubble_bg, bubble_fg, max_width)

    def _render_markdown_text(self, parent, content: str, bg: str, fg: str, max_width: int):
        content_frame = tk.Frame(parent, bg=bg)
        content_frame.pack(fill="x", padx=12, pady=(4, 12))
        lines = (content or "").splitlines() or [""]
        in_code = False
        code_lines = []
        for raw_line in lines:
            line = raw_line.rstrip()
            if line.strip().startswith("```"):
                if in_code:
                    self._render_code_label(content_frame, "\n".join(code_lines), max_width)
                    code_lines = []
                    in_code = False
                else:
                    in_code = True
                continue
            if in_code:
                code_lines.append(raw_line)
                continue
            self._render_markdown_label(content_frame, line, bg, fg, max_width)
        if code_lines:
            self._render_code_label(content_frame, "\n".join(code_lines), max_width)

    def _render_markdown_label(self, parent, line: str, bg: str, fg: str, max_width: int):
        stripped = line.strip()
        display = self._clean_markdown_inline(stripped)
        font = DEFAULT_FONT
        text_fg = fg
        pad_left = 0
        if not display:
            display = " "
        elif stripped.startswith("#"):
            display = self._clean_markdown_inline(stripped.lstrip("#").strip())
            font = get_font(11, "bold")
        elif stripped.startswith(("- ", "* ")):
            display = "• " + self._clean_markdown_inline(stripped[2:].strip())
            pad_left = 18
        elif len(stripped) > 2 and stripped[0].isdigit() and ". " in stripped[:4]:
            display = self._clean_markdown_inline(stripped)
            pad_left = 18
        elif stripped.startswith(">"):
            display = self._clean_markdown_inline(stripped.lstrip(">").strip())
            text_fg = self.tc["text_secondary"]
            pad_left = 12

        label = tk.Label(
            parent,
            text=display,
            font=font,
            bg=bg,
            fg=text_fg,
            justify="left",
            anchor="w",
            wraplength=max_width - 36,
        )
        label.pack(fill="x", padx=(pad_left, 0), pady=(1, 4), anchor="w")

    def _render_code_label(self, parent, content: str, max_width: int):
        code_bg = "#1f2937" if self.tc["bg"] != "#f0f0f0" else "#f3f4f6"
        code_fg = "#e5e7eb" if code_bg == "#1f2937" else "#111827"
        label = tk.Label(
            parent,
            text=content or " ",
            font=get_font(9),
            bg=code_bg,
            fg=code_fg,
            justify="left",
            anchor="w",
            wraplength=max_width - 44,
            padx=8,
            pady=6,
        )
        label.pack(fill="x", padx=0, pady=(4, 8), anchor="w")

    @staticmethod
    def _clean_markdown_inline(text: str) -> str:
        value = text.replace("**", "").replace("__", "").replace("`", "")
        value = value.replace("[", "").replace("](", "：").replace(")", "")
        return value

    def _on_chat_frame_configure(self, _event=None):
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def _on_chat_canvas_configure(self, event):
        self.chat_width = event.width
        self.chat_canvas.itemconfigure(self.chat_window, width=event.width)

    def _on_mousewheel(self, event):
        try:
            self.chat_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            pass

    def _scroll_to_bottom(self):
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        self.chat_canvas.yview_moveto(1.0)

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.send_btn.config(state=state)
        self.input_entry.config(state=state)

    def _restart_review(self):
        self.history.clear()
        self._render_history()
        self._start_review()

    def _start_review(self):
        self._run_ai_task(
            display_user_message="请复核本题，判断题库答案和解析是否可靠。",
            task=lambda history: self.ai_service.review_question(self.question, self.user_answer, history),
        )

    def _send_followup(self):
        message = self.input_var.get().strip()
        if not message:
            return
        self.input_var.set("")
        self._run_ai_task(
            display_user_message=message,
            task=lambda history: self.ai_service.ask_followup(
                self.question,
                self.user_answer,
                message,
                history,
            ),
        )

    def _run_ai_task(self, display_user_message: str, task):
        history_snapshot = list(self.history)
        self._append_message("user", display_user_message)
        self._set_busy(True)

        def worker():
            try:
                answer = task(history_snapshot)
                self.window.after(0, lambda ai_answer=answer: self._on_ai_success(ai_answer))
            except AIServiceError as exc:
                message = str(exc)
                self.window.after(0, lambda error_message=message: self._on_ai_error(error_message))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ai_success(self, answer: str):
        self._append_message("assistant", answer)
        self._set_busy(False)

    def _on_ai_error(self, message: str):
        self.history.pop()
        self._render_history()
        self._set_busy(False)
        messagebox.showerror("AI 复核失败", message, parent=self.window)

    def _copy_all(self):
        chunks = []
        for item in self.history:
            title = "你" if item.get("role") == "user" else "AI"
            chunks.append(f"{title}：\n{item.get('content', '')}")
        content = "\n\n".join(chunks).strip()
        if not content:
            return
        self.window.clipboard_clear()
        self.window.clipboard_append(content)
        messagebox.showinfo("复制", "AI 对话内容已复制", parent=self.window)

    def _close_window(self):
        try:
            self.chat_canvas.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass
        self.window.destroy()


def show_ai_review_window(
    parent: tk.Tk,
    question: Question,
    user_answer: str = "",
    history: Optional[List[Dict[str, str]]] = None,
):
    """显示 AI 复核窗口。"""
    AIReviewWindow(parent, question, user_answer, history)
