# backend/tests/test_analytics_api.py
"""API tests for POST /analytics/descriptive and GET /jobs."""
import io

import pytest
from httpx import AsyncClient

CSV_CONTENT = (
    b"date,region,price,marketing_spend,sales\n"
    b"2024-01-01,Alger,50000,1000,12000\n"
    b"2024-01-02,Oran,90000,1500,18000\n"
    b"2024-01-03,Alger,60000,1200,15000\n"
    b"2024-01-04,Constantine,40000,800,7000\n"
    b"2024-01-05,Alger,70000,1300,16000\n"
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


async def _upload(client: AsyncClient, headers: dict) -> str:
    files = {"file": ("sales.csv", io.BytesIO(CSV_CONTENT), "text/csv")}
    resp = await client.post("/api/v1/datasets", headers=headers, files=files)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_descriptive_analysis_returns_stats_and_correlation(client: AsyncClient):
    headers = await _auth_headers(client, "desc1@an.dz")
    dataset_id = await _upload(client, headers)

    resp = await client.post(
        "/api/v1/analytics/descriptive", headers=headers, json={"dataset_id": dataset_id}
    )
    assert resp.status_code == 201
    body = resp.json()

    assert body["row_count"] == 5
    numeric_names = {c["column"] for c in body["numeric_columns"]}
    assert {"price", "marketing_spend", "sales"}.issubset(numeric_names)

    categorical_names = {c["column"] for c in body["categorical_columns"]}
    assert "region" in categorical_names

    assert body["correlation"] is not None
    assert "sales" in body["correlation"]["columns"]
    assert "sales" in body["target_candidates"]


@pytest.mark.asyncio
async def test_descriptive_analysis_creates_job_record(client: AsyncClient):
    headers = await _auth_headers(client, "desc2@an.dz")
    dataset_id = await _upload(client, headers)

    await client.post(
        "/api/v1/analytics/descriptive", headers=headers, json={"dataset_id": dataset_id}
    )

    jobs_resp = await client.get("/api/v1/jobs?type=descriptive", headers=headers)
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "completed"
    assert jobs[0]["progress"] == 100.0
    assert jobs[0]["result"] is not None


@pytest.mark.asyncio
async def test_descriptive_analysis_unknown_column_returns_422(client: AsyncClient):
    headers = await _auth_headers(client, "desc3@an.dz")
    dataset_id = await _upload(client, headers)

    resp = await client.post(
        "/api/v1/analytics/descriptive",
        headers=headers,
        json={"dataset_id": dataset_id, "columns": ["does_not_exist"]},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "unknown_columns"

    # A failed run still leaves an auditable job row.
    jobs_resp = await client.get("/api/v1/jobs?status=failed", headers=headers)
    assert len(jobs_resp.json()) == 1


@pytest.mark.asyncio
async def test_get_single_job(client: AsyncClient):
    headers = await _auth_headers(client, "desc4@an.dz")
    dataset_id = await _upload(client, headers)

    run = await client.post(
        "/api/v1/analytics/descriptive", headers=headers, json={"dataset_id": dataset_id}
    )
    jobs_resp = await client.get("/api/v1/jobs", headers=headers)
    job_id = jobs_resp.json()[0]["id"]

    get_resp = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["type"] == "descriptive"


@pytest.mark.asyncio
async def test_jobs_isolated_between_companies(client: AsyncClient):
    headers_a = await _auth_headers(client, "descA@an.dz")
    headers_b = await _auth_headers(client, "descB@an.dz")
    dataset_id = await _upload(client, headers_a)

    await client.post(
        "/api/v1/analytics/descriptive", headers=headers_a, json={"dataset_id": dataset_id}
    )

    jobs_b = await client.get("/api/v1/jobs", headers=headers_b)
    assert jobs_b.json() == []
