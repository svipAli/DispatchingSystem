"""
充值订单 - 业务逻辑层

充值流程：
1. 客服创建充值订单（order_status=pending）
2. 客服确认完成充值：
   a. 更新订单状态为 completed
   b. 增加用户余额
   c. 创建流水记录（type=recharge）
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.recharge.crud import RechargeCRUD
from app.modules.recharge.models import RechargeOrder
from app.modules.recharge.schemas import RechargeCreate
from app.modules.user.crud import UserCRUD
from app.modules.billing.service import BillingService


class RechargeService:
    def __init__(self):
        self.crud = RechargeCRUD()

    async def get(self, db: AsyncSession, order_id: int) -> RechargeOrder | None:
        return await self.crud.get_by_id(db, order_id)

    async def list_all(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[RechargeOrder], int]:
        return await self.crud.get_list(db, page=page, page_size=page_size)

    async def create(self, db: AsyncSession, data: RechargeCreate) -> RechargeOrder:
        return await self.crud.create(
            db, user_id=data.user_id, amount=data.amount, remark=data.remark,
        )

    async def complete(
        self, db: AsyncSession, order_id: int, operator_id: int
    ) -> RechargeOrder | None:
        order = await self.crud.get_by_id(db, order_id)
        if not order or order.order_status != "pending":
            return None

        # 更新订单状态
        order = await self.crud.complete(db, order_id, operator_id)
        if not order:
            return None

        # 增加用户余额
        user_crud = UserCRUD()
        user = await user_crud.get_by_id(db, order.user_id)
        balance_before = user.balance
        balance_after = balance_before + order.amount
        await user_crud.update(db, order.user_id, balance=balance_after)

        # 创建流水记录
        billing_svc = BillingService()
        await billing_svc.create_record(
            db,
            user_id=order.user_id,
            type_="recharge",
            amount=order.amount,
            balance_before=balance_before,
            balance_after=balance_after,
            related_id=order.id,
            related_type="recharge",
            remark=order.remark,
        )

        return order
