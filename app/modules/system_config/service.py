"""
系统设置模块 - 业务逻辑层
-----------------------
在 CRUD 之上封装业务规则：
- create 时从 Schema 提取字段传给 CRUD
- update 时用 model_dump(exclude_unset=True) 只更新传入的字段
- get_all_kv 返回键值对字典供全局使用
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.system_config.crud import SystemConfigCRUD
from app.modules.system_config.schemas import SystemConfigCreate, SystemConfigUpdate
from app.modules.system_config.models import SystemConfig


class SystemConfigService:
    """系统设置的业务逻辑服务"""

    def __init__(self):
        self.crud = SystemConfigCRUD()

    async def get(self, db: AsyncSession, config_id: int) -> SystemConfig | None:
        """按 ID 查询单条配置"""
        return await self.crud.get_by_id(db, config_id)

    async def get_by_key(self, db: AsyncSession, key: str) -> SystemConfig | None:
        """按 key 查询启用的配置"""
        return await self.crud.get_by_key(db, key)

    async def list(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        group: str | None = None,
    ) -> tuple[list[SystemConfig], int]:
        """
        分页查询配置列表
        :param group: 可选，按分组过滤（如只查 email 分组的配置）
        """
        filters = {}
        if group:
            filters["group"] = group
        return await self.crud.get_list(db, page=page, page_size=page_size, **filters)

    async def create(self, db: AsyncSession, data: SystemConfigCreate) -> SystemConfig:
        """创建一条系统配置"""
        return await self.crud.create(
            db,
            key=data.key,
            value=data.value,
            group=data.group,
            description=data.description,
            remark=data.remark,
        )

    async def update(
        self, db: AsyncSession, config_id: int, data: SystemConfigUpdate
    ) -> SystemConfig | None:
        """
        更新一条系统配置
        exclude_unset=True：只更新客户端实际传了的字段，未传的字段保持原值
        """
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return None
        return await self.crud.update(db, config_id, **updates)

    async def get_all_kv(self, db: AsyncSession) -> dict[str, str]:
        """获取所有启用配置的键值对"""
        return await self.crud.get_all_grouped(db)
