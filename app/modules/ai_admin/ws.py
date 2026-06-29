"""AI 助手 WebSocket 端点 — Agent 模式，支持工具调用"""
import json, asyncio, httpx, os
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect

TOOLS = [
    {"type": "function", "function": {
        "name": "get_system_stats",
        "description": "获取系统运行统计：用户数、在线节点数、今日任务数、今日收入",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "get_node_list",
        "description": "获取所有 MCP 节点的运行状态列表",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "get_recent_tasks",
        "description": "获取最近的 N 条任务记录",
        "parameters": {"type": "object", "properties": {
            "limit": {"type": "integer", "description": "返回条数，默认10"}
        }}
    }},
    {"type": "function", "function": {
        "name": "get_db_stats",
        "description": "获取数据库表的数据统计（任务总数、流水总额、文件数等）",
        "parameters": {"type": "object", "properties": {}}
    }},
]


async def execute_tool(name: str, args: dict, websocket: WebSocket) -> str:
    """执行工具调用，返回结果字符串"""
    factory = websocket.app.state.db_session_factory
    from sqlalchemy import select, func

    try:
        if name == "get_system_stats":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            async with factory() as db:
                from app.modules.user.models import User
                from app.modules.task.models import Task
                from app.modules.mcp_node.models import McpNode
                from app.modules.billing.models import BillingRecord
                users = (await db.execute(select(func.count(User.id)).where(User.status==True))).scalar() or 0
                nodes = (await db.execute(select(func.count(McpNode.id)).where(McpNode.node_status=="online"))).scalar() or 0
                tasks = (await db.execute(select(func.count(Task.id)).where(Task.created_at>=today))).scalar() or 0
                completed = (await db.execute(select(func.count(Task.id)).where(Task.created_at>=today, Task.status=="completed"))).scalar() or 0
                revenue = (await db.execute(select(func.coalesce(func.sum(BillingRecord.amount),0)).where(
                    BillingRecord.created_at>=today, BillingRecord.type=="deduct"))).scalar() or 0
            return json.dumps({"total_users": users, "online_nodes": nodes, "today_tasks": tasks, "today_completed": completed, "today_revenue": round(float(revenue),2)}, ensure_ascii=False)

        elif name == "get_node_list":
            async with factory() as db:
                from app.modules.mcp_node.models import McpNode
                result = await db.execute(select(McpNode).where(McpNode.status==True).order_by(McpNode.id))
                nodes = [{"id": n.id, "name": n.name, "status": n.node_status, "load": f"{n.current_load}/{n.max_concurrent}", "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else "从未"} for n in result.scalars()]
            return json.dumps(nodes, ensure_ascii=False)

        elif name == "get_recent_tasks":
            limit = min(args.get("limit", 10), 50)
            async with factory() as db:
                from app.modules.task.models import Task
                result = await db.execute(select(Task).order_by(Task.id.desc()).limit(limit))
                tasks = [{"id": t.id, "service_type": t.service_type, "status": t.status, "cost": t.cost, "created": t.created_at.isoformat()} for t in result.scalars()]
            return json.dumps(tasks, ensure_ascii=False)

        elif name == "get_db_stats":
            async with factory() as db:
                from app.modules.task.models import Task
                from app.modules.user.models import User
                from app.modules.billing.models import BillingRecord
                from app.modules.file_record.models import FileRecord
                total_tasks = (await db.execute(select(func.count(Task.id)))).scalar() or 0
                total_users = (await db.execute(select(func.count(User.id)).where(User.status==True))).scalar() or 0
                total_revenue = (await db.execute(select(func.coalesce(func.sum(BillingRecord.amount),0)).where(BillingRecord.type=="deduct"))).scalar() or 0
                total_files = (await db.execute(select(func.count(FileRecord.id)).where(FileRecord.status==True))).scalar() or 0
            return json.dumps({"total_tasks": total_tasks, "total_users": total_users, "total_revenue": round(float(total_revenue),2), "total_files": total_files}, ensure_ascii=False)

        return json.dumps({"error": f"未知工具: {name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_ai_chat(websocket: WebSocket):
    """管理员 AI Agent：鉴权 → 对话 → 工具调用 → 流式返回"""
    from app.core.security import decode_token
    from app.modules.user.crud import UserCRUD
    from app.modules.role.crud import RoleCRUD
    from app.modules.system_config.crud import SystemConfigCRUD
    from app.modules.ai_admin.crud import ChatCRUD

    token = websocket.query_params.get("token", "")
    payload = decode_token(token)
    if not payload: await websocket.close(code=4001, reason="Token 无效"); return

    async with websocket.app.state.db_session_factory() as db:
        user = await UserCRUD().get_by_id(db, int(payload["sub"]))
        if not user: await websocket.close(code=4001, reason="用户不存在"); return
        role_ids = await RoleCRUD().get_user_role_ids(db, user.id)
        is_admin = any((await RoleCRUD().get_by_id(db, rid)).code == "admin" for rid in role_ids) if False else False
        for rid in role_ids:
            r = await RoleCRUD().get_by_id(db, rid)
            if r and r.code == "admin": is_admin = True; break
        if not is_admin: await websocket.close(code=4003, reason="需要管理员权限"); return

    async with websocket.app.state.db_session_factory() as db:
        cfgs = await SystemConfigCRUD().get_all_grouped(db)
    ai_url = (cfgs.get("ai_api_url", "") or "https://api.deepseek.com/v1").rstrip("/")
    ai_key = cfgs.get("ai_api_key", "")
    ai_model = cfgs.get("ai_model", "") or "deepseek-chat"
    system_prompt = """你是 MCP 调度平台的运维助手。你的性格是专业、友好、简洁。

规则：
1. 用自然的中文对话，不要直接 dump 数据表
2. 查询数据后，用简短的话总结关键信息，必要时用 Markdown 表格
3. 发现异常时主动提醒管理员
4. 回复简洁，不要长篇大论"""

    if not ai_key: await websocket.accept(); await websocket.close(code=4000, reason="AI 未配置"); return
    await websocket.accept()

    messages = [{"role": "system", "content": system_prompt}]
    max_history = 20
    crud = ChatCRUD()

    async def save(role: str, content: str):
        try:
            async with websocket.app.state.db_session_factory() as db:
                await crud.add(db, user.id, role, content)
                await db.commit()
        except Exception: pass

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") != "chat":
                if data.get("type") == "stop": continue
                if data.get("type") == "ping": await websocket.send_json({"type":"pong"})
                if data.get("type") == "clear":
                    messages = [{"role": "system", "content": system_prompt}]
                    asyncio.create_task(_clear_history(user.id, websocket))
                    await websocket.send_json({"type":"cleared"})
                continue
            user_msg = data.get("message", "")
            if not user_msg: continue
            messages.append({"role": "user", "content": user_msg})
            asyncio.create_task(save("user", user_msg))
            if len(messages) > max_history * 2 + 1:
                messages = [messages[0]] + messages[-(max_history * 2):]

            # Agent 循环：AI 可能多次调用工具
            http = httpx.AsyncClient(timeout=120)
            try:
                while True:
                    resp = await http.post(
                        f"{ai_url}/chat/completions",
                        headers={"Authorization": f"Bearer {ai_key}", "Content-Type": "application/json"},
                        json={"model": ai_model, "messages": messages, "tools": TOOLS, "stream": False},
                    )
                    body = resp.json()
                    choice = body["choices"][0]
                    finish = choice.get("finish_reason", "stop")

                    if finish == "tool_calls":
                        msg = choice["message"]
                        messages.append(msg)
                        for tc in msg.get("tool_calls", []):
                            tool_name = tc["function"]["name"]
                            tool_args = json.loads(tc["function"].get("arguments", "{}"))
                            await websocket.send_json({"type": "status", "content": f"🔧 正在查询 {tool_name}..."})
                            result = await execute_tool(tool_name, tool_args, websocket)
                            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                    elif finish == "stop":
                        answer = choice["message"].get("content", "")
                        if answer:
                            # 流式输出
                            messages.append({"role": "assistant", "content": answer})
                            asyncio.create_task(save("assistant", answer))
                            # 模拟流式逐字输出
                            for i in range(0, len(answer), 3):
                                await websocket.send_json({"type": "chunk", "content": answer[i:i+3]})
                                await asyncio.sleep(0.01)
                        await websocket.send_json({"type": "done"})
                        break
                    else:
                        await websocket.send_json({"type": "error", "message": f"AI 异常: {finish}"})
                        break
            except Exception as e:
                await websocket.send_json({"type": "error", "message": f"请求失败: {e}"})
            finally:
                await http.aclose()

    except (WebSocketDisconnect, Exception):
        pass


async def _clear_history(user_id: int, websocket: WebSocket):
    """软删除用户所有聊天记录"""
    try:
        from app.modules.ai_admin.crud import ChatCRUD
        from app.modules.ai_admin.models import ChatMessage
        from sqlalchemy import update
        async with websocket.app.state.db_session_factory() as db:
            await db.execute(update(ChatMessage).where(ChatMessage.user_id == user_id).values(status=False))
            await db.commit()
    except Exception:
        pass
