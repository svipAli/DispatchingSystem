"""
Alembic 数据库迁移配置
---------------------
数据库版本管理工具，支持自动生成迁移脚本和执行迁移。

用法：
    alembic revision --autogenerate -m "创建用户表"   # 自动生成迁移
    alembic upgrade head                               # 执行所有待迁移
    alembic downgrade -1                               # 回滚一个版本

配置要点：
- 使用异步引擎（create_async_engine）连接 PostgreSQL
- 从 .env 读取数据库 URL，不依赖 alembic.ini 中的硬编码连接串
- target_metadata = Base.metadata 让 autogenerate 自动检测模型变更
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Alembic Config 对象
config = context.config

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 导入所有模型的基类，让 autogenerate 能检测到表结构变化
from app.core.database import Base

# 导入所有模型（autogenerate 需要扫描这些）
import app.modules.user.models
import app.modules.role.models
import app.modules.permission.models
import app.modules.menu.models
import app.modules.api_token.models
import app.modules.mcp_node.models
import app.modules.task.models
import app.modules.billing.models
import app.modules.recharge.models
import app.modules.file_record.models
import app.modules.system_config.models
import app.modules.ai_admin.models
import app.modules.ai_admin.models

# 从 .env 读取数据库连接 URL，不用 alembic.ini 中的硬编码值
from app.config import settings

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 告诉 Alembic 要追踪哪些表的变更
target_metadata = Base.metadata


def run_migrations_offline():
    """
    离线迁移模式
    生成 SQL 脚本文件，不直接连接数据库执行。
    用于需要 DBA 审核 SQL 再手动执行的场景。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """在给定连接上执行迁移"""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """
    在线迁移模式
    直接连接数据库执行 DDL 变更，是最常用的方式。
    使用 NullPool 因为迁移是短暂操作，不需要连接池。
    """
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        # run_sync 在异步上下文中运行同步的 do_run_migrations
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# 判断是离线还是在线模式并执行
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
