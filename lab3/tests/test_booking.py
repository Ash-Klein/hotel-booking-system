"""Core business-rule tests for the hotel booking system.

Run with:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
import threading
import unittest
import uuid

from hotel_booking.domain.enums import (
    ExceptionType,
    HotelStatus,
    OrderStatus,
    PayMode,
    PaymentStatus,
    RefundStatus,
    RoomStatus,
    RoomTypeStatus,
)
from hotel_booking.domain.errors import (
    ConflictError,
    DomainError,
    PermissionDenied,
    StateTransitionError,
    ValidationError,
)
from hotel_booking.domain.money import as_money, mask_phone
from hotel_booking.services.app import Services, create_services


class ServiceTestCase(unittest.TestCase):
    """Build a fresh, demo-free database for every test."""

    def setUp(self) -> None:
        base = Path(__file__).resolve().parent.parent / "data"
        base.mkdir(exist_ok=True)
        self.db_path = base / f"test_{uuid.uuid4().hex}.db"
        self.services: Services = create_services(self.db_path, demo=False)
        self.guest_phone = "13800000099"
        self.frontdesk = self.services.staff_repo.find_by_username("frontdesk")
        self.manager = self.services.staff_repo.find_by_username("manager")
        self.admin = self.services.staff_repo.find_by_username("admin")
        assert self.frontdesk and self.manager and self.admin

    def tearDown(self) -> None:
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(self.db_path) + suffix)
            if path.exists():
                path.unlink()

    def new_order(
        self,
        *,
        hotel_id: str = "H001",
        room_type_id: str = "RT001",
        offset: int = 10,
        nights: int = 2,
        qty: int = 1,
        pay_mode: PayMode = PayMode.ONLINE,
        pay: bool = False,
        phone: str | None = None,
    ):  # type: ignore[no-untyped-def]
        check_in = date.today() + timedelta(days=offset)
        order = self.services.booking.create_order(
            guest_name="测试客人",
            phone=phone or self.guest_phone,
            hotel_id=hotel_id,
            room_type_id=room_type_id,
            check_in=check_in,
            check_out=check_in + timedelta(days=nights),
            qty=qty,
            pay_mode=pay_mode,
        )
        if pay:
            order = self.services.booking.pay_order(order.order_no)
        return order

    def inventory(self, order, offset: int = 0):  # type: ignore[no-untyped-def]
        return self.services.inventory_repo.get(
            None,
            order.hotel_id,
            order.room_type_id,
            order.check_in + timedelta(days=offset),
        )


class InventoryTests(ServiceTestCase):
    """REQ-009: natural-day stock accounting and atomic multi-night lock."""

    def test_multi_night_lock_and_release(self) -> None:
        order = self.new_order(offset=10, nights=3, qty=1)
        first = self.inventory(order, 0)
        second = self.inventory(order, 1)
        third = self.inventory(order, 2)
        fourth = self.inventory(order, 3)
        self.assertEqual(first.locked, 1)
        self.assertEqual(second.locked, 1)
        self.assertEqual(third.locked, 1)
        self.assertEqual(fourth.locked, 0)
        result = self.services.booking.cancel_order(
            order.order_no,
            reason="测试取消",
            guest_phone=self.guest_phone,
        )
        self.assertEqual(result["order"].status, OrderStatus.CANCELLED)
        for offset in range(3):
            self.assertEqual(self.inventory(order, offset).locked, 0)

    def test_pay_moves_locked_to_sold(self) -> None:
        order = self.new_order(offset=10, nights=2, pay=True)
        for offset in range(2):
            inventory = self.inventory(order, offset)
            self.assertEqual(inventory.locked, 0)
            self.assertEqual(inventory.sold, 1)
            self.assertGreaterEqual(inventory.available, 0)
        self.assertEqual(order.status, OrderStatus.CONFIRMED)

    def test_multi_room_order_multiplies_stock(self) -> None:
        order = self.new_order(offset=11, nights=2, qty=3, pay=True)
        self.assertEqual(order.total_amount, as_money(order.item.unit_price * 3))
        for offset in range(2):
            self.assertEqual(self.inventory(order, offset).sold, 3)

    def test_last_room_concurrency(self) -> None:
        target = date.today() + timedelta(days=8)
        room_type = self.services.catalog.room_type("RT001")
        with self.services.db.transaction() as connection:
            self.services.inventory_repo.set_total(
                connection,
                room_type.hotel_id,
                room_type.room_type_id,
                target,
                1,
            )
        barrier = threading.Barrier(2)
        outcomes: list[str] = []
        lock = threading.Lock()

        def worker(phone: str) -> None:
            barrier.wait()
            try:
                self.services.booking.create_order(
                    guest_name=f"并发{phone[-2:]}",
                    phone=phone,
                    hotel_id=room_type.hotel_id,
                    room_type_id=room_type.room_type_id,
                    check_in=target,
                    check_out=target + timedelta(days=1),
                    qty=1,
                    pay_mode=PayMode.ONLINE,
                )
                result = "success"
            except DomainError:
                result = "rejected"
            with lock:
                outcomes.append(result)

        threads = [
            threading.Thread(target=worker, args=("13800000101",)),
            threading.Thread(target=worker, args=("13800000102",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertEqual(outcomes.count("success"), 1)
        self.assertEqual(outcomes.count("rejected"), 1)
        inventory = self.services.inventory_repo.get(
            None, room_type.hotel_id, room_type.room_type_id, target
        )
        self.assertEqual(inventory.locked, 1)
        self.assertEqual(inventory.available, 0)


class OrderStateTests(ServiceTestCase):
    """REQ-016 / REQ-017 / REQ-018 order state machine."""

    def test_at_hotel_confirmation(self) -> None:
        order = self.new_order(
            offset=6, pay_mode=PayMode.AT_HOTEL, pay=False
        )
        self.assertEqual(order.status, OrderStatus.PENDING_PAYMENT)
        with self.assertRaises(ConflictError):
            self.services.booking.pay_order(order.order_no)
        confirmed = self.services.booking.confirm_at_hotel(
            order.order_no, self.frontdesk
        )
        self.assertEqual(confirmed.status, OrderStatus.CONFIRMED)
        payments = self.services.order_repo.list_payments(order.order_no)
        self.assertEqual(payments[-1].status, PaymentStatus.PENDING)

    def test_pending_cannot_check_in(self) -> None:
        order = self.new_order(offset=3)
        rooms = self.services.catalog_repo.list_rooms(
            order.hotel_id, order.room_type_id
        )
        with self.assertRaises(ConflictError):
            self.services.fulfillment.check_in(
                order.order_no, [rooms[0].room_no], self.frontdesk
            )

    def test_forbidden_transition_is_rejected(self) -> None:
        order = self.new_order(offset=4)
        with self.assertRaises(StateTransitionError):
            order.transition_to(OrderStatus.CHECKED_OUT)

    def test_full_lifecycle_check_in_check_out(self) -> None:
        order = self.new_order(offset=0, nights=1, pay=True)
        room = self.services.catalog_repo.list_rooms(
            order.hotel_id, order.room_type_id
        )[0]
        checked_in = self.services.fulfillment.check_in(
            order.order_no, [room.room_no], self.frontdesk
        )
        self.assertEqual(checked_in.status, OrderStatus.CHECKED_IN)
        checked_out = self.services.fulfillment.check_out(
            order.order_no, self.frontdesk
        )
        self.assertEqual(
            checked_out["order"].status, OrderStatus.CHECKED_OUT
        )
        refreshed = self.services.catalog_repo.list_rooms(
            order.hotel_id, order.room_type_id
        )
        assigned = [item for item in refreshed if item.room_no == room.room_no]
        self.assertEqual(assigned[0].status, RoomStatus.AVAILABLE)

    def test_no_show_releases_stock(self) -> None:
        order = self.new_order(offset=0, nights=1, pay=True)
        self.services.fulfillment.mark_no_show(
            order.order_no, self.frontdesk
        )
        refreshed = self.services.order_repo.get(order.order_no)
        self.assertEqual(refreshed.status, OrderStatus.NO_SHOW)
        self.assertEqual(self.inventory(order, 0).sold, 0)

    def test_expired_payment_cancels_atomically(self) -> None:
        order = self.new_order(offset=5, nights=1)
        future = datetime.now() + timedelta(minutes=16)
        with self.assertRaises(ConflictError):
            self.services.booking.pay_order(order.order_no, now=future)
        refreshed = self.services.order_repo.get(order.order_no)
        self.assertEqual(refreshed.status, OrderStatus.CANCELLED)
        self.assertEqual(self.inventory(order, 0).locked, 0)


class CancellationTests(ServiceTestCase):
    """REQ-021 / REQ-022 / REQ-023 cancellation and refund rules."""

    def test_free_cancel_more_than_24_hours(self) -> None:
        order = self.new_order(offset=5, nights=2, pay=True)
        paid = order.total_amount
        result = self.services.booking.cancel_order(
            order.order_no,
            reason="提前取消",
            guest_phone=self.guest_phone,
        )
        self.assertEqual(result["penalty"], Decimal("0.00"))
        self.assertEqual(result["refund_amount"], paid)
        self.assertIsNotNone(result["refund"])
        self.assertIn(
            result["refund"].status,
            {RefundStatus.AUTO_APPROVED, RefundStatus.PENDING_APPROVAL},
        )
        for offset in range(2):
            self.assertEqual(self.inventory(order, offset).sold, 0)

    def test_late_cancel_charges_first_night(self) -> None:
        order = self.new_order(offset=0, nights=2, pay=True)
        first_night = order.item.first_night_price
        result = self.services.booking.cancel_order(
            order.order_no,
            reason="临时取消",
            guest_phone=self.guest_phone,
        )
        self.assertEqual(result["penalty"], first_night)
        self.assertEqual(
            result["refund_amount"],
            as_money(order.total_amount - first_night),
        )

    def test_special_date_always_charges_first_night(self) -> None:
        special = self.services.catalog.special_dates()[0].biz_date
        offset = (special - date.today()).days
        order = self.new_order(offset=offset, nights=1, pay=True)
        result = self.services.booking.cancel_order(
            order.order_no,
            reason="展会行程变更",
            guest_phone=self.guest_phone,
        )
        self.assertEqual(result["penalty"], order.item.first_night_price)

    def test_refund_over_500_needs_approval(self) -> None:
        order = self.new_order(
            hotel_id="H001", room_type_id="RT003", offset=8, nights=2, pay=True
        )
        self.assertGreater(order.first_night_amount, Decimal("500.00"))
        result = self.services.booking.cancel_order(
            order.order_no,
            reason="大额退款",
            guest_phone=self.guest_phone,
        )
        self.assertIsNotNone(result["refund"])
        self.assertEqual(
            result["refund"].status, RefundStatus.PENDING_APPROVAL
        )
        pending = self.services.refunds.pending_refunds(self.manager)
        self.assertTrue(any(item.refund_no == result["refund"].refund_no for item in pending))
        decided = self.services.refunds.decide(
            result["refund"].refund_no, self.manager, approve=True
        )
        self.assertEqual(decided.status, RefundStatus.SUCCESS)

    def test_refund_under_500_auto_approves(self) -> None:
        order = self.new_order(
            hotel_id="H006",
            room_type_id="RT016",
            offset=13,
            nights=1,
            pay=True,
        )
        self.assertLessEqual(order.first_night_amount, Decimal("500.00"))
        result = self.services.booking.cancel_order(
            order.order_no,
            reason="小额退款",
            guest_phone=self.guest_phone,
        )
        self.assertEqual(
            result["refund"].status, RefundStatus.AUTO_APPROVED
        )

    def test_frontdesk_cannot_approve_refund(self) -> None:
        order = self.new_order(
            hotel_id="H001", room_type_id="RT003", offset=8, nights=1, pay=True
        )
        result = self.services.booking.cancel_order(
            order.order_no,
            reason="权限测试",
            guest_phone=self.guest_phone,
        )
        with self.assertRaises(PermissionDenied):
            self.services.refunds.decide(
                result["refund"].refund_no, self.frontdesk, approve=True
            )

    def test_partial_cancel_keeps_remaining_room(self) -> None:
        order = self.new_order(offset=12, nights=1, qty=2, pay=True)
        result = self.services.booking.cancel_order(
            order.order_no,
            reason="取消一间",
            qty=1,
            guest_phone=self.guest_phone,
        )
        refreshed = result["order"]
        self.assertEqual(refreshed.status, OrderStatus.CONFIRMED)
        self.assertEqual(refreshed.item.cancelled_qty, 1)
        self.assertEqual(refreshed.item.active_qty, 1)
        self.assertEqual(self.inventory(order, 0).sold, 1)


class ModificationTests(ServiceTestCase):
    """REQ-020: atomic change of dates and stock."""

    def test_modify_dates_moves_inventory(self) -> None:
        order = self.new_order(offset=10, nights=2, pay=True)
        new_in = date.today() + timedelta(days=15)
        result = self.services.booking.modify_order(
            order.order_no,
            hotel_id="H001",
            room_type_id="RT001",
            check_in=new_in,
            check_out=new_in + timedelta(days=3),
            guest_phone=self.guest_phone,
        )
        updated = result["order"]
        self.assertEqual(updated.check_in, new_in)
        self.assertEqual(updated.nights, 3)
        self.assertEqual(self.inventory(order, 0).sold, 0)
        new_inventory = self.services.inventory_repo.get(
            None, "H001", "RT001", new_in
        )
        self.assertEqual(new_inventory.sold, 1)
        self.assertEqual(len(
            self.services.order_repo.list_changes(order.order_no)
        ), 1)

    def test_cross_city_modify_rejected(self) -> None:
        order = self.new_order(offset=10, nights=2, pay=True)
        with self.assertRaises(ValidationError):
            self.services.booking.modify_order(
                order.order_no,
                hotel_id="H004",
                room_type_id="RT010",
                check_in=date.today() + timedelta(days=12),
                check_out=date.today() + timedelta(days=14),
                guest_phone=self.guest_phone,
            )


class AdministrationTests(ServiceTestCase):
    """Price, closure, group lock, audit and reporting rules."""

    def test_frontdesk_cannot_change_price(self) -> None:
        with self.assertRaises(ValidationError):
            self.services.inventory.set_price(
                self.frontdesk,
                "H001",
                "RT001",
                date.today() + timedelta(days=3),
                Decimal("600.00"),
            )

    def test_manager_changes_price_and_audits(self) -> None:
        target = date.today() + timedelta(days=3)
        self.services.inventory.set_price(
            self.manager, "H001", "RT001", target, Decimal("620.00")
        )
        price = self.services.inventory_repo.get_price(
            None, "H001", "RT001", target
        )
        self.assertEqual(price.final_price, Decimal("620.00"))
        logs = self.services.audit_repo.list_logs(
            self.manager, action="UPDATE_PRICE"
        )
        self.assertTrue(logs)

    def test_group_lock_and_release(self) -> None:
        start = date.today() + timedelta(days=6)
        lock = self.services.inventory.create_group_lock(
            self.manager,
            "H001",
            "RT003",
            start,
            start + timedelta(days=2),
            2,
            datetime.combine(
                date.today() + timedelta(days=7), time(hour=18)
            ),
        )
        inventory = self.services.inventory_repo.get(
            None, "H001", "RT003", start
        )
        self.assertEqual(inventory.group_locked, 2)
        self.services.inventory.release_group_lock(
            self.manager, lock.lock_id
        )
        inventory = self.services.inventory_repo.get(
            None, "H001", "RT003", start
        )
        self.assertEqual(inventory.group_locked, 0)

    def test_group_lock_cannot_exceed_stock(self) -> None:
        start = date.today() + timedelta(days=6)
        with self.assertRaises(ConflictError):
            self.services.inventory.create_group_lock(
                self.manager,
                "H001",
                "RT003",
                start,
                start + timedelta(days=1),
                20,
                datetime.now() + timedelta(days=2),
            )

    def test_closure_blocks_new_booking_but_not_existing(self) -> None:
        order = self.new_order(offset=14, nights=1, pay=True)
        start = order.check_in
        self.services.inventory.close_rooms(
            self.manager,
            order.hotel_id,
            order.room_type_id,
            start,
            start + timedelta(days=1),
            "管道维修",
        )
        existing = self.services.order_repo.get(order.order_no)
        self.assertEqual(existing.status, OrderStatus.CONFIRMED)
        with self.assertRaises(ConflictError):
            self.services.booking.create_order(
                guest_name="新客人",
                phone="13800000200",
                hotel_id=order.hotel_id,
                room_type_id=order.room_type_id,
                check_in=start,
                check_out=start + timedelta(days=1),
                qty=1,
                pay_mode=PayMode.ONLINE,
            )

    def test_audit_scope_is_hotel_bound(self) -> None:
        self.new_order(hotel_id="H004", room_type_id="RT010", offset=9)
        self.new_order(hotel_id="H001", room_type_id="RT001", offset=9)
        manager_logs = self.services.audit_repo.list_logs(self.manager)
        self.assertTrue(manager_logs)
        self.assertFalse(any(log.hotel_id == "H004" for log in manager_logs))
        admin_logs = self.services.audit_repo.list_logs(self.admin)
        self.assertTrue(any(log.hotel_id == "H004" for log in admin_logs))

    def test_exception_flow(self) -> None:
        order = self.new_order(offset=9, nights=1, pay=True)
        self.services.fulfillment.mark_exception(
            order.order_no,
            self.frontdesk,
            exception_type=ExceptionType.NO_ROOM,
            description="到店无房，已协调同城门店",
            compensation=Decimal("200.00"),
        )
        exceptions = self.services.order_repo.list_exceptions()
        self.assertEqual(len(exceptions), 1)
        self.services.fulfillment.resolve_exception(
            exceptions[0].exception_id,
            self.admin,
            cancel_order=True,
            note="已与客人协商",
        )
        refreshed = self.services.order_repo.get(order.order_no)
        self.assertEqual(refreshed.status, OrderStatus.CANCELLED)

    def test_report_totals_are_consistent(self) -> None:
        self.new_order(offset=5, nights=2, pay=True)
        start = date.today()
        rows = self.services.reporting.hotel_report(
            start, start + timedelta(days=30), self.admin
        )
        first = next(row for row in rows if row.hotel_id == "H001")
        self.assertGreaterEqual(first.order_count, 1)
        self.assertGreater(first.revenue, Decimal("0"))


class GuestProfileTests(ServiceTestCase):
    """Catalogue display fields and the guest details shown on screens 02-05."""

    def test_catalog_exposes_star_rating_and_area(self) -> None:
        hotel = self.services.catalog.hotel("H001")
        self.assertEqual(hotel.star, 5)
        self.assertEqual(f"{float(hotel.rating):.1f}", "4.8")
        self.assertIn("黄浦区", hotel.full_address)
        room = self.services.catalog.room_type("RT001")
        self.assertEqual(room.area_sqm, 28)
        self.assertIn("28㎡", room.short_spec)

    def test_order_keeps_guests_and_arrival_time(self) -> None:
        check_in = date.today() + timedelta(days=8)
        order = self.services.booking.create_order(
            guest_name="黄若希",
            phone="13800000098",
            hotel_id="H001",
            room_type_id="RT001",
            check_in=check_in,
            check_out=check_in + timedelta(days=2),
            qty=2,
            pay_mode=PayMode.ONLINE,
            arrival_time="预计 20:00 前",
            guests=["李明", "李明", "王芳"],
        )
        stored = self.services.order_repo.require(order.order_no)
        self.assertEqual(stored.arrival_time, "预计 20:00 前")
        self.assertEqual(stored.guest_names, ["黄若希", "李明", "王芳"])
        self.assertEqual(stored.guests_label, "黄若希、李明、王芳")

    def test_short_guest_name_is_rejected(self) -> None:
        check_in = date.today() + timedelta(days=8)
        with self.assertRaises(ValidationError):
            self.services.booking.create_order(
                guest_name="黄若希",
                phone="13800000097",
                hotel_id="H001",
                room_type_id="RT001",
                check_in=check_in,
                check_out=check_in + timedelta(days=1),
                qty=2,
                pay_mode=PayMode.ONLINE,
                guests=["王"],
            )


class DomainModelTests(unittest.TestCase):
    """Pure domain helpers and enum labels."""

    def test_mask_phone(self) -> None:
        self.assertEqual(mask_phone("13812345678"), "138****5678")

    def test_inventory_invariant(self) -> None:
        from hotel_booking.domain.models import DailyInventory

        inventory = DailyInventory(
            hotel_id="H",
            room_type_id="R",
            biz_date=date.today(),
            total=3,
        )
        self.assertTrue(inventory.reserve(2))
        self.assertFalse(inventory.reserve(2))
        inventory.confirm(2)
        self.assertEqual(inventory.sold, 2)
        self.assertEqual(inventory.available, 1)
        inventory.release_sold(1)
        self.assertEqual(inventory.available, 2)


if __name__ == "__main__":
    unittest.main()
