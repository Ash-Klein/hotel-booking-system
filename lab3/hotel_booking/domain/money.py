"""Money and masking helpers.

Money is always represented as :class:`decimal.Decimal` in the domain and as
fixed-scale text in SQLite, never as ``float``. This avoids the classic
``0.1 + 0.2`` error in refund and reconciliation amounts.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import re

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def as_money(value: Decimal | str | int | float) -> Decimal:
    """Return a two-decimal Decimal rounded half-up."""
    if isinstance(value, float):
        value = str(value)
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def money_text(value: Decimal | str | int | float) -> str:
    """Fixed-scale string for persistence."""
    return f"{as_money(value):.2f}"


def yuan(value: Decimal | str | int | float) -> str:
    """Format an amount for the UI."""
    return f"¥{as_money(value):,.2f}"


def mask_phone(phone: str) -> str:
    """Mask the middle four digits of an 11-digit mobile number."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 11:
        return f"{digits[:3]}****{digits[-4:]}"
    if len(digits) > 4:
        return f"{digits[:2]}***{digits[-2:]}"
    return phone or "-"


def parse_date(value: str | date) -> date:
    """Parse ISO text into a date."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse an ISO datetime, tolerating a trailing ``Z``."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def date_range(start: date, end: date) -> list[date]:
    """Return every night of a half-open stay ``[start, end)``."""
    nights: list[date] = []
    cursor = start
    while cursor < end:
        nights.append(cursor)
        cursor += timedelta(days=1)
    return nights


def datetime_text(value: datetime | None) -> str | None:
    """Persist a naive local datetime with second precision."""
    return value.isoformat(timespec="seconds") if value else None
