"""
用户模块 - API 路由
------------------
提供用户相关的 REST API 接口：

公开接口（不需要登录）：
- POST /api/v1/users/register    注册新用户
- POST /api/v1/users/login       用户登录

需要登录的接口（需要 Bearer Token）：
- GET  /api/v1/users/me          查看自己的信息
- PUT  /api/v1/users/me          更新自己的信息
- PUT  /api/v1/users/me/identity 提交实名认证

鉴权链路：
    公开接口：仅 Depends(get_db)
    需登录接口：Depends(get_db) + Depends(get_current_user)
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, error, paginate
from app.core.security import create_access_token
from app.dependencies import get_db, get_current_user, require_admin
from app.modules.user.schemas import (
    UserRegisterIn,
    UserLoginIn,
    UserUpdateIn,
    UserUpdateIdentityIn,
    UserOut,
)
from app.modules.user.service import UserService

router = APIRouter(prefix="/users", tags=["用户"])
service = UserService()


# ========== 公开接口 ==========


@router.post("/register", summary="用户注册")
async def register(data: UserRegisterIn, db: AsyncSession = Depends(get_db)):
    """
    注册新用户
    - 检查用户名是否已存在
    - 密码 bcrypt 哈希后存储
    - 注册成功直接返回 JWT Token，不需要再登录
    """
    existing = await service.get_by_username(db, data.username)
    if existing:
        return error(code=1001, message="用户名已存在")

    user = await service.register(db, data)
    token = create_access_token(user.id)
    return success(
        {"user": UserOut.model_validate(user).model_dump(), "token": token},
        message="注册成功",
    )


@router.post("/login", summary="用户登录")
async def login(data: UserLoginIn, db: AsyncSession = Depends(get_db)):
    """
    用户登录
    - 验证用户名、密码、账户状态
    - 成功返回 JWT Token
    """
    user = await service.verify_login(db, data.username, data.password)
    if user is None:
        return error(code=1002, message="用户名或密码错误，或账户已被禁用")

    token = create_access_token(user.id)
    return success(
        {"user": UserOut.model_validate(user).model_dump(), "token": token},
        message="登录成功",
    )


# ========== 需登录接口 ==========


@router.get("/me", summary="查看个人信息")
async def get_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    查看当前登录用户的个人信息
    需要 Authorization Header 中携带有效的 Bearer Token
    """
    return success(UserOut.model_validate(current_user).model_dump())


