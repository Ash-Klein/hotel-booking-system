"""Demo transactions so the GUI opens with a realistic, non-empty dataset."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from ..domain.enums import ExceptionType, PayMode
from .app import Services


def seed_demo_orders(services: Services) -> None:
    """Create a handful of orders covering every major status.

    The demo is deliberately small: one arrival, one in-house guest, one
    pay-at-hotel order waiting for the front desk, one cancelled family-suite
    order with a pending refund, one exception order, and one checked-out
    order. It makes every screen and report meaningful on first launch.
    """
    today = date.today()
    frontdesk = services.staff_repo.find_by_username("frontdesk")
    manager = services.staff_repo.find_by_username("manager")
    admin = services.staff_repo.find_by_username("admin")
    if not frontdesk or not manager or not admin:
        return

    arrival = services.booking.create_order(
        guest_name="张伟",
        phone="13800000001",
        hotel_id="H001",
        room_type_id="RT001",
        check_in=today,
        check_out=today + timedelta(days=1),
        qty=1,
        pay_mode=PayMode.ONLINE,
    )
    services.booking.pay_order(arrival.order_no)

    in_house = services.booking.create_order(
        guest_name="李娜",
        phone="13900000002",
        hotel_id="H001",
        room_type_id="RT002",
        check_in=today,
        check_out=today + timedelta(days=2),
        qty=1,
        pay_mode=PayMode.ONLINE,
    )
    services.booking.pay_order(in_house.order_no)
    services.fulfillment.check_in(
        in_house.order_no, ["201"], frontdesk
    )

    pay_at_hotel = services.booking.create_order(
        guest_name="王强",
        phone="13700000003",
        hotel_id="H002",
        room_type_id="RT004",
        check_in=today + timedelta(days=1),
        check_out=today + timedelta(days=3),
        qty=1,
        pay_mode=PayMode.AT_HOTEL,
    )
    _ = pay_at_hotel

    family = services.booking.create_order(
        guest_name="陈静",
        phone="13600000004",
        hotel_id="H001",
        room_type_id="RT003",
        check_in=today + timedelta(days=3),
        check_out=today + timedelta(days=5),
        qty=1,
        pay_mode=PayMode.ONLINE,
    )
    services.booking.pay_order(family.order_no)
    services.booking.cancel_order(
        family.order_no,
        reason="行程变化，取消预订",
        staff=manager,
        guest_phone="13600000004",
    )

    exception_order = services.booking.create_order(
        guest_name="刘洋",
        phone="13500000005",
        hotel_id="H004",
        room_type_id="RT010",
        check_in=today + timedelta(days=4),
        check_out=today + timedelta(days=6),
        qty=1,
        pay_mode=PayMode.ONLINE,
    )
    services.booking.pay_order(exception_order.order_no)
    services.fulfillment.mark_exception(
        exception_order.order_no,
        admin,
        exception_type=ExceptionType.NO_ROOM,
        description="客人到店后原房型管道维修，已协调同城门店安置",
        compensation="300.00",
    )

    checked_out = services.booking.create_order(
        guest_name="周敏",
        phone="13400000006",
        hotel_id="H001",
        room_type_id="RT001",
        check_in=today,
        check_out=today + timedelta(days=2),
        qty=1,
        pay_mode=PayMode.ONLINE,
    )
    services.booking.pay_order(checked_out.order_no)
    services.fulfillment.check_in(
        checked_out.order_no, ["101"], frontdesk
    )
    services.fulfillment.check_out(
        checked_out.order_no,
        frontdesk,
        inspected=True,
        actual_check_out=today,
    )

    release_at = datetime.combine(
        today + timedelta(days=6), time(hour=18)
    )
    services.inventory.create_group_lock(
        manager,
        "H001",
        "RT003",
        today + timedelta(days=5),
        today + timedelta(days=7),
        2,
        release_at,
        note="上海国际展会协议客户预留",
    )
