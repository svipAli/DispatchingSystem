"""
API Token 模块 - Pydantic 数据校验
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ApiTokenCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Token 名称")


class ApiTokenUpdate(BaseModel):
    name: str | None = None
    remark: str | None = None
    status: bool | None = None


class ApiTokenOut(BaseModel):
    id: int
    user_id: int
    name: str
    token: str
    jti: str | None
    last_used_at: datetime | None
    expires_at: datetime | None
    status: bool
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
