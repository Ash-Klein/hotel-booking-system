"""Guest-facing portal: search, room detail, booking and self-service orders."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import simpledialog, ttk
from typing import TYPE_CHECKING

from ..domain.enums import OrderStatus, PayMode
from ..domain.errors import DomainError
from ..domain.models import Order, SearchResult
from ..domain.money import yuan
from .dialogs import (
    BookingDialog,
    ModifyOrderDialog,
    OrderDetailDialog,
    RoomDetailDialog,
    parse_date_entry,
)
from .theme import COLORS, choose_font
from .widgets import (
    Card,
    DataTable,
    PageHeader,
    confirm,
    make_field,
    show_error,
    show_info,
)

if TYPE_CHECKING:
    from .app import HotelBookingApp


class GuestPortal(tk.Frame):
    """Header plus a small tab switch for the guest journey."""

    def __init__(
        self,
        parent: tk.Misc,
        app: "HotelBookingApp",
        initial_tab: str = "search",
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self.services = app.services
        self.font = choose_font(self)
        self._build_header()
        self.content = tk.Frame(self, bg=COLORS["bg"])
        self.content.pack(fill="both", expand=True, padx=30, pady=20)
        self.search_view: GuestSearchView | None = None
        self.orders_view: GuestOrdersView | None = None
        if initial_tab == "orders":
            self.show_orders()
        else:
            self.show_search()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=COLORS["navy"], height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        brand = tk.Frame(header, bg=COLORS["navy"])
        brand.pack(side="left", padx=30)
        tk.Label(
            brand,
            text="云栖",
            bg=COLORS["navy"],
            fg=COLORS["accent"],
            font=(self.font, 20, "bold"),
        ).pack(side="left")
        tk.Label(
            brand,
            text="  酒店预订",
            bg=COLORS["navy"],
            fg=COLORS["white"],
            font=(self.font, 14),
        ).pack(side="left", padx=(4, 0))
        tabs = tk.Frame(header, bg=COLORS["navy"])
        tabs.pack(side="left", padx=40)
        self.tab_buttons: dict[str, tk.Button] = {}
        for key, label in (("search", "查房预订"), ("orders", "我的订单")):
            button = tk.Button(
                tabs,
                text=label,
                bg=COLORS["navy"],
                fg="#C8D4E0",
                activebackground=COLORS["navy_light"],
                activeforeground=COLORS["white"],
                bd=0,
                padx=16,
                pady=8,
                font=(self.font, 11),
                cursor="hand2",
                command=(
                    self.show_search if key == "search" else self.show_orders
                ),
            )
            button.pack(side="left", padx=2)
            self.tab_buttons[key] = button
        tk.Button(
            header,
            text="员工登录  →",
            bg=COLORS["navy"],
            fg=COLORS["accent"],
            activebackground=COLORS["navy_light"],
            activeforeground=COLORS["white"],
            bd=0,
            padx=20,
            font=(self.font, 10),
            cursor="hand2",
            command=self.app.show_login,
        ).pack(side="right", padx=30)

    def _activate(self, key: str) -> None:
        for name, button in self.tab_buttons.items():
            button.configure(
                bg=COLORS["blue"] if name == key else COLORS["navy"],
                fg=COLORS["white"] if name == key else "#C8D4E0",
            )

    def show_search(self) -> None:
        """Show the room search tab."""
        self._activate("search")
        for child in self.content.winfo_children():
            child.destroy()
        self.search_view = GuestSearchView(self.content, self)
        self.search_view.pack(fill="both", expand=True)

    def show_orders(self, phone: str = "") -> None:
        """Show the order lookup tab, optionally pre-filling a phone."""
        self._activate("orders")
        for child in self.content.winfo_children():
            child.destroy()
        self.orders_view = GuestOrdersView(self.content, self, phone)
        self.orders_view.pack(fill="both", expand=True)


class GuestSearchView(tk.Frame):
    """Multi-condition room search backed by real inventory."""

    def __init__(self, parent: tk.Misc, portal: GuestPortal) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.portal = portal
        self.app = portal.app
        self.services = portal.services
        self.font = choose_font(self)
        self.results: list[SearchResult] = []
        self._build_header()
        self._build_filters()
        self._build_results()
        self.after(80, self.search)

    def _build_header(self) -> None:
        header = PageHeader(
            self,
            "找到合适的房间",
            "填写日期与人数，系统会逐晚校验库存，任意一晚不足则整单不可订。",
        )
        header.pack(fill="x", pady=(0, 12))
        tk.Label(
            header.actions,
            text="无需登录 · 实时库存",
            bg=COLORS["green_light"],
            fg=COLORS["green"],
            font=(self.font, 9, "bold"),
            padx=10,
            pady=5,
        ).pack()

    def _build_filters(self) -> None:
        card = Card(self, padding=14)
        card.pack(fill="x", pady=(0, 12))
        form = tk.Frame(card.inner, bg=COLORS["card"])
        form.pack(fill="x")
        self.city_var = tk.StringVar(value="全部城市")
        self.check_in_var = tk.StringVar(
            value=(date.today() + timedelta(days=1)).isoformat()
        )
        self.check_out_var = tk.StringVar(
            value=(date.today() + timedelta(days=2)).isoformat()
        )
        self.guests_var = tk.StringVar(value="2")
        self.price_var = tk.StringVar(value="")
        self.breakfast_var = tk.BooleanVar(value=False)
        cities = ["全部城市", *self.services.catalog.cities()]
        make_field(
            form, "城市", self.city_var, 0, 0, width=14, values=cities
        )
        make_field(form, "入住日期", self.check_in_var, 0, 1, width=14)
        make_field(form, "离店日期", self.check_out_var, 0, 2, width=14)
        make_field(
            form,
            "入住人数",
            self.guests_var,
            0,
            3,
            width=8,
            values=[str(index) for index in range(1, 7)],
        )
        make_field(form, "每晚最高价", self.price_var, 0, 4, width=12)
        check_holder = tk.Frame(form, bg=COLORS["card"])
        check_holder.grid(row=0, column=5, padx=6, pady=5, sticky="w")
        tk.Label(
            check_holder,
            text="早餐",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 9),
            anchor="w",
        ).pack(fill="x")
        ttk.Checkbutton(
            check_holder,
            text="仅含早",
            variable=self.breakfast_var,
            style="Card.TCheckbutton",
        ).pack(anchor="w", pady=(6, 0))
        button_holder = tk.Frame(form, bg=COLORS["card"])
        button_holder.grid(row=0, column=6, padx=(14, 4), pady=(17, 0))
        ttk.Button(
            button_holder,
            text="查询空房",
            command=self.search,
        ).pack(fill="x")
        for column in range(5):
            form.grid_columnconfigure(column, weight=1)

    def _build_results(self) -> None:
        card = Card(self, padding=12)
        card.pack(fill="both", expand=True)
        top = tk.Frame(card.inner, bg=COLORS["card"])
        top.pack(fill="x", pady=(0, 8))
        self.summary_var = tk.StringVar(value="正在查询…")
        tk.Label(
            top,
            textvariable=self.summary_var,
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=(self.font, 11, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            top,
            text="总价 = 每晚成交价 × 间数；显示价格为每晚单价",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 8),
        ).pack(side="right")
        self.table = DataTable(
            card.inner,
            [
                ("hotel", "门店", 180),
                ("room_type", "房型", 150),
                ("bed", "床型", 150),
                ("price", "每晚起", 100),
                ("nights", "晚数", 60),
                ("total", "总价", 100),
                ("available", "可订", 80),
                ("status", "状态", 150),
            ],
            height=11,
            on_double=lambda _: self.open_detail(),
        )
        self.table.pack(fill="both", expand=True)
        actions = tk.Frame(card.inner, bg=COLORS["card"])
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(
            actions,
            text="查看房型详情",
            style="Secondary.TButton",
            command=self.open_detail,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="立即预订",
            command=self.book_selected,
        ).pack(side="left", padx=8)
        tk.Label(
            actions,
            text="双击结果行也可以查看每晚价格与取消政策",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 8),
        ).pack(side="right")

    def search(self) -> None:
        """Run the query and render the result table."""
        try:
            city = self.city_var.get()
            city = "" if city == "全部城市" else city
            check_in = parse_date_entry(self.check_in_var.get(), "入住日期")
            check_out = parse_date_entry(self.check_out_var.get(), "离店日期")
            guests = int(self.guests_var.get())
            max_price: Decimal | None = None
            if self.price_var.get().strip():
                try:
                    max_price = Decimal(self.price_var.get().strip())
                except InvalidOperation as exc:
                    raise ValueError("每晚最高价格式不正确") from exc
            results = self.services.catalog.search(
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                city=city,
                max_price=max_price,
                breakfast_only=self.breakfast_var.get(),
            )
        except (DomainError, ValueError) as exc:
            self.summary_var.set(str(exc))
            self.table.clear()
            return
        self.results = results
        rows: list[dict[str, object]] = []
        for result in results:
            quote = result.quote
            rows.append(
                {
                    "hotel": f"{result.hotel.name} · {result.hotel.district}",
                    "room_type": result.room_type.name,
                    "bed": result.room_type.bed_type,
                    "price": yuan(min(night.unit_price for night in quote.nights))
                    if quote.nights
                    else "-",
                    "nights": quote.night_count,
                    "total": yuan(quote.total),
                    "available": f"{quote.min_available} 间",
                    "status": "可预订" if quote.is_available else quote.reason,
                    "_tag": "ok" if quote.is_available else "bad",
                    "_result": result,
                }
            )
        if not rows:
            rows.append(
                {
                    "hotel": "暂无可预订房源",
                    "room_type": "可尝试调整日期、城市或价格条件",
                    "bed": "",
                    "price": "",
                    "nights": "",
                    "total": "",
                    "available": "",
                    "status": "无结果",
                    "_tag": "muted",
                }
            )
        self.table.set_rows(rows)
        available = sum(1 for item in results if item.available)
        self.summary_var.set(
            f"共 {len(results)} 个房型 · {available} 个可订 · "
            f"{check_in} 至 {check_out}"
        )

    def _selected_result(self) -> SearchResult | None:
        row = self.table.selected_row()
        if not row or "_result" not in row:
            show_info(self, "请先选择一条查询结果", "提示")
            return None
        return row["_result"]  # type: ignore[return-value]

    def open_detail(self) -> None:
        """Open the room detail dialog for the selected row."""
        result = self._selected_result()
        if not result:
            return
        RoomDetailDialog(self, result, self.open_booking)

    def book_selected(self) -> None:
        """Jump straight to the booking dialog."""
        result = self._selected_result()
        if not result:
            return
        if not result.quote.is_available:
            show_error(self, result.quote.reason or "该房型当前不可预订")
            return
        self.open_booking(result)

    def open_booking(self, result: SearchResult) -> None:
        """Open the booking form for a selected result."""
        BookingDialog(
            self,
            self.services,
            result,
            on_created=lambda order: self.app.open_guest_orders(
                order.contact_phone
            ),
        )


class GuestOrdersView(tk.Frame):
    """Phone-based order lookup and guest self-service."""

    def __init__(
        self, parent: tk.Misc, portal: GuestPortal, phone: str = ""
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.portal = portal
        self.app = portal.app
        self.services = portal.services
        self.font = choose_font(self)
        self.orders: list[Order] = []
        self._build_header()
        self._build_filters(phone)
        self._build_table()
        if phone:
            self.after(80, self.search)

    def _build_header(self) -> None:
        header = PageHeader(
            self,
            "我的订单",
            "输入预订时使用的手机号查询订单；支付、取消与改期均在此完成。",
        )
        header.pack(fill="x", pady=(0, 12))

    def _build_filters(self, phone: str) -> None:
        card = Card(self, padding=14)
        card.pack(fill="x", pady=(0, 12))
        form = tk.Frame(card.inner, bg=COLORS["card"])
        form.pack(fill="x")
        self.phone_var = tk.StringVar(value=phone)
        self.order_var = tk.StringVar()
        make_field(form, "手机号", self.phone_var, 0, 0, width=18)
        make_field(form, "订单号（可选）", self.order_var, 0, 1, width=22)
        button = tk.Frame(form, bg=COLORS["card"])
        button.grid(row=0, column=2, padx=(12, 0), pady=(17, 0))
        ttk.Button(button, text="查询订单", command=self.search).pack()
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)

    def _build_table(self) -> None:
        card = Card(self, padding=12)
        card.pack(fill="both", expand=True)
        self.summary_var = tk.StringVar(value="输入手机号后点击查询")
        tk.Label(
            card.inner,
            textvariable=self.summary_var,
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=(self.font, 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        self.table = DataTable(
            card.inner,
            [
                ("order_no", "订单号", 190),
                ("hotel", "门店", 150),
                ("room_type", "房型", 120),
                ("dates", "入住 / 离店", 190),
                ("qty", "间数", 60),
                ("amount", "金额", 100),
                ("status", "状态", 120),
                ("created", "下单时间", 140),
            ],
            height=10,
            on_double=lambda _: self.show_detail(),
        )
        self.table.pack(fill="both", expand=True)
        actions = tk.Frame(card.inner, bg=COLORS["card"])
        actions.pack(fill="x", pady=(10, 0))
        for text, command in (
            ("去支付", self.pay_selected),
            ("查看详情", self.show_detail),
            ("修改订单", self.modify_selected),
            ("取消订单", self.cancel_selected),
        ):
            style = "Secondary.TButton" if text != "去支付" else "TButton"
            ttk.Button(
                actions, text=text, style=style, command=command
            ).pack(side="left", padx=(0, 8))
        tk.Label(
            actions,
            text="取消费用按入住前 24 小时规则自动计算",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(self.font, 8),
        ).pack(side="right")

    def search(self) -> None:
        """Look up orders for the entered phone number."""
        phone = self.phone_var.get().strip()
        if not phone:
            self.summary_var.set("请先输入预订手机号")
            self.table.clear()
            return
        guest = self.services.order_repo.find_guest_by_phone(None, phone)
        if not guest:
            self.summary_var.set("没有找到该手机号对应的订单")
            self.table.clear()
            return
        orders = self.services.order_repo.list_for_guest(guest.guest_id)
        order_no = self.order_var.get().strip().upper()
        if order_no:
            orders = [order for order in orders if order_no in order.order_no]
        self.orders = orders
        rows = [self._row(order) for order in orders]
        if not rows:
            rows = [{"order_no": "暂无订单", "status": "", "_tag": "muted"}]
        self.table.set_rows(rows)
        self.summary_var.set(
            f"共 {len(orders)} 笔订单 · 手机号 {guest.phone_masked}"
        )

    @staticmethod
    def _row(order: Order) -> dict[str, object]:
        tag = {
            OrderStatus.CANCELLED: "muted",
            OrderStatus.CHECKED_OUT: "ok",
            OrderStatus.PENDING_PAYMENT: "warn",
            OrderStatus.EXCEPTION: "bad",
            OrderStatus.NO_SHOW: "bad",
        }.get(order.status, "")
        return {
            "order_no": order.order_no,
            "hotel": order.hotel_name,
            "room_type": order.room_type_name,
            "dates": f"{order.check_in} / {order.check_out}",
            "qty": order.qty,
            "amount": yuan(order.total_amount),
            "status": order.status.label,
            "created": order.created_at.strftime("%m-%d %H:%M"),
            "_tag": tag,
            "_order": order,
        }

    def _selected_order(self) -> Order | None:
        row = self.table.selected_row()
        if not row or "_order" not in row:
            show_info(self, "请先选择一笔订单", "提示")
            return None
        return row["_order"]  # type: ignore[return-value]

    def pay_selected(self) -> None:
        """Pay a pending online order."""
        order = self._selected_order()
        if not order:
            return
        if order.status is not OrderStatus.PENDING_PAYMENT:
            show_info(self, "该订单当前无需支付", "提示")
            return
        if order.pay_mode is not PayMode.ONLINE:
            show_info(self, "到店现付订单请等待前台确认", "提示")
            return
        if not confirm(self, "确认支付", f"确认支付 {yuan(order.total_amount)}？"):
            return
        try:
            paid = self.services.booking.pay_order(order.order_no, "WECHAT")
        except DomainError as exc:
            show_error(self, str(exc))
            self.search()
            return
        show_info(
            self, f"支付成功，订单状态：{paid.status.label}", "支付成功"
        )
        self.search()

    def cancel_selected(self) -> None:
        """Cancel an order with a mandatory reason."""
        order = self._selected_order()
        if not order:
            return
        reason = simpledialog.askstring(
            "取消订单",
            "请填写取消原因（至少 2 个字）：",
            parent=self,
        )
        if not reason:
            return
        if not confirm(
            self,
            "确认取消",
            "取消后库存立即释放。入住前 24 小时内取消将扣除首晚房费，是否继续？",
        ):
            return
        try:
            result = self.services.booking.cancel_order(
                order.order_no,
                reason=reason,
                guest_phone=self.phone_var.get().strip(),
            )
        except DomainError as exc:
            show_error(self, str(exc))
            return
        refund = result["refund"]
        message = (
            f"订单已取消。\n违约金：{yuan(result['penalty'])}"
            f"\n退款金额：{yuan(result['refund_amount'])}"
        )
        if refund:
            message += f"\n退款状态：{refund.status.label}（原路退回）"
        show_info(self, message, "取消成功")
        self.search()

    def modify_selected(self) -> None:
        """Open the self-service modification dialog."""
        order = self._selected_order()
        if not order:
            return
        if not order.can_modify:
            show_info(self, "仅已确认待入住的订单可以修改", "提示")
            return
        ModifyOrderDialog(
            self,
            self.services,
            order,
            guest_phone=self.phone_var.get().strip(),
            on_changed=lambda _: self.search(),
        )

    def show_detail(self) -> None:
        """Show read-only order details."""
        order = self._selected_order()
        if order:
            OrderDetailDialog(self, self.services, order)
