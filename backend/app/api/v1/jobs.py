# backend/app/api/v1/jobs.py
"""Job status endpoints: list/filter and fetch a single AnalysisJob (progress + result)."""
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.models.analysis_job import AnalysisJob, JobStatus, JobType
from app.schemas.errors import ApiError
from app.schemas.job import AnalysisJobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[AnalysisJobRead])
async def list_jobs(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    type: Optional[JobType] = Query(default=None),
    job_status: Optional[JobStatus] = Query(default=None, alias="status"),
) -> list[AnalysisJob]:
    """List analysis jobs for the current company, optionally filtered by type/status."""
    query = select(AnalysisJob).where(AnalysisJob.company_id == user.company_id)
    if type is not None:
        query = query.where(AnalysisJob.type == type)
    if job_status is not None:
        query = query.where(AnalysisJob.status == job_status)
    query = query.order_by(AnalysisJob.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{job_id}", response_model=AnalysisJobRead)
async def get_job(
    job_id: UUID, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> AnalysisJob:
    """Return a single job's status, progress, and result (once completed)."""
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.id == job_id, AnalysisJob.company_id == user.company_id
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "job_not_found", "Tâche introuvable.")
    return job
