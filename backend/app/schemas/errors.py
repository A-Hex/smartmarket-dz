# backend/app/schemas/errors.py
"""Standard error envelope used across the API: {"detail": {"code", "message", "field_errors"}}."""
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    field_errors: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    detail: ErrorDetail


class ApiError(HTTPException):
    """Raise this anywhere in the API to get the standard error envelope."""

    def __init__(self, status_code: int, code: str, message: str, field_errors: Optional[dict[str, Any]] = None):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message, "field_errors": field_errors},
        )
