"""
权限模块 - 数据模型
-----------------
权限标识（Permission）和角色-权限关联（RolePermission）。
每个 API 接口对应一个权限标识，RolePermission 决定哪些角色可以访问哪些接口。
"""
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class Permission(BaseModel):
    """
    权限标识表

    字段说明：
    - code：权限标识（全系统唯一），如 "user:delete"、"task:create"、"billing:view"
           格式约定：module:action
    - module：所属模块，用于后台按模块分组展示权限列表
    """
    __tablename__ = "permission"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="权限名称，如\"删除用户\""
    )
    code: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False, comment="权限标识，如\"user:delete\""
    )
    module: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="所属模块，如\"user\""
    )
    description: Mapped[str | None] = mapped_column(
        String(200), default=None, comment="权限说明"
    )


class RolePermission(BaseModel):
    """
    角色-权限关联表
    一个角色拥有多个权限，一个权限可以分配给多个角色。
    """
    __tablename__ = "role_permission"

    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.id", ondelete="CASCADE"), nullable=False, comment="角色ID"
    )
    permission_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("permission.id", ondelete="CASCADE"), nullable=False, comment="权限ID"
    )
