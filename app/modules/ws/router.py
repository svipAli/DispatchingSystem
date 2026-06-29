"""
WebSocket 路由模块
-----------------
节点连接 /ws/node/{node_id}：MCP 节点维持心跳 + 接收任务 + 回传结果
管理端连接 /ws/admin：实时接收节点状态推送
AI 助手连接 /ws/admin/ai → app.modules.ai_admin.ws
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/node/{node_id}")
async def ws_node(websocket: WebSocket, node_id: int):
    from app.core.ws_manager import node_manager
    factory = websocket.app.state.db_session_factory
    try:
        await node_manager.connect_node(node_id, websocket, factory)
        while True:
            await asyncio.sleep(3600)
    except (WebSocketDisconnect, Exception):
        pass


@router.websocket("/ws/admin")
async def ws_admin(websocket: WebSocket):
    from app.core.ws_manager import node_manager
    await node_manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        await node_manager.disconnect_admin(websocket)


@router.websocket("/ws/admin/ai")
async def ws_admin_ai(websocket: WebSocket, token: str = Query(...)):
    from app.modules.ai_admin.ws import handle_ai_chat
    await handle_ai_chat(websocket)
