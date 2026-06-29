"""
API Token 模块 - API 路由

所有接口都需要登录：
- GET    /api/v1/api-tokens            查看自己的 Token 列表
- POST   /api/v1/api-tokens            创建新 Token（JWT，90天过期）
- DELETE /api/v1/api-tokens/{id}       撤销 Token（加入黑名单）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, paginate, error
from app.dependencies import get_db, get_current_user
from app.modules.api_token.schemas import ApiTokenCreate, ApiTokenUpdate, ApiTokenOut
from app.modules.api_token.service import ApiTokenService

router = APIRouter(prefix="/api-tokens", tags=["API Token"])
service = ApiTokenService()


@router.get("", summary="查看我的 Token 列表")
async def list_my_tokens(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_by_user(
        db, current_user.id, page=page, page_size=page_size
    )
    return paginate(
        [ApiTokenOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.post("", summary="创建新 Token")
async def create_token(
    data: ApiTokenCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await service.create(db, current_user.id, data)
    return success(
        ApiTokenOut.model_validate(item).model_dump(), message="Token 创建成功，请立即复制保存"
    )


@router.put("/{token_id}", summary="更新 Token")
async def update_token(
    token_id: int,
    data: ApiTokenUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await service.get(db, token_id)
    if not item or item.user_id != current_user.id:
        return error(code=404, message="Token 不存在")
    updated = await service.update(db, token_id, data)
    return success(
        ApiTokenOut.model_validate(updated).model_dump(), message="更新成功"
    )


@router.delete("/{token_id}", summary="撤销 Token")
async def revoke_token(
    token_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await service.get(db, token_id)
    if not item or item.user_id != current_user.id:
        return error(code=404, message="Token 不存在")
    redis = request.app.state.redis
    await service.revoke(db, token_id, redis)
    return success(message="Token 已撤销")
