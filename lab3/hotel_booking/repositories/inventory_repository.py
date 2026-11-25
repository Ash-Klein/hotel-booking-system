"""Inventory, price, closure and protocol-lock persistence.

Every stock mutation is a single conditional UPDATE. The database therefore
re-checks availability at the moment of writing, not merely when the page was
rendered. This is the mechanism that prevents two guests from buying the same
last room.
"""

from __future__ import annotations

from datetime import date, datetime
import sqlite3

from ..domain.enums import GroupLockStatus
from ..domain.errors import InventoryUnavailable, NotFoundError
from ..domain.models import DailyInventory, DailyPrice, GroupLock, RoomClosure
from ..domain.money import date_range, datetime_text, money_text
from ..infrastructure.database import Database
from .mappers import (
    closure_from_row,
    group_lock_from_row,
    inventory_from_row,
    price_from_row,
)


class InventoryRepository:
    """Persistence for the M2 inventory and price domain."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def get(
        self,
        connection: sqlite3.Connection | None,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
    ) -> DailyInventory | None:
        sql = (
            "SELECT * FROM daily_inventory "
            "WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?"
        )
        params = (hotel_id, room_type_id, biz_date.isoformat())
        row = (
            connection.execute(sql, params).fetchone()
            if connection
            else self.db.query_one(sql, params)
        )
        return inventory_from_row(row) if row else None

    def require(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
    ) -> DailyInventory:
        inventory = self.get(connection, hotel_id, room_type_id, biz_date)
        if not inventory:
            raise NotFoundError(f"{biz_date} 的库存记录不存在")
        return inventory

    def list_range(
        self, hotel_id: str, room_type_id: str, start: date, end: date
    ) -> list[DailyInventory]:
        rows = self.db.query(
            """
            SELECT * FROM daily_inventory
            WHERE hotel_id = ? AND room_type_id = ?
              AND biz_date >= ? AND biz_date < ?
            ORDER BY biz_date
            """,
            (hotel_id, room_type_id, start.isoformat(), end.isoformat()),
        )
        return [inventory_from_row(row) for row in rows]

    def list_for_hotel(
        self, hotel_id: str, start: date, end: date
    ) -> list[DailyInventory]:
        rows = self.db.query(
            """
            SELECT * FROM daily_inventory
            WHERE hotel_id = ? AND biz_date >= ? AND biz_date < ?
            ORDER BY biz_date, room_type_id
            """,
            (hotel_id, start.isoformat(), end.isoformat()),
        )
        return [inventory_from_row(row) for row in rows]

    def available_sum(self, hotel_id: str, biz_date: date) -> int:
        value = self.db.scalar(
            """
            SELECT COALESCE(SUM(total - sold - locked - group_locked), 0)
            FROM daily_inventory WHERE hotel_id = ? AND biz_date = ?
            """,
            (hotel_id, biz_date.isoformat()),
            default=0,
        )
        return int(value)

    # ------------------------------------------------------------------
    # Stock mutations
    # ------------------------------------------------------------------
    def lock_rooms(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
        qty: int,
    ) -> None:
        cursor = connection.execute(
            """
            UPDATE daily_inventory
               SET locked = locked + ?, version = version + 1
             WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?
               AND total - sold - locked - group_locked >= ?
            """,
            (
                qty,
                hotel_id,
                room_type_id,
                biz_date.isoformat(),
                qty,
            ),
        )
        if cursor.rowcount != 1:
            current = self.get(connection, hotel_id, room_type_id, biz_date)
            remaining = current.available if current else 0
            raise InventoryUnavailable(biz_date.isoformat(), remaining)

    def release_locked(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
        qty: int,
    ) -> None:
        cursor = connection.execute(
            """
            UPDATE daily_inventory
               SET locked = locked - ?, version = version + 1
             WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?
               AND locked >= ?
            """,
            (qty, hotel_id, room_type_id, biz_date.isoformat(), qty),
        )
        if cursor.rowcount != 1:
            raise NotFoundError(f"{biz_date} 待释放的锁房数量不足")

    def confirm_locked(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
        qty: int,
    ) -> None:
        cursor = connection.execute(
            """
            UPDATE daily_inventory
               SET locked = locked - ?, sold = sold + ?, version = version + 1
             WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?
               AND locked >= ?
            """,
            (qty, qty, hotel_id, room_type_id, biz_date.isoformat(), qty),
        )
        if cursor.rowcount != 1:
            raise NotFoundError(f"{biz_date} 待确认的锁房数量不足")

    def sell_confirmed(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
        qty: int,
    ) -> None:
        cursor = connection.execute(
            """
            UPDATE daily_inventory
               SET sold = sold + ?, version = version + 1
             WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?
               AND total - sold - locked - group_locked >= ?
            """,
            (qty, hotel_id, room_type_id, biz_date.isoformat(), qty),
        )
        if cursor.rowcount != 1:
            current = self.get(connection, hotel_id, room_type_id, biz_date)
            remaining = current.available if current else 0
            raise InventoryUnavailable(biz_date.isoformat(), remaining)

    def release_sold(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
        qty: int,
    ) -> None:
        """Return sold rooms, clamping at zero for defensive safety."""
        connection.execute(
            """
            UPDATE daily_inventory
               SET sold = CASE WHEN sold >= ? THEN sold - ? ELSE 0 END,
                   version = version + 1
             WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?
            """,
            (qty, qty, hotel_id, room_type_id, biz_date.isoformat()),
        )

    def set_total(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
        new_total: int,
    ) -> None:
        if new_total < 0:
            raise ValueError("库存总数不能为负数")
        cursor = connection.execute(
            """
            UPDATE daily_inventory
               SET total = ?, version = version + 1
             WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?
               AND ? >= sold + locked + group_locked
            """,
            (
                new_total,
                hotel_id,
                room_type_id,
                biz_date.isoformat(),
                new_total,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError("修正后的总数不能小于已售、锁定与协议占用之和")

    # ------------------------------------------------------------------
    # Prices
    # ------------------------------------------------------------------
    def get_price(
        self,
        connection: sqlite3.Connection | None,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
    ) -> DailyPrice | None:
        sql = (
            "SELECT * FROM daily_price "
            "WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?"
        )
        params = (hotel_id, room_type_id, biz_date.isoformat())
        row = (
            connection.execute(sql, params).fetchone()
            if connection
            else self.db.query_one(sql, params)
        )
        return price_from_row(row) if row else None

    def list_prices(
        self, hotel_id: str, room_type_id: str, start: date, end: date
    ) -> list[DailyPrice]:
        rows = self.db.query(
            """
            SELECT * FROM daily_price
            WHERE hotel_id = ? AND room_type_id = ?
              AND biz_date >= ? AND biz_date < ?
            ORDER BY biz_date
            """,
            (hotel_id, room_type_id, start.isoformat(), end.isoformat()),
        )
        return [price_from_row(row) for row in rows]

    def set_price(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
        final_price: str,
    ) -> None:
        cursor = connection.execute(
            """
            UPDATE daily_price SET final_price = ?
             WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?
            """,
            (final_price, hotel_id, room_type_id, biz_date.isoformat()),
        )
        if cursor.rowcount == 0:
            base_row = connection.execute(
                "SELECT base_price FROM daily_price WHERE room_type_id = ? LIMIT 1",
                (room_type_id,),
            ).fetchone()
            base = base_row["base_price"] if base_row else final_price
            connection.execute(
                """
                INSERT INTO daily_price
                    (hotel_id, room_type_id, biz_date, base_price, final_price)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    hotel_id,
                    room_type_id,
                    biz_date.isoformat(),
                    money_text(base),
                    final_price,
                ),
            )

    # ------------------------------------------------------------------
    # Closures
    # ------------------------------------------------------------------
    def add_closure(
        self,
        connection: sqlite3.Connection,
        closure: RoomClosure,
    ) -> None:
        connection.execute(
            """
            INSERT INTO room_closures
                (closure_id, hotel_id, room_type_id, start_date, end_date,
                 reason, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                closure.closure_id,
                closure.hotel_id,
                closure.room_type_id,
                closure.start_date.isoformat(),
                closure.end_date.isoformat(),
                closure.reason,
                closure.created_by,
                datetime_text(closure.created_at),
            ),
        )

    def list_closures(
        self, hotel_id: str, room_type_id: str | None = None
    ) -> list[RoomClosure]:
        sql = "SELECT * FROM room_closures WHERE hotel_id = ?"
        params: list[object] = [hotel_id]
        if room_type_id:
            sql += " AND room_type_id = ?"
            params.append(room_type_id)
        sql += " ORDER BY start_date DESC"
        return [closure_from_row(row) for row in self.db.query(sql, params)]

    def closure_reason(
        self,
        connection: sqlite3.Connection | None,
        hotel_id: str,
        room_type_id: str,
        start: date,
        end: date,
    ) -> str:
        for biz_date in date_range(start, end):
            sql = (
                "SELECT reason FROM room_closures WHERE hotel_id = ? "
                "AND room_type_id = ? AND start_date <= ? AND end_date > ? "
                "LIMIT 1"
            )
            params = (
                hotel_id,
                room_type_id,
                biz_date.isoformat(),
                biz_date.isoformat(),
            )
            row = (
                connection.execute(sql, params).fetchone()
                if connection
                else self.db.query_one(sql, params)
            )
            if row:
                return str(row["reason"])
        return ""

    def delete_closure(
        self, connection: sqlite3.Connection, closure_id: str
    ) -> None:
        connection.execute(
            "DELETE FROM room_closures WHERE closure_id = ?", (closure_id,)
        )

    # ------------------------------------------------------------------
    # Group locks
    # ------------------------------------------------------------------
    def lock_group(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        start: date,
        end: date,
        qty: int,
    ) -> None:
        for biz_date in date_range(start, end):
            cursor = connection.execute(
                """
                UPDATE daily_inventory
                   SET group_locked = group_locked + ?, version = version + 1
                 WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?
                   AND total - sold - locked - group_locked >= ?
                """,
                (
                    qty,
                    hotel_id,
                    room_type_id,
                    biz_date.isoformat(),
                    qty,
                ),
            )
            if cursor.rowcount != 1:
                current = self.get(connection, hotel_id, room_type_id, biz_date)
                remaining = current.available if current else 0
                raise InventoryUnavailable(biz_date.isoformat(), remaining)

    def release_group(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_type_id: str,
        start: date,
        end: date,
        qty: int,
    ) -> None:
        for biz_date in date_range(start, end):
            cursor = connection.execute(
                """
                UPDATE daily_inventory
                   SET group_locked = group_locked - ?, version = version + 1
                 WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?
                   AND group_locked >= ?
                """,
                (
                    qty,
                    hotel_id,
                    room_type_id,
                    biz_date.isoformat(),
                    qty,
                ),
            )
            if cursor.rowcount != 1:
                raise NotFoundError(f"{biz_date} 协议锁房释放失败，占用不足")

    def add_group_lock(
        self, connection: sqlite3.Connection, lock: GroupLock
    ) -> None:
        connection.execute(
            """
            INSERT INTO group_locks
                (lock_id, hotel_id, room_type_id, start_date, end_date, qty,
                 release_at, status, created_by, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lock.lock_id,
                lock.hotel_id,
                lock.room_type_id,
                lock.start_date.isoformat(),
                lock.end_date.isoformat(),
                lock.qty,
                datetime_text(lock.release_at),
                lock.status.value,
                lock.created_by,
                lock.note,
                datetime_text(lock.created_at),
            ),
        )

    def get_group_lock(
        self, connection: sqlite3.Connection, lock_id: str
    ) -> GroupLock | None:
        row = connection.execute(
            "SELECT * FROM group_locks WHERE lock_id = ?", (lock_id,)
        ).fetchone()
        return group_lock_from_row(row) if row else None

    def list_group_locks(
        self, hotel_id: str, active_only: bool = False
    ) -> list[GroupLock]:
        sql = "SELECT * FROM group_locks WHERE hotel_id = ?"
        params: list[object] = [hotel_id]
        if active_only:
            sql += " AND status = ?"
            params.append(GroupLockStatus.ACTIVE.value)
        sql += " ORDER BY start_date DESC, lock_id DESC"
        return [group_lock_from_row(row) for row in self.db.query(sql, params)]

    def list_expired_group_locks(self, now: datetime) -> list[GroupLock]:
        rows = self.db.query(
            """
            SELECT * FROM group_locks
             WHERE status = ? AND release_at <= ?
            """,
            (GroupLockStatus.ACTIVE.value, datetime_text(now)),
        )
        return [group_lock_from_row(row) for row in rows]

    def update_group_lock_status(
        self,
        connection: sqlite3.Connection,
        lock_id: str,
        status: GroupLockStatus,
    ) -> None:
        connection.execute(
            "UPDATE group_locks SET status = ? WHERE lock_id = ?",
            (status.value, lock_id),
        )
