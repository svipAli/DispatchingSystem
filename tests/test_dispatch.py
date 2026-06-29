"""
Celery 调度任务单元测试
直接 await run_dispatch()，不依赖 Celery Worker
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.core.dispatch import run_dispatch


class TestDispatchFlow:
    """完整调度流程测试"""

    @pytest.mark.asyncio
    async def test_full_dispatch_flow(self, admin_client: AsyncClient, session_factory):
        """
        完整流程：创建节点 → 创建服务 → 审核 → 提交任务 → 调度执行 → 验证结果
        """

        from app.modules.user.crud import UserCRUD

        # 1. 注册用户并充值
        resp = await admin_client.post("/api/v1/users/register", json={
            "username": "dispatch_user", "email": "disp@test.com", "password": "Test123456",
        })
        uid = resp.json()["data"]["user"]["id"]
        user_token = resp.json()["data"]["token"]

        # 给用户充值 100 元（直接改库）
        async with session_factory() as db, db.begin():
            await UserCRUD().update(db, uid, balance=100.0)

        # 2. 创建节点
        resp = await admin_client.post("/api/v1/mcp-nodes", json={
            "name": "TestNode", "host": "10.0.0.1", "port": 8080, "max_concurrent": 5,
        })
        nid = resp.json()["data"]["id"]

        # 3. 创建服务并审核
        resp = await admin_client.post("/api/v1/mcp-services", json={
            "node_id": nid,
            "service_name": "代码执行",
            "service_type": "code-execution",
            "price_per_call": 0.05,
        })
        sid = resp.json()["data"]["id"]
        await admin_client.put(f"/api/v1/mcp-services/{sid}", json={"is_verified": True})

        # 4. 模拟节点在线
        async with session_factory() as db, db.begin():
            from app.modules.mcp_node.crud import McpNodeCRUD
            await McpNodeCRUD().update(db, nid, node_status="online", current_load=0)

        # 5. 用户提交任务
        resp = await admin_client.post("/api/v1/tasks", json={
            "service_type": "code-execution",
            "request_params": {"code": "print('hello')"},
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.json()["code"] == 0
        tid = resp.json()["data"]["id"]
        assert resp.json()["data"]["status"] == "queued"

        # 6. Mock WebSocket dispatch（测试环境无真实节点连接）
        mock_result = {"code": 0, "message": "success", "data": {"output": "hello"}}
        with patch("app.core.ws_manager.node_manager.dispatch_task", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = mock_result
            result = await run_dispatch(tid, session_factory)
        assert result["status"] == "completed"

        # 7. 验证任务状态
        resp = await admin_client.get(f"/api/v1/tasks/{tid}", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.json()["data"]["status"] == "completed"
        assert resp.json()["data"]["cost"] == 0.05
        assert resp.json()["data"]["result"]["code"] == 0

        # 8. 验证余额已扣
        resp = await admin_client.post("/api/v1/users/login", json={
            "username": "dispatch_user", "password": "Test123456",
        })
        assert resp.json()["data"]["user"]["balance"] == 99.95  # 100 - 0.05

        # 9. 验证流水记录
        resp = await admin_client.get("/api/v1/billing", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.json()["data"]["total"] == 1
        assert resp.json()["data"]["items"][0]["type"] == "deduct"

    @pytest.mark.asyncio
    async def test_no_available_node(self, admin_client: AsyncClient, session_factory):
        """没有可用节点时任务应标记为失败"""
        

        resp = await admin_client.post("/api/v1/users/register", json={
            "username": "nofail", "email": "nofail@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        resp = await admin_client.post("/api/v1/tasks", json={
            "service_type": "no-such-service",
        }, headers={"Authorization": f"Bearer {token}"})
        tid = resp.json()["data"]["id"]

        result = await run_dispatch(tid, session_factory)
        assert result["status"] == "failed"
        assert "无可用节点" in result["reason"]

    @pytest.mark.asyncio
    async def test_task_already_processed(self, admin_client: AsyncClient, session_factory):
        """已完成的任务再次调度应跳过"""
        
        from app.modules.task.service import TaskService
        from app.modules.task.schemas import TaskCreate

        resp = await admin_client.post("/api/v1/users/register", json={
            "username": "skipped", "email": "skip@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        resp = await admin_client.post("/api/v1/tasks", json={
            "service_type": "test-skip",
        }, headers={"Authorization": f"Bearer {token}"})
        tid = resp.json()["data"]["id"]

        # 先标记为已完成
        async with session_factory() as db, db.begin():
            svc = TaskService()
            await svc.complete(db, tid, {"manual": True})

        result = await run_dispatch(tid, session_factory)
        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_insufficient_balance(self, admin_client: AsyncClient, session_factory):
        """余额不足时应标记失败"""
        
        from app.modules.user.crud import UserCRUD

        # 创建节点和服务
        resp = await admin_client.post("/api/v1/mcp-nodes", json={
            "name": "PoorNode", "host": "10.0.0.99", "port": 8080,
        })
        nid = resp.json()["data"]["id"]
        resp = await admin_client.post("/api/v1/mcp-services", json={
            "node_id": nid, "service_name": "Expensive", "service_type": "expensive_svc",
            "price_per_call": 999.0,
        })
        sid = resp.json()["data"]["id"]
        await admin_client.put(f"/api/v1/mcp-services/{sid}", json={"is_verified": True})
        # 直接设置节点在线
        async with session_factory() as db, db.begin():
            from app.modules.mcp_node.crud import McpNodeCRUD
            await McpNodeCRUD().update(db, nid, node_status="online", current_load=0)

        # 注册用户（余额 0）
        resp = await admin_client.post("/api/v1/users/register", json={
            "username": "poor_user", "email": "poor@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        resp = await admin_client.post("/api/v1/tasks", json={
            "service_type": "expensive_svc",
        }, headers={"Authorization": f"Bearer {token}"})
        tid = resp.json()["data"]["id"]

        result = await run_dispatch(tid, session_factory)
        assert result["status"] == "failed"
        assert "余额不足" in result["reason"]
