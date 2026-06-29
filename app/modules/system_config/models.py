"""
系统设置模块 - 数据模型
--------------------
系统配置的键值存储，代替硬编码的可变配置。
放这里的配置改了以后即时生效，不需要重启服务。
与 .env 的区别：
- .env：数据库连接、Redis 地址、JWT 密钥（改了要重启）
- system_config 表：站点标题、SMTP、COS 密钥、客服联系方式（改了立即生效）
"""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class SystemConfig(BaseModel):
    """
    系统配置表

    字段说明：
    - key：配置键名，全局唯一，如 site_title、smtp_host
    - value：配置值，TEXT 类型可存长文本（如富文本 HTML）
    - group：配置分组，便于后台管理分类展示
            常用分组：site（站点）、email（邮件）、sms（短信）、storage（存储）、general（通用）
    - description：该配置项的描述说明，给后台管理员看的
    """
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False, comment="配置键名"
    )
    value: Mapped[str] = mapped_column(Text, default="", comment="配置值")
    group: Mapped[str] = mapped_column(
        String(50), default="general", comment="配置分组：site/email/sms/storage/general"
    )
    description: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="配置说明"
    )
