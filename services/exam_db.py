#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""????????? - SQLite"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_DIR = Path("data")
DB_FILE = DB_DIR / "exam_history.db"


def _get_conn() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """?????????????????"""
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
    """????????"""
    conn = _get_conn()
    exam_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO exam_records (exam_date, score, total_questions, correct_count) VALUES (?, ?, ?, ?)",
        (exam_date, score, total_questions, correct_count)
    )
    conn.commit()
    conn.close()


def query_by_date(date_str: str) -> List[Dict[str, Any]]:
    """???????????"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM exam_records WHERE exam_date LIKE ? ORDER BY exam_date DESC",
        (date_str + "%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_all() -> List[Dict[str, Any]]:
    """????????"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM exam_records ORDER BY exam_date DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_daily_avg() -> List[Dict[str, Any]]:
    """???????"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DATE(exam_date) as day, AVG(score) as avg_score, COUNT(*) as count FROM exam_records GROUP BY day ORDER BY day"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
