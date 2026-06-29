"""
系统设置模块 - 数据访问层
-----------------------
继承 BaseCRUD，只添加 SystemConfig 特有的查询方法：
- get_by_key：根据 key 查询启用的配置
- get_all_grouped：获取所有启用配置的 {key: value} 字典，供全局使用
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud import BaseCRUD
from app.modules.system_config.models import SystemConfig


class SystemConfigCRUD(BaseCRUD[SystemConfig]):
    """系统配置的数据库操作类"""

    def __init__(self):
        super().__init__(SystemConfig)

    async def get_by_key(self, db: AsyncSession, key: str) -> SystemConfig | None:
        """
        根据配置键名查询启用状态的配置
        用于后端代码中读取系统设置，如：get_by_key(db, "site_title")
        """
        stmt = select(SystemConfig).where(
            SystemConfig.key == key, SystemConfig.status == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_grouped(self, db: AsyncSession) -> dict[str, str]:
        """
        获取所有启用配置的键值对字典
        用于一次性加载所有系统设置到应用内存或模板全局变量中。
        返回格式：{"site_title": "我的平台", "smtp_host": "smtp.qq.com", ...}
        """
        items, _ = await self.get_list(db, page=1, page_size=1000, status=True)
        return {item.key: item.value for item in items}

    async def upsert(self, db: AsyncSession, key: str, value: str, group: str = "general") -> SystemConfig:
        """创建或更新：key 已存在则更新，不存在则创建"""
        stmt = select(SystemConfig).where(SystemConfig.key == key)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return await self.update(db, existing.id, value=value, group=group)
        return await self.create(db, key=key, value=value, group=group)
