#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""应用图标设置。"""

import sys
import tkinter as tk
from pathlib import Path


ICON_PNG_PATH = Path("assets") / "lingce-logo-256.png"
ICON_ICO_PATH = Path("assets") / "lingce-logo.ico"


def resource_path(relative_path: Path) -> Path:
    """返回开发环境或 PyInstaller 环境中的资源路径。"""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative_path


def apply_app_icon(window: tk.Tk):
    """设置窗口左上角和任务栏图标。"""
    png_path = resource_path(ICON_PNG_PATH)
    ico_path = resource_path(ICON_ICO_PATH)
    try:
        icon_image = tk.PhotoImage(file=str(png_path))
        window.iconphoto(True, icon_image)
        window._lingce_icon_image = icon_image
    except tk.TclError:
        pass

    if sys.platform == "win32" and ico_path.exists():
        try:
            window.iconbitmap(str(ico_path))
        except tk.TclError:
            pass
