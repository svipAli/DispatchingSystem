"""
MCP 节点管理模块 - 数据模型
--------------------------
管理局域网内运行 MCP 服务的服务器节点（几十台机器）。
每个节点可以运行多种 MCP 服务，服务和节点的对应关系通过 node_service 表维护。

混合模式：
- 节点主动上报自己支持的服务列表（心跳时附带）
- 平台统一管理服务的价格、描述、审核
- 新出现的服务类型自动创建但需管理员审核（is_verified=False）
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class McpNode(BaseModel):
    """
    MCP 服务器节点表

    字段说明：
    - host：节点 IP 地址
    - port：节点 MCP 服务端口
    - status：online（在线）/ offline（离线）/ busy（繁忙）
    - max_concurrent：该节点最大并发任务数
    - current_load：当前正在执行的任务数
    - last_heartbeat：最后心跳时间，超时未上报则判定为离线
    """
    __tablename__ = "mcp_node"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="节点名称"
    )
    host: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="IP 地址"
    )
    port: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="端口"
    )
    node_status: Mapped[str] = mapped_column(
        String(20), default="offline", comment="运行状态：online/offline/busy"
    )
    max_concurrent: Mapped[int] = mapped_column(
        Integer, default=5, comment="最大并发任务数"
    )
    current_load: Mapped[int] = mapped_column(
        Integer, default=0, comment="当前正在执行的任务数"
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime, default=None, comment="最后心跳时间"
    )
    description: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="节点描述"
    )


class NodeService(BaseModel):
    """
    节点支持的 MCP 服务表

    字段说明：
    - service_name：服务展示名称
    - service_type：服务类型标识（如 text-generation、code-execution）
    - price_per_call：每次调用的单价（元）
    - description：服务详情（富文本 HTML），管理员用 Quill 编辑器填写
    - cover_image：服务封面图 URL
    - is_verified：是否已通过管理员审核，未审核的服务用户看不到
    """
    __tablename__ = "node_service"

    node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mcp_node.id", ondelete="CASCADE"), nullable=False, comment="所属节点ID"
    )
    service_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="服务名称"
    )
    service_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="服务类型标识"
    )
    price_per_call: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0.0, comment="每次调用单价（元）"
    )
    description: Mapped[str | None] = mapped_column(
        Text, default=None, comment="服务详情（富文本 HTML）"
    )
    version: Mapped[str | None] = mapped_column(
        String(50), default=None, comment="服务版本号，如 v1.0.0"
    )
    cover_image: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="服务封面图 URL"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="管理员是否已审核通过"
    )
    params: Mapped[dict | None] = mapped_column(
        JSON, default=None, comment="服务参数定义 [{field,label,type,required,description}]"
    )
    original_params: Mapped[dict | None] = mapped_column(
        JSON, default=None, comment="节点原始参数备份，仅首次创建时写入，用于恢复"
    )
    timeout: Mapped[int] = mapped_column(
        Integer, default=60, comment="任务超时时间（秒），默认60秒。≤60秒同步返回，>60秒异步返回task_id"
    )
