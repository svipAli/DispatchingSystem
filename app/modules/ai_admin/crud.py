from __future__ import annotations
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.ai_admin.models import ChatMessage


class ChatCRUD(BaseCRUD[ChatMessage]):
    def __init__(self):
        super().__init__(ChatMessage)

    async def get_history(
        self, db: AsyncSession, user_id: int, limit: int = 20, offset: int = 0
    ) -> tuple[list[ChatMessage], int]:
        base = select(ChatMessage).where(
            ChatMessage.user_id == user_id, ChatMessage.status == True
        )
        total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
        stmt = base.order_by(desc(ChatMessage.id)).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(reversed(result.scalars().all())), total

    async def add(self, db: AsyncSession, user_id: int, role: str, content: str) -> ChatMessage:
        return await self.create(db, user_id=user_id, role=role, content=content)
