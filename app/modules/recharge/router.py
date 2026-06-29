"""
充值订单 - API 路由

- GET  /api/v1/recharges              所有充值订单列表（后台管理）
- POST /api/v1/recharges              创建充值订单（客服操作）
- POST /api/v1/recharges/{id}/complete 确认完成充值（扣款+写流水）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, paginate, error
from app.dependencies import get_db, get_current_user, require_admin
from app.modules.recharge.schemas import RechargeCreate, RechargeOut
from app.modules.recharge.service import RechargeService

router = APIRouter(prefix="/recharges", tags=["充值管理"])
service = RechargeService()


@router.get("", summary="充值订单列表")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    items, total = await service.list_all(db, page=page, page_size=page_size)
    return paginate(
        [RechargeOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.post("", summary="创建充值订单")
async def create_order(
    data: RechargeCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    item = await service.create(db, data)
    return success(RechargeOut.model_validate(item).model_dump(), message="充值订单已创建")


@router.post("/{order_id}/complete", summary="确认完成充值")
async def complete_order(
    order_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    item = await service.complete(db, order_id, current_user.id)
    if not item:
        return error(code=1001, message="订单不存在或已处理")
    return success(RechargeOut.model_validate(item).model_dump(), message="充值完成")
