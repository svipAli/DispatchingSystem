from __future__ import annotations
"""
菜单模块 - API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, paginate, error
from app.dependencies import get_db, require_admin
from app.modules.menu.schemas import MenuCreate, MenuUpdate, AssignMenuIn, MenuOut
from app.modules.menu.service import MenuService

router = APIRouter(prefix="/menus", tags=["菜单管理"])
service = MenuService()


@router.get("/tree")
async def get_menu_tree(db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    """获取完整的菜单树（用于后台管理）"""
    tree = await service.get_tree(db)
    return success(tree)


@router.get("")
async def list_menus(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin),
):
    items, total = await service.list(db, page=page, page_size=page_size)
    return paginate(
        [MenuOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.get("/{menu_id}")
async def get_menu(menu_id: int, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await service.get(db, menu_id)
    if not item:
        return error(code=404, message="菜单不存在")
    return success(MenuOut.model_validate(item).model_dump())


@router.post("")
async def create_menu(data: MenuCreate, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await service.create(db, data)
    return success(MenuOut.model_validate(item).model_dump(), message="创建成功")


@router.put("/{menu_id}")
async def update_menu(menu_id: int, data: MenuUpdate, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await service.update(db, menu_id, data)
    if not item:
        return error(code=404, message="菜单不存在")
    return success(MenuOut.model_validate(item).model_dump(), message="更新成功")


@router.post("/assign")
async def assign_menus(data: AssignMenuIn, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    await service.assign_menus(db, data)
    return success(message="菜单分配成功")


@router.get("/role/{role_id}")
async def get_role_menus(role_id: int, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    menu_ids = await service.get_role_menus(db, role_id)
    return success({"role_id": role_id, "menu_ids": menu_ids})
