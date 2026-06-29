"""
定时任务
-------
- check_node_health：每隔 60 秒检查节点心跳，超时 120 秒标记离线
- check_user_expiry：每天凌晨检查用户月租是否到期
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from celery_worker.celery_app import celery_app
from app.config import settings


def _get_async_session():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task
def check_node_health():
    """检查节点心跳，超时节点标记为离线"""

    async def _run():
        from app.modules.mcp_node.models import McpNode
        from sqlalchemy import select, update

        factory = _get_async_session()
        async with factory() as db:
            # 超时 120 秒未心跳的节点标记离线
            timeout = datetime.utcnow() - timedelta(seconds=20)
            stmt = (
                update(McpNode)
                .where(
                    McpNode.node_status == "online",
                    McpNode.last_heartbeat < timeout,
                )
                .values(node_status="offline")
            )
            result = await db.execute(stmt)
            await db.commit()
            return {"offline_count": result.rowcount}

    return asyncio.run(_run())


@celery_app.task
def check_user_expiry():
    """检查用户月租到期（每天执行）"""

    async def _run():
        from app.modules.user.models import User
        from sqlalchemy import select, update

        factory = _get_async_session()
        async with factory() as db:
            now = datetime.utcnow()
            # 到期用户标记禁用
            stmt = (
                update(User)
                .where(
                    User.expire_date < now,
                    User.status == True,
                )
                .values(status=False)
            )
            result = await db.execute(stmt)
            await db.commit()
            return {"disabled_count": result.rowcount}

    return asyncio.run(_run())


# ===== 定时任务调度配置（在 Celery Beat 中使用） =====
CELERY_BEAT_SCHEDULE = {
    "check-node-health": {
        "task": "celery_worker.tasks.periodic.check_node_health",
        "schedule": 10.0,  # 每 10 秒检查一次
    },
    "check-user-expiry": {
        "task": "celery_worker.tasks.periodic.check_user_expiry",
        "schedule": timedelta(hours=24),  # 每 24 小时
    },
}
