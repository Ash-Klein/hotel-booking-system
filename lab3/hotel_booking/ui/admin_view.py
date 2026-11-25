"""Group-level portal for operations, finance and city managers."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, TYPE_CHECKING

from ..domain.enums import ExceptionStatus, HotelStatus, RoomTypeStatus
from ..domain.errors import DomainError
from ..domain.money import as_money, yuan
from .dialogs import OrderDetailDialog, ResolveExceptionDialog, parse_date_entry
from .staff_view import AuditLogView, RefundView
from .theme import COLORS, choose_font
from .widgets import (
    Card,
    DataTable,
    PageHeader,
    StatCard,
    confirm,
    make_field,
    show_error,
    show_info,
)

if TYPE_CHECKING:
    from .app import HotelBookingApp

ADMIN_NAV = {
    "overview": ("集团总览", "▦"),
    "reports": ("经营报表", "▤"),
    "refunds": ("退款审核", "◈"),
    "exceptions": ("异常台账", "△"),
    "logs": ("审计日志", "◎"),
    "hotels": ("门店与房型", "▥"),
}


class AdminShell(tk.Frame):
    """Sidebar shell for finance, operations and city-manager roles."""

    def __init__(self, parent: tk.Misc, app: "HotelBookingApp") -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self.services = app.services
        self.staff = app.current_staff
        if not self.staff:
            raise RuntimeError("AdminShell 需要已登录员工")
        self.font = choose_font(self)
        self.page: tk.Frame | None = None
        self.nav_buttons: dict[str, ttk.Button] = {}
        self._build_layout()
        self.navigate("overview")

    def _build_layout(self) -> None:
        sidebar = tk.Frame(self, bg=COLORS["navy"], width=232)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        brand = tk.Frame(sidebar, bg=COLORS["navy"])
        brand.pack(fill="x", padx=22, pady=(26, 24))
        tk.Label(
            brand,
            text="云栖",
            bg=COLORS["navy"],
            fg=COLORS["accent"],
            font=(self.font, 19, "bold"),
        ).pack(anchor="w")
        tk.Label(
            brand,
            text="集团运营中心",
            bg=COLORS["navy"],
            fg="#B9C7D5",
            font=(self.font, 9),
        ).pack(anchor="w", pady=(2, 0))
        user_card = tk.Frame(sidebar, bg=COLORS["navy_light"])
        user_card.pack(fill="x", padx=14, pady=(0, 18))
        tk.Label(
            user_card,
            text=self.staff.name,
            bg=COLORS["navy_light"],
            fg=COLORS["white"],
            font=(self.font, 12, "bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(
            user_card,
            text=self.staff.role.label,
            bg=COLORS["navy_light"],
            fg="#A9BBCC",
            font=(self.font, 8),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(2, 10))
        for key, (label, icon) in ADMIN_NAV.items():
            button = ttk.Button(
                sidebar,
                text=f"  {icon}   {label}",
                style="Nav.TButton",
                command=lambda name=key: self.navigate(name),
            )
            button.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = button
        tk.Frame(sidebar, bg=COLORS["navy"]).pack(fill="both", expand=True)
        ttk.Button(
            sidebar,
            text="  ⎋   退出登录",
            style="Nav.TButton",
            command=self.app.logout,
        ).pack(fill="x", padx=10, pady=(0, 20))

        main = tk.Frame(self, bg=COLORS["bg"])
        main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(main, bg=COLORS["card"], height=64)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top,
            text="集团视角",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=(self.font, 12, "bold"),
        ).pack(side="left", padx=24)
        tk.Label(
            top,
            text="直营 4 家 · 加盟 2 家 · 上海 / 杭州 / 南京",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 9),
        ).pack(side="left", padx=10)
        tk.Label(
            top,
            text=(
                "只读视图" if self.staff.role.read_only else "可操作视图"
            )
            + f"  ·  {date.today():%Y-%m-%d}",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 9),
        ).pack(side="right", padx=24)
        self.page_host = tk.Frame(main, bg=COLORS["bg"])
        self.page_host.pack(fill="both", expand=True, padx=24, pady=18)

    def navigate(self, key: str) -> None:
        """Switch group-level page."""
        for name, button in self.nav_buttons.items():
            button.configure(
                style="NavActive.TButton" if name == key else "Nav.TButton"
            )
        if self.page:
            self.page.destroy()
        views: dict[str, type[tk.Frame]] = {
            "overview": OverviewView,
            "reports": ReportsView,
            "refunds": RefundView,
            "exceptions": ExceptionView,
            "logs": AuditLogView,
            "hotels": HotelCatalogView,
        }
        self.page = views[key](self.page_host, self)
        self.page.pack(fill="both", expand=True)

    def refresh_page(self) -> None:
        if self.page and hasattr(self.page, "refresh"):
            self.page.refresh()  # type: ignore[attr-defined]

    def notify(self, message: str, kind: str = "info") -> None:
        self.app.notify(message, kind)


class OverviewView(tk.Frame):
    """Group dashboard with a hand-drawn seven-day trend chart."""

    def __init__(self, parent: tk.Misc, host: AdminShell) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.host = host
        self.services = host.services
        self.staff = host.staff
        self.font = choose_font(self)
        self.cards: dict[str, StatCard] = {}
        self.trend_data: list[dict[str, object]] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = PageHeader(
            self,
            "集团总览",
            "跨门店查看经营结果、资金待办与异常风险。",
        )
        header.pack(fill="x", pady=(0, 12))
        ttk.Button(
            header.actions, text="刷新", command=self.refresh
        ).pack(side="right")
        stats = tk.Frame(self, bg=COLORS["bg"])
        stats.pack(fill="x", pady=(0, 12))
        definitions = [
            ("hotels", "在营门店", "覆盖 3 个城市", COLORS["blue"]),
            ("orders", "近 30 天订单", "含全部渠道", COLORS["navy_light"]),
            ("revenue", "近 30 天营收", "已确认订单金额", COLORS["green"]),
            ("occupancy", "平均出租率", "按库存间夜加权", COLORS["accent"]),
            ("refunds", "待审退款", "超过 500 元审批线", COLORS["orange"]),
            ("exceptions", "未结异常", "需集团裁决", COLORS["red"]),
        ]
        for index, (key, title, hint, color) in enumerate(definitions):
            row, column = divmod(index, 3)
            card = StatCard(stats, title, "—", hint, color)
            card.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 8, 0),
                pady=(0, 8),
            )
            self.cards[key] = card
        for column in range(3):
            stats.grid_columnconfigure(column, weight=1)
        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True)
        chart_card = Card(body, padding=12)
        chart_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(
            chart_card.inner,
            text="近 7 天订单趋势",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=(self.font, 12, "bold"),
            anchor="w",
        ).pack(fill="x")
        self.chart = tk.Canvas(
            chart_card.inner,
            bg=COLORS["card"],
            highlightthickness=0,
            height=250,
        )
        self.chart.pack(fill="both", expand=True, pady=(8, 0))
        self.chart.bind("<Configure>", lambda _: self.draw_chart())
        recent_card = Card(body, padding=12)
        recent_card.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(
            recent_card.inner,
            text="最近订单",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=(self.font, 12, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        self.table = DataTable(
            recent_card.inner,
            [
                ("order_no", "订单号", 160),
                ("hotel", "门店", 120),
                ("guest", "客人", 80),
                ("amount", "金额", 85),
                ("status", "状态", 100),
            ],
            height=8,
            on_double=lambda _: self.show_order(),
        )
        self.table.pack(fill="both", expand=True)
        ttk.Button(
            recent_card.inner,
            text="查看订单详情",
            style="Secondary.TButton",
            command=self.show_order,
        ).pack(anchor="e", pady=(8, 0))

    def refresh(self) -> None:
        today = date.today()
        start = today - timedelta(days=29)
        rows = self.services.reporting.hotel_report(
            start, today + timedelta(days=1), self.staff
        )
        hotels = self.services.catalog.hotels()
        occupancy_values = [row.occupancy for row in rows if row.occupancy > 0]
        average_occupancy = (
            sum(occupancy_values, Decimal("0")) / len(occupancy_values)
            if occupancy_values
            else Decimal("0")
        )
        revenue = sum((row.revenue for row in rows), Decimal("0"))
        orders = sum(row.order_count for row in rows)
        open_exceptions = len(
            [
                item
                for item in self.services.order_repo.list_exceptions(
                    ExceptionStatus.OPEN
                )
            ]
        )
        self.cards["hotels"].update_value(str(len(hotels)))
        self.cards["orders"].update_value(str(orders))
        self.cards["revenue"].update_value(yuan(revenue))
        self.cards["occupancy"].update_value(f"{average_occupancy:.1f}%")
        self.cards["refunds"].update_value(
            str(self.services.reporting.pending_count(self.staff))
        )
        self.cards["exceptions"].update_value(str(open_exceptions))
        self.trend_data = self.services.reporting.trend(
            self.staff, days=7
        )
        self.draw_chart()
        recent = self.services.order_repo.search(limit=12)
        self.table.set_rows(
            [
                {
                    "order_no": order.order_no,
                    "hotel": order.hotel_name,
                    "guest": order.contact_name,
                    "amount": yuan(order.total_amount),
                    "status": order.status.label,
                    "_tag": "bad" if order.status.value == "EXCEPTION" else "",
                    "_order": order,
                }
                for order in recent
            ]
        )

    def draw_chart(self) -> None:
        """Draw a simple bar chart without external chart dependencies."""
        canvas = self.chart
        canvas.delete("all")
        width = max(canvas.winfo_width(), 360)
        height = max(canvas.winfo_height(), 200)
        if not self.trend_data:
            return
        values = [int(item["orders"]) for item in self.trend_data]
        maximum = max(max(values), 1)
        left, right, top, bottom = 42, 18, 18, 44
        plot_width = width - left - right
        plot_height = height - top - bottom
        for step in range(4):
            y = top + plot_height * step / 3
            canvas.create_line(
                left,
                y,
                width - right,
                y,
                fill="#EDF1F5",
            )
            canvas.create_text(
                left - 8,
                y,
                text=str(round(maximum * (3 - step) / 3)),
                fill=COLORS["muted"],
                anchor="e",
                font=(self.font, 8),
            )
        slot = plot_width / len(self.trend_data)
        bar_width = min(34, slot * 0.55)
        for index, item in enumerate(self.trend_data):
            value = int(item["orders"])
            bar_height = plot_height * value / maximum
            x = left + slot * index + (slot - bar_width) / 2
            y = top + plot_height - bar_height
            canvas.create_rectangle(
                x,
                y,
                x + bar_width,
                top + plot_height,
                fill=COLORS["blue"],
                outline="",
            )
            canvas.create_text(
                x + bar_width / 2,
                y - 8,
                text=str(value),
                fill=COLORS["navy"],
                font=(self.font, 8, "bold"),
            )
            canvas.create_text(
                x + bar_width / 2,
                top + plot_height + 16,
                text=str(item["date"])[5:],
                fill=COLORS["muted"],
                font=(self.font, 8),
            )

    def show_order(self) -> None:
        row = self.table.selected_row()
        if not row or "_order" not in row:
            show_info(self, "请先选择一笔订单", "提示")
            return
        OrderDetailDialog(self, self.services, row["_order"])


class ReportsView(tk.Frame):
    """Hotel-level operating report and room-type sales ranking."""

    def __init__(self, parent: tk.Misc, host: AdminShell) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.host = host
        self.services = host.services
        self.staff = host.staff
        self.font = choose_font(self)
        self.rows = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = PageHeader(
            self,
            "经营报表",
            "按日/周/月统计订单量、间夜、营收、出租率与取消率。",
        )
        header.pack(fill="x", pady=(0, 12))
        ttk.Button(
            header.actions,
            text="导出 CSV",
            style="Secondary.TButton",
            command=self.export,
        ).pack(side="right", padx=(8, 0))
        ttk.Button(
            header.actions, text="刷新", command=self.refresh
        ).pack(side="right")
        filter_card = Card(self, padding=12)
        filter_card.pack(fill="x", pady=(0, 10))
        form = tk.Frame(filter_card.inner, bg=COLORS["card"])
        form.pack(fill="x")
        self.start_var = tk.StringVar(
            value=(date.today() - timedelta(days=29)).isoformat()
        )
        self.end_var = tk.StringVar(value=date.today().isoformat())
        self.city_var = tk.StringVar(value="全部城市")
        make_field(form, "开始日期", self.start_var, 0, 0, width=14)
        make_field(form, "结束日期", self.end_var, 0, 1, width=14)
        make_field(
            form,
            "城市",
            self.city_var,
            0,
            2,
            width=12,
            values=["全部城市", *self.services.catalog.cities()],
        )
        button = tk.Frame(form, bg=COLORS["card"])
        button.grid(row=0, column=3, padx=(12, 0), pady=(17, 0))
        ttk.Button(button, text="生成报表", command=self.refresh).pack()
        table_card = Card(self, padding=12)
        table_card.pack(fill="both", expand=True)
        self.table = DataTable(
            table_card.inner,
            [
                ("hotel", "门店", 160),
                ("city", "城市", 70),
                ("type", "类型", 60),
                ("orders", "订单量", 70),
                ("room_nights", "间夜", 70),
                ("revenue", "营收", 110),
                ("cancel", "取消单", 65),
                ("occupancy", "出租率", 80),
                ("adr", "ADR", 90),
                ("cancel_rate", "取消率", 80),
            ],
            height=8,
        )
        self.table.pack(fill="both", expand=True)
        self.total_var = tk.StringVar(value="")
        tk.Label(
            table_card.inner,
            textvariable=self.total_var,
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=(self.font, 10, "bold"),
            anchor="e",
        ).pack(fill="x", pady=(8, 4))
        tk.Label(
            table_card.inner,
            text="房型销量 Top 5",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=(self.font, 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(8, 4))
        self.room_table = DataTable(
            table_card.inner,
            [
                ("room_type", "房型", 220),
                ("orders", "订单数", 100),
                ("rooms", "间数", 100),
                ("revenue", "营收", 130),
            ],
            height=5,
        )
        self.room_table.pack(fill="x")

    def refresh(self) -> None:
        try:
            start = parse_date_entry(self.start_var.get(), "开始日期")
            end = parse_date_entry(self.end_var.get(), "结束日期")
        except ValueError as exc:
            show_error(self, str(exc))
            return
        if end < start:
            show_error(self, "结束日期不能早于开始日期")
            return
        rows = self.services.reporting.hotel_report(
            start, end + timedelta(days=1), self.staff
        )
        city = self.city_var.get()
        if city != "全部城市":
            rows = [row for row in rows if row.city == city]
        self.rows = rows
        self.table.set_rows(
            [
                {
                    "hotel": row.hotel_name,
                    "city": row.city,
                    "type": "直营" if row.franchise_type == "DIRECT" else "加盟",
                    "orders": row.order_count,
                    "room_nights": row.room_nights,
                    "revenue": yuan(row.revenue),
                    "cancel": row.cancellations,
                    "occupancy": f"{row.occupancy:.1f}%",
                    "adr": yuan(row.adr),
                    "cancel_rate": f"{row.cancel_rate:.1f}%",
                    "_tag": "warn" if row.cancel_rate >= 30 else "ok",
                }
                for row in rows
            ]
        )
        revenue = sum((row.revenue for row in rows), Decimal("0"))
        orders = sum(row.order_count for row in rows)
        room_nights = sum(row.room_nights for row in rows)
        self.total_var.set(
            f"合计：{len(rows)} 家门店 · {orders} 笔订单 · "
            f"{room_nights} 间夜 · 营收 {yuan(revenue)}"
        )
        sales = self.services.reporting.room_type_sales(
            self.staff, start, end + timedelta(days=1)
        )
        self.room_table.set_rows(
            [
                {
                    "room_type": item["room_type"],
                    "orders": item["orders"],
                    "rooms": item["rooms"],
                    "revenue": yuan(item["revenue"]),
                }
                for item in sales[:5]
            ]
        )

    def export(self) -> None:
        try:
            start = parse_date_entry(self.start_var.get(), "开始日期")
            end = parse_date_entry(self.end_var.get(), "结束日期")
        except ValueError as exc:
            show_error(self, str(exc))
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="导出经营报表",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
            initialfile=f"report_{start}_{end}.csv",
        )
        if not path:
            return
        self.services.reporting.export_hotel_report(
            self.staff, start, end + timedelta(days=1), path
        )
        show_info(self, f"报表已导出到\n{path}", "导出成功")


class ExceptionView(tk.Frame):
    """Group exception ledger and resolution flow."""

    def __init__(self, parent: tk.Misc, host: AdminShell) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.host = host
        self.services = host.services
        self.staff = host.staff
        self.font = choose_font(self)
        self.rows: list[dict[str, object]] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = PageHeader(
            self,
            "异常台账",
            "到店无房、支付掉单与退款失败在这里闭环；异常订单不自动流转。",
        )
        header.pack(fill="x", pady=(0, 12))
        ttk.Button(
            header.actions, text="刷新", command=self.refresh
        ).pack(side="right")
        card = Card(self, padding=12)
        card.pack(fill="both", expand=True)
        self.table = DataTable(
            card.inner,
            [
                ("type", "异常类型", 110),
                ("order_no", "订单号", 175),
                ("hotel", "门店", 140),
                ("description", "说明", 300),
                ("amount", "费用", 90),
                ("status", "状态", 85),
                ("created", "上报时间", 135),
            ],
            height=11,
        )
        self.table.pack(fill="both", expand=True)
        actions = tk.Frame(card.inner, bg=COLORS["card"])
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(
            actions,
            text="裁决选中异常",
            command=self.resolve,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="查看关联订单",
            style="Secondary.TButton",
            command=self.show_order,
        ).pack(side="left", padx=8)
        tk.Label(
            actions,
            text="裁决后订单转为已取消或正常离店，异常记录保留",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 8),
        ).pack(side="right")

    def refresh(self) -> None:
        self.rows = self.services.reporting.exception_rows(self.staff)
        self.table.set_rows(
            [
                {
                    "type": row["type"],
                    "order_no": row["order_no"],
                    "hotel": row["hotel"],
                    "description": row["description"],
                    "amount": yuan(row["amount"]),
                    "status": row["status"],
                    "created": row["created_at"],
                    "_tag": (
                        "warn" if row["status"] == "待处理" else "muted"
                    ),
                    "_row": row,
                }
                for row in self.rows
            ]
        )

    def resolve(self) -> None:
        row = self.table.selected_row()
        if not row or "_row" not in row:
            show_info(self, "请先选择一条异常记录", "提示")
            return
        if row["status"] != "待处理":
            show_info(self, "该异常已经处理", "提示")
            return
        ResolveExceptionDialog(
            self,
            lambda cancel, note: self._do_resolve(
                int(row["exception_id"]), cancel, note
            ),
            str(row["order_no"]),
            str(row["amount"]),
        )

    def _do_resolve(self, exception_id: int, cancel: bool, note: str) -> None:
        try:
            self.services.fulfillment.resolve_exception(
                exception_id,
                self.staff,
                cancel_order=cancel,
                note=note,
            )
        except DomainError as exc:
            show_error(self, str(exc))
            return
        self.host.notify("异常订单已裁决", "success")
        self.refresh()

    def show_order(self) -> None:
        row = self.table.selected_row()
        if not row or "_row" not in row:
            show_info(self, "请先选择一条异常记录", "提示")
            return
        order = self.services.order_repo.get(str(row["order_no"]))
        if order:
            OrderDetailDialog(self, self.services, order)


class HotelCatalogView(tk.Frame):
    """Hotel status and room-type catalogue."""

    def __init__(self, parent: tk.Misc, host: AdminShell) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.host = host
        self.services = host.services
        self.staff = host.staff
        self.font = choose_font(self)
        self.hotels = []
        self.room_types = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = PageHeader(
            self,
            "门店与房型",
            "查看集团门店状态、房型与今日可售；停业只影响新预订。",
        )
        header.pack(fill="x", pady=(0, 12))
        ttk.Button(
            header.actions, text="刷新", command=self.refresh
        ).pack(side="right")
        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True)
        hotel_card = Card(body, padding=12)
        hotel_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(
            hotel_card.inner,
            text="门店",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=(self.font, 12, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        self.hotel_table = DataTable(
            hotel_card.inner,
            [
                ("hotel_id", "编号", 60),
                ("name", "门店", 140),
                ("city", "城市", 70),
                ("type", "类型", 60),
                ("status", "状态", 70),
                ("available", "今日可售", 75),
            ],
            height=11,
            on_select=lambda _: self._load_room_types(),
        )
        self.hotel_table.pack(fill="both", expand=True)
        buttons = tk.Frame(hotel_card.inner, bg=COLORS["card"])
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(
            buttons,
            text="临时停业 / 恢复",
            style="Secondary.TButton",
            command=self.toggle_hotel,
        ).pack(side="left")
        room_card = Card(body, padding=12)
        room_card.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(
            room_card.inner,
            text="房型",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=(self.font, 12, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        self.room_table = DataTable(
            room_card.inner,
            [
                ("name", "房型", 140),
                ("bed", "床型", 140),
                ("capacity", "可住", 55),
                ("price", "基准价", 90),
                ("status", "状态", 70),
            ],
            height=11,
        )
        self.room_table.pack(fill="both", expand=True)
        ttk.Button(
            room_card.inner,
            text="停售 / 恢复房型",
            style="Secondary.TButton",
            command=self.toggle_room_type,
        ).pack(anchor="w", pady=(8, 0))

    def refresh(self) -> None:
        self.hotels = self.services.catalog.hotels()
        today = date.today()
        rows = []
        for hotel in self.hotels:
            rows.append(
                {
                    "hotel_id": hotel.hotel_id,
                    "name": hotel.name,
                    "city": hotel.city,
                    "type": hotel.type_label,
                    "status": hotel.status.label,
                    "available": self.services.inventory_repo.available_sum(
                        hotel.hotel_id, today
                    ),
                    "_tag": "ok" if hotel.is_open else "bad",
                    "_hotel": hotel,
                }
            )
        self.hotel_table.set_rows(rows)
        self.hotel_table.select_first()
        self._load_room_types()

    def _selected_hotel(self):  # type: ignore[no-untyped-def]
        row = self.hotel_table.selected_row()
        return row.get("_hotel") if row else None

    def _load_room_types(self) -> None:
        hotel = self._selected_hotel()
        if not hotel:
            return
        self.room_types = self.services.catalog.room_types(hotel.hotel_id)
        self.room_table.set_rows(
            [
                {
                    "name": room.name,
                    "bed": room.bed_type,
                    "capacity": room.capacity,
                    "price": yuan(room.base_price),
                    "status": room.status.label,
                    "_tag": "ok" if room.is_on_sale else "muted",
                    "_room": room,
                }
                for room in self.room_types
            ]
        )

    def toggle_hotel(self) -> None:
        hotel = self._selected_hotel()
        if not hotel:
            show_info(self, "请先选择一家门店", "提示")
            return
        status = (
            HotelStatus.SUSPENDED
            if hotel.status is HotelStatus.OPEN
            else HotelStatus.OPEN
        )
        if not confirm(
            self, "变更营业状态", f"将「{hotel.name}」设为 {status.label}？"
        ):
            return
        try:
            self.services.inventory.set_hotel_status(
                self.staff, hotel.hotel_id, status
            )
        except DomainError as exc:
            show_error(self, str(exc))
            return
        self.refresh()

    def toggle_room_type(self) -> None:
        hotel = self._selected_hotel()
        row = self.room_table.selected_row()
        if not hotel or not row or "_room" not in row:
            show_info(self, "请先选择门店和房型", "提示")
            return
        room = row["_room"]
        status = (
            RoomTypeStatus.OFF_SALE
            if room.status is RoomTypeStatus.ON_SALE
            else RoomTypeStatus.ON_SALE
        )
        if not confirm(
            self, "变更房型状态", f"将「{room.name}」设置为 {status.label}？"
        ):
            return
        try:
            self.services.inventory.set_room_type_status(
                self.staff, hotel.hotel_id, room.room_type_id, status
            )
        except DomainError as exc:
            show_error(self, str(exc))
            return
        self._load_room_types()
