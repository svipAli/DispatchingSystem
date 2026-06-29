import pytest
from httpx import AsyncClient


class TestRecharge:
    @pytest.mark.asyncio
    async def test_create_order(self, admin_client: AsyncClient):
        # 注册一个普通用户
        resp = await admin_client.post("/api/v1/users/register", json={
            "username": "normal_user", "email": "normal@test.com", "password": "Test123456",
        })
        uid = resp.json()["data"]["user"]["id"]

        # 管理员创建充值订单
        resp = await admin_client.post("/api/v1/recharges", json={
            "user_id": uid, "amount": 100.0, "remark": "月租充值",
        })
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["amount"] == 100.0
        assert resp.json()["data"]["order_status"] == "pending"

    @pytest.mark.asyncio
    async def test_complete_recharge(self, admin_client: AsyncClient, session_factory):
        from app.modules.recharge.service import RechargeService
        from app.modules.recharge.schemas import RechargeCreate

        # 注册用户
        resp = await admin_client.post("/api/v1/users/register", json={
            "username": "user2", "email": "user2@test.com", "password": "Test123456",
        })
        uid = resp.json()["data"]["user"]["id"]

        # 创建充值订单
        async with session_factory() as db, db.begin():
            svc = RechargeService()
            order = await svc.create(db, RechargeCreate(user_id=uid, amount=50, remark="测试充值"))
            oid = order.id

        # 管理员确认完成充值
        resp = await admin_client.post(f"/api/v1/recharges/{oid}/complete")
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["order_status"] == "completed"

        # 重新登录用户获取最新余额
        resp = await admin_client.post("/api/v1/users/login", json={
            "username": "user2", "password": "Test123456",
        })
        assert resp.json()["data"]["user"]["balance"] == 50.0
