# backend/tests/test_auth.py
"""API tests for authentication: register, login, refresh."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_creates_company_and_owner(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Épicerie El Djazair",
            "full_name": "Sara Benali",
            "email": "sara@eldjazair.dz",
            "password": "StrongPass1!",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client: AsyncClient):
    payload = {
        "company_name": "Company A",
        "full_name": "User A",
        "email": "dup@test.dz",
        "password": "StrongPass1!",
    }
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/auth/register",
        json={**payload, "company_name": "Company B"},
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "email_taken"


@pytest.mark.asyncio
async def test_login_success_and_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Boutique Oran",
            "full_name": "Karim",
            "email": "karim@oran.dz",
            "password": "CorrectPass1!",
        },
    )

    ok = await client.post(
        "/api/v1/auth/login", json={"email": "karim@oran.dz", "password": "CorrectPass1!"}
    )
    assert ok.status_code == 200
    assert "access_token" in ok.json()

    bad = await client.post(
        "/api/v1/auth/login", json={"email": "karim@oran.dz", "password": "WrongPass"}
    )
    assert bad.status_code == 401
    assert bad.json()["detail"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Refresh Co",
            "full_name": "Yasmine",
            "email": "yasmine@refresh.dz",
            "password": "RefreshPass1!",
        },
    )
    refresh_token = reg.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_with_access_token_rejected(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Guard Co",
            "full_name": "Nadia",
            "email": "nadia@guard.dz",
            "password": "GuardPass1!",
        },
    )
    access_token = reg.json()["access_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401
