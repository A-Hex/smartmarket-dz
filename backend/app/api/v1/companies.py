# backend/app/api/v1/companies.py
"""Company profile endpoints (scoped to the current user's own company)."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_role
from app.db.session import get_db
from app.models.company import Company
from app.models.user import UserRole
from app.schemas.company import CompanyRead, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/me", response_model=CompanyRead)
async def get_my_company(
    user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> Company:
    """Return the profile of the current user's company."""
    result = await db.execute(select(Company).where(Company.id == user.company_id))
    return result.scalar_one()


@router.patch("/me", response_model=CompanyRead)
async def update_my_company(
    payload: CompanyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[object, Depends(require_role(UserRole.OWNER))],
) -> Company:
    """Update the current user's company profile. Owner only."""
    result = await db.execute(select(Company).where(Company.id == user.company_id))
    company = result.scalar_one()

    if payload.name is not None:
        company.name = payload.name

    await db.commit()
    await db.refresh(company)
    return company
