"""
API Token 模块 - 业务逻辑层
生成 JWT Token（type=mcp），过期时间默认 90 天
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.api_token.crud import ApiTokenCRUD
from app.modules.api_token.models import ApiToken
from app.modules.api_token.schemas import ApiTokenCreate, ApiTokenUpdate
from app.core.security import create_mcp_token


class ApiTokenService:
    def __init__(self):
        self.crud = ApiTokenCRUD()

    async def get(self, db: AsyncSession, token_id: int) -> ApiToken | None:
        return await self.crud.get_by_id(db, token_id)

    async def get_by_jti(self, db: AsyncSession, jti: str) -> ApiToken | None:
        return await self.crud.get_by_jti(db, jti)

    async def list_by_user(
        self, db: AsyncSession, user_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[ApiToken], int]:
        return await self.crud.get_by_user(db, user_id, page=page, page_size=page_size)

    async def create(self, db: AsyncSession, user_id: int, data: ApiTokenCreate) -> ApiToken:
        jti = uuid.uuid4().hex
        token_str = create_mcp_token(user_id, jti)
        expires_at = datetime.now() + timedelta(days=90)
        return await self.crud.create(
            db,
            user_id=user_id,
            name=data.name,
            token=token_str,
            jti=jti,
            expires_at=expires_at,
        )

    async def update(
        self, db: AsyncSession, token_id: int, data: ApiTokenUpdate
    ) -> ApiToken | None:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return None
        return await self.crud.update(db, token_id, **updates)

    async def mark_used(self, db: AsyncSession, token_id: int):
        await self.crud.update(db, token_id, last_used_at=datetime.now())

    async def revoke(self, db: AsyncSession, token_id: int, redis=None):
        """撤销 Token：软删除 + 加入 Redis 黑名单"""
        token = await self.crud.get_by_id(db, token_id)
        if token and redis and token.jti:
            # 计算剩余有效期，设为黑名单 TTL
            now = datetime.now()
            if token.expires_at and token.expires_at > now:
                ttl = int((token.expires_at - now).total_seconds())
            else:
                ttl = 86400 * 90  # 默认90天
            await redis.set(f"token_revoked:{token.jti}", "1", ex=max(ttl, 1))
        await self.crud.delete(db, token_id, soft=True)