@router.put("/me", summary="更新个人信息")
async def update_me(
    data: UserUpdateIn,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新当前用户的个人信息
    只更新请求体中实际传了的字段，未传的保持原值
    修改邮箱时需提供 email_code 验证码
    """
    updates = data.model_dump(exclude_unset=True)

    if "email" in updates and updates["email"] != current_user.email:
        # 检查邮箱是否被其他用户占用
        existing = await service.crud.get_by_email(db, updates["email"])
        if existing and existing.id != current_user.id:
            return error(code=1001, message="该邮箱已被其他账号使用")
        # 验证邮箱验证码
        code = updates.pop("email_code", None)
        if not code:
            return error(code=1001, message="修改邮箱需要验证码")
        redis: Redis = request.app.state.redis
        stored = await redis.get(f"email_code:{current_user.id}")
        if not stored:
            return error(code=1001, message="验证码已过期，请重新发送")
        expected_code, expected_email = stored.decode().split(":", 1)
        if code != expected_code or updates["email"] != expected_email:
            return error(code=1001, message="验证码错误")
        await redis.delete(f"email_code:{current_user.id}")

    user = await service.update(db, current_user.id, data)
    return success(UserOut.model_validate(user).model_dump(), message="更新成功")


@router.post("/me/send-email-code", summary="发送邮箱验证码")
async def send_email_code(
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送邮箱验证码，用于修改邮箱时验证"""
    from pydantic import BaseModel, EmailStr

    class EmailCodeIn(BaseModel):
        email: EmailStr

    try:
        body = await request.json()
    except Exception:
        body = await request.form()
    email_in = EmailCodeIn(email=body.get("email", ""))

    # 检查邮箱是否被占用
    existing = await service.crud.get_by_email(db, email_in.email)
    if existing:
        return error(code=1001, message="该邮箱已被其他账号使用")

    # 频率限制：每分钟最多 3 次
    redis: Redis = request.app.state.redis
    rate_key = f"email_rate:{current_user.id}"
    count = await redis.get(rate_key)
    if count and int(count) >= 3:
        return error(code=1001, message="发送过于频繁，请稍后再试")
    await redis.incr(rate_key)
    await redis.expire(rate_key, 60)

    # 生成6位数字验证码，存 Redis 5分钟
    import random
    code = "".join(str(random.randint(0, 9)) for _ in range(6))
    await redis.set(f"email_code:{current_user.id}", f"{code}:{email_in.email}", ex=300)

    from app.core.mail import send_verify_code
    ok = await send_verify_code(request.app.state.db_session_factory, email_in.email, code)
    if not ok:
        return error(code=500, message="邮件发送失败，请检查邮箱地址或SMTP配置")

    return success(message="验证码已发送至新邮箱，5分钟内有效")


@router.put("/me/identity", summary="提交实名认证")
async def update_identity(
    data: UserUpdateIdentityIn,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    提交实名认证信息
    提交后不自动通过，需要后台管理员审核
    """
    user = await service.update_identity(db, current_user.id, data)
    return success(
        UserOut.model_validate(user).model_dump(),
        message="实名信息已提交，等待审核",
    )


# ========== 管理端接口 ==========


@router.get("", summary="用户列表（管理员）")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    status: bool | None = Query(None),
    date_from: str | None = Query(None, description="创建时间起始 YYYY-MM-DD"),
    date_to: str | None = Query(None, description="创建时间截止 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    items, total = await service.list(db, page=page, page_size=page_size, keyword=keyword, status=status, date_from=date_from, date_to=date_to)
    return paginate(
        [UserOut.model_validate(item).model_dump() for item in items],
        total, page, page_size,
    )


@router.get("/{user_id}", summary="查看用户详情（管理员）")
async def admin_get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    item = await service.get(db, user_id)
    if not item:
        return error(code=404, message="用户不存在")
    return success(UserOut.model_validate(item).model_dump())


@router.put("/{user_id}", summary="更新用户（管理员）")
async def admin_update_user(
    user_id: int,
    data: UserUpdateIn,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    item = await service.update(db, user_id, data)
    if not item:
        return error(code=404, message="用户不存在")
    return success(UserOut.model_validate(item).model_dump(), message="更新成功")


@router.put("/{user_id}/status", summary="启用/禁用用户（管理员）")
async def admin_toggle_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    user = await service.get(db, user_id)
    if not user:
        return error(code=404, message="用户不存在")
    new_status = not user.status
    item = await service.set_status(db, user_id, new_status)
    # 清除 Redis 缓存使立即生效
    from app.dependencies import get_redis
    return success(
        UserOut.model_validate(item).model_dump(),
        message="用户已" + ("启用" if new_status else "禁用"),
    )


@router.delete("/{user_id}", summary="删除用户（管理员）")
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    user = await service.get(db, user_id)
    if not user:
        return error(code=404, message="用户不存在")
    await service.set_status(db, user_id, False)
    return success(message="用户已删除")


# ========== 忘记密码 ==========


@router.post("/forgot-password", summary="忘记密码")
async def forgot_password(request: Request, db: AsyncSession = Depends(get_db)):
    from pydantic import BaseModel, EmailStr
    import uuid

    class ForgotIn(BaseModel):
        email: EmailStr

    try:
        body = await request.json()
        data = ForgotIn(**body)
    except Exception:
        body = await request.form()
        data = ForgotIn(email=body.get("email", ""))

    user = await service.crud.get_by_email(db, data.email)
    if not user:
        return success(message="如果邮箱已注册，重置链接已发送")

    # 生成重置 token，存 Redis 15 分钟
    token = uuid.uuid4().hex
    from redis.asyncio import Redis
    redis: Redis = request.app.state.redis
    await redis.set(f"reset:{token}", str(user.id), ex=900)

    # 发邮件
    from app.core.mail import send_reset_email
    reset_url = f"{request.base_url}reset-password?token={token}"
    await send_reset_email(request.app.state.db_session_factory, data.email, reset_url)

    return success(message="如果邮箱已注册，重置链接已发送")


@router.post("/reset-password", summary="重置密码")
async def reset_password(request: Request, db: AsyncSession = Depends(get_db)):
    from pydantic import BaseModel, Field

    class ResetIn(BaseModel):
        token: str
        password: str = Field(min_length=6, max_length=128)

    try:
        body = await request.json()
        data = ResetIn(**body)
    except Exception:
        body = await request.form()
        data = ResetIn(token=body.get("token", ""), password=body.get("password", ""))

    redis: Redis = request.app.state.redis
    user_id = await redis.get(f"reset:{data.token}")
    if not user_id:
        return error(code=1001, message="重置链接已过期")

    from app.core.security import hash_password
    await service.crud.update(db, int(user_id), password_hash=hash_password(data.password))
    await redis.delete(f"reset:{data.token}")
    return success(message="密码已重置，请重新登录")
