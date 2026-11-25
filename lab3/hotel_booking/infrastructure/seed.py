"""Deterministic master data for the demo and for unit tests."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import sqlite3

from ..domain.enums import HotelStatus, Role, RoomStatus, RoomTypeStatus
from ..domain.money import as_money, money_text
from .database import Database
from .security import hash_password

HOTELS: list[dict[str, str]] = [
    {
        "hotel_id": "H001",
        "name": "云栖外滩酒店",
        "city": "上海",
        "district": "黄浦区",
        "address": "中山东一路 18 号",
        "franchise_type": "DIRECT",
        "phone": "021-6300-1001",
    },
    {
        "hotel_id": "H002",
        "name": "云栖静安酒店",
        "city": "上海",
        "district": "静安区",
        "address": "南京西路 1266 号",
        "franchise_type": "DIRECT",
        "phone": "021-6300-1002",
    },
    {
        "hotel_id": "H003",
        "name": "云栖虹桥加盟店",
        "city": "上海",
        "district": "闵行区",
        "address": "申长路 688 号",
        "franchise_type": "FRANCHISE",
        "phone": "021-6300-1003",
    },
    {
        "hotel_id": "H004",
        "name": "云栖西湖酒店",
        "city": "杭州",
        "district": "西湖区",
        "address": "北山街 29 号",
        "franchise_type": "DIRECT",
        "phone": "0571-8800-2001",
    },
    {
        "hotel_id": "H005",
        "name": "云栖滨江加盟店",
        "city": "杭州",
        "district": "滨江区",
        "address": "江南大道 3850 号",
        "franchise_type": "FRANCHISE",
        "phone": "0571-8800-2002",
    },
    {
        "hotel_id": "H006",
        "name": "云栖新街口酒店",
        "city": "南京",
        "district": "秦淮区",
        "address": "中山南路 88 号",
        "franchise_type": "DIRECT",
        "phone": "025-8600-3001",
    },
]

ROOM_TYPE_TEMPLATES: list[dict[str, object]] = [
    {
        "name": "高级大床房",
        "bed_type": "1.8m 大床",
        "capacity": 2,
        "breakfast": True,
        "base_price": "468.00",
        "total": 10,
    },
    {
        "name": "豪华双床房",
        "bed_type": "1.35m 双床",
        "capacity": 2,
        "breakfast": True,
        "base_price": "568.00",
        "total": 8,
    },
    {
        "name": "家庭套房",
        "bed_type": "1.8m 大床 + 沙发床",
        "capacity": 3,
        "breakfast": True,
        "base_price": "788.00",
        "total": 6,
    },
]

CITY_FACTOR = {"上海": Decimal("1.15"), "杭州": Decimal("1.00"), "南京": Decimal("0.92")}
TYPE_FACTOR = [Decimal("1.00"), Decimal("1.22"), Decimal("1.62")]


def _special_dates(today: date) -> list[tuple[date, str, str]]:
    """Relative special dates keep the demo interesting on any run date."""
    return [
        (today + timedelta(days=12), "城市秋季展会", "展会周期，取消扣首晚 100%"),
        (today + timedelta(days=21), "法定节假日", "节假日特殊取消规则"),
    ]


def seed_master_data(db: Database) -> None:
    """Insert hotels, room types, inventory, prices, rooms and staff.

    The function is idempotent: calling it on an already seeded database does
    nothing beyond a quick count check.
    """
    if db.table_count("hotels") > 0:
        return
    today = date.today()
    specials = {item[0] for item in _special_dates(today)}
    with db.transaction() as connection:
        _insert_hotels(connection)
        _insert_room_types_and_stock(connection, today, specials)
        _insert_special_dates(connection, today)
        _insert_staff(connection)


def _insert_hotels(connection: sqlite3.Connection) -> None:
    """Insert one block of seeded master data."""
    for hotel in HOTELS:
        connection.execute(
            """
            INSERT INTO hotels
                (hotel_id, name, city, district, address, franchise_type, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hotel["hotel_id"],
                hotel["name"],
                hotel["city"],
                hotel["district"],
                hotel["address"],
                hotel["franchise_type"],
                hotel["phone"],
                HotelStatus.OPEN.value,
            ),
        )


