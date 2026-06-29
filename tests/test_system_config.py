import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestSystemConfigAPI:
    """系统设置模块 API 接口测试"""

    @pytest.mark.asyncio
    async def test_create_config(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/v1/system-configs", json={
            "key": "site_title",
            "value": "我的调度平台",
            "group": "site",
            "description": "站点标题",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["key"] == "site_title"
        assert data["data"]["id"] > 0

    @pytest.mark.asyncio
    async def test_get_config(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/v1/system-configs", json={
            "key": "site_logo", "value": "/static/logo.png", "group": "site",
        })
        config_id = resp.json()["data"]["id"]

        resp = await admin_client.get(f"/api/v1/system-configs/{config_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["key"] == "site_logo"

    @pytest.mark.asyncio
    async def test_get_not_found(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/system-configs/99999")
        assert resp.json()["code"] == 404

    @pytest.mark.asyncio
    async def test_list_configs(self, admin_client: AsyncClient):
        await admin_client.post("/api/v1/system-configs", json={
            "key": "smtp_host", "value": "smtp.qq.com", "group": "email",
        })
        await admin_client.post("/api/v1/system-configs", json={
            "key": "smtp_port", "value": "465", "group": "email",
        })

        resp = await admin_client.get("/api/v1/system-configs?group=email")
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["total"] >= 2
        assert all(item["group"] == "email" for item in data["data"]["items"])

    @pytest.mark.asyncio
    async def test_update_config(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/v1/system-configs", json={
            "key": "old_key", "value": "old_value",
        })
        config_id = resp.json()["data"]["id"]

        resp = await admin_client.put(f"/api/v1/system-configs/{config_id}", json={
            "value": "new_value",
            "description": "更新后的描述",
        })
        assert resp.json()["data"]["value"] == "new_value"
        assert resp.json()["data"]["description"] == "更新后的描述"

    @pytest.mark.asyncio
    async def test_pagination(self, admin_client: AsyncClient):
        for i in range(5):
            await admin_client.post("/api/v1/system-configs", json={
                "key": f"test_key_{i}", "value": str(i),
            })

        resp = await admin_client.get("/api/v1/system-configs?page=1&page_size=2")
        data = resp.json()
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 2
        assert len(data["data"]["items"]) <= 2


class TestSystemConfigService:
    """系统设置模块 Service 层测试（不经过 HTTP）"""

    @pytest.mark.asyncio
    async def test_create_and_get(self, session_factory):
        from app.modules.system_config.service import SystemConfigService
        from app.modules.system_config.schemas import SystemConfigCreate

        svc = SystemConfigService()
        async with session_factory() as db:
            data = SystemConfigCreate(key="test_key", value="test_value", group="test")
            item = await svc.create(db, data)
            assert item.id > 0
            assert item.key == "test_key"

            found = await svc.get_by_key(db, "test_key")
            assert found is not None
            assert found.value == "test_value"

            await db.rollback()

    @pytest.mark.asyncio
    async def test_list(self, session_factory):
        from app.modules.system_config.service import SystemConfigService
        from app.modules.system_config.schemas import SystemConfigCreate

        svc = SystemConfigService()
        async with session_factory() as db:
            for i in range(3):
                data = SystemConfigCreate(key=f"k{i}", value=f"v{i}")
                await svc.create(db, data)

            items, total = await svc.list(db, page=1, page_size=2)
            assert total == 3
            assert len(items) == 2

            await db.rollback()

    @pytest.mark.asyncio
    async def test_update(self, session_factory):
        from app.modules.system_config.service import SystemConfigService
        from app.modules.system_config.schemas import SystemConfigCreate, SystemConfigUpdate

        svc = SystemConfigService()
        async with session_factory() as db:
            item = await svc.create(db, SystemConfigCreate(key="upd", value="old"))
            updated = await svc.update(db, item.id, SystemConfigUpdate(value="new"))
            assert updated.value == "new"

            await db.rollback()

    @pytest.mark.asyncio
    async def test_default_status_true(self, session_factory):
        from app.modules.system_config.service import SystemConfigService
        from app.modules.system_config.schemas import SystemConfigCreate

        svc = SystemConfigService()
        async with session_factory() as db:
            item = await svc.create(db, SystemConfigCreate(key="status_test", value="1"))
            assert item.status is True
            await db.rollback()
