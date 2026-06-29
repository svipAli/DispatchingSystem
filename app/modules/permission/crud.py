"""
权限模块 - 数据访问层
"""
from __future__ import annotations

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.permission.models import Permission, RolePermission


class PermissionCRUD(BaseCRUD[Permission]):
    def __init__(self):
        super().__init__(Permission)

    async def get_by_code(self, db: AsyncSession, code: str) -> Permission | None:
        stmt = select(Permission).where(
            Permission.code == code, Permission.status == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_permission_ids(self, db: AsyncSession, role_id: int) -> list[int]:
        """查询角色拥有的权限 ID 列表"""
        stmt = select(RolePermission.permission_id).where(
            RolePermission.role_id == role_id, RolePermission.status == True
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_role_permission_codes(self, db: AsyncSession, role_id: int) -> set[str]:
        """查询角色拥有的权限 code 集合（用于 PermissionChecker）"""
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(
                RolePermission.role_id == role_id,
                RolePermission.status == True,
                Permission.status == True,
            )
        )
        result = await db.execute(stmt)
        return {row[0] for row in result.all()}

    async def assign_permissions(
        self, db: AsyncSession, role_id: int, permission_ids: list[int]
    ):
        """给角色分配权限：删除旧关联，批量创建新关联"""
        await db.execute(
            sa_delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        for perm_id in permission_ids:
            rp = RolePermission(role_id=role_id, permission_id=perm_id)
            db.add(rp)
        await db.flush()
