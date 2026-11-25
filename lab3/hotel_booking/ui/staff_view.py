"""Front-desk and hotel-manager desktop portal."""

from __future__ import annotations

import csv
from datetime import date, timedelta
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, TYPE_CHECKING

from ..domain.enums import (
    HotelStatus,
    OrderStatus,
    PayMode,
    RefundStatus,
    RoomTypeStatus,
)
from ..domain.errors import DomainError
from ..domain.models import Order, Refund
from ..domain.money import as_money, yuan
from .dialogs import (
    CheckInDialog,
    ClosureDialog,
    ExceptionDialog,
    GroupLockDialog,
    OrderDetailDialog,
    PriceDialog,
    StockDialog,
    parse_date_entry,
)
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

NAV_ITEMS = {
    "workbench": ("今日工作台", "▦"),
    "orders": ("订单办理", "▤"),
    "inventory": ("库存与房价", "▥"),
    "group_locks": ("协议锁房", "▧"),
    "refunds": ("退款审核", "◈"),
    "logs": ("操作日志", "◎"),
}


class StaffShell(tk.Frame):
    """Sidebar shell for front-desk and manager roles."""

    def __init__(self, parent: tk.Misc, app: "HotelBookingApp") -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self.services = app.services
        self.staff = app.current_staff
        if not self.staff:
            raise RuntimeError("StaffShell 需要已登录员工")
        self.font = choose_font(self)
        self.hotels = self._visible_hotels()
        self.hotel_id = self.hotels[0].hotel_id if self.hotels else ""
        self.page: tk.Frame | None = None
        self.nav_buttons: dict[str, ttk.Button] = {}
        self._build_layout()
        self.navigate("workbench")

    def _visible_hotels(self):  # type: ignore[no-untyped-def]
        hotels = self.services.catalog.hotels()
        if self.staff.role.is_group_level:
            return hotels
        return [
            hotel
            for hotel in hotels
            if hotel.hotel_id in self.staff.hotel_ids
        ]

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
            text="预订运营工作台",
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
            text=f"{self.staff.role.label} · {len(self.hotels)} 家门店",
            bg=COLORS["navy_light"],
            fg="#A9BBCC",
            font=(self.font, 8),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(2, 10))
        allowed = ["workbench", "orders", "refunds", "logs"]
        if self.staff.role.value in {"MANAGER", "ADMIN"}:
            allowed = [
                "workbench",
                "orders",
                "inventory",
                "group_locks",
                "refunds",
                "logs",
            ]
        for key in allowed:
            label, icon = NAV_ITEMS[key]
            button = ttk.Button(
                sidebar,
                text=f"  {icon}   {label}",
                style="Nav.TButton",
                command=lambda name=key: self.navigate(name),
            )
            button.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = button
        spacer = tk.Frame(sidebar, bg=COLORS["navy"])
        spacer.pack(fill="both", expand=True)
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
            text="当前门店",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 9),
        ).pack(side="left", padx=(24, 6))
        self.hotel_var = tk.StringVar(
            value=self.hotels[0].name if self.hotels else "无可见门店"
        )
        self.hotel_box = ttk.Combobox(
            top,
            textvariable=self.hotel_var,
            state="readonly",
            values=[hotel.name for hotel in self.hotels],
            width=24,
        )
        self.hotel_box.pack(side="left", pady=16)
        self.hotel_box.bind("<<ComboboxSelected>>", lambda _: self._hotel_changed())
        tk.Label(
            top,
            text=f"{date.today():%Y-%m-%d}  ·  {self.staff.role.label}",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 9),
        ).pack(side="right", padx=24)
        self.page_host = tk.Frame(main, bg=COLORS["bg"])
        self.page_host.pack(fill="both", expand=True, padx=24, pady=18)

    def _hotel_changed(self) -> None:
        name = self.hotel_var.get()
        for hotel in self.hotels:
            if hotel.name == name:
                self.hotel_id = hotel.hotel_id
                break
        self.refresh_page()

    @property
    def hotel_name(self) -> str:
        for hotel in self.hotels:
            if hotel.hotel_id == self.hotel_id:
                return hotel.name
        return "全部门店"

    def navigate(self, key: str) -> None:
        """Switch the main content page."""
        for name, button in self.nav_buttons.items():
            button.configure(
                style="NavActive.TButton" if name == key else "Nav.TButton"
            )
        if self.page:
            self.page.destroy()
        views: dict[str, type[tk.Frame]] = {
            "workbench": WorkbenchView,
            "orders": OrdersView,
            "inventory": InventoryView,
            "group_locks": GroupLockView,
            "refunds": RefundView,
            "logs": AuditLogView,
        }
        view_class = views[key]
        self.page = view_class(self.page_host, self)
        self.page.pack(fill="both", expand=True)

    def refresh_page(self) -> None:
        """Ask the current page to reload its data."""
        if self.page and hasattr(self.page, "refresh"):
            self.page.refresh()  # type: ignore[attr-defined]

    def notify(self, message: str, kind: str = "info") -> None:
        """Forward a toast to the application."""
        self.app.notify(message, kind)


