"""Authentication service."""

from __future__ import annotations

from ..domain.enums import Terminal
from ..domain.errors import PermissionDenied, ValidationError
from ..domain.models import Staff
from ..infrastructure.database import Database
from ..infrastructure.security import verify_password
from ..repositories.audit_repository import AuditRepository
from ..repositories.staff_repository import StaffRepository


class AuthService:
    """Verify staff credentials and record the login event."""

    def __init__(
        self,
        db: Database,
        staff_repo: StaffRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self.db = db
        self.staff_repo = staff_repo
        self.audit_repo = audit_repo

    def login(self, username: str, password: str) -> Staff:
        """Authenticate a staff account.

        A failed login is deliberately not logged: the account is unknown at
        that point, and logging every typo would create a denial-of-service
        vector against the audit table.
        """
        username = username.strip()
        if not username or not password:
            raise ValidationError("请输入账号和密码")
        staff = self.staff_repo.find_by_username(username)
        if not staff or not verify_password(
            password, staff.password_hash, staff.salt
        ):
            raise PermissionDenied("账号或密码错误")
        if not staff.active:
            raise PermissionDenied("该账号已被停用")
        with self.db.transaction() as connection:
            self.audit_repo.write(
                connection,
                staff,
                "LOGIN",
                hotel_id=staff.hotel_ids[0] if staff.hotel_ids else "",
                terminal=Terminal.DESKTOP,
                after_data=f"角色={staff.role.label}",
            )
        return staff
