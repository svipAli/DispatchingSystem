"""MCP 网关单元测试"""
import pytest
from httpx import AsyncClient
import httpx


class TestMcpGateway:
    """MCP 网关 API 测试"""

    @pytest.mark.asyncio
    async def test_sse_rejects_no_token(self, client: AsyncClient):
        resp = await client.get("/mcp/sse")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_sse_rejects_login_token(self, client: AsyncClient):
        """登录 Token (type=login) 不能用于 MCP"""
        from app.core.security import create_access_token
        token = create_access_token(1)
        resp = await client.get("/mcp/sse", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_sse_accepts_mcp_token(self, client: AsyncClient):
        """MCP Token 可以连 SSE"""
        import uuid
        from app.core.security import create_mcp_token
        token = create_mcp_token(1, uuid.uuid4().hex)
        # 用 stream 避免阻塞
        async with httpx.AsyncClient(base_url="http://test") as c:
            async with c.stream("GET", f"{client.base_url}/mcp/sse", headers={"Authorization": f"Bearer {token}"}) as resp:
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_messages_rejects_no_session(self, client: AsyncClient):
        resp = await client.post("/mcp/messages?sessionId=fake123", json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mcp_token_blacklist(self, admin_client: AsyncClient):
        """撤销 Token 后应被拒绝"""
        import uuid
        from app.core.security import create_mcp_token
        from redis.asyncio import Redis

        jti = uuid.uuid4().hex
        token = create_mcp_token(1, jti)

        r = Redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
        await r.set(f"token_revoked:{jti}", "1", ex=60)

        async with httpx.AsyncClient(base_url=admin_client.base_url) as c:
            async with c.stream("GET", "/mcp/sse", headers={"Authorization": f"Bearer {token}"}) as resp:
                assert resp.status_code == 401

        await r.delete(f"token_revoked:{jti}")
        await r.close()
