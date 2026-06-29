"""计费流水 - 业务逻辑层"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.billing.crud import BillingCRUD
from app.modules.billing.models import BillingRecord


class BillingService:
    def __init__(self):
        self.crud = BillingCRUD()

    async def list_by_user(
        self, db: AsyncSession, user_id: int, *,
        page: int = 1, page_size: int = 20,
        record_type: str | None = None,
    ) -> tuple[list[BillingRecord], int]:
        return await self.crud.get_by_user(
            db, user_id, page=page, page_size=page_size, record_type=record_type,
        )

    async def create_record(
        self, db: AsyncSession, *,
        user_id: int, type_: str, amount: float,
        balance_before: float, balance_after: float,
        related_id: int | None = None, related_type: str | None = None,
        remark: str | None = None,
    ) -> BillingRecord:
        """创建一条流水记录（由扣费或充值时调用）"""
        return await self.crud.create(
            db,
            user_id=user_id,
            type=type_,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            related_id=related_id,
            related_type=related_type,
            remark=remark,
        )
