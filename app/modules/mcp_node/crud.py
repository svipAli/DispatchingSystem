"""
MCP 节点管理模块 - 数据访问层
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.mcp_node.models import McpNode, NodeService


class McpNodeCRUD(BaseCRUD[McpNode]):
    def __init__(self):
        super().__init__(McpNode)

    async def get_online_nodes(self, db: AsyncSession) -> list[McpNode]:
        """获取所有在线的节点"""
        stmt = select(McpNode).where(
            McpNode.node_status == "online", McpNode.status == True
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_idle_node(self, db: AsyncSession, service_type: str) -> McpNode | None:
        """
        选择一台负载最低的在线节点来执行任务
        优先选择支持指定 service_type 且当前负载小于最大并发的节点
        """
        stmt = (
            select(McpNode)
            .join(NodeService, NodeService.node_id == McpNode.id)
            .where(
                McpNode.node_status == "online",
                McpNode.status == True,
                NodeService.service_type == service_type,
                NodeService.is_verified == True,
                NodeService.status == True,
                McpNode.current_load < McpNode.max_concurrent,
            )
            .order_by(McpNode.current_load.asc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_heartbeat(
        self, db: AsyncSession, node_id: int, load: int
    ):
        """更新节点心跳时间和当前负载"""
        await self.update(
            db, node_id,
            last_heartbeat=datetime.now(),
            current_load=load,
            node_status="online",
        )


class NodeServiceCRUD(BaseCRUD[NodeService]):
    def __init__(self):
        super().__init__(NodeService)

    async def get_by_node(
        self, db: AsyncSession, node_id: int
    ) -> list[NodeService]:
        """获取某个节点的所有服务"""
        stmt = select(NodeService).where(
            NodeService.node_id == node_id, NodeService.status == True
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_public_services(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        keyword: str | None = None, status: bool | None = None,
        is_verified: bool | None = None,
        node_id: int | None = None,
        date_from: str | None = None, date_to: str | None = None
    ) -> tuple[list[NodeService], int]:
        """服务列表：is_verified=None 查全部，True 查已审核，node_id 按节点过滤"""
        filters = {}
        if is_verified is not None:
            filters["is_verified"] = is_verified
        if node_id is not None:
            filters["node_id"] = node_id
        return await self.get_list(
            db, page=page, page_size=page_size,
            keyword=keyword, status=status,
            date_from=date_from, date_to=date_to, **filters,
        )

    async def ensure_service(
        self, db: AsyncSession, node_id: int, service_type: str
    ) -> tuple[bool, NodeService | None]:
        """
        确保服务类型存在：如果该节点还没有此服务类型，则自动创建（is_verified=False）
        返回 (是否新创建, 服务对象)
        """
        stmt = select(NodeService).where(
            NodeService.node_id == node_id,
            NodeService.service_type == service_type,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return False, existing
        created = await self.create(
            db,
            node_id=node_id,
            service_name=service_type,
            service_type=service_type,
            price_per_call=0.0,
            is_verified=False,
        )
        return True, created
