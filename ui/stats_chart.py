#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计图表面板 — 支持 matplotlib（可选）和 tkinter Canvas 两种渲染方式
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

from core.config import DEFAULT_FONT, BOLD_FONT, COLORS, get_font, get_theme_colors
from ui.components import center_window

# 尝试导入 matplotlib
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class StatsChartPanel:
    """统计图表面板"""

    def __init__(self, parent_window, user_data):
        self.parent = parent_window
        self.user_data = user_data

        self.window = tk.Toplevel(parent_window)
        self.window.title("学习统计图表")
        self.window.geometry("800x600")
        center_window(self.window, 800, 600)

        tc = get_theme_colors()
        self.bg = tc["bg"]
        self.fg = tc["text"]
        self.window.configure(bg=self.bg)

        self._create_content()

    def _create_content(self):
        stats = self.user_data.get_stats()
        daily = self.user_data.get_daily_stats(30)

        # 顶部摘要
        summary = tk.Frame(self.window, bg=self.bg)
        summary.pack(fill="x", padx=20, pady=10)

        total_a = stats.get("total_answered", 0)
        total_c = stats.get("total_correct", 0)
        accuracy = (total_c / total_a * 100) if total_a > 0 else 0

        for text in [f"累计答题: {total_a}", f"累计正确: {total_c}", f"正确率: {accuracy:.1f}%"]:
            tk.Label(summary, text=text, font=get_font(14, "bold"),
                     bg=self.bg, fg=self.fg).pack(side="left", padx=20)

        # 图表区域
        chart_frame = tk.Frame(self.window, bg=self.bg)
        chart_frame.pack(fill="both", expand=True, padx=20, pady=10)

        if HAS_MATPLOTLIB and daily:
            self._draw_matplotlib(chart_frame, daily)
        elif daily:
            self._draw_canvas(chart_frame, daily)
        else:
            tk.Label(chart_frame, text="暂无统计数据\n开始练习后将自动记录",
                     font=get_font(14), bg=self.bg, fg=self.fg).pack(expand=True)

        ttk.Button(self.window, text="关闭", command=self.window.destroy).pack(pady=10)

    def _draw_matplotlib(self, parent, daily: dict):
        """使用 matplotlib 绘制图表"""
        tc = get_theme_colors()

        fig = Figure(figsize=(8, 4), dpi=100, facecolor=tc["bg"])

        # 每日答题量柱状图 + 正确率折线图
        ax1 = fig.add_subplot(111)
        ax1.set_facecolor(tc["card_bg"])

        dates = list(daily.keys())
        answered = [d.get("answered", 0) for d in daily.values()]
        correct = [d.get("correct", 0) for d in daily.values()]
        rates = [(d.get("correct", 0) / d.get("answered", 1) * 100) for d in daily.values()]

        x = range(len(dates))
        bar_width = 0.35
        ax1.bar([i - bar_width / 2 for i in x], answered, bar_width,
                label="答题数", color=tc["primary"], alpha=0.8)
        ax1.bar([i + bar_width / 2 for i in x], correct, bar_width,
                label="正确数", color=tc["success"], alpha=0.8)

        ax1.set_ylabel("题数", color=tc["text"], fontsize=10)
        ax1.set_xticks(list(x))
        ax1.set_xticklabels([d[5:] for d in dates], rotation=45, fontsize=8)
        ax1.tick_params(colors=tc["text"])
        ax1.legend(loc="upper left", fontsize=8)

        # 正确率折线
        ax2 = ax1.twinx()
        ax2.plot(list(x), rates, color=tc["warning"], marker="o", linewidth=2, label="正确率")
        ax2.set_ylabel("正确率", color=tc["text"], fontsize=10)
        ax2.set_ylim(0, 105)
        ax2.tick_params(colors=tc["text"])
        ax2.legend(loc="upper right", fontsize=8)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _draw_canvas(self, parent, daily: dict):
        """纯 tkinter Canvas 绘制简易柱状图"""
        tc = get_theme_colors()

        canvas = tk.Canvas(parent, bg=tc["card_bg"], highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        dates = list(daily.keys())
        answered = [d.get("answered", 0) for d in daily.values()]
        max_val = max(answered) if answered else 1

        def _draw(event=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            margin = 60
            chart_w = w - 2 * margin
            chart_h = h - 2 * margin

            if not dates or chart_w <= 0 or chart_h <= 0:
                return

            bar_w = max(8, chart_w / len(dates) * 0.7)
            gap = chart_w / len(dates)

            # Y 轴
            canvas.create_line(margin, margin, margin, h - margin, fill=tc["text"], width=1)
            canvas.create_line(margin, h - margin, w - margin, h - margin, fill=tc["text"], width=1)

            # 标题
            canvas.create_text(w // 2, 20, text="每日答题统计", font=BOLD_FONT,
                               fill=tc["text"])

            for i, (date, data) in enumerate(daily.items()):
                x = margin + gap * i + gap / 2
                val = data.get("answered", 0)
                cor = data.get("correct", 0)
                bar_h = (val / max_val) * (chart_h - 20) if max_val > 0 else 0
                cor_h = (cor / max_val) * (chart_h - 20) if max_val > 0 else 0

                # 答题数柱
                canvas.create_rectangle(
                    x - bar_w / 2, h - margin - bar_h,
                    x, h - margin,
                    fill=tc["primary"], outline="",
                )
                # 正确数柱
                canvas.create_rectangle(
                    x, h - margin - cor_h,
                    x + bar_w / 2, h - margin,
                    fill=tc["success"], outline="",
                )
                # 日期标签
                canvas.create_text(x, h - margin + 15, text=date[5:],
                                   font=get_font(7), fill=tc["text"])

            # 图例
            lx, ly = w - margin - 100, margin + 10
            canvas.create_rectangle(lx, ly, lx + 12, ly + 12, fill=tc["primary"], outline="")
            canvas.create_text(lx + 18, ly + 6, text="答题数", font=get_font(8),
                               fill=tc["text"], anchor="w")
            canvas.create_rectangle(lx, ly + 20, lx + 12, ly + 32, fill=tc["success"], outline="")
            canvas.create_text(lx + 18, ly + 26, text="正确数", font=get_font(8),
                               fill=tc["text"], anchor="w")

        canvas.bind("<Configure>", _draw)


def show_stats_chart(parent_window, user_data):
    """显示统计图表面板"""
    StatsChartPanel(parent_window, user_data)