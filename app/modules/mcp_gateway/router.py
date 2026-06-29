"""
MCP Gateway — 对外暴露标准 MCP 协议接口

Dify 智能体通过此接口连接平台，将平台服务作为 MCP Tools 暴露。

端点：
- GET  /mcp/sse        SSE 长连接（Authorization: Bearer <token>）
- POST /mcp/messages   JSON-RPC 消息处理（?sessionId=xxx）
"""
import json
import asyncio
import logging
from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import StreamingResponse, Response, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.modules.mcp_gateway.session import session_manager, MCPSession
from app.core.security import decode_token

logger = logging.getLogger(__name__)

mcp_router = APIRouter(prefix="/mcp", tags=["MCP Gateway"])


# ========== Token 验证 ==========

async def _verify_token(request: Request, db_factory) -> int | None:
    """
    验证 MCP Token：
    1. JWT 本地解密
    2. type 必须为 "mcp"
    3. 检查 Redis 黑名单（jti 是否被撤销）
    返回 user_id 或 None
    """
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        return None

    payload = decode_token(token)
    if payload is None:
        return None

    if payload.get("type") != "mcp":
        return None

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id:
        return None

    # 检查 Redis 黑名单
    if jti:
        redis = request.app.state.redis
        if await redis.get(f"token_revoked:{jti}"):
            return None

    return int(user_id)


# ========== SSE 端点 ==========

@mcp_router.get("/sse")
async def mcp_sse(request: Request):
    """SSE 连接端点，维持长连接用于推送消息"""
    db_factory = request.app.state.db_session_factory
    user_id = await _verify_token(request, db_factory)
    if user_id is None:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    session_id = session_manager.create(user_id, db_factory)
    base_url = str(request.base_url).rstrip("/")
    messages_url = f"{base_url}/mcp/messages?sessionId={session_id}"
    logger.info(f"MCP SSE 会话创建: session={session_id[:8]}.. user={user_id}")

    async def event_stream():
        try:
            yield f"event: endpoint\ndata: {messages_url}\n\n"

            sess = session_manager.get(session_id)
            if not sess:
                return

            while True:
                try:
                    msg = await asyncio.wait_for(sess.queue.get(), timeout=30)
                    yield f"event: message\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        except (asyncio.CancelledError, ConnectionError):
            pass
        finally:
            session_manager.remove(session_id)
            logger.info(f"MCP SSE 会话关闭: session={session_id[:8]}..")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ========== JSON-RPC 消息端点 ==========

@mcp_router.post("/messages")
async def mcp_messages(request: Request, sessionId: str = Query(...)):
    """处理 JSON-RPC 消息，结果通过 SSE 推回"""
    session = session_manager.get(sessionId)
    if not session:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Session not found"}},
            status_code=404,
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )

    request_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    # 异步处理，不阻塞 POST 返回
    asyncio.create_task(_handle_method(session, method, params, request_id))

    return Response(status_code=202)


async def _handle_method(session: MCPSession, method: str, params: dict, request_id):
    """处理 JSON-RPC 方法，结果推入 SSE 队列"""
    result = None
    error = None

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "DispatchingSystem", "version": "1.0.0"},
            }
        elif method == "notifications/initialized":
            return  # 客户端初始化完成通知，无需回复
        elif method == "tools/list":
            result = await _list_tools(session)
        elif method == "tools/call":
            result = await _call_tool(session, params)
        else:
            error = {"code": -32601, "message": f"Method not found: {method}"}
    except Exception as e:
        logger.error(f"MCP 方法处理异常: {method}: {e}", exc_info=True)
        error = {"code": -32603, "message": str(e)}

    if request_id is not None:
        resp = {"jsonrpc": "2.0", "id": request_id}
        if error:
            resp["error"] = error
        else:
            resp["result"] = result
        await session.push(resp)


# ========== 工具实现 ==========

async def _list_tools(session: MCPSession) -> dict:
    """列出所有已审核上线的服务，作为 MCP Tool"""
    from app.modules.mcp_node.crud import NodeServiceCRUD

    async with session.db_factory() as db:
        svc_crud = NodeServiceCRUD()
        services, _ = await svc_crud.get_public_services(
            db, page_size=1000, is_verified=True, status=True
        )

    # 去重：同一 service_type 只列一次
    seen = set()
    tools = []
    # Python 类型 → JSON Schema 类型映射
    type_map = {"int": "integer", "float": "number", "bool": "boolean", "list": "array", "dict": "object"}
    for s in services:
        if s.service_type in seen:
            continue
        seen.add(s.service_type)

        # 组装 inputSchema
        properties = {}
        required = []
        if s.params:
            for p in s.params:
                prop = {}
                raw_type = p.get("type", "string")
                prop["type"] = type_map.get(raw_type, raw_type)
                prop["description"] = p.get("label") or p.get("description") or ""
                if "default" in p and p["default"] is not None:
                    prop["default"] = p["default"]
                properties[p["field"]] = prop
                if p.get("required"):
                    required.append(p["field"])

        tools.append({
            "name": s.service_type,
            "description": f"{s.service_name} — ¥{s.price_per_call}/次 | {s.description or ''}",
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        })

    # 额外加一个 query_task 工具，用于轮询任务结果
    tools.append({
        "name": "query_task",
        "description": "查询异步任务的执行结果。提交任务后会返回 task_id，使用此工具查询最终结果。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "任务 ID"}
            },
            "required": ["task_id"],
        },
    })

    return {"tools": tools}


