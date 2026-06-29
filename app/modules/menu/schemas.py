"""
菜单模块 - Pydantic 数据校验
"""
from datetime import datetime
from pydantic import BaseModel, Field


class MenuCreate(BaseModel):
    parent_id: int | None = None
    name: str = Field(..., min_length=1, max_length=50)
    icon: str | None = None
    path: str | None = None
    component: str | None = None
    sort: int = 0
    remark: str | None = None


class MenuUpdate(BaseModel):
    parent_id: int | None = None
    name: str | None = None
    icon: str | None = None
    path: str | None = None
    component: str | None = None
    sort: int | None = None
    remark: str | None = None
    status: bool | None = None


class AssignMenuIn(BaseModel):
    """给角色分配菜单"""
    role_id: int
    menu_ids: list[int]


class MenuOut(BaseModel):
    id: int
    parent_id: int | None
    name: str
    icon: str | None
    path: str | None
    component: str | None
    sort: int
    status: bool
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MenuTreeOut(BaseModel):
    """树形菜单结构，用于前端渲染"""
    id: int
    parent_id: int | None
    name: str
    icon: str | None
    path: str | None
    component: str | None
    sort: int
    children: list["MenuTreeOut"] = []
