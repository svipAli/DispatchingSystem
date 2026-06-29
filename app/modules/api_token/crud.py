"""
API Token 模块 - 数据访问层
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.api_token.models import ApiToken


class ApiTokenCRUD(BaseCRUD[ApiToken]):
    def __init__(self):
        super().__init__(ApiToken)

    async def get_by_jti(self, db: AsyncSession, jti: str) -> ApiToken | None:
        stmt = select(ApiToken).where(
            ApiToken.jti == jti, ApiToken.status == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user(
        self, db: AsyncSession, user_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[ApiToken], int]:
        return await self.get_list(
            db, page=page, page_size=page_size, user_id=user_id, status=True
        )
