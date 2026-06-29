"""文件管理 - Pydantic 校验"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class FileOut(BaseModel):
    id: int
    user_id: int
    original_name: str
    file_path: str
    file_size: int
    mime_type: str | None
    storage_type: str
    status: bool
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
