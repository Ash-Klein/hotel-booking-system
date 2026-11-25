"""Dashboard, reports and CSV export use cases."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import csv
from pathlib import Path
from typing import Any

from ..domain.enums import OrderStatus
from ..domain.models import DashboardStats, ReportRow, Staff
from ..domain.money import as_money
from ..infrastructure.database import Database
from ..repositories.audit_repository import AuditRepository
from ..repositories.catalog_repository import CatalogRepository
from ..repositories.inventory_repository import InventoryRepository
from ..repositories.order_repository import OrderRepository
from ..repositories.reporting_repository import ReportingRepository
from ..services.permissions import require_staff


class ReportingService:
    """Build read models for the workbench and the group report."""

    def __init__(
        self,
        db: Database,
        catalog_repo: CatalogRepository,
        inventory_repo: InventoryRepository,
        order_repo: OrderRepository,
        report_repo: ReportingRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self.db = db
        self.catalog_repo = catalog_repo
        self.inventory_repo = inventory_repo
        self.orders = order_repo
        self.reports = report_repo
        self.audit = audit_repo

    def dashboard(
        self, staff: Staff, hotel_id: str, biz_date: date | None = None
    ) -> DashboardStats:
        """Numbers shown at the top of the staff workbench."""
        current = require_staff(staff)
        today = biz_date or date.today()
        scope = hotel_id if hotel_id else None
        if scope and not current.can_access_hotel(scope):
            scope = current.hotel_ids[0] if current.hotel_ids else None
        stats = self.orders.stats(scope, today)
        if scope:
            available = self.inventory_repo.available_sum(scope, today)
        else:
            available = int(
                self.db.scalar(
                    """
                    SELECT COALESCE(SUM(total - sold - locked - group_locked), 0)
                      FROM daily_inventory WHERE biz_date = ?
                    """,
                    (today.isoformat(),),
                    default=0,
                )
            )
        revenue = self.reports.payment_total_between(today, today, scope)
        return DashboardStats(
            arrivals=stats["arrivals"],
            departures=stats["departures"],
            in_house=stats["in_house"],
            pending=stats["pending"],
            available_today=available,
            revenue_today=revenue,
        )

    def hotel_report(self, start: date, end: date, staff: Staff) -> list[ReportRow]:
        """Group report filtered to hotels visible to the current role."""
        rows = self.reports.hotel_summary(start, end)
        if staff.role.is_group_level and not staff.hotel_ids:
            return rows
        allowed = set(staff.hotel_ids)
        return [row for row in rows if row.hotel_id in allowed]

    def trend(
        self, staff: Staff, hotel_id: str = "", days: int = 7
    ) -> list[dict[str, Any]]:
        """Daily order and revenue series for the dashboard."""
        start = date.today() - timedelta(days=days - 1)
        end = date.today() + timedelta(days=1)
        scope = hotel_id or None
        if scope and not staff.can_access_hotel(scope):
            scope = None
        return self.reports.daily_series(start, end, scope)

    def room_type_sales(
        self, staff: Staff, start: date, end: date, hotel_id: str = ""
    ) -> list[dict[str, Any]]:
        """Room type sales ranking."""
        scope = hotel_id or None
        if scope and not staff.can_access_hotel(scope):
            scope = None
        return self.reports.room_type_sales(start, end, scope)

    def exception_rows(self, staff: Staff) -> list[dict[str, Any]]:
        """Exception ledger joined with order and hotel information."""
        rows: list[dict[str, Any]] = []
        for record in self.orders.list_exceptions():
            order = self.orders.get(record.order_no)
            if not order:
                continue
            if not staff.can_access_hotel(order.hotel_id):
                continue
            rows.append(
                {
                    "exception_id": record.exception_id,
                    "order_no": record.order_no,
                    "hotel": order.hotel_name,
                    "type": record.exception_type.label,
                    "description": record.description,
                    "amount": str(record.amount),
                    "status": record.status.label,
                    "created_at": record.created_at.strftime("%Y-%m-%d %H:%M"),
                }
            )
        return rows

    def recent_orders(
        self, staff: Staff, limit: int = 30
    ) -> list[dict[str, Any]]:
        """Recent orders visible to the current staff member."""
        hotel_id = None
        if not staff.role.is_group_level:
            hotel_id = staff.hotel_ids[0] if staff.hotel_ids else "__none__"
        orders = self.orders.search(hotel_id=hotel_id, limit=limit)
        return [self.order_dict(order) for order in orders]

    @staticmethod
    def order_dict(order) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        """Flat representation used by Treeview tables."""
        return {
            "order_no": order.order_no,
            "hotel": order.hotel_name,
            "room_type": order.room_type_name,
            "guest": order.contact_name,
            "phone": order.contact_phone,
            "check_in": order.check_in.isoformat(),
            "check_out": order.check_out.isoformat(),
            "nights": order.nights,
            "qty": order.qty,
            "amount": str(order.total_amount),
            "status": order.status.label,
            "pay_mode": order.pay_mode.label,
            "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
        }

    def export_hotel_report(
        self, staff: Staff, start: date, end: date, path: str | Path
    ) -> Path:
        """Export the current role's hotel summary as UTF-8 BOM CSV."""
        output = Path(path)
        rows = self.hotel_report(start, end, staff)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "门店编号",
                    "门店",
                    "城市",
                    "类型",
                    "订单量",
                    "间夜数",
                    "营收",
                    "取消单数",
                    "出租率%",
                    "ADR",
                    "取消率%",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row.hotel_id,
                        row.hotel_name,
                        row.city,
                        "直营" if row.franchise_type == "DIRECT" else "加盟",
                        row.order_count,
                        row.room_nights,
                        row.revenue,
                        row.cancellations,
                        row.occupancy,
                        row.adr,
                        row.cancel_rate,
                    ]
                )
        return output

    def export_orders(
        self, staff: Staff, orders: list, path: str | Path
    ) -> Path:
        """Export the currently filtered order list."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            ("order_no", "订单号"),
            ("hotel_name", "门店"),
            ("room_type_name", "房型"),
            ("contact_name", "入住人"),
            ("contact_phone", "手机号"),
            ("check_in", "入住日期"),
            ("check_out", "离店日期"),
            ("status", "状态"),
            ("total_amount", "金额"),
        ]
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow([label for _, label in fields])
            for order in orders:
                writer.writerow(
                    [
                        getattr(order, key)
                        if key != "status"
                        else order.status.label
                        for key, _ in fields
                    ]
                )
        return output

    def total_revenue(self, staff: Staff, start: date, end: date) -> Decimal:
        """Sum revenue of report rows for the footer line."""
        return as_money(
            sum(
                (row.revenue for row in self.hotel_report(start, end, staff)),
                Decimal("0.00"),
            )
        )

    def pending_count(self, staff: Staff) -> int:
        """Pending refund count in scope, used for the sidebar badge."""
        hotel_id = None
        if not staff.role.is_group_level:
            hotel_id = staff.hotel_ids[0] if staff.hotel_ids else "__none__"
        return self.orders.pending_refund_count(hotel_id)

    def status_counts(self, staff: Staff) -> dict[str, int]:
        """Order counts by status for the admin dashboard cards."""
        hotel_id = None
        if not staff.role.is_group_level:
            hotel_id = staff.hotel_ids[0] if staff.hotel_ids else "__none__"
        rows = self.orders.search(hotel_id=hotel_id, limit=5000)
        counts = {status.label: 0 for status in OrderStatus}
        for order in rows:
            counts[order.status.label] += 1
        return counts
