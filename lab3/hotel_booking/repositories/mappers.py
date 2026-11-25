"""Row-to-dataclass mappers.

Keeping SQL column knowledge in one place means a schema rename touches this
module instead of every repository and service.
"""

from __future__ import annotations

from datetime import date, datetime
import sqlite3
from typing import Any

from ..domain.enums import (
    ExceptionStatus,
    ExceptionType,
    GroupLockStatus,
    HotelStatus,
    OrderStatus,
    PayMode,
    PaymentStatus,
    RefundStatus,
    Role,
    RoomStatus,
    RoomTypeStatus,
)
from ..domain.models import (
    Cancellation,
    DailyInventory,
    DailyPrice,
    ExceptionRecord,
    GroupLock,
    Guest,
    Hotel,
    OperationLog,
    Order,
    OrderChange,
    OrderItem,
    Payment,
    Refund,
    ReportRow,
    Room,
    RoomClosure,
    RoomType,
    SpecialDate,
    Staff,
)
from ..domain.money import as_money, parse_date, parse_datetime


def _dt(value: str | None) -> datetime | None:
    """Map one SQLite row to the corresponding domain object."""
    return parse_datetime(value)


def hotel_from_row(row: sqlite3.Row) -> Hotel:
    """Map one SQLite row to the corresponding domain object."""
    return Hotel(
        hotel_id=row["hotel_id"],
        name=row["name"],
        city=row["city"],
        district=row["district"],
        address=row["address"],
        franchise_type=row["franchise_type"],
        phone=row["phone"],
        status=HotelStatus(row["status"]),
    )


def room_type_from_row(row: sqlite3.Row) -> RoomType:
    """Map one SQLite row to the corresponding domain object."""
    return RoomType(
        room_type_id=row["room_type_id"],
        hotel_id=row["hotel_id"],
        name=row["name"],
        bed_type=row["bed_type"],
        capacity=int(row["capacity"]),
        breakfast=bool(row["breakfast"]),
        base_price=as_money(row["base_price"]),
        status=RoomTypeStatus(row["status"]),
    )


def inventory_from_row(row: sqlite3.Row) -> DailyInventory:
    """Map one SQLite row to the corresponding domain object."""
    return DailyInventory(
        hotel_id=row["hotel_id"],
        room_type_id=row["room_type_id"],
        biz_date=parse_date(row["biz_date"]),
        total=int(row["total"]),
        sold=int(row["sold"]),
        locked=int(row["locked"]),
        group_locked=int(row["group_locked"]),
        version=int(row["version"]),
    )


def price_from_row(row: sqlite3.Row) -> DailyPrice:
    """Map one SQLite row to the corresponding domain object."""
    return DailyPrice(
        hotel_id=row["hotel_id"],
        room_type_id=row["room_type_id"],
        biz_date=parse_date(row["biz_date"]),
        base_price=as_money(row["base_price"]),
        final_price=as_money(row["final_price"]),
    )


def closure_from_row(row: sqlite3.Row) -> RoomClosure:
    """Map one SQLite row to the corresponding domain object."""
    return RoomClosure(
        closure_id=row["closure_id"],
        hotel_id=row["hotel_id"],
        room_type_id=row["room_type_id"],
        start_date=parse_date(row["start_date"]),
        end_date=parse_date(row["end_date"]),
        reason=row["reason"],
        created_by=row["created_by"],
        created_at=_dt(row["created_at"]) or datetime.now(),
    )


def group_lock_from_row(row: sqlite3.Row) -> GroupLock:
    """Map one SQLite row to the corresponding domain object."""
    return GroupLock(
        lock_id=row["lock_id"],
        hotel_id=row["hotel_id"],
        room_type_id=row["room_type_id"],
        start_date=parse_date(row["start_date"]),
        end_date=parse_date(row["end_date"]),
        qty=int(row["qty"]),
        release_at=_dt(row["release_at"]) or datetime.now(),
        status=GroupLockStatus(row["status"]),
        created_by=row["created_by"],
        note=row["note"],
        created_at=_dt(row["created_at"]) or datetime.now(),
    )


def guest_from_row(row: sqlite3.Row) -> Guest:
    """Map one SQLite row to the corresponding domain object."""
    return Guest(
        guest_id=row["guest_id"],
        name=row["name"],
        phone=row["phone"],
        created_at=_dt(row["created_at"]) or datetime.now(),
    )


def order_item_from_row(row: sqlite3.Row) -> OrderItem:
    """Map one SQLite row to the corresponding domain object."""
    return OrderItem(
        item_id=int(row["item_id"]),
        order_no=row["order_no"],
        qty=int(row["qty"]),
        cancelled_qty=int(row["cancelled_qty"]),
        unit_price=as_money(row["unit_price"]),
        breakfast=bool(row["breakfast"]),
        first_night_price=as_money(row["first_night_price"]),
    )


def order_from_row(
    row: sqlite3.Row, item: OrderItem | None = None, hotel_name: str = ""
) -> Order:
    """Map one order row and its item to the order aggregate."""
    keys = row.keys()
    return Order(
        order_no=row["order_no"],
        guest_id=row["guest_id"],
        hotel_id=row["hotel_id"],
        room_type_id=row["room_type_id"],
        room_type_name=row["room_type_name"],
        check_in=parse_date(row["check_in"]),
        check_out=parse_date(row["check_out"]),
        status=OrderStatus(row["status"]),
        pay_mode=PayMode(row["pay_mode"]),
        total_amount=as_money(row["total_amount"]),
        contact_name=row["contact_name"],
        contact_phone=row["contact_phone"],
        expire_at=_dt(row["expire_at"]),
        assigned_rooms=row["assigned_rooms"],
        version=int(row["version"]),
        created_at=_dt(row["created_at"]) or datetime.now(),
        updated_at=_dt(row["updated_at"]) or datetime.now(),
        hotel_name=hotel_name or (row["hotel_name"] if "hotel_name" in keys else ""),
        item=item,
    )


