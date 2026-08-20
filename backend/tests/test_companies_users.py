# backend/tests/test_companies_users.py
"""API tests for company profile and user management, including RBAC."""
import pytest
from httpx import AsyncClient


async def _register_owner(client: AsyncClient, email="owner@rbac.dz") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "RBAC Test Co",
            "full_name": "Owner Person",
            "email": email,
            "password": "OwnerPass1!",
        },
    )
    return resp.json()


@pytest.mark.asyncio
async def test_get_my_company(client: AsyncClient):
    tokens = await _register_owner(client)
    resp = await client.get(
        "/api/v1/companies/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "RBAC Test Co"


@pytest.mark.asyncio
async def test_owner_can_create_teammate_with_analyst_role(client: AsyncClient):
    tokens = await _register_owner(client, email="owner2@rbac.dz")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "analyst@rbac.dz",
            "full_name": "Analyst Person",
            "password": "AnalystPass1!",
            "role": "analyst",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "analyst"


@pytest.mark.asyncio
async def test_viewer_cannot_create_teammate(client: AsyncClient):
    owner_tokens = await _register_owner(client, email="owner3@rbac.dz")
    owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}

    create_resp = await client.post(
        "/api/v1/users",
        headers=owner_headers,
        json={
            "email": "viewer@rbac.dz",
            "full_name": "Viewer Person",
            "password": "ViewerPass1!",
            "role": "viewer",
        },
    )
    assert create_resp.status_code == 201

    viewer_login = await client.post(
        "/api/v1/auth/login", json={"email": "viewer@rbac.dz", "password": "ViewerPass1!"}
    )
    viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}

    forbidden = await client.post(
        "/api/v1/users",
        headers=viewer_headers,
        json={
            "email": "someone@rbac.dz",
            "full_name": "Someone",
            "password": "SomeonePass1!",
            "role": "analyst",
        },
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "insufficient_role"


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
