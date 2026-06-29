"""
RBAC 模块集成测试（role + permission + menu）
"""
import pytest
from httpx import AsyncClient


class TestRoleAPI:
    @pytest.mark.asyncio
    async def test_create_role(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/v1/roles", json={
            "name": "测试角色", "code": "test_role", "description": "测试用"
        })
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["code"] == "test_role"

    @pytest.mark.asyncio
    async def test_create_role_duplicate_code(self, admin_client: AsyncClient):
        await admin_client.post("/api/v1/roles", json={"name": "R1", "code": "dup_role"})
        resp = await admin_client.post("/api/v1/roles", json={"name": "R2", "code": "dup_role"})
        assert resp.json()["code"] == 1001

    @pytest.mark.asyncio
    async def test_list_roles(self, admin_client: AsyncClient):
        await admin_client.post("/api/v1/roles", json={"name": "A", "code": "role_a"})
        await admin_client.post("/api/v1/roles", json={"name": "B", "code": "role_b"})
        resp = await admin_client.get("/api/v1/roles")
        assert resp.json()["data"]["total"] >= 2

    @pytest.mark.asyncio
    async def test_get_role(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/v1/roles", json={"name": "G", "code": "role_g"})
        rid = resp.json()["data"]["id"]
        resp = await admin_client.get(f"/api/v1/roles/{rid}")
        assert resp.json()["data"]["name"] == "G"

    @pytest.mark.asyncio
    async def test_update_role(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/v1/roles", json={"name": "旧名", "code": "update_role"})
        rid = resp.json()["data"]["id"]
        resp = await admin_client.put(f"/api/v1/roles/{rid}", json={"name": "新名"})
        assert resp.json()["data"]["name"] == "新名"

    @pytest.mark.asyncio
    async def test_assign_roles(self, admin_client: AsyncClient):
        r1 = await admin_client.post("/api/v1/roles", json={"name": "R1", "code": "r1"})
        r2 = await admin_client.post("/api/v1/roles", json={"name": "R2", "code": "r2"})
        # 先注册用户
        u = await admin_client.post("/api/v1/users/register", json={
            "username": "roletest", "email": "role@test.com", "password": "Test123456",
        })
        uid = u.json()["data"]["user"]["id"]
        # 分配角色
        resp = await admin_client.post("/api/v1/roles/assign", json={
            "user_id": uid,
            "role_ids": [r1.json()["data"]["id"], r2.json()["data"]["id"]],
        })
        assert resp.json()["code"] == 0
        # 查用户角色
        resp = await admin_client.get(f"/api/v1/roles/user/{uid}")
        assert len(resp.json()["data"]["role_ids"]) == 2


class TestPermissionAPI:
    @pytest.mark.asyncio
    async def test_create_permission(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/v1/permissions", json={
            "name": "查看用户", "code": "user:view", "module": "user",
        })
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["code"] == "user:view"

    @pytest.mark.asyncio
    async def test_list_by_module(self, admin_client: AsyncClient):
        await admin_client.post("/api/v1/permissions", json={
            "name": "P1", "code": "task:create", "module": "task",
        })
        await admin_client.post("/api/v1/permissions", json={
            "name": "P2", "code": "task:delete", "module": "task",
        })
        resp = await admin_client.get("/api/v1/permissions?module=task")
        assert resp.json()["data"]["total"] >= 2

    @pytest.mark.asyncio
    async def test_assign_permissions(self, admin_client: AsyncClient):
        r = await admin_client.post("/api/v1/roles", json={"name": "PR", "code": "perm_role"})
        p = await admin_client.post("/api/v1/permissions", json={
            "name": "测试权限", "code": "test:perm", "module": "test",
        })
        resp = await admin_client.post("/api/v1/permissions/assign", json={
            "role_id": r.json()["data"]["id"],
            "permission_ids": [p.json()["data"]["id"]],
        })
        assert resp.json()["code"] == 0


class TestMenuAPI:
    @pytest.mark.asyncio
    async def test_create_menu(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/v1/menus", json={
            "name": "系统管理", "icon": "settings", "sort": 1,
        })
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["name"] == "系统管理"

    @pytest.mark.asyncio
    async def test_create_child_menu(self, admin_client: AsyncClient):
        parent = await admin_client.post("/api/v1/menus", json={
            "name": "父菜单", "sort": 1,
        })
        pid = parent.json()["data"]["id"]
        resp = await admin_client.post("/api/v1/menus", json={
            "name": "子菜单", "parent_id": pid, "path": "/child", "sort": 1,
        })
        assert resp.json()["data"]["parent_id"] == pid

    @pytest.mark.asyncio
    async def test_menu_tree(self, admin_client: AsyncClient):
        # 创建两级菜单
        p = await admin_client.post("/api/v1/menus", json={"name": "一级", "sort": 1})
        pid = p.json()["data"]["id"]
        await admin_client.post("/api/v1/menus", json={
            "name": "二级A", "parent_id": pid, "sort": 1,
        })
        await admin_client.post("/api/v1/menus", json={
            "name": "二级B", "parent_id": pid, "sort": 2,
        })
        resp = await admin_client.get("/api/v1/menus/tree")
        data = resp.json()["data"]
        assert len(data) >= 1
        assert "children" in data[0]

    @pytest.mark.asyncio
    async def test_assign_menus(self, admin_client: AsyncClient):
        r = await admin_client.post("/api/v1/roles", json={"name": "MR", "code": "menu_role"})
        m = await admin_client.post("/api/v1/menus", json={"name": "测试菜单", "sort": 1})
        resp = await admin_client.post("/api/v1/menus/assign", json={
            "role_id": r.json()["data"]["id"],
            "menu_ids": [m.json()["data"]["id"]],
        })
        assert resp.json()["code"] == 0
