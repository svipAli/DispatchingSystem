"""
MCP 节点管理模块 - API 路由

节点管理接口：
- GET    /api/v1/mcp-nodes               节点列表
- POST   /api/v1/mcp-nodes               添加节点
- GET    /api/v1/mcp-nodes/{id}          节点详情
- PUT    /api/v1/mcp-nodes/{id}          更新节点
- POST   /api/v1/mcp-nodes/heartbeat     节点心跳上报

服务管理接口：
- GET    /api/v1/mcp-services            公开服务列表（服务市场）
- GET    /api/v1/mcp-services/{id}       服务详情
- POST   /api/v1/mcp-services            创建服务
- PUT    /api/v1/mcp-services/{id}       更新服务（设置价格、审核）
- GET    /api/v1/mcp-nodes/{node_id}/services  某节点的服务列表
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, paginate, error
from app.core.ws_manager import node_manager
from app.dependencies import get_db, require_admin
from app.modules.mcp_node.schemas import (
    McpNodeCreate, McpNodeUpdate, McpNodeOut,
    NodeServiceCreate, NodeServiceUpdate, NodeServiceOut,
)
from app.modules.mcp_node.service import McpNodeService, NodeServiceService
from app.core.ws_manager import node_manager

async def _push_config(node_id: int):
    """推送配置同步到节点"""
    try:
        await node_manager.push_config_sync(node_id)
    except Exception:
        pass

router = APIRouter(prefix="/mcp-nodes", tags=["MCP 节点管理"])
node_svc = McpNodeService()
service_svc = NodeServiceService()

# 注册一个额外路由给服务管理（不同的前缀）
service_router = APIRouter(prefix="/mcp-services", tags=["MCP 服务管理"])


# ========== 节点管理 ==========


@router.get("")
async def list_nodes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    status: bool | None = Query(None),
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await node_svc.list(db, page=page, page_size=page_size, keyword=keyword, status=status, date_from=date_from, date_to=date_to)
    return paginate(
        [McpNodeOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.get("/{node_id}")
async def get_node(node_id: int, db: AsyncSession = Depends(get_db)):
    item = await node_svc.get(db, node_id)
    if not item:
        return error(code=404, message="节点不存在")
    return success(McpNodeOut.model_validate(item).model_dump())


@router.post("")
async def create_node(data: McpNodeCreate, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await node_svc.create(db, data)
    return success(McpNodeOut.model_validate(item).model_dump(), message="节点添加成功")
    await _push_config(node_id)


@router.put("/{node_id}")
async def update_node(node_id: int, data: McpNodeUpdate, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await node_svc.update(db, node_id, data)
    if not item:
        return error(code=404, message="节点不存在")
    return success(McpNodeOut.model_validate(item).model_dump(), message="更新成功")
    await _push_config(node_id)


@router.delete("/{node_id}", summary="删除节点")
async def delete_node(node_id: int, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await node_svc.get(db, node_id)
    if not item:
        return error(code=404, message="节点不存在")
    await node_svc.crud.delete(db, node_id, soft=False)
    return success(message="节点已删除")


@router.get("/{node_id}/services")
async def get_node_services(node_id: int, db: AsyncSession = Depends(get_db)):
    items = await service_svc.list_by_node(db, node_id)
    return success([NodeServiceOut.model_validate(item).model_dump() for item in items])


# ========== 服务管理（独立路由，会被 main.py 自动注册） ==========


@service_router.get("")
async def list_public_services(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    status: bool | None = Query(None),
    is_verified: bool | None = Query(None),
    node_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """服务列表：不传 is_verified 则查全部（管理端），传 true 则查已审核（用户端）"""
    items, total = await service_svc.list_public(db, page=page, page_size=page_size, keyword=keyword, status=status, is_verified=is_verified, node_id=node_id, date_from=date_from, date_to=date_to)
    return paginate(
        [NodeServiceOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@service_router.get("/{service_id}")
async def get_service(service_id: int, db: AsyncSession = Depends(get_db)):
    item = await service_svc.get(db, service_id)
    if not item:
        return error(code=404, message="服务不存在")
    return success(NodeServiceOut.model_validate(item).model_dump())


@service_router.post("")
async def create_service(data: NodeServiceCreate, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    data.price_per_call = round(data.price_per_call, 2)
    item = await service_svc.create(db, data)
    await _push_config(data.node_id)
    return success(NodeServiceOut.model_validate(item).model_dump(), message="服务创建成功")


@service_router.put("/{service_id}")
async def update_service(service_id: int, data: NodeServiceUpdate, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await service_svc.update(db, service_id, data)
    if not item:
        return error(code=404, message="服务不存在")
    await _push_config(item.node_id)
    return success(NodeServiceOut.model_validate(item).model_dump(), message="更新成功")


@service_router.delete("/{service_id}", summary="删除服务")
async def delete_service(service_id: int, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    item = await service_svc.get(db, service_id)
    if not item:
        return error(code=404, message="服务不存在")
    nid = item.node_id
    await service_svc.crud.delete(db, service_id, soft=False)
    await _push_config(nid)
    return success(message="服务已删除")


# 告诉 main.py 额外注册 service_router
extra_routers = [service_router]
