"""
任务调度模块 - API 路由

用户端接口（需要登录）：
- GET  /api/v1/tasks                我的任务列表
- POST /api/v1/tasks                提交新任务
- GET  /api/v1/tasks/{id}           任务详情
- POST /api/v1/tasks/{id}/cancel    取消排队中的任务

后台管理接口（需要管理员权限，暂未加权限校验）：
- GET  /api/v1/tasks/node/{node_id} 查看某节点上的任务
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, paginate, error
from app.dependencies import get_db, get_current_user, require_admin
from app.modules.task.schemas import TaskCreate, TaskUpdate, TaskOut
from app.modules.task.service import TaskService

router = APIRouter(prefix="/tasks", tags=["任务管理"])
service = TaskService()


@router.get("", summary="我的任务列表")
async def list_my_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_by_user(
        db, current_user.id, page=page, page_size=page_size, status=status, keyword=keyword,
    )
    return paginate(
        [TaskOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.get("/admin", summary="全部任务列表（管理员）")
async def list_all_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    items, total = await service.list_all(db, page=page, page_size=page_size, status=status, keyword=keyword)
    return paginate(
        [TaskOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.get("/{task_id}", summary="任务详情")
async def get_task(
    task_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await service.get(db, task_id)
    if not item or item.user_id != current_user.id:
        return error(code=404, message="任务不存在")
    return success(TaskOut.model_validate(item).model_dump())


@router.post("", summary="提交任务")
async def submit_task(
    data: TaskCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await service.submit(db, current_user.id, data)
    # 异步调度：直接用 asyncio 在同一个进程里执行，共享 WS 连接
    import asyncio
    from app.core.dispatch import run_dispatch
    asyncio.create_task(run_dispatch(item.id))
    return success(
        TaskOut.model_validate(item).model_dump(), message="任务已提交，排队中"
    )


@router.post("/{task_id}/cancel", summary="取消任务")
async def cancel_task(
    task_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await service.get(db, task_id)
    if not item or item.user_id != current_user.id:
        return error(code=404, message="任务不存在")
    if item.status != "queued":
        return error(code=1001, message="只能取消排队中的任务")
    await service.cancel(db, task_id)
    return success(message="任务已取消")


@router.get("/node/{node_id}", summary="查看节点上的任务")
async def list_node_tasks(
    node_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    items, total = await service.crud.get_by_node(
        db, node_id, page=page, page_size=page_size,
    )
    return paginate(
        [TaskOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )
