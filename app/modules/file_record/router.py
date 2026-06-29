"""文件管理 - API 路由"""
from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, paginate, error
from app.dependencies import get_db, get_current_user, require_admin
from app.modules.file_record.schemas import FileOut
from app.modules.file_record.service import FileService

router = APIRouter(prefix="/files", tags=["文件管理"])
service = FileService()


@router.get("", summary="我的文件列表")
async def list_my_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_by_user(
        db, current_user.id, page=page, page_size=page_size,
    )
    return paginate(
        [FileOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.get("/admin", summary="全部文件列表（管理员）")
async def list_all_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    items, total = await service.list_all(db, page=page, page_size=page_size)
    return paginate(
        [FileOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.post("/upload", summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await service.upload(db, current_user.id, file)
    return success(FileOut.model_validate(item).model_dump(), message="上传成功")


@router.get("/{file_id}", summary="文件详情")
async def get_file(
    file_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await service.get(db, file_id)
    if not item or item.user_id != current_user.id:
        return error(code=404, message="文件不存在")
    return success(FileOut.model_validate(item).model_dump())
