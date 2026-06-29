"""
权限模块 - Pydantic 数据校验
"""
from datetime import datetime
from pydantic import BaseModel, Field


class PermissionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=100, description="权限标识，如 user:delete")
    module: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    remark: str | None = None


class PermissionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    remark: str | None = None
    status: bool | None = None


class AssignPermissionIn(BaseModel):
    """给角色分配权限"""
    role_id: int
    permission_ids: list[int]


class PermissionOut(BaseModel):
    id: int
    name: str
    code: str
    module: str
    description: str | None
    status: bool
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
