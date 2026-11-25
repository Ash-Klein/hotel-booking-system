"""Standalone mobile-style guest client.

The guest program is deliberately a separate Tk root and entry point
(``run_guest.py``) from the staff/group desktop client (``run.py``). It uses a
390 x 844-ish portrait viewport, card lists and a bottom tab bar so that the
implemented UI follows the experiment-two mini-program design instead of the
desktop staff layout.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import simpledialog, ttk

from .. import config
from ..domain.enums import OrderStatus, PayMode
from ..domain.errors import DomainError
from ..domain.models import Order, SearchResult
from ..domain.money import yuan
from ..services.app import Services, create_services
from .theme import COLORS, choose_font, configure_styles
from .widgets import Toast

PHONE_BG = "#E8EDF2"
SOFT = "#F7F9FC"
WHITE = "#FFFFFF"


def label(parent: tk.Misc, text: str, size: int = 10, color: str = COLORS["text"],
          bold: bool = False, bg: str = WHITE, **kwargs) -> tk.Label:
    """Create a compact mobile label."""
    return tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=color,
        font=("Microsoft YaHei UI", size, "bold" if bold else "normal"),
        **kwargs,
    )


def field(
    parent: tk.Misc,
    text: str,
    variable: tk.Variable,
    *,
    values: list[str] | None = None,
    show: str | None = None,
) -> tk.Widget:
    """Mobile label + entry/combobox block."""
    holder = tk.Frame(parent, bg=WHITE)
    holder.pack(fill="x", pady=(0, 9))
    label(holder, text, 8, COLORS["muted"], bg=WHITE, anchor="w").pack(fill="x")
    if values is not None:
        widget: tk.Widget = ttk.Combobox(
            holder, textvariable=variable, values=values, state="readonly"
        )
    else:
        widget = tk.Entry(
            holder,
            textvariable=variable,
            show=show or "",
            bg=SOFT,
            fg=COLORS["text"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["line"],
            highlightcolor=COLORS["blue"],
            font=("Microsoft YaHei UI", 10),
        )
    widget.pack(fill="x", ipady=5, pady=(3, 0))
    return widget


def box(parent: tk.Misc, padding: int = 12) -> tk.Frame:
    """White mobile card."""
    frame = tk.Frame(
        parent,
        bg=WHITE,
        highlightbackground=COLORS["line"],
        highlightthickness=1,
    )
    inner = tk.Frame(frame, bg=WHITE)
    inner.pack(fill="both", expand=True, padx=padding, pady=padding)
    frame.inner = inner  # type: ignore[attr-defined]
    return frame


def mobile_button(parent: tk.Misc, text: str, command, *, primary: bool = True,
                  width: int = 0) -> tk.Button:
    """Flat mobile action button."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=COLORS["blue"] if primary else WHITE,
        fg=WHITE if primary else COLORS["blue"],
        activebackground=COLORS["navy_light"] if primary else COLORS["blue_light"],
        activeforeground=WHITE if primary else COLORS["navy"],
        relief="flat",
        bd=0,
        highlightthickness=1 if not primary else 0,
        highlightbackground=COLORS["line"],
        font=("Microsoft YaHei UI", 9, "bold" if primary else "normal"),
        padx=12,
        pady=7,
        cursor="hand2",
        width=width,
    )


