"""
角色模块 - 数据访问层
"""
from __future__ import annotations

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.role.models import Role, UserRole


class RoleCRUD(BaseCRUD[Role]):
    def __init__(self):
        super().__init__(Role)

    async def get_by_code(self, db: AsyncSession, code: str) -> Role | None:
        stmt = select(Role).where(Role.code == code, Role.status == True)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_role_ids(self, db: AsyncSession, user_id: int) -> list[int]:
        """查询用户拥有的角色 ID 列表"""
        stmt = select(UserRole.role_id).where(
            UserRole.user_id == user_id, UserRole.status == True
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.all()]

    async def assign_roles(self, db: AsyncSession, user_id: int, role_ids: list[int]):
        """给用户分配角色：先删除旧关联，再批量创建新关联"""
        # 删除旧关联
        await db.execute(
            sa_delete(UserRole).where(UserRole.user_id == user_id)
        )
        # 批量创建新关联
        for role_id in role_ids:
            ur = UserRole(user_id=user_id, role_id=role_id)
            db.add(ur)
        await db.flush()

    async def get_users_by_role(
        self, db: AsyncSession, role_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[int], int]:
        """分页查询拥有某个角色的用户 ID 列表"""
        from sqlalchemy import func
        base = select(UserRole.user_id).where(
            UserRole.role_id == role_id, UserRole.status == True
        )
        count_stmt = select(func.count()).select_from(UserRole).where(
            UserRole.role_id == role_id, UserRole.status == True
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        offset = (page - 1) * page_size
        stmt = base.offset(offset).limit(page_size)
        result = await db.execute(stmt)
        return [row[0] for row in result.all()], total
