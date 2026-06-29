from __future__ import annotations
"""
权限模块 - 业务逻辑层
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.permission.crud import PermissionCRUD
from app.modules.permission.models import Permission
from app.modules.permission.schemas import PermissionCreate, PermissionUpdate, AssignPermissionIn


class PermissionService:
    def __init__(self):
        self.crud = PermissionCRUD()

    async def get(self, db: AsyncSession, perm_id: int) -> Permission | None:
        return await self.crud.get_by_id(db, perm_id)

    async def list(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20, module: str | None = None
    ) -> tuple[list[Permission], int]:
        filters = {}
        if module:
            filters["module"] = module
        return await self.crud.get_list(db, page=page, page_size=page_size, **filters)

    async def create(self, db: AsyncSession, data: PermissionCreate) -> Permission:
        return await self.crud.create(
            db,
            name=data.name,
            code=data.code,
            module=data.module,
            description=data.description,
            remark=data.remark,
        )

    async def update(
        self, db: AsyncSession, perm_id: int, data: PermissionUpdate
    ) -> Permission | None:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return None
        return await self.crud.update(db, perm_id, **updates)

    async def assign_permissions(self, db: AsyncSession, data: AssignPermissionIn):
        await self.crud.assign_permissions(db, data.role_id, data.permission_ids)

    async def get_role_permissions(self, db: AsyncSession, role_id: int) -> list[int]:
        return await self.crud.get_role_permission_ids(db, role_id)
