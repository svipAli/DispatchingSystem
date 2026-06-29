"""
用户模块 - 数据模型
-----------------
用户表是所有业务的核心，与角色、订单、任务等模块关联。
继承 BaseModel 获得公共字段（id/remark/status/created_at/updated_at）。

字段说明：
    基本信息：username、email、phone、password_hash
    账户余额：balance（余额）、expire_date（月租到期时间）
    实名认证：real_name、id_card_number、id_card_front_url、id_card_back_url、is_verified
    状态控制：status（False=禁用/软删除）、is_verified（实名是否通过）

注意：__table_args__ = {"quote": True} 是因为 "user" 是 PostgreSQL 保留字，
不加引号会导致 SQL 语法错误。
"""
from datetime import datetime
from sqlalchemy import String, Float, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class User(BaseModel):
    __tablename__ = "user"
    # user 是 PostgreSQL 保留关键字，ORM 操作会自动处理引号
    # 注意：__table_args__ 中的 quote 会破坏 ForeignKey 解析，已移除
    __tablename__ = "user"

    # ===== 账号信息 =====
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False, comment="用户名"
    )
    email: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, comment="邮箱"
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), default=None, comment="手机号"
    )
    password_hash: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="bcrypt 密码哈希"
    )

    # ===== 账户余额与订阅 =====
    balance: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0.0, server_default="0", comment="账户余额（元）"
    )
    expire_date: Mapped[datetime | None] = mapped_column(
        default=None, comment="月租到期时间，到期后不能调用 API"
    )

    # ===== 实名认证 =====
    real_name: Mapped[str | None] = mapped_column(
        String(50), default=None, comment="真实姓名"
    )
    address: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="联系地址"
    )
    id_card_number: Mapped[str | None] = mapped_column(
        String(18), default=None, comment="身份证号码"
    )
    id_card_front_url: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="身份证正面照片 URL"
    )
    id_card_back_url: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="身份证反面照片 URL"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
        comment="是否已通过实名认证（后台人工审核）"
    )
