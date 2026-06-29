"""文件管理 - 数据访问层"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.file_record.models import FileRecord


class FileCRUD(BaseCRUD[FileRecord]):
    def __init__(self):
        super().__init__(FileRecord)

    async def get_by_user(
        self, db: AsyncSession, user_id: int, *,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[FileRecord], int]:
        return await self.get_list(db, page=page, page_size=page_size, user_id=user_id)
