#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""考试统计与趋势分析窗口。"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from core.config import DEFAULT_FONT, BOLD_FONT, get_font, get_theme_colors
from ui.components import center_window
from services.exam_db import query_by_date, query_all, get_daily_avg


def _load_matplotlib():
    """按需加载 matplotlib，未安装时返回 None。"""
    try:
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
    except Exception:
        return None

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    return Figure, FigureCanvasTkAgg


class ExamStatsPanel:
    """考试历史记录和每日平均分趋势面板。"""

    def __init__(self, parent_window):
        self.parent = parent_window
        tc = get_theme_colors()
        self.bg = tc["bg"]
        self.fg = tc["text"]
        self.card_bg = tc["card_bg"]

        self.window = tk.Toplevel(parent_window)
        self.window.title("\u8003\u8bd5\u7edf\u8ba1\u4e0e\u8d8b\u52bf\u5206\u6790")
        self.window.geometry("900x700")
        center_window(self.window, 900, 700)
        self.window.configure(bg=self.bg)

        self._create_control_bar()
        self._create_treeview()
        self._create_chart_area()
        self._load_all()

    def _create_control_bar(self):
        bar = tk.Frame(self.window, bg=self.bg)
        bar.pack(fill="x", padx=20, pady=(15, 5))

        tk.Label(bar, text="\u65e5\u671f (YYYY-MM-DD):", font=DEFAULT_FONT,
                 bg=self.bg, fg=self.fg).pack(side="left", padx=(0, 5))

        self.date_entry = tk.Entry(bar, font=DEFAULT_FONT, width=12)
        self.date_entry.pack(side="left", padx=(0, 10))
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.bind("<Return>", lambda e: self._do_query())

        ttk.Button(bar, text="\u67e5\u8be2", command=self._do_query).pack(side="left", padx=(0, 10))
        ttk.Button(bar, text="\u67e5\u770b\u5168\u90e8", command=self._load_all).pack(side="left")

    def _create_treeview(self):
        tree_frame = tk.LabelFrame(self.window, text="\u8003\u8bd5\u8bb0\u5f55", font=BOLD_FONT,
                                   bg=self.bg, fg=self.fg)
        tree_frame.pack(fill="both", expand=False, padx=20, pady=(5, 5))

        columns = ("exam_date", "score", "correct", "total", "rate")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)

        self.tree.heading("exam_date", text="\u8003\u8bd5\u65f6\u95f4")
        self.tree.heading("score", text="\u5f97\u5206")
        self.tree.heading("correct", text="\u6b63\u786e\u9898\u6570")
        self.tree.heading("total", text="\u603b\u9898\u6570")
        self.tree.heading("rate", text="\u6b63\u786e\u7387")

        self.tree.column("exam_date", width=180, anchor="center")
        self.tree.column("score", width=80, anchor="center")
        self.tree.column("correct", width=100, anchor="center")
        self.tree.column("total", width=80, anchor="center")
        self.tree.column("rate", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

    def _create_chart_area(self):
        self.chart_frame = tk.LabelFrame(self.window, text="\u6bcf\u65e5\u5e73\u5747\u5206\u8d8b\u52bf", font=BOLD_FONT,
                                          bg=self.bg, fg=self.fg)
        self.chart_frame.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        self.chart_inner = tk.Frame(self.chart_frame, bg=self.bg)
        self.chart_inner.pack(fill="both", expand=True, padx=10, pady=10)

    def _do_query(self):
        date_str = self.date_entry.get().strip()
        if not date_str:
            messagebox.showwarning("\u8f93\u5165\u9519\u8bef", "\u8bf7\u8f93\u5165\u65e5\u671f")
            return
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("\u683c\u5f0f\u9519\u8bef", "\u65e5\u671f\u683c\u5f0f\u5e94\u4e3a YYYY-MM-DD")
            return

        records = query_by_date(date_str)
        self._populate_tree(records)
        self._refresh_chart()

    def _load_all(self):
        records = query_all()
        self._populate_tree(records)
        self._refresh_chart()

    def _populate_tree(self, records):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in records:
            total = r["total_questions"]
            correct = r["correct_count"]
            rate = (correct / total * 100) if total > 0 else 0
            self.tree.insert("", "end", values=(
                r["exam_date"],
                f"{r['score']:.1f}",
                f"{correct}/{total}",
                str(total),
                f"{rate:.1f}%"
            ))

    def _refresh_chart(self):
        for w in self.chart_inner.winfo_children():
            w.destroy()

        daily_data = get_daily_avg()
        if not daily_data:
            tk.Label(self.chart_inner, text="\u6682\u65e0\u8003\u8bd5\u6570\u636e",
                     font=get_font(14), bg=self.bg, fg=self.fg).pack(expand=True)
            return

        chart_lib = _load_matplotlib()
        if chart_lib is None:
            tk.Label(
                self.chart_inner,
                text="\u672a\u5b89\u88c5 matplotlib\uff0c\u6682\u65e0\u6cd5\u663e\u793a\u8d8b\u52bf\u56fe",
                font=get_font(12),
                bg=self.bg,
                fg=self.fg,
            ).pack(expand=True)
            return

        Figure, FigureCanvasTkAgg = chart_lib
        tc = get_theme_colors()
        fig = Figure(figsize=(8, 3.5), dpi=100, facecolor=tc["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(tc["card_bg"])

        days = [d["day"] for d in daily_data]
        scores = [d["avg_score"] for d in daily_data]

        x = range(len(days))
        ax.plot(x, scores, marker="o", linewidth=2, color=tc["primary"],
                markersize=6, markerfacecolor=tc["primary"])

        for xi, s in zip(x, scores):
            ax.annotate(f"{s:.0f}", (xi, s), textcoords="offset points",
                        xytext=(0, 12), ha="center", fontsize=8, color=tc["text"])

        ax.set_xticks(list(x))
        ax.set_xticklabels(days, rotation=45, fontsize=8)
        ax.set_ylabel("\u5e73\u5747\u5206", fontsize=10, color=tc["text"])
        ax.set_title("\u6bcf\u65e5\u8003\u8bd5\u5e73\u5747\u5206\u8d8b\u52bf", fontsize=12, fontweight="bold", color=tc["text"])
        ax.tick_params(colors=tc["text"])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(tc["text"])
        ax.spines["left"].set_color(tc["text"])
        ax.set_ylim(0, 105)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, self.chart_inner)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


def show_exam_stats(parent_window):
    """打开考试统计窗口。"""
    ExamStatsPanel(parent_window)
