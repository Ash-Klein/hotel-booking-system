"""Domain entities of the hotel booking system.

The classes mirror the eleven core classes of the experiment-two UML class
diagram and add the supporting entities listed in its note (staff, logs,
order changes, cancellations and exception records).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from .enums import (
    ExceptionStatus,
    ExceptionType,
    GroupLockStatus,
    HotelStatus,
    ORDER_TRANSITIONS,
    OrderStatus,
    PayMode,
    PaymentStatus,
    RefundStatus,
    Role,
    RoomStatus,
    RoomTypeStatus,
)
from .errors import StateTransitionError, ValidationError
from .money import ZERO, as_money, mask_phone


@dataclass(slots=True)
class Hotel:
    """A hotel (property) in the group."""

    hotel_id: str
    name: str
    city: str
    district: str
    address: str
    franchise_type: str
    phone: str
    status: HotelStatus = HotelStatus.OPEN
    star: int = 4
    rating: Decimal = Decimal("4.6")

    @property
    def is_open(self) -> bool:
        return self.status is HotelStatus.OPEN

    @property
    def type_label(self) -> str:
        return "直营店" if self.franchise_type == "DIRECT" else "加盟店"

    @property
    def full_address(self) -> str:
        """City + district + street, the line shown on the room list header."""
        return f"{self.city} · {self.district}{self.address}"


@dataclass(slots=True)
class RoomType:
    """A sellable room type belonging to exactly one hotel."""

    room_type_id: str
    hotel_id: str
    name: str
    bed_type: str
    capacity: int
    breakfast: bool
    base_price: Decimal
    status: RoomTypeStatus = RoomTypeStatus.ON_SALE
    area_sqm: int = 28

    @property
    def breakfast_label(self) -> str:
        return "含早" if self.breakfast else "不含早"

    @property
    def short_spec(self) -> str:
        """One-line spec used on the room cards (``28㎡ · 1.8m 大床 · 含早``)."""
        return f"{self.area_sqm}㎡ · {self.bed_type} · {self.breakfast_label}"

    @property
    def is_on_sale(self) -> bool:
        return self.status is RoomTypeStatus.ON_SALE


@dataclass(slots=True)
class DailyInventory:
    """Inventory of one hotel + room type + natural day.

    The invariant is ``available = total - sold - locked - group_locked`` and
    must never be negative. The ``version`` field is the optimistic-lock token
    mentioned in the UML note.
    """

    hotel_id: str
    room_type_id: str
    biz_date: date
    total: int
    sold: int = 0
    locked: int = 0
    group_locked: int = 0
    version: int = 0

    @property
    def available(self) -> int:
        return self.total - self.sold - self.locked - self.group_locked

    @property
    def occupied(self) -> int:
        return self.sold + self.locked + self.group_locked

    def reserve(self, qty: int) -> bool:
        """Lock ``qty`` rooms for a pending order."""
        if qty <= 0 or self.available < qty:
            return False
        self.locked += qty
        self.version += 1
        return True

    def release(self, qty: int) -> None:
        """Release locked rooms when a pending order is cancelled."""
        if qty <= 0 or qty > self.locked:
            raise ValidationError("释放锁房数量超过当前锁定量")
        self.locked -= qty
        self.version += 1

    def confirm(self, qty: int) -> None:
        """Turn locked rooms into sold rooms after payment."""
        if qty <= 0 or qty > self.locked:
            raise ValidationError("确认锁房数量超过当前锁定量")
        self.locked -= qty
        self.sold += qty
        self.version += 1

    def lock_group(self, qty: int) -> bool:
        """Reserve rooms for a corporate agreement."""
        if qty <= 0 or self.available < qty:
            return False
        self.group_locked += qty
        self.version += 1
        return True

    def release_group(self, qty: int) -> None:
        """Release corporate rooms back to public availability."""
        if qty <= 0 or qty > self.group_locked:
            raise ValidationError("释放协议锁房数量超过当前锁定量")
        self.group_locked -= qty
        self.version += 1

    def sell_confirmed(self, qty: int) -> bool:
        """Directly consume available rooms for a confirmed-order change."""
        if qty <= 0 or self.available < qty:
            return False
        self.sold += qty
        self.version += 1
        return True

    def release_sold(self, qty: int) -> None:
        """Return sold rooms to availability (cancel / checkout)."""
        qty = min(qty, self.sold)
        if qty <= 0:
            return
        self.sold -= qty
        self.version += 1


@dataclass(slots=True)
class DailyPrice:
    """Nightly price snapshot. ``final_price`` is what the guest pays."""

    hotel_id: str
    room_type_id: str
    biz_date: date
    base_price: Decimal
    final_price: Decimal

    @property
    def is_discounted(self) -> bool:
        return self.final_price < self.base_price


@dataclass(slots=True)
class RoomClosure:
    """A manual closure of one room type for a date interval."""

    closure_id: str
    hotel_id: str
    room_type_id: str
    start_date: date
    end_date: date
    reason: str
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)

    def covers(self, biz_date: date) -> bool:
        return self.start_date <= biz_date < self.end_date


@dataclass(slots=True)
class GroupLock:
    """Rooms reserved for a corporate agreement (REQ-008)."""

    lock_id: str
    hotel_id: str
    room_type_id: str
    start_date: date
    end_date: date
    qty: int
    release_at: datetime
    status: GroupLockStatus
    created_by: str
    note: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def nights(self) -> int:
        return max((self.end_date - self.start_date).days, 0)

    @property
    def is_active(self) -> bool:
        return self.status is GroupLockStatus.ACTIVE


@dataclass(slots=True)
class Guest:
    """A guest identified by mobile number."""

    guest_id: str
    name: str
    phone: str
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def phone_masked(self) -> str:
        return mask_phone(self.phone)


@dataclass(slots=True)
class OrderItem:
    """Room quantity and transaction price snapshot of an order."""

    item_id: int
    order_no: str
    qty: int
    cancelled_qty: int
    unit_price: Decimal
    breakfast: bool
    first_night_price: Decimal = ZERO

    @property
    def active_qty(self) -> int:
        return self.qty - self.cancelled_qty

    @property
    def room_subtotal(self) -> Decimal:
        return as_money(self.unit_price * self.active_qty)


@dataclass(slots=True)
class Order:
    """The order aggregate root. One order contains one room type only."""

    order_no: str
    guest_id: str
    hotel_id: str
    room_type_id: str
    room_type_name: str
    check_in: date
    check_out: date
    status: OrderStatus
    pay_mode: PayMode
    total_amount: Decimal
    contact_name: str
    contact_phone: str
    expire_at: datetime | None
    assigned_rooms: str = ""
    arrival_time: str = ""
    version: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    hotel_name: str = ""
    item: OrderItem | None = None
    guest_names: list[str] = field(default_factory=list)

    @property
    def nights(self) -> int:
        return max((self.check_out - self.check_in).days, 0)

    @property
    def guests_label(self) -> str:
        """Every registered guest of the order, contact first."""
        names = [name for name in self.guest_names if name]
        if self.contact_name and self.contact_name not in names:
            names.insert(0, self.contact_name)
        return "、".join(names) if names else self.contact_name

    @property
    def qty(self) -> int:
        return self.item.qty if self.item else 1

    @property
    def active_qty(self) -> int:
        return self.item.active_qty if self.item else 1

    @property
    def first_night_amount(self) -> Decimal:
        """Per-room first-night amount, the refund approval base."""
        if not self.item:
            return ZERO
        return as_money(self.item.first_night_price)

    @property
    def assigned_room_list(self) -> list[str]:
        return [part for part in self.assigned_rooms.split(",") if part]

    @property
    def is_expired(self) -> bool:
        return self.is_expired_at(datetime.now())

    def is_expired_at(self, moment: datetime) -> bool:
        """Whether the payment/confirmation window has elapsed."""
        return bool(
            self.status is OrderStatus.PENDING_PAYMENT
            and self.expire_at
            and moment > self.expire_at
        )

    @property
    def status_label(self) -> str:
        return self.status.label

    def can_transition(self, target: OrderStatus) -> bool:
        """Check the UML state machine before any mutation."""
        return target in ORDER_TRANSITIONS.get(self.status, frozenset())

    def transition_to(self, target: OrderStatus) -> None:
        """Apply a legal transition or raise a domain error."""
        if not self.can_transition(target):
            raise StateTransitionError(
                f"订单 {self.order_no} 不能从「{self.status.label}」"
                f"变更为「{target.label}」"
            )
        self.status = target
        self.updated_at = datetime.now()

    # The two public methods below intentionally mirror the UML operations.
    def confirm(self) -> None:
        """Confirm a paid / front-desk accepted order."""
        self.transition_to(OrderStatus.CONFIRMED)
        self.expire_at = None

    def cancel(self) -> None:
        """Cancel an order; inventory and refunds are handled by services."""
        self.transition_to(OrderStatus.CANCELLED)

    @property
    def can_cancel(self) -> bool:
        return self.status in {OrderStatus.PENDING_PAYMENT, OrderStatus.CONFIRMED}

    @property
    def can_modify(self) -> bool:
        return self.status is OrderStatus.CONFIRMED

    @property
    def can_check_in(self) -> bool:
        return self.status is OrderStatus.CONFIRMED

    @property
    def can_check_out(self) -> bool:
        return self.status is OrderStatus.CHECKED_IN


@dataclass(slots=True)
class Payment:
    """A payment transaction."""

    payment_no: str
    order_no: str
    amount: Decimal
    method: str
    status: PaymentStatus
    paid_at: datetime | None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class Refund:
    """A refund transaction with approval metadata."""

    refund_no: str
    order_no: str
    payment_no: str
    amount: Decimal
    status: RefundStatus
    reason: str
    requested_by: str
    first_night_amount: Decimal
    approver_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    approved_at: datetime | None = None
    submitted_at: datetime | None = None

    @property
    def requires_approval(self) -> bool:
        return self.first_night_amount > Decimal("500.00")


@dataclass(slots=True)
class Staff:
    """A back-office user, optionally scoped to several hotels."""

    staff_id: str
    username: str
    password_hash: str
    salt: str
    name: str
    role: Role
    active: bool = True
    hotel_ids: list[str] = field(default_factory=list)

    @property
    def role_label(self) -> str:
        return self.role.label

    def can_access_hotel(self, hotel_id: str) -> bool:
        return self.role.is_group_level or hotel_id in self.hotel_ids


@dataclass(slots=True)
class OperationLog:
    """Immutable audit record (REQ-030)."""

    log_id: int
    staff_id: str
    staff_name: str
    hotel_id: str
    terminal: str
    action: str
    before_data: str
    after_data: str
    order_no: str
    guest_id: str
    result: str
    created_at: datetime


@dataclass(slots=True)
class OrderChange:
    """Audit record of a date / room type / hotel change."""

    change_id: int
    order_no: str
    change_type: str
    before_data: str
    after_data: str
    amount_delta: Decimal
    operator_id: str
    created_at: datetime


@dataclass(slots=True)
class Cancellation:
    """Cancellation and penalty snapshot."""

    cancellation_id: int
    order_no: str
    cancelled_qty: int
    penalty: Decimal
    refund_amount: Decimal
    reason: str
    operator_id: str
    created_at: datetime


@dataclass(slots=True)
class ExceptionRecord:
    """Exception ledger entry for no-room, payment drop and refund failure."""

    exception_id: int
    order_no: str
    exception_type: ExceptionType
    description: str
    amount: Decimal
    status: ExceptionStatus
    created_by: str
    created_at: datetime
    resolved_at: datetime | None = None


@dataclass(slots=True)
class Room:
    """A physical room number, assigned only at check-in."""

    hotel_id: str
    room_no: str
    room_type_id: str
    status: RoomStatus
    floor: int

    @property
    def display(self) -> str:
        return f"{self.room_no}（{self.floor}层）"


@dataclass(slots=True)
class SpecialDate:
    """A date with a non-refundable special cancellation policy."""

    biz_date: date
    name: str
    note: str = ""


@dataclass(slots=True)
class NightlyPrice:
    """One night of a quotation."""

    biz_date: date
    unit_price: Decimal
    available: int
    is_special: bool = False


@dataclass(slots=True)
class Quote:
    """A complete price and availability quotation.

    Quoting has no side effects. A quote is recalculated and revalidated again
    inside the booking transaction, so a stale quote can never oversell.
    """

    hotel: Hotel
    room_type: RoomType
    check_in: date
    check_out: date
    qty: int
    nights: list[NightlyPrice]
    reason: str = ""

    @property
    def night_count(self) -> int:
        return len(self.nights)

    @property
    def min_available(self) -> int:
        return min((night.available for night in self.nights), default=0)

    @property
    def nightly_total(self) -> Decimal:
        return as_money(sum((night.unit_price for night in self.nights), ZERO))

    @property
    def total(self) -> Decimal:
        return as_money(self.nightly_total * self.qty)

    @property
    def first_night_price(self) -> Decimal:
        return self.nights[0].unit_price if self.nights else ZERO

    @property
    def is_available(self) -> bool:
        return not self.reason and self.min_available >= self.qty


@dataclass(slots=True)
class SearchResult:
    """A row on the guest search page."""

    hotel: Hotel
    room_type: RoomType
    quote: Quote

    @property
    def available(self) -> bool:
        return self.quote.is_available


@dataclass(slots=True)
class ReportRow:
    """One aggregated row of the operation report."""

    hotel_id: str
    hotel_name: str
    city: str
    franchise_type: str
    order_count: int
    room_nights: int
    revenue: Decimal
    cancellations: int
    occupancy: Decimal
    adr: Decimal
    cancel_rate: Decimal


@dataclass(slots=True)
class DashboardStats:
    """Numbers displayed on the staff workbench."""

    arrivals: int = 0
    departures: int = 0
    in_house: int = 0
    pending: int = 0
    available_today: int = 0
    revenue_today: Decimal = ZERO


def make_expiry(pay_mode: PayMode, now: datetime | None = None) -> datetime:
    """Return the lock expiry for a new order."""
    base = now or datetime.now()
    return base + timedelta(minutes=pay_mode.lock_minutes)


def decimal_or_zero(value: Any) -> Decimal:
    """Repository helper for nullable numeric text columns."""
    return as_money(value) if value not in (None, "") else ZERO
