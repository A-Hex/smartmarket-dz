# backend/app/api/v1/users.py
"""User management endpoints. Listing/inviting/updating teammates is owner-only."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.errors import ApiError
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_users(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> list[User]:
    """List every user in the current user's company."""
    result = await db.execute(select(User).where(User.company_id == user.company_id))
    return list(result.scalars().all())


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser) -> User:
    """Return the currently authenticated user's profile."""
    return user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role(UserRole.OWNER))],
) -> User:
    """Create a new teammate within the current company. Owner only."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise ApiError(status.HTTP_409_CONFLICT, "email_taken", "Cette adresse e-mail est déjà utilisée.")

    new_user = User(
        company_id=owner.company_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role(UserRole.OWNER))],
) -> User:
    """Update a teammate's profile/role/active status. Owner only, same company."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.company_id == owner.company_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "user_not_found", "Utilisateur introuvable.")

    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.role is not None:
        target.role = payload.role
    if payload.is_active is not None:
        target.is_active = payload.is_active

    await db.commit()
    await db.refresh(target)
    return target
