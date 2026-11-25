"""Catalogue queries and side-effect-free quotations."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import sqlite3

from ..domain.enums import HotelStatus, RoomTypeStatus
from ..domain.errors import NotFoundError, ValidationError
from ..domain.models import (
    Hotel,
    NightlyPrice,
    Quote,
    RoomType,
    SearchResult,
    SpecialDate,
)
from ..domain.money import date_range
from ..infrastructure.database import Database
from ..repositories.catalog_repository import CatalogRepository
from ..repositories.inventory_repository import InventoryRepository


class CatalogService:
    """Read-only search and quotation use cases."""

    def __init__(
        self,
        db: Database,
        catalog_repo: CatalogRepository,
        inventory_repo: InventoryRepository,
    ) -> None:
        self.db = db
        self.catalog_repo = catalog_repo
        self.inventory_repo = inventory_repo

    def hotels(self, city: str | None = None) -> list[Hotel]:
        """List hotels, optionally filtered by city."""
        return self.catalog_repo.list_hotels(city=city or None)

    def cities(self) -> list[str]:
        """List cities that currently have hotels."""
        return self.catalog_repo.list_cities()

    def room_types(self, hotel_id: str) -> list[RoomType]:
        """List room types of one hotel."""
        return self.catalog_repo.list_room_types(hotel_id)

    def room_type(self, room_type_id: str) -> RoomType:
        """Load one room type or raise a friendly error."""
        room_type = self.catalog_repo.get_room_type(room_type_id)
        if not room_type:
            raise NotFoundError("房型不存在")
        return room_type

    def hotel(self, hotel_id: str) -> Hotel:
        """Load one hotel or raise a friendly error."""
        hotel = self.catalog_repo.get_hotel(hotel_id)
        if not hotel:
            raise NotFoundError("门店不存在")
        return hotel

    def special_dates(self) -> list[SpecialDate]:
        """Return configured special cancellation dates."""
        return self.catalog_repo.list_special_dates()

    def quote(
        self,
        hotel_id: str,
        room_type_id: str,
        check_in: date,
        check_out: date,
        qty: int = 1,
        connection: sqlite3.Connection | None = None,
    ) -> Quote:
        """Build a quotation without changing any data.

        The optional connection lets the booking transaction recalculate the
        quote using the same snapshot that will be used for the conditional
        stock update.
        """
        self._validate_dates(check_in, check_out)
        if qty <= 0 or qty > 9:
            raise ValidationError("预订间数须在 1 至 9 间之间")
        hotel = self.catalog_repo.get_hotel(hotel_id)
        room_type = self.catalog_repo.get_room_type(room_type_id)
        if not hotel or not room_type or room_type.hotel_id != hotel_id:
            raise NotFoundError("门店或房型不存在")
        specials = self.catalog_repo.special_date_set()
        nightly: list[NightlyPrice] = []
        reason = ""
        if not hotel.is_open:
            reason = "门店暂停营业"
        if not room_type.is_on_sale:
            reason = reason or "该房型已停售"
        closure_reason = self.inventory_repo.closure_reason(
            connection, hotel_id, room_type_id, check_in, check_out
        )
        if closure_reason and not reason:
            reason = f"所选日期已关房：{closure_reason}"
        for biz_date in date_range(check_in, check_out):
            inventory = self.inventory_repo.get(
                connection, hotel_id, room_type_id, biz_date
            )
            price = self.inventory_repo.get_price(
                connection, hotel_id, room_type_id, biz_date
            )
            available = inventory.available if inventory else 0
            unit_price = price.final_price if price else room_type.base_price
            if inventory is None and not reason:
                reason = "所选日期暂未开放库存"
            elif inventory is not None and available < qty and not reason:
                reason = f"{biz_date.isoformat()} 仅剩 {available} 间"
            nightly.append(
                NightlyPrice(
                    biz_date=biz_date,
                    unit_price=unit_price,
                    available=available,
                    is_special=biz_date in specials,
                )
            )
        return Quote(
            hotel=hotel,
            room_type=room_type,
            check_in=check_in,
            check_out=check_out,
            qty=qty,
            nights=nightly,
            reason=reason,
        )

    def search(
        self,
        check_in: date,
        check_out: date,
        guests: int = 1,
        city: str = "",
        hotel_id: str = "",
        max_price: Decimal | None = None,
        breakfast_only: bool = False,
    ) -> list[SearchResult]:
        """Search sellable rooms across all matching hotels."""
        self._validate_dates(check_in, check_out)
        if guests <= 0 or guests > 9:
            raise ValidationError("入住人数须在 1 至 9 人之间")
        hotels = self.catalog_repo.list_hotels(
            city=city or None, open_only=True
        )
        if hotel_id:
            hotels = [hotel for hotel in hotels if hotel.hotel_id == hotel_id]
        results: list[SearchResult] = []
        for hotel in hotels:
            for room_type in self.catalog_repo.list_room_types(
                hotel.hotel_id, on_sale_only=True
            ):
                if room_type.capacity < guests:
                    continue
                if breakfast_only and not room_type.breakfast:
                    continue
                quote = self.quote(
                    hotel.hotel_id,
                    room_type.room_type_id,
                    check_in,
                    check_out,
                )
                if max_price is not None and any(
                    night.unit_price > max_price for night in quote.nights
                ):
                    continue
                results.append(SearchResult(hotel, room_type, quote))
        results.sort(
            key=lambda item: (
                not item.available,
                item.quote.total,
                item.hotel.hotel_id,
            )
        )
        return results

    def availability_reason(
        self, hotel_id: str, room_type_id: str, check_in: date, check_out: date
    ) -> str:
        """Return an empty string when the interval is bookable."""
        return self.quote(hotel_id, room_type_id, check_in, check_out).reason

    @staticmethod
    def _validate_dates(check_in: date, check_out: date) -> None:
        if not isinstance(check_in, date) or not isinstance(check_out, date):
            raise ValidationError("请选择入住和离店日期")
        if check_in < date.today():
            raise ValidationError("入住日期不能早于今天")
        if check_out <= check_in:
            raise ValidationError("离店日期必须晚于入住日期")
        if (check_out - check_in).days > 30:
            raise ValidationError("单笔订单最长连续入住 30 晚")
