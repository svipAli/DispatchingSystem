"""充值订单 - 数据访问层"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.recharge.models import RechargeOrder


class RechargeCRUD(BaseCRUD[RechargeOrder]):
    def __init__(self):
        super().__init__(RechargeOrder)

    async def get_by_user(
        self, db: AsyncSession, user_id: int, *,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[RechargeOrder], int]:
        return await self.get_list(db, page=page, page_size=page_size, user_id=user_id)

    async def complete(
        self, db: AsyncSession, order_id: int, operator_id: int
    ) -> RechargeOrder | None:
        return await self.update(
            db, order_id,
            order_status="completed",
            operator_id=operator_id,
            completed_at=datetime.now(),
        )
