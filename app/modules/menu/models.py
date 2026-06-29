"""
菜单模块 - 数据模型
-----------------
菜单表（Menu）和角色-菜单关联（RoleMenu）。
菜单采用树形结构（parent_id 自引用），不同角色看到不同的菜单树。
"""
from sqlalchemy import Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class Menu(BaseModel):
    """
    菜单表（树形结构）

    字段说明：
    - parent_id：父菜单 ID，NULL 表示一级菜单
    - path：前端路由路径，如 /admin/users
    - component：前端组件名，可选，用于动态路由
    - sort：排序值，数值越小越靠前
    - status：继承自 BaseModel，True=显示，False=隐藏

    示例数据：
        id=1, parent_id=null, name="系统管理", sort=1
        id=2, parent_id=1,    name="用户管理", path="/admin/users"
        id=3, parent_id=1,    name="角色管理", path="/admin/roles"
    """
    __tablename__ = "menu"

    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("menu.id", ondelete="SET NULL"),
        default=None, comment="父菜单ID，空表示一级菜单"
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="菜单名称"
    )
    icon: Mapped[str | None] = mapped_column(
        String(50), default=None, comment="图标类名，如\"home\""
    )
    path: Mapped[str | None] = mapped_column(
        String(200), default=None, comment="前端路由路径，如\"/admin/users\""
    )
    component: Mapped[str | None] = mapped_column(
        String(200), default=None, comment="前端组件名，可选"
    )
    sort: Mapped[int] = mapped_column(
        Integer, default=0, comment="排序值，越小越靠前"
    )


class RoleMenu(BaseModel):
    """
    角色-菜单关联表
    决定某个角色能看到哪些菜单。
    """
    __tablename__ = "role_menu"

    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.id", ondelete="CASCADE"), nullable=False, comment="角色ID"
    )
    menu_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("menu.id", ondelete="CASCADE"), nullable=False, comment="菜单ID"
    )
