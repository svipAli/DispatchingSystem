"""
公共依赖注入模块
---------------
所有 FastAPI 路由共用的 Depends 函数都在这里定义：
- get_redis：获取 Redis 连接
- get_db：获取数据库会话（自动 commit/rollback）
- get_current_user：JWT 鉴权 + Redis 状态检查，返回当前登录用户

鉴权全链路：
    请求带 Authorization: Bearer <token>
    → HTTPBearer 提取 token
    → JWT 本地解密拿到 user_id（纯 CPU，不查任何存储）
    → Redis 查 user:status:{id} 缓存（0.5ms）
        命中且 is_active=False → 403
        未命中 → 查 DB → 写入 Redis 缓存（TTL 60秒）
    → 返回 User 对象注入到路由函数
"""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import decode_token

# HTTPBearer 负责从请求头中提取 Bearer Token
# auto_error=False：不主动报错，由下游逻辑统一处理未登录情况
security_scheme = HTTPBearer(auto_error=False)


async def get_redis(request: Request) -> Redis:
    """获取 Redis 连接，依赖注入用"""
    return request.app.state.redis


async def get_db(request: Request) -> AsyncSession:
    """
    获取数据库会话（每个请求一个会话）

    自动管理事务：
    - 路由处理正常结束 → commit
    - 路由处理抛出异常 → rollback
    - 无论如何 → 关闭会话归还连接到连接池
    """
    factory = request.app.state.db_session_factory
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    从 JWT 中获取当前登录用户（最重要的依赖注入函数）

    每次请求都完整校验：
    1. 提取 Authorization Header 中的 Bearer Token
    2. JWT 本地解密，拿到 user_id（纯 CPU，不查数据库，不查 Redis）
    3. Redis 检查用户状态缓存 user:status:{id}
       - 命中 → 检查 is_active 是否为 True
       - 未命中 → 查 DB → 写入 Redis 缓存（TTL=60秒）
    4. 从 DB 加载完整用户对象返回

    禁用用户流程：
        管理员禁用用户 → 删除 Redis user:status:{id} 缓存
        → 用户下次请求时 Redis 未命中 → 查 DB 发现 status=False → 403
        → 即时生效，不依赖 Token 过期时间
    """
    # 第一步：从 Authorization Header 提取 Token
    if credentials is None:
        raise HTTPException(status_code=401, detail="请先登录")

    # 第二步：JWT 解密（纯 CPU 运算，不查 Redis/DB）
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    user_id = int(payload["sub"])

    # 拒绝 MCP 类型的 Token（只允许 login 类型或无 type 字段的旧 Token）
    if payload.get("type") == "mcp":
        raise HTTPException(status_code=403, detail="MCP Token 不能用于 Web 登录")

    # 第三步：Redis 缓存检查用户状态（热点数据，0.5ms 返回）
    redis: Redis = request.app.state.redis
    cached = await redis.get(f"user:status:{user_id}")

    if cached is not None:
        # 缓存命中，直接判断
        if cached != "True":
            raise HTTPException(status_code=403, detail="账户已被禁用，请联系客服")
    else:
        # 缓存未命中，查数据库并回写缓存
        from app.modules.user.crud import UserCRUD

        async with request.app.state.db_session_factory() as db:
            user = await UserCRUD().get_by_id(db, user_id)
            if user is None:
                raise HTTPException(status_code=401, detail="用户不存在")
            # 写入 Redis 缓存，TTL 60 秒
            await redis.set(f"user:status:{user_id}", str(user.status), ex=60)
            if not user.status:
                raise HTTPException(status_code=403, detail="账户已被禁用，请联系客服")

    # 第四步：从数据库加载完整用户对象返回（后续鉴权需要角色和权限信息）
    from app.modules.user.crud import UserCRUD

    async with request.app.state.db_session_factory() as db:
        user = await UserCRUD().get_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="用户不存在")
        return user


# ========== 管理员权限 ==========


async def require_admin(
    request: Request,
    current_user=Depends(get_current_user),
) -> bool:
    """
    管理员权限校验依赖
    在 get_current_user 之后执行，检查用户是否拥有 admin 角色。

    用法：
        @router.delete("/users/{id}")
        async def delete_user(id: int, _=Depends(require_admin)):
            ...
    """
    from app.modules.role.crud import RoleCRUD

    async with request.app.state.db_session_factory() as db:
        role_ids = await RoleCRUD().get_user_role_ids(db, current_user.id)
        for rid in role_ids:
            role = await RoleCRUD().get_by_id(db, rid)
            if role and role.code == "admin":
                return True

    raise HTTPException(status_code=403, detail="需要管理员权限")
