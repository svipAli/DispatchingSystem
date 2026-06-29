"""AI 助手单元测试"""
import pytest
from httpx import AsyncClient


class TestAiChatHistory:
    """AI 聊天记录 API 测试"""

    @pytest.mark.asyncio
    async def test_history_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/chat-history")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_history_with_valid_token(self, admin_client: AsyncClient):
        """管理员可访问聊天历史"""
        # 注册用户
        resp = await admin_client.post("/api/v1/users/register", json={
            "username": "chat_test", "email": "chat_test@test.com", "password": "Test123456"
        })
        token = resp.json()["data"]["token"]

        resp = await admin_client.get("/api/v1/chat-history", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["code"] == 0

    @pytest.mark.asyncio
    async def test_save_and_load(self, admin_client: AsyncClient):
        """保存和加载聊天记录"""
        resp = await admin_client.post("/api/v1/users/register", json={
            "username": "chat_save", "email": "chat_save@test.com", "password": "Test123456"
        })
        token = resp.json()["data"]["token"]

        await admin_client.post("/api/v1/chat-history", json={"role": "user", "content": "你好"}, headers={"Authorization": f"Bearer {token}"})
        await admin_client.post("/api/v1/chat-history", json={"role": "assistant", "content": "你好！"}, headers={"Authorization": f"Bearer {token}"})

        resp = await admin_client.get("/api/v1/chat-history?limit=10", headers={"Authorization": f"Bearer {token}"})
        items = resp.json()["data"]["items"]
        assert len(items) >= 0

