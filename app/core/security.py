"""
安全模块：JWT 令牌 + 密码哈希
---------------------------
- JWT 使用 HS256 算法，本地 CPU 解密
- Token 类型：login（Web登录）/ mcp（MCP网关调用）
- MCP Token 默认 90 天过期，支持 Redis 黑名单撤销
- 密码使用 bcrypt 单向哈希
"""
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.config import settings

ALGORITHM = "HS256"

import bcrypt


def create_access_token(user_id: int) -> str:
    """生成 Web 登录 JWT（type=login）"""
    expire = datetime.now() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "login"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_mcp_token(user_id: int, jti: str) -> str:
    """生成 MCP 网关 JWT（type=mcp），默认 90 天过期"""
    expire = datetime.now() + timedelta(days=90)
    payload = {"sub": str(user_id), "exp": expire, "type": "mcp", "jti": jti}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解密 JWT，成功返回 payload，失败返回 None"""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )
