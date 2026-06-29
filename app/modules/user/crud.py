"""
用户模块 - 数据访问层
-------------------
继承 BaseCRUD，添加用户特有的查询方法：
- get_by_username：按用户名查（登录、注册去重用）
- get_by_email：按邮箱查
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.user.models import User


class UserCRUD(BaseCRUD[User]):
    """用户表的数据库操作类"""

    def __init__(self):
        super().__init__(User)

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        """根据用户名精确查询用户（用于登录和注册去重）"""
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """根据邮箱查询用户"""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
