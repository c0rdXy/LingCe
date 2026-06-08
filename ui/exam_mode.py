#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
考试模式界面模块 — 重构版
- 业务逻辑委托给 ExamService
- 题目渲染委托给 QuestionWidget
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import time
import random
from typing import Optional, Dict, Any, List

from core.config import DEFAULT_FONT, BOLD_FONT, COLORS, get_font
from core.models import QuestionBank, Question
from services.exam_service import ExamService
from services.user_data_service import UserDataService
from services.exam_db import save_exam_record, init_db
from ui.components import show_message_dialog, center_window
from ui.widgets import QuestionWidget, get_question_type_name


class ExamModeWindow:
    """考试模式窗口类"""

    def __init__(self, root: tk.Tk, question_bank: QuestionBank):
        self.root = root
        self.exam_service = ExamService()
        self.exam_service.set_question_bank(question_bank)

        # 考试状态
        self.exam_questions: List[Question] = []
        self.current_question_index = 0
        self.current_question: Optional[Question] = None
        self.exam_start_time: Optional[float] = None
        self.exam_answers: Dict[int, str] = {}
        self.is_review_mode = False
        self.exam_time_limit = 90

        # 当前题目渲染组件
        self._question_widget: Optional[QuestionWidget] = None

        # UI 组件引用
        self.question_container: Optional[tk.Frame] = None
        self.timer_label: Optional[tk.Label] = None
        self.progress_label: Optional[tk.Label] = None
        self.status_buttons: list = []
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

    def prepare_exam_questions(self) -> bool:
        """准备考试题目（20单选 + 20多选 + 4简答 = 44题）"""
        all_questions = self.exam_service.question_bank.questions
        if not all_questions:
            return False

        single = [q for q in all_questions if q.type == "single"]
        multiple = [q for q in all_questions if q.type == "multiple"]
        short = [q for q in all_questions if q.type in ("short", "essay")]

        self.exam_questions = []

        n_single = min(20, len(single))
        if n_single < 20:
            show_message_dialog("警告", f"单选题不足20道，当前只有{len(single)}道")
        self.exam_questions.extend(random.sample(single, n_single))

        n_multiple = min(20, len(multiple))
        if n_multiple < 20:
            show_message_dialog("警告", f"多选题不足20道，当前只有{len(multiple)}道")
        self.exam_questions.extend(random.sample(multiple, n_multiple))

        n_short = min(4, len(short))
        if n_short < 4:
            show_message_dialog("警告", f"问答题不足4道，当前只有{len(short)}道")
        self.exam_questions.extend(random.sample(short, n_short))

        self.current_question_index = 0
        self.exam_start_time = time.time()
        self.exam_answers = {}
        return True

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def create_exam_interface(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.title("灵测 LingCe - 考试模式")
        self._create_menu_bar()

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        self._create_header(main_frame)

        content = tk.Frame(main_frame)
        content.pack(fill="both", expand=True, padx=10, pady=5)

        right = tk.Frame(content, width=225)
        right.pack(side="right", fill="y", padx=(5, 0))
        right.pack_propagate(False)
        self._create_status_area(right)

        left = tk.Frame(content)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._create_control_buttons(left)
        self._create_question_area(left)

    def _create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        exam_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="考试", menu=exam_menu)
        exam_menu.add_command(label="提交试卷", command=self.submit_exam)
        exam_menu.add_separator()
        exam_menu.add_command(label="退出考试", command=self._confirm_exit)

        nav_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="导航", menu=nav_menu)
        nav_menu.add_command(label="上一题", command=self.prev_question)
        nav_menu.add_command(label="下一题", command=self.next_question)
        nav_menu.add_command(label="跳转到题目", command=self._jump_dialog)

    def _create_header(self, parent):
        header = tk.Frame(parent, bg="#e74c3c", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="考试模式 - 总分100分",
                 font=get_font(16, "bold"), fg="white", bg="#e74c3c"
                 ).pack(side="left", padx=20, pady=15)

        self.progress_label = tk.Label(header, text="", font=get_font(12, "bold"),
                                       fg="white", bg="#e74c3c")
        self.progress_label.pack(side="left", padx=20, pady=15)

        self.timer_label = tk.Label(header, text="用时: 00:00:00",
                                    font=get_font(14, "bold"), fg="white", bg="#e74c3c")
        self.timer_label.pack(side="right", padx=20, pady=15)

    def _create_question_area(self, parent):
        self.question_container = tk.Frame(parent)
        self.question_container.pack(fill="both", expand=True, pady=10)
        self._show_loading()

    def _create_control_buttons(self, parent):
        ctrl = tk.Frame(parent, height=50)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)

        nav = tk.Frame(ctrl)
        nav.pack(side="left", pady=10)
        ttk.Button(nav, text="上一题 (←)", command=self.prev_question).pack(side="left", padx=5)
        ttk.Button(nav, text="下一题 (→)", command=self.next_question).pack(side="left", padx=5)

        exam = tk.Frame(ctrl)
        exam.pack(side="right", pady=10)
        self.submit_exam_btn = tk.Button(exam, text="提交试卷",
                                         font=get_font(12, "bold"),
                                         bg="#e74c3c", fg="white", command=self.submit_exam)
        self.submit_exam_btn.pack(side="left", padx=5)

    def _create_status_area(self, parent):
        status_frame = tk.LabelFrame(parent, text="答题状态", font=BOLD_FONT)
        status_frame.pack(fill="both", expand=True, pady=(0, 10))

        canvas = tk.Canvas(status_frame)
        scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=canvas.yview)
        self.status_container = tk.Frame(canvas)
        self.status_container.bind("<Configure>",
                                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.status_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")

        self._create_status_buttons()
        self._create_stats_area(parent)

    def _create_status_buttons(self):
        for w in self.status_container.winfo_children():
            w.destroy()
        self.status_buttons = []

        cols = 5
        current_row = 0

        # 按题型分组显示答题状态
        sections = []
        # 单选题区
        single_count = sum(1 for q in self.exam_questions if q.type == "single")
        if single_count > 0:
            sections.append(("一、单选题", single_count, "single"))
        # 多选题区
        multiple_count = sum(1 for q in self.exam_questions if q.type == "multiple")
        if multiple_count > 0:
            sections.append(("二、多选题", multiple_count, "multiple"))
        # 判断题区
        judge_count = sum(1 for q in self.exam_questions if q.type in ("judge", "judgement"))
        if judge_count > 0:
            sections.append(("判断题", judge_count, "judge"))
        # 填空/简答题区
        short_count = sum(1 for q in self.exam_questions if q.type in ("fill", "short", "essay"))
        if short_count > 0:
            sections.append(("三、简答题", short_count, "short"))

        question_index = 0
        for section_title, section_count, section_type in sections:
            # 题型标题
            title_label = tk.Label(self.status_container, text=section_title,
                                   font=get_font(9, "bold"), bg="white", anchor="w")
            title_label.grid(row=current_row, column=0, columnspan=cols,
                             sticky="w", padx=2, pady=(6, 2))
            current_row += 1

            # 该题型的按钮
            for j in range(section_count):
                row, col = divmod(j, cols)
                btn = tk.Button(self.status_container, text=str(question_index + 1),
                                width=3, bg="#95a5a6", fg="white", font=get_font(9),
                                command=lambda idx=question_index: self.jump_to_question(idx))
                btn.grid(row=current_row + row, column=col, padx=2, pady=2)
                self.status_buttons.append(btn)
                question_index += 1

            rows_used = (section_count - 1) // cols + 1
            current_row += rows_used

    def _create_stats_area(self, parent):
        stats_frame = tk.LabelFrame(parent, text="考试统计", font=BOLD_FONT)
        stats_frame.pack(fill="x", pady=(0, 10))
        self.stats_container = tk.Frame(stats_frame)
        self.stats_container.pack(fill="x", padx=10, pady=10)
        self.answered_label = tk.Label(self.stats_container, text="已答: 0", font=DEFAULT_FONT)
        self.answered_label.pack(anchor="w")
        self.unanswered_label = tk.Label(self.stats_container, text="未答: 0", font=DEFAULT_FONT)
        self.unanswered_label.pack(anchor="w")

    # ------------------------------------------------------------------ #
    #  题目显示
    # ------------------------------------------------------------------ #

    def _show_loading(self):
        for w in self.question_container.winfo_children():
            w.destroy()
        tk.Label(self.question_container, text="正在加载考试题目...", font=DEFAULT_FONT).pack(expand=True)

    def show_current_question(self):
        if not self.exam_questions or self.current_question_index >= len(self.exam_questions):
            return

        # 保存旧答案
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
        )
        frame = self._question_widget.render()
        frame.pack(fill="both", expand=True)

        # 恢复答案（非回顾模式）
        if not self.is_review_mode and user_ans:
            self._question_widget.set_user_answer(user_ans)

        self._update_progress()
        self._update_answer_status()
        self._update_nav_buttons()

    def _save_current_answer(self):
        if not self.current_question or not self._question_widget:
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
            return ua == ca
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
                        btn.config(bg="#e74c3c", fg="white")
                    elif self._check_correct(q, ua, ca):
                        # 答对 → 绿色
                        btn.config(bg="#27ae60", fg="white")
                    else:
                        # 答错 → 红色
                        btn.config(bg="#e74c3c", fg="white")
                else:
                    # 考试模式：当前题蓝色，已答绿色，未答灰色
                    if i == self.current_question_index:
                        btn.config(bg="#3498db", fg="white")
                    elif q.id in answered_ids:
                        btn.config(bg="#27ae60", fg="white")
                    else:
                        btn.config(bg="#95a5a6", fg="white")

        # 统计
        total = len(self.exam_questions)
        answered = sum(1 for q in self.exam_questions if q.id in answered_ids)
        if self.answered_label:
            self.answered_label.config(text=f"已答: {answered}/{total}")
        if self.unanswered_label:
            self.unanswered_label.config(text=f"未答: {total - answered}/{total}")

    def _update_nav_buttons(self):
        pass  # 简化，按钮始终可用

    def _highlight_review_status(self, wrong_ids: set):
        """回顾模式：答对绿色，答错/未答红色"""
        for i, btn in enumerate(self.status_buttons):
            if i < len(self.exam_questions):
                q = self.exam_questions[i]
                ua = self.exam_answers.get(q.id, "").strip()
                ca = q.answer.strip()

                if not ua:
                    # 未答题 → 红色
                    btn.config(bg="#e74c3c", fg="white")
                elif q.id in wrong_ids:
                    # 答错题 → 红色
                    btn.config(bg="#e74c3c", fg="white")
                else:
                    # 答对题 → 绿色
                    btn.config(bg="#27ae60", fg="white")

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
        instructions = """考试规则：

1. 考试时间：90分钟，总分100分

2. 题目构成：
   • 单选题：20题 × 2分 = 40分
   • 多选题：20题 × 3分 = 60分
   • 简答题：4题，需人工评分

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
        return messagebox.askyesno("考试说明", instructions)

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

    def submit_exam(self):
        if self.current_question:
            self._save_current_answer()

        # 未答检查
        unanswered = [i + 1 for i, q in enumerate(self.exam_questions)
                      if not self.exam_answers.get(q.id, "").strip()]
        if unanswered:
            preview = ", ".join(map(str, unanswered[:10]))
            if len(unanswered) > 10:
                preview += f" 等{len(unanswered)}题"
            if not messagebox.askyesno("提交确认",
                                       f"还有 {len(unanswered)} 题未答：{preview}\n\n确定要提交试卷吗？"):
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
        correct_count = 0
        wrong_questions = []
        single_score = 0
        multiple_score = 0

        for question in self.exam_questions:
            ua = self.exam_answers.get(question.id, "").strip()
            ca = question.answer.strip()

            if question.type == "single":
                if ua and ua.upper() == ca.upper():
                    correct_count += 1
                    single_score += 2
                else:
                    wrong_questions.append(question.id)
            elif question.type == "multiple":
                if ua:
                    if sorted(ua.upper()) == sorted(ca.upper()):
                        correct_count += 1
                        multiple_score += 3
                    else:
                        wrong_questions.append(question.id)
                else:
                    wrong_questions.append(question.id)
            elif question.type in ("judge", "judgement"):
                if ua and ua.upper() == ca.upper():
                    correct_count += 1
                else:
                    wrong_questions.append(question.id)
            # short/essay 不自动评分

        total_score = single_score + multiple_score

        save_exam_record(total_score, len(self.exam_questions), correct_count)
        # 更新累计统计
        total_answered = sum(1 for q in self.exam_questions if q.type in ("single", "multiple", "judge", "judgement"))
        user_data = UserDataService()
        user_data.update_stats(total_answered, correct_count, mode="exam")

        # 记录错题
        if wrong_questions and self.on_wrong_questions:
            self.on_wrong_questions(wrong_questions)

        self._show_result_dialog(total_score, correct_count, wrong_questions,
                                 single_score, multiple_score)

    def _show_result_dialog(self, total_score, correct_count, wrong_questions,
                            single_score, multiple_score):
        elapsed = int(time.time() - self.exam_start_time) if self.exam_start_time else 0
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60

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

        result_text = (
            f"考试完成！\n\n"
            f"总分：{total_score}/100 分\n"
            f"正确题数：{correct_count}/{len(self.exam_questions)} 题\n"
            f"错误题数：{len(wrong_questions)} 题\n"
            f"用时：{h:02d}:{m:02d}:{s:02d}\n\n"
            f"详细得分：\n"
            f"• 单选题：{single_score}/40 分 (20题×2分)\n"
            f"• 多选题：{multiple_score}/60 分 (20题×3分)\n"
            f"• 简答题：需人工评分 (4题)\n\n"
            f"{wrong_text}"
        )

        result_window = tk.Toplevel(self.root)
        result_window.title("考试结果")
        center_window(result_window, 550, 600)
        result_window.transient(self.root)
        result_window.grab_set()

        # 结果文本 - 使用 ScrolledText 固定高度，不挤压按钮
        from tkinter import scrolledtext
        text = scrolledtext.ScrolledText(result_window, wrap=tk.WORD, font=DEFAULT_FONT,
                                         height=20)
        text.pack(fill="both", expand=True, padx=20, pady=(20, 5))
        text.insert("1.0", result_text)
        text.config(state="disabled")

        # 按钮区域 - 固定在底部
        btn_frame = tk.Frame(result_window)
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=(5, 15))

        def on_close():
            result_window.destroy()
            if wrong_questions:
                self.submit_exam_btn.config(text="查看错题",
                                            command=lambda: self._enter_review_mode(wrong_questions))

        if wrong_questions:
            ttk.Button(btn_frame, text="查看错题",
                       command=lambda: [result_window.destroy(),
                                        self._enter_review_mode(wrong_questions)]).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="关闭", command=on_close).pack(side="right", padx=10)

    # ------------------------------------------------------------------ #
    #  回顾模式
    # ------------------------------------------------------------------ #

    def _enter_review_mode(self, wrong_questions: List[int]):
        """进入错题回顾模式"""
        self.is_review_mode = True
        wrong_set = set(wrong_questions)
        self.current_question_index = 0
        self._highlight_review_status(wrong_set)

        # 修改底部按钮区域：返回主页 + 重新考试
        if hasattr(self, "submit_exam_btn") and self.submit_exam_btn:
            self.submit_exam_btn.config(text="重新考试", command=self._restart_exam)

        # 在提交按钮左边添加"返回主页"按钮
        if not hasattr(self, "return_main_btn"):
            self.return_main_btn = tk.Button(
                self.submit_exam_btn.master,
                text="返回主页",
                font=get_font(12, "bold"),
                bg="#6c757d", fg="white",
                command=self._return_to_main_from_review,
            )
        self.return_main_btn.pack(side="left", padx=5, before=self.submit_exam_btn)

        self.show_current_question()

    def _return_to_main_from_review(self):
        """从回顾模式返回主页"""
        self.is_review_mode = False
        self._stop_timer()
        if self.on_return_to_main:
            self.on_return_to_main()

    def _restart_exam(self):
        """重新开始考试"""
        self.is_review_mode = False
        self.exam_answers = {}
        self.current_question_index = 0
        self.exam_start_time = time.time()

        # 恢复提交按钮，移除返回主页按钮
        if hasattr(self, "submit_exam_btn") and self.submit_exam_btn:
            self.submit_exam_btn.config(text="提交试卷", command=self.submit_exam)
        if hasattr(self, "return_main_btn") and self.return_main_btn:
            self.return_main_btn.destroy()

        # 重新准备题目
        self.prepare_exam_questions()
        self._create_status_buttons()
        self.start_timer()
        self.show_current_question()

    # ------------------------------------------------------------------ #
    #  回调设置
    # ------------------------------------------------------------------ #

    def set_return_callback(self, callback):
        self.on_return_to_main = callback

    def set_wrong_questions_callback(self, callback):
        self.on_wrong_questions = callback
