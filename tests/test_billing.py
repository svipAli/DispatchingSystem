import pytest
from httpx import AsyncClient


class TestBilling:
    @pytest.mark.asyncio
    async def test_view_empty_records(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "bill0", "email": "bill0@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        resp = await client.get("/api/v1/billing", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_view_records(self, client: AsyncClient, session_factory):
        from app.modules.billing.service import BillingService

        resp = await client.post("/api/v1/users/register", json={
            "username": "bill1", "email": "bill1@test.com", "password": "Test123456",
        })
        uid = resp.json()["data"]["user"]["id"]
        token = resp.json()["data"]["token"]

        # 通过 service 层创建几条流水记录
        async with session_factory() as db, db.begin():
            svc = BillingService()
            await svc.create_record(db, user_id=uid, type_="recharge",
                amount=100, balance_before=0, balance_after=100,
                remark="客服充值")
            await svc.create_record(db, user_id=uid, type_="deduct",
                amount=0.05, balance_before=100, balance_after=99.95,
                related_id=1, related_type="task", remark="调用 text-generation")

        resp = await client.get("/api/v1/billing", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["total"] == 2

        # 按类型过滤
        resp = await client.get("/api/v1/billing?type=recharge", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["total"] == 1

    @pytest.mark.asyncio
    async def test_record_detail(self, client: AsyncClient, session_factory):
        from app.modules.billing.service import BillingService

        resp = await client.post("/api/v1/users/register", json={
            "username": "bill2", "email": "bill2@test.com", "password": "Test123456",
        })
        uid = resp.json()["data"]["user"]["id"]
        token = resp.json()["data"]["token"]

        async with session_factory() as db, db.begin():
            svc = BillingService()
            await svc.create_record(db, user_id=uid, type_="deduct",
                amount=0.5, balance_before=50, balance_after=49.5)

        resp = await client.get("/api/v1/billing", headers={"Authorization": f"Bearer {token}"})
        record = resp.json()["data"]["items"][0]
        assert record["amount"] == 0.5
        assert record["balance_before"] == 50.0
        assert record["balance_after"] == 49.5

    @pytest.mark.asyncio
    async def test_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/billing")
        assert resp.status_code == 401
