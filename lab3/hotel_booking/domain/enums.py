"""Enumerations shared by the domain, persistence and presentation layers."""

from __future__ import annotations

from enum import Enum


class StringEnum(str, Enum):
    """Enum whose value is stored directly in SQLite text columns."""

    def __str__(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        """Human readable label supplied by ``__labels__``."""
        return self.__labels__.get(self, self.value)  # type: ignore[attr-defined]


class Role(StringEnum):
    """Staff roles defined by the requirement specification."""

    FRONT_DESK = "FRONT_DESK"
    MANAGER = "MANAGER"
    FINANCE = "FINANCE"
    ADMIN = "ADMIN"
    CITY_MANAGER = "CITY_MANAGER"

    __labels__ = {
        "FRONT_DESK": "门店前台",
        "MANAGER": "门店店长",
        "FINANCE": "集团财务",
        "ADMIN": "集团运营管理员",
        "CITY_MANAGER": "城市经理（只读）",
    }

    @property
    def is_group_level(self) -> bool:
        """Whether the role works for the group rather than one hotel."""
        return self in {Role.FINANCE, Role.ADMIN, Role.CITY_MANAGER}

    @property
    def can_manage_inventory(self) -> bool:
        """Only a hotel manager may change price, closure and stock."""
        return self in {Role.MANAGER, Role.ADMIN}

    @property
    def can_approve_refund(self) -> bool:
        """Refund approval belongs to hotel managers and group finance."""
        return self in {Role.MANAGER, Role.FINANCE, Role.ADMIN}

    @property
    def can_resolve_exception(self) -> bool:
        """Group operations resolves exception orders."""
        return self in {Role.ADMIN, Role.FINANCE}

    @property
    def read_only(self) -> bool:
        """City managers can inspect reports but cannot mutate data."""
        return self is Role.CITY_MANAGER


class HotelStatus(StringEnum):
    """Hotel operation status."""

    OPEN = "OPEN"
    SUSPENDED = "SUSPENDED"

    __labels__ = {"OPEN": "营业中", "SUSPENDED": "临时停业"}


class RoomTypeStatus(StringEnum):
    """Room type sale status."""

    ON_SALE = "ON_SALE"
    OFF_SALE = "OFF_SALE"

    __labels__ = {"ON_SALE": "在售", "OFF_SALE": "停售"}


class OrderStatus(StringEnum):
    """Seven order states from REQ-016 plus the exception sub-flow."""

    PENDING_PAYMENT = "PENDING_PAYMENT"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    EXCEPTION = "EXCEPTION"

    __labels__ = {
        "PENDING_PAYMENT": "待支付",
        "CONFIRMED": "已确认待入住",
        "CHECKED_IN": "已入住",
        "CHECKED_OUT": "正常离店",
        "CANCELLED": "已取消",
        "NO_SHOW": "客人未到店",
        "EXCEPTION": "异常订单",
    }

    @property
    def is_terminal(self) -> bool:
        """Terminal states cannot be recovered in phase one."""
        return self in {
            OrderStatus.CHECKED_OUT,
            OrderStatus.CANCELLED,
            OrderStatus.NO_SHOW,
        }

    @property
    def consumes_inventory(self) -> bool:
        """Whether the order still owns sold (not merely locked) rooms."""
        return self in {
            OrderStatus.CONFIRMED,
            OrderStatus.CHECKED_IN,
            OrderStatus.EXCEPTION,
        }


# The only legal transitions. Anything not present here is rejected and
# audited, as required by REQ-017.
ORDER_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING_PAYMENT: frozenset(
        {OrderStatus.CONFIRMED, OrderStatus.CANCELLED}
    ),
    OrderStatus.CONFIRMED: frozenset(
        {
            OrderStatus.CHECKED_IN,
            OrderStatus.CANCELLED,
            OrderStatus.NO_SHOW,
            OrderStatus.EXCEPTION,
        }
    ),
    OrderStatus.CHECKED_IN: frozenset(
        {OrderStatus.CHECKED_OUT, OrderStatus.EXCEPTION}
    ),
    OrderStatus.EXCEPTION: frozenset(
        {OrderStatus.CANCELLED, OrderStatus.CHECKED_OUT}
    ),
    OrderStatus.CHECKED_OUT: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
    OrderStatus.NO_SHOW: frozenset(),
}


class PayMode(StringEnum):
    """Online prepay or pay at the front desk."""

    ONLINE = "ONLINE"
    AT_HOTEL = "AT_HOTEL"

    __labels__ = {"ONLINE": "线上预付", "AT_HOTEL": "到店现付"}

    @property
    def lock_minutes(self) -> int:
        """15 minutes for prepay, 30 minutes for pay-at-hotel."""
        return 15 if self is PayMode.ONLINE else 30


class PaymentStatus(StringEnum):
    """Payment record status."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

    __labels__ = {
        "PENDING": "待支付",
        "SUCCESS": "支付成功",
        "FAILED": "支付失败",
        "REFUNDED": "已退款",
    }


class RefundStatus(StringEnum):
    """Refund record workflow status."""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    AUTO_APPROVED = "AUTO_APPROVED"
    SUCCESS = "SUCCESS"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

    __labels__ = {
        "PENDING_APPROVAL": "待店长审核",
        "AUTO_APPROVED": "自动审核通过",
        "SUCCESS": "退款成功",
        "REJECTED": "已驳回",
        "FAILED": "退款失败",
    }


class GroupLockStatus(StringEnum):
    """Protocol room lock lifecycle."""

    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    CONVERTED = "CONVERTED"

    __labels__ = {
        "ACTIVE": "生效中",
        "RELEASED": "已释放",
        "CONVERTED": "已转订单",
    }


class ExceptionType(StringEnum):
    """Exception ledger categories."""

    NO_ROOM = "NO_ROOM"
    PAYMENT_DROP = "PAYMENT_DROP"
    REFUND_FAIL = "REFUND_FAIL"
    HOTEL_CLOSED = "HOTEL_CLOSED"
    OTHER = "OTHER"

    __labels__ = {
        "NO_ROOM": "到店无房",
        "PAYMENT_DROP": "支付掉单",
        "REFUND_FAIL": "退款失败",
        "HOTEL_CLOSED": "门店停业",
        "OTHER": "其他异常",
    }


class ExceptionStatus(StringEnum):
    """Exception handling status."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"

    __labels__ = {"OPEN": "待处理", "RESOLVED": "已处理", "REJECTED": "已驳回"}


class RoomStatus(StringEnum):
    """Physical room status used during check-in."""

    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"

    __labels__ = {"AVAILABLE": "可用", "OCCUPIED": "已入住", "MAINTENANCE": "维修"}


class Terminal(StringEnum):
    """Entry point recorded in operation logs."""

    DESKTOP = "DESKTOP"
    GUEST = "GUEST"
    SYSTEM = "SYSTEM"

    __labels__ = {"DESKTOP": "桌面端", "GUEST": "客人端", "SYSTEM": "系统任务"}
