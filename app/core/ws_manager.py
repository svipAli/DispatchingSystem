"""
WebSocket 连接管理
-----------------
管理 MCP 节点的 WebSocket 长连接：
- 心跳维持 + 在线状态追踪
- 任务下发（平台 → 节点）
- 结果回传（节点 → 平台）
"""
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict
from fastapi import WebSocket

logging.basicConfig(level=logging.INFO, format='%(asctime)s [WS] %(message)s', datefmt='%H:%M:%S')
ws_log = logging.getLogger(__name__)


class NodeManager:
    """MCP 节点连接管理器（全局单例）"""

    def __init__(self):
        self._nodes: Dict[int, WebSocket] = {}
        self._node_info: Dict[int, dict] = {}
        self._admin_clients: list[WebSocket] = []
        # task_id → Future，用于等待节点回传结果
        self._pending_tasks: Dict[int, asyncio.Future] = {}

    # ===== 节点连接管理 =====

    async def connect_node(self, node_id: int, ws: WebSocket, db_factory):
        await ws.accept()
        self._nodes[node_id] = ws
        self._node_info[node_id] = {"current_load": 0, "connected_at": datetime.now()}
        ws_log.info(f"节点 {node_id} 已连接（等待 hello 注册）")
        await self._update_db_status(node_id, "online", 0, db_factory)
        await self._notify_admins()
        # 处理节点发来的消息（心跳 + 结果回传）
        asyncio.create_task(self._handle_node_messages(node_id, ws, db_factory))

    async def _handle_node_messages(self, node_id: int, ws: WebSocket, db_factory):
        """循环接收节点消息"""
        try:
            while True:
                data = await ws.receive_json()
                msg_type = data.get("type", "heartbeat")

                if msg_type == "hello":
                    ws_log.info(f"节点 {node_id} 上报 hello: config={data.get('config',{})}, services={data.get('services',[])}")
                    cfg = data.get("config", {})
                    self._node_info[node_id]["config"] = cfg
                    await self._ensure_node_exists(node_id, ws, db_factory, cfg)
                    await self._sync_services(node_id, data.get("services", []), db_factory)

                elif msg_type == "config_sync":
                    # 节点请求同步配置，平台以数据库为准回传
                    sync_cfg = await self._get_platform_config(node_id, db_factory)
                    await ws.send_json(sync_cfg)

                elif msg_type == "result":
                    task_id = data.get("task_id")
                    if task_id and task_id in self._pending_tasks:
                        self._pending_tasks[task_id].set_result(data.get("result"))
                    info = self._node_info.get(node_id, {})
                    info["current_load"] = max(0, info.get("current_load", 1) - 1)

                elif msg_type == "heartbeat" or "load" in data:
                    self._node_info[node_id] = {
                        "current_load": data.get("load", 0),
                        "last_heartbeat": datetime.now(),
                        "metrics": data.get("metrics", {}),
                    }
                    # 存储 metrics 到 Redis（最近60条）
                    metrics = data.get("metrics", {})
                    if metrics:
                        try:
                            import json as _json
                            key = f"node_metrics:{node_id}"
                            d = dict(metrics)
                            d["_time"] = datetime.now().isoformat()
                            await ws.app.state.redis.lpush(key, _json.dumps(d))
                            await ws.app.state.redis.ltrim(key, 0, 59)
                        except Exception:
                            pass
                    # 如果带了 services，同步服务注册
                    services = data.get("services", [])
                    if services:
                        await self._sync_services(node_id, services, db_factory)
                    await self._update_db_status(node_id, "online", data.get("load", 0), db_factory)
                    await self._notify_admins()

        except Exception as e:
            ws_log.error(f"节点 {node_id} 消息循环错误: {e}", exc_info=True)
        finally:
            await self.disconnect_node(node_id, db_factory)

    async def disconnect_node(self, node_id: int, db_factory):
        ws_log.info(f"节点 {node_id} 已断开")
        self._nodes.pop(node_id, None)
        self._node_info.pop(node_id, None)
        # 取消该节点上所有待处理任务（还在等待 future 的）
        for tid, fut in list(self._pending_tasks.items()):
            if not fut.done():
                fut.set_result({"code": -1, "message": "节点已断开", "data": None})
        # 扫描该节点上所有 running 状态的任务，标记失败并退款
        await self._fail_running_tasks(node_id, db_factory)
        await self._update_db_status(node_id, "offline", 0, db_factory)
        await self._notify_admins()

    # ===== 任务下发 =====

    async def dispatch_task(self, node_id: int, task_id: int, service_type: str, request_params: dict) -> dict:
        """
        向指定节点下发任务，等待返回结果（超时 60 秒）
        返回: {"code": 0, "message": "success", "data": {...}}
        """
        ws = self._nodes.get(node_id)
        if not ws:
            return {"code": -1, "message": "节点不在线", "data": None}

        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_tasks[task_id] = future

        try:
            await ws.send_json({
                "type": "task",
                "task_id": task_id,
                "service_type": service_type,
                "request_params": request_params,
            })
            # 增加负载
            info = self._node_info.get(node_id, {})
            info["current_load"] = info.get("current_load", 0) + 1

            # 等待结果（超时 60 秒）
            result = await asyncio.wait_for(future, timeout=60)
            return result
        except asyncio.TimeoutError:
            return {"code": -1, "message": "任务执行超时", "data": None}
        finally:
            self._pending_tasks.pop(task_id, None)

    # ===== 配置同步 =====

    async def _get_platform_config(self, node_id: int, db_factory) -> dict:
        """读取平台数据库中的节点和服务配置（平台是权威数据源）"""
        from app.modules.mcp_node.crud import McpNodeCRUD, NodeServiceCRUD
        try:
            async with db_factory() as db:
                node = await McpNodeCRUD().get_by_id(db, node_id)
                services = await NodeServiceCRUD().get_by_node(db, node_id)
                return {
                    "type": "config_sync",
                    "config": {
                        "name": node.name,
                        "port": node.port,
                        "max_concurrent": node.max_concurrent,
                        "description": node.description or "",
                    } if node else {},
                    "services": [
                        {"name": s.service_name, "type": s.service_type,
                         "version": s.version or "", "description": s.description or "",
                         "params": s.params or [], "timeout": s.timeout or 300}
                        for s in services if s.status
                    ],
                }
        except Exception:
            return {"type": "config_sync", "config": {}, "services": []}

    # ===== 管理端 =====

    async def connect_admin(self, ws: WebSocket):
        await ws.accept()
        self._admin_clients.append(ws)
        await ws.send_json({
            "type": "snapshot",
            "nodes": [
                {"node_id": nid, "status": "online", "load": info["current_load"]}
                for nid, info in self._node_info.items()
            ]
        })

    async def disconnect_admin(self, ws: WebSocket):
        if ws in self._admin_clients:
            self._admin_clients.remove(ws)

    # ===== 配置推送 =====

    async def push_config_sync(self, node_id: int):
        """主动推送配置同步指令到节点"""
        ws = self._nodes.get(node_id)
        if ws:
            try:
                await ws.send_json({"type": "config_sync"})
                ws_log.info(f"已向节点 {node_id} 推送配置同步")
            except Exception:
                pass

    # ===== 内部方法 =====

    async def _sync_services(self, node_id: int, services: list, db_factory):
        """同步节点上报的服务列表：仅创建新服务，已有服务不覆盖管理端设置的任何内容"""
        from app.modules.mcp_node.crud import NodeServiceCRUD
        async with db_factory() as db:
            svc_crud = NodeServiceCRUD()
            for item in services:
                if isinstance(item, str):
                    await svc_crud.ensure_service(db, node_id, item)
                elif isinstance(item, dict):
                    service_type = item.get("type", "")
                    is_new, existing = await svc_crud.ensure_service(db, node_id, service_type)
                    if is_new and existing:
                        # 新创建的服务：写入节点上报的元数据
                        updates = {}
                        if item.get("name"):
                            updates["service_name"] = item["name"]
                        if item.get("version"):
                            updates["version"] = item["version"]
                        if item.get("description"):
                            updates["description"] = item["description"]
                        if item.get("params"):
                            updates["params"] = item["params"]
                            updates["original_params"] = item["params"]
                        if updates:
                            await svc_crud.update(db, existing.id, **updates)
                    elif existing and existing.original_params is None and item.get("params"):
                        # 已有服务但缺少 original_params 备份，补上（不覆盖当前 params）
                        await svc_crud.update(db, existing.id, original_params=item["params"])
            await db.commit()
        ws_log.info(f"节点 {node_id} 服务同步完成: {len(services)} 个服务")

    async def _ensure_node_exists(self, node_id: int, ws: WebSocket, db_factory, config: dict = None):
        """自动注册/更新节点，优先使用节点上报的配置"""
        from app.modules.mcp_node.crud import McpNodeCRUD
        from sqlalchemy import select
        from app.modules.mcp_node.models import McpNode
        async with db_factory() as db:
            crud = McpNodeCRUD()
            # 按 node_id（业务ID，非数据库主键）查找节点
            stmt = select(McpNode).where(McpNode.id == node_id)
            result = await db.execute(stmt)
            node = result.scalar_one_or_none()
            cfg = config or {}
            if not node:
                host = ws.client.host if ws.client else "unknown"
                await crud.create(
                    db,
                    id=node_id,
                    name=cfg.get("name", f"自动注册-{host}"),
                    host=host,
                    port=int(cfg.get("port", 0)),
                    max_concurrent=int(cfg.get("max_concurrent", 5)),
                    node_status="offline",
                    description=cfg.get("description", "节点自动注册"),
                )
                ws_log.info(f"节点 {node_id} 已自动创建: {cfg.get('name', 'unknown')}")
                await db.commit()
                # 节点已存在则不做更新，保留后台手动修改的内容

    async def _update_db_status(self, node_id: int, status: str, load: int, db_factory):
        try:
            async with db_factory() as db:
                from app.modules.mcp_node.crud import McpNodeCRUD
                crud = McpNodeCRUD()
                node = await crud.get_by_id(db, node_id)
                if node:
                    await crud.update(db, node_id, node_status=status, current_load=load, last_heartbeat=datetime.now())
                    await db.commit()
        except Exception:
            pass

    async def _fail_running_tasks(self, node_id: int, db_factory):
        """节点断连时，将该节点上所有 running 状态的任务标记为失败并退款"""
        from app.modules.task.crud import TaskCRUD
        from app.modules.user.crud import UserCRUD
        from app.modules.billing.service import BillingService
        try:
            async with db_factory() as db:
                task_crud = TaskCRUD()
                running_tasks, _ = await task_crud.get_by_node(db, node_id, page_size=1000)
                for task in running_tasks:
                    await task_crud.update_status(db, task.id, "failed", error_message="节点断连，任务中断")
                    if task.cost and task.cost > 0:
                        user_crud = UserCRUD()
                        user = await user_crud.get_by_id(db, task.user_id)
                        if user:
                            new_balance = user.balance + task.cost
                            await user_crud.update(db, task.user_id, balance=new_balance)
                            billing_svc = BillingService()
                            await billing_svc.create_record(
                                db, user_id=task.user_id, type_="refund",
                                amount=task.cost,
                                balance_before=user.balance,
                                balance_after=new_balance,
                                related_id=task.id, related_type="task",
                                remark=f"节点断连退款: {task.service_type}",
                            )
                    ws_log.info(f"节点断连，任务 {task.id} 已标记失败并退款")
                await db.commit()
        except Exception as e:
            ws_log.error(f"处理节点断连任务失败: {e}")

    async def _notify_admins(self):
        offline = []
        for ws in self._admin_clients[:]:
            try:
                nodes_data = [
                    {"node_id": nid, "status": "online", "load": info["current_load"]}
                    for nid, info in self._node_info.items()
                ]
                await ws.send_json({"type": "update", "nodes": nodes_data})
            except Exception:
                offline.append(ws)
        for ws in offline:
            self._admin_clients.remove(ws)


node_manager = NodeManager()
