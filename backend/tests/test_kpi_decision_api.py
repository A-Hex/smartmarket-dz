# backend/tests/test_kpi_decision_api.py
"""API tests for POST /analytics/kpis and POST /analytics/decision."""
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


def _transactions_csv_bytes(n_customers=60, seed=11) -> bytes:
    rng = np.random.default_rng(seed)
    rows = []
    base_date = pd.Timestamp("2024-01-01")
    for cust in range(n_customers):
        n_orders = rng.integers(1, 5)
        for _ in range(n_orders):
            rows.append(
                {
                    "customer_id": f"C{cust}",
                    "date": (base_date + pd.Timedelta(days=int(rng.integers(0, 300)))).strftime("%Y-%m-%d"),
                    "revenue": float(rng.uniform(50, 500)),
                    "cost": float(rng.uniform(20, 300)),
                    "marketing_spend": float(rng.uniform(1, 20)),
                    "region": rng.choice(["Alger", "Oran", "Constantine"]),
                }
            )
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


async def _upload(client: AsyncClient, headers: dict, content: bytes) -> str:
    files = {"file": ("transactions.csv", io.BytesIO(content), "text/csv")}
    resp = await client.post("/api/v1/datasets", headers=headers, files=files)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_kpi_endpoint_computes_and_persists(client: AsyncClient):
    headers = await _auth_headers(client, "kpi1@analytics.dz")
    dataset_id = await _upload(client, headers, _transactions_csv_bytes())

    resp = await client.post(
        "/api/v1/analytics/kpis",
        headers=headers,
        json={
            "dataset_id": dataset_id,
            "date_column": "date",
            "customer_id_column": "customer_id",
            "revenue_column": "revenue",
            "cost_column": "cost",
            "marketing_spend_column": "marketing_spend",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["kpis"]) == 7
    assert len(body["supporting_metrics"]) == 2

    cltv = next(k for k in body["kpis"] if k["kpi_type"] == "cltv")
    assert cltv["status"] == "computed"
    assert cltv["value"] > 0

    jobs_resp = await client.get("/api/v1/jobs?type=kpi", headers=headers)
    assert jobs_resp.status_code == 200
    assert jobs_resp.json()[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_kpi_endpoint_graceful_with_no_column_mapping(client: AsyncClient):
    headers = await _auth_headers(client, "kpi2@analytics.dz")
    dataset_id = await _upload(client, headers, _transactions_csv_bytes())

    resp = await client.post(
        "/api/v1/analytics/kpis", headers=headers, json={"dataset_id": dataset_id}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert all(k["status"] == "insufficient_data" for k in body["kpis"])


@pytest.mark.asyncio
async def test_decision_endpoint_uses_prior_kpi_and_regression_results(client: AsyncClient):
    headers = await _auth_headers(client, "dec1@analytics.dz")
    dataset_id = await _upload(client, headers, _transactions_csv_bytes(n_customers=80, seed=21))

    # Run a regression first so the decision engine has a significant driver to react to.
    reg = await client.post(
        "/api/v1/analytics/regression",
        headers=headers,
        json={"dataset_id": dataset_id, "target": "revenue", "features": ["marketing_spend", "cost"]},
    )
    assert reg.status_code == 201

    kpi_resp = await client.post(
        "/api/v1/analytics/kpis",
        headers=headers,
        json={
            "dataset_id": dataset_id,
            "date_column": "date",
            "customer_id_column": "customer_id",
            "revenue_column": "revenue",
            "cost_column": "cost",
            "marketing_spend_column": "marketing_spend",
        },
    )
    assert kpi_resp.status_code == 201

    dec_resp = await client.post(
        "/api/v1/analytics/decision", headers=headers, json={"dataset_id": dataset_id}
    )
    assert dec_resp.status_code == 201
    body = dec_resp.json()
    assert "decisions" in body
    # Every decision must carry the required fields per section 11.
    for d in body["decisions"]:
        assert d["priority"] in ("high", "medium", "low")
        assert d["category"]
        assert d["title"]
        assert d["description"]
        assert d["evidence"]
        assert d["recommended_action"]
        assert d["confidence"] in ("high", "medium", "low")
        assert d["status"] == "open"

    jobs_resp = await client.get("/api/v1/jobs?type=decision", headers=headers)
    assert jobs_resp.status_code == 200
    assert jobs_resp.json()[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_decision_endpoint_with_no_prior_analysis_returns_empty_list(client: AsyncClient):
    headers = await _auth_headers(client, "dec2@analytics.dz")
    dataset_id = await _upload(client, headers, _transactions_csv_bytes())

    resp = await client.post("/api/v1/analytics/decision", headers=headers, json={"dataset_id": dataset_id})
    assert resp.status_code == 201
    assert resp.json()["decisions"] == []


@pytest.mark.asyncio
async def test_decision_dataset_isolated_between_companies(client: AsyncClient):
    headers_a = await _auth_headers(client, "decTenantA@analytics.dz")
    headers_b = await _auth_headers(client, "decTenantB@analytics.dz")
    dataset_id = await _upload(client, headers_a, _transactions_csv_bytes())

    resp = await client.post("/api/v1/analytics/decision", headers=headers_b, json={"dataset_id": dataset_id})
    assert resp.status_code == 404