class WorkbenchView(tk.Frame):
    """Today's arrivals, departures and operational metrics."""

    def __init__(self, parent: tk.Misc, host: StaffShell) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.host = host
        self.services = host.services
        self.staff = host.staff
        self.font = choose_font(self)
        self.cards: dict[str, StatCard] = {}
        self.arrivals: list[Order] = []
        self.departures: list[Order] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = PageHeader(
            self,
            "今日工作台",
            "到店、离店、在住与待处理事项集中在这里。",
        )
        header.pack(fill="x", pady=(0, 12))
        ttk.Button(
            header.actions,
            text="执行夜审",
            style="Secondary.TButton",
            command=self.run_night_audit,
        ).pack(side="right", padx=(8, 0))
        ttk.Button(
            header.actions,
            text="刷新",
            command=self.refresh,
        ).pack(side="right")
        stats = tk.Frame(self, bg=COLORS["bg"])
        stats.pack(fill="x", pady=(0, 12))
        definitions = [
            ("arrivals", "今日到店", "待办理入住的已确认订单", COLORS["blue"]),
            ("departures", "今日离店", "已入住、今日应退房", COLORS["accent"]),
            ("in_house", "当前在住", "已入住未退房", COLORS["green"]),
            ("pending", "待支付", "线上/现付待处理", COLORS["orange"]),
            ("available", "今日可售", "全房型剩余房间数", COLORS["navy_light"]),
            ("revenue", "今日收款", "已支付流水合计", COLORS["red"]),
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
        tables = tk.Frame(self, bg=COLORS["bg"])
        tables.pack(fill="both", expand=True)
        tables.grid_columnconfigure(0, weight=1, uniform="workbench")
        tables.grid_columnconfigure(1, weight=1, uniform="workbench")
        tables.grid_rowconfigure(0, weight=1)
        left = tk.Frame(tables, bg=COLORS["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = tk.Frame(tables, bg=COLORS["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.arrival_table = self._table_card(
            left,
            "今日到店",
            [
                ("order_no", "订单号", 150),
                ("guest", "客人", 55),
                ("room_type", "房型", 90),
                ("qty", "间", 35),
                ("amount", "金额", 75),
                ("status", "状态", 100),
            ],
            "办理选中订单入住",
            self.check_in_arrival,
        )
        self.departure_table = self._table_card(
            right,
            "今日离店",
            [
                ("order_no", "订单号", 160),
                ("guest", "客人", 60),
                ("room", "房号", 55),
                ("qty", "间", 35),
                ("amount", "金额", 80),
                ("status", "状态", 85),
            ],
            "办理选中订单退房",
            self.check_out_departure,
        )

    def _table_card(
        self,
        parent: tk.Misc,
        title: str,
        columns: list[tuple[str, str, int]],
        action_text: str,
        action: Callable[[], None],
    ) -> DataTable:
        card = Card(parent, padding=12)
        card.pack(fill="both", expand=True)
        tk.Label(
            card.inner,
            text=title,
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=(self.font, 12, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        table = DataTable(card.inner, columns, height=7,
                          on_double=lambda _: action())
        table.pack(fill="both", expand=True)
        actions = tk.Frame(card.inner, bg=COLORS["card"])
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(
            actions,
            text=action_text,
            style="Secondary.TButton",
            command=action,
        ).pack(side="left")
        return table

    def refresh(self) -> None:
        """Reload dashboard metrics and today's lists."""
        stats = self.services.reporting.dashboard(
            self.staff, self.host.hotel_id
        )
        self.cards["arrivals"].update_value(str(stats.arrivals))
        self.cards["departures"].update_value(str(stats.departures))
        self.cards["in_house"].update_value(str(stats.in_house))
        self.cards["pending"].update_value(str(stats.pending))
        self.cards["available"].update_value(str(stats.available_today))
        self.cards["revenue"].update_value(yuan(stats.revenue_today))
        today = date.today()
        self.arrivals = self.services.order_repo.list_arrivals(
            self.host.hotel_id, today
        )
        self.departures = self.services.order_repo.list_departures(
            self.host.hotel_id, today
        )
        self.arrival_table.set_rows(
            [
                {
                    "order_no": order.order_no,
                    "guest": order.contact_name,
                    "room_type": order.room_type_name,
                    "qty": order.qty,
                    "amount": yuan(order.total_amount),
                    "status": order.status.label,
                    "_tag": "warn",
                    "_order": order,
                }
                for order in self.arrivals
            ]
        )
        self.departure_table.set_rows(
            [
                {
                    "order_no": order.order_no,
                    "guest": order.contact_name,
                    "room": order.assigned_rooms or "-",
                    "qty": order.qty,
                    "amount": yuan(order.total_amount),
                    "status": order.status.label,
                    "_tag": "ok",
                    "_order": order,
                }
                for order in self.departures
            ]
        )

    def check_in_arrival(self) -> None:
        row = self.arrival_table.selected_row()
        if not row or "_order" not in row:
            show_info(self, "请先选择一条到店订单", "提示")
            return
        order = row["_order"]
        CheckInDialog(
            self, self.services, order, self.staff,
            on_done=lambda _: self.refresh(),
        )

    def check_out_departure(self) -> None:
        row = self.departure_table.selected_row()
        if not row or "_order" not in row:
            show_info(self, "请先选择一条离店订单", "提示")
            return
        order = row["_order"]
        if not confirm(self, "确认退房", "请确认已查房且无物品损坏、无未结消费。"):
            return
        try:
            result = self.services.fulfillment.check_out(
                order.order_no, self.staff, inspected=True
            )
        except DomainError as exc:
            show_error(self, str(exc))
            return
        message = f"退房完成，订单状态：{result['order'].status.label}"
        if result["refund_amount"]:
            message += f"\n提前退房退款：{yuan(result['refund_amount'])}"
        show_info(self, message, "退房成功")
        self.refresh()

    def run_night_audit(self) -> None:
        if not confirm(
            self,
            "执行夜审",
            "将超时未支付订单自动取消，并把今日未到店订单标记为 No-show。是否继续？",
        ):
            return
        try:
            result = self.services.fulfillment.run_night_audit(
                self.staff, force=True
            )
        except DomainError as exc:
            show_error(self, str(exc))
            return
        show_info(
            self,
            f"夜审完成：释放超时订单 {result['expired']} 笔，"
            f"标记 No-show {result['no_show']} 笔。",
            "夜审结果",
        )
        self.refresh()


class OrdersView(tk.Frame):
    """Search and operate orders for the current hotel."""

    def __init__(self, parent: tk.Misc, host: StaffShell) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.host = host
        self.services = host.services
        self.staff = host.staff
        self.font = choose_font(self)
        self.orders: list[Order] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = PageHeader(
            self,
            "订单办理",
            "按订单号、手机号或姓名检索；所有状态变更都会写入操作日志。",
        )
        header.pack(fill="x", pady=(0, 12))
        ttk.Button(
            header.actions,
            text="导出当前列表",
            style="Secondary.TButton",
            command=self.export,
        ).pack(side="right", padx=(8, 0))
        ttk.Button(
            header.actions, text="刷新", command=self.refresh
        ).pack(side="right")
        card = Card(self, padding=12)
        card.pack(fill="x", pady=(0, 10))
        form = tk.Frame(card.inner, bg=COLORS["card"])
        form.pack(fill="x")
        self.keyword_var = tk.StringVar()
        self.status_var = tk.StringVar(value="全部状态")
        make_field(form, "订单号 / 手机号 / 姓名", self.keyword_var, 0, 0, width=24)
        make_field(
            form,
            "订单状态",
            self.status_var,
            0,
            1,
            width=16,
            values=["全部状态", *[status.label for status in OrderStatus]],
        )
        button = tk.Frame(form, bg=COLORS["card"])
        button.grid(row=0, column=2, padx=(12, 0), pady=(17, 0))
        ttk.Button(button, text="查 询", command=self.refresh).pack()
        form.grid_columnconfigure(0, weight=1)
        table_card = Card(self, padding=12)
        table_card.pack(fill="both", expand=True)
        self.table = DataTable(
            table_card.inner,
            [
                ("order_no", "订单号", 175),
                ("guest", "入住人", 80),
                ("phone", "手机号", 115),
                ("room_type", "房型", 110),
                ("dates", "入住 / 离店", 170),
                ("amount", "金额", 90),
                ("pay_mode", "支付", 80),
                ("status", "状态", 110),
            ],
            height=10,
            on_double=lambda _: self.show_detail(),
        )
        self.table.pack(fill="both", expand=True)
        actions = tk.Frame(table_card.inner, bg=COLORS["card"])
        actions.pack(fill="x", pady=(10, 0))
        buttons = [
            ("确认接单", self.confirm_booking),
            ("办理入住", self.check_in),
            ("办理退房", self.check_out),
            ("标记异常", self.mark_exception),
            ("标记 No-show", self.mark_no_show),
            ("查看详情", self.show_detail),
        ]
        for text, command in buttons:
            ttk.Button(
                actions, text=text, style="Secondary.TButton", command=command
            ).pack(side="left", padx=(0, 6))
        self.hint_var = tk.StringVar(value="")
        tk.Label(
            actions,
            textvariable=self.hint_var,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 8),
        ).pack(side="right")

    def refresh(self) -> None:
        status = None
        if self.status_var.get() != "全部状态":
            for candidate in OrderStatus:
                if candidate.label == self.status_var.get():
                    status = candidate
                    break
        self.orders = self.services.order_repo.search(
            hotel_id=self.host.hotel_id or None,
            status=status,
            keyword=self.keyword_var.get().strip(),
            limit=300,
        )
        rows: list[dict[str, object]] = []
        for order in self.orders:
            tag = {
                OrderStatus.PENDING_PAYMENT: "warn",
                OrderStatus.CHECKED_OUT: "ok",
                OrderStatus.CANCELLED: "muted",
                OrderStatus.EXCEPTION: "bad",
                OrderStatus.NO_SHOW: "bad",
            }.get(order.status, "")
            rows.append(
                {
                    "order_no": order.order_no,
                    "guest": order.contact_name,
                    "phone": order.contact_phone,
                    "room_type": order.room_type_name,
                    "dates": f"{order.check_in} / {order.check_out}",
                    "amount": yuan(order.total_amount),
                    "pay_mode": order.pay_mode.label,
                    "status": order.status.label,
                    "_tag": tag,
                    "_order": order,
                }
            )
        self.table.set_rows(rows)
        self.hint_var.set(f"共 {len(rows)} 笔订单")

    def _selected(self) -> Order | None:
        row = self.table.selected_row()
        if not row or "_order" not in row:
            show_info(self, "请先选择一笔订单", "提示")
            return None
        return row["_order"]  # type: ignore[return-value]

    def confirm_booking(self) -> None:
        order = self._selected()
        if not order:
            return
        try:
            updated = self.services.booking.confirm_at_hotel(
                order.order_no, self.staff
            )
        except DomainError as exc:
            show_error(self, str(exc))
            self.refresh()
            return
        show_info(self, f"已确认接单，状态：{updated.status.label}", "接单成功")
        self.refresh()

    def check_in(self) -> None:
        order = self._selected()
        if not order:
            return
        if not order.can_check_in:
            show_info(self, "只有已确认待入住的订单可以办理入住", "提示")
            return
        CheckInDialog(
            self, self.services, order, self.staff,
            on_done=lambda _: self.refresh(),
        )

    def check_out(self) -> None:
        order = self._selected()
        if not order:
            return
        if not order.can_check_out:
            show_info(self, "只有已入住订单可以办理退房", "提示")
            return
        if not confirm(self, "确认退房", "已查房且无未结消费？"):
            return
        try:
            result = self.services.fulfillment.check_out(
                order.order_no, self.staff
            )
        except DomainError as exc:
            show_error(self, str(exc))
            return
        message = "退房完成"
        if result["refund_amount"]:
            message += f"，提前退房退款 {yuan(result['refund_amount'])}"
        show_info(self, message, "退房成功")
        self.refresh()

    def mark_exception(self) -> None:
        order = self._selected()
        if not order:
            return
        if order.status not in {OrderStatus.CONFIRMED, OrderStatus.CHECKED_IN}:
            show_info(self, "当前状态不可标记异常", "提示")
            return
        ExceptionDialog(
            self, self.services, order, self.staff,
            on_done=self.refresh,
        )

    def mark_no_show(self) -> None:
        order = self._selected()
        if not order:
            return
        if order.status is not OrderStatus.CONFIRMED:
            show_info(self, "仅已确认待入住订单可标记 No-show", "提示")
            return
        if not confirm(
            self,
            "标记 No-show",
            "标记后订单不可恢复，库存释放，客人再次到店须重新下单。继续？",
        ):
            return
        try:
            self.services.fulfillment.mark_no_show(order.order_no, self.staff)
        except DomainError as exc:
            show_error(self, str(exc))
            return
        show_info(self, "已标记客人未到店，库存已释放", "操作成功")
        self.refresh()

    def show_detail(self) -> None:
        order = self._selected()
        if order:
            OrderDetailDialog(self, self.services, order)

    def export(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="导出订单",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
            initialfile=f"orders_{date.today():%Y%m%d}.csv",
        )
        if not path:
            return
        self.services.reporting.export_orders(self.staff, self.orders, path)
        show_info(self, f"已导出到\n{path}", "导出成功")


class InventoryView(tk.Frame):
    """Daily stock, price, closure and stock-correction screen."""

    def __init__(self, parent: tk.Misc, host: StaffShell) -> None:
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
            "库存与房价",
            "按自然日维护总房量、售价与关房；协议锁房单独计量。",
        )
        header.pack(fill="x", pady=(0, 12))
        ttk.Button(
            header.actions, text="刷新", command=self.refresh
        ).pack(side="right")
        card = Card(self, padding=12)
        card.pack(fill="x", pady=(0, 10))
        form = tk.Frame(card.inner, bg=COLORS["card"])
        form.pack(fill="x")
        self.start_var = tk.StringVar(value=date.today().isoformat())
        self.end_var = tk.StringVar(
            value=(date.today() + timedelta(days=7)).isoformat()
        )
        make_field(form, "开始日期", self.start_var, 0, 0, width=14)
        make_field(form, "结束日期（不含）", self.end_var, 0, 1, width=14)
        button = tk.Frame(form, bg=COLORS["card"])
        button.grid(row=0, column=2, padx=(12, 0), pady=(17, 0))
        ttk.Button(button, text="加载日历", command=self.refresh).pack()
        table_card = Card(self, padding=12)
        table_card.pack(fill="both", expand=True)
        self.table = DataTable(
            table_card.inner,
            [
                ("date", "日期", 105),
                ("room_type", "房型", 130),
                ("total", "总房量", 70),
                ("sold", "已售", 60),
                ("locked", "订单锁定", 80),
                ("group", "协议锁定", 80),
                ("available", "可售", 65),
                ("price", "售价", 100),
            ],
            height=12,
            on_double=lambda _: self.edit_price(),
        )
        self.table.pack(fill="both", expand=True)
        actions = tk.Frame(table_card.inner, bg=COLORS["card"])
        actions.pack(fill="x", pady=(10, 0))
        for text, command in (
            ("修改房价", self.edit_price),
            ("关房", self.close_rooms),
            ("库存修正", self.correct_stock),
            ("停售/恢复", self.toggle_room_type),
        ):
            ttk.Button(
                actions, text=text, style="Secondary.TButton", command=command
            ).pack(side="left", padx=(0, 6))
        tk.Label(
            actions,
            text="单价为最终成交价；改价仅影响新订单",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 8),
        ).pack(side="right")

    def refresh(self) -> None:
        try:
            start = parse_date_entry(self.start_var.get(), "开始日期")
            end = parse_date_entry(self.end_var.get(), "结束日期")
            self.rows = self.services.inventory.inventory_rows(
                self.host.hotel_id, start, end
            )
        except (DomainError, ValueError) as exc:
            show_error(self, str(exc))
            return
        self.table.set_rows(
            [
                {
                    "date": row["date"],
                    "room_type": row["room_type"],
                    "total": row["total"],
                    "sold": row["sold"],
                    "locked": row["locked"],
                    "group": row["group_locked"],
                    "available": row["available"],
                    "price": yuan(row["price"]),
                    "_tag": "warn" if int(row["available"]) <= 2 else "ok",
                    "_row": row,
                }
                for row in self.rows
            ]
        )

    def _selected(self) -> dict[str, object] | None:
        selected = self.table.selected_row()
        if not selected or "_row" not in selected:
            show_info(self, "请先选择一行库存", "提示")
            return None
        return selected["_row"]  # type: ignore[return-value]

    def _run(self, action: Callable[[], None], message: str) -> None:
        try:
            action()
        except (DomainError, ValueError) as exc:
            show_error(self, str(exc))
            return
        show_info(self, message, "操作成功")
        self.refresh()

    def edit_price(self) -> None:
        row = self._selected()
        if not row:
            return
        PriceDialog(
            self,
            lambda biz_date, price: self._run(
                lambda: self.services.inventory.set_price(
                    self.staff,
                    self.host.hotel_id,
                    str(row["room_type_id"]),
                    biz_date,
                    price,
                ),
                "价格已更新",
            ),
            parse_date_entry(str(row["date"]), "日期"),
            str(row["price"]),
        )

    def close_rooms(self) -> None:
        row = self._selected()
        if not row:
            return
        ClosureDialog(
            self,
            lambda start, end, reason: self._run(
                lambda: self.services.inventory.close_rooms(
                    self.staff,
                    self.host.hotel_id,
                    str(row["room_type_id"]),
                    start,
                    end,
                    reason,
                ),
                "关房设置已生效",
            ),
            parse_date_entry(str(row["date"]), "日期"),
        )

    def correct_stock(self) -> None:
        row = self._selected()
        if not row:
            return
        StockDialog(
            self,
            lambda total, reason: self._run(
                lambda: self.services.inventory.correct_total(
                    self.staff,
                    self.host.hotel_id,
                    str(row["room_type_id"]),
                    parse_date_entry(str(row["date"]), "日期"),
                    total,
                    reason,
                ),
                "库存已修正并留痕",
            ),
            int(row["total"]),
        )

    def toggle_room_type(self) -> None:
        row = self._selected()
        if not row:
            return
        room = self.services.catalog_repo.get_room_type(
            str(row["room_type_id"])
        )
        if not room:
            return
        status = (
            RoomTypeStatus.OFF_SALE
            if room.status is RoomTypeStatus.ON_SALE
            else RoomTypeStatus.ON_SALE
        )
        if confirm(
            self,
            "变更房型状态",
            f"将「{room.name}」设置为 {status.label}？",
        ):
            self._run(
                lambda: self.services.inventory.set_room_type_status(
                    self.staff, self.host.hotel_id, room.room_type_id, status
                ),
                f"房型已{status.label}",
            )


class GroupLockView(tk.Frame):
    """Protocol room lock list and operations."""

    def __init__(self, parent: tk.Misc, host: StaffShell) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.host = host
        self.services = host.services
        self.staff = host.staff
        self.font = choose_font(self)
        self.locks = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = PageHeader(
            self,
            "协议锁房",
            "为企业协议客户预留固定房源，到期自动释放，避免被散客误售。",
        )
        header.pack(fill="x", pady=(0, 12))
        ttk.Button(
            header.actions,
            text="释放到期锁房",
            style="Secondary.TButton",
            command=self.release_expired,
        ).pack(side="right", padx=(8, 0))
        ttk.Button(
            header.actions, text="新建协议锁房", command=self.create
        ).pack(side="right")
        card = Card(self, padding=12)
        card.pack(fill="both", expand=True)
        self.table = DataTable(
            card.inner,
            [
                ("lock_id", "锁房编号", 140),
                ("room_type", "房型", 130),
                ("dates", "日期", 175),
                ("qty", "间数", 65),
                ("release", "释放时间", 140),
                ("status", "状态", 90),
                ("note", "备注", 180),
            ],
            height=11,
            on_double=lambda _: self.release(),
        )
        self.table.pack(fill="both", expand=True)
        actions = tk.Frame(card.inner, bg=COLORS["card"])
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(
            actions,
            text="释放选中锁房",
            style="Secondary.TButton",
            command=self.release,
        ).pack(side="left")
        tk.Label(
            actions,
            text="协议锁房计入已占用库存，但不进入订单状态机",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 8),
        ).pack(side="right")

    def refresh(self) -> None:
        self.locks = self.services.inventory_repo.list_group_locks(
            self.host.hotel_id
        )
        room_types = {
            item.room_type_id: item.name
            for item in self.services.catalog.room_types(self.host.hotel_id)
        }
        self.table.set_rows(
            [
                {
                    "lock_id": lock.lock_id,
                    "room_type": room_types.get(
                        lock.room_type_id, lock.room_type_id
                    ),
                    "dates": f"{lock.start_date} ~ {lock.end_date}",
                    "qty": lock.qty,
                    "release": lock.release_at.strftime("%Y-%m-%d %H:%M"),
                    "status": lock.status.label,
                    "note": lock.note,
                    "_tag": "ok" if lock.is_active else "muted",
                    "_lock": lock,
                }
                for lock in self.locks
            ]
        )

    def create(self) -> None:
        GroupLockDialog(
            self,
            self.services,
            self.host.hotel_id,
            lambda room_type_id, start, end, qty, release_at, note: self._run(
                lambda: self.services.inventory.create_group_lock(
                    self.staff,
                    self.host.hotel_id,
                    room_type_id,
                    start,
                    end,
                    qty,
                    release_at,
                    note,
                ),
                "协议锁房已创建",
            ),
        )

    def release(self) -> None:
        row = self.table.selected_row()
        if not row or "_lock" not in row:
            show_info(self, "请先选择一条协议锁房", "提示")
            return
        lock = row["_lock"]
        if not lock.is_active:
            show_info(self, "该锁房已经释放", "提示")
            return
        if not confirm(self, "释放协议锁房", "释放后房源立即回到公开可售，继续？"):
            return
        self._run(
            lambda: self.services.inventory.release_group_lock(
                self.staff, lock.lock_id
            ),
            "协议锁房已释放",
        )

    def release_expired(self) -> None:
        count = self.services.inventory.release_expired_group_locks()
        show_info(self, f"已自动释放 {count} 条到期锁房", "处理完成")
        self.refresh()

    def _run(self, action: Callable[[], None], message: str) -> None:
        try:
            action()
        except DomainError as exc:
            show_error(self, str(exc))
            return
        show_info(self, message, "操作成功")
        self.refresh()


class RefundView(tk.Frame):
    """Refund review and approval, shared by staff and group portals."""

    def __init__(self, parent: tk.Misc, host) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent, bg=COLORS["bg"])
        self.host = host
        self.services = host.services
        self.staff = host.staff
        self.font = choose_font(self)
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = PageHeader(
            self,
            "退款审核",
            "单笔退款按首晚实际成交价判定：≤500 元自动通过，>500 元须店长审批。",
        )
        header.pack(fill="x", pady=(0, 12))
        ttk.Button(
            header.actions, text="刷新", command=self.refresh
        ).pack(side="right")
        card = Card(self, padding=12)
        card.pack(fill="both", expand=True)
        self.status_var = tk.StringVar(value="待审核")
        top = tk.Frame(card.inner, bg=COLORS["card"])
        top.pack(fill="x", pady=(0, 8))
        tk.Label(
            top,
            text="筛选",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 9),
        ).pack(side="left")
        ttk.Combobox(
            top,
            textvariable=self.status_var,
            values=["待审核", "全部"],
            state="readonly",
            width=12,
        ).pack(side="left", padx=8)
        ttk.Button(
            top,
            text="应用",
            style="Secondary.TButton",
            command=self.refresh,
        ).pack(side="left")
        self.table = DataTable(
            card.inner,
            [
                ("refund_no", "退款号", 150),
                ("order_no", "订单号", 175),
                ("amount", "退款金额", 100),
                ("first", "首晚成交价", 105),
                ("status", "状态", 115),
                ("requested", "申请人", 100),
                ("reason", "原因", 220),
                ("created", "时间", 140),
            ],
            height=10,
            on_double=lambda _: self.show_order(),
        )
        self.table.pack(fill="both", expand=True)
        actions = tk.Frame(card.inner, bg=COLORS["card"])
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(
            actions,
            text="通过",
            command=lambda: self.decide(True),
        ).pack(side="left")
        ttk.Button(
            actions,
            text="驳回",
            style="Danger.TButton",
            command=lambda: self.decide(False),
        ).pack(side="left", padx=8)
        ttk.Button(
            actions,
            text="查看关联订单",
            style="Secondary.TButton",
            command=self.show_order,
        ).pack(side="left")
        tk.Label(
            actions,
            text="审批后系统在 2 小时内提交支付渠道，到账 1–3 个工作日",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 8),
        ).pack(side="right")

    def refresh(self) -> None:
        status = (
            RefundStatus.PENDING_APPROVAL
            if self.status_var.get() == "待审核"
            else None
        )
        refunds = self.services.order_repo.list_refunds(status)
        visible: list[Refund] = []
        for refund in refunds:
            order = self.services.order_repo.get(refund.order_no)
            if not order:
                continue
            if not self.staff.can_access_hotel(order.hotel_id):
                continue
            visible.append(refund)
        self.table.set_rows(
            [
                {
                    "refund_no": refund.refund_no,
                    "order_no": refund.order_no,
                    "amount": yuan(refund.amount),
                    "first": yuan(refund.first_night_amount),
                    "status": refund.status.label,
                    "requested": refund.requested_by,
                    "reason": refund.reason,
                    "created": refund.created_at.strftime("%m-%d %H:%M"),
                    "_tag": (
                        "warn"
                        if refund.status is RefundStatus.PENDING_APPROVAL
                        else "ok"
                    ),
                    "_refund": refund,
                }
                for refund in visible
            ]
        )

    def decide(self, approve: bool) -> None:
        row = self.table.selected_row()
        if not row or "_refund" not in row:
            show_info(self, "请先选择一条退款记录", "提示")
            return
        refund = row["_refund"]
        if refund.status is not RefundStatus.PENDING_APPROVAL:
            show_info(self, "该退款已经处理", "提示")
            return
        action = "通过" if approve else "驳回"
        if not confirm(
            self, f"{action}退款", f"确认{action}退款 {yuan(refund.amount)}？"
        ):
            return
        try:
            self.services.refunds.decide(
                refund.refund_no, self.staff, approve=approve
            )
        except DomainError as exc:
            show_error(self, str(exc))
            return
        self.host.notify(f"退款已{action}", "success")
        self.refresh()

    def show_order(self) -> None:
        row = self.table.selected_row()
        if not row or "_refund" not in row:
            show_info(self, "请先选择一条退款记录", "提示")
            return
        order = self.services.order_repo.get(row["_refund"].order_no)
        if order:
            OrderDetailDialog(self, self.services, order)


