# backend/app/api/v1/auth.py
"""Authentication endpoints: register (creates company + owner), login, refresh."""
import re
import unicodedata
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import rate_limit_auth
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    get_subject_from_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.errors import ApiError

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    """Turn a company name into a URL-safe, ASCII slug (handles French/Arabic input gracefully)."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or f"company-{uuid.uuid4().hex[:8]}"


async def _unique_slug(db: AsyncSession, base_slug: str) -> str:
    slug = base_slug
    suffix = 1
    while True:
        result = await db.execute(select(Company).where(Company.slug == slug))
        if result.scalar_one_or_none() is None:
            return slug
        suffix += 1
        slug = f"{base_slug}-{suffix}"


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
)
async def register(
    payload: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    """Create a new company and its first user (role=owner), then issue tokens."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise ApiError(
            status.HTTP_409_CONFLICT, "email_taken", "Cette adresse e-mail est déjà utilisée."
        )

    slug = await _unique_slug(db, _slugify(payload.company_name))
    company = Company(name=payload.company_name, slug=slug, country="DZ")
    db.add(company)
    await db.flush()  # assigns company.id

    user = User(
        company_id=company.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.OWNER,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit_auth)])
async def login(
    payload: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    """Authenticate with email + password and issue an access/refresh token pair."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED, "invalid_credentials", "E-mail ou mot de passe incorrect."
        )
    if not user.is_active:
        raise ApiError(status.HTTP_403_FORBIDDEN, "user_disabled", "Ce compte est désactivé.")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    """Exchange a valid refresh token for a new access/refresh token pair (rotation)."""
    try:
        user_id = get_subject_from_token(payload.refresh_token, expected_type="refresh")
    except InvalidTokenError as exc:
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED, "invalid_token", "Refresh token invalide ou expiré."
        ) from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise ApiError(status.HTTP_401_UNAUTHORIZED, "user_not_found", "Utilisateur introuvable.")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),  # rotation
    )
