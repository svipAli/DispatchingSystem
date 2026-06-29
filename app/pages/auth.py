"""
前端页面路由 - 登录/注册（Authorization Header 鉴权）
登录/注册 POST 返回 JSON token，前端存 localStorage 后 navigate 跳转
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.template import templates
from app.dependencies import get_db
from app.modules.user.schemas import UserRegisterIn
from app.modules.user.service import UserService
from app.core.security import create_access_token

router = APIRouter(tags=["前端页面 - 认证"])
user_service = UserService()


async def _get_config(request: Request) -> dict:
    from app.modules.system_config.crud import SystemConfigCRUD
    async with request.app.state.db_session_factory() as db:
        return await SystemConfigCRUD().get_all_grouped(db)


async def _verify_captcha(request: Request, form) -> bool:
    """校验图形验证码"""
    captcha_id = form.get("captcha_id", "")
    captcha_code = form.get("captcha_code", "").upper()
    if not captcha_id or not captcha_code:
        return False
    redis = request.app.state.redis
    answer = await redis.get(f"captcha:{captcha_id}")
    if answer is None:
        return False
    await redis.delete(f"captcha:{captcha_id}")
    return answer == captcha_code


@router.get("/login")
async def login_page(request: Request):
    cfg = await _get_config(request)
    return templates.TemplateResponse("auth/login.html", {"request": request, "cfg": cfg})


@router.get("/forgot-password")
async def forgot_password_page(request: Request):
    cfg = await _get_config(request)
    return templates.TemplateResponse("auth/forgot.html", {"request": request, "cfg": cfg})


@router.get("/reset-password")
async def reset_password_page(request: Request):
    cfg = await _get_config(request)
    return templates.TemplateResponse("auth/reset.html", {"request": request, "cfg": cfg})


@router.get("/register")
async def register_page(request: Request):
    cfg = await _get_config(request)
    return templates.TemplateResponse("auth/register.html", {"request": request, "cfg": cfg})


@router.post("/login")
async def do_login(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    if not await _verify_captcha(request, form):
        return JSONResponse(status_code=400, content={"code": 1003, "message": "验证码错误"})

    user = await user_service.verify_login(
        db, form.get("username", ""), form.get("password", "")
    )
    if user is None:
        return JSONResponse(
            status_code=400,
            content={"code": 1002, "message": "用户名或密码错误，或账户已被禁用"},
        )

    token = create_access_token(user.id)
    return JSONResponse(content={"code": 0, "data": {"token": token}, "message": "登录成功"})


@router.post("/register")
async def do_register(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    if not await _verify_captcha(request, form):
        return JSONResponse(status_code=400, content={"code": 1003, "message": "验证码错误"})

    username = form.get("username", "")
    email = form.get("email", "")
    password = form.get("password", "")
    password_confirm = form.get("password_confirm", "")

    if password != password_confirm:
        return JSONResponse(
            status_code=400,
            content={"code": 1001, "message": "两次密码不一致"},
        )

    existing = await user_service.get_by_username(db, username)
    if existing:
        return JSONResponse(
            status_code=400,
            content={"code": 1002, "message": "用户名已存在"},
        )

    try:
        data = UserRegisterIn(username=username, email=email, password=password)
        user = await user_service.register(db, data)
        token = create_access_token(user.id)
        return JSONResponse(content={"code": 0, "data": {"token": token}, "message": "注册成功"})
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"code": 1003, "message": str(e)},
        )
