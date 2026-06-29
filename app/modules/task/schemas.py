"""
任务调度模块 - Pydantic 数据校验
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """用户提交任务请求"""
    task_type: str = Field(default="mcp_call", max_length=50)
    service_type: str = Field(..., min_length=1, max_length=100, description="服务类型")
    request_params: dict | None = Field(default=None, description="请求参数")


class TaskUpdate(BaseModel):
    """后台更新任务（如手动取消）"""
    status: str | None = Field(None, pattern=r"^(cancelled)$")
    remark: str | None = None


class TaskOut(BaseModel):
    id: int
    user_id: int
    api_token_id: int | None
    task_type: str
    service_type: str
    request_params: dict | None
    result: dict | None
    status: str
    node_id: int | None
    cost: float
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
