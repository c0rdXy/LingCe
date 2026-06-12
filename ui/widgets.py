#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版共享 UI 组件 — 练习模式和考试模式共用
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import List, Dict, Any, Optional, Callable
from core.config import DEFAULT_FONT, BOLD_FONT, COLORS, get_theme_colors
from core.models import Question
from core.utils import format_judge_answer, normalize_judge_answer


# ---------------------------------------------------------------------------
# 题型中文名称映射
# ---------------------------------------------------------------------------
TYPE_NAMES = {
    "single": "单选题",
    "multiple": "多选题",
    "judge": "判断题",
    "judgement": "判断题",
    "fill": "填空题",
    "short": "简答题",
    "essay": "简答题",
}


def get_question_type_name(question_type: str) -> str:
    """获取题型中文名称"""
    return TYPE_NAMES.get(question_type, "未知类型")


# ---------------------------------------------------------------------------
# 增强版题目渲染组件
# ---------------------------------------------------------------------------
class QuestionWidget:
    """支持普通模式 & 回顾模式的题目渲染组件"""

    def __init__(
        self,
        parent: tk.Frame,
        question: Question,
        index: int = 1,
        show_id: bool = False,
        review_mode: bool = False,
        user_answer: str = "",
        correct_answer: str = "",
    ):
        self.parent = parent
        self.question = question
        self.index = index
        self.show_id = show_id
        self.review_mode = review_mode
        self.user_answer = user_answer
        self.correct_answer = correct_answer

        # 答题变量
        self.answer_var = tk.StringVar()
        self.multi_vars: list = []  # [(BooleanVar, letter), ...]
        self.text_widget: Optional[scrolledtext.ScrolledText] = None

    # ---- 公共接口 ----

    def render(self) -> tk.Frame:
        """渲染完整的题目框架，返回外层 Frame"""
        tc = get_theme_colors()
        frame = tk.Frame(self.parent, bg=tc["card_bg"], relief="solid", bd=1,
                         highlightbackground=tc["card_border"])

        # 标题栏
        self._render_title(frame)

        # 内容区
        content = tk.Frame(frame, bg=tc["card_bg"])
        content.pack(fill="both", expand=True, padx=10, pady=10)

        # 题目文本
        text_height = 2 if self.question.type in ("fill", "short") else (3 if self.review_mode else 6)
        q_text = scrolledtext.ScrolledText(
            content, height=text_height, wrap=tk.WORD,
            font=DEFAULT_FONT, relief="flat", bd=1,
            bg=tc["card_bg"], fg=tc["text"], insertbackground=tc["text"],
        )
        q_text.pack(fill="x", pady=(0, 10))
        q_text.insert("1.0", self.question.question)
        q_text.config(state="disabled")

        # 选项 / 输入区
        self._render_options(content)

        # 回顾模式：追加答案解析
        if self.review_mode:
            self._render_analysis(content)

        return frame

    def get_user_answer(self) -> str:
        """获取用户作答"""
        qtype = self.question.type
        if qtype == "single" or qtype in ("judge", "judgement"):
            return self.answer_var.get().strip()
        elif qtype == "multiple":
            selected = [letter for var, letter in self.multi_vars if var.get()]
            return "".join(sorted(selected))
        elif qtype in ("fill", "short", "essay"):
            if self.text_widget:
                return self.text_widget.get("1.0", tk.END).strip()
            return ""
        return ""

    def set_user_answer(self, answer: str):
        """恢复用户作答"""
        qtype = self.question.type
        if qtype in ("judge", "judgement"):
            self.answer_var.set(format_judge_answer(answer))
        elif qtype == "single":
            self.answer_var.set(answer)
        elif qtype == "multiple":
            for var, letter in self.multi_vars:
                var.set(letter in answer.upper())
        elif qtype in ("fill", "short", "essay"):
            if self.text_widget and self.text_widget.cget("state") == "normal":
                self.text_widget.delete("1.0", tk.END)
                self.text_widget.insert("1.0", answer)

    # ---- 内部渲染 ----

    def _render_title(self, parent):
        tc = get_theme_colors()
        title_frame = tk.Frame(parent, bg=tc["header_bg"], height=40)
        title_frame.pack(fill="x", padx=2, pady=2)
        title_frame.pack_propagate(False)

        type_name = get_question_type_name(self.question.type)
        title_text = f"第 {self.index} 题 ({type_name})"
        if self.show_id:
            title_text += f" [ID: {self.question.id}]"

        tk.Label(
            title_frame, text=title_text, font=BOLD_FONT,
            background=tc["header_bg"], foreground=tc["header_fg"]
        ).pack(side="left", padx=10, pady=8)

    def _render_options(self, parent):
        qtype = self.question.type
        options = self.question.options

        if qtype == "single":
            self._render_single(parent, options)
        elif qtype == "multiple":
            self._render_multiple(parent, options)
        elif qtype in ("judge", "judgement"):
            self._render_judge(parent)
        elif qtype in ("fill", "short", "essay"):
            self._render_text_input(parent)

    def _render_single(self, parent, options: List[str]):
        self.answer_var = tk.StringVar()
        tc = get_theme_colors()
        options_frame = tk.Frame(parent, bg=tc["card_bg"])
        options_frame.pack(fill="x", pady=5)

        for option in options:
            letter = option.split(".", 1)[0].strip() if "." in option else option[:1]
            text = option.split(".", 1)[1].strip() if "." in option else option
            container = tk.Frame(options_frame, bg=tc["card_bg"])
            container.pack(fill="x", pady=3)

            if self.review_mode:
                # 回顾：高亮正确/错误
                fg = tc["text"]
                if letter.upper() == self.correct_answer.upper():
                    fg = "green"
                elif letter.upper() == self.user_answer.upper() and letter.upper() != self.correct_answer.upper():
                    fg = "red"

                tk.Label(container, text=f"{letter}.", font=DEFAULT_FONT,
                         fg=fg, bg=tc["card_bg"]).pack(side="left", anchor="n")
                lbl = tk.Label(container, text=text, font=DEFAULT_FONT,
                               fg=fg, bg=tc["card_bg"], anchor="w", justify="left")
                lbl.pack(side="left", fill="x", expand=True, padx=(5, 0))
            else:
                rb = ttk.Radiobutton(container, text=f"{letter}.",
                                     variable=self.answer_var, value=letter)
                rb.pack(side="left", anchor="n")
                lbl = tk.Label(container, text=text, font=DEFAULT_FONT,
                               bg=tc["card_bg"], fg=tc["text"], anchor="w", justify="left")
                lbl.pack(side="left", fill="x", expand=True, padx=(5, 0))
                lbl.bind("<Button-1>", lambda e, v=letter: self.answer_var.set(v))

            # 动态换行
            container.bind("<Configure>",
                           lambda e, l=lbl, c=container: self._update_wraplength(l, c))

    def _render_multiple(self, parent, options: List[str]):
        self.multi_vars = []
        tc = get_theme_colors()
        options_frame = tk.Frame(parent, bg=tc["card_bg"])
        options_frame.pack(fill="x", pady=5)

        user_letters = set(self.user_answer.upper()) if self.review_mode else set()
        correct_letters = set(self.correct_answer.upper()) if self.review_mode else set()

        for option in options:
            letter = option.split(".", 1)[0].strip() if "." in option else option[:1]
            text = option.split(".", 1)[1].strip() if "." in option else option
            container = tk.Frame(options_frame, bg=tc["card_bg"])
            container.pack(fill="x", pady=3)

            if self.review_mode:
                fg = tc["text"]
                if letter.upper() in correct_letters:
                    fg = "green"
                elif letter.upper() in user_letters and letter.upper() not in correct_letters:
                    fg = "red"

                tk.Label(container, text=f"{letter}.", font=DEFAULT_FONT,
                         fg=fg, bg=tc["card_bg"]).pack(side="left", anchor="n")
                lbl = tk.Label(container, text=text, font=DEFAULT_FONT,
                               fg=fg, bg=tc["card_bg"], anchor="w", justify="left")
                lbl.pack(side="left", fill="x", expand=True, padx=(5, 0))
            else:
                var = tk.BooleanVar(value=False)
                cb = ttk.Checkbutton(container, text=f"{letter}.", variable=var)
                cb.pack(side="left", anchor="n")
                lbl = tk.Label(container, text=text, font=DEFAULT_FONT,
                               bg=tc["card_bg"], fg=tc["text"], anchor="w", justify="left")
                lbl.pack(side="left", fill="x", expand=True, padx=(5, 0))
                lbl.bind("<Button-1>", lambda e, v=var: v.set(not v.get()))
                self.multi_vars.append((var, letter))

            container.bind("<Configure>",
                           lambda e, l=lbl, c=container: self._update_wraplength(l, c))

    def _render_judge(self, parent):
        self.answer_var = tk.StringVar()
        tc = get_theme_colors()
        frame = tk.Frame(parent, bg=tc["card_bg"])
        frame.pack(fill="x", pady=5)
        judge_frame = tk.Frame(frame, bg=tc["card_bg"])
        judge_frame.pack(anchor="w", pady=10)

        if self.review_mode:
            correct = normalize_judge_answer(self.correct_answer)
            user = normalize_judge_answer(self.user_answer)
            fg_true = "green" if correct == "A" else tc["text"]
            fg_false = "green" if correct == "B" else tc["text"]
            if user == "A" and fg_true != "green":
                fg_true = "red"
            if user == "B" and fg_false != "green":
                fg_false = "red"

            tk.Label(judge_frame, text="正确", font=DEFAULT_FONT,
                     fg=fg_true, bg=tc["card_bg"]).pack(side="left", padx=20)
            tk.Label(judge_frame, text="错误", font=DEFAULT_FONT,
                     fg=fg_false, bg=tc["card_bg"]).pack(side="left", padx=20)
        else:
            ttk.Radiobutton(judge_frame, text="正确",
                            variable=self.answer_var, value="正确").pack(side="left", padx=20)
            ttk.Radiobutton(judge_frame, text="错误",
                            variable=self.answer_var, value="错误").pack(side="left", padx=20)

    def _render_text_input(self, parent):
        qtype = self.question.type
        label_text = "请填写答案：" if qtype == "fill" else "请输入答案："
        tc = get_theme_colors()
        input_frame = tk.Frame(parent, bg=tc["card_bg"])
        input_frame.pack(fill="both", expand=True, pady=5)

        tk.Label(input_frame, text=label_text, font=DEFAULT_FONT,
                 bg=tc["card_bg"], fg=tc["text"]).pack(anchor="w", pady=(10, 5))
        state = "disabled" if self.review_mode else "normal"
        self.text_widget = scrolledtext.ScrolledText(
            input_frame, font=DEFAULT_FONT, wrap=tk.WORD, height=6, state=state,
            bg=tc["bg_secondary"], fg=tc["text"], insertbackground=tc["text"],
        )
        self.text_widget.pack(fill="both", expand=True, pady=5)

        if self.review_mode and self.user_answer:
            self.text_widget.config(state="normal")
            self.text_widget.insert("1.0", self.user_answer)
            self.text_widget.config(state="disabled")

    def _render_analysis(self, parent):
        """回顾模式：显示答案解析"""
        tc = get_theme_colors()
        analysis_bg = tc["answer_bg"]
        analysis_frame = tk.Frame(parent, bg=analysis_bg, relief="solid", bd=1)
        analysis_frame.pack(fill="x", pady=(15, 5))
        is_text_answer = self.question.type in ("fill", "short", "essay")

        # 正确答案
        correct_text = self._format_answer_for_display(self.correct_answer)
        if is_text_answer:
            self._render_answer_text_block(
                analysis_frame, "正确答案：", correct_text,
                title_fg=tc["correct_fg"], text_fg=tc["correct_fg"], bg=analysis_bg,
            )
        else:
            answer_frame = tk.Frame(analysis_frame, bg=analysis_bg)
            answer_frame.pack(fill="x", padx=10, pady=5)
            tk.Label(answer_frame, text="正确答案：", font=BOLD_FONT,
                     bg=analysis_bg, fg=tc["text"]).pack(side="left")
            tk.Label(answer_frame, text=correct_text, font=DEFAULT_FONT,
                     fg=tc["correct_fg"], bg=analysis_bg).pack(side="left")

        # 用户答案
        if self.user_answer:
            is_correct = self._check_correct()
            user_fg = "green" if is_correct else "red"
            user_text = self._format_answer_for_display(self.user_answer)
            if is_text_answer:
                self._render_answer_text_block(
                    analysis_frame, "你的答案：", user_text,
                    title_fg=user_fg, text_fg=user_fg, bg=analysis_bg,
                )
            else:
                user_frame = tk.Frame(analysis_frame, bg=analysis_bg)
                user_frame.pack(fill="x", padx=10, pady=5)
                tk.Label(user_frame, text="你的答案：", font=BOLD_FONT,
                         bg=analysis_bg, fg=tc["text"]).pack(side="left")
                tk.Label(user_frame, text=user_text, font=DEFAULT_FONT,
                         fg=user_fg, bg=analysis_bg).pack(side="left")

        # 解析
        if self.question.explanation:
            expl_frame = tk.Frame(analysis_frame, bg=analysis_bg)
            expl_frame.pack(fill="x", padx=10, pady=5)
            tk.Label(expl_frame, text="解析：", font=BOLD_FONT,
                     bg=analysis_bg, fg=tc["text"]).pack(anchor="w")
            expl_text = tk.Text(expl_frame, height=3, wrap=tk.WORD, font=DEFAULT_FONT,
                                relief="flat", bg=analysis_bg, fg=tc["text"],
                                insertbackground=tc["text"])
            expl_text.pack(fill="x")
            expl_text.insert("1.0", self.question.explanation)
            expl_text.config(state="disabled")

    def _render_answer_text_block(self, parent, title: str, content: str,
                                  title_fg: str, text_fg: str, bg: str):
        """渲染多行答案块，用于填空/简答/问答回顾。"""
        tk.Label(parent, text=title, font=BOLD_FONT,
                 bg=bg, fg=title_fg).pack(anchor="w", padx=10, pady=(6, 0))

        height = self._answer_block_height(content)
        text = scrolledtext.ScrolledText(
            parent, height=height, wrap=tk.WORD, font=DEFAULT_FONT,
            relief="flat", bd=0, bg=bg, fg=text_fg,
            insertbackground=get_theme_colors()["text"],
        )
        text.pack(fill="x", padx=10, pady=(0, 5))
        text.insert("1.0", content)
        text.config(state="disabled")

    @staticmethod
    def _answer_block_height(content: str) -> int:
        """根据内容长度估算答案块高度。"""
        text = content or ""
        newline_count = text.count("\n")
        char_lines = len(text) // 80
        return max(3, min(10, newline_count + char_lines + 1))

    def _check_correct(self) -> bool:
        """检查用户答案是否正确"""
        if not self.user_answer:
            return False
        ua = self.user_answer.upper().strip()
        ca = self.correct_answer.upper().strip()
        qtype = self.question.type

        if qtype == "single" or qtype in ("judge", "judgement"):
            if qtype in ("judge", "judgement"):
                return normalize_judge_answer(ua) == normalize_judge_answer(ca)
            return ua == ca
        elif qtype == "multiple":
            return sorted(ua) == sorted(ca)
        else:
            return ua == ca

    def _format_answer_for_display(self, answer: str) -> str:
        """将内部答案转换成回顾页展示文本。"""
        if self.question.type in ("judge", "judgement"):
            return format_judge_answer(answer)
        return answer

    @staticmethod
    def _update_wraplength(label: tk.Label, container: tk.Frame):
        available = container.winfo_width() - 40
        if available > 100:
            label.config(wraplength=available)
