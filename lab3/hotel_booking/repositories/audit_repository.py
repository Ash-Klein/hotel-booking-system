"""Append-only operation log persistence (REQ-030)."""

from __future__ import annotations

from datetime import date, datetime
import sqlite3

from ..domain.enums import Terminal
from ..domain.models import OperationLog, Staff
from ..infrastructure.database import Database
from .mappers import log_from_row


class AuditRepository:
    """Writes and queries immutable audit records."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def write(
        self,
        connection: sqlite3.Connection,
        staff: Staff | None,
        action: str,
        *,
        hotel_id: str = "",
        terminal: Terminal = Terminal.DESKTOP,
        before_data: str = "",
        after_data: str = "",
        order_no: str = "",
        guest_id: str = "",
        result: str = "SUCCESS",
    ) -> None:
        """Write one log row inside the caller's transaction.

        Because the row is inserted in the same transaction as the business
        change, a failed log insert rolls the business change back too. That
        satisfies the "log failure means operation failure" rule.
        """
        connection.execute(
            """
            INSERT INTO operation_logs
                (staff_id, staff_name, hotel_id, terminal, action,
                 before_data, after_data, order_no, guest_id, result, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                staff.staff_id if staff else "SYSTEM",
                staff.name if staff else "系统",
                hotel_id,
                terminal.value,
                action,
                before_data[:2000],
                after_data[:2000],
                order_no,
                guest_id,
                result,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )

    def list_logs(
        self,
        staff: Staff,
        *,
        action: str = "",
        order_no: str = "",
        start: date | None = None,
        end: date | None = None,
        limit: int = 300,
    ) -> list[OperationLog]:
        """Return logs allowed by the role's data scope."""
        clauses: list[str] = []
        params: list[object] = []
        if not staff.role.is_group_level:
            if not staff.hotel_ids:
                return []
            placeholders = ",".join("?" for _ in staff.hotel_ids)
            clauses.append(f"hotel_id IN ({placeholders})")
            params.extend(staff.hotel_ids)
        if action:
            clauses.append("action LIKE ?")
            params.append(f"%{action}%")
        if order_no:
            clauses.append("order_no LIKE ?")
            params.append(f"%{order_no}%")
        if start:
            clauses.append("created_at >= ?")
            params.append(datetime.combine(start, datetime.min.time()).isoformat())
        if end:
            clauses.append("created_at < ?")
            params.append(
                datetime.combine(end, datetime.max.time()).isoformat()
            )
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.db.query(
            f"SELECT * FROM operation_logs {where} "
            "ORDER BY created_at DESC, log_id DESC LIMIT ?",
            [*params, limit],
        )
        return [log_from_row(row) for row in rows]

    def count(self, hotel_id: str | None = None) -> int:
        if hotel_id:
            value = self.db.scalar(
                "SELECT COUNT(*) FROM operation_logs WHERE hotel_id = ?",
                (hotel_id,),
                default=0,
            )
        else:
            value = self.db.scalar(
                "SELECT COUNT(*) FROM operation_logs", default=0
            )
        return int(value)

    def export_rows(self, staff: Staff) -> list[OperationLog]:
        """Return the same scoped rows without truncation for CSV export."""
        return self.list_logs(staff, limit=100_000)
