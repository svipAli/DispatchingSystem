"""计费流水 - 数据访问层"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.billing.models import BillingRecord


class BillingCRUD(BaseCRUD[BillingRecord]):
    def __init__(self):
        super().__init__(BillingRecord)

    async def get_by_user(
        self, db: AsyncSession, user_id: int, *,
        page: int = 1, page_size: int = 20,
        record_type: str | None = None,
    ) -> tuple[list[BillingRecord], int]:
        """分页查询用户的流水记录"""
        filters = {"user_id": user_id}
        if record_type:
            filters["type"] = record_type
        return await self.get_list(db, page=page, page_size=page_size, **filters)

    async def get_user_total_charge(
        self, db: AsyncSession, user_id: int, record_type: str = "deduct"
    ) -> float:
        """统计用户某类流水的总金额（如累计扣费）"""
        stmt = select(func.coalesce(func.sum(BillingRecord.amount), 0.0)).where(
            BillingRecord.user_id == user_id,
            BillingRecord.type == record_type,
        )
        result = await db.execute(stmt)
        return result.scalar() or 0.0
