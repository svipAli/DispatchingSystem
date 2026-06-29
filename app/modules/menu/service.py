"""
菜单模块 - 业务逻辑层
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.menu.crud import MenuCRUD
from app.modules.menu.models import Menu
from app.modules.menu.schemas import MenuCreate, MenuUpdate, AssignMenuIn


class MenuService:
    def __init__(self):
        self.crud = MenuCRUD()

    async def get(self, db: AsyncSession, menu_id: int) -> Menu | None:
        return await self.crud.get_by_id(db, menu_id)

    async def list(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Menu], int]:
        return await self.crud.get_list(db, page=page, page_size=page_size)

    async def create(self, db: AsyncSession, data: MenuCreate) -> Menu:
        return await self.crud.create(
            db,
            parent_id=data.parent_id,
            name=data.name,
            icon=data.icon,
            path=data.path,
            component=data.component,
            sort=data.sort,
            remark=data.remark,
        )

    async def update(
        self, db: AsyncSession, menu_id: int, data: MenuUpdate
    ) -> Menu | None:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return None
        return await self.crud.update(db, menu_id, **updates)

    async def get_tree(self, db: AsyncSession) -> list[dict]:
        """组装树形菜单结构"""
        items = await self.crud.get_tree(db)
        return self._build_tree(items, None)

    def _build_tree(self, items: list[Menu], parent_id: int | None) -> list[dict]:
        result = []
        for item in items:
            if item.parent_id == parent_id:
                node = {
                    "id": item.id,
                    "parent_id": item.parent_id,
                    "name": item.name,
                    "icon": item.icon,
                    "path": item.path,
                    "component": item.component,
                    "sort": item.sort,
                    "children": self._build_tree(items, item.id),
                }
                result.append(node)
        return result

    async def get_user_menus(self, db: AsyncSession, role_ids: list[int]) -> list[dict]:
        """获取用户的菜单树（根据角色过滤）"""
        items = await self.crud.get_by_role_ids(db, role_ids)
        return self._build_tree(items, None)

    async def assign_menus(self, db: AsyncSession, data: AssignMenuIn):
        await self.crud.assign_menus(db, data.role_id, data.menu_ids)

    async def get_role_menus(self, db: AsyncSession, role_id: int) -> list[int]:
        return await self.crud.get_role_menu_ids(db, role_id)
