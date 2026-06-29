"""
文件管理模块 - 数据模型
-----------------------
记录用户上传的所有文件（身份证照片、任务附件等）。
自动选择存储方式：配置了腾讯云 COS 则上传到 COS，否则上传到本地。
"""
from __future__ import annotations

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class FileRecord(BaseModel):
    """
    文件记录表

    字段说明：
    - original_name：用户上传时的原始文件名
    - file_path：存储路径或 URL（COS 时是 CDN URL，本地时是相对路径）
    - file_size：文件大小（字节）
    - mime_type：MIME 类型（如 image/png）
    - storage_type：存储方式 local / tencent_cos
    """
    __tablename__ = "file_record"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False,
        comment="上传用户ID"
    )
    original_name: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="原始文件名"
    )
    file_path: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="存储路径/URL"
    )
    file_size: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="文件大小（字节）"
    )
    mime_type: Mapped[str | None] = mapped_column(
        String(100), default=None, comment="MIME 类型"
    )
    storage_type: Mapped[str] = mapped_column(
        String(20), default="local", comment="存储方式：local / tencent_cos"
    )
