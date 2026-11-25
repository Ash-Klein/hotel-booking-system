"""Read/write repository for hotels, room types, rooms and special dates."""

from __future__ import annotations

from datetime import date
import sqlite3

from ..domain.enums import HotelStatus, RoomStatus, RoomTypeStatus
from ..domain.models import Hotel, Room, RoomType, SpecialDate
from ..infrastructure.database import Database
from .mappers import (
    hotel_from_row,
    room_from_row,
    room_type_from_row,
    special_date_from_row,
)


class CatalogRepository:
    """Persistence for relatively static catalog data."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def list_hotels(
        self, city: str | None = None, open_only: bool = False
    ) -> list[Hotel]:
        clauses: list[str] = []
        params: list[object] = []
        if city:
            clauses.append("city = ?")
            params.append(city)
        if open_only:
            clauses.append("status = ?")
            params.append(HotelStatus.OPEN.value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.db.query(
            f"SELECT * FROM hotels {where} ORDER BY city, hotel_id", params
        )
        return [hotel_from_row(row) for row in rows]

    def get_hotel(self, hotel_id: str) -> Hotel | None:
        row = self.db.query_one(
            "SELECT * FROM hotels WHERE hotel_id = ?", (hotel_id,)
        )
        return hotel_from_row(row) if row else None

    def list_cities(self) -> list[str]:
        rows = self.db.query("SELECT DISTINCT city FROM hotels ORDER BY city")
        return [str(row["city"]) for row in rows]

    def list_room_types(
        self, hotel_id: str, on_sale_only: bool = False
    ) -> list[RoomType]:
        sql = "SELECT * FROM room_types WHERE hotel_id = ?"
        params: list[object] = [hotel_id]
        if on_sale_only:
            sql += " AND status = ?"
            params.append(RoomTypeStatus.ON_SALE.value)
        sql += " ORDER BY room_type_id"
        rows = self.db.query(sql, params)
        return [room_type_from_row(row) for row in rows]

    def list_all_room_types(self) -> list[RoomType]:
        rows = self.db.query("SELECT * FROM room_types ORDER BY room_type_id")
        return [room_type_from_row(row) for row in rows]

    def get_room_type(self, room_type_id: str) -> RoomType | None:
        row = self.db.query_one(
            "SELECT * FROM room_types WHERE room_type_id = ?", (room_type_id,)
        )
        return room_type_from_row(row) if row else None

    def set_hotel_status(
        self, connection: sqlite3.Connection, hotel_id: str, status: HotelStatus
    ) -> int:
        cursor = connection.execute(
            "UPDATE hotels SET status = ? WHERE hotel_id = ?",
            (status.value, hotel_id),
        )
        return cursor.rowcount

    def set_room_type_status(
        self,
        connection: sqlite3.Connection,
        room_type_id: str,
        status: RoomTypeStatus,
    ) -> int:
        cursor = connection.execute(
            "UPDATE room_types SET status = ? WHERE room_type_id = ?",
            (status.value, room_type_id),
        )
        return cursor.rowcount

    def set_base_price(
        self, connection: sqlite3.Connection, room_type_id: str, price: str
    ) -> int:
        cursor = connection.execute(
            "UPDATE room_types SET base_price = ? WHERE room_type_id = ?",
            (price, room_type_id),
        )
        return cursor.rowcount

    def list_rooms(
        self, hotel_id: str, room_type_id: str | None = None
    ) -> list[Room]:
        sql = "SELECT * FROM rooms WHERE hotel_id = ?"
        params: list[object] = [hotel_id]
        if room_type_id:
            sql += " AND room_type_id = ?"
            params.append(room_type_id)
        sql += " ORDER BY room_no"
        return [room_from_row(row) for row in self.db.query(sql, params)]

    def get_room(
        self, connection: sqlite3.Connection, hotel_id: str, room_no: str
    ) -> Room | None:
        row = connection.execute(
            "SELECT * FROM rooms WHERE hotel_id = ? AND room_no = ?",
            (hotel_id, room_no),
        ).fetchone()
        return room_from_row(row) if row else None

    def set_rooms_status(
        self,
        connection: sqlite3.Connection,
        hotel_id: str,
        room_numbers: list[str],
        status: RoomStatus,
    ) -> None:
        for room_no in room_numbers:
            connection.execute(
                "UPDATE rooms SET status = ? WHERE hotel_id = ? AND room_no = ?",
                (status.value, hotel_id, room_no),
            )

    def list_special_dates(self) -> list[SpecialDate]:
        rows = self.db.query("SELECT * FROM special_dates ORDER BY biz_date")
        return [special_date_from_row(row) for row in rows]

    def special_date_set(self) -> set[date]:
        return {item.biz_date for item in self.list_special_dates()}

    def add_special_date(
        self,
        connection: sqlite3.Connection,
        special: SpecialDate,
    ) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO special_dates (biz_date, name, note)
            VALUES (?, ?, ?)
            """,
            (special.biz_date.isoformat(), special.name, special.note),
        )
