"""
系统设置模块 - Pydantic 数据校验模型
----------------------------------
- SystemConfigCreate：创建配置时的入参校验
- SystemConfigUpdate：更新配置时的入参（全部可选，只更新传了的字段）
- SystemConfigOut：返回给前端的输出格式（from_attributes=True 支持 ORM 对象直接转换）
"""
from datetime import datetime
from pydantic import BaseModel, Field


class SystemConfigCreate(BaseModel):
    """创建系统配置的请求体"""

    key: str = Field(..., min_length=1, max_length=100, description="配置键名")
    value: str = Field(default="", description="配置值")
    group: str = Field(default="general", max_length=50, description="配置分组")
    description: str | None = None
    remark: str | None = None


class SystemConfigUpdate(BaseModel):
    """更新系统配置的请求体，所有字段可选（只传需要更新的字段）"""

    value: str | None = None
    group: str | None = None
    description: str | None = None
    remark: str | None = None
    status: bool | None = None


class SystemConfigOut(BaseModel):
    """系统配置的输出格式，可被前端/API 客户端使用"""

    id: int
    key: str
    value: str
    group: str
    description: str | None
    remark: str | None
    status: bool
    created_at: datetime
    updated_at: datetime

    # 允许从 ORM 对象直接转换
    model_config = {"from_attributes": True}
