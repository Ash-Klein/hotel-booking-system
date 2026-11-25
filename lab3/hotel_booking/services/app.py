"""Composition root for the desktop application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import config
from ..infrastructure.database import Database
from ..repositories.audit_repository import AuditRepository
from ..repositories.catalog_repository import CatalogRepository
from ..repositories.inventory_repository import InventoryRepository
from ..repositories.order_repository import OrderRepository
from ..repositories.reporting_repository import ReportingRepository
from ..repositories.staff_repository import StaffRepository
from .auth_service import AuthService
from .booking_service import BookingService
from .catalog_service import CatalogService
from .fulfillment_service import FulfillmentService
from .inventory_admin_service import InventoryAdminService
from .refund_service import RefundService
from .reporting_service import ReportingService


@dataclass(slots=True)
class Services:
    """All application services wired to one database."""

    db: Database
    auth: AuthService
    catalog: CatalogService
    booking: BookingService
    fulfillment: FulfillmentService
    inventory: InventoryAdminService
    refunds: RefundService
    reporting: ReportingService
    staff_repo: StaffRepository
    catalog_repo: CatalogRepository
    inventory_repo: InventoryRepository
    order_repo: OrderRepository
    audit_repo: AuditRepository


def create_services(
    db_path: str | Path | None = None,
    *,
    demo: bool = True,
) -> Services:
    """Build the object graph and optionally seed a demo dataset."""
    config.ensure_runtime_dirs()
    db = Database(db_path or config.database_path())
    db.initialize()
    catalog_repo = CatalogRepository(db)
    inventory_repo = InventoryRepository(db)
    order_repo = OrderRepository(db)
    audit_repo = AuditRepository(db)
    staff_repo = StaffRepository(db)
    report_repo = ReportingRepository(db)

    catalog = CatalogService(db, catalog_repo, inventory_repo)
    booking = BookingService(
        db,
        catalog,
        catalog_repo,
        inventory_repo,
        order_repo,
        audit_repo,
    )
    fulfillment = FulfillmentService(
        db,
        booking,
        catalog_repo,
        inventory_repo,
        order_repo,
        audit_repo,
    )
    services = Services(
        db=db,
        auth=AuthService(db, staff_repo, audit_repo),
        catalog=catalog,
        booking=booking,
        fulfillment=fulfillment,
        inventory=InventoryAdminService(
            db, catalog_repo, inventory_repo, audit_repo
        ),
        refunds=RefundService(db, order_repo, audit_repo),
        reporting=ReportingService(
            db,
            catalog_repo,
            inventory_repo,
            order_repo,
            report_repo,
            audit_repo,
        ),
        staff_repo=staff_repo,
        catalog_repo=catalog_repo,
        inventory_repo=inventory_repo,
        order_repo=order_repo,
        audit_repo=audit_repo,
    )
    if demo and db.table_count("orders") == 0:
        from .demo_data import seed_demo_orders

        seed_demo_orders(services)
    return services
