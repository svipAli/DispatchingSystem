"""AI 助手 - REST 接口"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.response import success
from app.dependencies import get_db, get_current_user

router = APIRouter(prefix="/chat-history", tags=["AI 聊天"])


@router.get("")
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.ai_admin.crud import ChatCRUD
    items, total = await ChatCRUD().get_history(db, current_user.id, limit=limit, offset=offset)
    return success({
        "items": [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in items],
        "total": total,
        "has_more": (offset + limit) < total,
    })
