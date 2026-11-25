"""Check-in, check-out, no-show and exception handling."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json

from ..domain.enums import (
    ExceptionStatus,
    ExceptionType,
    OrderStatus,
    PaymentStatus,
    RefundStatus,
    RoomStatus,
    Terminal,
)
from ..domain.errors import ConflictError, NotFoundError, ValidationError
from ..domain.models import (
    ExceptionRecord,
    Order,
    Refund,
    Staff,
)
from ..domain.money import as_money, date_range
from ..infrastructure.database import Database
from ..infrastructure.security import new_token
from ..repositories.audit_repository import AuditRepository
from ..repositories.catalog_repository import CatalogRepository
from ..repositories.inventory_repository import InventoryRepository
from ..repositories.order_repository import OrderRepository
from .booking_service import BookingService
from .permissions import require_hotel_access, require_staff


def _json(data: dict[str, object]) -> str:
    """Serialize an audit payload for the operation log."""
    return json.dumps(data, ensure_ascii=False, default=str)


class FulfillmentService:
    """The front-desk fulfilment use cases from M3."""

    def __init__(
        self,
        db: Database,
        booking: BookingService,
        catalog_repo: CatalogRepository,
        inventory_repo: InventoryRepository,
        order_repo: OrderRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self.db = db
        self.booking = booking
        self.catalog_repo = catalog_repo
        self.inventory_repo = inventory_repo
        self.orders = order_repo
        self.audit = audit_repo

    def check_in(
        self,
        order_no: str,
        room_numbers: list[str],
        staff: Staff,
        now: datetime | None = None,
    ) -> Order:
        """Assign physical rooms and move the order to checked-in."""
        moment = now or datetime.now()
        rooms = [number.strip() for number in room_numbers if number.strip()]
        with self.db.transaction() as connection:
            order = self.orders.require(order_no, connection)
            require_hotel_access(staff, order.hotel_id)
            if not order.can_check_in:
                raise ConflictError(
                    f"订单当前为「{order.status.label}」，不可办理入住"
                )
            if order.check_in > moment.date():
                raise ConflictError("未到入住日期，不能提前办理入住")
            if len(rooms) != order.active_qty:
                raise ValidationError(
                    f"需为 {order.active_qty} 间房各分配一个房号"
                )
            if len(set(rooms)) != len(rooms):
                raise ValidationError("房号不能重复")
            for room_no in rooms:
                room = self.catalog_repo.get_room(
                    connection, order.hotel_id, room_no
                )
                if not room:
                    raise NotFoundError(f"房号 {room_no} 不存在")
                if room.room_type_id != order.room_type_id:
                    raise ValidationError(
                        f"房号 {room_no} 不属于订单房型"
                    )
                if room.status is not RoomStatus.AVAILABLE:
                    raise ConflictError(f"房号 {room_no} 当前不可用")
            self.catalog_repo.set_rooms_status(
                connection, order.hotel_id, rooms, RoomStatus.OCCUPIED
            )
            order.assigned_rooms = ",".join(rooms)
            order.transition_to(OrderStatus.CHECKED_IN)
            order.updated_at = moment
            self.orders.update_order(connection, order)
            self.audit.write(
                connection,
                staff,
                "CHECK_IN",
                hotel_id=order.hotel_id,
                before_data=_json({"status": OrderStatus.CONFIRMED.label}),
                after_data=_json(
                    {"status": order.status.label, "rooms": order.assigned_rooms}
                ),
                order_no=order.order_no,
                guest_id=order.guest_id,
            )
        return self.orders.require(order_no)

    def check_out(
        self,
        order_no: str,
        staff: Staff,
        *,
        inspected: bool = True,
        actual_check_out: date | None = None,
        now: datetime | None = None,
    ) -> dict[str, object]:
        """Check out, release future stock and refund unused early nights."""
        if not inspected:
            raise ValidationError("请先完成查房确认，再办理退房")
        moment = now or datetime.now()
        today = actual_check_out or moment.date()
        refund: Refund | None = None
        refund_amount = as_money(0)
        with self.db.transaction() as connection:
            order = self.orders.require(order_no, connection)
            require_hotel_access(staff, order.hotel_id)
            if not order.can_check_out:
                raise ConflictError(
                    f"订单当前为「{order.status.label}」，不可办理退房"
                )
            release_from = max(today, order.check_in)
            for biz_date in date_range(release_from, order.check_out):
                self.inventory_repo.release_sold(
                    connection,
                    order.hotel_id,
                    order.room_type_id,
                    biz_date,
                    order.active_qty,
                )
            # Pay-at-hotel orders settle at check-out.
            for payment in self.orders.list_payments(order.order_no):
                if payment.status is PaymentStatus.PENDING:
                    self.orders.update_payment_status(
                        connection,
                        payment.payment_no,
                        PaymentStatus.SUCCESS,
                        moment,
                    )
            unused_nights = max(
                (order.check_out - release_from).days,
                0,
            )
            if unused_nights > 0 and order.nights > 0 and order.item:
                per_night_total = (
                    order.total_amount / Decimal(order.nights)
                )
                candidate = as_money(per_night_total * unused_nights)
                paid = sum(
                    (
                        item.amount
                        for item in self.orders.successful_payments(
                            connection, order.order_no
                        )
                    ),
                    as_money(0),
                )
                refund_amount = min(candidate, paid)
                if refund_amount > 0:
                    refund = self._create_refund(
                        connection,
                        order,
                        refund_amount,
                        reason=f"提前退房，退还未住 {unused_nights} 晚房费",
                        requested_by=staff.name,
                    )
            if order.assigned_rooms:
                self.catalog_repo.set_rooms_status(
                    connection,
                    order.hotel_id,
                    order.assigned_room_list,
                    RoomStatus.AVAILABLE,
                )
            order.transition_to(OrderStatus.CHECKED_OUT)
            order.updated_at = moment
            self.orders.update_order(connection, order)
            self.audit.write(
                connection,
                staff,
                "CHECK_OUT",
                hotel_id=order.hotel_id,
                before_data=_json({"status": OrderStatus.CHECKED_IN.label}),
                after_data=_json(
                    {
                        "status": order.status.label,
                        "early_refund": str(refund_amount),
                    }
                ),
                order_no=order.order_no,
                guest_id=order.guest_id,
            )
        return {
            "order": self.orders.require(order_no),
            "refund": refund,
            "refund_amount": refund_amount,
        }

    def mark_no_show(
        self,
        order_no: str,
        staff: Staff | None,
        now: datetime | None = None,
        system: bool = False,
    ) -> Order:
        """Night-audit action: no-show, release sellable future stock."""
        moment = now or datetime.now()
        with self.db.transaction() as connection:
            order = self.orders.require(order_no, connection)
            if staff:
                require_hotel_access(staff, order.hotel_id)
            elif not system:
                require_staff(staff)
            if order.status is not OrderStatus.CONFIRMED:
                raise ConflictError("仅已确认待入住订单可标记 No-show")
            if order.check_in > moment.date():
                raise ConflictError("未到入住日，不能标记 No-show")
            for biz_date in date_range(
                max(moment.date(), order.check_in), order.check_out
            ):
                self.inventory_repo.release_sold(
                    connection,
                    order.hotel_id,
                    order.room_type_id,
                    biz_date,
                    order.active_qty,
                )
            for payment in self.orders.list_payments(order.order_no):
                if payment.status is PaymentStatus.PENDING:
                    self.orders.update_payment_status(
                        connection,
                        payment.payment_no,
                        PaymentStatus.FAILED,
                    )
            order.transition_to(OrderStatus.NO_SHOW)
            order.updated_at = moment
            self.orders.update_order(connection, order)
            self.audit.write(
                connection,
                staff,
                "MARK_NO_SHOW",
                hotel_id=order.hotel_id,
                terminal=Terminal.SYSTEM if system else Terminal.DESKTOP,
                before_data=_json({"status": OrderStatus.CONFIRMED.label}),
                after_data=_json({"status": order.status.label}),
                order_no=order.order_no,
                guest_id=order.guest_id,
            )
        return self.orders.require(order_no)

    def mark_exception(
        self,
        order_no: str,
        staff: Staff,
        *,
        exception_type: ExceptionType = ExceptionType.NO_ROOM,
        description: str,
        compensation: Decimal = Decimal("0.00"),
        now: datetime | None = None,
    ) -> ExceptionRecord:
        """Move a confirmed order into the exception ledger."""
        moment = now or datetime.now()
        if len(description.strip()) < 4:
            raise ValidationError("请填写至少 4 个字符的异常说明")
        with self.db.transaction() as connection:
            order = self.orders.require(order_no, connection)
            require_hotel_access(staff, order.hotel_id)
            if not order.can_transition(OrderStatus.EXCEPTION):
                raise ConflictError("当前订单状态不可标记为异常")
            order.transition_to(OrderStatus.EXCEPTION)
            order.updated_at = moment
            self.orders.update_order(connection, order)
            record = ExceptionRecord(
                exception_id=0,
                order_no=order.order_no,
                exception_type=exception_type,
                description=description.strip(),
                amount=as_money(compensation),
                status=ExceptionStatus.OPEN,
                created_by=staff.staff_id,
                created_at=moment,
            )
            self.orders.add_exception(connection, record)
            self.audit.write(
                connection,
                staff,
                "MARK_EXCEPTION",
                hotel_id=order.hotel_id,
                before_data=_json({"status": OrderStatus.CONFIRMED.label}),
                after_data=_json(
                    {
                        "status": order.status.label,
                        "type": exception_type.label,
                        "compensation": str(compensation),
                    }
                ),
                order_no=order.order_no,
                guest_id=order.guest_id,
            )
        return record

    def resolve_exception(
        self,
        exception_id: int,
        staff: Staff,
        *,
        cancel_order: bool,
        note: str,
        now: datetime | None = None,
    ) -> Order:
        """Group-level resolution: refund and cancel, or close as checked out."""
        moment = now or datetime.now()
        if not staff.role.can_resolve_exception:
            raise ValidationError("仅集团运营或财务可裁决异常订单")
        records = {
            record.exception_id: record
            for record in self.orders.list_exceptions()
        }
        record = records.get(exception_id)
        if not record:
            raise NotFoundError("异常记录不存在")
        if record.status is not ExceptionStatus.OPEN:
            raise ConflictError("该异常记录已经处理")
        with self.db.transaction() as connection:
            order = self.orders.require(record.order_no, connection)
            status = (
                OrderStatus.CANCELLED
                if cancel_order
                else OrderStatus.CHECKED_OUT
            )
            order.transition_to(status)
            for biz_date in date_range(
                max(moment.date(), order.check_in), order.check_out
            ):
                self.inventory_repo.release_sold(
                    connection,
                    order.hotel_id,
                    order.room_type_id,
                    biz_date,
                    order.active_qty,
                )
            if order.assigned_rooms:
                self.catalog_repo.set_rooms_status(
                    connection,
                    order.hotel_id,
                    order.assigned_room_list,
                    RoomStatus.AVAILABLE,
                )
            if cancel_order:
                paid = self.orders.paid_total(order.order_no)
                if paid > 0:
                    self._create_refund(
                        connection,
                        order,
                        paid,
                        reason=f"异常订单裁决退款：{note}",
                        requested_by=staff.name,
                        force_success=True,
                    )
            order.updated_at = moment
            self.orders.update_order(connection, order)
            self.orders.resolve_exception(
                connection, exception_id, ExceptionStatus.RESOLVED
            )
            self.audit.write(
                connection,
                staff,
                "RESOLVE_EXCEPTION",
                hotel_id=order.hotel_id,
                before_data=_json(
                    {"exception": record.exception_type.label, "status": "待处理"}
                ),
                after_data=_json(
                    {"order_status": order.status.label, "note": note}
                ),
                order_no=order.order_no,
                guest_id=order.guest_id,
            )
        return self.orders.require(record.order_no)

    def run_night_audit(
        self,
        staff: Staff | None = None,
        now: datetime | None = None,
        force: bool = False,
    ) -> dict[str, int]:
        """Run expiry, no-show and basic night-audit checks.

        The real system runs at 24:00. For a classroom demo the operator can
        use ``force=True`` after a confirmation dialog.
        """
        moment = now or datetime.now()
        if moment.hour < 23 and not force:
            raise ValidationError("夜审仅在 23:00 后执行，演示模式可强制运行")
        expired = self.booking.cancel_expired(moment)
        no_show = 0
        for order in self.orders.list_due_no_show(moment.date()):
            if order.check_in > moment.date():
                continue
            try:
                self.mark_no_show(
                    order.order_no, staff, moment, system=staff is None
                )
                no_show += 1
            except (ConflictError, ValidationError):
                continue
        if staff:
            with self.db.transaction() as connection:
                self.audit.write(
                    connection,
                    staff,
                    "NIGHT_AUDIT",
                    hotel_id=staff.hotel_ids[0] if staff.hotel_ids else "",
                    before_data="",
                    after_data=_json(
                        {"expired": expired, "no_show": no_show}
                    ),
                )
        return {"expired": expired, "no_show": no_show}

    def _create_refund(
        self,
        connection,
        order: Order,
        amount: Decimal,
        *,
        reason: str,
        requested_by: str,
        force_success: bool = False,
    ) -> Refund:
        payments = self.orders.successful_payments(connection, order.order_no)
        now = datetime.now()
        refund = Refund(
            refund_no=f"RF{new_token()}",
            order_no=order.order_no,
            payment_no=payments[-1].payment_no if payments else "",
            amount=as_money(amount),
            status=RefundStatus.SUCCESS,
            reason=reason,
            requested_by=requested_by,
            first_night_amount=order.first_night_amount,
            created_at=now,
            approved_at=now,
            submitted_at=now,
        )
        if not force_success and order.first_night_amount > Decimal("500.00"):
            refund.status = RefundStatus.PENDING_APPROVAL
            refund.approved_at = None
            refund.submitted_at = None
        self.orders.add_refund(connection, refund)
        return refund
