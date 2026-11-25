"""Inventory, price, closure and protocol-lock administration."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json

from ..domain.enums import (
    GroupLockStatus,
    HotelStatus,
    Role,
    RoomTypeStatus,
    Terminal,
)
from ..domain.errors import ConflictError, NotFoundError, ValidationError
from ..domain.models import GroupLock, RoomClosure, SpecialDate, Staff
from ..domain.money import as_money, money_text
from ..infrastructure.database import Database
from ..infrastructure.security import new_token
from ..repositories.audit_repository import AuditRepository
from ..repositories.catalog_repository import CatalogRepository
from ..repositories.inventory_repository import InventoryRepository
from ..services.permissions import require_hotel_access, require_staff


def _json(data: dict[str, object]) -> str:
    """Serialize before/after values for auditing."""
    return json.dumps(data, ensure_ascii=False, default=str)


class InventoryAdminService:
    """Manager-facing stock and price operations."""

    def __init__(
        self,
        db: Database,
        catalog_repo: CatalogRepository,
        inventory_repo: InventoryRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self.db = db
        self.catalog_repo = catalog_repo
        self.inventory_repo = inventory_repo
        self.audit = audit_repo

    # ------------------------------------------------------------------
    # Price and closure
    # ------------------------------------------------------------------
    def set_price(
        self,
        staff: Staff,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
        price: Decimal,
    ) -> None:
        """Set the final nightly price of one room type and date."""
        require_hotel_access(staff, hotel_id)
        if not staff.role.can_manage_inventory:
            raise ValidationError("仅门店店长或集团运营可修改价格")
        amount = as_money(price)
        if amount <= 0 or amount > Decimal("100000.00"):
            raise ValidationError("价格须在 0.01 至 100000 元之间")
        with self.db.transaction() as connection:
            old = self.inventory_repo.get_price(
                connection, hotel_id, room_type_id, biz_date
            )
            self.inventory_repo.set_price(
                connection,
                hotel_id,
                room_type_id,
                biz_date,
                money_text(amount),
            )
            self.audit.write(
                connection,
                staff,
                "UPDATE_PRICE",
                hotel_id=hotel_id,
                before_data=_json(
                    {
                        "date": biz_date.isoformat(),
                        "price": str(old.final_price) if old else "无",
                    }
                ),
                after_data=_json(
                    {"date": biz_date.isoformat(), "price": str(amount)}
                ),
            )

    def close_rooms(
        self,
        staff: Staff,
        hotel_id: str,
        room_type_id: str,
        start: date,
        end: date,
        reason: str,
    ) -> RoomClosure:
        """Close a room type for new bookings on ``[start, end)``."""
        require_hotel_access(staff, hotel_id)
        if not staff.role.can_manage_inventory:
            raise ValidationError("仅门店店长可执行关房")
        if end <= start:
            raise ValidationError("关房结束日期必须晚于开始日期")
        if start < date.today():
            raise ValidationError("不能关闭已过去的日期")
        if len(reason.strip()) < 2:
            raise ValidationError("请填写关房原因")
        closure = RoomClosure(
            closure_id=f"CL{new_token()}",
            hotel_id=hotel_id,
            room_type_id=room_type_id,
            start_date=start,
            end_date=end,
            reason=reason.strip(),
            created_by=staff.staff_id,
            created_at=datetime.now(),
        )
        with self.db.transaction() as connection:
            self.inventory_repo.add_closure(connection, closure)
            self.audit.write(
                connection,
                staff,
                "CLOSE_ROOMS",
                hotel_id=hotel_id,
                before_data="",
                after_data=_json(
                    {
                        "room_type": room_type_id,
                        "dates": f"{start}~{end}",
                        "reason": reason,
                    }
                ),
            )
        return closure

    def remove_closure(self, staff: Staff, closure_id: str) -> None:
        """Delete a closure after manager confirmation."""
        with self.db.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM room_closures WHERE closure_id = ?",
                (closure_id,),
            ).fetchone()
            if not row:
                raise NotFoundError("关房记录不存在")
            require_hotel_access(staff, str(row["hotel_id"]))
            if not staff.role.can_manage_inventory:
                raise ValidationError("仅门店店长可恢复关房")
            connection.execute(
                "DELETE FROM room_closures WHERE closure_id = ?", (closure_id,)
            )
            self.audit.write(
                connection,
                staff,
                "REOPEN_ROOMS",
                hotel_id=str(row["hotel_id"]),
                before_data=(
                    f"{row['room_type_id']} {row['start_date']}~{row['end_date']}"
                ),
                after_data="已恢复销售",
            )

    # ------------------------------------------------------------------
    # Stock correction
    # ------------------------------------------------------------------
    def correct_total(
        self,
        staff: Staff,
        hotel_id: str,
        room_type_id: str,
        biz_date: date,
        new_total: int,
        reason: str,
    ) -> None:
        """Correct physical stock with a before/after audit record."""
        require_hotel_access(staff, hotel_id)
        if not staff.role.can_manage_inventory:
            raise ValidationError("普通员工无强制修改库存的权限")
        if len(reason.strip()) < 4:
            raise ValidationError("请填写至少 4 个字符的修正原因")
        with self.db.transaction() as connection:
            old = self.inventory_repo.require(
                connection, hotel_id, room_type_id, biz_date
            )
            self.inventory_repo.set_total(
                connection, hotel_id, room_type_id, biz_date, new_total
            )
            self.audit.write(
                connection,
                staff,
                "CORRECT_INVENTORY",
                hotel_id=hotel_id,
                before_data=_json(
                    {
                        "date": biz_date.isoformat(),
                        "total": old.total,
                        "available": old.available,
                    }
                ),
                after_data=_json(
                    {
                        "date": biz_date.isoformat(),
                        "total": new_total,
                        "reason": reason,
                    }
                ),
            )

    # ------------------------------------------------------------------
    # Protocol room locks
    # ------------------------------------------------------------------
    def create_group_lock(
        self,
        staff: Staff,
        hotel_id: str,
        room_type_id: str,
        start: date,
        end: date,
        qty: int,
        release_at: datetime,
        note: str = "",
    ) -> GroupLock:
        """Reserve corporate rooms for every night of an interval."""
        require_hotel_access(staff, hotel_id)
        if not staff.role.can_manage_inventory:
            raise ValidationError("仅门店店长可创建协议锁房")
        if end <= start:
            raise ValidationError("协议锁房结束日期必须晚于开始日期")
        if start < date.today():
            raise ValidationError("不能为已过去的日期锁房")
        if qty <= 0 or qty > 50:
            raise ValidationError("锁房间数须在 1 至 50 间之间")
        if release_at <= datetime.now():
            raise ValidationError("释放时间必须晚于当前时间")
        lock = GroupLock(
            lock_id=f"GL{new_token()}",
            hotel_id=hotel_id,
            room_type_id=room_type_id,
            start_date=start,
            end_date=end,
            qty=qty,
            release_at=release_at,
            status=GroupLockStatus.ACTIVE,
            created_by=staff.staff_id,
            note=note.strip(),
            created_at=datetime.now(),
        )
        with self.db.transaction() as connection:
            self.inventory_repo.lock_group(
                connection, hotel_id, room_type_id, start, end, qty
            )
            self.inventory_repo.add_group_lock(connection, lock)
            self.audit.write(
                connection,
                staff,
                "CREATE_GROUP_LOCK",
                hotel_id=hotel_id,
                before_data="",
                after_data=_json(
                    {
                        "lock_id": lock.lock_id,
                        "qty": qty,
                        "dates": f"{start}~{end}",
                        "release_at": str(release_at),
                    }
                ),
            )
        return lock

    def release_group_lock(
        self,
        staff: Staff,
        lock_id: str,
        now: datetime | None = None,
    ) -> None:
        """Release a corporate lock early, returning rooms to sale."""
        moment = now or datetime.now()
        with self.db.transaction() as connection:
            lock = self.inventory_repo.get_group_lock(connection, lock_id)
            if not lock:
                raise NotFoundError("协议锁房记录不存在")
            require_hotel_access(staff, lock.hotel_id)
            if not staff.role.can_manage_inventory:
                raise ValidationError("仅门店店长可释放协议锁房")
            if lock.status is not GroupLockStatus.ACTIVE:
                raise ConflictError("该协议锁房已经释放")
            self.inventory_repo.release_group(
                connection,
                lock.hotel_id,
                lock.room_type_id,
                lock.start_date,
                lock.end_date,
                lock.qty,
            )
            self.inventory_repo.update_group_lock_status(
                connection, lock_id, GroupLockStatus.RELEASED
            )
            self.audit.write(
                connection,
                staff,
                "RELEASE_GROUP_LOCK",
                hotel_id=lock.hotel_id,
                before_data=_json(
                    {
                        "lock_id": lock_id,
                        "status": lock.status.label,
                        "qty": lock.qty,
                    }
                ),
                after_data=_json(
                    {"status": GroupLockStatus.RELEASED.label, "at": str(moment)}
                ),
            )

    def release_expired_group_locks(
        self, now: datetime | None = None
    ) -> int:
        """Scheduler action: release every lock whose release time has passed."""
        moment = now or datetime.now()
        count = 0
        for lock in self.inventory_repo.list_expired_group_locks(moment):
            try:
                with self.db.transaction() as connection:
                    self.inventory_repo.release_group(
                        connection,
                        lock.hotel_id,
                        lock.room_type_id,
                        lock.start_date,
                        lock.end_date,
                        lock.qty,
                    )
                    self.inventory_repo.update_group_lock_status(
                        connection, lock.lock_id, GroupLockStatus.RELEASED
                    )
                    self.audit.write(
                        connection,
                        None,
                        "AUTO_RELEASE_GROUP_LOCK",
                        hotel_id=lock.hotel_id,
                        terminal=Terminal.SYSTEM,
                        before_data=_json({"lock_id": lock.lock_id}),
                        after_data=_json(
                            {"status": GroupLockStatus.RELEASED.label}
                        ),
                    )
                count += 1
            except ConflictError:
                continue
        return count

    # ------------------------------------------------------------------
    # Status and special dates
    # ------------------------------------------------------------------
    def set_hotel_status(
        self, staff: Staff, hotel_id: str, status: HotelStatus
    ) -> None:
        """Suspend or reopen a hotel."""
        require_hotel_access(staff, hotel_id)
        if not staff.role.can_manage_inventory:
            raise ValidationError("仅门店店长或集团运营可变更营业状态")
        with self.db.transaction() as connection:
            self.catalog_repo.set_hotel_status(connection, hotel_id, status)
            self.audit.write(
                connection,
                staff,
                "SET_HOTEL_STATUS",
                hotel_id=hotel_id,
                before_data="",
                after_data=status.label,
            )

    def set_room_type_status(
        self, staff: Staff, hotel_id: str, room_type_id: str, status: RoomTypeStatus
    ) -> None:
        """Stop or resume sale of a room type."""
        require_hotel_access(staff, hotel_id)
        if not staff.role.can_manage_inventory:
            raise ValidationError("仅门店店长可变更房型销售状态")
        with self.db.transaction() as connection:
            self.catalog_repo.set_room_type_status(
                connection, room_type_id, status
            )
            self.audit.write(
                connection,
                staff,
                "SET_ROOM_TYPE_STATUS",
                hotel_id=hotel_id,
                before_data="",
                after_data=status.label,
            )

    def add_special_date(
        self, staff: Staff, special: SpecialDate
    ) -> None:
        """Group operations configures a special cancellation date."""
        current = require_staff(staff)
        if current.role is not Role.ADMIN:
            raise ValidationError("特殊日期仅限集团运营管理员配置")
        with self.db.transaction() as connection:
            self.catalog_repo.add_special_date(connection, special)
            self.audit.write(
                connection,
                staff,
                "ADD_SPECIAL_DATE",
                hotel_id="",
                before_data="",
                after_data=f"{special.biz_date} {special.name}",
            )

    # ------------------------------------------------------------------
    # Read models for the staff inventory screen
    # ------------------------------------------------------------------
    def inventory_rows(
        self, hotel_id: str, start: date, end: date
    ) -> list[dict[str, object]]:
        """Return a denormalised calendar for the inventory table."""
        room_types = {
            item.room_type_id: item.name
            for item in self.catalog_repo.list_room_types(hotel_id)
        }
        result: list[dict[str, object]] = []
        for inventory in self.inventory_repo.list_for_hotel(hotel_id, start, end):
            price = self.inventory_repo.get_price(
                None,
                hotel_id,
                inventory.room_type_id,
                inventory.biz_date,
            )
            result.append(
                {
                    "date": inventory.biz_date.isoformat(),
                    "room_type_id": inventory.room_type_id,
                    "room_type": room_types.get(
                        inventory.room_type_id, inventory.room_type_id
                    ),
                    "total": inventory.total,
                    "sold": inventory.sold,
                    "locked": inventory.locked,
                    "group_locked": inventory.group_locked,
                    "available": inventory.available,
                    "price": str(price.final_price) if price else "0.00",
                }
            )
        return result
