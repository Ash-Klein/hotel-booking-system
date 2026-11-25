"""Authorization helpers shared by application services."""

from __future__ import annotations

from ..domain.errors import PermissionDenied
from ..domain.models import Staff


def require_staff(staff: Staff | None) -> Staff:
    """Ensure an authenticated staff member is present."""
    if staff is None:
        raise PermissionDenied("请先登录员工账号")
    if not staff.active:
        raise PermissionDenied("该账号已被停用")
    return staff


def require_hotel_access(staff: Staff | None, hotel_id: str) -> Staff:
    """Ensure the staff member can operate on the hotel."""
    current = require_staff(staff)
    if not current.can_access_hotel(hotel_id):
        raise PermissionDenied("无权操作该门店的数据")
    if current.role.read_only:
        raise PermissionDenied("城市经理账号为只读角色")
    return current


def require_group_role(staff: Staff | None) -> Staff:
    """Ensure the staff member belongs to the group level."""
    current = require_staff(staff)
    if not current.role.is_group_level:
        raise PermissionDenied("该操作仅限集团角色")
    return current


def require_writable(staff: Staff | None) -> Staff:
    """Block the read-only city-manager role from mutations."""
    current = require_staff(staff)
    if current.role.read_only:
        raise PermissionDenied("城市经理账号为只读角色")
    return current
