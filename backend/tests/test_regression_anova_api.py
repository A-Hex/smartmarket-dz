# backend/tests/test_regression_anova_api.py
"""API tests for POST /analytics/regression and POST /analytics/anova."""
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


def _regression_csv_bytes() -> bytes:
    rng = np.random.default_rng(42)
    n = 150
    marketing = rng.uniform(100, 5000, n)
    price = rng.uniform(1000, 50000, n)
    region = rng.choice(["Alger", "Oran", "Constantine"], n)
    noise = rng.normal(0, 200, n)
    sales = 500 + 3.0 * marketing - 0.02 * price + noise
    df = pd.DataFrame(
        {"marketing_spend": marketing, "price": price, "region": region, "sales": sales}
    )
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


async def _upload_dataset(client: AsyncClient, headers: dict) -> str:
    files = {"file": ("sales.csv", io.BytesIO(_regression_csv_bytes()), "text/csv")}
    resp = await client.post("/api/v1/datasets", headers=headers, files=files)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_regression_endpoint_returns_significant_coefficient(client: AsyncClient):
    headers = await _auth_headers(client, "reg1@analytics.dz")
    dataset_id = await _upload_dataset(client, headers)

    resp = await client.post(
        "/api/v1/analytics/regression",
        headers=headers,
        json={
            "dataset_id": dataset_id,
            "target": "sales",
            "features": ["marketing_spend", "price"],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["r_squared"] > 0.8
    assert "model_id" in body

    marketing_coef = next(c for c in body["coefficients"] if "marketing_spend" in c["term"])
    assert marketing_coef["significant"] is True

    # The job should be queryable afterward.
    jobs_resp = await client.get("/api/v1/jobs?type=regression", headers=headers)
    assert jobs_resp.status_code == 200
    assert len(jobs_resp.json()) == 1
    assert jobs_resp.json()[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_regression_endpoint_rejects_unknown_feature(client: AsyncClient):
    headers = await _auth_headers(client, "reg2@analytics.dz")
    dataset_id = await _upload_dataset(client, headers)

    resp = await client.post(
        "/api/v1/analytics/regression",
        headers=headers,
        json={"dataset_id": dataset_id, "target": "sales", "features": ["nonexistent_col"]},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "regression_failed"


@pytest.mark.asyncio
async def test_anova_endpoint_returns_tukey_table(client: AsyncClient):
    headers = await _auth_headers(client, "anova1@analytics.dz")
    dataset_id = await _upload_dataset(client, headers)

    resp = await client.post(
        "/api/v1/analytics/anova",
        headers=headers,
        json={"dataset_id": dataset_id, "factor": "region", "response": "sales"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert set(body["groups"]) == {"Alger", "Oran", "Constantine"}
    assert "f_statistic" in body
    assert "interpretation" in body


@pytest.mark.asyncio
async def test_anova_endpoint_dataset_not_found_for_other_company(client: AsyncClient):
    headers_a = await _auth_headers(client, "tenantA@analytics.dz")
    headers_b = await _auth_headers(client, "tenantB@analytics.dz")
    dataset_id = await _upload_dataset(client, headers_a)

    resp = await client.post(
        "/api/v1/analytics/anova",
        headers=headers_b,
        json={"dataset_id": dataset_id, "factor": "region", "response": "sales"},
    )
    assert resp.status_code == 404
