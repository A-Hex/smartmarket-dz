# backend/tests/test_datasets.py
"""API tests for dataset upload, listing, preview, and deletion."""
import io

import pytest
from httpx import AsyncClient

CSV_CONTENT = (
    b"date,region,product,price,marketing_spend,sales\n"
    b"2024-01-01,Alger,Smartphone,50000,1000,12000\n"
    b"2024-01-02,Oran,Laptop,90000,1500,18000\n"
    b"2024-01-03,Alger,,60000,,9000\n"
    b"2024-01-04,Constantine,Tablette,40000,800,7000\n"
)


async def _auth_headers(client: AsyncClient, email: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Co {email}",
            "full_name": "Owner",
            "email": email,
            "password": "StrongPass1!",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_upload_dataset_profiles_columns(client: AsyncClient):
    headers = await _auth_headers(client, "up1@ds.dz")
    files = {"file": ("sales.csv", io.BytesIO(CSV_CONTENT), "text/csv")}

    resp = await client.post("/api/v1/datasets", headers=headers, files=files)
    assert resp.status_code == 201
    body = resp.json()

    assert body["row_count"] == 4
    assert body["column_count"] == 6
    assert body["status"] == "uploaded"

    col_names = {c["name"] for c in body["columns"]}
    assert col_names == {"date", "region", "product", "price", "marketing_spend", "sales"}

    price_col = next(c for c in body["columns"] if c["name"] == "price")
    assert price_col["null_count"] == 0
    sales_col = next(c for c in body["columns"] if c["name"] == "sales")
    assert sales_col["is_target_candidate"] is True


@pytest.mark.asyncio
async def test_reject_unsupported_extension(client: AsyncClient):
    headers = await _auth_headers(client, "up2@ds.dz")
    files = {"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")}

    resp = await client.post("/api/v1/datasets", headers=headers, files=files)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "unsupported_file_type"


@pytest.mark.asyncio
async def test_preview_and_delete_dataset(client: AsyncClient):
    headers = await _auth_headers(client, "up3@ds.dz")
    files = {"file": ("sales.csv", io.BytesIO(CSV_CONTENT), "text/csv")}
    created = await client.post("/api/v1/datasets", headers=headers, files=files)
    dataset_id = created.json()["id"]

    preview = await client.get(f"/api/v1/datasets/{dataset_id}/preview?limit=2", headers=headers)
    assert preview.status_code == 200
    body = preview.json()
    assert body["preview_rows"] == 2
    assert body["total_rows"] == 4
    assert len(body["rows"]) == 2

    deleted = await client.delete(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_dataset_isolated_between_companies(client: AsyncClient):
    headers_a = await _auth_headers(client, "tenantA@ds.dz")
    headers_b = await _auth_headers(client, "tenantB@ds.dz")

    files = {"file": ("sales.csv", io.BytesIO(CSV_CONTENT), "text/csv")}
    created = await client.post("/api/v1/datasets", headers=headers_a, files=files)
    dataset_id = created.json()["id"]

    # Company B must not be able to see Company A's dataset.
    resp = await client.get(f"/api/v1/datasets/{dataset_id}", headers=headers_b)
    assert resp.status_code == 404

    list_b = await client.get("/api/v1/datasets", headers=headers_b)
    assert list_b.json() == []
