"""
API Token 模块 - 数据模型
------------------------
用户创建 API Token 后可以通过 Token 调用 MCP 服务（按次扣费）。
一个用户可以有多个 Token（如开发环境、生产环境各一个）。
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class ApiToken(BaseModel):
    """
    API Token 表（MCP 网关专用 JWT Token）

    字段说明：
    - name：Token 的备注名称，用户自己起名区分
    - token：JWT Token 字符串（创建时一次性展示，后续不可见）
    - jti：JWT ID，用于 Redis 黑名单撤销
    - last_used_at：最后一次使用的时间
    - expires_at：过期时间（JWT 中 exp 的对应时间）
    """
    __tablename__ = "api_token"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Token 名称"
    )
    token: Mapped[str] = mapped_column(
        String(500), unique=True, index=True, nullable=False, comment="JWT Token 字符串"
    )
    jti: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False, comment="JWT ID，用于撤销"
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=None, comment="最后使用时间"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=None, comment="过期时间"
    )
