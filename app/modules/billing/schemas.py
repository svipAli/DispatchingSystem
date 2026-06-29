"""计费流水 - Pydantic 校验"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class BillingOut(BaseModel):
    id: int
    user_id: int
    type: str
    amount: float
    balance_before: float
    balance_after: float
    related_id: int | None
    related_type: str | None
    remark: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
