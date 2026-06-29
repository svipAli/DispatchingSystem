"""
任务调度模块 - 数据模型
-----------------------
任务记录表是平台核心，记录了每一次 MCP 服务调用的完整生命周期。
用户提交任务 → 调度到节点 → 执行 → 返回结果 → 扣费。
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class Task(BaseModel):
    """
    任务记录表

    字段说明：
    - task_type：用户自定义的任务类型标签
    - service_type：调用的 MCP 服务类型（如 text-generation）
    - request_params：调用时传入的参数（JSON）
    - result：执行完成后返回的结果（JSON），未完成时为空
    - status：queued（排队中）→ running（执行中）→ completed（完成）/ failed（失败）/ cancelled（取消）
    - node_id：被调度到哪个 MCP 节点上执行，未分配时为空
    - cost：本次调用扣费金额
    - api_token_id：使用哪个 API Token 调用的（可空，前端提交时不需要 Token）
    - started_at / finished_at：执行开始和结束时间
    """
    __tablename__ = "task"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="提交任务的用户ID"
    )
    api_token_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("api_token.id", ondelete="SET NULL"),
        default=None, comment="使用的 API Token ID"
    )
    task_type: Mapped[str] = mapped_column(
        String(50), default="mcp_call", comment="任务类型"
    )
    service_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="调用的 MCP 服务类型"
    )
    request_params: Mapped[dict | None] = mapped_column(
        JSON, default=None, comment="请求参数（JSON）"
    )
    result: Mapped[dict | None] = mapped_column(
        JSON, default=None, comment="执行结果（JSON）"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="queued", index=True,
        comment="状态：queued/running/completed/failed/cancelled"
    )
    node_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("mcp_node.id", ondelete="SET NULL"),
        default=None, comment="被分配到的节点ID"
    )
    cost: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0.0, comment="扣费金额（元）"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, default=None, comment="失败原因"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=None, comment="开始执行时间"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=None, comment="完成时间"
    )
