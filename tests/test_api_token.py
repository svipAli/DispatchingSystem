import pytest
from httpx import AsyncClient


class TestApiToken:
    @pytest.mark.asyncio
    async def test_create_token(self, client: AsyncClient):
        # 注册登录
        resp = await client.post("/api/v1/users/register", json={
            "username": "tokener", "email": "tokener@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        # 创建 API Token
        resp = await client.post("/api/v1/api-tokens", json={
            "name": "我的开发环境",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["code"] == 0
        data = resp.json()["data"]
        assert data["name"] == "我的开发环境"
        assert len(data["token"]) > 50  # JWT token is long

    @pytest.mark.asyncio
    async def test_list_my_tokens(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "lister", "email": "lister@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        await client.post("/api/v1/api-tokens", json={"name": "T1"}, headers={"Authorization": f"Bearer {token}"})
        await client.post("/api/v1/api-tokens", json={"name": "T2"}, headers={"Authorization": f"Bearer {token}"})

        resp = await client.get("/api/v1/api-tokens", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["total"] == 2

    @pytest.mark.asyncio
    async def test_revoke_token(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "revolker", "email": "revolker@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        created = await client.post("/api/v1/api-tokens", json={"name": "T1"}, headers={"Authorization": f"Bearer {token}"})
        tid = created.json()["data"]["id"]

        resp = await client.delete(f"/api/v1/api-tokens/{tid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["code"] == 0

        # 查列表应该只有 0 个启用
        resp = await client.get("/api/v1/api-tokens", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_cannot_access_others_token(self, client: AsyncClient):
        # 用户 A
        r1 = await client.post("/api/v1/users/register", json={
            "username": "userA", "email": "a@test.com", "password": "Test123456",
        })
        t1 = r1.json()["data"]["token"]
        created = await client.post("/api/v1/api-tokens", json={"name": "A-Token"}, headers={"Authorization": f"Bearer {t1}"})
        tid = created.json()["data"]["id"]

        # 用户 B 尝试改 A 的 Token
        r2 = await client.post("/api/v1/users/register", json={
            "username": "userB", "email": "b@test.com", "password": "Test123456",
        })
        t2 = r2.json()["data"]["token"]

        resp = await client.put(f"/api/v1/api-tokens/{tid}", json={"name": "hacked!"}, headers={"Authorization": f"Bearer {t2}"})
        assert resp.json()["code"] == 404

    @pytest.mark.asyncio
    async def test_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/api-tokens")
        assert resp.status_code == 401
