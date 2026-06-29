"""
菜单模块 - 数据访问层
"""
from __future__ import annotations

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.menu.models import Menu, RoleMenu


class MenuCRUD(BaseCRUD[Menu]):
    def __init__(self):
        super().__init__(Menu)

    async def get_tree(self, db: AsyncSession) -> list[Menu]:
        """获取全部启用菜单的平铺列表，按 sort 排序（树结构由 service 层组装）"""
        items, _ = await self.get_list(db, page=1, page_size=1000, status=True)
        return sorted(items, key=lambda x: x.sort)

    async def get_by_role_ids(
        self, db: AsyncSession, role_ids: list[int]
    ) -> list[Menu]:
        """查询多个角色能看到的菜单合集"""
        if not role_ids:
            return []
        stmt = (
            select(Menu)
            .distinct()
            .join(RoleMenu, RoleMenu.menu_id == Menu.id)
            .where(
                RoleMenu.role_id.in_(role_ids),
                RoleMenu.status == True,
                Menu.status == True,
            )
            .order_by(Menu.sort)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_role_menu_ids(self, db: AsyncSession, role_id: int) -> list[int]:
        """查询角色拥有的菜单 ID 列表"""
        stmt = select(RoleMenu.menu_id).where(
            RoleMenu.role_id == role_id, RoleMenu.status == True
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.all()]

    async def assign_menus(
        self, db: AsyncSession, role_id: int, menu_ids: list[int]
    ):
        """给角色分配菜单：删除旧关联，批量创建新关联"""
        await db.execute(
            sa_delete(RoleMenu).where(RoleMenu.role_id == role_id)
        )
        for menu_id in menu_ids:
            rm = RoleMenu(role_id=role_id, menu_id=menu_id)
            db.add(rm)
        await db.flush()