def payment_from_row(row: sqlite3.Row) -> Payment:
    """Map one SQLite row to the corresponding domain object."""
    return Payment(
        payment_no=row["payment_no"],
        order_no=row["order_no"],
        amount=as_money(row["amount"]),
        method=row["method"],
        status=PaymentStatus(row["status"]),
        paid_at=_dt(row["paid_at"]),
        created_at=_dt(row["created_at"]) or datetime.now(),
    )


def refund_from_row(row: sqlite3.Row) -> Refund:
    """Map one SQLite row to the corresponding domain object."""
    return Refund(
        refund_no=row["refund_no"],
        order_no=row["order_no"],
        payment_no=row["payment_no"],
        amount=as_money(row["amount"]),
        status=RefundStatus(row["status"]),
        reason=row["reason"],
        requested_by=row["requested_by"],
        first_night_amount=as_money(row["first_night_amount"]),
        approver_id=row["approver_id"],
        created_at=_dt(row["created_at"]) or datetime.now(),
        approved_at=_dt(row["approved_at"]),
        submitted_at=_dt(row["submitted_at"]),
    )


def staff_from_row(
    row: sqlite3.Row, hotel_ids: list[str] | None = None
) -> Staff:
    """Map a staff row plus its hotel scope to a staff member."""
    return Staff(
        staff_id=row["staff_id"],
        username=row["username"],
        password_hash=row["password_hash"],
        salt=row["salt"],
        name=row["name"],
        role=Role(row["role"]),
        active=bool(row["active"]),
        hotel_ids=hotel_ids or [],
    )


def log_from_row(row: sqlite3.Row) -> OperationLog:
    """Map one SQLite row to the corresponding domain object."""
    return OperationLog(
        log_id=int(row["log_id"]),
        staff_id=row["staff_id"],
        staff_name=row["staff_name"],
        hotel_id=row["hotel_id"],
        terminal=row["terminal"],
        action=row["action"],
        before_data=row["before_data"],
        after_data=row["after_data"],
        order_no=row["order_no"],
        guest_id=row["guest_id"],
        result=row["result"],
        created_at=_dt(row["created_at"]) or datetime.now(),
    )


def change_from_row(row: sqlite3.Row) -> OrderChange:
    """Map one SQLite row to the corresponding domain object."""
    return OrderChange(
        change_id=int(row["change_id"]),
        order_no=row["order_no"],
        change_type=row["change_type"],
        before_data=row["before_data"],
        after_data=row["after_data"],
        amount_delta=as_money(row["amount_delta"]),
        operator_id=row["operator_id"],
        created_at=_dt(row["created_at"]) or datetime.now(),
    )


def cancellation_from_row(row: sqlite3.Row) -> Cancellation:
    """Map one SQLite row to the corresponding domain object."""
    return Cancellation(
        cancellation_id=int(row["cancellation_id"]),
        order_no=row["order_no"],
        cancelled_qty=int(row["cancelled_qty"]),
        penalty=as_money(row["penalty"]),
        refund_amount=as_money(row["refund_amount"]),
        reason=row["reason"],
        operator_id=row["operator_id"],
        created_at=_dt(row["created_at"]) or datetime.now(),
    )


def exception_from_row(row: sqlite3.Row) -> ExceptionRecord:
    """Map one SQLite row to the corresponding domain object."""
    return ExceptionRecord(
        exception_id=int(row["exception_id"]),
        order_no=row["order_no"],
        exception_type=ExceptionType(row["exception_type"]),
        description=row["description"],
        amount=as_money(row["amount"]),
        status=ExceptionStatus(row["status"]),
        created_by=row["created_by"],
        created_at=_dt(row["created_at"]) or datetime.now(),
        resolved_at=_dt(row["resolved_at"]),
    )


def room_from_row(row: sqlite3.Row) -> Room:
    """Map one SQLite row to the corresponding domain object."""
    return Room(
        hotel_id=row["hotel_id"],
        room_no=row["room_no"],
        room_type_id=row["room_type_id"],
        status=RoomStatus(row["status"]),
        floor=int(row["floor"]),
    )


def special_date_from_row(row: sqlite3.Row) -> SpecialDate:
    """Map one SQLite row to the corresponding domain object."""
    return SpecialDate(
        biz_date=parse_date(row["biz_date"]),
        name=row["name"],
        note=row["note"],
    )


def report_row_from_row(row: sqlite3.Row) -> ReportRow:
    """Map one SQLite row to the corresponding domain object."""
    return ReportRow(
        hotel_id=row["hotel_id"],
        hotel_name=row["hotel_name"],
        city=row["city"],
        franchise_type=row["franchise_type"],
        order_count=int(row["order_count"] or 0),
        room_nights=int(row["room_nights"] or 0),
        revenue=as_money(row["revenue"] or "0"),
        cancellations=int(row["cancellations"] or 0),
        occupancy=as_money(row["occupancy"] or "0"),
        adr=as_money(row["adr"] or "0"),
        cancel_rate=as_money(row["cancel_rate"] or "0"),
    )


def row_value(row: sqlite3.Row, key: str, default: Any = None) -> Any:
    """Safe optional column access used by aggregate queries."""
    return row[key] if key in row.keys() else default
