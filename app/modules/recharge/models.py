"""
充值订单模块 - 数据模型
-----------------------
充值由客服手动操作，不涉及在线支付。
充值完成时：增加用户余额 + 创建流水记录。
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class RechargeOrder(BaseModel):
    """
    充值订单表

    字段说明：
    - operator_id：操作的客服 ID（FK → user）
    - order_status：订单状态 pending（待处理）/ completed（已完成）/ cancelled（已取消）
    - completed_at：完成时间
    """
    __tablename__ = "recharge_order"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False,
        comment="充值用户ID"
    )
    amount: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="充值金额（元）"
    )
    operator_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="SET NULL"),
        default=None, comment="操作客服ID"
    )
    order_status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="订单状态：pending/completed/cancelled"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=None, comment="完成时间"
    )
