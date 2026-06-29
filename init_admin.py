"""
首次部署初始化脚本
用法：python init_admin.py
在 .env 配置好数据库后运行，创建默认管理员账号
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings
from app.core.security import hash_password
from app.modules.user.models import User
from app.modules.role.models import Role, UserRole

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123456"


async def init():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as db:
        # 检查是否已初始化
        from sqlalchemy import select, func
        count = (await db.execute(select(func.count(User.id)))).scalar() or 0
        if count > 0:
            print(f"数据库已有 {count} 个用户，跳过初始化")
            return

        # 创建管理员角色
        role = Role(code="admin", name="管理员", is_system=True, status=True)
        db.add(role)
        await db.flush()

        # 创建管理员用户
        user = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            balance=0.0,
            status=True,
        )
        db.add(user)
        await db.flush()

        # 分配管理员角色
        ur = UserRole(user_id=user.id, role_id=role.id)
        db.add(ur)

        await db.commit()
        print(f"管理员账号创建成功：{ADMIN_USERNAME} / {ADMIN_PASSWORD}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init())
