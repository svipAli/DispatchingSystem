"""
角色模块 - 数据模型
-----------------
RBAC 核心表：角色（Role）和用户-角色关联（UserRole）。
角色是权限的集合体，用户通过角色获得相应的权限和菜单访问权。
"""
from sqlalchemy import Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class Role(BaseModel):
    """
    角色表

    字段说明：
    - code：角色标识（全系统唯一），如 "admin"、"customer_service"、"user"
           代码中通过 code 判断角色，而不是通过 name
    - is_system：系统内置角色（admin、user）不可删除，防止误删导致系统异常
    """
    __tablename__ = "role"

    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="角色名称，如\"管理员\""
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False, comment="角色标识，如\"admin\""
    )
    description: Mapped[str | None] = mapped_column(
        String(200), default=None, comment="角色描述"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="系统内置角色，不可删除"
    )


class UserRole(BaseModel):
    """
    用户-角色关联表
    一个用户可以拥有多个角色，一个角色下可以有多个用户。
    """
    __tablename__ = "user_role"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.id", ondelete="CASCADE"), nullable=False, comment="角色ID"
    )
