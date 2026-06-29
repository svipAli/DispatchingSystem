import pytest
from httpx import AsyncClient


class TestUserAPI:
    """用户模块 API 接口测试"""

    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "Test123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["user"]["username"] == "newuser"
        assert data["data"]["token"] is not None
        assert "password_hash" not in data["data"]["user"]

    @pytest.mark.asyncio
    async def test_register_duplicate(self, client: AsyncClient):
        await client.post("/api/v1/users/register", json={
            "username": "dupuser",
            "email": "dup@example.com",
            "password": "Test123456",
        })
        resp = await client.post("/api/v1/users/register", json={
            "username": "dupuser",
            "email": "dup2@example.com",
            "password": "Test123456",
        })
        assert resp.json()["code"] == 1001

    @pytest.mark.asyncio
    async def test_login(self, client: AsyncClient):
        await client.post("/api/v1/users/register", json={
            "username": "loginuser",
            "email": "login@example.com",
            "password": "Test123456",
        })
        resp = await client.post("/api/v1/users/login", json={
            "username": "loginuser",
            "password": "Test123456",
        })
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["token"] is not None

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/api/v1/users/register", json={
            "username": "wrongpw",
            "email": "wrongpw@example.com",
            "password": "Test123456",
        })
        resp = await client.post("/api/v1/users/login", json={
            "username": "wrongpw",
            "password": "wrongpassword",
        })
        assert resp.json()["code"] == 1002

    @pytest.mark.asyncio
    async def test_login_disabled_user(self, client: AsyncClient, session_factory):
        from app.modules.user.schemas import UserRegisterIn
        from app.modules.user.service import UserService

        # 注册一个用户
        svc = UserService()
        async with session_factory() as db, db.begin():
            user = await svc.register(db, UserRegisterIn(
                username="disabled", email="disabled@example.com", password="Test123456",
            ))
            # 禁用
            await svc.set_status(db, user.id, False)

        # 尝试登录
        resp = await client.post("/api/v1/users/login", json={
            "username": "disabled",
            "password": "Test123456",
        })
        assert resp.json()["code"] == 1002

    @pytest.mark.asyncio
    async def test_get_me(self, client: AsyncClient):
        # 注册并获取 token
        resp = await client.post("/api/v1/users/register", json={
            "username": "meuser",
            "email": "me@example.com",
            "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        # 用 token 查自己的信息
        resp = await client.get("/api/v1/users/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["username"] == "meuser"

    @pytest.mark.asyncio
    async def test_get_me_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me")
        # FastAPI 的 HTTPBearer + HTTPException 返回 401
        assert resp.status_code == 401
        assert "请先登录" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_me(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "updateuser",
            "email": "update@example.com",
            "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        resp = await client.put("/api/v1/users/me", json={
            "real_name": "张三",
            "phone": "13800138000",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["real_name"] == "张三"
        assert resp.json()["data"]["phone"] == "13800138000"

    @pytest.mark.asyncio
    async def test_update_identity(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "iduser",
            "email": "id@example.com",
            "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        resp = await client.put("/api/v1/users/me/identity", json={
            "real_name": "李四",
            "id_card_number": "110101199001011234",
            "id_card_front_url": "/static/upload/front.jpg",
            "id_card_back_url": "/static/upload/back.jpg",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["real_name"] == "李四"
        assert resp.json()["data"]["id_card_number"] == "110101199001011234"
        assert resp.json()["data"]["is_verified"] is False  # 还没审核

    @pytest.mark.asyncio
    async def test_default_balance_zero(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "bal0",
            "email": "bal0@example.com",
            "password": "Test123456",
        })
        assert resp.json()["data"]["user"]["balance"] == 0.0
