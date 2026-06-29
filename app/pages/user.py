"""
前端页面路由 - Authorization Header 鉴权，无 token 返回中转页自动补鉴权
"""
from fastapi import APIRouter, Request

from app.template import templates

router = APIRouter(tags=["前端页面"])


async def _get_user(request: Request):
    """从 Authorization Header 获取用户，无 token 返回 None"""
    from app.core.security import decode_token
    from app.modules.user.crud import UserCRUD
    from app.modules.role.crud import RoleCRUD

    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else None
    if not token:
        return None, False
    payload = decode_token(token)
    if not payload:
        return None, False
    async with request.app.state.db_session_factory() as db:
        user = await UserCRUD().get_by_id(db, int(payload["sub"]))
        if not user:
            return None, False
        role_ids = await RoleCRUD().get_user_role_ids(db, user.id)
        is_admin = False
        for rid in role_ids:
            role = await RoleCRUD().get_by_id(db, rid)
            if role and role.code == "admin":
                is_admin = True
                break
        return user, is_admin


def _check(request: Request):
    """中转页：让浏览器用 localStorage token 重新请求"""
    from fastapi.responses import HTMLResponse
    resp = templates.TemplateResponse("auth_check.html", {"request": request})
    resp.headers["X-Page-Type"] = "auth-check"
    return resp


async def _render(request: Request, template: str, user, is_admin: bool):
    return templates.TemplateResponse(template, {
        "request": request, "user": user, "is_admin": is_admin,
        "current_path": request.url.path,
        "cfg": await _load_config(request),
    })


async def _load_config(request: Request) -> dict:
    """从数据库加载系统设置"""
    from app.modules.system_config.crud import SystemConfigCRUD
    async with request.app.state.db_session_factory() as db:
        return await SystemConfigCRUD().get_all_grouped(db)


@router.get("/dashboard")
async def dashboard(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "user/dashboard.html", u, a) if u else _check(request)

@router.get("/services")
async def services(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "user/services.html", u, a) if u else _check(request)

@router.get("/tasks")
async def tasks(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "user/tasks.html", u, a) if u else _check(request)

@router.get("/tasks/create")
async def task_create(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "user/task_create.html", u, a) if u else _check(request)

@router.get("/tokens")
async def tokens(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "user/tokens.html", u, a) if u else _check(request)

@router.get("/billing")
async def billing(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "user/billing.html", u, a) if u else _check(request)

@router.get("/profile")
async def profile(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "user/profile.html", u, a) if u else _check(request)

@router.get("/admin")
async def admin(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/dashboard.html", u, a) if u else _check(request)

@router.get("/admin/users")
async def admin_users(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/users.html", u, a) if u else _check(request)

@router.get("/admin/nodes")
async def admin_nodes(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/nodes.html", u, a) if u else _check(request)

@router.get("/admin/recharges")
async def admin_recharges(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/recharges.html", u, a) if u else _check(request)

@router.get("/admin/billing")
async def admin_billing(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/billing.html", u, a) if u else _check(request)

@router.get("/admin/services")
async def admin_services(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/services.html", u, a) if u else _check(request)

@router.get("/admin/config")
async def admin_config(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/config.html", u, a) if u else _check(request)

@router.get("/admin/roles")
async def admin_roles(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/roles.html", u, a) if u else _check(request)

@router.get("/admin/files")
async def admin_files(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/files.html", u, a) if u else _check(request)

@router.get("/admin/ai")
async def admin_ai(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/ai.html", u, a) if u else _check(request)

@router.get("/admin/monitor")
async def admin_monitor(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/monitor.html", u, a) if u else _check(request)

@router.get("/admin/tasks")
async def admin_tasks(request: Request):
    u, a = await _get_user(request)
    return await _render(request, "admin/tasks.html", u, a) if u else _check(request)
