# backend/app/api/v1/datasets.py
"""Dataset endpoints: upload (CSV/XLSX), list, metadata, preview, delete."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser
from app.core.storage import delete_file, save_upload, validate_upload
from app.db.session import get_db
from app.models.dataset import Dataset, DatasetColumn, DatasetStatus, FileType
from app.schemas.dataset import DatasetDetailRead, DatasetPreviewRead, DatasetRead
from app.schemas.errors import ApiError
from app.services.datasets.profiling import preview_rows, profile_dataframe, read_dataset_file

router = APIRouter(prefix="/datasets", tags=["datasets"])

_EXT_TO_FILE_TYPE = {".csv": FileType.CSV, ".xlsx": FileType.XLSX, ".xls": FileType.XLSX}


@router.get("", response_model=list[DatasetRead])
async def list_datasets(
    user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[Dataset]:
    """List every dataset belonging to the current user's company."""
    result = await db.execute(
        select(Dataset).where(Dataset.company_id == user.company_id).order_by(Dataset.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=DatasetDetailRead, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile,
) -> Dataset:
    """
    Upload a CSV/XLSX file (multipart), persist it, profile every column,
    and create the Dataset + DatasetColumn rows.
    """
    ext = validate_upload(file)
    storage_path, _size = await save_upload(file, user.company_id, ext)

    dataset = Dataset(
        company_id=user.company_id,
        name=file.filename or "dataset",
        original_filename=file.filename or "dataset",
        file_type=_EXT_TO_FILE_TYPE[ext],
        storage_path=storage_path,
        status=DatasetStatus.UPLOADED,
    )

    try:
        df = read_dataset_file(storage_path, dataset.file_type.value)
        profile = profile_dataframe(df)
    except ApiError:
        delete_file(storage_path)
        raise

    dataset.row_count = profile.row_count
    dataset.column_count = profile.column_count

    db.add(dataset)
    await db.flush()

    for col in profile.columns:
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

    await db.commit()
    await db.refresh(dataset, attribute_names=["columns"])
    return dataset


async def _get_owned_dataset(db: AsyncSession, dataset_id: UUID, company_id: UUID) -> Dataset:
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.company_id == company_id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "dataset_not_found", "Jeu de données introuvable.")
    return dataset


@router.get("/{dataset_id}", response_model=DatasetDetailRead)
async def get_dataset(
    dataset_id: UUID, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> Dataset:
    """Return dataset metadata plus its column profile."""
    dataset = await _get_owned_dataset(db, dataset_id, user.company_id)
    await db.refresh(dataset, attribute_names=["columns"])
    return dataset


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewRead)
async def preview_dataset(
    dataset_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=1000),
) -> DatasetPreviewRead:
    """Return the first `limit` rows of the dataset for a quick preview table."""
    dataset = await _get_owned_dataset(db, dataset_id, user.company_id)
    df = read_dataset_file(dataset.storage_path, dataset.file_type.value)
    rows = preview_rows(df, limit=limit)
    return DatasetPreviewRead(
        columns=[str(c) for c in df.columns],
        rows=rows,
        total_rows=len(df),
        preview_rows=len(rows),
    )


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: UUID, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a dataset (and its stored file). Cascades to columns/jobs/etc via FK."""
    dataset = await _get_owned_dataset(db, dataset_id, user.company_id)
    delete_file(dataset.storage_path)
    await db.delete(dataset)
    await db.commit()
