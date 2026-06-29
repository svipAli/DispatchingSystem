"""
角色模块 - Pydantic 数据校验
"""
from datetime import datetime
from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    remark: str | None = None


class RoleUpdate(BaseModel):
    """更新角色请求（全部可选）"""
    name: str | None = None
    description: str | None = None
    remark: str | None = None
    status: bool | None = None


class AssignRoleIn(BaseModel):
    """给用户分配角色"""
    user_id: int
    role_ids: list[int]


class RoleOut(BaseModel):
    id: int
    name: str
    code: str
    description: str | None
    is_system: bool
    status: bool
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
