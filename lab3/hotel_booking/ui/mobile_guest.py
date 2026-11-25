"""Standalone portrait guest client built from the experiment-two mockups.

The six designed screens (``lab2/UI界面/界面01`` ... ``界面05`` and ``界面02A``)
are reproduced one-to-one: the same 390 x 844 canvas, the same navigation stack
(城市 → 门店 → 房型 → 详情 → 填单 → 支付 → 订单改退), the same cards, pills and
type scale. Business behaviour is unchanged: the screens still call
``CatalogService`` and ``BookingService`` and every amount comes from a real
quotation, never from a hard-coded sample.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import tkinter as tk

from .. import config
from ..domain.enums import OrderStatus, PayMode
from ..domain.errors import DomainError
from ..domain.models import Hotel, Order, Quote, RoomType, SearchResult
from ..domain.money import ZERO, as_money, mask_phone
from ..services.app import Services, create_services
from .guest_canvas import InfoPopover, MobileCanvas, Sheet, show_confirm, show_options
from .guest_theme import COLORS, FAMILY, HEIGHT, STATUS_COLORS, WIDTH, setup_guest_root
from .guest_theme import font_px

WEEKDAY_LABELS = "一二三四五六日"
TAB_BAR_TOP = 782
TAB_BAR_HEIGHT = 62
DEFAULT_ARRIVAL = "预计 18:00 前"
ARRIVAL_CHOICES = [
    "预计 18:00 前",
    "预计 20:00 前",
    "预计 22:00 前",
    "次日 02:00 前",
]


# ----------------------------------------------------------------------
# Formatting helpers (the mockups never show a trailing ``.00``)
# ----------------------------------------------------------------------
def money(value: Decimal | str | int) -> str:
    """Format an amount the way the mockups do: ``¥2272``."""
    amount = as_money(value)
    text = f"{amount:.2f}"
    if text.endswith(".00"):
        text = text[:-3]
    return "¥" + text


def md(value: date) -> str:
    """Render ``11月14日``."""
    return f"{value.month}月{value.day}日"


def weekday_label(value: date) -> str:
    """Render ``周六``."""
    return "周" + WEEKDAY_LABELS[value.weekday()]


def md_week(value: date) -> str:
    """Render ``11月14日 周六``."""
    return f"{md(value)} {weekday_label(value)}"


def clock(value: datetime) -> str:
    """Render the status-bar clock."""
    return value.strftime("%H:%M")


def short_time(value: datetime | None) -> str:
    """Render the timeline timestamp ``11-10 14:20``."""
    return value.strftime("%m-%d %H:%M") if value else "--"


def countdown_text(deadline: datetime) -> str:
    """Render a remaining window as ``14:32`` (minutes:seconds)."""
    remaining = int((deadline - datetime.now()).total_seconds())
    remaining = max(remaining, 0)
    return f"{remaining // 60:02d}:{remaining % 60:02d}"


def night_rate(quote: Quote) -> Decimal:
    """Average nightly rate used by the detail page headline."""
    nights = quote.night_count or 1
    return as_money(quote.nightly_total / nights)


def stay_nights(check_in: date, check_out: date) -> int:
    """Number of nights of a stay."""
    return max((check_out - check_in).days, 0)


def availability_pill_text(quote: Quote) -> tuple[str, str, str]:
    """Return ``(text, foreground, background)`` of the stock pill."""
    if quote.reason and quote.min_available <= 0:
        return "不可订", COLORS["red"], COLORS["red_bg"]
    if quote.min_available <= 0:
        return "满房", COLORS["red"], COLORS["red_bg"]
    if quote.min_available <= 5:
        return f"仅剩 {quote.min_available} 间", COLORS["amber"], COLORS["amber_bg"]
    return f"剩余 {quote.min_available} 间", COLORS["amber"], COLORS["amber_bg"]


# ----------------------------------------------------------------------
# Shared chrome: status bar, navigation header, bottom tabs
# ----------------------------------------------------------------------
def back_button(canvas: MobileCanvas, command) -> None:  # type: ignore[no-untyped-def]
    """Draw the chevron used by every sub-page."""
    line = canvas.create_line(
        32, 56, 25, 62, 32, 68,
        fill="#FFFFFF", width=2, capstyle="round", joinstyle="round",
    )
    hit = canvas.create_rectangle(12, 44, 46, 80, fill="", outline="")
    canvas.link([line, hit], command)


def draw_header(
    canvas: MobileCanvas,
    height: float,
    *,
    title: str = "",
    subtitle: str = "",
    back=None,  # type: ignore[no-untyped-def]
) -> None:
    """Draw the gradient header of screens 02, 02A, 03, 04 and 05."""
    canvas.gradient(0, 0, WIDTH, height, COLORS["primary"], COLORS["primary_soft"])
    canvas.status_bar(clock(datetime.now()))
    if back is not None:
        back_button(canvas, back)
    if title:
        canvas.text(195, 62, title, 17, "#FFFFFF", True, "n")
    if subtitle:
        canvas.text(195, 88, subtitle, 10, "#C9D6E7", False, "n")


def draw_bottom_tabs(
    canvas: MobileCanvas,
    active: str,
    open_tab,  # type: ignore[no-untyped-def]
    *,
    top: float = TAB_BAR_TOP,
) -> None:
    """Draw the three-tab bar of screen 01 (首页 / 订单 / 我的)."""
    canvas.rect(0, top, WIDTH, TAB_BAR_HEIGHT, "#FFFFFF")
    canvas.line(0, top, WIDTH, top, COLORS["border"])
    items = [("home", "首页"), ("orders", "订单"), ("mine", "我的")]
    for index, (key, label) in enumerate(items):
        center = 65 + index * 130
        color = COLORS["primary"] if key == active else COLORS["faint"]
        icon: list[int] = []
        if key == "home":
            icon.append(
                canvas.create_line(
                    center - 10, top + 25, center, top + 15, center + 10, top + 25,
                    fill=color, width=1.8, capstyle="round", joinstyle="round",
                )
            )
            icon.append(
                canvas.create_line(
                    center - 7, top + 23, center - 7, top + 35,
                    center + 7, top + 35, center + 7, top + 23,
                    fill=color, width=1.8, capstyle="round", joinstyle="round",
                )
            )
        elif key == "orders":
            for step in range(3):
                y = top + 18 + step * 6
                icon.append(
                    canvas.create_line(
                        center - 9, y, center + 9, y, fill=color, width=1.8
                    )
                )
                icon.append(
                    canvas.create_oval(
                        center - 12, y - 1.2, center - 9.6, y + 1.2,
                        fill=color, outline=color,
                    )
                )
        else:
            icon.append(
                canvas.create_oval(
                    center - 4.2, top + 7, center + 4.2, top + 15.4,
                    outline=color, width=1.8,
                )
            )
            icon.append(
                canvas.create_arc(
                    center - 9, top + 14, center + 9, top + 34,
                    start=0, extent=180, style="arc", outline=color, width=1.8,
                )
            )
        text = canvas.text(
            center, top + 43, label, 10, color, key == active, "center"
        )
        hit = canvas.create_rectangle(
            center - 32, top + 8, center + 32, top + 56, fill="", outline=""
        )
        canvas.link([*icon, text, hit], lambda name=key: open_tab(name))


class DateSheet(Sheet):
    """Bottom sheet that adjusts the check-in and check-out dates."""

    def __init__(
        self,
        page: tk.Frame,
        check_in: date,
        check_out: date,
        on_apply,  # type: ignore[no-untyped-def]
        title: str = "选择日期",
    ) -> None:
        self.check_in = check_in
        self.check_out = check_out
        self.on_apply = on_apply
        super().__init__(page, title, 374)

    def build(self) -> None:
        """Redraw the whole sheet after a date change."""
        self.chrome()
        top = self.y
        self._date_row(top, "入住日期", self.check_in, self._shift_in(-1), self._shift_in(1))
        self._date_row(
            top + 86, "离店日期", self.check_out, self._shift_out(-1), self._shift_out(1)
        )
        nights = stay_nights(self.check_in, self.check_out)
        self.c.text(24, top + 172, f"共 {nights} 晚", 10, COLORS["muted"])
        self.c.text(
            24,
            top + 192,
            "入住 14:00 后，退房次日 12:00 前",
            9,
            COLORS["faint"],
        )
        self.primary("确定", self._apply)

    def _date_row(self, top, label, value, minus, plus):  # type: ignore[no-untyped-def]
        self.c.text(24, top + 2, label, 10, COLORS["muted"])
        self.c.text(24, top + 22, md_week(value), 15, COLORS["text"], True)
        self._stepper(WIDTH - 104, top + 14, "−", minus)
        self._stepper(WIDTH - 62, top + 14, "+", plus)

    def _stepper(self, x, y, label, command):  # type: ignore[no-untyped-def]
        self.c.round_fill(x, y, 36, 34, 8, COLORS["border"])
        self.c.round_fill(x + 1, y + 1, 34, 32, 7, COLORS["card"])
        text = self.c.text(x + 18, y + 17, label, 15, COLORS["primary"], True, "center")
        hit = self.c.create_rectangle(x, y, x + 36, y + 34, fill="", outline="")
        self.c.link([text, hit], command)

    def _shift_in(self, delta: int):
        def apply() -> None:
            candidate = self.check_in + timedelta(days=delta)
            if candidate < date.today():
                return
            if candidate >= self.check_out:
                self.check_out = candidate + timedelta(days=1)
            if stay_nights(candidate, self.check_out) > 30:
                return
            self.check_in = candidate
            self.build()

        return apply

    def _shift_out(self, delta: int):
        def apply() -> None:
            candidate = self.check_out + timedelta(days=delta)
            if candidate <= self.check_in:
                return
            if stay_nights(self.check_in, candidate) > 30:
                return
            self.check_out = candidate
            self.build()

        return apply

    def _apply(self) -> None:
        self.on_apply(self.check_in, self.check_out)
        self.close()


class TextSheet(Sheet):
    """Bottom sheet with one text field (guest names, cancellation reason)."""

    def __init__(
        self,
        page: tk.Frame,
        title: str,
        label: str,
        on_submit,  # type: ignore[no-untyped-def]
        *,
        initial: str = "",
    ) -> None:
        self.label = label
        self.on_submit = on_submit
        self.initial = initial
        self.error = ""
        self.variable = tk.StringVar(master=page, value=initial)
        super().__init__(page, title, 300)

    def build(self) -> None:
        """Draw the field, its error line and the submit action."""
        self.chrome()
        top = self.y
        self.c.text(24, top, self.label, 10, COLORS["muted"])
        entry = tk.Entry(
            self.c,
            textvariable=self.variable,
            bd=0,
            relief="flat",
            bg=COLORS["card"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            font=(FAMILY, font_px(13)),
            highlightthickness=0,
        )
        self.c.create_window(
            24, top + 22, window=entry, anchor="nw", width=WIDTH - 48, height=30
        )
        self.c.line(24, top + 56, WIDTH - 24, top + 56, COLORS["border"])
        if self.error:
            self.c.text(24, top + 64, self.error, 10, COLORS["red"])
        entry.focus_set()
        self.primary("确定", self._submit)

    def _submit(self) -> None:
        value = self.variable.get().strip()
        message = self.on_submit(value)
        if message:
            self.error = message
            self.build()
            return
        self.close()


@dataclass
class RoomHold:
    """Client-side room reservation created by 确认下单 on screen 02A."""

    result: SearchResult
    qty: int
    deadline: datetime


# ----------------------------------------------------------------------
# Page base
# ----------------------------------------------------------------------
class GuestPage(tk.Frame):
    """One full-screen page: a canvas plus embedded input widgets."""

    def __init__(self, app: "GuestApplication") -> None:
        super().__init__(app, bg=COLORS["bg"])
        self.app = app
        self.services: Services = app.services
        self.c = MobileCanvas(self, COLORS["bg"])
        self.c.pack()
        self._widgets: list[tk.Widget] = []
        self._timers: list[str] = []
        self.build()

    def build(self) -> None:
        """Render the page; subclasses must override."""
        raise NotImplementedError

    def redraw(self) -> None:
        """Rebuild the page after a state change."""
        self._cancel_timers()
        for widget in self._widgets:
            widget.destroy()
        self._widgets = []
        self.c.delete("all")
        self.build()

    def entry(
        self,
        x: float,
        y: float,
        width: float,
        variable: tk.StringVar,
        *,
        size: int = 13,
        height: float = 26,
        anchor: str = "nw",
    ) -> tk.Entry:
        """Embed a flat entry that blends into a drawn form row."""
        widget = tk.Entry(
            self.c,
            textvariable=variable,
            bd=0,
            relief="flat",
            bg=COLORS["card"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            font=(FAMILY, font_px(size)),
            highlightthickness=0,
        )
        self.c.create_window(x, y, window=widget, anchor=anchor, width=width, height=height)
        self._widgets.append(widget)
        return widget

    def tick(self, callback) -> None:  # type: ignore[no-untyped-def]
        """Schedule the single recurring one-second timer of this page."""
        self._timers = [self.after(1000, callback)]

    def _cancel_timers(self) -> None:
        for job in self._timers:
            try:
                self.after_cancel(job)
            except (tk.TclError, ValueError):
                continue
        self._timers = []

    def destroy(self) -> None:
        """Cancel pending timers before the page disappears."""
        self._cancel_timers()
        super().destroy()


# ----------------------------------------------------------------------
# 01 首页选店
# ----------------------------------------------------------------------
class HomePage(GuestPage):
    """Screen 01: pick a city, pick a hotel, pick dates, preview its rooms."""

    def build(self) -> None:
        """Render the home page from the current search state."""
        app = self.app
        hotel = app.hotel
        canvas = self.c
        canvas.gradient(0, 0, WIDTH, 280, COLORS["primary"], COLORS["primary_soft"])
        canvas.status_bar(clock(datetime.now()))
        canvas.text(24, 60, "云栖酒店 · YUNQI", 11, "#C9D6E7", True)
        canvas.text(24, 82, "挑一家", 27, "#FFFFFF", True)
        canvas.text(24, 116, "想住的酒店", 27, "#FFFFFF", True)
        canvas.text(
            24,
            158,
            f"{app.city} · {len(app.hotels)} 家门店 · 实时房态",
            11,
            "#B9C9DC",
        )

        canvas.card(20, 180, 350, 224, 16)
        city_text = canvas.text(
            38, 196, app.city or "选择城市", 18, COLORS["text"], True
        )
        chevron = canvas.create_line(
            82, 207, 88, 213, 94, 207,
            fill=COLORS["muted"], width=1.6, capstyle="round", joinstyle="round",
        )
        nights = stay_nights(app.check_in, app.check_out)
        guest_text = canvas.text_right(
            332, 200, f"{nights} 晚 · {app.guests} 位", 10, COLORS["muted"]
        )
        canvas.link([guest_text], self._pick_guests)
        canvas.line(38, 232, 352, 232, COLORS["line"])
        canvas.text(38, 246, "入住门店", 9, COLORS["faint"])
        canvas.text(38, 262, hotel.name if hotel else "暂无可订门店", 14, COLORS["text"], True)
        change = canvas.text(352, 264, "更换", 10, COLORS["primary"], False, "ne")
        canvas.line(38, 292, 352, 292, COLORS["line"])
        canvas.text(38, 306, "入住", 9, COLORS["faint"])
        canvas.text(38, 320, md(app.check_in), 14, COLORS["text"], True)
        canvas.text(38, 340, weekday_label(app.check_in), 9, COLORS["muted"])
        canvas.text(176, 318, "→", 14, COLORS["faint"])
        canvas.text(204, 306, "离店", 9, COLORS["faint"])
        canvas.text(204, 320, md(app.check_out), 14, COLORS["text"], True)
        canvas.text(204, 340, weekday_label(app.check_out), 9, COLORS["muted"])
        canvas.button(38, 356, 314, 40, "查看房型", self.app.show_rooms, size=14)
        canvas.link([city_text, chevron], self._pick_city)
        canvas.link([change], self._pick_hotel)
        canvas.link(
            [canvas.create_rectangle(38, 300, 352, 350, fill="", outline="")],
            self._pick_dates,
        )

        short_name = hotel.name.replace("云栖", "") if hotel else ""
        canvas.text(20, 428, f"{short_name} · 房型推荐", 15, COLORS["text"], True)
        rooms = self._recommendations()
        canvas.text_right(370, 434, f"共 {len(self._room_type_count())} 种房型", 9, COLORS["muted"])
        if not rooms:
            canvas.card(20, 456, 350, 96, 12)
            canvas.text(195, 496, "该门店暂无可预订房型", 11, COLORS["muted"], False, "center")
        for index, result in enumerate(rooms[:3]):
            self._room_card(result, 456 + index * 106)
        draw_bottom_tabs(canvas, "home", self.app.open_tab)

    def _room_type_count(self) -> list[RoomType]:
        if not self.app.hotel:
            return []
        return self.services.catalog.room_types(self.app.hotel.hotel_id)

    def _recommendations(self) -> list[SearchResult]:
        hotel = self.app.hotel
        if not hotel:
            return []
        try:
            return self.services.catalog.search(
                check_in=self.app.check_in,
                check_out=self.app.check_out,
                guests=max(1, min(self.app.guests, 3)),
                hotel_id=hotel.hotel_id,
            )
        except DomainError as exc:
            self.app.notify(str(exc), "error")
            return []

    def _room_card(self, result: SearchResult, top: float) -> None:
        canvas = self.c
        quote = result.quote
        canvas.card(20, top, 350, 96, 12)
        canvas.photo(20, top, 76, 96, 12, corners="l")
        canvas.text(108, top + 16, result.room_type.name, 13, COLORS["text"], True)
        canvas.text(
            108, top + 38, result.room_type.short_spec, 9, COLORS["muted"],
            width=190, anchor="nw",
        )
        label, fg, bg = availability_pill_text(quote)
        canvas.pill(108, top + 62, label, 9, fg, bg, 8, 18)
        canvas.text_right(344, top + 20, money(night_rate(quote)), 15, COLORS["red"], True)
        canvas.text_right(344, top + 42, "起 / 晚", 8, COLORS["muted"])
        canvas.bind_area(20, top, 350, 96, lambda item=result: self.app.show_detail(item))

    def _pick_city(self) -> None:
        cities = self.services.catalog.cities()
        options = []
        for city in cities:
            count = len(self.services.catalog.hotels(city=city))
            options.append((city, f"{count} 家门店", lambda value=city: self._choose_city(value)))
        show_options(self, "选择城市", options, current=self.app.city)

    def _choose_city(self, city: str) -> None:
        self.app.city = city
        self.app.hotels = self.services.catalog.hotels(city=city)
        self.app.hotel = self.app.hotels[0] if self.app.hotels else None
        self.redraw()

    def _pick_hotel(self) -> None:
        options = []
        for hotel in self.app.hotels:
            options.append(
                (
                    hotel.name,
                    f"{hotel.district} · {hotel.type_label}",
                    lambda value=hotel: self._choose_hotel(value),
                )
            )
        show_options(self, "选择门店", options, current=self.app.hotel.name if self.app.hotel else "")

    def _choose_hotel(self, hotel: Hotel) -> None:
        self.app.hotel = hotel
        self.redraw()

    def _pick_guests(self) -> None:
        options = [
            (
                f"{count} 位",
                "按可住人数筛选房型",
                lambda value=count: self._choose_guests(value),
            )
            for count in range(1, 7)
        ]
        show_options(
            self, "选择入住人数", options, current=f"{self.app.guests} 位"
        )

    def _choose_guests(self, count: int) -> None:
        self.app.guests = count
        self.redraw()

    def _pick_dates(self) -> None:
        DateSheet(self, self.app.check_in, self.app.check_out, self._choose_dates)

    def _choose_dates(self, check_in: date, check_out: date) -> None:
        self.app.check_in = check_in
        self.app.check_out = check_out
        self.redraw()


# ----------------------------------------------------------------------
# 02 选房型
# ----------------------------------------------------------------------
class RoomListPage(GuestPage):
    """Screen 02: compare room types of the chosen hotel, without totals."""

    def __init__(self, app: "GuestApplication") -> None:
        self.only_breakfast = False
        self.only_king = False
        super().__init__(app)

    def build(self) -> None:
        """Render the hotel header, date bar, filter chips and room cards."""
        app = self.app
        hotel = app.hotel
        canvas = self.c
        assert hotel is not None
        canvas.gradient(0, 0, WIDTH, 168, COLORS["primary"], COLORS["primary_soft"])
        canvas.status_bar(clock(datetime.now()))
        back_button(canvas, app.show_home)
        canvas.text(195, 62, hotel.name, 17, "#FFFFFF", True, "n")
        canvas.text(195, 88, hotel.full_address, 10, "#C9D6E7", False, "n")
        for index in range(hotel.star):
            canvas.star(171 + index * 13, 108, 11)
        canvas.text(242, 108, f"{float(hotel.rating):.1f} / 5", 10, "#E8D9A8")

        canvas.card(16, 146, 358, 56, 12)
        canvas.text(30, 160, md_week(app.check_in), 12, COLORS["text"], True)
        canvas.text(180, 164, "→", 14, COLORS["faint"])
        canvas.text(206, 160, md_week(app.check_out), 12, COLORS["text"], True)
        canvas.text(30, 180, f"{stay_nights(app.check_in, app.check_out)} 晚", 10, COLORS["muted"])
        modify = canvas.text(344, 170, "修改", 11, COLORS["primary"], False, "ne")
        canvas.link([modify], self._pick_dates)

        results = self._filtered()
        chips = [("含早", self.only_breakfast), ("大床", self.only_king), ("可取消", False)]
        x = 16.0
        for label, active in chips:
            width = canvas.pill(
                x, 218, label, 10,
                "#FFFFFF" if active else COLORS["primary"],
                COLORS["primary"] if active else COLORS["blue_bg"],
                9, 24,
            )
            handler = (
                self._toggle_breakfast if label == "含早"
                else self._toggle_king if label == "大床"
                else self._noop
            )
            hit = canvas.create_rectangle(x, 218, x + width, 242, fill="", outline="")
            canvas.link([hit], handler)
            x += width + 8
        canvas.text_right(370, 226, f"{len(results)} 种房型", 10, COLORS["muted"])

        for index, result in enumerate(results[:3]):
            self._room_card(result, 258 + index * 176)
        if not results:
            canvas.card(16, 258, 358, 160, 14)
            canvas.text(195, 320, "没有符合条件的房型", 13, COLORS["text"], True, "center")
            canvas.text(195, 344, "试试取消筛选或修改日期", 10, COLORS["muted"], False, "center")
        canvas.text(195, 796, "价格为每晚起价，点选房型查看详情", 9, COLORS["faint"], False, "n")

    def _filtered(self) -> list[SearchResult]:
        hotel = self.app.hotel
        assert hotel is not None
        try:
            results = self.services.catalog.search(
                check_in=self.app.check_in,
                check_out=self.app.check_out,
                guests=max(1, self.app.guests),
                hotel_id=hotel.hotel_id,
            )
        except DomainError as exc:
            self.app.notify(str(exc), "error")
            return []
        if self.only_breakfast:
            results = [item for item in results if item.room_type.breakfast]
        if self.only_king:
            results = [item for item in results if "大床" in item.room_type.bed_type]
        return results

    def _room_card(self, result: SearchResult, top: float) -> None:
        canvas = self.c
        quote = result.quote
        canvas.card(16, top, 358, 160, 14)
        canvas.photo(16, top, 100, 160, 14, corners="l")
        canvas.text(132, top + 14, result.room_type.name, 16, COLORS["text"], True)
        canvas.text(
            132, top + 40, result.room_type.short_spec, 10, COLORS["muted"], width=210
        )
        label, fg, bg = availability_pill_text(quote)
        width = canvas.pill(132, top + 60, label, 9, fg, bg, 6, 18)
        canvas.pill(
            132 + width + 10, top + 60, "可取消", 9,
            COLORS["green"], COLORS["green_bg"], 6, 18,
        )
        rate = night_rate(quote)
        canvas.text(132, top + 94, "¥", 10, COLORS["red"])
        canvas.text(142, top + 86, f"{rate:.0f}", 22, COLORS["red"], True)
        rate_width = canvas.measure(f"{rate:.0f}", 22, True)
        canvas.text(142 + rate_width + 4, top + 97, "起/晚", 9, COLORS["muted"])
        canvas.chevron(350, top + 74)
        canvas.bind_area(16, top, 358, 160, lambda item=result: self.app.show_detail(item))

    def _toggle_breakfast(self) -> None:
        self.only_breakfast = not self.only_breakfast
        self.redraw()

    def _toggle_king(self) -> None:
        self.only_king = not self.only_king
        self.redraw()

    def _noop(self) -> None:
        self.app.notify("所有房型均支持入住前 24 小时免费取消")

    def _pick_dates(self) -> None:
        DateSheet(self, self.app.check_in, self.app.check_out, self._choose_dates)

    def _choose_dates(self, check_in: date, check_out: date) -> None:
        self.app.check_in = check_in
        self.app.check_out = check_out
        self.redraw()


# ----------------------------------------------------------------------
# 02A 房型详情
# ----------------------------------------------------------------------
class RoomDetailPage(GuestPage):
    """Screen 02A: choose the room quantity, check the breakdown, lock rooms."""

    def __init__(self, app: "GuestApplication", result: SearchResult, qty: int = 1) -> None:
        self.result = result
        self.quote = app.services.booking.quote(
            result.hotel.hotel_id,
            result.room_type.room_type_id,
            result.quote.check_in,
            result.quote.check_out,
            max(1, qty),
        )
        super().__init__(app)

    @property
    def max_qty(self) -> int:
        """Largest quantity the current stock allows."""
        return max(1, min(self.quote.min_available, 9))

    def build(self) -> None:
        """Render the photo header, rate, stepper, breakdown and booking bar."""
        canvas = self.c
        quote = self.quote
        room = self.result.room_type
        hotel = self.result.hotel
        canvas.gradient(0, 0, WIDTH, 96, COLORS["primary"], COLORS["primary_soft"])
        canvas.status_bar(clock(datetime.now()))
        back_button(canvas, self.app.show_rooms)
        canvas.text(195, 62, "房型详情", 17, "#FFFFFF", True, "n")
        canvas.photo(0, 96, WIDTH, 180, 0)
        canvas.pill(308, 240, f"{room.area_sqm}㎡", 9, COLORS["text"], "#FFFFFF", 10, 20)

        canvas.rect(0, 276, WIDTH, 506, COLORS["card"])
        canvas.text(24, 288, room.name, 22, COLORS["text"], True)
        spec = f"{room.bed_type} · {room.breakfast_label} · 可取消"
        canvas.text(24, 322, spec, 10, COLORS["muted"])
        rate = night_rate(quote)
        canvas.text(24, 346, "¥", 12, COLORS["red"])
        canvas.text(34, 338, f"{rate:.0f}", 30, COLORS["red"], True)
        rate_width = canvas.measure(f"{rate:.0f}", 30, True)
        canvas.text(34 + rate_width + 4, 354, "/晚", 10, COLORS["muted"])
        label, fg, bg = availability_pill_text(quote)
        canvas.pill_right(370, 344, label, 9, fg, bg, 6, 20)

        canvas.line(16, 384, 374, 384, COLORS["line"])
        canvas.text(24, 396, "入住日期", 9, COLORS["faint"])
        canvas.text(
            24, 412,
            f"{md(quote.check_in)} - {md(quote.check_out)} · {quote.night_count} 晚",
            13, COLORS["text"], True,
        )
        modify = canvas.text(344, 398, "修改", 10, COLORS["primary"], False, "ne")
        canvas.link([modify], self._pick_dates)

        canvas.line(16, 446, 374, 446, COLORS["line"])
        canvas.text(24, 458, "间数", 13, COLORS["text"], True)
        canvas.text(24, 480, f"最多 {self.max_qty} 间", 9, COLORS["muted"])
        self._stepper(256, 454, "−", COLORS["card"], COLORS["border"], COLORS["primary"], self._dec)
        self._stepper(
            290, 454, str(quote.qty),
            COLORS["card"], COLORS["border"], COLORS["text"], None,
        )
        self._stepper(
            324, 454, "+",
            COLORS["blue_bg"], COLORS["primary"], COLORS["primary"], self._inc,
        )

        canvas.card(16, 520, 358, 118, 12, COLORS["bg"], shadow=False)
        canvas.text(32, 534, "价格明细", 12, COLORS["text"], True)
        if quote.night_count and len({night.unit_price for night in quote.nights}) == 1:
            fee_label = f"房费（¥{rate:.0f} × {quote.night_count} 晚 × {quote.qty} 间）"
        else:
            fee_label = f"房费（{quote.night_count} 晚 · 均价 ¥{rate:.0f} × {quote.qty} 间）"
        canvas.text(32, 560, fee_label, 10, COLORS["muted"])
        canvas.text_right(358, 560, money(quote.total), 10, COLORS["text"])
        canvas.text(32, 582, "服务费", 10, COLORS["muted"])
        canvas.text_right(358, 582, "¥0", 10, COLORS["text"])
        canvas.line(32, 600, 358, 600, COLORS["border"])
        canvas.text(32, 608, "合计", 11, COLORS["text"], True)
        canvas.text_right(358, 604, money(quote.total), 18, COLORS["red"], True)

        canvas.card(16, 654, 358, 86, 12, COLORS["blue_bg"], shadow=False)
        canvas.text(32, 668, "预订须知", 11, COLORS["primary"], True)
        canvas.text(32, 686, "入住 14:00 后 · 退房次日 12:00 前", 9, COLORS["muted"])
        canvas.text(32, 702, "入住前 24 小时可免费取消，之后扣首晚房费", 9, COLORS["muted"])
        canvas.text(32, 720, "需要其他房型？请分开下单", 9, COLORS["amber"])

        canvas.rect(0, 782, WIDTH, 62, COLORS["card"])
        canvas.line(0, 782, WIDTH, 782, COLORS["border"])
        canvas.text(20, 790, "合计", 9, COLORS["muted"])
        canvas.text(20, 804, money(quote.total), 20, COLORS["red"], True)
        canvas.button(
            220, 794, 150, 42,
            "确认下单" if quote.is_available else "当前不可订",
            self._confirm, size=14, enabled=quote.is_available,
        )

    def _stepper(
        self,
        x: float,
        y: float,
        label: str,
        fill: str,
        outline: str,
        fg: str,
        command,  # type: ignore[no-untyped-def]
    ) -> None:
        canvas = self.c
        canvas.round_fill(x, y, 32, 32, 8, outline)
        canvas.round_fill(x + 1.2, y + 1.2, 29.6, 29.6, 7, fill)
        text = canvas.text(x + 16, y + 16, label, 14, fg, True, "center")
        if command is not None:
            hit = canvas.create_rectangle(x, y, x + 32, y + 32, fill="", outline="")
            canvas.link([text, hit], command)

    def _reprice(self, qty: int) -> None:
        self.quote = self.app.services.booking.quote(
            self.result.hotel.hotel_id,
            self.result.room_type.room_type_id,
            self.quote.check_in,
            self.quote.check_out,
            max(1, min(qty, self.max_qty)),
        )

    def _inc(self) -> None:
        if self.quote.qty >= self.max_qty:
            self.app.notify(f"该房型最多可订 {self.max_qty} 间")
            return
        self._reprice(self.quote.qty + 1)
        self.redraw()

    def _dec(self) -> None:
        if self.quote.qty <= 1:
            return
        self._reprice(self.quote.qty - 1)
        self.redraw()

    def _pick_dates(self) -> None:
        DateSheet(self, self.quote.check_in, self.quote.check_out, self._choose_dates)

    def _choose_dates(self, check_in: date, check_out: date) -> None:
        quote = self.app.services.booking.quote(
            self.result.hotel.hotel_id,
            self.result.room_type.room_type_id,
            check_in,
            check_out,
            self.quote.qty,
        )
        self.quote = quote
        if not quote.is_available and quote.qty > 1:
            self._reprice(1)
        self.redraw()

    def _confirm(self) -> None:
        if not self.quote.is_available:
            self.app.notify(self.quote.reason or "所选房型不可预订", "error")
            return
        self.app.start_booking(self.result, self.quote.qty)


# ----------------------------------------------------------------------
# 03 填写订单（锁房倒计时）
# ----------------------------------------------------------------------
class BookingPage(GuestPage):
    """Screen 03: fill the guest form inside the 15-minute lock window."""

    def __init__(self, app: "GuestApplication", hold: RoomHold) -> None:
        self.hold = hold
        self.name_var = tk.StringVar(master=app, value=app.last_name)
        self.phone_var = tk.StringVar(master=app, value=app.last_phone)
        self.arrival = DEFAULT_ARRIVAL
        self.guests: list[str] = []
        self.expired = False
        self.countdown_id: int | None = None
        self.expired_notified = False
        super().__init__(app)

    def build(self) -> None:
        """Render the countdown, lock banner, guest form and order summary."""
        canvas = self.c
        quote = self._quote()
        result = self.hold.result
        room = result.room_type

        canvas.gradient(0, 0, WIDTH, 108, COLORS["primary"], COLORS["primary_soft"])
        canvas.status_bar(clock(datetime.now()))
        back_button(canvas, lambda: self.app.show_detail(result, self.hold.qty))
        canvas.text(195, 62, "填写订单", 17, "#FFFFFF", True, "n")
        self.countdown_id = self._countdown_pill(countdown_text(self.hold.deadline))
        self.banner_id: int | None = None
        self._banner()

        canvas.card(16, 170, 358, 232, 14)
        canvas.text(32, 188, "入住人信息", 14, COLORS["text"], True)
        canvas.text_right(358, 190, f"{quote.qty} 间房", 10, COLORS["muted"])
        canvas.text(32, 218, "姓名", 10, COLORS["faint"])
        self.entry(32, 234, 326, self.name_var)
        canvas.line(32, 262, 358, 262, COLORS["line"])
        canvas.text(32, 268, "手机号", 10, COLORS["faint"])
        self.entry(32, 284, 326, self.phone_var)
        canvas.line(32, 312, 358, 312, COLORS["line"])
        canvas.text(32, 318, "到店时间", 10, COLORS["faint"])
        canvas.text(32, 334, self.arrival, 13, COLORS["text"])
        canvas.bind_area(32, 318, 326, 34, self._pick_arrival)
        canvas.line(32, 362, 358, 362, COLORS["line"])
        remaining_guests = max(quote.qty - 1 - len(self.guests), 0)
        if remaining_guests:
            add = canvas.text(
                32, 376, f"+ 添加入住人（还需 {remaining_guests} 位）", 11, COLORS["primary"]
            )
            canvas.link([add], self._add_guest)
        else:
            canvas.text(32, 376, f"已登记 {len(self.guests) + 1} 位入住人", 11, COLORS["muted"])

        canvas.card(16, 418, 358, 236, 14)
        canvas.text(32, 436, "订单信息", 14, COLORS["text"], True)
        canvas.photo(32, 460, 56, 56, 8, decor=False)
        canvas.text(100, 464, room.name, 13, COLORS["text"], True)
        canvas.text(
            100, 484, f"{md(quote.check_in)} - {md(quote.check_out)} · {quote.night_count} 晚",
            10, COLORS["muted"],
        )
        canvas.text(
            100, 500,
            f"{room.breakfast_label} · 可取消 · {quote.qty} 间",
            10, COLORS["muted"],
        )
        canvas.line(32, 528, 358, 528, COLORS["line"])
        rows = [
            (f"房费（{quote.night_count} 晚 × {quote.qty} 间）", money(quote.total)),
            ("服务费", "¥0"),
            ("优惠", "-¥0"),
        ]
        for index, (label, value) in enumerate(rows):
            y = 540 + index * 22
            canvas.text(32, y, label, 11, COLORS["muted"])
            canvas.text_right(358, y, value, 11, COLORS["text"])
        canvas.line(32, 606, 358, 606, COLORS["line"])
        canvas.text(32, 620, "应付总额", 12, COLORS["text"], True)
        canvas.text_right(358, 614, money(quote.total), 18, COLORS["red"], True)

        canvas.card(16, 670, 358, 84, 12, COLORS["blue_bg"], shadow=False)
        canvas.text(32, 684, "预订须知", 11, COLORS["primary"], True)
        canvas.text(32, 704, "入住 14:00 后 · 退房次日 12:00 前", 9, COLORS["muted"])
        canvas.text(32, 720, "免费取消以订单取消规则为准", 9, COLORS["muted"])
        canvas.text(32, 736, "到店请出示入住人身份证件", 9, COLORS["muted"])

        canvas.rect(0, 770, WIDTH, 74, COLORS["card"])
        canvas.line(0, 770, WIDTH, 770, COLORS["border"])
        canvas.text(20, 786, money(quote.total), 20, COLORS["red"], True)
        canvas.text(20, 810, "含税总价", 9, COLORS["muted"])
        if self.expired:
            canvas.button(220, 784, 150, 44, "重新选房", self._restart, size=15)
        else:
            canvas.button(220, 784, 150, 44, "去支付", self._submit, size=15)

        self.tick(self._tick)

    def _quote(self) -> Quote:
        quote = self.hold.result.quote
        return self.app.services.booking.quote(
            self.hold.result.hotel.hotel_id,
            self.hold.result.room_type.room_type_id,
            quote.check_in,
            quote.check_out,
            self.hold.qty,
        )

    def _countdown_pill(self, text: str) -> int:
        canvas = self.c
        width = canvas.measure(text, 11, True) + 20
        x = 366 - width
        canvas.round_fill(x, 50, width, 24, 12, "#8FA6C4")
        canvas.round_fill(x + 1, 51, width - 2, 22, 11, "#3A5A82")
        return canvas.text(x + width / 2, 62, text, 11, "#FFFFFF", True, "center")

    def _banner(self) -> None:
        canvas = self.c
        if self.expired:
            canvas.rect(0, 108, WIDTH, 46, COLORS["red_bg"])
            canvas.text(20, 121, "锁房已释放，请重新选择房型", 11, COLORS["red"])
            canvas.text_right(370, 121, "已失效", 10, COLORS["red"])
            return
        canvas.rect(0, 108, WIDTH, 46, COLORS["gold_soft"])
        self.banner_id = canvas.text(
            20, 121,
            f"房源已为你锁定，{countdown_text(self.hold.deadline)} 后自动释放",
            11, "#8A6A12",
        )
        canvas.text_right(370, 121, "倒计时", 10, "#8A6A12")

    def _tick(self) -> None:
        if self.expired:
            return
        remaining = (self.hold.deadline - datetime.now()).total_seconds()
        if remaining <= 0:
            self.expired = True
            self.redraw()
            if not self.expired_notified:
                self.expired_notified = True
                self.app.notify("锁房已释放，请重新选择房型", "error")
            return
        if self.countdown_id is not None:
            self.c.itemconfigure(self.countdown_id, text=countdown_text(self.hold.deadline))
        if self.banner_id is not None:
            self.c.itemconfigure(
                self.banner_id,
                text=f"房源已为你锁定，{countdown_text(self.hold.deadline)} 后自动释放",
            )
        self.tick(self._tick)

    def _pick_arrival(self) -> None:
        options = [
            (choice, "", lambda value=choice: self._choose_arrival(value))
            for choice in ARRIVAL_CHOICES
        ]
        show_options(self, "选择到店时间", options, current=self.arrival)

    def _choose_arrival(self, value: str) -> None:
        self.arrival = value
        self.redraw()

    def _add_guest(self) -> None:
        TextSheet(self, "添加入住人", "入住人姓名", self._save_guest)

    def _save_guest(self, value: str) -> str:
        if len(value) < 2 or len(value) > 20:
            return "姓名须为 2 至 20 个字符"
        quote = self._quote()
        if len(self.guests) + 1 >= quote.qty:
            return f"本单 {quote.qty} 间房，入住人已登记完整"
        self.guests.append(value)
        self.redraw()
        return ""

    def _restart(self) -> None:
        self.app.show_detail(self.hold.result, self.hold.qty)

    def _submit(self) -> None:
        if self.expired:
            self.app.notify("锁房已释放，请重新选择房型", "error")
            return
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        try:
            order = self.services.booking.create_order(
                guest_name=name,
                phone=phone,
                hotel_id=self.hold.result.hotel.hotel_id,
                room_type_id=self.hold.result.room_type.room_type_id,
                check_in=self.hold.result.quote.check_in,
                check_out=self.hold.result.quote.check_out,
                qty=self.hold.qty,
                pay_mode=PayMode.ONLINE,
                arrival_time=self.arrival,
                guests=self.guests,
            )
        except (DomainError, ValueError) as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.last_name = name
        self.app.last_phone = phone
        self.app.show_payment(order.order_no)


# ----------------------------------------------------------------------
# 04 支付
# ----------------------------------------------------------------------
class PaymentPage(GuestPage):
    """Screen 04: settle the pending order with one of the three channels."""

    METHODS = [
        ("微信支付", "推荐使用", "WECHAT", "微", COLORS["green"], COLORS["green_bg"]),
        ("支付宝", "", "ALIPAY", "支", COLORS["primary"], COLORS["blue_bg"]),
        ("银行卡", "储蓄卡 / 信用卡", "CARD", "银", COLORS["primary"], COLORS["blue_bg"]),
    ]

    def __init__(self, app: "GuestApplication", order_no: str) -> None:
        self.order_no = order_no
        self.method = "WECHAT"
        self.countdown_id: int | None = None
        self.expired = False
        super().__init__(app)

    def build(self) -> None:
        """Render the amount, payment channels, summary and pay bar."""
        order = self._order()
        if order is None:
            self._missing_order()
            return
        room = self.services.catalog.room_type(order.room_type_id)
        canvas = self.c
        canvas.gradient(0, 0, WIDTH, 110, COLORS["primary"], COLORS["primary_soft"])
        canvas.status_bar(clock(datetime.now()))
        back_button(canvas, lambda: self.app.show_order_detail(order, order.contact_phone))
        canvas.text(195, 62, "收银台", 17, "#FFFFFF", True, "n")
        deadline = order.expire_at or datetime.now()
        self.countdown_id = self._countdown_pill(countdown_text(deadline))

        canvas.card(16, 128, 358, 104, 14)
        canvas.text(32, 146, "待支付金额", 11, COLORS["muted"])
        canvas.text(32, 164, money(order.total_amount), 30, COLORS["red"], True)
        canvas.text(
            32, 202,
            f"订单号 {order.order_no} · {order.nights} 晚 {order.qty} 间",
            10, COLORS["muted"],
        )

        canvas.text(20, 254, "选择支付方式", 14, COLORS["text"], True)
        for index, (name, desc, code, glyph, fg, bg) in enumerate(self.METHODS):
            top = 282 + index * 76
            selected = self.method == code
            canvas.card(
                16, top, 358, 64, 12,
                outline=COLORS["primary"] if selected else COLORS["border"],
                width=2 if selected else 1,
            )
            canvas.create_oval(27, top + 17, 57, top + 47, fill=bg, outline=bg)
            canvas.text(42, top + 32, glyph, 13, fg, True, "center")
            canvas.text(66, top + 18, name, 13, COLORS["text"], True)
            if desc:
                canvas.text(66, top + 38, desc, 9, COLORS["muted"])
            canvas.create_oval(
                333, top + 23, 351, top + 41,
                outline=COLORS["primary"] if selected else COLORS["border"],
                width=1.4,
            )
            if selected:
                canvas.create_oval(
                    338, top + 28, 346, top + 36,
                    fill=COLORS["primary"], outline=COLORS["primary"],
                )
            canvas.bind_area(16, top, 358, 64, lambda value=code: self._choose(value))

        canvas.card(16, 522, 358, 56, 12, COLORS["blue_bg"], shadow=False)
        canvas.text(32, 536, "支付安全", 11, COLORS["primary"], True)
        canvas.text(32, 552, "支付由持牌机构处理，云栖不留存银行卡信息", 9, COLORS["muted"])

        canvas.card(16, 594, 358, 150, 14)
        canvas.text(32, 610, "订单摘要", 12, COLORS["text"], True)
        canvas.text_right(358, 612, f"{order.nights} 晚 {order.qty} 间", 9, COLORS["muted"])
        canvas.text(32, 636, f"{order.room_type_name} · {room.breakfast_label}", 11, COLORS["text"])
        canvas.text(32, 658, f"{md(order.check_in)} - {md(order.check_out)}", 10, COLORS["muted"])
        canvas.text(32, 680, f"入住人 {order.contact_name}", 10, COLORS["muted"])
        canvas.line(32, 702, 358, 702, COLORS["line"])
        canvas.text(32, 714, "房费合计", 10, COLORS["muted"])
        canvas.text_right(358, 712, money(order.total_amount), 16, COLORS["red"], True)

        canvas.rect(0, 770, WIDTH, 74, COLORS["card"])
        canvas.line(0, 770, WIDTH, 770, COLORS["border"])
        canvas.text(20, 786, "实付", 10, COLORS["muted"])
        canvas.text(20, 800, money(order.total_amount), 20, COLORS["red"], True)
        canvas.button(
            220, 784, 150, 44, "确认支付" if not self.expired else "订单已超时",
            self._pay, size=15, enabled=not self.expired,
        )
        self.tick(self._tick)

    def _order(self) -> Order | None:
        try:
            return self.services.order_repo.require(self.order_no)
        except DomainError:
            return None

    def _missing_order(self) -> None:
        """Show a friendly state instead of navigating during construction."""
        canvas = self.c
        draw_header(canvas, 110, title="收银台", back=self.app.show_orders)
        canvas.card(16, 160, 358, 190, 14)
        canvas.text(195, 210, "订单不存在或已被释放", 14, COLORS["text"], True, "center")
        canvas.text(195, 242, "库存已释放，请返回订单列表重新选择", 10, COLORS["muted"], False, "center")
        canvas.button(40, 280, WIDTH - 80, 44, "返回订单列表", self.app.show_orders, size=14)

    def _countdown_pill(self, text: str) -> int:
        canvas = self.c
        width = canvas.measure(text, 11, True) + 20
        x = 366 - width
        canvas.round_fill(x, 50, width, 24, 12, "#8FA6C4")
        canvas.round_fill(x + 1, 51, width - 2, 22, 11, "#3A5A82")
        return canvas.text(x + width / 2, 62, text, 11, "#FFFFFF", True, "center")

    def _tick(self) -> None:
        if self.expired:
            return
        order = self.services.order_repo.get(self.order_no)
        if order is None or order.expire_at is None:
            return
        if order.expire_at <= datetime.now():
            self.expired = True
            self.redraw()
            self.app.notify("订单支付超时，将在库存释放后自动取消", "error")
            return
        if self.countdown_id is not None:
            self.c.itemconfigure(self.countdown_id, text=countdown_text(order.expire_at))
        self.tick(self._tick)

    def _choose(self, method: str) -> None:
        if self.expired:
            return
        self.method = method
        self.redraw()

    def _pay(self) -> None:
        if self.expired:
            return
        try:
            paid = self.services.booking.pay_order(self.order_no, method=self.method)
        except DomainError as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.show_order_detail(paid, paid.contact_phone)
        self.app.notify("支付成功，订单已确认", "success")


# ----------------------------------------------------------------------
# 05 订单改退
# ----------------------------------------------------------------------
class OrderDetailPage(GuestPage):
    """Screen 05: status, timeline, cancellation rules and self-service."""

    def __init__(self, app: "GuestApplication", order_no: str, phone: str = "") -> None:
        self.order_no = order_no
        self.phone = phone
        super().__init__(app)

    def build(self) -> None:
        """Render the order detail from a freshly loaded aggregate."""
        order = self.services.order_repo.get(self.order_no)
        if order is None:
            self._missing_order()
            return
        self.order = order
        room = self.services.catalog.room_type(order.room_type_id)
        hotel = self.services.catalog.hotel(order.hotel_id)
        canvas = self.c
        canvas.gradient(0, 0, WIDTH, 160, COLORS["primary"], COLORS["primary_soft"])
        canvas.status_bar(clock(datetime.now()))
        back_button(canvas, lambda: self.app.show_orders(self.phone))
        canvas.text(195, 62, "订单详情", 17, "#FFFFFF", True, "n")

        canvas.card(16, 120, 358, 132, 14)
        status_color = STATUS_COLORS.get(order.status.value, COLORS["muted"])
        canvas.text(32, 138, order.status.label, 16, status_color, True)
        canvas.pill_right(
            340, 136, f"{order.nights} 晚 {order.qty} 间", 9,
            COLORS["primary"], COLORS["blue_bg"], 7, 20,
        )
        canvas.text(32, 168, f"订单号 {order.order_no}", 10, COLORS["muted"])
        canvas.text(
            32, 190,
            f"{md(order.check_in)} - {md(order.check_out)}",
            14, COLORS["text"], True,
        )
        canvas.text(32, 216, hotel.name if hotel else order.hotel_name, 11, COLORS["muted"])

        canvas.card(16, 268, 358, 142, 14)
        canvas.photo(32, 286, 72, 72, 8, decor=False)
        canvas.text(116, 288, f"{order.room_type_name} · {order.qty} 间", 13, COLORS["text"], True)
        canvas.text(116, 310, room.short_spec, 10, COLORS["muted"])
        canvas.text(116, 330, f"入住人：{order.guests_label}", 10, COLORS["muted"])
        canvas.text(116, 348, f"到店时间：{order.arrival_time or DEFAULT_ARRIVAL}", 10, COLORS["muted"])
        canvas.text(32, 380, money(order.total_amount), 16, COLORS["red"], True)
        paid = self._is_paid(order)
        canvas.text(
            32 + canvas.measure(money(order.total_amount), 16, True) + 8,
            386,
            "已支付" if paid else "待支付",
            9, COLORS["green"] if paid else COLORS["amber"],
        )

        canvas.text(20, 432, "订单进度", 13, COLORS["text"], True)
        self._timeline(order, paid)

        self._rules(order)

        if order.status is OrderStatus.PENDING_PAYMENT and order.pay_mode is PayMode.ONLINE:
            canvas.button(16, 714, 172, 42, "去支付", self._pay, size=13,
                          fill=COLORS["card"], fg=COLORS["primary"],
                          outline=COLORS["primary"], outline_width=1)
        else:
            canvas.button(
                16, 714, 172, 42, "修改订单",
                lambda: self.app.show_modify(order, self.phone),
                size=13, fill=COLORS["card"],
                fg=COLORS["primary"] if order.can_modify else COLORS["faint"],
                outline=COLORS["border"], outline_width=1, enabled=order.can_modify,
            )
        canvas.button(
            202, 714, 172, 42, "取消订单", self._cancel,
            size=13, fill=COLORS["card"],
            fg=COLORS["red"] if order.can_cancel else COLORS["faint"],
            outline=COLORS["red"] if order.can_cancel else COLORS["border"],
            outline_width=1, enabled=order.can_cancel,
        )
        canvas.button(
            16, 772, 172, 40, "联系酒店", self._contact_hotel,
            size=12, fill=COLORS["blue_bg"], fg=COLORS["primary"],
        )
        canvas.button(
            202, 772, 172, 40, "在线客服", self._service,
            size=12, fill=COLORS["blue_bg"], fg=COLORS["primary"],
        )

    def _is_paid(self, order: Order) -> bool:
        payments = self.services.order_repo.list_payments(order.order_no)
        return any(payment.paid_at for payment in payments)

    def _missing_order(self) -> None:
        """Show a friendly state when the order row no longer exists."""
        canvas = self.c
        draw_header(
            canvas, 160, title="订单详情",
            back=lambda: self.app.show_orders(self.phone),
        )
        canvas.card(16, 190, 358, 190, 14)
        canvas.text(195, 240, "订单不存在", 14, COLORS["text"], True, "center")
        canvas.text(195, 272, "订单可能已被取消或数据已归档", 10, COLORS["muted"], False, "center")
        canvas.button(
            40, 310, WIDTH - 80, 44, "返回订单列表",
            lambda: self.app.show_orders(self.phone), size=14,
        )

    def _timeline(self, order: Order, paid: bool) -> None:
        canvas = self.c
        payments = self.services.order_repo.list_payments(order.order_no)
        paid_at = next((payment.paid_at for payment in payments if payment.paid_at), None)
        steps: list[tuple[str, str, bool]] = [("提交订单", short_time(order.created_at), True)]
        if paid_at:
            steps.append(("支付成功", short_time(paid_at), True))
        elif order.status is OrderStatus.PENDING_PAYMENT:
            steps.append(("等待支付", "请在倒计时内完成支付", False))
        if order.status is OrderStatus.CONFIRMED:
            steps.append(("等待入住", f"{md(order.check_in)} 14:00 后", False))
        elif order.status is OrderStatus.CHECKED_IN:
            rooms = order.assigned_rooms or "待分配"
            steps.append(("已入住", f"{rooms} · {md(order.check_in)}", True))
        elif order.status is OrderStatus.CHECKED_OUT:
            steps.append(("正常离店", short_time(order.updated_at), True))
        elif order.status is OrderStatus.CANCELLED:
            steps.append(("订单已取消", short_time(order.updated_at), True))
        elif order.status is OrderStatus.NO_SHOW:
            steps.append(("客人未到店", short_time(order.updated_at), True))
        elif order.status is OrderStatus.EXCEPTION:
            steps.append(("异常处理中", "门店正在处理，请留意客服来电", False))

        y = 462.0
        for index, (name, when, done) in enumerate(steps):
            color = COLORS["green"] if done else COLORS["border"]
            canvas.create_oval(27, y, 37, y + 10, fill=color, outline=color)
            if index < len(steps) - 1:
                canvas.line(32, y + 12, 32, y + 40, COLORS["border"], 1.5)
            canvas.text(48, y - 3, name, 11, COLORS["text"], done)
            canvas.text(48, y + 15, when, 9, COLORS["muted"])
            y += 44

    def _rules(self, order: Order) -> None:
        canvas = self.c
        penalty = as_money(order.first_night_amount * order.active_qty)
        free_until = datetime.combine(order.check_in, time.min) - timedelta(hours=24)
        specials = {item.biz_date for item in self.services.catalog.special_dates()}
        is_special = any(
            order.check_in + timedelta(days=offset) in specials
            for offset in range(order.nights)
        )
        canvas.card(16, 594, 358, 104, 14, COLORS["amber_bg"], shadow=False)
        canvas.text(32, 610, "取消规则", 11, COLORS["amber"], True)
        if is_special:
            canvas.text(32, 630, "所选日期为特殊日期（节假日/展会），", 10, "#7A5A10")
            canvas.text(32, 648, f"取消扣首晚房费 {money(penalty)}（{order.active_qty} 间）。", 10, "#7A5A10")
        elif datetime.now() < free_until:
            canvas.text(32, 630, "入住前 24 小时可免费取消；", 10, "#7A5A10")
            canvas.text(
                32, 648,
                f"24 小时内取消扣首晚房费 {money(penalty)}（{order.active_qty} 间）。",
                10, "#7A5A10",
            )
        else:
            canvas.text(32, 630, "当前已进入入住前 24 小时，", 10, "#7A5A10")
            canvas.text(
                32, 648,
                f"取消将扣首晚房费 {money(penalty)}（{order.active_qty} 间）。",
                10, "#7A5A10",
            )
        canvas.text(32, 668, "特殊日期（节假日/展会）按专属规则。", 9, "#8A6A12")

    def _pay(self) -> None:
        self.app.show_payment(self.order.order_no)

    def _cancel(self) -> None:
        order = self.order
        penalty = as_money(order.first_night_amount * order.active_qty)
        paid_total = self.services.order_repo.paid_total(order.order_no)
        lines = [
            f"订单号 {order.order_no}",
            f"取消后扣违约金 {money(penalty)}，可退 {money(max(paid_total - penalty, ZERO))}。",
            "退款将在 1-3 个工作日退回原支付方式。",
        ]
        show_confirm(self, "确认取消订单", lines, "确认取消", self._confirm_cancel)

    def _confirm_cancel(self) -> None:
        try:
            result = self.services.booking.cancel_order(
                self.order.order_no,
                reason="客人自助取消",
                guest_phone=self.order.contact_phone,
            )
        except DomainError as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.show_orders(self.phone)
        self.app.notify(
            f"已取消，退款 {money(result['refund_amount'])}，违约金 {money(result['penalty'])}",
            "success",
        )

    def _contact_hotel(self) -> None:
        hotel = self.services.catalog.hotel(self.order.hotel_id)
        if hotel is None:
            return
        InfoPopover(
            self,
            "联系酒店",
            hotel.phone,
            f"{hotel.name} · 24 小时前台",
            action_label="复制号码",
            on_action=lambda: self._copy_number(hotel.phone),
        )

    def _service(self) -> None:
        InfoPopover(
            self,
            "在线客服",
            "400-820-1234",
            "每日 9:00 - 22:00",
            action_label="复制号码",
            on_action=lambda: self._copy_number("400-820-1234"),
        )

    def _copy_number(self, number: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(number)
        self.app.notify(f"已复制 {number}", "success")


# ----------------------------------------------------------------------
# 订单列表（底部 Tab，进入 05 的入口）
# ----------------------------------------------------------------------
class OrdersPage(GuestPage):
    """Order history reached from the 订单 tab."""

    def __init__(self, app: "GuestApplication", phone: str = "") -> None:
        self.phone_var = tk.StringVar(master=app, value=phone or app.last_phone)
        self.orders: list[Order] = []
        self.loaded = False
        super().__init__(app)

    def build(self) -> None:
        """Render the phone lookup and the order cards."""
        canvas = self.c
        canvas.configure(height=TAB_BAR_TOP)
        self.nav = MobileCanvas(self, COLORS["card"], height=TAB_BAR_HEIGHT)
        self.nav.pack(side="bottom", fill="x")
        self._widgets.append(self.nav)
        draw_bottom_tabs(self.nav, "orders", self.app.open_tab, top=0)
        if not self.loaded and self.phone_var.get().strip():
            self.loaded = True
            self.orders = self._load(self.phone_var.get().strip())

        canvas.gradient(0, 0, WIDTH, 150, COLORS["primary"], COLORS["primary_soft"])
        canvas.status_bar(clock(datetime.now()))
        canvas.text(195, 62, "我的订单", 17, "#FFFFFF", True, "n")
        canvas.text(195, 88, "输入预订手机号查询", 10, "#C9D6E7", False, "n")

        canvas.card(16, 130, 358, 84, 14)
        canvas.text(32, 146, "预订手机号", 9, COLORS["faint"])
        self.entry(32, 162, 200, self.phone_var, size=13)
        canvas.button(244, 156, 112, 38, "查询订单", self._search, size=12)
        canvas.text(32, 194, "仅展示该手机号下的全部订单", 9, COLORS["muted"])

        self._draw_list(236)

    def _load(self, phone: str) -> list[Order]:
        guest = self.services.order_repo.find_guest_by_phone(None, phone)
        if guest is None:
            return []
        self.app.last_phone = phone
        return self.services.order_repo.list_for_guest(guest.guest_id)

    def _draw_list(self, start: float) -> None:
        canvas = self.c
        if self.orders:
            canvas.text(16, start, f"共 {len(self.orders)} 笔订单", 10, COLORS["muted"])
        y = start + 24
        if not self.orders:
            canvas.card(16, y, 358, 120, 14)
            canvas.text(195, y + 42, "还没有查到订单", 13, COLORS["text"], True, "center")
            canvas.text(195, y + 68, "输入预订时使用的手机号后点击查询", 10, COLORS["muted"], False, "center")
        for order in self.orders:
            y = self._order_card(order, y)
        canvas.enable_scroll(y + 20)

    def _order_card(self, order: Order, top: float) -> float:
        canvas = self.c
        canvas.card(16, top, 358, 168, 14)
        color = STATUS_COLORS.get(order.status.value, COLORS["muted"])
        canvas.text(32, top + 14, order.status.label, 11, color, True)
        canvas.text_right(
            358, top + 14, f"{order.nights} 晚 {order.qty} 间", 9, COLORS["muted"]
        )
        canvas.text(
            32, top + 36,
            f"{order.hotel_name} · {order.room_type_name}",
            13, COLORS["text"], True,
        )
        canvas.text(
            32, top + 58,
            f"{md(order.check_in)} - {md(order.check_out)}",
            10, COLORS["muted"],
        )
        canvas.text(32, top + 78, f"入住人 {order.guests_label}", 10, COLORS["muted"])
        canvas.text(32, top + 106, money(order.total_amount), 13, COLORS["red"], True)
        detail = canvas.text(358, top + 108, "查看详情 ›", 10, COLORS["primary"], True, "ne")

        def open_detail(item=order) -> None:  # type: ignore[no-untyped-def]
            self.app.show_order_detail(item, self.phone_var.get())

        def open_modify(item=order) -> None:  # type: ignore[no-untyped-def]
            self.app.show_modify(item, self.phone_var.get())

        def open_pay(item=order) -> None:  # type: ignore[no-untyped-def]
            self.app.show_payment(item.order_no)

        def open_cancel(item=order) -> None:  # type: ignore[no-untyped-def]
            self._cancel(item)

        canvas.link([detail], open_detail)
        actions: list[tuple[str, object, bool]] = []
        if order.can_modify:
            actions.append(("改期", open_modify, False))
        if order.can_cancel:
            actions.append(("取消", open_cancel, False))
        if order.status is OrderStatus.PENDING_PAYMENT and order.pay_mode is PayMode.ONLINE:
            actions.insert(0, ("去支付", open_pay, True))
        x = 358.0
        for label, command, primary in reversed(actions):
            width = canvas.measure(label, 11) + 30
            x -= width
            canvas.button(
                x, top + 130, width, 30, label, command, size=11,
                fill=COLORS["primary"] if primary else COLORS["card"],
                fg="#FFFFFF" if primary else COLORS["primary"],
                outline=None if primary else COLORS["border"],
                r=8,
            )
            x -= 8
        return top + 180

    def _search(self) -> None:
        phone = self.phone_var.get().strip()
        if not phone:
            self.app.notify("请输入预订时使用的手机号")
            return
        self.loaded = True
        self.orders = self._load(phone)
        if not self.orders:
            self.app.notify("没有查到该手机号的订单", "error")
        self.redraw()

    def _cancel(self, order: Order) -> None:
        penalty = as_money(order.first_night_amount * order.active_qty)
        paid_total = self.services.order_repo.paid_total(order.order_no)
        lines = [
            f"订单号 {order.order_no}",
            f"取消后扣违约金 {money(penalty)}，可退 {money(max(paid_total - penalty, ZERO))}。",
            "退款将在 1-3 个工作日退回原支付方式。",
        ]
        show_confirm(
            self, "确认取消订单", lines, "确认取消",
            lambda item=order: self._confirm_cancel(item),
        )

    def _confirm_cancel(self, order: Order) -> None:
        try:
            result = self.services.booking.cancel_order(
                order.order_no,
                reason="客人自助取消",
                guest_phone=order.contact_phone,
            )
        except DomainError as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.notify(
            f"已取消，退款 {money(result['refund_amount'])}，违约金 {money(result['penalty'])}",
            "success",
        )
        self._search()


# ----------------------------------------------------------------------
# 修改订单（05 的下一级页面）
# ----------------------------------------------------------------------
class ModifyPage(GuestPage):
    """Change dates, room type or same-city hotel of a confirmed order."""

    def __init__(self, app: "GuestApplication", order_no: str, phone: str) -> None:
        order = app.services.order_repo.require(order_no)
        self.order = order
        self.phone = phone
        source = app.services.catalog.hotel(order.hotel_id)
        self.hotel = source
        self.hotels = {
            item.name: item for item in app.services.catalog.hotels(city=source.city)
        } if source else {}
        self.room_type = app.services.catalog.room_type(order.room_type_id)
        self.check_in = order.check_in
        self.check_out = order.check_out
        self.quote: Quote | None = None
        super().__init__(app)

    def build(self) -> None:
        """Render the editable order and the re-priced difference."""
        canvas = self.c
        order = self.order
        canvas.gradient(0, 0, WIDTH, 108, COLORS["primary"], COLORS["primary_soft"])
        canvas.status_bar(clock(datetime.now()))
        back_button(canvas, lambda: self.app.show_order_detail(order, self.phone))
        canvas.text(195, 62, "修改订单", 17, "#FFFFFF", True, "n")
        canvas.text(195, 88, order.order_no, 10, "#C9D6E7", False, "n")

        canvas.card(16, 130, 358, 300, 14)
        self._row(16, 146, "门店（限同城）", self.hotel.name if self.hotel else "-", self._pick_hotel)
        self._row(16, 208, "房型", self.room_type.name, self._pick_room)
        self._row(16, 270, "入住日期", md_week(self.check_in), self._pick_dates)
        self._row(16, 332, "离店日期", md_week(self.check_out), self._pick_out_dates)
        canvas.text(32, 400, "修改后按新日期重新计价，差价多退少补。", 9, COLORS["muted"])

        canvas.card(16, 450, 358, 150, 14)
        canvas.text(32, 466, "价格预览", 12, COLORS["text"], True)
        self._quote_box(482)
        canvas.text(32, 566, "原订单金额", 11, COLORS["muted"])
        canvas.text_right(358, 566, money(order.total_amount), 11, COLORS["text"])

        canvas.rect(0, 770, WIDTH, 74, COLORS["card"])
        canvas.line(0, 770, WIDTH, 770, COLORS["border"])
        canvas.button(24, 784, WIDTH - 48, 44, "确认修改", self._submit, size=15)

    def _row(self, x, top, label, value, command):  # type: ignore[no-untyped-def]
        canvas = self.c
        canvas.text(32, top, label, 9, COLORS["faint"])
        canvas.text(32, top + 18, value, 13, COLORS["text"], True)
        canvas.chevron(348, top + 22, 6, COLORS["faint"], 1.4)
        canvas.line(32, top + 50, 358, top + 50, COLORS["line"])
        canvas.bind_area(24, top - 4, 342, 56, command)

    def _quote_box(self, top: float) -> None:
        canvas = self.c
        if self.quote is None:
            nights = stay_nights(self.check_in, self.check_out)
            canvas.text(
                32, top, f"{nights} 晚 · 点击下方重新计价", 10, COLORS["muted"]
            )
            canvas.button(32, top + 30, 120, 34, "重新计价", self._reprice, size=11,
                          fill=COLORS["blue_bg"], fg=COLORS["primary"])
            return
        quote = self.quote
        canvas.text(
            32, top,
            f"{quote.night_count} 晚 {quote.qty} 间 · 新总价 {money(quote.total)}",
            11, COLORS["text"],
        )
        delta = as_money(quote.total - self.order.total_amount)
        if delta > 0:
            note, color = f"需补差价 {money(delta)}", COLORS["amber"]
        elif delta < 0:
            note, color = f"可退差价 {money(-delta)}", COLORS["green"]
        else:
            note, color = "无差价", COLORS["muted"]
        canvas.text(32, top + 22, note, 10, color, True)
        canvas.button(32, top + 44, 120, 34, "重新计价", self._reprice, size=11,
                      fill=COLORS["blue_bg"], fg=COLORS["primary"])

    def _reprice(self) -> None:
        if self.hotel is None:
            return
        try:
            self.quote = self.app.services.booking.quote(
                self.hotel.hotel_id,
                self.room_type.room_type_id,
                self.check_in,
                self.check_out,
                self.order.qty,
            )
        except DomainError as exc:
            self.app.notify(str(exc), "error")
            return
        if not self.quote.is_available:
            self.app.notify(self.quote.reason or "目标房源不可预订", "error")
        self.redraw()

    def _pick_hotel(self) -> None:
        options = [
            (hotel.name, f"{hotel.district} · {hotel.type_label}",
             lambda value=hotel: self._choose_hotel(value))
            for hotel in self.hotels.values()
        ]
        show_options(self, "选择门店（限同城）", options,
                     current=self.hotel.name if self.hotel else "")

    def _choose_hotel(self, hotel: Hotel) -> None:
        self.hotel = hotel
        room_types = self.app.services.catalog.room_types(hotel.hotel_id)
        if room_types:
            self.room_type = room_types[0]
        self.quote = None
        self.redraw()

    def _pick_room(self) -> None:
        if self.hotel is None:
            return
        options = [
            (room.name, room.short_spec, lambda value=room: self._choose_room(value))
            for room in self.app.services.catalog.room_types(self.hotel.hotel_id)
        ]
        show_options(self, "选择房型", options, current=self.room_type.name)

    def _choose_room(self, room: RoomType) -> None:
        self.room_type = room
        self.quote = None
        self.redraw()

    def _pick_dates(self) -> None:
        DateSheet(self, self.check_in, self.check_out, self._choose_dates)

    def _pick_out_dates(self) -> None:
        DateSheet(self, self.check_in, self.check_out, self._choose_dates)

    def _choose_dates(self, check_in: date, check_out: date) -> None:
        self.check_in = check_in
        self.check_out = check_out
        self.quote = None
        self.redraw()

    def _submit(self) -> None:
        if self.hotel is None:
            return
        try:
            result = self.app.services.booking.modify_order(
                self.order.order_no,
                hotel_id=self.hotel.hotel_id,
                room_type_id=self.room_type.room_type_id,
                check_in=self.check_in,
                check_out=self.check_out,
                guest_phone=self.phone,
            )
        except DomainError as exc:
            self.app.notify(str(exc), "error")
            return
        updated = result["order"]
        self.app.show_order_detail(updated, self.phone)
        self.app.notify("修改成功，订单已按新日期确认", "success")


# ----------------------------------------------------------------------
# 我的
# ----------------------------------------------------------------------
class MinePage(GuestPage):
    """Simple profile tab; it keeps the three-tab structure of screen 01."""

    def build(self) -> None:
        """Render the guest identity and the shortcuts."""
        canvas = self.c
        canvas.gradient(0, 0, WIDTH, 250, COLORS["primary"], COLORS["primary_soft"])
        canvas.status_bar(clock(datetime.now()))
        canvas.text(24, 82, "我的", 27, "#FFFFFF", True)
        canvas.text(24, 126, "云栖酒店 · 会员中心", 11, "#B9C9DC")
        canvas.create_oval(24, 164, 88, 228, fill="#FFFFFF", outline="#FFFFFF")
        initial = (self.app.last_name or "客")[:1]
        canvas.text(56, 196, initial, 26, COLORS["primary"], True, "center")
        canvas.text(104, 170, self.app.last_name or "未登录客人", 18, "#FFFFFF", True)
        if self.app.last_phone:
            canvas.text(104, 198, mask_phone(self.app.last_phone), 11, "#C9D6E7")
        else:
            canvas.text(104, 198, "预订后自动绑定手机号", 11, "#C9D6E7")

        canvas.card(16, 268, 358, 150, 14)
        rows = [
            ("我的订单", lambda: self.app.open_tab("orders")),
            ("联系客服", self._service),
            ("关于云栖", self._about),
        ]
        for index, (label, command) in enumerate(rows):
            top = 282 + index * 46
            text = canvas.text(32, top, label, 13, COLORS["text"])
            canvas.chevron(352, top + 4, 6, COLORS["faint"], 1.4)
            if index < len(rows) - 1:
                canvas.line(32, top + 34, 358, top + 34, COLORS["line"])
            canvas.bind_area(16, top - 10, 358, 44, command)

        canvas.card(16, 438, 358, 96, 14, COLORS["blue_bg"], shadow=False)
        canvas.text(32, 456, "预订须知", 11, COLORS["primary"], True)
        canvas.text(32, 478, "入住 14:00 后 · 退房次日 12:00 前", 9, COLORS["muted"])
        canvas.text(32, 496, "入住前 24 小时可免费取消", 9, COLORS["muted"])
        draw_bottom_tabs(canvas, "mine", self.app.open_tab)

    def _service(self) -> None:
        InfoPopover(
            self,
            "在线客服",
            "400-820-1234",
            "每日 9:00 - 22:00",
            action_label="复制号码",
            on_action=lambda: self._copy_number("400-820-1234"),
        )

    def _copy_number(self, number: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(number)
        self.app.notify(f"已复制 {number}", "success")

    def _about(self) -> None:
        InfoPopover(
            self,
            "关于云栖",
            "云栖酒店集团",
            f"版本 {config.APP_VERSION}",
            value_size=18,
        )


# ----------------------------------------------------------------------
# Application shell
# ----------------------------------------------------------------------
class GuestApplication(tk.Tk):
    """Portrait guest application; owns the search state and page stack."""

    def __init__(self, services: Services) -> None:
        super().__init__()
        setup_guest_root(self)
        self.services = services
        self.title(config.GUEST_APP_NAME)
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self._center_window()

        cities = services.catalog.cities()
        self.city = "上海" if "上海" in cities else (cities[0] if cities else "")
        self.hotels = services.catalog.hotels(city=self.city) if self.city else []
        self.hotel: Hotel | None = self.hotels[0] if self.hotels else None
        self.check_in = date.today() + timedelta(days=1)
        self.check_out = self.check_in + timedelta(days=2)
        self.guests = 2
        self.last_name = ""
        self.last_phone = ""
        self.hold: RoomHold | None = None
        self.current_page: GuestPage | None = None
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.show_home()

    def _center_window(self) -> None:
        self.update_idletasks()
        x = max((self.winfo_screenwidth() - WIDTH) // 2, 0)
        y = max((self.winfo_screenheight() - HEIGHT) // 2 - 20, 0)
        self.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")

    def _show(self, page: GuestPage) -> None:
        """Replace the current page."""
        if self.current_page is not None:
            self.current_page.destroy()
        self.current_page = page
        page.pack(fill="both", expand=True)

    def notify(self, message: str, kind: str = "info") -> None:
        """Show a transient message on the active page."""
        if self.current_page is not None:
            self.current_page.c.toast(message, kind)

    def show_home(self) -> None:
        """Open screen 01."""
        self._show(HomePage(self))

    def show_rooms(self) -> None:
        """Open screen 02 for the selected hotel."""
        if self.hotel is None:
            self.notify("请先选择门店", "error")
            return
        self._show(RoomListPage(self))

    def show_detail(self, result: SearchResult, qty: int = 1) -> None:
        """Open screen 02A."""
        self._show(RoomDetailPage(self, result, qty))

    def start_booking(self, result: SearchResult, qty: int) -> None:
        """Lock the quote for 15 minutes and open screen 03."""
        self.hold = RoomHold(
            result=result,
            qty=qty,
            deadline=datetime.now() + timedelta(minutes=PayMode.ONLINE.lock_minutes),
        )
        self._show(BookingPage(self, self.hold))

    def show_payment(self, order_no: str) -> None:
        """Open screen 04 for a pending order."""
        self._show(PaymentPage(self, order_no))

    def show_order_detail(self, order: Order, phone: str = "") -> None:
        """Open screen 05."""
        self._show(OrderDetailPage(self, order.order_no, phone or order.contact_phone))

    def show_orders(self, phone: str = "") -> None:
        """Open the order tab."""
        self._show(OrdersPage(self, phone))

    def show_modify(self, order: Order, phone: str) -> None:
        """Open the self-service modification page."""
        self._show(ModifyPage(self, order.order_no, phone))

    def show_mine(self) -> None:
        """Open the profile tab."""
        self._show(MinePage(self))

    def open_tab(self, key: str) -> None:
        """Route a bottom-tab tap."""
        if key == "home":
            self.show_home()
        elif key == "orders":
            self.show_orders(self.last_phone)
        else:
            self.show_mine()


def main() -> None:
    """Start the standalone guest client."""
    services = create_services()
    app = GuestApplication(services)
    app.mainloop()


if __name__ == "__main__":
    main()
