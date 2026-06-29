"""
用户模块 - Pydantic 数据校验模型
-------------------------------
设计要点：
- 入参 Schema 和出参 Schema 严格分离，绝不把 password_hash 输出给前端
- 使用 EmailStr 自动校验邮箱格式
- UserUpdateIn 所有字段可选，用 exclude_unset 只更新实际传了的字段
"""
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


# ========== 入参 Schema（客户端发送的请求体） ==========


class UserRegisterIn(BaseModel):
    """用户注册请求体"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱（自动校验格式）")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    phone: str | None = None


class UserLoginIn(BaseModel):
    """用户登录请求体"""

    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class UserUpdateIn(BaseModel):
    """更新用户信息的请求体，所有字段可选（管理员可修改全部字段）"""

    username: str | None = Field(None, min_length=3, max_length=50)
    email: EmailStr | None = None
    email_code: str | None = Field(None, description="修改邮箱时的验证码")
    phone: str | None = None
    password: str | None = Field(None, min_length=6, max_length=128, description="新密码，留空不修改")
    balance: float | None = None
    expire_date: str | None = Field(None, description="月租到期日期 YYYY-MM-DD")
    real_name: str | None = None
    address: str | None = None
    id_card_number: str | None = None
    is_verified: bool | None = None
    remark: str | None = None
    status: bool | None = None


class UserUpdateIdentityIn(BaseModel):
    """提交实名认证的请求体，所有字段必填"""

    real_name: str = Field(..., min_length=1, max_length=50, description="真实姓名")
    id_card_number: str = Field(
        ..., min_length=15, max_length=18, description="身份证号码"
    )
    id_card_front_url: str = Field(..., min_length=1, description="身份证正面照片URL")
    id_card_back_url: str = Field(..., min_length=1, description="身份证反面照片URL")


# ========== 出参 Schema（返回给客户端的响应） ==========


class UserOut(BaseModel):
    """用户信息的输出格式，不含 password_hash"""

    id: int
    username: str
    email: str
    phone: str | None
    balance: float
    expire_date: datetime | None
    real_name: str | None
    address: str | None
    id_card_number: str | None
    id_card_front_url: str | None
    id_card_back_url: str | None
    is_verified: bool
    status: bool
    remark: str | None
    created_at: datetime
    updated_at: datetime

    # 允许从 SQLAlchemy ORM 对象直接转换
    model_config = {"from_attributes": True}
