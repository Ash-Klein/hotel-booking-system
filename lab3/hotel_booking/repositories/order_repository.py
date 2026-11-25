"""Order, guest, payment, refund and exception persistence."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import sqlite3
from typing import Sequence
from ..domain.enums import (
    ExceptionStatus,
    OrderStatus,
    PaymentStatus,
    RefundStatus,
)
from ..domain.errors import ConflictError, NotFoundError
from ..domain.models import (
    Cancellation,
    ExceptionRecord,
    Guest,
    Order,
    OrderChange,
    OrderItem,
    Payment,
    Refund,
)
from ..domain.money import as_money, datetime_text, money_text
from ..infrastructure.database import Database
from .mappers import (
    cancellation_from_row,
    change_from_row,
    exception_from_row,
    guest_from_row,
    order_from_row,
    order_item_from_row,
    payment_from_row,
    refund_from_row,
)

ORDER_SELECT = """
SELECT o.*, h.name AS hotel_name, h.city AS hotel_city
  FROM orders o
  JOIN hotels h ON h.hotel_id = o.hotel_id
"""


class OrderRepository:
    """Persistence for the order aggregate and its child records."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Guests
    # ------------------------------------------------------------------
    def find_guest_by_phone(
        self, connection: sqlite3.Connection | None, phone: str
    ) -> Guest | None:
        sql = "SELECT * FROM guests WHERE phone = ?"
        row = (
            connection.execute(sql, (phone,)).fetchone()
            if connection
            else self.db.query_one(sql, (phone,))
        )
        return guest_from_row(row) if row else None

    def insert_guest(
        self, connection: sqlite3.Connection, guest: Guest
    ) -> None:
        connection.execute(
            """
            INSERT INTO guests (guest_id, name, phone, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                guest.guest_id,
                guest.name,
                guest.phone,
                datetime_text(guest.created_at),
            ),
        )

    def update_guest_name(
        self, connection: sqlite3.Connection, guest_id: str, name: str
    ) -> None:
        connection.execute(
            "UPDATE guests SET name = ? WHERE guest_id = ?", (name, guest_id)
        )

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def get(
        self, order_no: str, connection: sqlite3.Connection | None = None
    ) -> Order | None:
        sql = f"{ORDER_SELECT} WHERE o.order_no = ?"
        row = (
            connection.execute(sql, (order_no,)).fetchone()
            if connection
            else self.db.query_one(sql, (order_no,))
        )
        if not row:
            return None
        item_row = (
            connection.execute(
                "SELECT * FROM order_items WHERE order_no = ? LIMIT 1",
                (order_no,),
            ).fetchone()
            if connection
            else self.db.query_one(
                "SELECT * FROM order_items WHERE order_no = ? LIMIT 1",
                (order_no,),
            )
        )
        item = order_item_from_row(item_row) if item_row else None
        return order_from_row(row, item)

    def require(
        self, order_no: str, connection: sqlite3.Connection | None = None
    ) -> Order:
        order = self.get(order_no, connection)
        if not order:
            raise NotFoundError(f"订单 {order_no} 不存在")
        return order

    def insert_order(
        self,
        connection: sqlite3.Connection,
        order: Order,
        item: OrderItem,
    ) -> None:
        connection.execute(
            """
            INSERT INTO orders
                (order_no, guest_id, hotel_id, room_type_id, room_type_name,
                 check_in, check_out, status, pay_mode, total_amount,
                 contact_name, contact_phone, expire_at, assigned_rooms,
                 version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order.order_no,
                order.guest_id,
                order.hotel_id,
                order.room_type_id,
                order.room_type_name,
                order.check_in.isoformat(),
                order.check_out.isoformat(),
                order.status.value,
                order.pay_mode.value,
                money_text(order.total_amount),
                order.contact_name,
                order.contact_phone,
                datetime_text(order.expire_at),
                order.assigned_rooms,
                order.version,
                datetime_text(order.created_at),
                datetime_text(order.updated_at),
            ),
        )
        connection.execute(
            """
            INSERT INTO order_items
                (order_no, qty, cancelled_qty, unit_price, breakfast,
                 first_night_price)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                order.order_no,
                item.qty,
                item.cancelled_qty,
                money_text(item.unit_price),
                int(item.breakfast),
                money_text(item.first_night_price),
            ),
        )

    def update_order(
        self, connection: sqlite3.Connection, order: Order
    ) -> None:
        """Update an order with an optimistic version check."""
        cursor = connection.execute(
            """
            UPDATE orders
               SET hotel_id = ?, room_type_id = ?, room_type_name = ?,
                   check_in = ?, check_out = ?, status = ?, pay_mode = ?,
                   total_amount = ?, contact_name = ?, contact_phone = ?,
                   expire_at = ?, assigned_rooms = ?,
                   version = version + 1, updated_at = ?
             WHERE order_no = ? AND version = ?
            """,
            (
                order.hotel_id,
                order.room_type_id,
                order.room_type_name,
                order.check_in.isoformat(),
                order.check_out.isoformat(),
                order.status.value,
                order.pay_mode.value,
                money_text(order.total_amount),
                order.contact_name,
                order.contact_phone,
                datetime_text(order.expire_at),
                order.assigned_rooms,
                datetime_text(datetime.now()),
                order.order_no,
                order.version,
            ),
        )
        if cursor.rowcount != 1:
            raise ConflictError("订单已被其他操作修改，请刷新后重试")
        order.version += 1
        order.updated_at = datetime.now()

    def update_item(
        self, connection: sqlite3.Connection, item: OrderItem
    ) -> None:
        connection.execute(
            """
            UPDATE order_items
               SET qty = ?, cancelled_qty = ?, unit_price = ?, breakfast = ?,
                   first_night_price = ?
             WHERE item_id = ?
            """,
            (
                item.qty,
                item.cancelled_qty,
                money_text(item.unit_price),
                int(item.breakfast),
                money_text(item.first_night_price),
                item.item_id,
            ),
        )

    def search(
        self,
        hotel_id: str | None = None,
        status: OrderStatus | None = None,
        phone: str = "",
        name: str = "",
        order_no: str = "",
        keyword: str = "",
        check_in: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 200,
    ) -> list[Order]:
        clauses: list[str] = []
        params: list[object] = []
        if hotel_id:
            clauses.append("o.hotel_id = ?")
            params.append(hotel_id)
        if status:
            clauses.append("o.status = ?")
            params.append(status.value)
        if phone:
            clauses.append("(o.contact_phone LIKE ? OR g.phone LIKE ?)")
            params.extend([f"%{phone}%", f"%{phone}%"])
        if name:
            clauses.append("(o.contact_name LIKE ? OR g.name LIKE ?)")
            params.extend([f"%{name}%", f"%{name}%"])
        if order_no:
            clauses.append("o.order_no LIKE ?")
            params.append(f"%{order_no}%")
        if keyword:
            clauses.append(
                "(o.order_no LIKE ? OR o.contact_phone LIKE ? "
                "OR o.contact_name LIKE ? OR g.phone LIKE ? OR g.name LIKE ?)"
            )
            params.extend([f"%{keyword}%"] * 5)
        if check_in:
            clauses.append("o.check_in = ?")
            params.append(check_in.isoformat())
        if date_from:
            clauses.append("o.check_in >= ?")
            params.append(date_from.isoformat())
        if date_to:
            clauses.append("o.check_in <= ?")
            params.append(date_to.isoformat())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            f"{ORDER_SELECT} JOIN guests g ON g.guest_id = o.guest_id "
            f"{where} ORDER BY o.created_at DESC LIMIT ?"
        )
        params.append(limit)
        rows = self.db.query(sql, params)
        return [self._hydrate(row) for row in rows]

    def list_for_guest(self, guest_id: str) -> list[Order]:
        rows = self.db.query(
            f"{ORDER_SELECT} WHERE o.guest_id = ? ORDER BY o.created_at DESC",
            (guest_id,),
        )
        return [self._hydrate(row) for row in rows]

    def list_arrivals(self, hotel_id: str, biz_date: date) -> list[Order]:
        rows = self.db.query(
            f"{ORDER_SELECT} WHERE o.hotel_id = ? AND o.check_in = ? "
            "AND o.status = ? ORDER BY o.created_at",
            (hotel_id, biz_date.isoformat(), OrderStatus.CONFIRMED.value),
        )
        return [self._hydrate(row) for row in rows]

    def list_departures(self, hotel_id: str, biz_date: date) -> list[Order]:
        rows = self.db.query(
            f"{ORDER_SELECT} WHERE o.hotel_id = ? AND o.check_out = ? "
            "AND o.status = ? ORDER BY o.created_at",
            (hotel_id, biz_date.isoformat(), OrderStatus.CHECKED_IN.value),
        )
        return [self._hydrate(row) for row in rows]

    def list_pending_expired(self, now: datetime) -> list[Order]:
        rows = self.db.query(
            f"{ORDER_SELECT} WHERE o.status = ? AND o.expire_at IS NOT NULL "
            "AND o.expire_at <= ?",
            (OrderStatus.PENDING_PAYMENT.value, datetime_text(now)),
        )
        return [self._hydrate(row) for row in rows]

    def list_due_no_show(self, biz_date: date) -> list[Order]:
        rows = self.db.query(
            f"{ORDER_SELECT} WHERE o.status = ? AND o.check_in <= ?",
            (OrderStatus.CONFIRMED.value, biz_date.isoformat()),
        )
        return [self._hydrate(row) for row in rows]

    def _hydrate(self, row: sqlite3.Row) -> Order:
        item_row = self.db.query_one(
            "SELECT * FROM order_items WHERE order_no = ? LIMIT 1",
            (row["order_no"],),
        )
        item = order_item_from_row(item_row) if item_row else None
        return order_from_row(row, item)

    def stats(self, hotel_id: str | None, biz_date: date) -> dict[str, int]:
        clauses = "WHERE 1 = 1"
        params: list[object] = []
        if hotel_id:
            clauses += " AND hotel_id = ?"
            params.append(hotel_id)
        row = self.db.query_one(
            f"""
            SELECT
              SUM(CASE WHEN check_in = ? AND status = 'CONFIRMED' THEN 1 ELSE 0 END)
                  AS arrivals,
              SUM(CASE WHEN check_out = ? AND status = 'CHECKED_IN' THEN 1 ELSE 0 END)
                  AS departures,
              SUM(CASE WHEN status = 'CHECKED_IN' THEN 1 ELSE 0 END) AS in_house,
              SUM(CASE WHEN status = 'PENDING_PAYMENT' THEN 1 ELSE 0 END) AS pending
            FROM orders {clauses}
            """,
            [biz_date.isoformat(), biz_date.isoformat(), *params],
        )
        if not row:
            return {"arrivals": 0, "departures": 0, "in_house": 0, "pending": 0}
        return {key: int(row[key] or 0) for key in row.keys()}

    # ------------------------------------------------------------------
    # Payments and refunds
    # ------------------------------------------------------------------
    def add_payment(
        self, connection: sqlite3.Connection, payment: Payment
    ) -> None:
        connection.execute(
            """
            INSERT INTO payments
                (payment_no, order_no, amount, method, status, paid_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payment.payment_no,
                payment.order_no,
                money_text(payment.amount),
                payment.method,
                payment.status.value,
                datetime_text(payment.paid_at),
                datetime_text(payment.created_at),
            ),
        )

    def list_payments(self, order_no: str) -> list[Payment]:
        rows = self.db.query(
            "SELECT * FROM payments WHERE order_no = ? ORDER BY created_at",
            (order_no,),
        )
        return [payment_from_row(row) for row in rows]

    def successful_payments(
        self, connection: sqlite3.Connection, order_no: str
    ) -> list[Payment]:
        rows = connection.execute(
            "SELECT * FROM payments WHERE order_no = ? AND status = ?",
            (order_no, PaymentStatus.SUCCESS.value),
        ).fetchall()
        return [payment_from_row(row) for row in rows]

    def paid_total(self, order_no: str) -> Decimal:
        rows = self.db.query(
            "SELECT amount FROM payments WHERE order_no = ? AND status = ?",
            (order_no, PaymentStatus.SUCCESS.value),
        )
        return as_money(sum((as_money(row["amount"]) for row in rows), Decimal("0")))

    def update_payment_status(
        self,
        connection: sqlite3.Connection,
        payment_no: str,
        status: PaymentStatus,
        paid_at: datetime | None = None,
    ) -> None:
        connection.execute(
            "UPDATE payments SET status = ?, paid_at = ? WHERE payment_no = ?",
            (status.value, datetime_text(paid_at), payment_no),
        )

    def add_refund(
        self, connection: sqlite3.Connection, refund: Refund
    ) -> None:
        connection.execute(
            """
            INSERT INTO refunds
                (refund_no, order_no, payment_no, amount, status, reason,
                 requested_by, first_night_amount, approver_id,
                 created_at, approved_at, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                refund.refund_no,
                refund.order_no,
                refund.payment_no,
                money_text(refund.amount),
                refund.status.value,
                refund.reason,
                refund.requested_by,
                money_text(refund.first_night_amount),
                refund.approver_id,
                datetime_text(refund.created_at),
                datetime_text(refund.approved_at),
                datetime_text(refund.submitted_at),
            ),
        )

    def get_refund(self, refund_no: str) -> Refund | None:
        row = self.db.query_one(
            "SELECT * FROM refunds WHERE refund_no = ?", (refund_no,)
        )
        return refund_from_row(row) if row else None

    def list_refunds(
        self, status: RefundStatus | None = None, order_no: str = ""
    ) -> list[Refund]:
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("r.status = ?")
            params.append(status.value)
        if order_no:
            clauses.append("r.order_no = ?")
            params.append(order_no)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.db.query(
            f"SELECT r.* FROM refunds r {where} ORDER BY r.created_at DESC",
            params,
        )
        return [refund_from_row(row) for row in rows]

    def update_refund(
        self, connection: sqlite3.Connection, refund: Refund
    ) -> None:
        connection.execute(
            """
            UPDATE refunds
               SET status = ?, approver_id = ?, approved_at = ?, submitted_at = ?
             WHERE refund_no = ?
            """,
            (
                refund.status.value,
                refund.approver_id,
                datetime_text(refund.approved_at),
                datetime_text(refund.submitted_at),
                refund.refund_no,
            ),
        )

    def refunded_total(self, order_no: str) -> Decimal:
        rows = self.db.query(
            """
            SELECT amount FROM refunds
             WHERE order_no = ? AND status IN (?, ?, ?)
            """,
            (
                order_no,
                RefundStatus.SUCCESS.value,
                RefundStatus.AUTO_APPROVED.value,
                RefundStatus.PENDING_APPROVAL.value,
            ),
        )
        return as_money(sum((as_money(row["amount"]) for row in rows), Decimal("0")))

    def pending_refund_count(self, hotel_id: str | None = None) -> int:
        sql = """
            SELECT COUNT(*) FROM refunds r
            JOIN orders o ON o.order_no = r.order_no
            WHERE r.status = ?
        """
        params: list[object] = [RefundStatus.PENDING_APPROVAL.value]
        if hotel_id:
            sql += " AND o.hotel_id = ?"
            params.append(hotel_id)
        return int(self.db.scalar(sql, params, default=0))

    # ------------------------------------------------------------------
    # Changes, cancellations and exception ledger
    # ------------------------------------------------------------------
    def add_change(
        self, connection: sqlite3.Connection, change: OrderChange
    ) -> None:
        connection.execute(
            """
            INSERT INTO order_changes
                (order_no, change_type, before_data, after_data,
                 amount_delta, operator_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                change.order_no,
                change.change_type,
                change.before_data,
                change.after_data,
                money_text(change.amount_delta),
                change.operator_id,
                datetime_text(change.created_at),
            ),
        )

    def list_changes(self, order_no: str) -> list[OrderChange]:
        rows = self.db.query(
            "SELECT * FROM order_changes WHERE order_no = ? "
            "ORDER BY created_at DESC",
            (order_no,),
        )
        return [change_from_row(row) for row in rows]

    def add_cancellation(
        self, connection: sqlite3.Connection, cancellation: Cancellation
    ) -> None:
        connection.execute(
            """
            INSERT INTO cancellations
                (order_no, cancelled_qty, penalty, refund_amount,
                 reason, operator_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cancellation.order_no,
                cancellation.cancelled_qty,
                money_text(cancellation.penalty),
                money_text(cancellation.refund_amount),
                cancellation.reason,
                cancellation.operator_id,
                datetime_text(cancellation.created_at),
            ),
        )

    def add_exception(
        self, connection: sqlite3.Connection, record: ExceptionRecord
    ) -> None:
        connection.execute(
            """
            INSERT INTO exception_records
                (order_no, exception_type, description, amount, status,
                 created_by, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.order_no,
                record.exception_type.value,
                record.description,
                money_text(record.amount),
                record.status.value,
                record.created_by,
                datetime_text(record.created_at),
                datetime_text(record.resolved_at),
            ),
        )

    def list_exceptions(
        self, status: ExceptionStatus | None = None
    ) -> list[ExceptionRecord]:
        sql = "SELECT * FROM exception_records"
        params: list[object] = []
        if status:
            sql += " WHERE status = ?"
            params.append(status.value)
        sql += " ORDER BY created_at DESC"
        return [exception_from_row(row) for row in self.db.query(sql, params)]

    def resolve_exception(
        self,
        connection: sqlite3.Connection,
        exception_id: int,
        status: ExceptionStatus,
    ) -> None:
        connection.execute(
            """
            UPDATE exception_records
               SET status = ?, resolved_at = datetime('now', 'localtime')
             WHERE exception_id = ?
            """,
            (status.value, exception_id),
        )

    def order_numbers_for_hotel(
        self, hotel_id: str, start: date, end: date
    ) -> Sequence[str]:
        rows = self.db.query(
            "SELECT order_no FROM orders WHERE hotel_id = ? "
            "AND check_in >= ? AND check_in <= ?",
            (hotel_id, start.isoformat(), end.isoformat()),
        )
        return [str(row["order_no"]) for row in rows]
