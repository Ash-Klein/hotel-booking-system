"""SQLite connection and transaction management."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Sequence

from .. import config
from .schema import SCHEMA_SQL


class Database:
    """Small connection factory around SQLite.

    Every operation gets its own connection. This keeps the Tkinter UI free of
    long-lived cursors and makes the same code safe for the concurrent unit
    tests that simulate two guests competing for the last room.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else config.database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Open a configured connection."""
        connection = sqlite3.connect(
            self.path, timeout=10.0, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 8000")
        return connection

    def initialize(self) -> None:
        """Create the schema and seed master data once."""
        connection = self.connect()
        try:
            connection.executescript(SCHEMA_SQL)
        finally:
            connection.close()
        from .seed import seed_master_data

        seed_master_data(self)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run a write transaction with immediate lock and rollback."""
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def read_connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a read-only style connection that is always closed."""
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    def query(
        self, sql: str, params: Sequence[Any] | None = None
    ) -> list[sqlite3.Row]:
        """Return all rows of a SELECT."""
        with self.read_connection() as connection:
            return list(connection.execute(sql, tuple(params or ())).fetchall())

    def query_one(
        self, sql: str, params: Sequence[Any] | None = None
    ) -> sqlite3.Row | None:
        """Return the first row of a SELECT, or ``None``."""
        with self.read_connection() as connection:
            return connection.execute(sql, tuple(params or ())).fetchone()

    def scalar(
        self, sql: str, params: Sequence[Any] | None = None, default: Any = None
    ) -> Any:
        """Return the first column of the first row."""
        row = self.query_one(sql, params)
        return row[0] if row is not None else default

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> int:
        """Execute one statement in its own transaction."""
        with self.transaction() as connection:
            cursor = connection.execute(sql, tuple(params or ()))
            return cursor.rowcount

    def table_count(self, table: str) -> int:
        """Return a row count for a whitelisted table."""
        allowed = {
            "hotels",
            "room_types",
            "daily_inventory",
            "orders",
            "staff",
            "guests",
            "operation_logs",
        }
        if table not in allowed:
            raise ValueError(f"不允许统计表 {table}")
        return int(self.scalar(f"SELECT COUNT(*) FROM {table}", default=0))

    def close(self) -> None:
        """Compatibility no-op; connections are opened per operation."""
