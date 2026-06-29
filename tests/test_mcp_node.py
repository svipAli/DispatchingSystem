import pytest
from httpx import AsyncClient


class TestMcpNode:
    @pytest.mark.asyncio
    async def test_create_node(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/v1/mcp-nodes", json={
            "name": "GPU 服务器 01",
            "host": "192.168.1.100",
            "port": 8080,
            "max_concurrent": 10,
        })
        assert resp.json()["code"] == 0
        data = resp.json()["data"]
        assert data["name"] == "GPU 服务器 01"
        assert data["node_status"] == "offline"  # 默认离线

    @pytest.mark.asyncio
    async def test_list_nodes(self, admin_client: AsyncClient):
        await admin_client.post("/api/v1/mcp-nodes", json={
            "name": "N1", "host": "10.0.0.1", "port": 8080,
        })
        await admin_client.post("/api/v1/mcp-nodes", json={
            "name": "N2", "host": "10.0.0.2", "port": 8080,
        })
        resp = await admin_client.get("/api/v1/mcp-nodes")
        assert resp.json()["data"]["total"] >= 2

    @pytest.mark.asyncio
    async def test_get_node(self, admin_client: AsyncClient):
        created = await admin_client.post("/api/v1/mcp-nodes", json={
            "name": "NodeX", "host": "10.0.0.99", "port": 9090,
        })
        nid = created.json()["data"]["id"]
        resp = await admin_client.get(f"/api/v1/mcp-nodes/{nid}")
        assert resp.json()["data"]["host"] == "10.0.0.99"


class TestMcpService:
    @pytest.mark.asyncio
    async def test_create_service(self, admin_client: AsyncClient):
        node = await admin_client.post("/api/v1/mcp-nodes", json={
            "name": "SvcNode", "host": "10.0.0.70", "port": 8080,
        })
        nid = node.json()["data"]["id"]

        resp = await admin_client.post("/api/v1/mcp-services", json={
            "node_id": nid,
            "service_name": "文本生成服务",
            "service_type": "text-generation",
            "price_per_call": 0.05,
        })
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["price_per_call"] == 0.05

    @pytest.mark.asyncio
    async def test_list_public_services(self, admin_client: AsyncClient):
        node = await admin_client.post("/api/v1/mcp-nodes", json={
            "name": "PubNode", "host": "10.0.0.80", "port": 8080,
        })
        nid = node.json()["data"]["id"]

        # 创建并审核通过
        created = await admin_client.post("/api/v1/mcp-services", json={
            "node_id": nid, "service_name": "S1", "service_type": "type_a", "price_per_call": 0.1,
        })
        sid = created.json()["data"]["id"]
        await admin_client.put(f"/api/v1/mcp-services/{sid}", json={"is_verified": True})

        # 服务市场应该能看到
        resp = await admin_client.get("/api/v1/mcp-services")
        assert resp.json()["data"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_update_service(self, admin_client: AsyncClient):
        node = await admin_client.post("/api/v1/mcp-nodes", json={
            "name": "UpdNode", "host": "10.0.0.90", "port": 8080,
        })
        nid = node.json()["data"]["id"]
        created = await admin_client.post("/api/v1/mcp-services", json={
            "node_id": nid, "service_name": "Old", "service_type": "upd_test",
        })
        sid = created.json()["data"]["id"]

        resp = await admin_client.put(f"/api/v1/mcp-services/{sid}", json={
            "service_name": "New Name",
            "price_per_call": 0.99,
            "is_verified": True,
        })
        assert resp.json()["data"]["service_name"] == "New Name"
        assert resp.json()["data"]["price_per_call"] == 0.99
        assert resp.json()["data"]["is_verified"] is True
