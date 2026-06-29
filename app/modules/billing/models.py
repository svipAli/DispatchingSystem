"""
计费流水模块 - 数据模型
-----------------------
流水记录表是完整的账本，记录每一笔资金变动（充值 + 扣费）。
只追加不修改不删除，保证账目可追溯。
"""
from __future__ import annotations

from sqlalchemy import Integer, String, Float, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class BillingRecord(BaseModel):
    """
    计费流水记录表（账本）

    字段说明：
    - type：recharge（充值）或 deduct（扣费）
    - amount：变动金额（正数）
    - balance_before / balance_after：操作前后用户的余额，方便对账
    - related_id / related_type：关联的业务记录，如(task, 123)或(recharge, 456)
    - 此表只追加不修改不删除，是完整账本
    """
    __tablename__ = "billing_record"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False,
        comment="用户ID"
    )
    type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="类型：recharge（充值）/ deduct（扣费）"
    )
    amount: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="变动金额（元）"
    )
    balance_before: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="操作前余额"
    )
    balance_after: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="操作后余额"
    )
    related_id: Mapped[int | None] = mapped_column(
        Integer, default=None, comment="关联业务记录ID"
    )
    related_type: Mapped[str | None] = mapped_column(
        String(50), default=None, comment="关联类型：task / recharge"
    )
