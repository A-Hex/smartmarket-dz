# backend/tests/test_forecast_segmentation_api.py
"""API tests for POST /analytics/forecast and POST /analytics/segmentation."""
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


def _timeseries_csv_bytes() -> bytes:
    rng = np.random.default_rng(5)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    trend = np.linspace(200, 500, 100)
    sales = trend + rng.normal(0, 15, 100)
    df = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "sales": sales})
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def _clustering_csv_bytes() -> bytes:
    rng = np.random.default_rng(6)
    g1 = rng.normal([20, 50], [3, 5], (50, 2))
    g2 = rng.normal([80, 20], [3, 5], (50, 2))
    data = np.vstack([g1, g2])
    df = pd.DataFrame(data, columns=["recency", "frequency"])
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


async def _upload(client: AsyncClient, headers: dict, content: bytes, filename="data.csv") -> str:
    files = {"file": (filename, io.BytesIO(content), "text/csv")}
    resp = await client.post("/api/v1/datasets", headers=headers, files=files)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_forecast_endpoint_returns_comparison_and_ci_bands(client: AsyncClient):
    headers = await _auth_headers(client, "fc1@analytics.dz")
    dataset_id = await _upload(client, headers, _timeseries_csv_bytes())

    resp = await client.post(
        "/api/v1/analytics/forecast",
        headers=headers,
        json={"dataset_id": dataset_id, "time_column": "date", "target": "sales", "horizon": 10},
    )
    assert resp.status_code == 201
    body = resp.json()

    assert body["best_model"] in ("arima", "ets")
    assert len(body["forecast"]["point"]) == 10
    assert len(body["forecast"]["ci_lower_95"]) == 10
    assert "arima_metrics" in body and "ets_metrics" in body
    assert "model_id" in body and "forecast_id" in body

    jobs_resp = await client.get("/api/v1/jobs?type=forecast", headers=headers)
    assert jobs_resp.status_code == 200
    assert jobs_resp.json()[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_forecast_endpoint_rejects_unknown_time_column(client: AsyncClient):
    headers = await _auth_headers(client, "fc2@analytics.dz")
    dataset_id = await _upload(client, headers, _timeseries_csv_bytes())

    resp = await client.post(
        "/api/v1/analytics/forecast",
        headers=headers,
        json={"dataset_id": dataset_id, "time_column": "nope", "target": "sales"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "forecast_failed"


@pytest.mark.asyncio
async def test_segmentation_endpoint_returns_named_clusters(client: AsyncClient):
    headers = await _auth_headers(client, "seg1@analytics.dz")
    dataset_id = await _upload(client, headers, _clustering_csv_bytes())

    resp = await client.post(
        "/api/v1/analytics/segmentation",
        headers=headers,
        json={"dataset_id": dataset_id, "features": ["recency", "frequency"], "algorithm": "kmeans"},
    )
    assert resp.status_code == 201
    body = resp.json()

    assert body["n_clusters"] == 2
    assert len(body["clusters"]) == 2
    assert all(c["name"] for c in body["clusters"])
    assert len(body["pca_points"]) == 100
    assert "segment_id" in body

    jobs_resp = await client.get("/api/v1/jobs?type=segmentation", headers=headers)
    assert jobs_resp.status_code == 200
    assert jobs_resp.json()[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_segmentation_dataset_isolated_between_companies(client: AsyncClient):
    headers_a = await _auth_headers(client, "segTenantA@analytics.dz")
    headers_b = await _auth_headers(client, "segTenantB@analytics.dz")
    dataset_id = await _upload(client, headers_a, _clustering_csv_bytes())

    resp = await client.post(
        "/api/v1/analytics/segmentation",
        headers=headers_b,
        json={"dataset_id": dataset_id, "features": ["recency", "frequency"]},
    )
    assert resp.status_code == 404
