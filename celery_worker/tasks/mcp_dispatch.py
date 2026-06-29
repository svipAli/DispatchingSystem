"""
MCP 任务调度 Celery 任务
------------------------
完整的异步调度流程：
1. 收到新任务 → dispatch_task.delay(task_id)
2. Celery Worker 选节点 → 发送请求 → 等结果
3. 更新任务状态 → 扣费 → 写流水

当前版本：模拟 MCP 节点执行（因为没有真实节点连接）
后续可替换为真实的 HTTP 请求到 MCP 节点。
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from celery_worker.celery_app import celery_app
from app.config import settings


def _get_async_session():
    """创建异步数据库会话"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def dispatch_task(self, task_id: int):
    """
    核心调度任务：将排队中的任务分配到 MCP 节点执行

    流程：
    1. 查询任务信息
    2. 选择负载最低的可用节点（支持该服务类型）
    3. 更新任务状态为 running
    4. 模拟执行（后续替换为真实 HTTP 调用）
    5. 更新任务结果 + 扣费
    """
    async def _run():
        from app.modules.task.service import TaskService
        from app.modules.task.schemas import TaskCreate
        from app.modules.mcp_node.crud import McpNodeCRUD, NodeServiceCRUD
        from app.modules.user.crud import UserCRUD
        from app.modules.billing.service import BillingService

        factory = _get_async_session()

        async with factory() as db:
            try:
                task_svc = TaskService()
                task = await task_svc.get(db, task_id)

                if task is None or task.status != "queued":
                    return {"status": "skipped", "reason": "任务不在排队状态"}

                # 1. 选择节点
                node_crud = McpNodeCRUD()
                node = await node_crud.get_idle_node(db, task.service_type)

                if node is None:
                    # 没有可用节点，标记失败
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

                # 3. 更新任务状态为 running
                await task_svc.dispatch(db, task_id, node.id, cost)

                # 4. 增加节点负载
                await node_crud.update_heartbeat(
                    db, node.id, node.current_load + 1
                )

                # 5. 模拟执行（实际项目中这里发 HTTP 请求到 MCP 节点）
                # TODO: 替换为真实的 MCP 调用
                result = {
                    "status": "ok",
                    "message": f"任务 {task_id} 在节点 {node.name} 上执行完成",
                    "service_type": task.service_type,
                    "executed_at": datetime.utcnow().isoformat(),
                }

                # 6. 标记完成
                await task_svc.complete(db, task_id, result)

                # 7. 减少节点负载
                await node_crud.update_heartbeat(
                    db, node.id, max(0, node.current_load)
                )

                # 8. 扣费 + 写流水
                if cost > 0:
                    user_crud = UserCRUD()
                    user = await user_crud.get_by_id(db, task.user_id)
                    balance_before = user.balance
                    balance_after = balance_before - cost

                    # 余额不足
                    if balance_after < 0:
                        await task_svc.fail(db, task_id, "余额不足")
                        await db.commit()
                        return {"status": "failed", "reason": "余额不足"}

                    # 扣余额
                    await user_crud.update(db, task.user_id, balance=balance_after)

                    # 写流水
                    billing_svc = BillingService()
                    await billing_svc.create_record(
                        db,
                        user_id=task.user_id,
                        type_="deduct",
                        amount=cost,
                        balance_before=balance_before,
                        balance_after=balance_after,
                        related_id=task_id,
                        related_type="task",
                        remark=f"调用 {task.service_type}",
                    )

                await db.commit()
                return {"status": "completed", "task_id": task_id, "node": node.name}

            except Exception as exc:
                await db.rollback()
                # 重试
                raise self.retry(exc=exc)

    return asyncio.run(run_dispatch(task_id))


async def run_dispatch(task_id: int, session_factory=None) -> dict:
    """
    异步版本的调度函数（供测试和内部调用直接 await）
    不依赖 Celery 装饰器和 asyncio.run()

    :param task_id: 任务 ID
    :param session_factory: 可选的数据库会话工厂，用于测试注入。不传则自动创建。
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

        # 3. 预扣费（先扣，失败再退）
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

        # 5. 通过 WebSocket 下发任务到节点
        from app.core.ws_manager import node_manager
        params = task.request_params or {}
        result = await node_manager.dispatch_task(
            node.id, task_id, task.service_type, params
        )

        # 6. 根据结果处理
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
                # 退款
                await user_crud.update(db, task.user_id, balance=balance_before)
                await billing_svc.create_record(db, user_id=task.user_id, type_="refund",
                    amount=cost, balance_before=balance_before - cost,
                    balance_after=balance_before,
                    related_id=task_id, related_type="task",
                    remark=f"任务失败退款: {task.service_type}")

        await db.commit()
        return {"status": "completed" if result.get("code") == 0 else "failed", "task_id": task_id}
