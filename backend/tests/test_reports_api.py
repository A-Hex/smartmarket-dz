# backend/tests/test_reports_api.py
"""API tests for POST /reports/generate and GET /reports/{id}/download."""
import io

import numpy as np
import pandas as pd
import pytest
from httpx import AsyncClient


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


def _sales_csv_bytes() -> bytes:
    rng = np.random.default_rng(4)
    n = 100
    marketing = rng.uniform(100, 5000, n)
    price = rng.uniform(1000, 50000, n)
    sales = 500 + 3.0 * marketing - 0.02 * price + rng.normal(0, 200, n)
    df = pd.DataFrame({"marketing_spend": marketing, "price": price, "sales": sales})
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


async def _upload(client: AsyncClient, headers: dict, content: bytes) -> str:
    files = {"file": ("sales.csv", io.BytesIO(content), "text/csv")}
    resp = await client.post("/api/v1/datasets", headers=headers, files=files)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_generate_and_download_pdf_report(client: AsyncClient):
    headers = await _auth_headers(client, "rep1@reports.dz")
    dataset_id = await _upload(client, headers, _sales_csv_bytes())

    gen_resp = await client.post(
        "/api/v1/reports/generate",
        headers=headers,
        json={"dataset_id": dataset_id, "format": "pdf"},
    )
    assert gen_resp.status_code == 201
    body = gen_resp.json()
    assert body["format"] == "pdf"
    assert body["type"] == "executive"

    download_resp = await client.get(f"/api/v1/reports/{body['id']}/download", headers=headers)
    assert download_resp.status_code == 200
    assert download_resp.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_generate_and_download_xlsx_report_with_full_pipeline(client: AsyncClient):
    headers = await _auth_headers(client, "rep2@reports.dz")
    dataset_id = await _upload(client, headers, _sales_csv_bytes())

    # Run the full analysis chain first so the workbook has real content.
    reg = await client.post(
        "/api/v1/analytics/regression",
        headers=headers,
        json={"dataset_id": dataset_id, "target": "sales", "features": ["marketing_spend", "price"]},
    )
    assert reg.status_code == 201
    val = await client.post(
        "/api/v1/analytics/validation", headers=headers, json={"model_id": reg.json()["model_id"]}
    )
    assert val.status_code == 201

    gen_resp = await client.post(
        "/api/v1/reports/generate",
        headers=headers,
        json={"dataset_id": dataset_id, "format": "xlsx"},
    )
    assert gen_resp.status_code == 201
    body = gen_resp.json()
    assert body["format"] == "xlsx"
    assert body["type"] == "raw_results"

    download_resp = await client.get(f"/api/v1/reports/{body['id']}/download", headers=headers)
    assert download_resp.status_code == 200
    assert download_resp.content[:2] == b"PK"  # xlsx is a zip archive


@pytest.mark.asyncio
async def test_report_download_isolated_between_companies(client: AsyncClient):
    headers_a = await _auth_headers(client, "repTenantA@reports.dz")
    headers_b = await _auth_headers(client, "repTenantB@reports.dz")
    dataset_id = await _upload(client, headers_a, _sales_csv_bytes())

    gen_resp = await client.post(
        "/api/v1/reports/generate", headers=headers_a, json={"dataset_id": dataset_id, "format": "pdf"}
    )
    report_id = gen_resp.json()["id"]

    resp = await client.get(f"/api/v1/reports/{report_id}/download", headers=headers_b)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_report_generate_unknown_dataset_404(client: AsyncClient):
    headers = await _auth_headers(client, "rep3@reports.dz")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        "/api/v1/reports/generate", headers=headers, json={"dataset_id": fake_id, "format": "pdf"}
    )
    assert resp.status_code == 404
