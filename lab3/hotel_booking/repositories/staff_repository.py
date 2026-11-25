"""Staff and role persistence."""

from __future__ import annotations

from ..domain.models import Staff
from ..infrastructure.database import Database
from .mappers import staff_from_row


class StaffRepository:
    """Lookup and administration of back-office users."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def find_by_username(self, username: str) -> Staff | None:
        row = self.db.query_one(
            "SELECT * FROM staff WHERE username = ?", (username,)
        )
        if not row:
            return None
        hotel_rows = self.db.query(
            "SELECT hotel_id FROM staff_hotels WHERE staff_id = ? ORDER BY hotel_id",
            (row["staff_id"],),
        )
        hotel_ids = [str(item["hotel_id"]) for item in hotel_rows]
        return staff_from_row(row, hotel_ids)

    def get(self, staff_id: str) -> Staff | None:
        row = self.db.query_one(
            "SELECT * FROM staff WHERE staff_id = ?", (staff_id,)
        )
        if not row:
            return None
        hotel_rows = self.db.query(
            "SELECT hotel_id FROM staff_hotels WHERE staff_id = ?",
            (staff_id,),
        )
        return staff_from_row(
            row, [str(item["hotel_id"]) for item in hotel_rows]
        )

    def list_staff(self) -> list[Staff]:
        rows = self.db.query("SELECT * FROM staff ORDER BY staff_id")
        result: list[Staff] = []
        for row in rows:
            hotel_rows = self.db.query(
                "SELECT hotel_id FROM staff_hotels WHERE staff_id = ?",
                (row["staff_id"],),
            )
            result.append(
                staff_from_row(
                    row, [str(item["hotel_id"]) for item in hotel_rows]
                )
            )
        return result

    def display_names(self) -> dict[str, str]:
        rows = self.db.query("SELECT staff_id, name FROM staff")
        return {str(row["staff_id"]): str(row["name"]) for row in rows}
