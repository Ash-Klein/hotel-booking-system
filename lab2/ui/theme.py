# -*- coding: utf-8 -*-
"""UI 设计系统：颜色、字体、尺寸。"""

import os

FONT_DIR = r"C:\Windows\Fonts"
FONT_REG = os.path.join(FONT_DIR, "msyh.ttc")
FONT_BOLD = os.path.join(FONT_DIR, "msyhbd.ttc")

C = {
    "primary": "#1F3A5F",
    "primary_deep": "#12263F",
    "primary_soft": "#2C5282",
    "gold": "#C9A227",
    "gold_soft": "#F7EBC8",
    "bg": "#F4F6FA",
    "card": "#FFFFFF",
    "text": "#1B2430",
    "muted": "#6B7785",
    "faint": "#9AA5B1",
    "border": "#E3E8EF",
    "line": "#EDF1F6",
    "green": "#1E8E5A",
    "green_bg": "#E6F4EC",
    "amber": "#C77700",
    "amber_bg": "#FFF3DE",
    "red": "#C0392B",
    "red_bg": "#FDECEA",
    "blue_bg": "#E8F0FA",
    "purple": "#6B4FA1",
    "purple_bg": "#F0EAF9",
}

MOBILE_W, MOBILE_H = 390, 844
DESK_W, DESK_H = 1440, 900
