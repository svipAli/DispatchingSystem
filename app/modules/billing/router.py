"""计费流水 - API 路由"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, paginate
from app.dependencies import get_db, get_current_user
from app.modules.billing.schemas import BillingOut
from app.modules.billing.service import BillingService

router = APIRouter(prefix="/billing", tags=["计费流水"])
service = BillingService()


@router.get("", summary="我的消费记录")
async def list_my_billing(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    record_type: str | None = Query(None, alias="type", description="recharge / deduct"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_by_user(
        db, current_user.id, page=page, page_size=page_size, record_type=record_type,
    )
    return paginate(
        [BillingOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )
