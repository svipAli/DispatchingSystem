from __future__ import annotations
"""
权限模块 - API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, paginate, error
from app.dependencies import get_db, require_admin
from app.modules.permission.schemas import (
    PermissionCreate, PermissionUpdate, AssignPermissionIn, PermissionOut,
)
from app.modules.permission.service import PermissionService

router = APIRouter(prefix="/permissions", tags=["权限管理"])
service = PermissionService()


@router.get("")
async def list_permissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    module: str | None = None,
    db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin),
):
    items, total = await service.list(db, page=page, page_size=page_size, module=module)
    return paginate(
        [PermissionOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.get("/{perm_id}")
async def get_permission(perm_id: int, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await service.get(db, perm_id)
    if not item:
        return error(code=404, message="权限不存在")
    return success(PermissionOut.model_validate(item).model_dump())


@router.post("")
async def create_permission(data: PermissionCreate, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await service.create(db, data)
    return success(PermissionOut.model_validate(item).model_dump(), message="创建成功")


@router.put("/{perm_id}")
async def update_permission(
    perm_id: int, data: PermissionUpdate, db: AsyncSession = Depends(get_db)
):
    item = await service.update(db, perm_id, data)
    if not item:
        return error(code=404, message="权限不存在")
    return success(PermissionOut.model_validate(item).model_dump(), message="更新成功")


@router.post("/assign")
async def assign_permissions(data: AssignPermissionIn, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    await service.assign_permissions(db, data)
    return success(message="权限分配成功")


@router.get("/role/{role_id}")
async def get_role_permissions(role_id: int, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    perm_ids = await service.get_role_permissions(db, role_id)
    return success({"role_id": role_id, "permission_ids": perm_ids})
