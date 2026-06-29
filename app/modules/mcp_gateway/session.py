"""
MCP Gateway 会话管理
每个 SSE 连接一个会话，绑定用户身份和数据库连接工厂
"""
import asyncio
import time
from datetime import datetime


class MCPSession:
    def __init__(self, user_id: int, db_factory):
        self.user_id = user_id
        self.db_factory = db_factory
        self.queue: asyncio.Queue = asyncio.Queue()
        self.created_at = datetime.now()

    async def push(self, data: dict):
        await self.queue.put(data)


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, MCPSession] = {}
        self._last_cleanup = time.monotonic()

    def create(self, user_id: int, db_factory) -> str:
        import uuid
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = MCPSession(user_id, db_factory)
        self._cleanup_expired()
        return session_id

    def get(self, session_id: str) -> MCPSession | None:
        return self._sessions.get(session_id)

    def remove(self, session_id: str):
        self._sessions.pop(session_id, None)

    def _cleanup_expired(self):
        now = time.monotonic()
        if now - self._last_cleanup < 60:
            return
        self._last_cleanup = now
        expired = [
            sid for sid, s in self._sessions.items()
            if (datetime.now() - s.created_at).total_seconds() > 600
        ]
        for sid in expired:
            self._sessions.pop(sid, None)


session_manager = SessionManager()
