"""
权限校验模块（RBAC）
------------------
- PermissionChecker：基于"权限标识"的细粒度检查，用于 API 接口级别的鉴权
- require_admin：简单的管理员角色检查函数
- 前端隐藏菜单只是体验优化，这里的 Depends 注入才是真正的安全防线
"""
from fastapi import Depends, HTTPException, Request
from app.modules.user.models import User


class PermissionChecker:
    """
    权限校验依赖注入类（FastAPI Depends 风格）

    用法举例：
        require_task_create = PermissionChecker("task:create")
        require_user_delete = PermissionChecker("user:delete")

        @router.post("/tasks")
        async def create_task(current_user: User = Depends(require_task_create)):
            ...

    校验流程：
        1. 用户必须已登录（通过 get_current_user 获取 current_user）
        2. 如果用户是 admin 角色 → 直接放行（超级管理员）
        3. 否则检查用户的所有角色拥有的权限集合
        4. 如果缺少任一 required_permissions → 返回 403
    """

    def __init__(self, *required_permissions: str):
        """
        :param required_permissions: 访问该接口需要的权限标识，如 "user:delete", "task:create"
        """
        self.required_permissions = set(required_permissions)

    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(),
    ) -> User:
        # 第一步：确保用户已登录
        if not current_user:
            raise HTTPException(status_code=401, detail="请先登录")

        # 第二步：管理员角色直接放行，不检查具体权限
        if hasattr(current_user, "roles"):
            role_codes = [r.code for r in current_user.roles]
            if "admin" in role_codes:
                return current_user

        # 第三步：没有指定权限要求，视为任何登录用户可访问
        if not self.required_permissions:
            return current_user

        # 第四步：收集用户的所有权限
        user_permissions = set()
        if hasattr(current_user, "roles"):
            for role in current_user.roles:
                for perm in role.permissions:
                    user_permissions.add(perm.code)

        # 第五步：检查是否拥有所有必需的权限
        if not self.required_permissions.issubset(user_permissions):
            raise HTTPException(status_code=403, detail="无权限访问")

        return current_user


def require_admin(current_user: User = None) -> User:
    """
    简单的管理员角色校验函数
    只检查是否有 admin 角色，不检查具体权限。
    用于后台管理接口的统一守卫。

    用法：@router.delete("/users/{id}", dependencies=[Depends(require_admin)])
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    if hasattr(current_user, "roles"):
        role_codes = [r.code for r in current_user.roles]
        if "admin" not in role_codes:
            raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