async def _call_tool(session: MCPSession, params: dict) -> dict:
    """调用工具：创建任务，由异步调度器完成扣费+下发+执行"""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})
    service_type = arguments.get("service_type", tool_name)

    if not service_type:
        return _tool_error("缺少 service_type 参数")

    # query_task 特殊处理：查询已有任务状态
    if service_type == "query_task":
        task_id = arguments.get("task_id")
        if not task_id:
            return _tool_error("缺少 task_id 参数")
        return await _query_task(session, int(task_id))

    task_input = {k: v for k, v in arguments.items() if k != "service_type"}

    async with session.db_factory() as db:
        from app.modules.task.service import TaskService
        from app.modules.mcp_node.crud import McpNodeCRUD
        from app.modules.user.crud import UserCRUD

        task_svc = TaskService()

        # 1. 快速检查：是否至少有一个可用节点支持此服务
        node_crud = McpNodeCRUD()
        node = await node_crud.get_idle_node(db, service_type)
        if not node:
            fail_task = await task_svc.crud.create(
                db,
                user_id=session.user_id,
                service_type=service_type,
                request_params={"input": task_input, "options": {"source": "mcp_gateway"}},
                status="failed",
                error_message=f"服务 {service_type} 暂无可用执行节点",
            )
            await db.commit()
            return _tool_error(f"服务 {service_type} 暂无可用执行节点", task_id=fail_task.id)

        # 2. 获取服务价格和超时
        from app.modules.mcp_node.crud import NodeServiceCRUD
        svc_crud = NodeServiceCRUD()
        services = await svc_crud.get_by_node(db, node.id)
        cost = 0.0
        timeout = 60  # 默认60秒
        for s in services:
            if s.service_type == service_type and s.is_verified:
                cost = s.price_per_call
                timeout = s.timeout or 300
                break

        # 余额预检
        if cost > 0:
            user_crud = UserCRUD()
            user = await user_crud.get_by_id(db, session.user_id)
            if not user:
                return _tool_error("用户不存在")
            if user.balance < cost:
                fail_task = await task_svc.crud.create(
                    db,
                    user_id=session.user_id,
                    service_type=service_type,
                    request_params={"input": task_input, "options": {"source": "mcp_gateway"}},
                    status="failed",
                    error_message=f"余额不足，需要 ¥{cost:.2f}，当前 ¥{user.balance:.2f}",
                )
                await db.commit()
                return _tool_error(
                    f"余额不足，需要 ¥{cost:.2f}，当前 ¥{user.balance:.2f}",
                    task_id=fail_task.id,
                    required=cost,
                    balance=user.balance,
                )

        # 3. 创建任务
        task = await task_svc.crud.create(
            db,
            user_id=session.user_id,
            service_type=service_type,
            request_params={"input": task_input, "options": {"source": "mcp_gateway"}},
            status="queued",
        )
        task_id = task.id
        await db.commit()

    # 4. 根据超时决定同步还是异步
    from app.core.dispatch import run_dispatch

    if timeout <= 60:
        # 短任务：同步等待结果，直接返回
        dispatch_result = await run_dispatch(task_id, session.db_factory)

        async with session.db_factory() as db:
            from app.modules.task.crud import TaskCRUD
            task = await TaskCRUD().get_by_id(db, task_id)

            if task and task.status == "completed":
                return _tool_success({
                    "task_id": task.id,
                    "status": "completed",
                    "result": task.result,
                    "cost": task.cost,
                })
            else:
                error_msg = getattr(task, 'error_message', None) if task else None
                return _tool_error(error_msg or "任务执行失败")

    else:
        # 长任务：异步，立即返回 task_id，由 AI 用 query_task 轮询
        asyncio.create_task(run_dispatch(task_id, session.db_factory))

        return _tool_success({
            "task_id": task_id,
            "status": "queued",
            "service_type": service_type,
            "estimated_cost": cost,
            "timeout_seconds": timeout,
            "message": f"任务已提交，预计耗时较长（{timeout}秒），请使用 query_task 查询执行结果",
        })


async def _query_task(session: MCPSession, task_id: int) -> dict:
    """查询任务执行结果"""
    async with session.db_factory() as db:
        from app.modules.task.crud import TaskCRUD
        task = await TaskCRUD().get_by_id(db, task_id)
        if not task:
            return _tool_error(f"任务 {task_id} 不存在")
        if task.user_id != session.user_id:
            return _tool_error("无权查询此任务")

        status_map = {"queued": "排队中", "running": "执行中", "completed": "已完成", "failed": "失败", "cancelled": "已取消"}

        if task.status == "completed":
            return _tool_success({
                "task_id": task.id,
                "status": "completed",
                "result": task.result,
                "cost": task.cost,
            })
        elif task.status in ("failed", "cancelled"):
            return _tool_error(f"任务{status_map.get(task.status, task.status)}: {getattr(task, 'error_message', '') or '无详细信息'}")
        else:
            return _tool_success({
                "task_id": task.id,
                "status": task.status,
                "status_text": status_map.get(task.status, task.status),
                "message": "任务尚未完成，请稍后再查询",
            })


def _tool_error(message: str, **extra) -> dict:
    data = {"code": -1, "message": message}
    data.update(extra)
    return {
        "content": [{
            "type": "text",
            "text": json.dumps(data, ensure_ascii=False),
        }],
    }


def _tool_success(data: dict) -> dict:
    return {
        "content": [{
            "type": "text",
            "text": json.dumps({"code": 0, "message": "success", **data}, ensure_ascii=False),
        }],
    }
