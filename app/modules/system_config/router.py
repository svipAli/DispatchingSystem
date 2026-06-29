"""
系统设置模块 - API 路由
-----------------------
提供系统配置的增删改查 REST API：
- GET    /api/v1/system-configs         分页列表（支持按 group 过滤）
- GET    /api/v1/system-configs/{id}    查询单条
- POST   /api/v1/system-configs         创建新配置
- PUT    /api/v1/system-configs/{id}    更新已有配置

所有返回均为统一格式 { code, message, data }
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, paginate, error
from app.dependencies import get_db, require_admin
from app.modules.system_config.schemas import (
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigOut,
)
from app.modules.system_config.service import SystemConfigService

# 创建路由实例，设置路径前缀和 OpenAPI 标签分组
router = APIRouter(prefix="/system-configs", tags=["系统设置"])
service = SystemConfigService()


@router.get("")
async def list_configs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    group: str | None = Query(None, description="按分组过滤"),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    """分页查询系统配置列表，可按分组过滤"""
    items, total = await service.list(db, page=page, page_size=page_size, group=group)
    # 将 ORM 对象转为 Pydantic Schema 再转 dict 输出
    return paginate(
        [SystemConfigOut.model_validate(item).model_dump() for item in items],
        total,
        page,
        page_size,
    )


@router.get("/{config_id}")
async def get_config(config_id: int, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)):
    """根据 ID 查询单条配置详情"""
    item = await service.get(db, config_id)
    if not item:
        return error(code=404, message="配置不存在")
    return success(SystemConfigOut.model_validate(item).model_dump())


@router.post("")
async def create_config(
    data: SystemConfigCreate, db: AsyncSession = Depends(get_db), _: bool = Depends(require_admin)
):
    """创建一条新的系统配置"""
    item = await service.create(db, data)
    return success(
        SystemConfigOut.model_validate(item).model_dump(), message="创建成功"
    )


@router.put("/{config_id}")
async def update_config(
    config_id: int,
    data: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    """更新已有系统配置（只更新传了的字段）"""
    item = await service.update(db, config_id, data)
    if not item:
        return error(code=404, message="配置不存在")
    return success(
        SystemConfigOut.model_validate(item).model_dump(), message="更新成功"
    )


@router.post("/upsert", summary="创建或更新配置")
async def upsert_config(
    data: SystemConfigCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    """key 已存在则更新 value，不存在则创建"""
    item = await service.crud.upsert(db, data.key, data.value, data.group)
    return success(SystemConfigOut.model_validate(item).model_dump(), message="保存成功")
