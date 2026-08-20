# backend/tests/test_validation_api.py
"""API tests for POST /analytics/validation, chained after a real regression fit."""
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


def _collinear_csv_bytes() -> bytes:
    rng = np.random.default_rng(9)
    n = 250
    marketing_spend = rng.uniform(100, 5000, n)
    marketing_spend_2 = marketing_spend * 0.98 + rng.normal(0, 5, n)  # deliberately collinear
    price = rng.uniform(1000, 50000, n)
    sales = 500 + 3.0 * marketing_spend - 0.02 * price + rng.normal(0, 200, n)
    df = pd.DataFrame(
        {
            "marketing_spend": marketing_spend,
            "marketing_spend_2": marketing_spend_2,
            "price": price,
            "sales": sales,
        }
    )
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


async def _upload_dataset(client: AsyncClient, headers: dict) -> str:
    files = {"file": ("sales.csv", io.BytesIO(_collinear_csv_bytes()), "text/csv")}
    resp = await client.post("/api/v1/datasets", headers=headers, files=files)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_validation_flags_collinear_features_as_vif_fail(client: AsyncClient):
    headers = await _auth_headers(client, "val1@analytics.dz")
    dataset_id = await _upload_dataset(client, headers)

    reg_resp = await client.post(
        "/api/v1/analytics/regression",
        headers=headers,
        json={
            "dataset_id": dataset_id,
            "target": "sales",
            "features": ["marketing_spend", "marketing_spend_2", "price"],
        },
    )
    assert reg_resp.status_code == 201
    model_id = reg_resp.json()["model_id"]

    val_resp = await client.post(
        "/api/v1/analytics/validation", headers=headers, json={"model_id": model_id}
    )
    assert val_resp.status_code == 201
    body = val_resp.json()

    assert body["multicollinearity"]["verdict"] == "fail"
    failing = [v for v in body["multicollinearity"]["vif"] if v["verdict"] == "fail"]
    assert len(failing) >= 1
    assert body["overall_verdict"] == "fail"
    assert len(body["remediation"]) >= 1

    for key in ["normality", "heteroscedasticity", "autocorrelation", "multicollinearity", "influence"]:
        assert key in body
    assert "residual_vs_fitted" in body
    assert "residual_histogram" in body

    jobs_resp = await client.get("/api/v1/jobs?type=validation", headers=headers)
    assert jobs_resp.status_code == 200
    assert jobs_resp.json()[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_validation_unknown_model_id_404(client: AsyncClient):
    headers = await _auth_headers(client, "val2@analytics.dz")
    fake_id = "00000000-0000-0000-0000-000000000000"

    resp = await client.post("/api/v1/analytics/validation", headers=headers, json={"model_id": fake_id})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_validation_model_isolated_between_companies(client: AsyncClient):
    headers_a = await _auth_headers(client, "valTenantA@analytics.dz")
    headers_b = await _auth_headers(client, "valTenantB@analytics.dz")
    dataset_id = await _upload_dataset(client, headers_a)

    reg_resp = await client.post(
        "/api/v1/analytics/regression",
        headers=headers_a,
        json={"dataset_id": dataset_id, "target": "sales", "features": ["marketing_spend", "price"]},
    )
    model_id = reg_resp.json()["model_id"]

    resp = await client.post(
        "/api/v1/analytics/validation", headers=headers_b, json={"model_id": model_id}
    )
    assert resp.status_code == 404
