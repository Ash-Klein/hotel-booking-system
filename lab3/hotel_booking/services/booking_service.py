"""Booking, payment, cancellation and order-change use cases."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json
import re
import sqlite3

from ..domain.enums import (
    OrderStatus,
    PayMode,
    PaymentStatus,
    RefundStatus,
    Terminal,
)
from ..domain.errors import (
    ConflictError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from ..domain.models import (
    Cancellation,
    Guest,
    Order,
    OrderChange,
    OrderItem,
    Payment,
    Quote,
    Refund,
    Staff,
    make_expiry,
)
from ..domain.money import as_money, date_range, money_text
from ..infrastructure.database import Database
from ..infrastructure.security import new_token
from ..repositories.audit_repository import AuditRepository
from ..repositories.catalog_repository import CatalogRepository
from ..repositories.inventory_repository import InventoryRepository
from ..repositories.order_repository import OrderRepository
from .catalog_service import CatalogService
from .permissions import require_hotel_access

PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")


def _json(data: dict[str, object]) -> str:
    """Serialize structured audit data as JSON text."""
    return json.dumps(data, ensure_ascii=False, default=str)


class BookingService:
    """Create, pay, cancel and modify orders.

    All inventory mutations happen inside ``Database.transaction()`` and are
    guarded by conditional SQL, so a stale quotation cannot oversell.
    """

    def __init__(
        self,
        db: Database,
        catalog: CatalogService,
        catalog_repo: CatalogRepository,
        inventory_repo: InventoryRepository,
        order_repo: OrderRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self.db = db
        self.catalog = catalog
        self.catalog_repo = catalog_repo
        self.inventory_repo = inventory_repo
        self.orders = order_repo
        self.audit = audit_repo

    # ------------------------------------------------------------------
    # Quotation and creation
    # ------------------------------------------------------------------
    def quote(
        self,
        hotel_id: str,
        room_type_id: str,
        check_in: date,
        check_out: date,
        qty: int = 1,
    ) -> Quote:
        """Public quotation used by the guest UI."""
        return self.catalog.quote(
            hotel_id, room_type_id, check_in, check_out, qty
        )

    def create_order(
        self,
        *,
        guest_name: str,
        phone: str,
        hotel_id: str,
        room_type_id: str,
        check_in: date,
        check_out: date,
        qty: int,
        pay_mode: PayMode,
        now: datetime | None = None,
    ) -> Order:
        """Create a pending order and lock every night atomically."""
        guest_name = guest_name.strip()
        phone = phone.strip()
        self._validate_guest(guest_name, phone)
        if not isinstance(pay_mode, PayMode):
            raise ValidationError("请选择支付方式")
        moment = now or datetime.now()
        with self.db.transaction() as connection:
            quote = self.catalog.quote(
                hotel_id, room_type_id, check_in, check_out, qty, connection
            )
            if not quote.is_available:
                raise ConflictError(quote.reason or "所选房型不可预订")
            guest = self._find_or_create_guest(
                connection, guest_name, phone, moment
            )
            order_no = self._new_order_no(connection, moment)
            item = OrderItem(
                item_id=0,
                order_no=order_no,
                qty=qty,
                cancelled_qty=0,
                unit_price=quote.nightly_total,
                breakfast=quote.room_type.breakfast,
                first_night_price=quote.first_night_price,
            )
            order = Order(
                order_no=order_no,
                guest_id=guest.guest_id,
                hotel_id=hotel_id,
                room_type_id=room_type_id,
                room_type_name=quote.room_type.name,
                check_in=check_in,
                check_out=check_out,
                status=OrderStatus.PENDING_PAYMENT,
                pay_mode=pay_mode,
                total_amount=quote.total,
                contact_name=guest_name,
                contact_phone=phone,
                expire_at=make_expiry(pay_mode, moment),
                version=0,
                created_at=moment,
                updated_at=moment,
                hotel_name=quote.hotel.name,
                item=item,
            )
            for biz_date in date_range(check_in, check_out):
                self.inventory_repo.lock_rooms(
                    connection,
                    hotel_id,
                    room_type_id,
                    biz_date,
                    qty,
                )
            self.orders.insert_order(connection, order, item)
            self.audit.write(
                connection,
                None,
                "CREATE_ORDER",
                hotel_id=hotel_id,
                terminal=Terminal.GUEST,
                after_data=_json(
                    {
                        "order_no": order_no,
                        "amount": str(quote.total),
                        "pay_mode": pay_mode.label,
                        "nights": quote.night_count,
                        "qty": qty,
                    }
                ),
                order_no=order_no,
                guest_id=guest.guest_id,
            )
        return self.orders.require(order_no)

    # ------------------------------------------------------------------
    # Payment
    # ------------------------------------------------------------------
    def pay_order(
        self,
        order_no: str,
        method: str = "WECHAT",
        now: datetime | None = None,
    ) -> Order:
        """Pay an online order and turn the stock lock into sold stock."""
        moment = now or datetime.now()
        expired = False
        with self.db.transaction() as connection:
            order = self.orders.require(order_no, connection)
            if order.status is not OrderStatus.PENDING_PAYMENT:
                raise ConflictError(
                    f"订单当前为「{order.status.label}」，无法支付"
                )
            if order.pay_mode is not PayMode.ONLINE:
                raise ConflictError("到店现付订单请由前台确认，不支持线上支付")
            if order.is_expired_at(moment):
                self._expire_pending(connection, order, moment)
                expired = True
            else:
                payment = Payment(
                    payment_no=f"PAY{new_token()}",
                    order_no=order_no,
                    amount=order.total_amount,
                    method=method,
                    status=PaymentStatus.SUCCESS,
                    paid_at=moment,
                )
                self.orders.add_payment(connection, payment)
                self._confirm_stock(connection, order)
                order.confirm()
                self.orders.update_order(connection, order)
                self.audit.write(
                    connection,
                    None,
                    "PAY_ORDER",
                    hotel_id=order.hotel_id,
                    terminal=Terminal.GUEST,
                    before_data=_json(
                        {"status": OrderStatus.PENDING_PAYMENT.label}
                    ),
                    after_data=_json(
                        {
                            "status": order.status.label,
                            "payment_no": payment.payment_no,
                            "amount": str(payment.amount),
                        }
                    ),
                    order_no=order_no,
                    guest_id=order.guest_id,
                )
        if expired:
            raise ConflictError("订单已超过 15 分钟支付时限并自动取消")
        return self.orders.require(order_no)

    def confirm_at_hotel(
        self,
        order_no: str,
        staff: Staff,
        now: datetime | None = None,
    ) -> Order:
        """Front desk accepts a pay-at-hotel order within 30 minutes."""
        moment = now or datetime.now()
        expired = False
        with self.db.transaction() as connection:
            order = self.orders.require(order_no, connection)
            require_hotel_access(staff, order.hotel_id)
            if order.pay_mode is not PayMode.AT_HOTEL:
                raise ConflictError("该订单不是到店现付订单")
            if order.status is not OrderStatus.PENDING_PAYMENT:
                raise ConflictError("订单已确认或已取消，不能重复接单")
            if order.is_expired_at(moment):
                self._expire_pending(connection, order, moment)
                expired = True
            else:
                self.orders.add_payment(
                    connection,
                    Payment(
                        payment_no=f"PAY{new_token()}",
                        order_no=order_no,
                        amount=order.total_amount,
                        method="AT_HOTEL",
                        status=PaymentStatus.PENDING,
                        paid_at=None,
                    ),
                )
                self._confirm_stock(connection, order)
                order.confirm()
                self.orders.update_order(connection, order)
                self.audit.write(
                    connection,
                    staff,
                    "CONFIRM_AT_HOTEL",
                    hotel_id=order.hotel_id,
                    before_data=_json(
                        {"status": OrderStatus.PENDING_PAYMENT.label}
                    ),
                    after_data=_json({"status": order.status.label}),
                    order_no=order_no,
                    guest_id=order.guest_id,
                )
        if expired:
            raise ConflictError("订单已超过 30 分钟确认时限并自动取消")
        return self.orders.require(order_no)

    def cancel_expired(self, now: datetime | None = None) -> int:
        """Auto-cancel every pending order whose lock has expired."""
        moment = now or datetime.now()
        expired = self.orders.list_pending_expired(moment)
        count = 0
        for order in expired:
            try:
                self.cancel_order(
                    order.order_no,
                    reason="超时未支付，系统自动取消",
                    staff=None,
                    terminal=Terminal.SYSTEM,
                    now=moment,
                    system=True,
                )
                count += 1
            except (ConflictError, NotFoundError):
                continue
        return count

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------
    def cancel_order(
        self,
        order_no: str,
        *,
        reason: str,
        staff: Staff | None = None,
        terminal: Terminal = Terminal.GUEST,
        now: datetime | None = None,
        qty: int = 0,
        guest_phone: str = "",
        system: bool = False,
    ) -> dict[str, object]:
        """Cancel all or part of an order, releasing stock and creating refunds."""
        reason = reason.strip()
        if len(reason) < 2:
            raise ValidationError("请填写取消原因")
        moment = now or datetime.now()
        refund: Refund | None = None
        penalty = as_money(0)
        refund_amount = as_money(0)
        with self.db.transaction() as connection:
            order = self.orders.require(order_no, connection)
            if staff:
                require_hotel_access(staff, order.hotel_id)
            elif not system and order.contact_phone != guest_phone:
                raise PermissionDenied("手机号与订单不一致，无法取消订单")
            if not order.can_cancel:
                raise ConflictError(
                    f"订单当前为「{order.status.label}」，不可取消"
                )
            if not order.item:
                raise NotFoundError("订单房明细缺失")
            active_qty = order.item.active_qty
            cancel_qty = qty or active_qty
            if cancel_qty <= 0 or cancel_qty > active_qty:
                raise ValidationError("取消间数不合法")
            if order.status is OrderStatus.PENDING_PAYMENT:
                for biz_date in date_range(order.check_in, order.check_out):
                    self.inventory_repo.release_locked(
                        connection,
                        order.hotel_id,
                        order.room_type_id,
                        biz_date,
                        cancel_qty,
                    )
                self._finish_cancellation(
                    connection,
                    order,
                    cancel_qty,
                    reason,
                    staff,
                    terminal,
                    penalty,
                    refund_amount,
                    refund,
                    moment,
                )
                return {
                    "order": order,
                    "refund": None,
                    "penalty": penalty,
                    "refund_amount": refund_amount,
                }
            self._release_sold_nights(connection, order, cancel_qty, moment.date())
            full_cancel = cancel_qty == active_qty
            paid_total = sum(
                (
                    payment.amount
                    for payment in self.orders.successful_payments(
                        connection, order_no
                    )
                ),
                as_money(0),
            )
            paid_share = (
                paid_total
                if full_cancel
                else as_money(paid_total * cancel_qty / order.qty)
            )
            if self._has_special_night(order):
                penalty = as_money(order.item.first_night_price * cancel_qty)
            elif datetime.combine(order.check_in, time.min) - moment < timedelta(
                hours=24
            ):
                penalty = as_money(order.item.first_night_price * cancel_qty)
            already_refunded = self.orders.refunded_total(order_no)
            refundable = max(paid_share - already_refunded, Decimal("0"))
            refund_amount = as_money(max(refundable - penalty, Decimal("0")))
            if refund_amount > 0:
                refund = self._create_refund(
                    connection,
                    order,
                    refund_amount,
                    first_night_amount=as_money(
                        order.item.first_night_price * cancel_qty
                    ),
                    reason=f"订单取消：{reason}",
                    requested_by=staff.name if staff else "客人自助",
                )
            self._finish_cancellation(
                connection,
                order,
                cancel_qty,
                reason,
                staff,
                terminal,
                penalty,
                refund_amount,
                refund,
                moment,
            )
            updated = order
        return {
            "order": updated,
            "refund": refund,
            "penalty": penalty,
            "refund_amount": refund_amount,
        }

    def _finish_cancellation(
        self,
        connection: sqlite3.Connection,
        order: Order,
        cancel_qty: int,
        reason: str,
        staff: Staff | None,
        terminal: Terminal,
        penalty: Decimal,
        refund_amount: Decimal,
        refund: Refund | None,
        moment: datetime,
    ) -> None:
        if not order.item:
            return
        before_status = order.status
        order.item.cancelled_qty += cancel_qty
        order.item.qty = max(order.item.qty, order.item.cancelled_qty)
        order.total_amount = as_money(
            order.item.unit_price * order.item.active_qty
        )
        if order.item.active_qty == 0:
            order.cancel()
        order.updated_at = moment
        self.orders.update_item(connection, order.item)
        self.orders.update_order(connection, order)
        self.orders.add_cancellation(
            connection,
            Cancellation(
                cancellation_id=0,
                order_no=order.order_no,
                cancelled_qty=cancel_qty,
                penalty=penalty,
                refund_amount=refund_amount,
                reason=reason,
                operator_id=staff.staff_id if staff else "GUEST",
                created_at=moment,
            ),
        )
        self.audit.write(
            connection,
            staff,
            "CANCEL_ORDER",
            hotel_id=order.hotel_id,
            terminal=terminal,
            before_data=_json({"status": before_status.label}),
            after_data=_json(
                {
                    "status": order.status.label,
                    "cancelled_qty": cancel_qty,
                    "penalty": str(penalty),
                    "refund": str(refund_amount),
                    "refund_status": refund.status.label if refund else "无需退款",
                }
            ),
            order_no=order.order_no,
            guest_id=order.guest_id,
        )

    # ------------------------------------------------------------------
    # Modification
    # ------------------------------------------------------------------
    def modify_order(
        self,
        order_no: str,
        *,
        hotel_id: str,
        room_type_id: str,
        check_in: date,
        check_out: date,
        staff: Staff | None = None,
        guest_phone: str = "",
        now: datetime | None = None,
    ) -> dict[str, object]:
        """Move an order to new dates / room type / same-city hotel."""
        moment = now or datetime.now()
        with self.db.transaction() as connection:
            order = self.orders.require(order_no, connection)
            if staff:
                require_hotel_access(staff, order.hotel_id)
            elif order.contact_phone != guest_phone:
                raise PermissionDenied("手机号与订单不一致，无法改单")
            if not order.can_modify:
                raise ConflictError(
                    f"订单当前为「{order.status.label}」，不可修改"
                )
            target_hotel = self.catalog_repo.get_hotel(hotel_id)
            old_hotel = self.catalog_repo.get_hotel(order.hotel_id)
            target_room = self.catalog_repo.get_room_type(room_type_id)
            if not target_hotel or not target_room:
                raise NotFoundError("目标门店或房型不存在")
            if target_room.hotel_id != hotel_id:
                raise ValidationError("房型不属于目标门店")
            if (
                old_hotel
                and target_hotel.city != old_hotel.city
                and hotel_id != order.hotel_id
            ):
                raise ValidationError("改门店仅限同城，跨城修改被拒绝")
            quote = self.catalog.quote(
                hotel_id, room_type_id, check_in, check_out, order.qty, connection
            )
            if not quote.is_available:
                raise ConflictError(quote.reason or "目标日期/房型不可预订")
            if order.status is OrderStatus.CONFIRMED and order.item:
                self._release_sold_nights(
                    connection, order, order.qty, moment.date()
                )
                self._sell_nights(
                    connection,
                    hotel_id,
                    room_type_id,
                    date_range(max(check_in, moment.date()), check_out),
                    order.qty,
                    confirmed=True,
                )
            before = {
                "hotel": order.hotel_name,
                "room_type": order.room_type_name,
                "dates": f"{order.check_in}~{order.check_out}",
                "amount": str(order.total_amount),
            }
            delta = as_money(quote.total - order.total_amount)
            order.hotel_id = hotel_id
            order.hotel_name = target_hotel.name
            order.room_type_id = room_type_id
            order.room_type_name = target_room.name
            order.check_in = check_in
            order.check_out = check_out
            order.total_amount = quote.total
            if order.item:
                order.item.unit_price = quote.nightly_total
                order.item.first_night_price = quote.first_night_price
                order.item.breakfast = target_room.breakfast
                self.orders.update_item(connection, order.item)
            self.orders.update_order(connection, order)
            refund: Refund | None = None
            if delta > 0:
                self.orders.add_payment(
                    connection,
                    Payment(
                        payment_no=f"PAY{new_token()}",
                        order_no=order.order_no,
                        amount=delta,
                        method="ADJUSTMENT",
                        status=PaymentStatus.SUCCESS,
                        paid_at=moment,
                    ),
                )
            elif delta < 0:
                refund = self._create_refund(
                    connection,
                    order,
                    as_money(-delta),
                    first_night_amount=order.first_night_amount,
                    reason="改单降价差额退款",
                    requested_by=staff.name if staff else "客人自助",
                )
            self.orders.add_change(
                connection,
                OrderChange(
                    change_id=0,
                    order_no=order.order_no,
                    change_type="MODIFY_STAY",
                    before_data=_json(before),
                    after_data=_json(
                        {
                            "hotel": target_hotel.name,
                            "room_type": target_room.name,
                            "dates": f"{check_in}~{check_out}",
                            "amount": str(quote.total),
                        }
                    ),
                    amount_delta=delta,
                    operator_id=staff.staff_id if staff else "GUEST",
                    created_at=moment,
                ),
            )
            self.audit.write(
                connection,
                staff,
                "MODIFY_ORDER",
                hotel_id=hotel_id,
                terminal=Terminal.DESKTOP if staff else Terminal.GUEST,
                before_data=_json(before),
                after_data=_json(
                    {
                        "hotel": target_hotel.name,
                        "room_type": target_room.name,
                        "dates": f"{check_in}~{check_out}",
                        "amount": str(quote.total),
                        "delta": str(delta),
                    }
                ),
                order_no=order.order_no,
                guest_id=order.guest_id,
            )
        return {
            "order": self.orders.require(order_no),
            "delta": delta,
            "refund": refund,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_guest(name: str, phone: str) -> None:
        if not 2 <= len(name) <= 20:
            raise ValidationError("入住人姓名须为 2 至 20 个字符")
        if not PHONE_PATTERN.match(phone):
            raise ValidationError("请输入有效的 11 位手机号")

    def _find_or_create_guest(
        self,
        connection: sqlite3.Connection,
        name: str,
        phone: str,
        moment: datetime,
    ) -> Guest:
        guest = self.orders.find_guest_by_phone(connection, phone)
        if guest:
            if guest.name != name:
                self.orders.update_guest_name(
                    connection, guest.guest_id, name
                )
                guest.name = name
            return guest
        guest = Guest(
            guest_id=f"G{new_token()}",
            name=name,
            phone=phone,
            created_at=moment,
        )
        self.orders.insert_guest(connection, guest)
        return guest

    def _new_order_no(
        self, connection: sqlite3.Connection, moment: datetime
    ) -> str:
        for _ in range(5):
            candidate = f"HB{moment:%Y%m%d}{new_token()[:5]}"
            row = connection.execute(
                "SELECT 1 FROM orders WHERE order_no = ?", (candidate,)
            ).fetchone()
            if not row:
                return candidate
        raise ConflictError("订单号生成冲突，请重试")

    def _confirm_stock(
        self, connection: sqlite3.Connection, order: Order
    ) -> None:
        for biz_date in date_range(order.check_in, order.check_out):
            self.inventory_repo.confirm_locked(
                connection,
                order.hotel_id,
                order.room_type_id,
                biz_date,
                order.qty,
            )

    def _release_sold_nights(
        self,
        connection: sqlite3.Connection,
        order: Order,
        qty: int,
        today: date,
    ) -> None:
        for biz_date in date_range(order.check_in, order.check_out):
            if biz_date < today:
                continue
            self.inventory_repo.release_sold(
                connection,
                order.hotel_id,
                order.room_type_id,
                biz_date,
                qty,
            )

    def _sell_nights(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        nights: list[date],
        qty: int,
        confirmed: bool,
    ) -> None:
        for biz_date in nights:
            if confirmed:
                self.inventory_repo.sell_confirmed(
                    connection, hotel_id, room_type_id, biz_date, qty
                )
            else:
                self.inventory_repo.lock_rooms(
                    connection, hotel_id, room_type_id, biz_date, qty
                )

    def _has_special_night(self, order: Order) -> bool:
        specials = self.catalog_repo.special_date_set()
        return any(
            biz_date in specials
            for biz_date in date_range(order.check_in, order.check_out)
        )

    def _expire_pending(
        self,
        connection: sqlite3.Connection,
        order: Order,
        moment: datetime,
    ) -> None:
        for biz_date in date_range(order.check_in, order.check_out):
            self.inventory_repo.release_locked(
                connection,
                order.hotel_id,
                order.room_type_id,
                biz_date,
                order.qty,
            )
        order.cancel()
        order.updated_at = moment
        self.orders.update_order(connection, order)
        self.audit.write(
            connection,
            None,
            "AUTO_CANCEL_EXPIRED",
            hotel_id=order.hotel_id,
            terminal=Terminal.SYSTEM,
            before_data=_json({"status": OrderStatus.PENDING_PAYMENT.label}),
            after_data=_json({"status": OrderStatus.CANCELLED.label}),
            order_no=order.order_no,
            guest_id=order.guest_id,
        )

    def _create_refund(
        self,
        connection: sqlite3.Connection,
        order: Order,
        amount: Decimal,
        first_night_amount: Decimal,
        reason: str,
        requested_by: str,
    ) -> Refund:
        """Create an auto-approved or manager-approval refund."""
        payments = self.orders.successful_payments(connection, order.order_no)
        payment_no = payments[-1].payment_no if payments else ""
        needs_approval = first_night_amount > Decimal("500.00")
        now = datetime.now()
        refund = Refund(
            refund_no=f"RF{new_token()}",
            order_no=order.order_no,
            payment_no=payment_no,
            amount=as_money(amount),
            status=(
                RefundStatus.PENDING_APPROVAL
                if needs_approval
                else RefundStatus.AUTO_APPROVED
            ),
            reason=reason,
            requested_by=requested_by,
            first_night_amount=as_money(first_night_amount),
            created_at=now,
            approved_at=None if needs_approval else now,
            submitted_at=None if needs_approval else now,
        )
        self.orders.add_refund(connection, refund)
        return refund
