"""
MCP 节点管理模块 - Pydantic 数据校验
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


# ===== MCP Node =====


class McpNodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1, max_length=100)
    port: int = Field(..., ge=1, le=65535)
    max_concurrent: int = Field(5, ge=1, le=100)
    description: str | None = None
    remark: str | None = None


class McpNodeUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    max_concurrent: int | None = None
    description: str | None = None
    remark: str | None = None
    status: bool | None = None


class McpNodeOut(BaseModel):
    id: int
    name: str
    host: str
    port: int
    node_status: str
    max_concurrent: int
    current_load: int
    last_heartbeat: datetime | None
    description: str | None
    remark: str | None
    status: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===== Node Service =====


class NodeServiceCreate(BaseModel):
    node_id: int
    service_name: str = Field(..., min_length=1, max_length=100)
    service_type: str = Field(..., min_length=1, max_length=100)
    price_per_call: float = Field(0.0, ge=0)
    description: str | None = None
    version: str | None = None
    cover_image: str | None = None
    params: list | None = None
    timeout: int = Field(300, ge=1, le=86400, description="任务超时时间（秒）")
    remark: str | None = None


class NodeServiceUpdate(BaseModel):
    service_name: str | None = None
    price_per_call: float | None = None
    description: str | None = None
    params: list | None = None
    version: str | None = None
    cover_image: str | None = None
    is_verified: bool | None = None
    timeout: int | None = Field(None, ge=1, le=86400, description="任务超时时间（秒）")
    remark: str | None = None
    status: bool | None = None


class NodeServiceOut(BaseModel):
    id: int
    node_id: int
    service_name: str
    service_type: str
    price_per_call: float
    description: str | None
    version: str | None
    cover_image: str | None
    is_verified: bool
    status: bool
    params: list | None
    original_params: list | None
    timeout: int
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
