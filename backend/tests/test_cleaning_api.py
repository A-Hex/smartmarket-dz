# backend/tests/test_cleaning_api.py
"""API tests for POST /datasets/{id}/cleaning and GET /cleaning/runs/{id}."""
import io

import pytest
from httpx import AsyncClient

CSV_WITH_ISSUES = (
    b"date,region,price,marketing_spend,sales\n"
    b"2024-01-01,Alger,50000,1000,12000\n"
    b"2024-01-02,Oran,,1500,18000\n"
    b"2024-01-03,Alger,60000,,9000\n"
    b"2024-01-04,Constantine,40000,800,7000\n"
    b"2024-01-05,Alger,999999,900,2000000\n"
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
    files = {"file": ("sales.csv", io.BytesIO(CSV_WITH_ISSUES), "text/csv")}
    resp = await client.post("/api/v1/datasets", headers=headers, files=files)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_cleaning_run_reduces_missing_values_and_updates_dataset(client: AsyncClient):
    headers = await _auth_headers(client, "clean1@ds.dz")
    dataset_id = await _upload(client, headers)

    config = {
        "columns": [
            {"column": "price", "missing_strategy": "median"},
            {"column": "marketing_spend", "missing_strategy": "mean"},
            {
                "column": "sales",
                "outlier_method": "iqr",
                "outlier_action": "cap",
            },
        ]
    }
    resp = await client.post(
        f"/api/v1/datasets/{dataset_id}/cleaning", headers=headers, json=config
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed"

    report = body["report"]
    assert report["missingness_before"]["price"] == 1
    assert report["missingness_after"]["price"] == 0
    assert report["missingness_before"]["marketing_spend"] == 1
    assert report["missingness_after"]["marketing_spend"] == 0

    price_report = next(c for c in report["per_column"] if c["column"] == "price")
    assert price_report["null_count_after"] == 0

    sales_report = next(c for c in report["per_column"] if c["column"] == "sales")
    assert sales_report["outliers_detected"] >= 1

    # Dataset should now be marked cleaned and reflect the cleaned profile.
    dataset_resp = await client.get(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert dataset_resp.status_code == 200
    assert dataset_resp.json()["status"] == "cleaned"


@pytest.mark.asyncio
async def test_get_cleaning_run_report(client: AsyncClient):
    headers = await _auth_headers(client, "clean2@ds.dz")
    dataset_id = await _upload(client, headers)

    run_resp = await client.post(
        f"/api/v1/datasets/{dataset_id}/cleaning",
        headers=headers,
        json={"columns": [{"column": "price", "missing_strategy": "mean"}]},
    )
    run_id = run_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/cleaning/runs/{run_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_cleaning_run_isolated_between_companies(client: AsyncClient):
    headers_a = await _auth_headers(client, "cleanA@ds.dz")
    headers_b = await _auth_headers(client, "cleanB@ds.dz")
    dataset_id = await _upload(client, headers_a)

    run_resp = await client.post(
        f"/api/v1/datasets/{dataset_id}/cleaning",
        headers=headers_a,
        json={"columns": [{"column": "price", "missing_strategy": "mean"}]},
    )
    run_id = run_resp.json()["id"]

    forbidden = await client.get(f"/api/v1/cleaning/runs/{run_id}", headers=headers_b)
    assert forbidden.status_code == 404
