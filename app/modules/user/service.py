"""
用户模块 - 业务逻辑层
-------------------
封装用户相关的所有业务逻辑：
- register：注册（密码哈希 + 创建用户）
- verify_login：登录验证（查用户 → 验密码 → 查状态）
- update / update_identity：更新个人信息 / 提交实名
- verify_identity / set_status：管理后台用的审核和禁用操作
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, verify_password
from app.modules.user.crud import UserCRUD
from app.modules.user.models import User
from app.modules.user.schemas import UserRegisterIn, UserUpdateIn, UserUpdateIdentityIn


class UserService:
    """用户模块业务逻辑服务"""

    def __init__(self):
        self.crud = UserCRUD()

    async def get(self, db: AsyncSession, user_id: int) -> User | None:
        """按 ID 查询用户"""
        return await self.crud.get_by_id(db, user_id)

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        """按用户名查询"""
        return await self.crud.get_by_username(db, username)

    async def list(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20, keyword: str | None = None,
        status: bool | None = None, date_from: str | None = None, date_to: str | None = None
    ) -> tuple[list[User], int]:
        """分页查询用户列表"""
        return await self.crud.get_list(db, page=page, page_size=page_size, keyword=keyword, status=status, date_from=date_from, date_to=date_to)

    async def register(self, db: AsyncSession, data: UserRegisterIn) -> User:
        """
        用户注册
        对明文密码进行 bcrypt 哈希后存入数据库，绝不存明文。
        """
        hashed = hash_password(data.password)
        return await self.crud.create(
            db,
            username=data.username,
            email=data.email,
            phone=data.phone,
            password_hash=hashed,
        )

    async def verify_login(
        self, db: AsyncSession, username: str, password: str
    ) -> User | None:
        """
        登录验证：三步检查
        1. 用户是否存在
        2. 密码是否正确（bcrypt 比对）
        3. 账户是否被禁用（status 检查）
        任意一步不通过返回 None
        """
        user = await self.crud.get_by_username(db, username)
        if user is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.status:
            return None
        return user

    async def update(
        self, db: AsyncSession, user_id: int, data: UserUpdateIn
    ) -> User | None:
        """
        更新用户信息
        - 如果传了 password，自动 bcrypt 哈希
        - 如果传了 expire_date（字符串），转为 datetime
        """
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return None
        # 密码单独处理：哈希后存 password_hash
        if "password" in updates:
            updates["password_hash"] = hash_password(updates.pop("password"))
        # 日期转换
        if "expire_date" in updates and updates["expire_date"] is not None:
            from datetime import datetime
            updates["expire_date"] = datetime.strptime(updates["expire_date"], "%Y-%m-%d")
        return await self.crud.update(db, user_id, **updates)

    async def update_identity(
        self, db: AsyncSession, user_id: int, data: UserUpdateIdentityIn
    ) -> User | None:
        """提交实名认证信息（不改变 is_verified，等待后台审核）"""
        return await self.crud.update(
            db,
            user_id,
            real_name=data.real_name,
            id_card_number=data.id_card_number,
            id_card_front_url=data.id_card_front_url,
            id_card_back_url=data.id_card_back_url,
        )

    async def verify_identity(
        self, db: AsyncSession, user_id: int, verified: bool = True
    ) -> User | None:
        """后台审核实名认证（管理员操作）"""
        return await self.crud.update(db, user_id, is_verified=verified)

    async def set_status(
        self, db: AsyncSession, user_id: int, status: bool
    ) -> User | None:
        """
        启用/禁用用户（管理员操作）
        禁用后需同步删除 Redis 缓存 user:status:{id} 使立即生效
        """
        return await self.crud.update(db, user_id, status=status)
