"""
任务调度模块 - 业务逻辑层

完整的任务调度流程：
1. 用户提交任务 → 创建 task（status=queued）
2. 调度器选择可用节点 → get_idle_node(service_type)
3. 分配到节点 → 更新 node_id, status=running, started_at
4. 发送请求到 MCP 节点执行
5. 收到结果 → 更新 result, status=completed, finished_at
6. 扣费 → 更新 cost, 调用 billing 模块扣余额
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.task.crud import TaskCRUD
from app.modules.task.models import Task
from app.modules.task.schemas import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self):
        self.crud = TaskCRUD()

    async def get(self, db: AsyncSession, task_id: int) -> Task | None:
        return await self.crud.get_by_id(db, task_id)

    async def list_by_user(
        self, db: AsyncSession, user_id: int, *,
        page: int = 1, page_size: int = 20,
        status: str | None = None, keyword: str | None = None,
    ) -> tuple[list[Task], int]:
        return await self.crud.get_by_user(
            db, user_id, page=page, page_size=page_size, status=status, keyword=keyword,
        )

    async def list_all(
        self, db: AsyncSession, *,
        page: int = 1, page_size: int = 20,
        status: str | None = None, keyword: str | None = None,
    ) -> tuple[list[Task], int]:
        return await self.crud.get_list(
            db, page=page, page_size=page_size, status=status, keyword=keyword,
        )

    async def submit(self, db: AsyncSession, user_id: int, data: TaskCreate) -> Task:
        """
        提交任务：创建任务记录，状态为 queued
        实际调度由 Celery Worker 异步执行
        """
        return await self.crud.create(
            db,
            user_id=user_id,
            task_type=data.task_type,
            service_type=data.service_type,
            request_params=data.request_params,
            status="queued",
        )

    async def dispatch(
        self, db: AsyncSession, task_id: int, node_id: int, cost: float
    ) -> Task | None:
        """将任务分配到指定节点执行"""
        return await self.crud.update_status(
            db, task_id, "running", node_id=node_id, cost=cost,
        )

    async def complete(
        self, db: AsyncSession, task_id: int, result: dict
    ) -> Task | None:
        """任务执行完成，记录结果"""
        return await self.crud.update_status(
            db, task_id, "completed", result=result,
        )

    async def fail(
        self, db: AsyncSession, task_id: int, error_message: str
    ) -> Task | None:
        """任务执行失败，记录错误信息"""
        return await self.crud.update_status(
            db, task_id, "failed", error_message=error_message,
        )

    async def cancel(
        self, db: AsyncSession, task_id: int
    ) -> Task | None:
        """取消任务（只能取消排队中的任务）"""
        return await self.crud.update_status(db, task_id, "cancelled")
