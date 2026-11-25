"""SQLite schema for the hotel booking system.

The schema follows the UML entities and keeps all money columns as fixed-scale
TEXT so that Decimal values round-trip exactly. Stock columns use CHECK
constraints to make negative inventory impossible even if a service bug slips
through.
"""

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS hotels (
    hotel_id        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    city            TEXT NOT NULL,
    district        TEXT NOT NULL,
    address         TEXT NOT NULL,
    franchise_type  TEXT NOT NULL CHECK (franchise_type IN ('DIRECT', 'FRANCHISE')),
    phone           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'OPEN'
);

CREATE TABLE IF NOT EXISTS room_types (
    room_type_id    TEXT PRIMARY KEY,
    hotel_id        TEXT NOT NULL REFERENCES hotels(hotel_id),
    name            TEXT NOT NULL,
    bed_type        TEXT NOT NULL,
    capacity        INTEGER NOT NULL CHECK (capacity > 0),
    breakfast       INTEGER NOT NULL CHECK (breakfast IN (0, 1)),
    base_price      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'ON_SALE'
);

CREATE TABLE IF NOT EXISTS daily_inventory (
    hotel_id        TEXT NOT NULL REFERENCES hotels(hotel_id),
    room_type_id    TEXT NOT NULL REFERENCES room_types(room_type_id),
    biz_date        TEXT NOT NULL,
    total           INTEGER NOT NULL CHECK (total >= 0),
    sold            INTEGER NOT NULL DEFAULT 0 CHECK (sold >= 0),
    locked          INTEGER NOT NULL DEFAULT 0 CHECK (locked >= 0),
    group_locked    INTEGER NOT NULL DEFAULT 0 CHECK (group_locked >= 0),
    version         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (hotel_id, room_type_id, biz_date),
    CHECK (total - sold - locked - group_locked >= 0)
);

CREATE TABLE IF NOT EXISTS daily_price (
    hotel_id        TEXT NOT NULL,
    room_type_id    TEXT NOT NULL,
    biz_date        TEXT NOT NULL,
    base_price      TEXT NOT NULL,
    final_price     TEXT NOT NULL,
    PRIMARY KEY (hotel_id, room_type_id, biz_date)
);

