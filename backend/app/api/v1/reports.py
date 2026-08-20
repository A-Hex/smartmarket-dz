# backend/app/api/v1/reports.py
"""Report endpoints: generate PDF/XLSX reports and download them."""
import os
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentUser
from app.db.session import get_db
from app.models.analysis_job import AnalysisJob, JobStatus, JobType
from app.models.company import Company
from app.models.dataset import Dataset
from app.models.decision import Decision
from app.models.report import Report, ReportFormat, ReportType
from app.schemas.errors import ApiError
from app.schemas.report import ReportGenerateRequest, ReportRead
from app.services.reports.pdf_report import build_executive_pdf
from app.services.reports.xlsx_report import build_raw_results_xlsx

router = APIRouter(tags=["reports"])


async def _get_owned_dataset(db: AsyncSession, dataset_id: UUID, company_id: UUID) -> Dataset:
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.company_id == company_id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "dataset_not_found", "Jeu de données introuvable.")
    return dataset


async def _latest_completed_result(db: AsyncSession, dataset_id: UUID, company_id: UUID, job_type: JobType):
    result = await db.execute(
        select(AnalysisJob)
        .where(
            AnalysisJob.dataset_id == dataset_id,
            AnalysisJob.company_id == company_id,
            AnalysisJob.type == job_type,
            AnalysisJob.status == JobStatus.COMPLETED,
        )
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    return job.result if job else None


@router.post("/reports/generate", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def generate_report(
    payload: ReportGenerateRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Report:
    """
    Build a report from the dataset's most recent completed analyses.
    format=pdf -> executive summary (KPIs, validation verdicts, forecast chart,
    top 5 recommendations). format=xlsx -> full raw-results workbook (one
    sheet per analysis).
    """
    dataset = await _get_owned_dataset(db, payload.dataset_id, user.company_id)
    company = (await db.execute(select(Company).where(Company.id == user.company_id))).scalar_one()

    descriptive = await _latest_completed_result(db, dataset.id, user.company_id, JobType.DESCRIPTIVE)
    regression = await _latest_completed_result(db, dataset.id, user.company_id, JobType.REGRESSION)
    validation = await _latest_completed_result(db, dataset.id, user.company_id, JobType.VALIDATION)
    forecast = await _latest_completed_result(db, dataset.id, user.company_id, JobType.FORECAST)
    segmentation = await _latest_completed_result(db, dataset.id, user.company_id, JobType.SEGMENTATION)
    kpi = await _latest_completed_result(db, dataset.id, user.company_id, JobType.KPI)

    decisions_result = await db.execute(
        select(Decision)
        .where(Decision.dataset_id == dataset.id, Decision.company_id == user.company_id)
        .order_by(Decision.created_at.desc())
        .limit(20)
    )
    decisions = [
        {
            "priority": d.priority.value, "category": d.category, "title": d.title,
            "description": d.description, "recommended_action": d.recommended_action,
            "confidence": d.evidence.get("confidence", "medium") if d.evidence else "medium",
        }
        for d in decisions_result.scalars().all()
    ]

    os.makedirs(settings.REPORT_DIR, exist_ok=True)
    company_dir = os.path.join(settings.REPORT_DIR, str(user.company_id))
    os.makedirs(company_dir, exist_ok=True)

    import uuid as uuid_lib

    if payload.format == ReportFormat.PDF:
        content = build_executive_pdf(company.name, dataset.name, kpi, validation, forecast, decisions)
        filename = f"{uuid_lib.uuid4().hex}.pdf"
        report_type = ReportType.EXECUTIVE
    else:
        content = build_raw_results_xlsx(
            dataset.name, descriptive, regression, validation, forecast, segmentation, kpi, decisions
        )
        filename = f"{uuid_lib.uuid4().hex}.xlsx"
        report_type = ReportType.RAW_RESULTS

    storage_path = os.path.join(company_dir, filename)
    with open(storage_path, "wb") as f:
        f.write(content)

    report = Report(
        company_id=user.company_id,
        type=report_type,
        format=payload.format,
        storage_path=storage_path,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: UUID, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Download a previously generated report.

    NOTE: the spec calls for a short-lived signed URL; this MVP has no
    separate object-storage layer, so downloads are instead gated by the
    same JWT auth + company-scoping as every other endpoint. Swapping in
    presigned S3/MinIO URLs later doesn't change this endpoint's contract.
    """
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.company_id == user.company_id)
    )
    report = result.scalar_one_or_none()
    if report is None or not os.path.exists(report.storage_path):
        raise ApiError(status.HTTP_404_NOT_FOUND, "report_not_found", "Rapport introuvable.")

    media_type = "application/pdf" if report.format == ReportFormat.PDF else (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = os.path.basename(report.storage_path)
    return FileResponse(report.storage_path, media_type=media_type, filename=filename)
