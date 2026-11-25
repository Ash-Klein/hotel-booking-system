"""Staff login screen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from ..domain.errors import DomainError
from .theme import COLORS, choose_font
from .widgets import Card

if TYPE_CHECKING:
    from .app import HotelBookingApp

DEMO_ACCOUNTS = [
    ("前台 · 陈晓", "frontdesk", "Frontdesk@123"),
    ("店长 · 王琳", "manager", "Manager@123"),
    ("财务 · 赵敏", "finance", "Finance@123"),
    ("运营 · 周远", "admin", "Admin@123"),
    ("城市经理 · 孙悦", "city", "City@123"),
]


class LoginView(tk.Frame):
    """Split-screen login with a small demo-account quick selector."""

    def __init__(self, parent: tk.Misc, app: "HotelBookingApp") -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self.font = choose_font(self)
        self.username_var = tk.StringVar(value="frontdesk")
        self.password_var = tk.StringVar(value="Frontdesk@123")
        self.error_var = tk.StringVar()
        self._build_brand()
        self._build_form()
        self.after(120, lambda: self.password_entry.focus_set())

    def _build_brand(self) -> None:
        brand = tk.Frame(self, bg=COLORS["navy"])
        brand.place(relx=0, rely=0, relwidth=0.46, relheight=1)
        inner = tk.Frame(brand, bg=COLORS["navy"])
        inner.place(relx=0.09, rely=0.10, relwidth=0.82, relheight=0.80)
        tk.Label(
            inner,
            text="云栖",
            bg=COLORS["navy"],
            fg=COLORS["accent"],
            font=(self.font, 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            inner,
            text="酒店预订\n管理系统",
            bg=COLORS["navy"],
            fg=COLORS["white"],
            font=(self.font, 34, "bold"),
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(10, 14))
        tk.Frame(inner, bg=COLORS["accent"], height=3, width=56).pack(
            anchor="w", pady=(0, 18)
        )
        tk.Label(
            inner,
            text=(
                "从查房、锁房、支付到入住、退房与对账，\n"
                "把一期主链跑通，让库存和价格动作可见。"
            ),
            bg=COLORS["navy"],
            fg="#C8D4E0",
            font=(self.font, 11),
            justify="left",
            anchor="w",
            pady=4,
        ).pack(fill="x")
        features = [
            ("01", "按自然日核算库存", "跨日逐晚校验，任一晚不足则整单拒绝"),
            ("02", "两类支付时限", "线上预付 15 分钟，到店现付 30 分钟"),
            ("03", "全链路留痕", "改价、关房、退款、改单均可追溯"),
        ]
        for number, title, desc in features:
            row = tk.Frame(inner, bg=COLORS["navy"])
            row.pack(fill="x", pady=(22, 0))
            tk.Label(
                row,
                text=number,
                bg=COLORS["navy"],
                fg=COLORS["accent"],
                font=(self.font, 11, "bold"),
                width=3,
                anchor="nw",
            ).pack(side="left", anchor="n")
            text = tk.Frame(row, bg=COLORS["navy"])
            text.pack(side="left", fill="x", expand=True)
            tk.Label(
                text,
                text=title,
                bg=COLORS["navy"],
                fg=COLORS["white"],
                font=(self.font, 10, "bold"),
                anchor="w",
            ).pack(fill="x")
            tk.Label(
                text,
                text=desc,
                bg=COLORS["navy"],
                fg="#9FB0C2",
                font=(self.font, 9),
                anchor="w",
            ).pack(fill="x", pady=(2, 0))
        tk.Label(
            inner,
            text="软件工程实验三 · 241220053 黄若希",
            bg=COLORS["navy"],
            fg="#7F94AA",
            font=(self.font, 8),
            anchor="w",
        ).pack(side="bottom", fill="x")

    def _build_form(self) -> None:
        right = tk.Frame(self, bg=COLORS["bg"])
        right.place(relx=0.46, rely=0, relwidth=0.54, relheight=1)
        holder = tk.Frame(right, bg=COLORS["bg"])
        holder.place(relx=0.12, rely=0.12, relwidth=0.76, relheight=0.76)
        tk.Label(
            holder,
            text="员工登录",
            bg=COLORS["bg"],
            fg=COLORS["navy"],
            font=(self.font, 25, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            holder,
            text="请使用门店或集团账号进入工作台",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(self.font, 10),
            anchor="w",
        ).pack(fill="x", pady=(6, 22))
        card = Card(holder, padding=24)
        card.pack(fill="x")
        form = tk.Frame(card.inner, bg=COLORS["card"])
        form.pack(fill="x")
        tk.Label(
            form,
            text="账号",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 9),
            anchor="w",
        ).pack(fill="x")
        username = ttk.Entry(form, textvariable=self.username_var)
        username.pack(fill="x", pady=(4, 14), ipady=4)
        tk.Label(
            form,
            text="密码",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 9),
            anchor="w",
        ).pack(fill="x")
        self.password_entry = ttk.Entry(
            form, textvariable=self.password_var, show="●"
        )
        self.password_entry.pack(fill="x", pady=(4, 8), ipady=4)
        error = tk.Label(
            form,
            textvariable=self.error_var,
            bg=COLORS["card"],
            fg=COLORS["red"],
            font=(self.font, 9),
            anchor="w",
            wraplength=430,
        )
        error.pack(fill="x", pady=(0, 8))
        ttk.Button(form, text="登 录", command=self._login).pack(
            fill="x", pady=(2, 4)
        )
        for entry in (username, self.password_entry):
            entry.bind("<Return>", lambda _: self._login())
        tk.Label(
            card.inner,
            text="内部员工系统 · 客人预订请使用独立的手机客户端",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 8),
            anchor="w",
        ).pack(fill="x", pady=(12, 0))
        tk.Label(
            holder,
            text="演示账号（点击自动填入）",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(self.font, 9),
            anchor="w",
        ).pack(fill="x", pady=(26, 8))
        demo = tk.Frame(holder, bg=COLORS["bg"])
        demo.pack(fill="x")
        for index, (label, username_text, password_text) in enumerate(
            DEMO_ACCOUNTS
        ):
            row, column = divmod(index, 2)
            button = ttk.Button(
                demo,
                text=label,
                style="Secondary.TButton",
                command=lambda u=username_text, p=password_text: self._fill(
                    u, p
                ),
            )
            button.grid(
                row=row,
                column=column,
                sticky="ew",
                padx=(0, 8) if column == 0 else (8, 0),
                pady=4,
            )
        demo.grid_columnconfigure(0, weight=1)
        demo.grid_columnconfigure(1, weight=1)
        tk.Label(
            holder,
            text=(
                "所有密码仅用于课程演示。真实系统应接入统一身份认证，"
                "并对登录失败做限流。"
            ),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(self.font, 8),
            anchor="w",
            wraplength=560,
            justify="left",
        ).pack(fill="x", pady=(18, 0))

    def _fill(self, username: str, password: str) -> None:
        self.username_var.set(username)
        self.password_var.set(password)
        self.error_var.set("")
        self.password_entry.focus_set()

    def _login(self) -> None:
        try:
            self.app.login(
                self.username_var.get().strip(), self.password_var.get()
            )
        except DomainError as exc:
            self.error_var.set(str(exc))
        except tk.TclError as exc:
            self.error_var.set(f"界面错误：{exc}")
