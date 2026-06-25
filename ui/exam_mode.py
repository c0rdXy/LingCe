#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""考试模式界面模块。"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import time
import random
from typing import Optional, Dict, Any, List

from core.config import DEFAULT_FONT, BOLD_FONT, get_font, get_theme_colors
from core.models import QuestionBank, Question
from core.utils import normalize_judge_answer
from services.exam_service import ExamService
from services.user_data_service import UserDataService
from services.settings_service import SettingsService
from services.exam_db import save_exam_record
from ui.ai_review_window import show_ai_review_window
from ui.components import show_message_dialog, center_window
from ui.widgets import QuestionWidget


class ExamModeWindow:
    """考试模式窗口类"""

    def __init__(self, root: tk.Tk, question_bank: QuestionBank):
        self.root = root
        self.exam_service = ExamService()
        self.exam_service.set_question_bank(question_bank)
        self.settings_service = SettingsService()
        self.exam_settings = self.settings_service.get_exam_settings()
        self.exam_rules = self.settings_service.get_exam_rules()

        # 考试状态
        self.exam_questions: List[Question] = []
        self.exam_question_rules: Dict[int, Dict[str, Any]] = {}
        self.exam_sections: List[Dict[str, Any]] = []
        self.current_question_index = 0
        self.current_question: Optional[Question] = None
        self.exam_start_time: Optional[float] = None
        self.exam_answers: Dict[int, str] = {}
        self.is_review_mode = False
        self.exam_time_limit = int(self.exam_settings.get("time_limit", 90))
        self._time_up_notified = False
        self.ai_histories: Dict[int, list] = {}

        # 当前题目渲染组件
        self._question_widget: Optional[QuestionWidget] = None

        # UI 组件引用
        self.question_container: Optional[tk.Frame] = None
        self.exam_button_frame: Optional[tk.Frame] = None
        self.timer_label: Optional[tk.Label] = None
        self.progress_label: Optional[tk.Label] = None
        self.status_buttons: list = []
        self.current_status_label: Optional[tk.Label] = None
        self.status_canvas: Optional[tk.Canvas] = None
        self.status_canvas_window = None
        self.timer_job = None

        # 统计
        self.stats_container: Optional[tk.Frame] = None
        self.answered_label: Optional[tk.Label] = None
        self.unanswered_label: Optional[tk.Label] = None

        # 回调
        self.on_return_to_main = None
        self.on_wrong_questions = None

    # ------------------------------------------------------------------ #
    #  考试准备
    # ------------------------------------------------------------------ #

    def prepare_exam_questions(self, show_warnings: bool = True) -> bool:
        """根据配置规则准备考试题目。"""
        all_questions = self.exam_service.question_bank.questions
        if not all_questions or not self.exam_rules:
            return False

        self.exam_questions = []
        self.exam_question_rules = {}
        self.exam_sections = []
        used_ids = set()
        shortage_lines = []

        for rule in self.exam_rules:
            candidates = [
                q for q in all_questions
                if q.id not in used_ids
                and self.settings_service.question_matches_rule(q.type, rule["type"])
            ]
            target_count = int(rule.get("count", 0))
            selected_count = min(target_count, len(candidates))
            if selected_count < target_count:
                shortage_lines.append(
                    f"{rule.get('name', rule['type'])}: 需要 {target_count} 道，当前 {len(candidates)} 道"
                )
            selected = random.sample(candidates, selected_count) if selected_count else []
            start_index = len(self.exam_questions)
            self.exam_questions.extend(selected)
            for question in selected:
                used_ids.add(question.id)
                self.exam_question_rules[question.id] = rule
            if selected:
                self.exam_sections.append({
                    "rule": rule,
                    "start": start_index,
                    "count": len(selected),
                })

        if shortage_lines and show_warnings:
            show_message_dialog(
                "题库数量不足",
                "以下题型题目不足，将按当前可用题目开始考试：\n\n" + "\n".join(shortage_lines),
                "warning",
            )
        if not self.exam_questions:
            return False

        self.current_question_index = 0
        self.exam_start_time = time.time()
        self.exam_answers = {}
        return True

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def create_exam_interface(self):
        tc = get_theme_colors()
        self.root.minsize(1100, 750)
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.title(self.settings_service.get_window_title("考试模式"))
        self.root.configure(bg=tc["bg"])
        self._create_menu_bar()

        main_frame = tk.Frame(self.root, bg=tc["bg"])
        main_frame.pack(fill="both", expand=True)

        self._create_header(main_frame)

        content = tk.Frame(main_frame, bg=tc["bg"])
        content.pack(fill="both", expand=True, padx=10, pady=5)

        right = tk.Frame(content, width=255, bg=tc["bg"])
        right.pack(side="right", fill="y", padx=(5, 0))
        right.pack_propagate(False)
        self._create_status_area(right)

        left = tk.Frame(content, bg=tc["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._create_control_buttons(left)
        self._create_question_area(left)

    def _create_menu_bar(self):
        tc = get_theme_colors()
        menu_opts = {
            "bg": tc["bg_secondary"],
            "fg": tc["text"],
            "activebackground": tc["primary"],
            "activeforeground": "#ffffff",
        }
        menubar = tk.Menu(self.root, **menu_opts)
        self.root.config(menu=menubar)

        exam_menu = tk.Menu(menubar, tearoff=0, **menu_opts)
        menubar.add_cascade(label="考试", menu=exam_menu)
        exam_menu.add_command(label="提交试卷", command=self.submit_exam)
        exam_menu.add_separator()
        exam_menu.add_command(label="退出考试", command=self._confirm_exit)

        nav_menu = tk.Menu(menubar, tearoff=0, **menu_opts)
        menubar.add_cascade(label="导航", menu=nav_menu)
        nav_menu.add_command(label="上一题", command=self.prev_question)
        nav_menu.add_command(label="下一题", command=self.next_question)
        nav_menu.add_command(label="跳转到题目", command=self._jump_dialog)

    def _create_header(self, parent):
        header = tk.Frame(parent, bg="#e74c3c", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        total_score = self._get_total_possible_score()
        tk.Label(header, text=f"考试模式 - 总分{total_score:g}分",
                 font=get_font(16, "bold"), fg="white", bg="#e74c3c"
                 ).pack(side="left", padx=20, pady=15)

        self.progress_label = tk.Label(header, text="", font=get_font(12, "bold"),
                                       fg="white", bg="#e74c3c")
        self.progress_label.pack(side="left", padx=20, pady=15)

        self.timer_label = tk.Label(header, text="用时: 00:00:00",
                                    font=get_font(14, "bold"), fg="white", bg="#e74c3c")
        self.timer_label.pack(side="right", padx=20, pady=15)

    def _create_question_area(self, parent):
        self.question_container = tk.Frame(parent, bg=get_theme_colors()["bg"])
        self.question_container.pack(fill="both", expand=True, pady=10)
        self._show_loading()

    def _create_control_buttons(self, parent):
        tc = get_theme_colors()
        ctrl = tk.Frame(parent, height=50, bg=tc["bg"])
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)

        nav = tk.Frame(ctrl, bg=tc["bg"])
        nav.pack(side="left", pady=10)
        style = ttk.Style(self.root)
        style.configure("ExamNav.TButton", anchor="center", padding=(10, 4))
        ttk.Button(nav, text="上一题", width=10, style="ExamNav.TButton",
                   command=self.prev_question).pack(side="left", padx=5)
        ttk.Button(nav, text="下一题", width=10, style="ExamNav.TButton",
                   command=self.next_question).pack(side="left", padx=5)

        exam = tk.Frame(ctrl, bg=tc["bg"])
        exam.pack(side="right", pady=10)
        self.exam_button_frame = exam
        self.submit_exam_btn = tk.Button(exam, text="提交试卷",
                                         font=get_font(12, "bold"),
                                         bg="#e74c3c", fg="white", command=self.submit_exam)
        self.submit_exam_btn.pack(side="left", padx=5)

    def _create_status_area(self, parent):
        tc = get_theme_colors()
        status_frame = tk.LabelFrame(parent, text="答题状态", font=BOLD_FONT,
                                     bg=tc["bg"], fg=tc["text"])
        status_frame.pack(fill="both", expand=True, pady=(0, 10))

        canvas = tk.Canvas(status_frame, bg=tc["bg"], highlightthickness=0)
        self.status_canvas = canvas
        scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=canvas.yview)
        self.status_container = tk.Frame(canvas, bg=tc["bg"])
        self.status_container.bind("<Configure>",
                                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.status_canvas_window = canvas.create_window((0, 0), window=self.status_container, anchor="nw")
        canvas.bind("<Configure>", self._resize_status_canvas_window)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")

        self._create_status_buttons()
        self._create_stats_area(parent)

    def _resize_status_canvas_window(self, event):
        """让答题状态网格宽度跟随右侧区域。"""
        if self.status_canvas and self.status_canvas_window:
            self.status_canvas.itemconfigure(self.status_canvas_window, width=event.width)

    def _create_status_buttons(self):
        for w in self.status_container.winfo_children():
            w.destroy()
        self.status_buttons = []

        cols = 5
        tc = get_theme_colors()
        self.current_status_label = tk.Label(
            self.status_container, text="", font=get_font(9, "bold"),
            bg=tc["bg"], fg=tc["primary"], anchor="w",
        )
        self.current_status_label.grid(row=0, column=0, columnspan=cols,
                                       sticky="we", padx=4, pady=(2, 6))
        current_row = 1
        for col in range(cols):
            self.status_container.grid_columnconfigure(col, weight=1, uniform="status_cols", minsize=42)

        for section_no, section in enumerate(self.exam_sections, start=1):
            rule = section["rule"]
            section_title = f"{section_no}、{rule.get('name', rule['type'])}"
            section_count = section["count"]
            question_index = section["start"]
            # 题型标题
            tc = get_theme_colors()
            title_label = tk.Label(self.status_container, text=section_title,
                                   font=get_font(9, "bold"), bg=tc["bg"], fg=tc["text"], anchor="w")
            title_label.grid(row=current_row, column=0, columnspan=cols,
                             sticky="w", padx=2, pady=(6, 2))
            current_row += 1

            # 该题型的按钮
            for j in range(section_count):
                row, col = divmod(j, cols)
                absolute_index = section["start"] + j
                cell = tk.Frame(self.status_container, width=38, height=38, bg=get_theme_colors()["bg"])
                cell.grid(row=current_row + row, column=col, padx=3, pady=4, sticky="n")
                cell.grid_propagate(False)
                btn = tk.Button(cell, text=str(absolute_index + 1),
                                bd=2, relief="raised",
                                bg="#95a5a6", fg="white", font=get_font(9),
                                command=lambda idx=absolute_index: self.jump_to_question(idx))
                btn.place(x=0, y=0, width=38, height=38)
                self.status_buttons.append(btn)
                question_index += 1

            rows_used = (section_count - 1) // cols + 1
            current_row += rows_used

    def _create_stats_area(self, parent):
        tc = get_theme_colors()
        stats_frame = tk.LabelFrame(parent, text="考试统计", font=BOLD_FONT,
                                    bg=tc["bg"], fg=tc["text"])
        stats_frame.pack(fill="x", pady=(0, 10))
        self.stats_container = tk.Frame(stats_frame, bg=tc["bg"])
        self.stats_container.pack(fill="x", padx=10, pady=10)
        self.answered_label = tk.Label(self.stats_container, text="已答: 0", font=DEFAULT_FONT,
                                       bg=tc["bg"], fg=tc["text"])
        self.answered_label.pack(anchor="w")
        self.unanswered_label = tk.Label(self.stats_container, text="未答: 0", font=DEFAULT_FONT,
                                         bg=tc["bg"], fg=tc["text"])
        self.unanswered_label.pack(anchor="w")

    # ------------------------------------------------------------------ #
    #  题目显示
    # ------------------------------------------------------------------ #

    def _show_loading(self):
        for w in self.question_container.winfo_children():
            w.destroy()
        tc = get_theme_colors()
        tk.Label(self.question_container, text="正在加载考试题目...", font=DEFAULT_FONT,
                 bg=tc["bg"], fg=tc["text"]).pack(expand=True)

    def show_current_question(self):
        if not self.exam_questions or self.current_question_index >= len(self.exam_questions):
            return

        # 保存当前答案
        if self.current_question:
            self._save_current_answer()

        self.current_question = self.exam_questions[self.current_question_index]

        for w in self.question_container.winfo_children():
            w.destroy()

        user_ans = self.exam_answers.get(self.current_question.id, "")
        self._question_widget = QuestionWidget(
            parent=self.question_container,
            question=self.current_question,
            index=self.current_question_index + 1,
            show_id=True,
            review_mode=self.is_review_mode,
            user_answer=user_ans,
            correct_answer=self.current_question.answer,
            ai_review_callback=self._open_ai_review if self._should_show_ai_review() else None,
        )
        frame = self._question_widget.render()
        frame.pack(fill="both", expand=True)

        # 恢复答案（非回顾模式）
        if not self.is_review_mode and user_ans:
            self._question_widget.set_user_answer(user_ans)

        self._update_progress()
        self._update_answer_status()

    def _should_show_ai_review(self) -> bool:
        """回顾模式下显示 AI 复核入口。"""
        return self.is_review_mode

    def _open_ai_review(self, question: Question, user_answer: str):
        """打开当前题 AI 复核窗口。"""
        history = self.ai_histories.setdefault(question.id, [])
        show_ai_review_window(self.root, question, user_answer, history)

    def _save_current_answer(self):
        if self.is_review_mode or not self.current_question or not self._question_widget:
            return
        try:
            ans = self._question_widget.get_user_answer()
            self.exam_answers[self.current_question.id] = ans
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ #
    #  导航
    # ------------------------------------------------------------------ #

    def prev_question(self):
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.show_current_question()

    def next_question(self):
        if self.current_question_index < len(self.exam_questions) - 1:
            self.current_question_index += 1
            self.show_current_question()

    def jump_to_question(self, index: int):
        if 0 <= index < len(self.exam_questions):
            self.current_question_index = index
            self.show_current_question()

    def _jump_dialog(self):
        result = simpledialog.askinteger("跳转", f"请输入题号 (1-{len(self.exam_questions)}):",
                                         parent=self.root)
        if result is not None and 1 <= result <= len(self.exam_questions):
            self.jump_to_question(result - 1)

    # ------------------------------------------------------------------ #
    #  状态更新
    # ------------------------------------------------------------------ #

    def _update_progress(self):
        if self.progress_label:
            self.progress_label.config(text=f"进度: {self.current_question_index + 1}/{len(self.exam_questions)}")
        if self.current_status_label:
            self.current_status_label.config(text=f"当前题：{self.current_question_index + 1}")

    @staticmethod
    def _check_correct(question, user_answer: str, correct_answer: str) -> bool:
        """检查单题是否答对"""
        if not user_answer:
            return False
        ua = user_answer.upper().strip()
        ca = correct_answer.upper().strip()
        if question.type == "single":
            return ua == ca
        elif question.type == "multiple":
            return sorted(ua) == sorted(ca)
        elif question.type in ("judge", "judgement"):
            return normalize_judge_answer(ua) == normalize_judge_answer(ca)
        else:
            return ua == ca

    def _update_answer_status(self):
        answered_ids = {qid for qid, ans in self.exam_answers.items() if ans.strip()}
        for i, btn in enumerate(self.status_buttons):
            if i < len(self.exam_questions):
                q = self.exam_questions[i]
                ua = self.exam_answers.get(q.id, "").strip()
                ca = q.answer.strip()

                if self.is_review_mode:
                    # 回顾模式：判断对错
                    if not ua:
                        # 未答题 → 红色
                        self._style_status_button(btn, "#e74c3c", current=i == self.current_question_index)
                    elif self._check_correct(q, ua, ca):
                        # 答对 → 绿色
                        self._style_status_button(btn, "#27ae60", current=i == self.current_question_index)
                    else:
                        # 答错 → 红色
                        self._style_status_button(btn, "#e74c3c", current=i == self.current_question_index)
                else:
                    # 考试模式：当前题蓝色，已答绿色，未答灰色
                    if i == self.current_question_index:
                        self._style_status_button(btn, "#3498db", current=True)
                    elif q.id in answered_ids:
                        self._style_status_button(btn, "#27ae60")
                    else:
                        self._style_status_button(btn, "#95a5a6")

        # 统计
        total = len(self.exam_questions)
        answered = sum(1 for q in self.exam_questions if q.id in answered_ids)
        if self.answered_label:
            self.answered_label.config(text=f"已答: {answered}/{total}")
        if self.unanswered_label:
            self.unanswered_label.config(text=f"未答: {total - answered}/{total}")

    def _style_status_button(self, btn: tk.Button, bg: str, current: bool = False):
        """设置答题状态按钮样式，当前题不改变尺寸以避免挤压网格。"""
        if current:
            btn.config(
                bg=bg, fg="white",
                font=get_font(9, "bold"), relief="solid", bd=3,
                activebackground="#f39c12", activeforeground="#111111",
                highlightthickness=2, highlightbackground="#f1c40f",
                highlightcolor="#f1c40f",
            )
        else:
            btn.config(
                bg=bg, fg="white",
                font=get_font(9), relief="raised", bd=2,
                activebackground=bg, activeforeground="white",
                highlightthickness=0,
            )

    def _highlight_review_status(self, wrong_ids: set):
        """回顾模式：答对绿色，答错/未答红色"""
        for i, btn in enumerate(self.status_buttons):
            if i < len(self.exam_questions):
                q = self.exam_questions[i]
                ua = self.exam_answers.get(q.id, "").strip()
                ca = q.answer.strip()

                if not ua:
                    # 未答题 → 红色
                    self._style_status_button(btn, "#e74c3c", current=i == self.current_question_index)
                elif q.id in wrong_ids:
                    # 答错题 → 红色
                    self._style_status_button(btn, "#e74c3c", current=i == self.current_question_index)
                else:
                    # 答对题 → 绿色
                    self._style_status_button(btn, "#27ae60", current=i == self.current_question_index)

    # ------------------------------------------------------------------ #
    #  计时器
    # ------------------------------------------------------------------ #

    def start_timer(self):
        if not self.exam_start_time:
            self.exam_start_time = time.time()
        self._update_timer()

    def _update_timer(self):
        if self.exam_start_time and self.timer_label:
            elapsed = int(time.time() - self.exam_start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self.timer_label.config(text=f"用时: {h:02d}:{m:02d}:{s:02d}")

            if elapsed >= self.exam_time_limit * 60:
                self.timer_label.config(fg="yellow")
                if self.exam_settings.get("auto_submit_when_time_up", False):
                    self.submit_exam(force=True)
                    return
                if not self._time_up_notified:
                    self._time_up_notified = True
                    show_message_dialog("提醒", "考试时间已到，请尽快提交试卷！")

            self.timer_job = self.root.after(1000, self._update_timer)

    def _stop_timer(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

    # ------------------------------------------------------------------ #
    #  快捷键
    # ------------------------------------------------------------------ #

    def bind_keyboard_shortcuts(self):
        self.root.bind("<Left>", lambda e: self.prev_question())
        self.root.bind("<Right>", lambda e: self.next_question())
        self.root.bind("<Control-Return>", lambda e: self.submit_exam())
        self.root.bind("<Escape>", lambda e: self._confirm_exit())

    # ------------------------------------------------------------------ #
    #  考试流程
    # ------------------------------------------------------------------ #

    def show_exam_instructions(self) -> bool:
        instructions = self._build_exam_instructions()
        return messagebox.askyesno("考试说明", instructions)

    def _build_exam_instructions(self) -> str:
        """生成考试说明。"""
        total_score = self._get_configured_total_score()
        rule_lines = []
        for rule in self.exam_rules:
            count = int(rule.get("count", 0))
            score = float(rule.get("score", 0))
            name = rule.get("name", rule["type"])
            if rule.get("auto_score", True) and score > 0:
                rule_lines.append(f"   • {name}：{count}题 × {score:g}分 = {count * score:g}分")
            else:
                rule_lines.append(f"   • {name}：{count}题，需人工评分")
        rules_text = "\n".join(rule_lines) or "   • 暂未配置考试题型"

        return f"""考试规则：

1. 考试时间：{self.exam_time_limit}分钟，总分{total_score:g}分

2. 题目构成：
{rules_text}

3. 操作说明：
   • 左右箭头键：切换题目
   • 点击右侧按钮：快速跳转
   • 绿色：已答题  蓝色：当前题
   • 灰色：未答题  红色：错题(回顾模式)

4. 快捷键：
   • Ctrl+Enter：提交试卷
   • Esc：退出考试
   • ←→：上下题导航

是否开始考试？"""

    def start_exam(self) -> bool:
        if self.prepare_exam_questions():
            self.create_exam_interface()
            self.bind_keyboard_shortcuts()
            self.start_timer()
            self.show_current_question()
            return True
        else:
            show_message_dialog("错误", "无法准备考试题目")
            return False

    def _confirm_exit(self):
        if messagebox.askyesno("确认退出", "确定要退出考试吗？未保存的答案将丢失。"):
            self._stop_timer()
            if self.on_return_to_main:
                self.on_return_to_main()

    def submit_exam(self, force: bool = False):
        if self.current_question:
            self._save_current_answer()

        if force:
            self._stop_timer()
            self._calculate_and_show_result()
            return

        # 未答检查
        unanswered = [i + 1 for i, q in enumerate(self.exam_questions)
                      if not self.exam_answers.get(q.id, "").strip()]
        if unanswered and self.exam_settings.get("allow_submit_with_unanswered", True):
            preview = ", ".join(map(str, unanswered[:10]))
            if len(unanswered) > 10:
                preview += f" 等{len(unanswered)}题"
            if not messagebox.askyesno("提交确认",
                                       f"还有 {len(unanswered)} 题未答：{preview}\n\n确定要提交试卷吗？"):
                return
        elif unanswered:
            show_message_dialog("提示", "当前设置不允许未答题时提交试卷", "warning")
            return
        else:
            if not messagebox.askyesno("提交确认", "确定要提交试卷吗？"):
                return

        self._stop_timer()
        self._calculate_and_show_result()

    # ------------------------------------------------------------------ #
    #  评分 & 结果
    # ------------------------------------------------------------------ #

    def _calculate_and_show_result(self):
        result = self._calculate_exam_result()
        total_score = result["total_score"]
        correct_count = result["correct_count"]
        wrong_questions = result["wrong_questions"]

        save_exam_record(total_score, len(self.exam_questions), correct_count)
        total_answered = result["auto_scored_count"]
        user_data = UserDataService()
        user_data.update_stats(total_answered, correct_count, mode="exam")

        if wrong_questions and self.on_wrong_questions:
            self.on_wrong_questions(wrong_questions)

        self._show_result_dialog(result)

    def _calculate_exam_result(self) -> Dict[str, Any]:
        """计算考试结果。"""
        correct_count = 0
        wrong_questions = []
        total_score = 0.0
        auto_scored_count = 0
        detail_by_type: Dict[str, Dict[str, Any]] = {}

        for section in self.exam_sections:
            rule = section["rule"]
            detail_by_type[rule["type"]] = {
                "name": rule.get("name", rule["type"]),
                "count": section["count"],
                "score_per_question": float(rule.get("score", 0)),
                "auto_score": bool(rule.get("auto_score", True)),
                "correct": 0,
                "earned": 0.0,
                "possible": section["count"] * float(rule.get("score", 0)),
            }

        for question in self.exam_questions:
            ua = self.exam_answers.get(question.id, "").strip()
            ca = question.answer.strip()
            rule = self.exam_question_rules.get(question.id, {})
            detail = detail_by_type.get(rule.get("type"))
            is_correct = self._check_correct(question, ua, ca)

            if detail and detail["auto_score"]:
                auto_scored_count += 1
                if is_correct:
                    correct_count += 1
                    detail["correct"] += 1
                    detail["earned"] += detail["score_per_question"]
                    total_score += detail["score_per_question"]
                else:
                    wrong_questions.append(question.id)

        return {
            "total_score": total_score,
            "possible_score": self._get_total_possible_score(),
            "pass_score": float(self.exam_settings.get("pass_score", 60)),
            "correct_count": correct_count,
            "auto_scored_count": auto_scored_count,
            "wrong_questions": wrong_questions,
            "details": list(detail_by_type.values()),
        }

    def _show_result_dialog(self, result: Dict[str, Any]):
        elapsed = int(time.time() - self.exam_start_time) if self.exam_start_time else 0
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
        wrong_questions = result["wrong_questions"]

        wrong_text = ""
        if wrong_questions:
            nums = []
            for qid in wrong_questions:
                for i, q in enumerate(self.exam_questions):
                    if q.id == qid:
                        nums.append(str(i + 1))
                        break
            wrong_text = f'错题序号：{", ".join(nums)}'
        else:
            wrong_text = "恭喜！全部答对！"

        detail_lines = []
        for detail in result["details"]:
            if detail["auto_score"]:
                detail_lines.append(
                    f"• {detail['name']}：{detail['earned']:g}/{detail['possible']:g} 分 "
                    f"({detail['correct']}/{detail['count']}题，{detail['score_per_question']:g}分/题)"
                )
            else:
                detail_lines.append(f"• {detail['name']}：需人工评分 ({detail['count']}题)")
        details_text = "\n".join(detail_lines)

        result_text = (
            f"考试完成！\n\n"
            f"总分：{result['total_score']:g}/{result['possible_score']:g} 分\n"
            f"及格分：{result['pass_score']:g} 分，"
            f"{'已通过' if result['total_score'] >= result['pass_score'] else '未通过'}\n"
            f"自动评分正确题数：{result['correct_count']}/{result['auto_scored_count']} 题\n"
            f"错误题数：{len(wrong_questions)} 题\n"
            f"用时：{h:02d}:{m:02d}:{s:02d}\n\n"
            f"详细得分：\n"
            f"{details_text}\n\n"
            f"{wrong_text}"
        )

        result_window = tk.Toplevel(self.root)
        result_window.title("考试结果")
        tc = get_theme_colors()
        result_window.configure(bg=tc["bg"])
        center_window(result_window, 550, 600)
        result_window.transient(self.root)
        result_window.grab_set()

        # 结果文本 - 使用 ScrolledText 固定高度，不挤压按钮
        from tkinter import scrolledtext
        text = scrolledtext.ScrolledText(result_window, wrap=tk.WORD, font=DEFAULT_FONT,
                                         height=20, bg=tc["bg_secondary"], fg=tc["text"],
                                         insertbackground=tc["text"])
        text.pack(fill="both", expand=True, padx=20, pady=(20, 5))
        text.insert("1.0", result_text)
        text.config(state="disabled")

        # 按钮区域 - 固定在底部
        btn_frame = tk.Frame(result_window, bg=tc["bg"])
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=(5, 15))

        def on_close():
            result_window.destroy()
            if wrong_questions:
                self.submit_exam_btn.config(text="查看错题",
                                            command=lambda: self._enter_review_mode(wrong_questions))

        if wrong_questions:
            ttk.Button(btn_frame, text="查看错题",
                       command=lambda: self._open_review_from_result(result_window, wrong_questions)
                       ).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="关闭", command=on_close).pack(side="right", padx=10)

    # ------------------------------------------------------------------ #
    #  回顾模式
    # ------------------------------------------------------------------ #

    def _open_review_from_result(self, result_window: tk.Toplevel, wrong_questions: List[int]):
        """关闭结果窗口后进入回顾模式。"""
        result_window.destroy()
        self.root.after_idle(lambda: self._enter_review_mode(wrong_questions))

    def _enter_review_mode(self, wrong_questions: List[int]):
        """进入错题回顾模式"""
        tc = get_theme_colors()
        self.is_review_mode = True
        wrong_set = set(wrong_questions)
        self.current_question_index = 0
        self._highlight_review_status(wrong_set)

        self._show_review_buttons()

        self.show_current_question()

    def _show_review_buttons(self):
        """重建回顾模式底部按钮，避免引用已销毁控件。"""
        tc = get_theme_colors()
        if not self.exam_button_frame or not self.exam_button_frame.winfo_exists():
            return
        for widget in self.exam_button_frame.winfo_children():
            widget.destroy()
        self.return_main_btn = tk.Button(
            self.exam_button_frame,
            text="返回主页",
            font=get_font(12, "bold"),
            bg="#6c757d", fg="white",
            activebackground=tc["bg_secondary"], activeforeground=tc["text"],
            command=self._return_to_main_from_review,
        )
        self.return_main_btn.pack(side="left", padx=5)
        self.submit_exam_btn = tk.Button(
            self.exam_button_frame,
            text="重新考试",
            font=get_font(12, "bold"),
            bg="#e74c3c", fg="white",
            command=self._confirm_restart_exam,
        )
        self.submit_exam_btn.pack(side="left", padx=5)

    def _get_configured_total_score(self) -> float:
        """按配置规则计算理论总分。"""
        return sum(
            int(rule.get("count", 0)) * float(rule.get("score", 0))
            for rule in self.exam_rules
            if rule.get("auto_score", True)
        )

    def _get_total_possible_score(self) -> float:
        """按实际抽到的题目计算本次考试总分。"""
        if not self.exam_sections:
            return self._get_configured_total_score()
        return sum(
            section["count"] * float(section["rule"].get("score", 0))
            for section in self.exam_sections
            if section["rule"].get("auto_score", True)
        )

    def _return_to_main_from_review(self):
        """从回顾模式返回主页"""
        self.is_review_mode = False
        self._stop_timer()
        if self.on_return_to_main:
            self.on_return_to_main()

    def _confirm_restart_exam(self):
        """确认后重新开始考试。"""
        if messagebox.askyesno("确认重新考试", "确定要重新考试吗？\n\n将重新抽题并清空本次答题记录。"):
            self._restart_exam()

    def _restart_exam(self):
        """重新开始考试"""
        self.is_review_mode = False
        self.exam_answers = {}
        self.current_question_index = 0
        self.exam_start_time = time.time()
        self._time_up_notified = False

        self._show_exam_buttons()

        # 重新准备题目
        self.prepare_exam_questions()
        self._create_status_buttons()
        self.start_timer()
        self.show_current_question()

    def _show_exam_buttons(self):
        """重建考试模式底部按钮。"""
        if not self.exam_button_frame or not self.exam_button_frame.winfo_exists():
            return
        for widget in self.exam_button_frame.winfo_children():
            widget.destroy()
        self.submit_exam_btn = tk.Button(
            self.exam_button_frame,
            text="提交试卷",
            font=get_font(12, "bold"),
            bg="#e74c3c", fg="white",
            command=self.submit_exam,
        )
        self.submit_exam_btn.pack(side="left", padx=5)

    # ------------------------------------------------------------------ #
    #  回调设置
    # ------------------------------------------------------------------ #

    def set_return_callback(self, callback):
        self.on_return_to_main = callback

    def set_wrong_questions_callback(self, callback):
        self.on_wrong_questions = callback
