"""
数据库基类和 Mixin
----------------
- Base：SQLAlchemy 声明式基类，所有模型都继承它
- TimestampMixin：给表自动加上 created_at / updated_at 时间字段
- BaseModel：所有业务表的父类，包含 id、remark、status 三个公共字段
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import Integer, DateTime, String, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings

# 可配置时区
_local_tz = timezone(timedelta(hours=settings.TZ_OFFSET))


def _now():
    return datetime.now(_local_tz).replace(tzinfo=None)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类，所有 ORM 模型继承它"""
    pass


class TimestampMixin:
    """
    时间戳混入类
    被继承后自动获得创建时间和更新时间两个字段。
    created_at 只在 INSERT 时写入，updated_at 在每次 UPDATE 时自动更新。
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now,
        onupdate=_now,
        nullable=False,
        comment="更新时间",
    )


class BaseModel(Base, TimestampMixin):
    """
    所有业务表的抽象父类
    每张表自动继承以下公共字段：
    - id：自增主键
    - remark：备注（管理员或用户写的备注信息）
    - status：通用状态位（True=启用/可见/未删除，False=禁用/隐藏/已删除）
    - created_at / updated_at：时间戳

    注意：这是一个抽象类（__abstract__=True），不会在数据库中单独建表。
    """
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键ID"
    )
    remark: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="备注"
    )
    status: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="状态：True=启用，False=禁用"
    )
