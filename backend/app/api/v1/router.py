# backend/app/api/v1/router.py
"""Aggregates all v1 routers. Phase 1 wires auth/companies/users; later phases add the rest."""
from fastapi import APIRouter

from app.api.v1 import analytics, auth, cleaning, companies, datasets, jobs, reports, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(users.router)
api_router.include_router(datasets.router)
api_router.include_router(cleaning.router)
api_router.include_router(analytics.router)
api_router.include_router(jobs.router)
api_router.include_router(reports.router)

# All 9 MVP phases now wired (Phase 9 bayesian/panel_data are interface-only stubs).