class GuestApplication(tk.Tk):
    """Standalone portrait guest application."""

    def __init__(self, services: Services) -> None:
        super().__init__()
        self.services = services
        self.font = configure_styles(self)
        self.title(config.GUEST_APP_NAME)
        self.geometry(config.GUEST_WINDOW_SIZE)
        self.resizable(False, False)
        self.configure(bg=PHONE_BG)
        self.current_page: tk.Frame | None = None
        self.last_search: dict[str, object] | None = None
        self.last_phone = ""
        self.toast = Toast(self)
        self._center_window()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.show_search()

    def _center_window(self) -> None:
        self.update_idletasks()
        width = 390
        height = 844
        x = max((self.winfo_screenwidth() - width) // 2, 0)
        y = max((self.winfo_screenheight() - height) // 2 - 20, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _show(self, page: tk.Frame) -> None:
        if self.current_page is not None:
            self.current_page.destroy()
        self.current_page = page
        page.pack(fill="both", expand=True)

    def show_search(self) -> None:
        """Open room search."""
        self._show(MobileSearchPage(self, self))

    def show_orders(self, phone: str = "") -> None:
        """Open order lookup."""
        if phone:
            self.last_phone = phone
        self._show(MobileOrdersPage(self, self, self.last_phone))

    def show_detail(self, result: SearchResult) -> None:
        """Open room detail for a search result."""
        self._show(MobileRoomDetailPage(self, self, result))

    def show_booking(self, result: SearchResult) -> None:
        """Open the booking form for a room."""
        self._show(MobileBookingPage(self, self, result))

    def show_success(self, order: Order, phone: str) -> None:
        """Show the booking success screen."""
        self._show(MobileSuccessPage(self, self, order, phone))

    def show_order_detail(self, order: Order, phone: str) -> None:
        """Show one order's detail."""
        self._show(MobileOrderDetailPage(self, self, order, phone))

    def show_modify(self, order: Order, phone: str) -> None:
        """Open the self-service modification page."""
        self._show(MobileModifyPage(self, self, order, phone))

    def notify(self, message: str, kind: str = "info") -> None:
        """Toast message."""
        self.toast.show(message, kind)


class MobileHeader(tk.Frame):
    """Portrait top bar."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        subtitle: str = "",
        *,
        back: object | None = None,
        brand: bool = False,
    ) -> None:
        super().__init__(parent, bg=COLORS["navy"], height=88)
        self.pack(fill="x")
        self.pack_propagate(False)
        if back is not None:
            tk.Button(
                self,
                text="‹",
                command=back,  # type: ignore[arg-type]
                bg=COLORS["navy"],
                fg=WHITE,
                activebackground=COLORS["navy_light"],
                activeforeground=WHITE,
                relief="flat",
                bd=0,
                font=("Microsoft YaHei UI", 24),
                cursor="hand2",
                padx=14,
            ).pack(side="left", fill="y")
        text = tk.Frame(self, bg=COLORS["navy"])
        text.pack(side="left", fill="both", expand=True, padx=(18 if back is None else 0, 16))
        if brand:
            label(
                text, "云栖酒店", 20, WHITE, True, COLORS["navy"], anchor="w"
            ).pack(fill="x", pady=(18, 0))
            label(
                text, subtitle or "手机预订", 9, "#B9C7D5",
                False, COLORS["navy"], anchor="w"
            ).pack(fill="x", pady=(1, 0))
        else:
            label(
                text, title, 16, WHITE, True, COLORS["navy"], anchor="w"
            ).pack(fill="x", pady=(22, 0))
            if subtitle:
                label(
                    text, subtitle, 8, "#B9C7D5", False,
                    COLORS["navy"], anchor="w"
                ).pack(fill="x", pady=(2, 0))


class BottomNav(tk.Frame):
    """Two-tab bottom navigation."""

    def __init__(self, parent: tk.Misc, app: GuestApplication, active: str) -> None:
        super().__init__(parent, bg=WHITE, height=62,
                         highlightbackground=COLORS["line"], highlightthickness=1)
        self.pack(side="bottom", fill="x")
        self.pack_propagate(False)
        items = [
            ("search", "⌕", "查房"),
            ("orders", "▤", "订单"),
        ]
        for index, (key, icon, text) in enumerate(items):
            frame = tk.Frame(self, bg=WHITE)
            frame.grid(row=0, column=index, sticky="nsew")
            active_item = key == active
            tk.Label(
                frame,
                text=icon,
                bg=WHITE,
                fg=COLORS["blue"] if active_item else COLORS["muted"],
                font=("Microsoft YaHei UI", 17),
            ).pack(pady=(7, 0))
            tk.Label(
                frame,
                text=text,
                bg=WHITE,
                fg=COLORS["blue"] if active_item else COLORS["muted"],
                font=("Microsoft YaHei UI", 8, "bold" if active_item else "normal"),
            ).pack()
            for widget in (frame,) + tuple(frame.winfo_children()):
                widget.bind(
                    "<Button-1>",
                    lambda _event, name=key: (
                        app.show_search() if name == "search"
                        else app.show_orders(app.last_phone)
                    ),
                )
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)


class MobileSearchPage(tk.Frame):
    """Portrait search page with card results."""

    def __init__(self, parent: tk.Misc, app: GuestApplication) -> None:
        super().__init__(parent, bg=PHONE_BG)
        self.app = app
        self.services = app.services
        self.results: list[SearchResult] = []
        MobileHeader(self, "云栖酒店", "选城市 · 选日期 · 看实价", brand=True)
        self.scroll = tk.Frame(self, bg=PHONE_BG)
        self.scroll.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(self.scroll, bg=PHONE_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self.scroll, orient="vertical", command=self.canvas.yview
        )
        self.inner = tk.Frame(self.canvas, bg=PHONE_BG)
        window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.inner.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(window, width=event.width),
        )
        BottomNav(self, app, "search")
        self._build_filters()
        self.results_box = tk.Frame(self.inner, bg=PHONE_BG)
        self.results_box.pack(fill="x", padx=12, pady=(0, 12))
        state = app.last_search
        if state:
            self.city_var.set(str(state["city"]))
            self.check_in_var.set(str(state["check_in"]))
            self.check_out_var.set(str(state["check_out"]))
            self.guests_var.set(str(state["guests"]))
            self.price_var.set(str(state["price"]))
            self.breakfast_var.set(bool(state["breakfast"]))
        self.after(60, self.search)

    def _build_filters(self) -> None:
        card = box(self.inner)
        card.pack(fill="x", padx=12, pady=10)
        form = card.inner  # type: ignore[attr-defined]
        self.city_var = tk.StringVar(value="全部城市")
        self.check_in_var = tk.StringVar(
            value=(date.today() + timedelta(days=1)).isoformat()
        )
        self.check_out_var = tk.StringVar(
            value=(date.today() + timedelta(days=2)).isoformat()
        )
        self.guests_var = tk.StringVar(value="2")
        self.price_var = tk.StringVar()
        self.breakfast_var = tk.BooleanVar(value=False)
        field(
            form,
            "目的地",
            self.city_var,
            values=["全部城市", *self.services.catalog.cities()],
        )
        dates = tk.Frame(form, bg=WHITE)
        dates.pack(fill="x", pady=(0, 9))
        left = tk.Frame(dates, bg=WHITE)
        left.pack(side="left", fill="x", expand=True, padx=(0, 5))
        label(left, "入住", 8, COLORS["muted"], bg=WHITE, anchor="w").pack(fill="x")
        ttk.Entry(left, textvariable=self.check_in_var).pack(
            fill="x", ipady=4, pady=(3, 0)
        )
        right = tk.Frame(dates, bg=WHITE)
        right.pack(side="left", fill="x", expand=True, padx=(5, 0))
        label(right, "离店", 8, COLORS["muted"], bg=WHITE, anchor="w").pack(fill="x")
        ttk.Entry(right, textvariable=self.check_out_var).pack(
            fill="x", ipady=4, pady=(3, 0)
        )
        extra = tk.Frame(form, bg=WHITE)
        extra.pack(fill="x", pady=(0, 8))
        left = tk.Frame(extra, bg=WHITE)
        left.pack(side="left", fill="x", expand=True, padx=(0, 5))
        label(left, "人数", 8, COLORS["muted"], bg=WHITE, anchor="w").pack(fill="x")
        ttk.Combobox(
            left,
            textvariable=self.guests_var,
            values=[str(index) for index in range(1, 7)],
            state="readonly",
        ).pack(fill="x", pady=(3, 0))
        right = tk.Frame(extra, bg=WHITE)
        right.pack(side="left", fill="x", expand=True, padx=(5, 0))
        label(right, "每晚最高价", 8, COLORS["muted"], bg=WHITE, anchor="w").pack(fill="x")
        tk.Entry(
            right,
            textvariable=self.price_var,
            bg=SOFT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["line"],
        ).pack(fill="x", ipady=4, pady=(3, 0))
        ttk.Checkbutton(
            form,
            text="仅看含早房型",
            variable=self.breakfast_var,
            style="Card.TCheckbutton",
        ).pack(anchor="w", pady=(0, 9))
        mobile_button(form, "查询空房", self.search).pack(fill="x")

    def search(self) -> None:
        """Run the search and draw cards."""
        for child in self.results_box.winfo_children():
            child.destroy()
        try:
            city = self.city_var.get()
            city = "" if city == "全部城市" else city
            check_in = date.fromisoformat(self.check_in_var.get().strip())
            check_out = date.fromisoformat(self.check_out_var.get().strip())
            guests = int(self.guests_var.get())
            max_price = None
            if self.price_var.get().strip():
                max_price = Decimal(self.price_var.get().strip())
            results = self.services.catalog.search(
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                city=city,
                max_price=max_price,
                breakfast_only=self.breakfast_var.get(),
            )
        except (ValueError, InvalidOperation, DomainError) as exc:
            label(self.results_box, str(exc), 9, COLORS["red"], bg=PHONE_BG,
                  wraplength=350, justify="left").pack(fill="x", pady=18)
            return
        self.results = results
        self.app.last_search = {
            "city": self.city_var.get(),
            "check_in": self.check_in_var.get(),
            "check_out": self.check_out_var.get(),
            "guests": self.guests_var.get(),
            "price": self.price_var.get(),
            "breakfast": self.breakfast_var.get(),
        }
        available = sum(1 for item in results if item.available)
        label(
            self.results_box,
            f"{len(results)} 个房型 · {available} 个可订",
            9,
            COLORS["muted"],
            bg=PHONE_BG,
            anchor="w",
        ).pack(fill="x", pady=(2, 6))
        if not results:
            empty = box(self.results_box, 18)
            empty.pack(fill="x")
            label(empty.inner, "暂无可预订房源", 13, COLORS["navy"], True).pack()
            label(
                empty.inner, "试试调整日期、城市或价格条件", 9, COLORS["muted"]
            ).pack(pady=(4, 0))
            return
        for result in results:
            self._result_card(result)

    def _result_card(self, result: SearchResult) -> None:
        quote = result.quote
        card = box(self.results_box, 12)
        card.pack(fill="x", pady=(0, 8))
        inner = card.inner  # type: ignore[attr-defined]
        top = tk.Frame(inner, bg=WHITE)
        top.pack(fill="x")
        label(top, result.hotel.name, 13, COLORS["navy"], True).pack(
            side="left", anchor="w"
        )
        label(
            top,
            f"¥{int(quote.nights[0].unit_price) if quote.nights else 0} 起",
            13,
            COLORS["red"],
            True,
        ).pack(side="right")
        label(
            inner,
            f"{result.room_type.name} · {result.room_type.bed_type}",
            9,
            COLORS["muted"],
            anchor="w",
        ).pack(fill="x", pady=(3, 0))
        label(
            inner,
            f"{quote.check_in} 至 {quote.check_out} · {quote.night_count} 晚 · "
            f"{quote.min_available} 间可订",
            8,
            COLORS["muted"],
            anchor="w",
        ).pack(fill="x", pady=(2, 0))
        bottom = tk.Frame(inner, bg=WHITE)
        bottom.pack(fill="x", pady=(8, 0))
        status = "可预订" if quote.is_available else quote.reason
        label(
            bottom,
            status,
            8,
            COLORS["green"] if quote.is_available else COLORS["red"],
            bg=WHITE,
        ).pack(side="left")
        button = mobile_button(
            bottom,
            "查看" if not quote.is_available else "订",
            lambda item=result: self.app.show_detail(item),
            primary=quote.is_available,
            width=4,
        )
        button.pack(side="right")
        label(
            bottom,
            f"总价 {yuan(quote.total)}",
            9,
            COLORS["navy"],
            True,
        ).pack(side="right", padx=8)


class MobileRoomDetailPage(tk.Frame):
    """Portrait room detail page."""

    def __init__(self, parent: tk.Misc, app: GuestApplication,
                 result: SearchResult) -> None:
        super().__init__(parent, bg=PHONE_BG)
        self.app = app
        self.result = result
        self.services = app.services
        quote = result.quote
        MobileHeader(
            self, "房型详情", f"{result.hotel.city}{result.hotel.district}",
            back=app.show_search,
        )
        self.scroll = tk.Frame(self, bg=PHONE_BG)
        self.scroll.pack(fill="both", expand=True)
        canvas = tk.Canvas(self.scroll, bg=PHONE_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.scroll, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=PHONE_BG)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        inner.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window, width=event.width),
        )
        hero = box(inner, 16)
        hero.pack(fill="x", padx=12, pady=10)
        label(hero.inner, result.hotel.name, 16, COLORS["navy"], True).pack(
            anchor="w"
        )
        label(
            hero.inner,
            f"{result.room_type.name} · {result.room_type.bed_type} · "
            f"可住 {result.room_type.capacity} 人",
            9,
            COLORS["muted"],
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))
        price_row = tk.Frame(hero.inner, bg=WHITE)
        price_row.pack(fill="x", pady=(12, 0))
        label(price_row, yuan(quote.total), 24, COLORS["red"], True).pack(side="left")
        label(price_row, f" / {quote.night_count} 晚", 9, COLORS["muted"]).pack(
            side="left", pady=(8, 0)
        )
        facts = box(inner, 12)
        facts.pack(fill="x", padx=12, pady=(0, 10))
        grid = tk.Frame(facts.inner, bg=WHITE)
        grid.pack(fill="x")
        data = [
            ("入住", quote.check_in.isoformat()),
            ("离店", quote.check_out.isoformat()),
            ("房间数", f"{quote.qty} 间"),
            ("早餐", "含早" if result.room_type.breakfast else "不含早"),
        ]
        for index, (name, value) in enumerate(data):
            row, column = divmod(index, 2)
            cell = tk.Frame(grid, bg=WHITE)
            cell.grid(row=row, column=column, sticky="w", padx=8, pady=5)
            label(cell, name, 8, COLORS["muted"], bg=WHITE).pack(anchor="w")
            label(cell, value, 10, COLORS["navy"], True, WHITE).pack(anchor="w")
        nightly = box(inner, 12)
        nightly.pack(fill="x", padx=12, pady=(0, 10))
        label(nightly.inner, "每晚价格", 11, COLORS["navy"], True).pack(
            anchor="w", pady=(0, 4)
        )
        for night in quote.nights:
            row = tk.Frame(nightly.inner, bg=WHITE)
            row.pack(fill="x", pady=3)
            label(row, night.biz_date.isoformat(), 9).pack(side="left")
            label(
                row,
                "特殊日期" if night.is_special else f"剩 {night.available} 间",
                8,
                COLORS["orange"] if night.is_special else COLORS["muted"],
                bg=WHITE,
            ).pack(side="left", padx=8)
            label(row, yuan(night.unit_price), 10, COLORS["navy"], True).pack(
                side="right"
            )
        policy = tk.Label(
            inner,
            text=(
                "取消政策：入住前 24 小时免费取消；24 小时内或当日取消扣首晚房费；"
                "特殊日期统一扣首晚 100%。"
            ),
            bg=COLORS["accent_light"],
            fg="#5D4037",
            justify="left",
            wraplength=340,
            padx=10,
            pady=9,
            anchor="w",
            font=("Microsoft YaHei UI", 8),
        )
        policy.pack(fill="x", padx=12, pady=(0, 12))
        action = tk.Frame(self, bg=WHITE, height=64,
                          highlightbackground=COLORS["line"], highlightthickness=1)
        action.pack(side="bottom", fill="x")
        action.pack_propagate(False)
        label(action, yuan(quote.total), 15, COLORS["red"], True).pack(
            side="left", padx=16
        )
        button = mobile_button(
            action,
            "立即预订" if quote.is_available else "当前不可订",
            lambda: self.app.show_booking(result),
            primary=quote.is_available,
        )
        button.pack(side="right", padx=14, pady=12)
        if not quote.is_available:
            button.configure(state="disabled", bg="#AEB9C4")


class MobileBookingPage(tk.Frame):
    """Portrait booking form."""

    def __init__(self, parent: tk.Misc, app: GuestApplication,
                 result: SearchResult) -> None:
        super().__init__(parent, bg=PHONE_BG)
        self.app = app
        self.result = result
        self.services = app.services
        quote = result.quote
        MobileHeader(
            self, "填写订单", f"{quote.night_count} 晚 · {quote.qty} 间",
            back=lambda: app.show_detail(result),
        )
        self.scroll = tk.Frame(self, bg=PHONE_BG)
        self.scroll.pack(fill="both", expand=True)
        canvas = tk.Canvas(self.scroll, bg=PHONE_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.scroll, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=PHONE_BG)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        inner.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window, width=event.width),
        )
        summary = box(inner, 12)
        summary.pack(fill="x", padx=12, pady=10)
        label(summary.inner, result.hotel.name, 13, COLORS["navy"], True).pack(
            anchor="w"
        )
        label(
            summary.inner,
            f"{result.room_type.name} · {quote.check_in} 至 {quote.check_out}",
            8,
            COLORS["muted"],
            anchor="w",
        ).pack(anchor="w", pady=(3, 0))
        label(
            summary.inner,
            yuan(quote.total),
            18,
            COLORS["red"],
            True,
            WHITE,
            anchor="e",
        ).pack(anchor="e", pady=(6, 0))
        self.error_var = tk.StringVar()
        form_card = box(inner, 12)
        form_card.pack(fill="x", padx=12, pady=(0, 10))
        form = form_card.inner  # type: ignore[attr-defined]
        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.qty_var = tk.IntVar(value=1)
        self.pay_var = tk.StringVar(value=PayMode.ONLINE.label)
        self.pay_now_var = tk.BooleanVar(value=True)
        field(form, "入住人姓名", self.name_var)
        field(form, "手机号", self.phone_var)
        row = tk.Frame(form, bg=WHITE)
        row.pack(fill="x", pady=(0, 9))
        qty = tk.Frame(row, bg=WHITE)
        qty.pack(side="left", fill="x", expand=True, padx=(0, 5))
        label(qty, "间数", 8, COLORS["muted"], bg=WHITE, anchor="w").pack(fill="x")
        ttk.Spinbox(
            qty, from_=1, to=5, textvariable=self.qty_var, width=8
        ).pack(fill="x", pady=(3, 0))
        pay = tk.Frame(row, bg=WHITE)
        pay.pack(side="left", fill="x", expand=True, padx=(5, 0))
        label(pay, "支付方式", 8, COLORS["muted"], bg=WHITE, anchor="w").pack(fill="x")
        ttk.Combobox(
            pay,
            textvariable=self.pay_var,
            values=[PayMode.ONLINE.label, PayMode.AT_HOTEL.label],
            state="readonly",
        ).pack(fill="x", pady=(3, 0))
        ttk.Checkbutton(
            form,
            text="创建后立即模拟支付",
            variable=self.pay_now_var,
            style="Card.TCheckbutton",
        ).pack(anchor="w")
        tk.Label(
            form,
            textvariable=self.error_var,
            bg=WHITE,
            fg=COLORS["red"],
            font=("Microsoft YaHei UI", 8),
            anchor="w",
            wraplength=330,
            justify="left",
        ).pack(fill="x", pady=(8, 0))
        label(
            inner,
            "提交后将逐晚校验库存并锁定房间；未支付订单超时自动取消。",
            8,
            COLORS["muted"],
            bg=PHONE_BG,
            anchor="w",
            wraplength=350,
            justify="left",
        ).pack(fill="x", padx=12, pady=(0, 12))
        action = tk.Frame(self, bg=WHITE, height=64,
                          highlightbackground=COLORS["line"], highlightthickness=1)
        action.pack(side="bottom", fill="x")
        action.pack_propagate(False)
        label(action, yuan(quote.total), 15, COLORS["red"], True).pack(
            side="left", padx=16
        )
        mobile_button(action, "提交订单", self.submit).pack(
            side="right", padx=14, pady=12
        )

    def submit(self) -> None:
        """Create and optionally pay the order."""
        try:
            mode = (
                PayMode.ONLINE
                if self.pay_var.get() == PayMode.ONLINE.label
                else PayMode.AT_HOTEL
            )
            order = self.services.booking.create_order(
                guest_name=self.name_var.get(),
                phone=self.phone_var.get(),
                hotel_id=self.result.hotel.hotel_id,
                room_type_id=self.result.room_type.room_type_id,
                check_in=self.result.quote.check_in,
                check_out=self.result.quote.check_out,
                qty=int(self.qty_var.get()),
                pay_mode=mode,
            )
            if mode is PayMode.ONLINE and self.pay_now_var.get():
                order = self.services.booking.pay_order(order.order_no)
        except (DomainError, ValueError) as exc:
            self.error_var.set(str(exc))
            return
        self.app.show_success(order, order.contact_phone)


class MobileSuccessPage(tk.Frame):
    """Booking success screen."""

    def __init__(self, parent: tk.Misc, app: GuestApplication,
                 order: Order, phone: str) -> None:
        super().__init__(parent, bg=PHONE_BG)
        self.app = app
        MobileHeader(self, "预订成功", "订单已生成", brand=False)
        inner = tk.Frame(self, bg=PHONE_BG)
        inner.pack(fill="both", expand=True, padx=20, pady=24)
        tk.Label(
            inner,
            text="✓",
            bg=COLORS["green_light"],
            fg=COLORS["green"],
            font=("Microsoft YaHei UI", 34, "bold"),
            width=3,
            height=1,
        ).pack(pady=(30, 12))
        label(inner, "预订成功", 20, COLORS["navy"], True, PHONE_BG).pack()
        card = box(inner, 14)
        card.pack(fill="x", pady=18)
        label(card.inner, order.order_no, 12, COLORS["navy"], True).pack(anchor="w")
        label(
            card.inner,
            f"{order.hotel_name} · {order.room_type_name}",
            9,
            COLORS["muted"],
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))
        label(
            card.inner,
            f"{order.check_in} 至 {order.check_out} · {yuan(order.total_amount)}",
            9,
            COLORS["navy"],
            anchor="w",
        ).pack(anchor="w", pady=(3, 0))
        label(
            card.inner,
            f"状态：{order.status.label}",
            9,
            COLORS["green"],
            True,
            WHITE,
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))
        mobile_button(
            inner, "查看我的订单", lambda: app.show_orders(phone)
        ).pack(fill="x", pady=(4, 8))
        mobile_button(
            inner, "继续订房", app.show_search, primary=False
        ).pack(fill="x")


class MobileOrdersPage(tk.Frame):
    """Portrait order history and guest self-service."""

    def __init__(self, parent: tk.Misc, app: GuestApplication,
                 phone: str = "") -> None:
        super().__init__(parent, bg=PHONE_BG)
        self.app = app
        self.services = app.services
        self.orders: list[Order] = []
        MobileHeader(self, "我的订单", "输入预订手机号查询", brand=False)
        self.scroll = tk.Frame(self, bg=PHONE_BG)
        self.scroll.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(self.scroll, bg=PHONE_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self.scroll, orient="vertical", command=self.canvas.yview
        )
        self.inner = tk.Frame(self.canvas, bg=PHONE_BG)
        window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.inner.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(window, width=event.width),
        )
        BottomNav(self, app, "orders")
        search = box(self.inner, 12)
        search.pack(fill="x", padx=12, pady=10)
        self.phone_var = tk.StringVar(value=phone)
        field(search.inner, "预订手机号", self.phone_var)
        mobile_button(search.inner, "查询订单", self.search).pack(fill="x")
        self.summary_var = tk.StringVar(value="")
        label(
            self.inner, "", 8, COLORS["muted"], bg=PHONE_BG,
            textvariable=self.summary_var, anchor="w"
        ).pack(fill="x", padx=14)
        self.list_box = tk.Frame(self.inner, bg=PHONE_BG)
        self.list_box.pack(fill="x", padx=0, pady=(4, 12))
        if phone:
            self.after(60, self.search)

    def search(self) -> None:
        """Load orders for the entered phone."""
        for child in self.list_box.winfo_children():
            child.destroy()
        phone = self.phone_var.get().strip()
        if not phone:
            self.summary_var.set("请输入预订时使用的手机号")
            return
        guest = self.services.order_repo.find_guest_by_phone(None, phone)
        if not guest:
            self.summary_var.set("没有查到该手机号的订单")
            return
        self.app.last_phone = phone
        self.orders = self.services.order_repo.list_for_guest(guest.guest_id)
        self.summary_var.set(f"共 {len(self.orders)} 笔订单")
        for order in self.orders:
            self._order_card(order)

    def _order_card(self, order: Order) -> None:
        card = box(self.list_box, 12)
        card.pack(fill="x", padx=12, pady=(0, 8))
        inner = card.inner  # type: ignore[attr-defined]
        top = tk.Frame(inner, bg=WHITE)
        top.pack(fill="x")
        label(top, order.order_no, 9, COLORS["muted"]).pack(side="left")
        color = {
            OrderStatus.PENDING_PAYMENT: COLORS["orange"],
            OrderStatus.CONFIRMED: COLORS["blue"],
            OrderStatus.CHECKED_IN: COLORS["green"],
            OrderStatus.CHECKED_OUT: COLORS["muted"],
            OrderStatus.CANCELLED: COLORS["muted"],
            OrderStatus.NO_SHOW: COLORS["red"],
            OrderStatus.EXCEPTION: COLORS["red"],
        }.get(order.status, COLORS["muted"])
        label(top, order.status.label, 8, color, True).pack(side="right")
        label(
            inner,
            f"{order.hotel_name} · {order.room_type_name}",
            11,
            COLORS["navy"],
            True,
            WHITE,
            anchor="w",
        ).pack(fill="x", pady=(5, 1))
        label(
            inner,
            f"{order.check_in} 至 {order.check_out} · {order.qty} 间 · "
            f"{yuan(order.total_amount)}",
            8,
            COLORS["muted"],
            anchor="w",
        ).pack(fill="x")
        actions = tk.Frame(inner, bg=WHITE)
        actions.pack(fill="x", pady=(8, 0))
        if order.status is OrderStatus.PENDING_PAYMENT and order.pay_mode is PayMode.ONLINE:
            mobile_button(
                actions, "支付", lambda item=order: self.pay(item),
                width=5,
            ).pack(side="right", padx=(4, 0))
        if order.can_modify:
            mobile_button(
                actions, "改期",
                lambda item=order: self.app.show_modify(item, self.phone_var.get()),
                primary=False,
                width=5,
            ).pack(side="right", padx=4)
        if order.can_cancel:
            mobile_button(
                actions, "取消", lambda item=order: self.cancel(item),
                primary=False,
                width=5,
            ).pack(side="right", padx=4)
        mobile_button(
            actions, "详情",
            lambda item=order: self.app.show_order_detail(item, self.phone_var.get()),
            primary=False,
            width=5,
        ).pack(side="right")

    def pay(self, order: Order) -> None:
        """Pay a pending online order."""
        try:
            paid = self.services.booking.pay_order(order.order_no)
        except DomainError as exc:
            self.app.notify(str(exc), "error")
            self.search()
            return
        self.app.notify(f"已支付 {yuan(paid.total_amount)}", "success")
        self.search()

    def cancel(self, order: Order) -> None:
        """Cancel an order with a reason."""
        reason = simpledialog.askstring(
            "取消订单", "请填写取消原因：", parent=self
        )
        if not reason:
            return
        try:
            result = self.services.booking.cancel_order(
                order.order_no,
                reason=reason,
                guest_phone=self.phone_var.get().strip(),
            )
        except DomainError as exc:
            self.app.notify(str(exc), "error")
            return
        message = (
            f"已取消，退款 {yuan(result['refund_amount'])}，"
            f"违约金 {yuan(result['penalty'])}"
        )
        self.app.notify(message, "success")
        self.search()


class MobileOrderDetailPage(tk.Frame):
    """Portrait order detail."""

    def __init__(self, parent: tk.Misc, app: GuestApplication,
                 order: Order, phone: str) -> None:
        super().__init__(parent, bg=PHONE_BG)
        self.app = app
        MobileHeader(
            self, "订单详情", order.status.label,
            back=lambda: app.show_orders(phone),
        )
        scroll = tk.Frame(self, bg=PHONE_BG)
        scroll.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroll, bg=PHONE_BG, highlightthickness=0)
        bar = ttk.Scrollbar(scroll, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=PHONE_BG)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        inner.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window, width=event.width),
        )
        card = box(inner, 14)
        card.pack(fill="x", padx=12, pady=10)
        label(card.inner, order.hotel_name, 14, COLORS["navy"], True).pack(anchor="w")
        label(
            card.inner,
            f"{order.room_type_name} · {order.qty} 间 · {order.nights} 晚",
            9,
            COLORS["muted"],
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))
        label(
            card.inner,
            yuan(order.total_amount),
            20,
            COLORS["red"],
            True,
            WHITE,
            anchor="w",
        ).pack(anchor="w", pady=(8, 0))
        field = box(inner, 12)
        field.pack(fill="x", padx=12, pady=(0, 10))
        data = [
            ("入住 / 离店", f"{order.check_in} / {order.check_out}"),
            ("入住人", order.contact_name),
            ("手机号", order.contact_phone),
            ("支付方式", order.pay_mode.label),
            ("房号", order.assigned_rooms or "入住时分配"),
        ]
        for name, value in data:
            row = tk.Frame(field.inner, bg=WHITE)
            row.pack(fill="x", pady=3)
            label(row, name, 8, COLORS["muted"]).pack(side="left")
            label(row, value, 9, COLORS["navy"]).pack(side="right")
        payments = app.services.order_repo.list_payments(order.order_no)
        if payments:
            pay_card = box(inner, 12)
            pay_card.pack(fill="x", padx=12, pady=(0, 10))
            label(pay_card.inner, "支付流水", 10, COLORS["navy"], True).pack(anchor="w")
            for payment in payments:
                row = tk.Frame(pay_card.inner, bg=WHITE)
                row.pack(fill="x", pady=3)
                label(row, payment.payment_no, 7, COLORS["muted"]).pack(side="left")
                label(
                    row, f"{yuan(payment.amount)} · {payment.status.label}",
                    8, COLORS["navy"]
                ).pack(side="right")


class MobileModifyPage(tk.Frame):
    """Portrait self-service modification."""

    def __init__(self, parent: tk.Misc, app: GuestApplication,
                 order: Order, phone: str) -> None:
        super().__init__(parent, bg=PHONE_BG)
        self.app = app
        self.order = order
        self.phone = phone
        self.services = app.services
        MobileHeader(
            self, "修改订单", order.order_no,
            back=lambda: app.show_orders(phone),
        )
        source = self.services.catalog.hotel(order.hotel_id)
        self.city = source.city
        self.hotel_map = {
            item.name: item
            for item in self.services.catalog.hotels(city=self.city)
        }
        self.hotel_var = tk.StringVar(value=source.name)
        self.room_var = tk.StringVar(value=order.room_type_name)
        self.check_in_var = tk.StringVar(value=order.check_in.isoformat())
        self.check_out_var = tk.StringVar(value=order.check_out.isoformat())
        self.quote_var = tk.StringVar(value="修改后点击“重新计价”")
        scroll = tk.Frame(self, bg=PHONE_BG)
        scroll.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroll, bg=PHONE_BG, highlightthickness=0)
        bar = ttk.Scrollbar(scroll, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=PHONE_BG)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        inner.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window, width=event.width),
        )
        card = box(inner, 12)
        card.pack(fill="x", padx=12, pady=10)
        form = card.inner  # type: ignore[attr-defined]
        self.hotel_box = field(
            form,
            "门店（限同城）",
            self.hotel_var,
            values=list(self.hotel_map),
        )
        self.room_box = field(
            form,
            "房型",
            self.room_var,
            values=self._room_names(order.hotel_id),
        )
        self.room_box.bind("<<ComboboxSelected>>", lambda _: self.refresh_quote())
        self.hotel_box.bind("<<ComboboxSelected>>", lambda _: self.hotel_changed())
        field(form, "入住日期", self.check_in_var)
        field(form, "离店日期", self.check_out_var)
        mobile_button(
            form, "重新计价", self.refresh_quote, primary=False
        ).pack(fill="x", pady=(2, 8))
        tk.Label(
            form,
            textvariable=self.quote_var,
            bg=COLORS["blue_light"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 9),
            justify="left",
            wraplength=320,
            padx=10,
            pady=9,
            anchor="w",
        ).pack(fill="x")
        action = tk.Frame(self, bg=WHITE, height=64,
                          highlightbackground=COLORS["line"], highlightthickness=1)
        action.pack(side="bottom", fill="x")
        action.pack_propagate(False)
        mobile_button(action, "确认修改", self.submit).pack(
            side="right", padx=14, pady=12
        )

    def _room_names(self, hotel_id: str) -> list[str]:
        return [item.name for item in self.services.catalog.room_types(hotel_id)]

    def hotel_changed(self) -> None:
        hotel = self.hotel_map.get(self.hotel_var.get())
        if hotel:
            names = self._room_names(hotel.hotel_id)
            self.room_box.configure(values=names)  # type: ignore[call-arg]
            if names:
                self.room_var.set(names[0])
            self.refresh_quote()

    def _room_id(self, hotel_id: str) -> str:
        for item in self.services.catalog.room_types(hotel_id):
            if item.name == self.room_var.get():
                return item.room_type_id
        raise ValueError("请选择房型")

    def refresh_quote(self) -> None:
        try:
            hotel = self.hotel_map[self.hotel_var.get()]
            room_type_id = self._room_id(hotel.hotel_id)
            check_in = date.fromisoformat(self.check_in_var.get().strip())
            check_out = date.fromisoformat(self.check_out_var.get().strip())
            quote = self.services.booking.quote(
                hotel.hotel_id, room_type_id, check_in, check_out, self.order.qty
            )
            if not quote.is_available:
                self.quote_var.set(f"不可修改：{quote.reason}")
                return
            delta = quote.total - self.order.total_amount
            direction = "补差" if delta > 0 else "退款" if delta < 0 else "无差价"
            self.quote_var.set(
                f"{quote.night_count} 晚 · 新总价 {yuan(quote.total)} · "
                f"{direction} {yuan(abs(delta))}"
            )
        except (ValueError, DomainError) as exc:
            self.quote_var.set(str(exc))

    def submit(self) -> None:
        try:
            hotel = self.hotel_map[self.hotel_var.get()]
            room_type_id = self._room_id(hotel.hotel_id)
            check_in = date.fromisoformat(self.check_in_var.get().strip())
            check_out = date.fromisoformat(self.check_out_var.get().strip())
            result = self.services.booking.modify_order(
                self.order.order_no,
                hotel_id=hotel.hotel_id,
                room_type_id=room_type_id,
                check_in=check_in,
                check_out=check_out,
                guest_phone=self.phone,
            )
        except (ValueError, DomainError) as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.notify(f"修改成功，{(result['order']).status.label}", "success")
        self.app.show_orders(self.phone)


def main() -> None:
    """Start the standalone guest client."""
    services = create_services()
    app = GuestApplication(services)
    app.mainloop()


if __name__ == "__main__":
    main()
