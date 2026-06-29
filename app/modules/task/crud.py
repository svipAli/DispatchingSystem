"""
任务调度模块 - 数据访问层
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.task.models import Task


class TaskCRUD(BaseCRUD[Task]):
    def __init__(self):
        super().__init__(Task)

    async def get_by_user(
        self, db: AsyncSession, user_id: int, *,
        page: int = 1, page_size: int = 20,
        status: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[Task], int]:
        """分页查询用户的任务列表，可按状态过滤，可按关键词搜索"""
        filters = {"user_id": user_id}
        if status:
            filters["status"] = status
        return await self.get_list(db, page=page, page_size=page_size, keyword=keyword, **filters)

    async def get_by_node(
        self, db: AsyncSession, node_id: int, *,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[Task], int]:
        """查询正在某个节点上执行的任务"""
        return await self.get_list(
            db, page=page, page_size=page_size,
            node_id=node_id, status="running",
        )

    async def update_status(
        self, db: AsyncSession, task_id: int, status: str, **extra
    ):
        """更新任务状态"""
        if status == "running":
            extra["started_at"] = datetime.now()
        elif status in ("completed", "failed", "cancelled"):
            extra["finished_at"] = datetime.now()
        extra["status"] = status
        return await self.update(db, task_id, **extra)
