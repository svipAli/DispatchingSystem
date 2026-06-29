"""充值订单 - Pydantic 校验"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class RechargeCreate(BaseModel):
    """客服创建充值订单"""
    user_id: int
    amount: float = Field(..., gt=0, description="充值金额")
    remark: str | None = None


class RechargeOut(BaseModel):
    id: int
    user_id: int
    amount: float
    operator_id: int | None
    order_status: str
    remark: str | None
    status: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
