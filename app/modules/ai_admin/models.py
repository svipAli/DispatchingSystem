"""
AI 助手聊天记录 - 数据模型
"""
from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class ChatMessage(BaseModel):
    __tablename__ = "chat_message"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="user / assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False)
