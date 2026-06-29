import pytest
from httpx import AsyncClient


class TestFile:
    @pytest.mark.asyncio
    async def test_upload_file(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "filer", "email": "filer@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        resp = await client.post("/api/v1/files/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["code"] == 0
        data = resp.json()["data"]
        assert data["original_name"] == "test.txt"
        assert data["file_size"] > 0
        assert data["storage_type"] == "local"

    @pytest.mark.asyncio
    async def test_list_files(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "flister", "email": "flister@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        await client.post("/api/v1/files/upload",
            files={"file": ("a.txt", b"a", "text/plain")},
            headers={"Authorization": f"Bearer {token}"})
        await client.post("/api/v1/files/upload",
            files={"file": ("b.txt", b"b", "text/plain")},
            headers={"Authorization": f"Bearer {token}"})

        resp = await client.get("/api/v1/files", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["total"] == 2

    @pytest.mark.asyncio
    async def test_get_file(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/register", json={
            "username": "fgetter", "email": "fgetter@test.com", "password": "Test123456",
        })
        token = resp.json()["data"]["token"]

        created = await client.post("/api/v1/files/upload",
            files={"file": ("doc.txt", b"content", "text/plain")},
            headers={"Authorization": f"Bearer {token}"})
        fid = created.json()["data"]["id"]

        resp = await client.get(f"/api/v1/files/{fid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["original_name"] == "doc.txt"

    @pytest.mark.asyncio
    async def test_cannot_access_others_file(self, client: AsyncClient):
        r1 = await client.post("/api/v1/users/register", json={
            "username": "fowner", "email": "fowner@test.com", "password": "Test123456",
        })
        t1 = r1.json()["data"]["token"]
        created = await client.post("/api/v1/files/upload",
            files={"file": ("secret.txt", b"secret", "text/plain")},
            headers={"Authorization": f"Bearer {t1}"})
        fid = created.json()["data"]["id"]

        r2 = await client.post("/api/v1/users/register", json={
            "username": "fintruder", "email": "fintruder@test.com", "password": "Test123456",
        })
        t2 = r2.json()["data"]["token"]

        resp = await client.get(f"/api/v1/files/{fid}", headers={"Authorization": f"Bearer {t2}"})
        assert resp.json()["code"] == 404

    @pytest.mark.asyncio
    async def test_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/files/upload")
        assert resp.status_code == 401
