import pytest
from httpx import AsyncClient


class TestTask:
    """任务模块测试"""

    @pytest.mark.asyncio
    async def test_submit_task(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "tasker", "email": "tasker@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        resp = await client.post("/api/v1/tasks", json={
            "service_type": "text-generation",
            "request_params": {"prompt": "Hello"},
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["status"] == "queued"
        assert resp.json()["data"]["service_type"] == "text-generation"

    @pytest.mark.asyncio
    async def test_list_my_tasks(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "tsklister", "email": "tsklister@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        await client.post("/api/v1/tasks", json={"service_type": "t1"}, headers={"Authorization": f"Bearer {token}"})
        await client.post("/api/v1/tasks", json={"service_type": "t2"}, headers={"Authorization": f"Bearer {token}"})

        resp = await client.get("/api/v1/tasks", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["total"] == 2

    @pytest.mark.asyncio
    async def test_filter_by_status(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "filterer", "email": "filterer@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        await client.post("/api/v1/tasks", json={"service_type": "type_a"}, headers={"Authorization": f"Bearer {token}"})
        await client.post("/api/v1/tasks", json={"service_type": "type_b"}, headers={"Authorization": f"Bearer {token}"})

        resp = await client.get("/api/v1/tasks?status=queued", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["total"] == 2

        resp = await client.get("/api/v1/tasks?status=completed", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_get_task(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "getter", "email": "getter@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        created = await client.post("/api/v1/tasks", json={
            "service_type": "code-execution",
            "request_params": {"code": "print(1)"},
        }, headers={"Authorization": f"Bearer {token}"})
        tid = created.json()["data"]["id"]

        resp = await client.get(f"/api/v1/tasks/{tid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["request_params"] == {"code": "print(1)"}

    @pytest.mark.asyncio
    async def test_cancel_task(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "canceller", "email": "canceller@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        created = await client.post("/api/v1/tasks", json={"service_type": "s"}, headers={"Authorization": f"Bearer {token}"})
        tid = created.json()["data"]["id"]

        resp = await client.post(f"/api/v1/tasks/{tid}/cancel", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["code"] == 0

        resp = await client.get(f"/api/v1/tasks/{tid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cannot_cancel_running(self, client: AsyncClient, session_factory):
        """不能取消正在执行的任务"""
        from app.modules.task.schemas import TaskCreate
        from app.modules.task.service import TaskService
        from app.modules.mcp_node.crud import McpNodeCRUD

        resp = await client.post("/api/v1/users/register", json={
            "username": "runner", "email": "runner@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]
        uid = resp.json()["data"]["user"]["id"]

        # 创建一个节点
        async with session_factory() as db, db.begin():
            node_crud = McpNodeCRUD()
            node = await node_crud.create(db, name="TestNode", host="127.0.0.1", port=8080)

            svc = TaskService()
            task = await svc.submit(db, uid, TaskCreate(service_type="test"))
            await svc.dispatch(db, task.id, node_id=node.id, cost=0.05)
            tid = task.id

        resp = await client.post(f"/api/v1/tasks/{tid}/cancel", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["code"] == 1001

    @pytest.mark.asyncio
    async def test_cannot_access_others_task(self, client: AsyncClient):
        r1 = await client.post("/api/v1/users/register", json={
            "username": "owner", "email": "owner@test.com", "password": "Test123456",
        })
        t1 = r1.json()["data"]["token"]
        created = await client.post("/api/v1/tasks", json={"service_type": "s"}, headers={"Authorization": f"Bearer {t1}"})
        tid = created.json()["data"]["id"]

        r2 = await client.post("/api/v1/users/register", json={
            "username": "intruder", "email": "intruder@test.com", "password": "Test123456",
        })
        t2 = r2.json()["data"]["token"]

        resp = await client.get(f"/api/v1/tasks/{tid}", headers={"Authorization": f"Bearer {t2}"})
        assert resp.json()["code"] == 404

    @pytest.mark.asyncio
    async def test_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/tasks", json={"service_type": "s"})
        assert resp.status_code == 401
