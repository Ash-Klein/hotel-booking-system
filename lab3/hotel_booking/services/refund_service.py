"""Refund approval workflow (REQ-022 / REQ-023)."""

from __future__ import annotations

from datetime import datetime

from ..domain.enums import RefundStatus, Terminal
from ..domain.errors import ConflictError, NotFoundError, PermissionDenied
from ..domain.models import Refund, Staff
from ..infrastructure.database import Database
from ..repositories.audit_repository import AuditRepository
from ..repositories.order_repository import OrderRepository


class RefundService:
    """List and decide refunds that exceed the front-desk limit."""

    def __init__(
        self,
        db: Database,
        order_repo: OrderRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self.db = db
        self.orders = order_repo
        self.audit = audit_repo

    def pending_refunds(self, staff: Staff) -> list[Refund]:
        """Return pending refunds in the staff member's data scope."""
        refunds = self.orders.list_refunds(RefundStatus.PENDING_APPROVAL)
        result: list[Refund] = []
        for refund in refunds:
            order = self.orders.get(refund.order_no)
            if order and staff.can_access_hotel(order.hotel_id):
                result.append(refund)
        return result

    def decide(
        self,
        refund_no: str,
        staff: Staff,
        *,
        approve: bool,
        note: str = "",
        now: datetime | None = None,
    ) -> Refund:
        """Approve or reject a pending refund.

        Approval is separated from cancellation: the order is already
        cancelled, while money moves only after a manager decides.
        """
        moment = now or datetime.now()
        if not staff.role.can_approve_refund:
            raise PermissionDenied("当前角色无退款审批权限")
        with self.db.transaction() as connection:
            refund = self.orders.get_refund(refund_no)
            if not refund:
                raise NotFoundError("退款记录不存在")
            order = self.orders.require(refund.order_no, connection)
            if not staff.can_access_hotel(order.hotel_id):
                raise PermissionDenied("无权审批该门店的退款")
            if refund.status is not RefundStatus.PENDING_APPROVAL:
                raise ConflictError("该退款已处理，不能重复审批")
            if approve:
                refund.status = RefundStatus.SUCCESS
                refund.approver_id = staff.staff_id
                refund.approved_at = moment
                refund.submitted_at = moment
            else:
                refund.status = RefundStatus.REJECTED
                refund.approver_id = staff.staff_id
                refund.approved_at = moment
            self.orders.update_refund(connection, refund)
            self.audit.write(
                connection,
                staff,
                "APPROVE_REFUND" if approve else "REJECT_REFUND",
                hotel_id=order.hotel_id,
                terminal=Terminal.DESKTOP,
                before_data=f"待审核，金额 {refund.amount}",
                after_data=(
                    f"{refund.status.label}，审批人 {staff.name}，备注 {note}"
                ),
                order_no=order.order_no,
                guest_id=order.guest_id,
            )
        return refund

    def failed_refunds(self, staff: Staff) -> list[Refund]:
        """List channel failures for manual follow-up."""
        refunds = self.orders.list_refunds(RefundStatus.FAILED)
        result: list[Refund] = []
        for refund in refunds:
            order = self.orders.get(refund.order_no)
            if order and staff.can_access_hotel(order.hotel_id):
                result.append(refund)
        return result
