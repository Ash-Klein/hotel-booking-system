"""Application dialogs: booking, order detail, check-in and inventory edits."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ..domain.enums import (
    ExceptionType,
    PayMode,
    RoomStatus,
)
from ..domain.errors import DomainError
from ..domain.models import Order, Quote, SearchResult, Staff
from ..domain.money import as_money, yuan
from ..services.app import Services
from .theme import COLORS
from .widgets import (
    DataTable,
    ModalDialog,
    ScrollableFrame,
    confirm,
    make_field,
    show_error,
    show_info,
)


def _date_text(value: date) -> str:
    """Format a date for display and form pre-fill."""
    return value.isoformat()


def parse_date_entry(text: str, field: str = "日期") -> date:
    """Parse a YYYY-MM-DD entry with a friendly error."""
    try:
        return date.fromisoformat(text.strip())
    except ValueError as exc:
        raise ValueError(f"{field}格式应为 YYYY-MM-DD") from exc


class RoomDetailDialog(ModalDialog):
    """Room photographs are out of scope; this dialog shows commercial detail."""

    def __init__(
        self,
        parent: tk.Misc,
        result: SearchResult,
        on_book: Callable[[SearchResult], None],
    ) -> None:
        super().__init__(
            parent,
            f"{result.hotel.name} · {result.room_type.name}",
            width=680,
            height=620,
        )
        self.result = result
        self.on_book = on_book
        for child in self.body.winfo_children():
            if isinstance(child, tk.Label) and child.cget("textvariable"):
                continue
            child.destroy()
        quote = result.quote
        title = tk.Label(
            self.body,
            text=f"{result.room_type.bed_type} · 可住 {result.room_type.capacity} 人",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 14, "bold"),
            anchor="w",
        )
        title.pack(fill="x")
        tk.Label(
            self.body,
            text=f"{result.hotel.city}{result.hotel.district} · {result.hotel.address}",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            anchor="w",
        ).pack(fill="x", pady=(4, 12))
        facts = tk.Frame(self.body, bg=COLORS["blue_light"])
        facts.pack(fill="x", pady=(0, 14))
        facts_text = [
            ("入住", quote.check_in.isoformat()),
            ("离店", quote.check_out.isoformat()),
            ("晚数", f"{quote.night_count} 晚"),
            ("总价", yuan(quote.total)),
        ]
        for index, (label, value) in enumerate(facts_text):
            cell = tk.Frame(facts, bg=COLORS["blue_light"])
            cell.grid(row=0, column=index, padx=18, pady=12, sticky="w")
            tk.Label(
                cell,
                text=label,
                bg=COLORS["blue_light"],
                fg=COLORS["muted"],
                font=("Microsoft YaHei UI", 8),
            ).pack(anchor="w")
            tk.Label(
                cell,
                text=value,
                bg=COLORS["blue_light"],
                fg=COLORS["navy"],
                font=("Microsoft YaHei UI", 11, "bold"),
            ).pack(anchor="w")
        tk.Label(
            self.body,
            text="每晚价格",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x")
        table = DataTable(
            self.body,
            [
                ("date", "日期", 140),
                ("price", "单价", 120),
                ("available", "剩余", 100),
                ("special", "特殊日期", 120),
            ],
            height=min(6, max(2, quote.night_count)),
        )
        table.pack(fill="both", expand=True, pady=(6, 12))
        table.set_rows(
            [
                {
                    "date": night.biz_date.isoformat(),
                    "price": yuan(night.unit_price),
                    "available": f"{night.available} 间",
                    "special": "是（取消扣首晚）" if night.is_special else "否",
                    "_tag": "warn" if night.is_special else "ok",
                }
                for night in quote.nights
            ]
        )
        note = (
            "取消政策：入住前 24 小时免费取消；24 小时内或当日取消扣首晚房费；"
            "特殊日期统一扣首晚 100%。"
        )
        tk.Label(
            self.body,
            text=note,
            bg=COLORS["accent_light"],
            fg="#5D4037",
            justify="left",
            wraplength=620,
            padx=10,
            pady=8,
            anchor="w",
        ).pack(fill="x")
        button_row = tk.Frame(self.body, bg=COLORS["card"])
        button_row.pack(fill="x", pady=(12, 0))
        ttk.Button(
            button_row,
            text="预订此房型",
            command=self._book,
        ).pack(side="right")
        ttk.Button(
            button_row,
            text="关闭",
            style="Secondary.TButton",
            command=self.close,
        ).pack(side="right", padx=(0, 8))
        if not quote.is_available:
            tk.Label(
                button_row,
                text=quote.reason,
                bg=COLORS["card"],
                fg=COLORS["red"],
            ).pack(side="left")

    def _book(self) -> None:
        self.close()
        self.on_book(self.result)


class BookingDialog(ModalDialog):
    """Create an order from a quotation and optionally pay immediately."""

    def __init__(
        self,
        parent: tk.Misc,
        services: Services,
        result: SearchResult,
        on_created: Callable[[Order], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            "确认预订",
            width=600,
            height=610,
            submit_text="提交订单",
            on_submit=self._create,
        )
        self.services = services
        self.result = result
        self.on_created = on_created
        quote = result.quote
        summary = tk.Frame(self.body, bg=COLORS["blue_light"])
        summary.pack(fill="x", pady=(0, 10))
        tk.Label(
            summary,
            text=f"{result.hotel.name} · {result.room_type.name}",
            bg=COLORS["blue_light"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 12, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 2))
        tk.Label(
            summary,
            text=(
                f"{quote.check_in} 至 {quote.check_out} · {quote.night_count} 晚 · "
                f"合计 {yuan(quote.total)}"
            ),
            bg=COLORS["blue_light"],
            fg=COLORS["muted"],
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 10))
        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        form = tk.Frame(self.body, bg=COLORS["card"])
        form.pack(fill="x")
        make_field(form, "入住人姓名", self.name_var, 0)
        make_field(form, "手机号", self.phone_var, 1)
        row = tk.Frame(self.body, bg=COLORS["card"])
        row.pack(fill="x", pady=5)
        self.qty_var = tk.IntVar(value=1)
        self.pay_var = tk.StringVar(value=PayMode.ONLINE.value)
        make_field(
            row,
            "间数",
            self.qty_var,
            0,
            0,
            width=10,
        )
        pay_holder = tk.Frame(row, bg=COLORS["card"])
        pay_holder.grid(row=0, column=1, sticky="ew", padx=6, pady=5)
        tk.Label(
            pay_holder,
            text="支付方式",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).pack(fill="x")
        ttk.Radiobutton(
            pay_holder,
            text="线上预付（锁房 15 分钟）",
            value=PayMode.ONLINE.value,
            variable=self.pay_var,
        ).pack(anchor="w")
        ttk.Radiobutton(
            pay_holder,
            text="到店现付（锁房 30 分钟）",
            value=PayMode.AT_HOTEL.value,
            variable=self.pay_var,
        ).pack(anchor="w")
        self.pay_now_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.body,
            text="创建后立即模拟支付（仅线上预付）",
            variable=self.pay_now_var,
            style="Card.TCheckbutton",
        ).pack(anchor="w", pady=(8, 0))
        tk.Label(
            self.body,
            text=(
                "提示：提交后将实时校验每日库存并锁定房间；"
                "未支付订单超时自动取消，库存自动释放。"
            ),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            wraplength=520,
            justify="left",
            padx=8,
            pady=6,
        ).pack(fill="x", pady=(14, 0))

    def _create(self) -> None:
        qty = int(self.qty_var.get() or 1)
        mode = PayMode(self.pay_var.get())
        order = self.services.booking.create_order(
            guest_name=self.name_var.get(),
            phone=self.phone_var.get(),
            hotel_id=self.result.hotel.hotel_id,
            room_type_id=self.result.room_type.room_type_id,
            check_in=self.result.quote.check_in,
            check_out=self.result.quote.check_out,
            qty=qty,
            pay_mode=mode,
        )
        if mode is PayMode.ONLINE and self.pay_now_var.get():
            order = self.services.booking.pay_order(order.order_no)
        show_info(
            self,
            (
                f"预订成功，订单号 {order.order_no}\n"
                f"状态：{order.status.label}\n"
                f"金额：{yuan(order.total_amount)}"
            ),
            "预订成功",
        )
        self.close()
        if self.on_created:
            self.on_created(order)


class ModifyOrderDialog(ModalDialog):
    """Change dates, room type and same-city hotel for a confirmed order."""

    def __init__(
        self,
        parent: tk.Misc,
        services: Services,
        order: Order,
        *,
        staff: Staff | None = None,
        guest_phone: str = "",
        on_changed: Callable[[Order], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            f"修改订单 {order.order_no}",
            width=620,
            height=570,
            submit_text="确认修改",
            on_submit=self._submit_change,
        )
        self.services = services
        self.order = order
        self.staff = staff
        self.guest_phone = guest_phone
        self.on_changed = on_changed
        self.hotel_map = {
            hotel.name: hotel
            for hotel in services.catalog.hotels(
                city=services.catalog.hotel(order.hotel_id).city
            )
        }
        self.hotel_var = tk.StringVar(value=order.hotel_name)
        self.room_var = tk.StringVar(value=order.room_type_name)
        self.check_in_var = tk.StringVar(value=order.check_in.isoformat())
        self.check_out_var = tk.StringVar(value=order.check_out.isoformat())
        form = tk.Frame(self.body, bg=COLORS["card"])
        form.pack(fill="x")
        self.hotel_box = make_field(
            form,
            "门店（仅同城）",
            self.hotel_var,
            0,
            values=list(self.hotel_map),
        )
        self.room_box = make_field(
            form,
            "房型",
            self.room_var,
            1,
            values=self._room_names(order.hotel_id),
        )
        self.room_box.bind("<<ComboboxSelected>>", lambda _: self._refresh_quote())
        make_field(form, "入住日期", self.check_in_var, 2)
        make_field(form, "离店日期", self.check_out_var, 3)
        ttk.Button(
            self.body,
            text="重新计算差价",
            style="Secondary.TButton",
            command=self._refresh_quote,
        ).pack(anchor="w", pady=8)
        self.quote_var = tk.StringVar(value="点击“重新计算差价”查看新价格")
        tk.Label(
            self.body,
            textvariable=self.quote_var,
            bg=COLORS["blue_light"],
            fg=COLORS["navy"],
            justify="left",
            anchor="w",
            padx=10,
            pady=10,
            wraplength=520,
        ).pack(fill="x")
        tk.Label(
            self.body,
            text="修改成功后原日期库存立即释放，新日期库存实时扣减。",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            anchor="w",
        ).pack(fill="x", pady=8)
        self.hotel_box.bind("<<ComboboxSelected>>", lambda _: self._hotel_changed())

    def _hotel_changed(self) -> None:
        hotel = self.hotel_map.get(self.hotel_var.get())
        if hotel:
            names = self._room_names(hotel.hotel_id)
            self.room_box.configure(values=names)  # type: ignore[call-arg]
            if names:
                self.room_var.set(names[0])

    def _room_names(self, hotel_id: str) -> list[str]:
        return [
            item.name for item in self.services.catalog.room_types(hotel_id)
        ]

    def _find_room(self, hotel_id: str) -> str:
        for room_type in self.services.catalog.room_types(hotel_id):
            if room_type.name == self.room_var.get():
                return room_type.room_type_id
        raise ValueError("请选择房型")

    def _refresh_quote(self) -> None:
        hotel = self.hotel_map.get(self.hotel_var.get())
        if not hotel:
            raise ValueError("请选择门店")
        room_type_id = self._find_room(hotel.hotel_id)
        check_in = parse_date_entry(self.check_in_var.get(), "入住日期")
        check_out = parse_date_entry(self.check_out_var.get(), "离店日期")
        quote = self.services.booking.quote(
            hotel.hotel_id, room_type_id, check_in, check_out, self.order.qty
        )
        if not quote.is_available:
            self.quote_var.set(f"不可修改：{quote.reason}")
            return
        delta = as_money(quote.total - self.order.total_amount)
        direction = "补差" if delta > 0 else "退款" if delta < 0 else "无差价"
        self.quote_var.set(
            f"{quote.night_count} 晚 · 新总价 {yuan(quote.total)} · "
            f"{direction} {yuan(abs(delta))}"
        )

    def _submit_change(self) -> None:
        hotel = self.hotel_map.get(self.hotel_var.get())
        if not hotel:
            raise ValueError("请选择门店")
        room_type_id = self._find_room(hotel.hotel_id)
        check_in = parse_date_entry(self.check_in_var.get(), "入住日期")
        check_out = parse_date_entry(self.check_out_var.get(), "离店日期")
        result = self.services.booking.modify_order(
            self.order.order_no,
            hotel_id=hotel.hotel_id,
            room_type_id=room_type_id,
            check_in=check_in,
            check_out=check_out,
            staff=self.staff,
            guest_phone=self.guest_phone,
        )
        show_info(
            self,
            f"修改成功，订单金额 {yuan(result['order'].total_amount)}",
            "改单成功",
        )
        self.close()
        if self.on_changed:
            self.on_changed(result["order"])


class CheckInDialog(ModalDialog):
    """Assign one physical room per active order room."""

    def __init__(
        self,
        parent: tk.Misc,
        services: Services,
        order: Order,
        staff: Staff,
        on_done: Callable[[Order], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            f"办理入住 · {order.order_no}",
            width=560,
            height=300 + 58 * max(order.active_qty - 1, 0),
            submit_text="确认入住",
            on_submit=self._check_in,
        )
        self.services = services
        self.order = order
        self.staff = staff
        self.on_done = on_done
        self.vars: list[tk.StringVar] = []
        rooms = [
            room
            for room in services.catalog_repo.list_rooms(
                order.hotel_id, order.room_type_id
            )
            if room.status is RoomStatus.AVAILABLE
        ]
        if not rooms:
            tk.Label(
                self.body,
                text="当前房型没有可用房号，请先在门店实际房源中处理。",
                bg=COLORS["card"],
                fg=COLORS["red"],
                wraplength=500,
            ).pack(fill="x")
            return
        tk.Label(
            self.body,
            text=(
                f"{order.contact_name} · {order.room_type_name} · "
                f"{order.active_qty} 间"
            ),
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 12, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))
        form = tk.Frame(self.body, bg=COLORS["card"])
        form.pack(fill="x")
        for index in range(order.active_qty):
            var = tk.StringVar(value=rooms[index].room_no)
            self.vars.append(var)
            make_field(
                form,
                f"第 {index + 1} 间房号",
                var,
                index,
                values=[room.room_no for room in rooms],
            )
        tk.Label(
            self.body,
            text="核对客人身份证件后分配房号；房号分配不改变房型库存。",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            wraplength=490,
            anchor="w",
            padx=8,
            pady=6,
        ).pack(fill="x", pady=10)

    def _check_in(self) -> None:
        if not self.vars:
            raise ValueError("当前没有可分配房号，无法办理入住")
        numbers = [var.get() for var in self.vars]
        if len(set(numbers)) != len(numbers):
            raise ValueError("房号不能重复")
        order = self.services.fulfillment.check_in(
            self.order.order_no, numbers, self.staff
        )
        show_info(self, f"入住办理完成，房号 {order.assigned_rooms}", "办理成功")
        self.close()
        if self.on_done:
            self.on_done(order)


class ExceptionDialog(ModalDialog):
    """Record a no-room / hotel-closed exception with compensation."""

    def __init__(
        self,
        parent: tk.Misc,
        services: Services,
        order: Order,
        staff: Staff,
        on_done: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            f"标记异常订单 · {order.order_no}",
            width=560,
            height=420,
            submit_text="提交集团审核",
            on_submit=self._submit_exception,
        )
        self.services = services
        self.order = order
        self.staff = staff
        self.on_done = on_done
        self.type_map = {item.label: item for item in ExceptionType}
        self.type_var = tk.StringVar(value=ExceptionType.NO_ROOM.label)
        self.desc_var = tk.StringVar(
            value="客人到店后无可用房，已协调同城门店安置"
        )
        self.amount_var = tk.StringVar(value="0.00")
        form = tk.Frame(self.body, bg=COLORS["card"])
        form.pack(fill="x")
        make_field(
            form,
            "异常类型",
            self.type_var,
            0,
            values=list(self.type_map),
        )
        make_field(form, "异常说明", self.desc_var, 1)
        make_field(form, "赔付/安置费用", self.amount_var, 2)
        tk.Label(
            self.body,
            text="提交后订单进入异常状态，集团审核前不得自动取消或退款。",
            bg=COLORS["accent_light"],
            fg="#5D4037",
            wraplength=480,
            justify="left",
            padx=10,
            pady=8,
            anchor="w",
        ).pack(fill="x", pady=12)

    def _submit_exception(self) -> None:
        exception_type = self.type_map[self.type_var.get()]
        self.services.fulfillment.mark_exception(
            self.order.order_no,
            self.staff,
            exception_type=exception_type,
            description=self.desc_var.get(),
            compensation=as_money(self.amount_var.get() or "0"),
        )
        show_info(self, "异常订单已提交集团审核", "提交成功")
        self.close()
        if self.on_done:
            self.on_done()


class OrderDetailDialog(ModalDialog):
    """Read-only order detail with payments and change history."""

    def __init__(
        self, parent: tk.Misc, services: Services, order: Order
    ) -> None:
        super().__init__(
            parent,
            f"订单详情 · {order.order_no}",
            width=760,
            height=650,
        )
        self.services = services
        self.order = order
        for child in self.body.winfo_children():
            if isinstance(child, tk.Label) and child.cget("textvariable"):
                continue
            child.destroy()
        header = tk.Frame(self.body, bg=COLORS["blue_light"])
        header.pack(fill="x", pady=(0, 12))
        tk.Label(
            header,
            text=f"{order.hotel_name} · {order.room_type_name}",
            bg=COLORS["blue_light"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 2))
        tk.Label(
            header,
            text=(
                f"{order.check_in} 至 {order.check_out} · {order.nights} 晚 · "
                f"{order.qty} 间 · {order.status.label}"
            ),
            bg=COLORS["blue_light"],
            fg=COLORS["muted"],
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 10))
        fields = [
            ("入住人", order.contact_name),
            ("手机号", order.contact_phone),
            ("支付方式", order.pay_mode.label),
            ("订单金额", yuan(order.total_amount)),
            ("房号", order.assigned_rooms or "未分配"),
            ("创建时间", order.created_at.strftime("%Y-%m-%d %H:%M")),
        ]
        grid = tk.Frame(self.body, bg=COLORS["card"])
        grid.pack(fill="x")
        for index, (label, value) in enumerate(fields):
            row, column = divmod(index, 2)
            cell = tk.Frame(grid, bg=COLORS["card"])
            cell.grid(row=row, column=column, sticky="w", padx=8, pady=4)
            tk.Label(
                cell,
                text=label,
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=("Microsoft YaHei UI", 8),
                anchor="w",
            ).pack(anchor="w")
            tk.Label(
                cell,
                text=value,
                bg=COLORS["card"],
                fg=COLORS["text"],
                font=("Microsoft YaHei UI", 10, "bold"),
                anchor="w",
            ).pack(anchor="w")
        ttk.Separator(self.body).pack(fill="x", pady=12)
        tk.Label(
            self.body,
            text="支付流水",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x")
        payment_table = DataTable(
            self.body,
            [
                ("payment_no", "流水号", 200),
                ("amount", "金额", 100),
                ("method", "方式", 100),
                ("status", "状态", 100),
                ("paid_at", "时间", 150),
            ],
            height=3,
        )
        payment_table.pack(fill="x", pady=6)
        payment_table.set_rows(
            [
                {
                    "payment_no": payment.payment_no,
                    "amount": yuan(payment.amount),
                    "method": payment.method,
                    "status": payment.status.label,
                    "paid_at": (
                        payment.paid_at.strftime("%Y-%m-%d %H:%M")
                        if payment.paid_at
                        else "-"
                    ),
                    "_tag": "ok" if payment.paid_at else "warn",
                }
                for payment in services.order_repo.list_payments(order.order_no)
            ]
        )
        tk.Label(
            self.body,
            text="改单记录",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(8, 0))
        change_table = DataTable(
            self.body,
            [
                ("time", "时间", 150),
                ("before", "修改前", 220),
                ("after", "修改后", 220),
                ("delta", "差额", 100),
            ],
            height=3,
        )
        change_table.pack(fill="both", expand=True, pady=6)
        change_table.set_rows(
            [
                {
                    "time": change.created_at.strftime("%Y-%m-%d %H:%M"),
                    "before": change.before_data[:48],
                    "after": change.after_data[:48],
                    "delta": yuan(change.amount_delta),
                }
                for change in services.order_repo.list_changes(order.order_no)
            ]
        )
        if not services.order_repo.list_changes(order.order_no):
            change_table.set_rows(
                [{"time": "暂无", "before": "", "after": "", "delta": ""}]
            )
        ttk.Button(
            self.body,
            text="关闭",
            style="Secondary.TButton",
            command=self.close,
        ).pack(anchor="e", pady=(8, 0))


class PriceDialog(ModalDialog):
    """Set one nightly price."""

    def __init__(
        self,
        parent: tk.Misc,
        on_submit: Callable[[date, Decimal], None],
        default_date: date,
        current_price: str,
    ) -> None:
        super().__init__(
            parent,
            "修改每日价格",
            width=460,
            height=330,
            submit_text="保存价格",
            on_submit=lambda: self._save(on_submit),
        )
        self.date_var = tk.StringVar(value=default_date.isoformat())
        self.price_var = tk.StringVar(value=current_price)
        form = tk.Frame(self.body, bg=COLORS["card"])
        form.pack(fill="x")
        make_field(form, "业务日期", self.date_var, 0)
        make_field(form, "最终售价（元）", self.price_var, 1)
        tk.Label(
            self.body,
            text="修改只影响之后的新订单，历史成交价已锁定在订单快照中。",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            wraplength=400,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=12)

    def _save(self, callback: Callable[[date, Decimal], None]) -> None:
        callback(
            parse_date_entry(self.date_var.get(), "业务日期"),
            as_money(self.price_var.get()),
        )
        self.close()


class ClosureDialog(ModalDialog):
    """Close a room type for new bookings."""

    def __init__(
        self,
        parent: tk.Misc,
        on_submit: Callable[[date, date, str], None],
        start: date,
    ) -> None:
        super().__init__(
            parent,
            "关房设置",
            width=480,
            height=380,
            submit_text="确认关房",
            on_submit=lambda: self._save(on_submit),
        )
        self.start_var = tk.StringVar(value=start.isoformat())
        self.end_var = tk.StringVar(value=(start + timedelta(days=1)).isoformat())
        self.reason_var = tk.StringVar(value="设备维护")
        form = tk.Frame(self.body, bg=COLORS["card"])
        form.pack(fill="x")
        make_field(form, "开始日期（含）", self.start_var, 0)
        make_field(form, "结束日期（不含）", self.end_var, 1)
        make_field(form, "关房原因", self.reason_var, 2)
        tk.Label(
            self.body,
            text=(
                "关房只阻止之后的新预订，已支付订单不受影响；"
                "关房期间仍可接待存量订单。"
            ),
            bg=COLORS["accent_light"],
            fg="#5D4037",
            wraplength=410,
            justify="left",
            padx=10,
            pady=8,
            anchor="w",
        ).pack(fill="x", pady=12)

    def _save(self, callback: Callable[[date, date, str], None]) -> None:
        callback(
            parse_date_entry(self.start_var.get(), "开始日期"),
            parse_date_entry(self.end_var.get(), "结束日期"),
            self.reason_var.get(),
        )
        self.close()


class StockDialog(ModalDialog):
    """Correct physical room count with an audit reason."""

    def __init__(
        self,
        parent: tk.Misc,
        on_submit: Callable[[int, str], None],
        current_total: int,
    ) -> None:
        super().__init__(
            parent,
            "库存修正",
            width=460,
            height=340,
            submit_text="提交修正",
            on_submit=lambda: self._save(on_submit),
        )
        self.total_var = tk.StringVar(value=str(current_total))
        self.reason_var = tk.StringVar()
        form = tk.Frame(self.body, bg=COLORS["card"])
        form.pack(fill="x")
        make_field(form, "修正后总房量", self.total_var, 0)
        make_field(form, "修正原因", self.reason_var, 1)
        tk.Label(
            self.body,
            text="修正后的总数不得小于已售、锁定与协议占用之和，操作全程留痕。",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            wraplength=400,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=12)

    def _save(self, callback: Callable[[int, str], None]) -> None:
        callback(int(self.total_var.get()), self.reason_var.get())
        self.close()


class GroupLockDialog(ModalDialog):
    """Create a corporate protocol room lock."""

    def __init__(
        self,
        parent: tk.Misc,
        services: Services,
        hotel_id: str,
        on_submit: Callable[[str, date, date, int, datetime, str], None],
    ) -> None:
        super().__init__(
            parent,
            "新建协议锁房",
            width=540,
            height=590,
            submit_text="锁定房源",
            on_submit=lambda: self._save(on_submit),
        )
        self.services = services
        self.hotel_id = hotel_id
        self.room_types = {
            item.name: item
            for item in services.catalog.room_types(hotel_id)
        }
        self.room_var = tk.StringVar(
            value=next(iter(self.room_types), "")
        )
        self.start_var = tk.StringVar(value=date.today().isoformat())
        self.end_var = tk.StringVar(
            value=(date.today() + timedelta(days=2)).isoformat()
        )
        self.qty_var = tk.StringVar(value="2")
        self.release_var = tk.StringVar(
            value=(date.today() + timedelta(days=3)).isoformat() + " 18:00"
        )
        self.note_var = tk.StringVar(value="企业协议客户预留")
        form = tk.Frame(self.body, bg=COLORS["card"])
        form.pack(fill="x")
        make_field(
            form,
            "房型",
            self.room_var,
            0,
            values=list(self.room_types),
        )
        make_field(form, "开始日期（含）", self.start_var, 1)
        make_field(form, "结束日期（不含）", self.end_var, 2)
        make_field(form, "锁定间数", self.qty_var, 3)
        make_field(form, "自动释放时间", self.release_var, 4)
        make_field(form, "备注", self.note_var, 5)
        tk.Label(
            self.body,
            text="锁房期间普通客人不可预订被锁定房源，到期自动释放。",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            wraplength=460,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=10)

    def _save(
        self,
        callback: Callable[[str, date, date, int, datetime, str], None],
    ) -> None:
        room = self.room_types.get(self.room_var.get())
        if not room:
            raise ValueError("请选择房型")
        try:
            release_at = datetime.strptime(
                self.release_var.get().strip(), "%Y-%m-%d %H:%M"
            )
        except ValueError as exc:
            raise ValueError("释放时间格式应为 YYYY-MM-DD HH:MM") from exc
        callback(
            room.room_type_id,
            parse_date_entry(self.start_var.get(), "开始日期"),
            parse_date_entry(self.end_var.get(), "结束日期"),
            int(self.qty_var.get()),
            release_at,
            self.note_var.get(),
        )
        self.close()


class ResolveExceptionDialog(ModalDialog):
    """Group-level exception decision."""

    def __init__(
        self,
        parent: tk.Misc,
        on_submit: Callable[[bool, str], None],
        order_no: str,
        amount: str,
    ) -> None:
        super().__init__(
            parent,
            f"裁决异常订单 · {order_no}",
            width=500,
            height=360,
            submit_text="确认裁决",
            on_submit=lambda: self._save(on_submit),
        )
        self.note_var = tk.StringVar(value="已与客人协商并完成安置")
        self.cancel_var = tk.BooleanVar(value=True)
        tk.Label(
            self.body,
            text=f"赔付/安置费用：{amount}",
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x")
        ttk.Checkbutton(
            self.body,
            text="取消订单并全额退款（否则按正常离店归档）",
            variable=self.cancel_var,
        ).pack(anchor="w", pady=10)
        form = tk.Frame(self.body, bg=COLORS["card"])
        form.pack(fill="x")
        make_field(form, "裁决说明", self.note_var, 0)
        tk.Label(
            self.body,
            text="异常订单不计入正常出租率，但全程保留在异常台账中。",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            wraplength=420,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=10)

    def _save(self, callback: Callable[[bool, str], None]) -> None:
        callback(self.cancel_var.get(), self.note_var.get())
        self.close()
