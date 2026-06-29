"""
文件管理 - 业务逻辑层

上传流程：
1. 检查 system_config 是否配置了腾讯云 COS
2. 有 COS 配置 → 上传到 COS，storage_type=tencent_cos
3. 无 COS 配置 → 保存到本地 app/static/upload/，storage_type=local
4. 在 file_record 表创建记录
"""
from __future__ import annotations

import os
import uuid
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from app.modules.file_record.crud import FileCRUD
from app.modules.file_record.models import FileRecord
from app.config import settings


class FileService:
    def __init__(self):
        self.crud = FileCRUD()

    async def get(self, db: AsyncSession, file_id: int) -> FileRecord | None:
        return await self.crud.get_by_id(db, file_id)

    async def list_by_user(
        self, db: AsyncSession, user_id: int, *,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[FileRecord], int]:
        return await self.crud.get_by_user(db, user_id, page=page, page_size=page_size)

    async def list_all(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
    ) -> tuple[list[FileRecord], int]:
        return await self.crud.get_list(db, page=page, page_size=page_size)

    async def _get_cos_client(self, db: AsyncSession):
        """尝试创建 COS 客户端，未配置返回 None"""
        from app.modules.system_config.crud import SystemConfigCRUD
        cfgs = await SystemConfigCRUD().get_all_grouped(db)
        secret_id = cfgs.get("cos_secret_id", "").strip()
        secret_key = cfgs.get("cos_secret_key", "").strip()
        region = cfgs.get("cos_region", "").strip()
        bucket = cfgs.get("cos_bucket", "").strip()
        if not all([secret_id, secret_key, region, bucket]):
            return None, None, None
        from qcloud_cos import CosConfig, CosS3Client
        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
        return CosS3Client(config), bucket, region

    async def upload(
        self, db: AsyncSession, user_id: int, file: UploadFile,
    ) -> FileRecord:
        ext = os.path.splitext(file.filename or "file")[1]
        saved_name = f"{uuid.uuid4().hex}{ext}"
        content = await file.read()

        # 尝试 COS 上传
        cos_client, bucket, region = await self._get_cos_client(db)
        if cos_client:
            from qcloud_cos.cos_exception import CosException
            try:
                cos_client.put_object(
                    Bucket=bucket,
                    Key=saved_name,
                    Body=content,
                )
                cdn_domain = (await self._get_config(db)).get("cos_cdn_domain", "").strip()
                if cdn_domain:
                    file_url = f"{cdn_domain}/{saved_name}"
                else:
                    file_url = f"https://{bucket}.cos.{region}.myqcloud.com/{saved_name}"
                return await self.crud.create(
                    db, user_id=user_id,
                    original_name=file.filename or "unknown",
                    file_path=file_url, file_size=len(content),
                    mime_type=file.content_type, storage_type="tencent_cos",
                )
            except CosException as e:
                pass  # COS 上传失败，回退到本地

        # 本地存储
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, saved_name)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return await self.crud.create(
            db, user_id=user_id,
            original_name=file.filename or "unknown",
            file_path=f"/static/upload/{saved_name}",
            file_size=len(content),
            mime_type=file.content_type,
            storage_type="local",
        )

    async def _get_config(self, db: AsyncSession) -> dict:
        from app.modules.system_config.crud import SystemConfigCRUD
        return await SystemConfigCRUD().get_all_grouped(db)