class AuditLogView(tk.Frame):
    """Scoped, read-only audit log with CSV export."""

    def __init__(self, parent: tk.Misc, host) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent, bg=COLORS["bg"])
        self.host = host
        self.services = host.services
        self.staff = host.staff
        self.font = choose_font(self)
        self.logs = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = PageHeader(
            self,
            "操作日志",
            "日志不可修改、不可删除；店长仅能查看本门店记录。",
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
        card = Card(self, padding=12)
        card.pack(fill="x", pady=(0, 10))
        form = tk.Frame(card.inner, bg=COLORS["card"])
        form.pack(fill="x")
        self.action_var = tk.StringVar()
        self.order_var = tk.StringVar()
        make_field(form, "操作类型", self.action_var, 0, 0, width=18)
        make_field(form, "关联订单号", self.order_var, 0, 1, width=22)
        button = tk.Frame(form, bg=COLORS["card"])
        button.grid(row=0, column=2, padx=(12, 0), pady=(17, 0))
        ttk.Button(button, text="查询", command=self.refresh).pack()
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        table_card = Card(self, padding=12)
        table_card.pack(fill="both", expand=True)
        self.table = DataTable(
            table_card.inner,
            [
                ("time", "时间", 140),
                ("staff", "操作人", 85),
                ("action", "操作类型", 145),
                ("order", "订单号", 165),
                ("hotel", "门店", 115),
                ("result", "结果", 70),
                ("before", "修改前", 180),
                ("after", "修改后", 180),
            ],
            height=12,
        )
        self.table.pack(fill="both", expand=True)

    def refresh(self) -> None:
        self.logs = self.services.audit_repo.list_logs(
            self.staff,
            action=self.action_var.get().strip(),
            order_no=self.order_var.get().strip(),
            limit=500,
        )
        self.table.set_rows(
            [
                {
                    "time": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "staff": log.staff_name,
                    "action": log.action,
                    "order": log.order_no,
                    "hotel": log.hotel_id,
                    "result": log.result,
                    "before": log.before_data[:70],
                    "after": log.after_data[:70],
                    "_tag": "bad" if log.result != "SUCCESS" else "",
                }
                for log in self.logs
            ]
        )

    def export(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="导出操作日志",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
            initialfile=f"audit_{date.today():%Y%m%d}.csv",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "时间",
                    "操作人",
                    "操作类型",
                    "门店",
                    "订单号",
                    "结果",
                    "修改前",
                    "修改后",
                ]
            )
            for log in self.logs:
                writer.writerow(
                    [
                        log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        log.staff_name,
                        log.action,
                        log.hotel_id,
                        log.order_no,
                        log.result,
                        log.before_data,
                        log.after_data,
                    ]
                )
        show_info(self, f"已导出 {len(self.logs)} 条日志到\n{path}", "导出成功")
