from __future__ import annotations
"""
角色模块 - API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, paginate, error
from app.dependencies import get_db, require_admin
from app.modules.role.schemas import RoleCreate, RoleUpdate, AssignRoleIn, RoleOut
from app.modules.role.service import RoleService

router = APIRouter(prefix="/roles", tags=["角色管理"])
service = RoleService()


@router.get("")
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin),
):
    items, total = await service.list(db, page=page, page_size=page_size)
    return paginate(
        [RoleOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.get("/{role_id}")
async def get_role(role_id: int, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await service.get(db, role_id)
    if not item:
        return error(code=404, message="角色不存在")
    return success(RoleOut.model_validate(item).model_dump())


@router.post("")
async def create_role(data: RoleCreate, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    existing = await service.get_by_code(db, data.code)
    if existing:
        return error(code=1001, message="角色标识已存在")
    item = await service.create(db, data)
    return success(RoleOut.model_validate(item).model_dump(), message="创建成功")


@router.put("/{role_id}")
async def update_role(role_id: int, data: RoleUpdate, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await service.update(db, role_id, data)
    if not item:
        return error(code=404, message="角色不存在")
    return success(RoleOut.model_validate(item).model_dump(), message="更新成功")


@router.post("/assign")
async def assign_roles(data: AssignRoleIn, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    await service.assign_roles(db, data)
    return success(message="角色分配成功")


@router.get("/user/{user_id}")
async def get_user_roles(user_id: int, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    role_ids = await service.get_user_role_ids(db, user_id)
    return success({"user_id": user_id, "role_ids": role_ids})