CREATE TABLE IF NOT EXISTS room_closures (
    closure_id      TEXT PRIMARY KEY,
    hotel_id        TEXT NOT NULL,
    room_type_id    TEXT NOT NULL,
    start_date      TEXT NOT NULL,
    end_date        TEXT NOT NULL,
    reason          TEXT NOT NULL,
    created_by      TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS group_locks (
    lock_id         TEXT PRIMARY KEY,
    hotel_id        TEXT NOT NULL,
    room_type_id    TEXT NOT NULL,
    start_date      TEXT NOT NULL,
    end_date        TEXT NOT NULL,
    qty             INTEGER NOT NULL CHECK (qty > 0),
    release_at      TEXT NOT NULL,
    status          TEXT NOT NULL,
    created_by      TEXT NOT NULL,
    note            TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS guests (
    guest_id        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    phone           TEXT NOT NULL UNIQUE,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_no        TEXT PRIMARY KEY,
    guest_id        TEXT NOT NULL REFERENCES guests(guest_id),
    hotel_id        TEXT NOT NULL REFERENCES hotels(hotel_id),
    room_type_id    TEXT NOT NULL REFERENCES room_types(room_type_id),
    room_type_name  TEXT NOT NULL,
    check_in        TEXT NOT NULL,
    check_out       TEXT NOT NULL,
    status          TEXT NOT NULL,
    pay_mode        TEXT NOT NULL,
    total_amount    TEXT NOT NULL,
    contact_name    TEXT NOT NULL,
    contact_phone   TEXT NOT NULL,
    expire_at       TEXT,
    assigned_rooms  TEXT NOT NULL DEFAULT '',
    version         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no        TEXT NOT NULL REFERENCES orders(order_no) ON DELETE CASCADE,
    qty             INTEGER NOT NULL CHECK (qty > 0),
    cancelled_qty   INTEGER NOT NULL DEFAULT 0 CHECK (cancelled_qty >= 0),
    unit_price      TEXT NOT NULL,
    breakfast       INTEGER NOT NULL DEFAULT 0,
    first_night_price TEXT NOT NULL DEFAULT '0.00',
    CHECK (cancelled_qty <= qty)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_no      TEXT PRIMARY KEY,
    order_no        TEXT NOT NULL REFERENCES orders(order_no),
    amount          TEXT NOT NULL,
    method          TEXT NOT NULL,
    status          TEXT NOT NULL,
    paid_at         TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS refunds (
    refund_no           TEXT PRIMARY KEY,
    order_no            TEXT NOT NULL REFERENCES orders(order_no),
    payment_no          TEXT NOT NULL DEFAULT '',
    amount              TEXT NOT NULL,
    status              TEXT NOT NULL,
    reason              TEXT NOT NULL,
    requested_by        TEXT NOT NULL,
    first_night_amount  TEXT NOT NULL,
    approver_id         TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL,
    approved_at         TEXT,
    submitted_at        TEXT
);

CREATE TABLE IF NOT EXISTS staff (
    staff_id        TEXT PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    salt            TEXT NOT NULL,
    name            TEXT NOT NULL,
    role            TEXT NOT NULL,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staff_hotels (
    staff_id        TEXT NOT NULL REFERENCES staff(staff_id) ON DELETE CASCADE,
    hotel_id        TEXT NOT NULL REFERENCES hotels(hotel_id),
    PRIMARY KEY (staff_id, hotel_id)
);

CREATE TABLE IF NOT EXISTS operation_logs (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id        TEXT NOT NULL,
    staff_name      TEXT NOT NULL,
    hotel_id        TEXT NOT NULL DEFAULT '',
    terminal        TEXT NOT NULL,
    action          TEXT NOT NULL,
    before_data     TEXT NOT NULL DEFAULT '',
    after_data      TEXT NOT NULL DEFAULT '',
    order_no        TEXT NOT NULL DEFAULT '',
    guest_id        TEXT NOT NULL DEFAULT '',
    result          TEXT NOT NULL DEFAULT 'SUCCESS',
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_changes (
    change_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no        TEXT NOT NULL REFERENCES orders(order_no),
    change_type     TEXT NOT NULL,
    before_data     TEXT NOT NULL,
    after_data      TEXT NOT NULL,
    amount_delta    TEXT NOT NULL,
    operator_id     TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cancellations (
    cancellation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no        TEXT NOT NULL REFERENCES orders(order_no),
    cancelled_qty   INTEGER NOT NULL,
    penalty         TEXT NOT NULL,
    refund_amount   TEXT NOT NULL,
    reason          TEXT NOT NULL,
    operator_id     TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exception_records (
    exception_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no        TEXT NOT NULL,
    exception_type  TEXT NOT NULL,
    description     TEXT NOT NULL,
    amount          TEXT NOT NULL DEFAULT '0.00',
    status          TEXT NOT NULL,
    created_by      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    resolved_at     TEXT
);

CREATE TABLE IF NOT EXISTS rooms (
    hotel_id        TEXT NOT NULL REFERENCES hotels(hotel_id),
    room_no         TEXT NOT NULL,
    room_type_id    TEXT NOT NULL REFERENCES room_types(room_type_id),
    status          TEXT NOT NULL DEFAULT 'AVAILABLE',
    floor           INTEGER NOT NULL,
    PRIMARY KEY (hotel_id, room_no)
);

CREATE TABLE IF NOT EXISTS special_dates (
    biz_date        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    note            TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_inventory_date
    ON daily_inventory (biz_date, hotel_id);
CREATE INDEX IF NOT EXISTS idx_orders_status
    ON orders (status, check_in);
CREATE INDEX IF NOT EXISTS idx_orders_guest
    ON orders (guest_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_hotel
    ON orders (hotel_id, check_in);
CREATE INDEX IF NOT EXISTS idx_payments_order
    ON payments (order_no);
CREATE INDEX IF NOT EXISTS idx_refunds_status
    ON refunds (status, created_at);
CREATE INDEX IF NOT EXISTS idx_logs_time
    ON operation_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_exceptions_status
    ON exception_records (status, created_at DESC);
"""
