from __future__ import annotations
"""
角色模块 - 业务逻辑层
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.role.crud import RoleCRUD
from app.modules.role.models import Role
from app.modules.role.schemas import RoleCreate, RoleUpdate, AssignRoleIn


class RoleService:
    def __init__(self):
        self.crud = RoleCRUD()

    async def get(self, db: AsyncSession, role_id: int) -> Role | None:
        return await self.crud.get_by_id(db, role_id)

    async def get_by_code(self, db: AsyncSession, code: str) -> Role | None:
        return await self.crud.get_by_code(db, code)

    async def list(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Role], int]:
        return await self.crud.get_list(db, page=page, page_size=page_size)

    async def create(self, db: AsyncSession, data: RoleCreate) -> Role:
        return await self.crud.create(
            db,
            name=data.name,
            code=data.code,
            description=data.description,
            remark=data.remark,
        )

    async def update(
        self, db: AsyncSession, role_id: int, data: RoleUpdate
    ) -> Role | None:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return None
        return await self.crud.update(db, role_id, **updates)

    async def assign_roles(self, db: AsyncSession, data: AssignRoleIn):
        await self.crud.assign_roles(db, data.user_id, data.role_ids)

    async def get_user_role_ids(self, db: AsyncSession, user_id: int) -> list[int]:
        return await self.crud.get_user_role_ids(db, user_id)
