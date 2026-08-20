# backend/app/core/deps.py
"""Shared FastAPI dependencies: DB session, current user, role guards, rate limiting."""
import time
from collections import defaultdict
from typing import Annotated

from fastapi import Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import InvalidTokenError, get_subject_from_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.errors import ApiError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolve the current user from a JWT access token."""
    try:
        user_id = get_subject_from_token(token, expected_type="access")
    except InvalidTokenError as exc:
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED, "invalid_token", "Session invalide ou expirée."
        ) from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED, "user_not_found", "Utilisateur introuvable ou désactivé."
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: UserRole):
    """Dependency factory enforcing that the current user has one of the allowed roles."""

    async def _guard(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise ApiError(
                status.HTTP_403_FORBIDDEN,
                "insufficient_role",
                "Vous n'avez pas les droits nécessaires pour cette action.",
            )
        return user

    return _guard


class InMemoryRateLimiter:
    """
    Minimal sliding-window rate limiter for auth endpoints.

    Suitable for a single-process dev/demo deployment. In production this
    should be backed by Redis (already available via settings.REDIS_URL).
    """

    def __init__(self, limit_per_minute: int):
        self.limit_per_minute = limit_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.time()
        window_start = now - 60
        hits = [t for t in self._hits[key] if t > window_start]
        hits.append(now)
        self._hits[key] = hits
        return len(hits) <= self.limit_per_minute


auth_rate_limiter = InMemoryRateLimiter(settings.AUTH_RATE_LIMIT_PER_MINUTE)


async def rate_limit_auth(request: Request) -> None:
    """Dependency: rate-limit auth endpoints by client IP."""
    client_ip = request.client.host if request.client else "unknown"
    if not auth_rate_limiter.check(f"auth:{client_ip}"):
        raise ApiError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "rate_limited",
            "Trop de tentatives. Veuillez réessayer plus tard.",
        )
