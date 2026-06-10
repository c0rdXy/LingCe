#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""考试记录数据库服务 - SQLite 存储。"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

DB_DIR = Path("data")
DB_FILE = DB_DIR / "exam_history.db"


def _get_conn() -> sqlite3.Connection:
    """创建考试记录数据库连接。"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化考试记录表，表已存在时保持原数据。"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS exam_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_date TEXT NOT NULL,
            score REAL NOT NULL,
            total_questions INTEGER NOT NULL,
            correct_count INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_exam_record(score: float, total_questions: int, correct_count: int):
    """保存一次考试成绩记录。"""
    conn = _get_conn()
    exam_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO exam_records (exam_date, score, total_questions, correct_count) VALUES (?, ?, ?, ?)",
        (exam_date, score, total_questions, correct_count)
    )
    conn.commit()
    conn.close()


def query_by_date(date_str: str) -> List[Dict[str, Any]]:
    """按日期前缀查询考试记录。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM exam_records WHERE exam_date LIKE ? ORDER BY exam_date DESC",
        (date_str + "%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_all() -> List[Dict[str, Any]]:
    """查询全部考试记录，按考试时间倒序返回。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM exam_records ORDER BY exam_date DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_daily_avg() -> List[Dict[str, Any]]:
    """按日期统计每日平均分和考试次数。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DATE(exam_date) as day, AVG(score) as avg_score, COUNT(*) as count FROM exam_records GROUP BY day ORDER BY day"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_exam_records():
    """清空全部考试统计记录。"""
    conn = _get_conn()
    conn.execute("DELETE FROM exam_records")
    conn.commit()
    conn.close()
