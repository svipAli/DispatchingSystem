"""
MCP 任务调度引擎
---------------
完整的异步调度流程：
1. 选择负载最低的可用节点
2. 预扣费（余额不足直接失败）
3. 更新任务状态为 running
4. 通过 WebSocket 下发任务
5. 等待结果（60s 超时）
6. 根据结果完成/失败 + 扣费/退款
"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings


def _get_async_session():
    """创建异步数据库会话"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


async def run_dispatch(task_id: int, session_factory=None) -> dict:
    """
    异步调度函数：将排队中的任务分配到 MCP 节点执行
    :param task_id: 任务 ID
    :param session_factory: 可选的数据库会话工厂
    """
    from app.modules.task.service import TaskService
    from app.modules.mcp_node.crud import McpNodeCRUD, NodeServiceCRUD
    from app.modules.user.crud import UserCRUD
    from app.modules.billing.service import BillingService

    if session_factory is None:
        session_factory = _get_async_session()

    async with session_factory() as db:
        task_svc = TaskService()
        task = await task_svc.get(db, task_id)

        if task is None or task.status != "queued":
            return {"status": "skipped", "reason": "任务不在排队状态"}

        # 1. 选择节点
        node_crud = McpNodeCRUD()
        node = await node_crud.get_idle_node(db, task.service_type)
        if node is None:
            await task_svc.fail(db, task_id, "没有可用的 MCP 节点")
            await db.commit()
            return {"status": "failed", "reason": "无可用节点"}

        # 2. 获取服务价格
        svc_crud = NodeServiceCRUD()
        services = await svc_crud.get_by_node(db, node.id)
        cost = 0.0
        for s in services:
            if s.service_type == task.service_type and s.is_verified:
                cost = s.price_per_call
                break

        # 3. 预扣费
        if cost > 0:
            user_crud = UserCRUD()
            user = await user_crud.get_by_id(db, task.user_id)
            balance_before = user.balance
            if balance_before < cost:
                await task_svc.fail(db, task_id, "余额不足")
                await db.commit()
                return {"status": "failed", "reason": "余额不足"}
            await user_crud.update(db, task.user_id, balance=balance_before - cost)

        # 4. 更新任务状态为 running
        await task_svc.dispatch(db, task_id, node.id, cost)
        await db.commit()

        # 5. WebSocket 下发
        from app.core.ws_manager import node_manager
        params = task.request_params or {}
        result = await node_manager.dispatch_task(node.id, task_id, task.service_type, params)

        # 6. 处理结果
        billing_svc = BillingService()
        if result.get("code") == 0:
            await task_svc.complete(db, task_id, result)
            if cost > 0:
                await billing_svc.create_record(db, user_id=task.user_id, type_="deduct",
                    amount=cost, balance_before=balance_before,
                    balance_after=balance_before - cost,
                    related_id=task_id, related_type="task",
                    remark=f"调用 {task.service_type}")
        else:
            await task_svc.fail(db, task_id, result.get("message", "执行失败"))
            if cost > 0:
                await user_crud.update(db, task.user_id, balance=balance_before)
                await billing_svc.create_record(db, user_id=task.user_id, type_="refund",
                    amount=cost, balance_before=balance_before - cost,
                    balance_after=balance_before,
                    related_id=task_id, related_type="task",
                    remark=f"任务失败退款: {task.service_type}")

        await db.commit()
        return {"status": "completed" if result.get("code") == 0 else "failed", "task_id": task_id}
