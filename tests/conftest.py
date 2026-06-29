"""
测试配置文件（pytest conftest）
-----------------------------
所有测试用例共享的 fixtures 定义在这里。

Fixture 说明：
- event_loop：为整个测试 session 创建独立的 asyncio 事件循环
- test_engine：测试数据库引擎（session 级别，只创建一次）
  - 使用 NullPool 避免异步连接池复用导致的 "another operation is in progress" 错误
  - 自动建表（create_all）和删表（drop_all）
- session_factory：测试数据库会话工厂（session 级别）
- client：异步 HTTP 测试客户端（每个测试函数独立）
  - 使用 fakeredis 模拟 Redis，避免依赖真实 Redis 服务
  - 每个测试结束后自动 TRUNCATE 所有表，确保测试隔离
- sample_user_data：用户注册的示例数据

使用方式：
    async def test_xxx(client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={...})
        assert resp.json()["code"] == 0
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base

# ========== 导入所有模型，确保 Base.metadata 知道所有表 ==========
# 必须在 create_all 之前导入，否则不会创建对应的表
import app.modules.system_config.models  # noqa: E402
import app.modules.user.models           # noqa: E402
import app.modules.role.models           # noqa: E402
import app.modules.permission.models     # noqa: E402
import app.modules.menu.models           # noqa: E402
import app.modules.api_token.models      # noqa: E402
import app.modules.mcp_node.models       # noqa: E402
import app.modules.task.models           # noqa: E402
import app.modules.billing.models        # noqa: E402
import app.modules.recharge.models       # noqa: E402
import app.modules.file_record.models    # noqa: E402
import app.modules.ai_admin.models       # noqa: E402

# 测试专用数据库 URL（独立于开发数据库，数据互不影响）
TEST_DATABASE_URL = "postgresql+asyncpg://zhangli@localhost:5432/dispatching_test"


@pytest.fixture(scope="session")
def event_loop():
    """
    为整个测试 session 创建独立的 asyncio 事件循环
    确保所有 async fixtures 共享同一个 loop
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    测试数据库引擎（session 级别，整个测试过程只创建一次）
    使用 NullPool 避免连接池中连接被多个 greenlet 争用的问题。
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)

    # 自动建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # 测试全部结束后删表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(test_engine):
    """
    测试数据库会话工厂（session 级别）
    expire_on_commit=False：commit 后模型属性不失效
    """
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    """
    异步 HTTP 测试客户端（每个测试函数独立）

    关键实现细节：
    - 使用 fakeredis 模拟 Redis（避免测试依赖真实 Redis 服务）
    - 将测试 session_factory 注入到 app.state，这样 get_db 依赖注入会使用测试数据库
    - 用 httpx.ASGITransport 直接调用 FastAPI app（不走网络，速度更快）
    - 每个测试结束后 TRUNCATE 所有表，保证测试之间的数据隔离

    表名用双引号包裹是因为 "user" 是 PostgreSQL 保留字，必须加引号。
    """
    from app.main import app

    # 用 fakeredis 替代真实 Redis，避免测试污染
    import fakeredis

    app.state.redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    # 让 get_db 依赖注入使用测试数据库的会话工厂
    app.state.db_session_factory = session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # === 测试后清理：清空所有表数据 ===
    async with session_factory() as session:
        async with session.begin():
            from sqlalchemy import text

            # reversed 确保先删子表再删父表（避免外键约束错误）
            for table in reversed(Base.metadata.sorted_tables):
                # RESTART IDENTITY CASCADE 同时重置自增 ID 计数器
                await session.execute(
                    text(
                        f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'
                    )
                )


@pytest.fixture
def sample_user_data():
    """用户注册的示例数据，供测试用例复用"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "Test123456",
    }


@pytest_asyncio.fixture
async def admin_token(session_factory) -> str:
    """
    创建一个管理员用户并返回 JWT Token
    用于测试需要管理员权限的接口

    流程：创建 admin 角色 → 创建管理员用户 → 分配角色 → 返回 Token
    """
    from app.modules.role.models import Role, UserRole
    from app.modules.user.models import User
    from app.core.security import hash_password, create_access_token

    async with session_factory() as db, db.begin():
        # 1. 创建 admin 角色
        role = Role(code="admin", name="管理员", is_system=True)
        db.add(role)
        await db.flush()

        # 2. 创建管理员用户
        user = User(
            username="admin_test",
            email="admin@test.local",
            password_hash=hash_password("Admin123456"),
            status=True,
        )
        db.add(user)
        await db.flush()

        # 3. 分配 admin 角色
        ur = UserRole(user_id=user.id, role_id=role.id)
        db.add(ur)

        return create_access_token(user.id)


@pytest_asyncio.fixture
async def admin_client(
    client: AsyncClient, admin_token: str
) -> AsyncGenerator[AsyncClient, None]:
    """
    带管理员认证的 HTTP 测试客户端
    所有请求自动带上 Authorization: Bearer <admin_token>
    用于测试需要管理员权限的接口
    """
    client.headers["Authorization"] = f"Bearer {admin_token}"
    yield client
    client.headers.pop("Authorization", None)
