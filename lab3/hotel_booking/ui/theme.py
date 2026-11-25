"""Visual theme for the Tkinter desktop client."""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from .. import config

COLORS = {
    "navy": "#12263A",
    "navy_light": "#1C3A57",
    "blue": "#1F4E79",
    "blue_light": "#E8F0F8",
    "accent": "#C9A227",
    "accent_light": "#FBF4DA",
    "bg": "#F4F6F9",
    "card": "#FFFFFF",
    "text": "#1B2733",
    "muted": "#6B7C8F",
    "line": "#DCE3EA",
    "green": "#2E7D5B",
    "green_light": "#E7F4EE",
    "red": "#B23A48",
    "red_light": "#FBEAEC",
    "orange": "#B26A1B",
    "orange_light": "#FFF3E3",
    "white": "#FFFFFF",
}


def choose_font(root: tk.Misc) -> str:
    """Pick an installed Chinese UI font, falling back safely."""
    available = set(tkfont.families(root))
    for name in (config.DEFAULT_FONT, "Microsoft YaHei", "SimHei", "Arial"):
        if name in available:
            return name
    return "TkDefaultFont"


def configure_styles(root: tk.Misc) -> str:
    """Configure ttk styles and return the chosen font family."""
    family = choose_font(root)
    root.option_add("*Font", (family, 10))
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", font=(family, 10), background=COLORS["bg"])
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["card"])
    style.configure("Sidebar.TFrame", background=COLORS["navy"])
    style.configure(
        "TLabel", background=COLORS["bg"], foreground=COLORS["text"]
    )
    style.configure(
        "Card.TLabel", background=COLORS["card"], foreground=COLORS["text"]
    )
    style.configure(
        "Muted.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["muted"],
        font=(family, 9),
    )
    style.configure(
        "CardMuted.TLabel",
        background=COLORS["card"],
        foreground=COLORS["muted"],
        font=(family, 9),
    )
    style.configure(
        "H1.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["navy"],
        font=(family, 22, "bold"),
    )
    style.configure(
        "H2.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["navy"],
        font=(family, 14, "bold"),
    )
    style.configure(
        "CardH2.TLabel",
        background=COLORS["card"],
        foreground=COLORS["navy"],
        font=(family, 13, "bold"),
    )
    style.configure(
        "CardValue.TLabel",
        background=COLORS["card"],
        foreground=COLORS["navy"],
        font=(family, 24, "bold"),
    )
    style.configure(
        "Accent.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["accent"],
        font=(family, 10, "bold"),
    )
    style.configure(
        "TButton",
        font=(family, 10),
        padding=(14, 7),
        background=COLORS["blue"],
        foreground=COLORS["white"],
        borderwidth=0,
        focusthickness=0,
    )
    style.map(
        "TButton",
        background=[
            ("active", COLORS["navy_light"]),
            ("disabled", "#AEB9C4"),
        ],
        foreground=[("disabled", "#F0F0F0")],
    )
    style.configure(
        "Secondary.TButton",
        background=COLORS["card"],
        foreground=COLORS["blue"],
        bordercolor=COLORS["line"],
        borderwidth=1,
        padding=(12, 6),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", COLORS["blue_light"])],
        foreground=[("active", COLORS["navy"])],
    )
    style.configure(
        "Ghost.TButton",
        background=COLORS["bg"],
        foreground=COLORS["muted"],
        padding=(8, 4),
    )
    style.map("Ghost.TButton", background=[("active", COLORS["line"])])
    style.configure(
        "Danger.TButton",
        background=COLORS["red"],
        foreground=COLORS["white"],
    )
    style.map("Danger.TButton", background=[("active", "#8E2A36")])
    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["navy"],
    )
    style.map("Accent.TButton", background=[("active", "#B08D1E")])
    style.configure(
        "Nav.TButton",
        background=COLORS["navy"],
        foreground="#DDE6EF",
        anchor="w",
        padding=(22, 12),
        font=(family, 11),
    )
    style.map(
        "Nav.TButton",
        background=[("active", COLORS["navy_light"])],
        foreground=[("active", COLORS["white"])],
    )
    style.configure(
        "NavActive.TButton",
        background=COLORS["blue"],
        foreground=COLORS["white"],
        anchor="w",
        padding=(22, 12),
        font=(family, 11, "bold"),
    )
    style.map(
        "NavActive.TButton",
        background=[("active", COLORS["blue"])],
        foreground=[("active", COLORS["white"])],
    )
    style.configure(
        "TEntry",
        fieldbackground=COLORS["white"],
        bordercolor=COLORS["line"],
        lightcolor=COLORS["line"],
        darkcolor=COLORS["line"],
        padding=6,
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["white"],
        padding=5,
        bordercolor=COLORS["line"],
    )
    style.configure(
        "Treeview",
        background=COLORS["card"],
        fieldbackground=COLORS["card"],
        foreground=COLORS["text"],
        rowheight=30,
        bordercolor=COLORS["line"],
        font=(family, 9),
    )
    style.configure(
        "Treeview.Heading",
        background="#ECF1F6",
        foreground=COLORS["navy"],
        font=(family, 9, "bold"),
        padding=6,
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["blue_light"])],
        foreground=[("selected", COLORS["navy"])],
    )
    style.configure(
        "TNotebook",
        background=COLORS["bg"],
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        background=COLORS["bg"],
        foreground=COLORS["muted"],
        padding=(16, 8),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["card"])],
        foreground=[("selected", COLORS["navy"])],
    )
    style.configure(
        "TLabelframe",
        background=COLORS["bg"],
        bordercolor=COLORS["line"],
        relief="solid",
    )
    style.configure(
        "TLabelframe.Label",
        background=COLORS["bg"],
        foreground=COLORS["navy"],
        font=(family, 10, "bold"),
    )
    style.configure(
        "TProgressbar",
        background=COLORS["blue"],
        troughcolor=COLORS["line"],
    )
    style.configure(
        "TCheckbutton",
        background=COLORS["bg"],
        foreground=COLORS["text"],
    )
    style.configure(
        "Card.TCheckbutton",
        background=COLORS["card"],
        foreground=COLORS["text"],
    )
    style.configure(
        "TRadiobutton",
        background=COLORS["card"],
        foreground=COLORS["text"],
    )
    return family
