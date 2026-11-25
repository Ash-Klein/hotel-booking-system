"""Aggregated queries used by dashboards and the operation report."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from ..domain.enums import OrderStatus
from ..domain.models import ReportRow
from ..domain.money import ZERO, as_money, date_range
from ..infrastructure.database import Database

COUNTABLE_STATUSES = {
    OrderStatus.CONFIRMED.value,
    OrderStatus.CHECKED_IN.value,
    OrderStatus.CHECKED_OUT.value,
    OrderStatus.EXCEPTION.value,
    OrderStatus.NO_SHOW.value,
}


class ReportingRepository:
    """Read-only aggregation queries.

    The project deliberately aggregates money in Python instead of using
    SQLite ``SUM(CAST(... AS REAL))`` so that no binary floating-point error can
    leak into a financial report.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def hotel_summary(self, start: date, end: date) -> list[ReportRow]:
        hotels = self.db.query(
            "SELECT hotel_id, name, city, franchise_type FROM hotels "
            "ORDER BY city, hotel_id"
        )
        nights = max((end - start).days, 1)
        result: list[ReportRow] = []
        for hotel in hotels:
            hotel_id = str(hotel["hotel_id"])
            orders = self.db.query(
                """
                SELECT o.status, o.total_amount, o.check_in, o.check_out,
                       i.qty, i.cancelled_qty
                  FROM orders o
                  JOIN order_items i ON i.order_no = o.order_no
                 WHERE o.hotel_id = ? AND o.check_in >= ? AND o.check_in < ?
                """,
                (hotel_id, start.isoformat(), end.isoformat()),
            )
            order_count = len(orders)
            cancellations = 0
            room_nights = 0
            revenue = ZERO
            for order in orders:
                if order["status"] == OrderStatus.CANCELLED.value:
                    cancellations += 1
                if order["status"] not in COUNTABLE_STATUSES:
                    continue
                check_in = date.fromisoformat(order["check_in"])
                check_out = date.fromisoformat(order["check_out"])
                active_qty = int(order["qty"]) - int(order["cancelled_qty"])
                stay_nights = max((check_out - check_in).days, 0)
                room_nights += active_qty * stay_nights
                revenue += as_money(order["total_amount"])
            stock = self.db.query_one(
                """
                SELECT COALESCE(SUM(total), 0) AS total,
                       COALESCE(SUM(sold), 0) AS sold
                  FROM daily_inventory
                 WHERE hotel_id = ? AND biz_date >= ? AND biz_date < ?
                """,
                (hotel_id, start.isoformat(), end.isoformat()),
            )
            capacity = int(stock["total"] or 0) if stock else 0
            sold = int(stock["sold"] or 0) if stock else 0
            occupancy = (
                (Decimal(sold) * Decimal("100") / Decimal(capacity)).quantize(
                    Decimal("0.01")
                )
                if capacity
                else ZERO
            )
            adr = (
                (revenue / Decimal(room_nights)).quantize(Decimal("0.01"))
                if room_nights
                else ZERO
            )
            cancel_rate = (
                (
                    Decimal(cancellations)
                    * Decimal("100")
                    / Decimal(order_count)
                ).quantize(Decimal("0.01"))
                if order_count
                else ZERO
            )
            result.append(
                ReportRow(
                    hotel_id=hotel_id,
                    hotel_name=str(hotel["name"]),
                    city=str(hotel["city"]),
                    franchise_type=str(hotel["franchise_type"]),
                    order_count=order_count,
                    room_nights=room_nights,
                    revenue=as_money(revenue),
                    cancellations=cancellations,
                    occupancy=occupancy,
                    adr=adr,
                    cancel_rate=cancel_rate,
                )
            )
        return result

    def daily_series(
        self, start: date, end: date, hotel_id: str | None = None
    ) -> list[dict[str, Any]]:
        params: list[object] = [start.isoformat(), end.isoformat()]
        clause = ""
        if hotel_id:
            clause = " AND hotel_id = ?"
            params.append(hotel_id)
        rows = self.db.query(
            f"""
            SELECT check_in AS biz_date, status, total_amount
              FROM orders
             WHERE check_in >= ? AND check_in < ? {clause}
            """,
            params,
        )
        buckets: dict[str, dict[str, Any]] = {}
        for biz_date in date_range(start, end):
            buckets[biz_date.isoformat()] = {
                "date": biz_date.isoformat(),
                "orders": 0,
                "cancelled": 0,
                "revenue": ZERO,
            }
        for row in rows:
            bucket = buckets.get(str(row["biz_date"]))
            if bucket is None:
                continue
            bucket["orders"] += 1
            if row["status"] == OrderStatus.CANCELLED.value:
                bucket["cancelled"] += 1
            elif row["status"] in COUNTABLE_STATUSES:
                bucket["revenue"] += as_money(row["total_amount"])
        return list(buckets.values())

    def room_type_sales(
        self, start: date, end: date, hotel_id: str | None = None
    ) -> list[dict[str, Any]]:
        params: list[object] = [start.isoformat(), end.isoformat()]
        clause = ""
        if hotel_id:
            clause = " AND o.hotel_id = ?"
            params.append(hotel_id)
        rows = self.db.query(
            f"""
            SELECT o.room_type_name, o.status, o.total_amount,
                   i.qty, i.cancelled_qty
              FROM orders o
              JOIN order_items i ON i.order_no = o.order_no
             WHERE o.check_in >= ? AND o.check_in < ? {clause}
               AND o.status != 'CANCELLED'
            """,
            params,
        )
        buckets: dict[str, dict[str, Any]] = {}
        for row in rows:
            name = str(row["room_type_name"])
            bucket = buckets.setdefault(
                name,
                {"room_type": name, "orders": 0, "rooms": 0, "revenue": ZERO},
            )
            bucket["orders"] += 1
            bucket["rooms"] += int(row["qty"]) - int(row["cancelled_qty"])
            bucket["revenue"] += as_money(row["total_amount"])
        result = list(buckets.values())
        result.sort(key=lambda item: (-item["rooms"], item["room_type"]))
        return result

    def payment_total_between(
        self, start: date, end: date, hotel_id: str | None = None
    ) -> Decimal:
        params: list[object] = [
            start.isoformat(),
            (end + timedelta(days=1)).isoformat(),
        ]
        clause = ""
        if hotel_id:
            clause = " AND o.hotel_id = ?"
            params.append(hotel_id)
        rows = self.db.query(
            f"""
            SELECT p.amount FROM payments p
              JOIN orders o ON o.order_no = p.order_no
             WHERE p.status = 'SUCCESS'
               AND p.paid_at >= ? AND p.paid_at < ? {clause}
            """,
            params,
        )
        return as_money(sum((as_money(row["amount"]) for row in rows), ZERO))

    def exception_statistics(self) -> list[dict[str, Any]]:
        rows = self.db.query(
            """
            SELECT exception_type, status, amount
              FROM exception_records
             ORDER BY exception_type, status
            """
        )
        buckets: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            key = (str(row["exception_type"]), str(row["status"]))
            bucket = buckets.setdefault(
                key,
                {"type": key[0], "status": key[1], "count": 0, "total": ZERO},
            )
            bucket["count"] += 1
            bucket["total"] += as_money(row["amount"])
        return list(buckets.values())

    def last_days(self, days: int = 7) -> tuple[date, date]:
        end = date.today() + timedelta(days=1)
        start = end - timedelta(days=days)
        return start, end

    def count_new_orders(self, hotel_id: str | None = None) -> int:
        if hotel_id:
            value = self.db.scalar(
                "SELECT COUNT(*) FROM orders WHERE hotel_id = ?", (hotel_id,),
                default=0,
            )
        else:
            value = self.db.scalar("SELECT COUNT(*) FROM orders", default=0)
        return int(value)
