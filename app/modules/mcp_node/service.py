"""
MCP 节点管理模块 - 业务逻辑层
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.mcp_node.crud import McpNodeCRUD, NodeServiceCRUD
from app.modules.mcp_node.models import McpNode, NodeService
from app.modules.mcp_node.schemas import (
    McpNodeCreate, McpNodeUpdate,
    NodeServiceCreate, NodeServiceUpdate,
)


class McpNodeService:
    """MCP 节点的业务逻辑"""

    def __init__(self):
        self.crud = McpNodeCRUD()

    async def get(self, db: AsyncSession, node_id: int) -> McpNode | None:
        return await self.crud.get_by_id(db, node_id)

    async def list(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20, keyword: str | None = None,
        status: bool | None = None, date_from: str | None = None, date_to: str | None = None
    ) -> tuple[list[McpNode], int]:
        return await self.crud.get_list(db, page=page, page_size=page_size, keyword=keyword, status=status, date_from=date_from, date_to=date_to)

    async def create(self, db: AsyncSession, data: McpNodeCreate) -> McpNode:
        return await self.crud.create(
            db,
            name=data.name,
            host=data.host,
            port=data.port,
            max_concurrent=data.max_concurrent,
            description=data.description,
            remark=data.remark,
        )

    async def update(
        self, db: AsyncSession, node_id: int, data: McpNodeUpdate
    ) -> McpNode | None:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return None
        return await self.crud.update(db, node_id, **updates)


class NodeServiceService:
    """节点服务的业务逻辑"""

    def __init__(self):
        self.crud = NodeServiceCRUD()

    async def get(self, db: AsyncSession, service_id: int) -> NodeService | None:
        return await self.crud.get_by_id(db, service_id)

    async def list_by_node(
        self, db: AsyncSession, node_id: int
    ) -> list[NodeService]:
        return await self.crud.get_by_node(db, node_id)

    async def list_public(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        keyword: str | None = None, status: bool | None = None,
        is_verified: bool | None = None,
        node_id: int | None = None,
        date_from: str | None = None, date_to: str | None = None,
    ) -> tuple[list[NodeService], int]:
        """服务列表：is_verified=None 查全部，True 查已审核，node_id 按节点过滤"""
        return await self.crud.get_public_services(
            db, page=page, page_size=page_size,
            keyword=keyword, status=status, is_verified=is_verified,
            node_id=node_id, date_from=date_from, date_to=date_to,
        )

    async def create(self, db: AsyncSession, data: NodeServiceCreate) -> NodeService:
        return await self.crud.create(
            db,
            node_id=data.node_id,
            service_name=data.service_name,
            service_type=data.service_type,
            price_per_call=data.price_per_call,
            description=data.description,
            version=data.version,
            params=data.params,
            cover_image=data.cover_image,
            remark=data.remark,
        )

    async def update(
        self, db: AsyncSession, service_id: int, data: NodeServiceUpdate
    ) -> NodeService | None:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return None
        return await self.crud.update(db, service_id, **updates)