def _insert_room_types_and_stock(
    connection: sqlite3.Connection, today: date, specials: set[date]
) -> None:
    """Insert room types, daily stock, prices and physical rooms."""
    start = today - timedelta(days=2)
    end = today + timedelta(days=46)
    type_index = 0
    for hotel in HOTELS:
        for template_index, template in enumerate(ROOM_TYPE_TEMPLATES):
            type_index += 1
            room_type_id = f"RT{type_index:03d}"
            base_price = as_money(template["base_price"])  # type: ignore[arg-type]
            connection.execute(
                """
                INSERT INTO room_types
                    (room_type_id, hotel_id, name, bed_type, capacity,
                     breakfast, base_price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    room_type_id,
                    hotel["hotel_id"],
                    template["name"],
                    template["bed_type"],
                    template["capacity"],
                    int(template["breakfast"]),  # type: ignore[arg-type]
                    money_text(base_price),
                    RoomTypeStatus.ON_SALE.value,
                ),
            )
            total = int(template["total"])  # type: ignore[arg-type]
            for offset in range((end - start).days):
                biz_date = start + timedelta(days=offset)
                final_price = _nightly_price(
                    base_price, hotel["city"], template_index, biz_date, specials
                )
                connection.execute(
                    """
                    INSERT INTO daily_inventory
                        (hotel_id, room_type_id, biz_date, total)
                    VALUES (?, ?, ?, ?)
                    """,
                    (hotel["hotel_id"], room_type_id, biz_date.isoformat(), total),
                )
                connection.execute(
                    """
                    INSERT INTO daily_price
                        (hotel_id, room_type_id, biz_date, base_price, final_price)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        hotel["hotel_id"],
                        room_type_id,
                        biz_date.isoformat(),
                        money_text(base_price),
                        money_text(final_price),
                    ),
                )
            for index in range(total):
                room_no = f"{template_index + 1}{index + 1:02d}"
                connection.execute(
                    """
                    INSERT INTO rooms
                        (hotel_id, room_no, room_type_id, status, floor)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        hotel["hotel_id"],
                        room_no,
                        room_type_id,
                        RoomStatus.AVAILABLE.value,
                        8 + template_index + index // 6,
                    ),
                )


def _nightly_price(
    base: Decimal,
    city: str,
    template_index: int,
    biz_date: date,
    specials: set[date],
) -> Decimal:
    """Apply city, room-type, weekend and special-date pricing."""
    price = base * CITY_FACTOR[city] * TYPE_FACTOR[template_index]
    if biz_date.weekday() in {4, 5}:
        price *= Decimal("1.18")
    if biz_date in specials:
        price += Decimal("180.00")
    # Hotel pricing commonly ends in whole ten yuan; keep it predictable.
    rounded = (price / Decimal("10")).quantize(Decimal("1")) * Decimal("10")
    return as_money(rounded)


def _insert_special_dates(connection: sqlite3.Connection, today: date) -> None:
    """Insert one block of seeded master data."""
    for biz_date, name, note in _special_dates(today):
        connection.execute(
            "INSERT INTO special_dates (biz_date, name, note) VALUES (?, ?, ?)",
            (biz_date.isoformat(), name, note),
        )


def _insert_staff(connection: sqlite3.Connection) -> None:
    """Insert one block of seeded master data."""
    accounts = [
        ("S001", "frontdesk", "Frontdesk@123", "陈晓", Role.FRONT_DESK, ["H001"]),
        ("S002", "manager", "Manager@123", "王琳", Role.MANAGER, ["H001", "H002"]),
        ("S003", "finance", "Finance@123", "赵敏", Role.FINANCE, []),
        ("S004", "admin", "Admin@123", "周远", Role.ADMIN, []),
        ("S005", "city", "City@123", "孙悦", Role.CITY_MANAGER, ["H001", "H002", "H003"]),
    ]
    for staff_id, username, password, name, role, hotel_ids in accounts:
        password_hash, salt = hash_password(password)
        connection.execute(
            """
            INSERT INTO staff
                (staff_id, username, password_hash, salt, name, role, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now', 'localtime'))
            """,
            (staff_id, username, password_hash, salt, name, role.value),
        )
        for hotel_id in hotel_ids:
            connection.execute(
                "INSERT INTO staff_hotels (staff_id, hotel_id) VALUES (?, ?)",
                (staff_id, hotel_id),
            )
