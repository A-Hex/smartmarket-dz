# backend/app/api/v1/cleaning.py
"""
Data Cleaning endpoints.

POST /datasets/{id}/cleaning runs the Cleaning Engine synchronously (fast enough
for MVP dataset sizes) and persists a CleaningRun with a before/after report.
The dataset's stored file is replaced by the cleaned version and its status
moves to `cleaned`. GET /cleaning/runs/{run_id} retrieves that report.
"""
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.models.cleaning_run import CleaningRun, CleaningStatus
from app.models.dataset import Dataset, DatasetColumn, DatasetStatus, FileType
from app.schemas.cleaning import CleaningConfig, CleaningRunRead
from app.schemas.errors import ApiError
from app.services.cleaning.engine import clean_dataframe
from app.services.datasets.profiling import profile_dataframe, read_dataset_file

router = APIRouter(tags=["cleaning"])


async def _get_owned_dataset(db: AsyncSession, dataset_id: UUID, company_id: UUID) -> Dataset:
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.company_id == company_id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "dataset_not_found", "Jeu de données introuvable.")
    return dataset


@router.post(
    "/datasets/{dataset_id}/cleaning",
    response_model=CleaningRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def run_cleaning(
    dataset_id: UUID,
    config: CleaningConfig,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CleaningRun:
    """Run the Data Cleaning Engine on a dataset with the given per-column config."""
    dataset = await _get_owned_dataset(db, dataset_id, user.company_id)

    run = CleaningRun(
        dataset_id=dataset.id,
        config=config.model_dump(),
        status=CleaningStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()

    try:
        df_before = read_dataset_file(dataset.storage_path, dataset.file_type.value)
        profile_before = profile_dataframe(df_before)

        df_after, cleaning_result = clean_dataframe(df_before, config)
        profile_after = profile_dataframe(df_after)

        # Persist the cleaned dataset, replacing the working copy used by
        # downstream analytics. The original upload remains untouched on disk
        # under its original storage_path history is not retained beyond this
        # report (per section 8, only one storage_path is modeled per dataset).
        cleaned_path = dataset.storage_path.rsplit(".", 1)[0] + "_cleaned.csv"
        df_after.to_csv(cleaned_path, index=False)

        report = {
            "rows_before": cleaning_result.rows_before,
            "rows_after": cleaning_result.rows_after,
            "columns_before": cleaning_result.columns_before,
            "columns_after": cleaning_result.columns_after,
            "missingness_before": {
                c.name: c.null_count for c in profile_before.columns
            },
            "missingness_after": {
                c.name: c.null_count for c in profile_after.columns
            },
            "per_column": [
                {
                    "column": pc.column,
                    "null_count_before": pc.null_count_before,
                    "null_count_after": pc.null_count_after,
                    "outliers_detected": pc.outliers_detected,
                    "outliers_handled": pc.outliers_handled,
                    "strategy_applied": pc.strategy_applied,
                }
                for pc in cleaning_result.per_column
            ],
            "cleaned_storage_path": cleaned_path,
        }

        run.status = CleaningStatus.COMPLETED
        run.report = report
        run.finished_at = datetime.now(timezone.utc)

        # Update the dataset to point at the cleaned file and refresh its column profile.
        # The cleaned file is always written as CSV regardless of the original format.
        dataset.storage_path = cleaned_path
        dataset.file_type = FileType.CSV
        dataset.status = DatasetStatus.CLEANED
        dataset.row_count = profile_after.row_count
        dataset.column_count = profile_after.column_count

        await db.execute(
            DatasetColumn.__table__.delete().where(DatasetColumn.dataset_id == dataset.id)
        )
        for col in profile_after.columns:
            db.add(
                DatasetColumn(
                    dataset_id=dataset.id,
                    name=col.name,
                    dtype=col.dtype,
                    null_count=col.null_count,
                    unique_count=col.unique_count,
                    min_value=col.min_value,
                    max_value=col.max_value,
                    mean_value=col.mean_value,
                    std_value=col.std_value,
                    is_target_candidate=col.is_target_candidate,
                )
            )

    except Exception as exc:  # pragma: no cover - defensive; engine errors are the main path
        run.status = CleaningStatus.FAILED
        run.finished_at = datetime.now(timezone.utc)
        run.report = {"error": str(exc)}
        await db.commit()
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "cleaning_failed", f"Le nettoyage a échoué : {exc}"
        ) from exc

    await db.commit()
    await db.refresh(run)
    return run


@router.get("/cleaning/runs/{run_id}", response_model=CleaningRunRead)
async def get_cleaning_run(
    run_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CleaningRun:
    """Return a cleaning run's before/after report, scoped to the caller's company."""
    result = await db.execute(
        select(CleaningRun, Dataset)
        .join(Dataset, Dataset.id == CleaningRun.dataset_id)
        .where(CleaningRun.id == run_id, Dataset.company_id == user.company_id)
    )
    row = result.first()
    if row is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND, "cleaning_run_not_found", "Exécution de nettoyage introuvable."
        )
    run, _dataset = row
    return run
