# backend/alembic/versions/0001_initial_schema.py
"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- companies ---------------------------------------------------
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("country", sa.String(2), nullable=False, server_default="DZ"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_companies_slug", "companies", ["slug"], unique=True)

    # --- users ---------------------------------------------------------
    user_role = postgresql.ENUM("owner", "analyst", "viewer", name="user_role", create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- datasets --------------------------------------------------------
    file_type = postgresql.ENUM("csv", "xlsx", name="file_type", create_type=False)
    file_type.create(op.get_bind(), checkfirst=True)
    dataset_status = postgresql.ENUM(
        "uploaded", "cleaning", "cleaned", "analyzed", "failed", name="dataset_status", create_type=False
    )
    dataset_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_type", file_type, nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("status", dataset_status, nullable=False, server_default="uploaded"),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("column_count", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_datasets_company_id", "datasets", ["company_id"])

    # --- dataset_columns ---------------------------------------------
    op.create_table(
        "dataset_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("dtype", sa.String(50), nullable=False),
        sa.Column("null_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unique_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("min_value", sa.Float, nullable=True),
        sa.Column("max_value", sa.Float, nullable=True),
        sa.Column("mean_value", sa.Float, nullable=True),
        sa.Column("std_value", sa.Float, nullable=True),
        sa.Column("is_target_candidate", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_dataset_columns_dataset_id", "dataset_columns", ["dataset_id"])

    # --- cleaning_runs ------------------------------------------------
    cleaning_status = postgresql.ENUM(
        "queued", "running", "completed", "failed", name="cleaning_status", create_type=False
    )
    cleaning_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "cleaning_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", cleaning_status, nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cleaning_runs_dataset_id", "cleaning_runs", ["dataset_id"])

    # --- analysis_jobs -----------------------------------------------
    job_type = postgresql.ENUM(
        "descriptive", "regression", "anova", "validation", "forecast",
        "segmentation", "kpi", "decision", name="job_type", create_type=False,
    )
    job_type.create(op.get_bind(), checkfirst=True)
    job_status = postgresql.ENUM("queued", "running", "completed", "failed", name="job_status", create_type=False)
    job_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "dataset_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("type", job_type, nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", job_status, nullable=False, server_default="queued"),
        sa.Column("progress", sa.Float, nullable=False, server_default="0"),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analysis_jobs_company_id", "analysis_jobs", ["company_id"])
    op.create_index("ix_analysis_jobs_dataset_id", "analysis_jobs", ["dataset_id"])

    # --- models ---------------------------------------------------------
    op.create_table(
        "models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "dataset_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "job_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("metrics", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("fitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_models_company_id", "models", ["company_id"])
    op.create_index("ix_models_dataset_id", "models", ["dataset_id"])
    op.create_index("ix_models_job_id", "models", ["job_id"])

    # --- forecasts ------------------------------------------------------
    op.create_table(
        "forecasts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("horizon", sa.Integer, nullable=False),
        sa.Column("point", postgresql.JSONB, nullable=False),
        sa.Column("ci_lower", postgresql.JSONB, nullable=False),
        sa.Column("ci_upper", postgresql.JSONB, nullable=False),
        sa.Column("metrics", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_forecasts_model_id", "forecasts", ["model_id"])

    # --- segments -------------------------------------------------------
    op.create_table(
        "segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "dataset_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("algorithm", sa.String(50), nullable=False),
        sa.Column("n_clusters", sa.Integer, nullable=True),
        sa.Column("features", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("silhouette", sa.Float, nullable=True),
        sa.Column("centroids", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_segments_company_id", "segments", ["company_id"])
    op.create_index("ix_segments_dataset_id", "segments", ["dataset_id"])

    # --- kpis -------------------------------------------------------------
    kpi_type = postgresql.ENUM(
        "cltv", "churn", "take_rate", "cac", "wom", "revenue_growth", "gross_margin",
        name="kpi_type", create_type=False,
    )
    kpi_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "kpis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "dataset_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("kpi_type", kpi_type, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("formula", sa.String(500), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kpis_company_id", "kpis", ["company_id"])
    op.create_index("ix_kpis_dataset_id", "kpis", ["dataset_id"])

    # --- decisions ------------------------------------------------------
    decision_priority = postgresql.ENUM("high", "medium", "low", name="decision_priority", create_type=False)
    decision_priority.create(op.get_bind(), checkfirst=True)
    decision_status = postgresql.ENUM(
        "open", "acknowledged", "applied", "dismissed", name="decision_status", create_type=False
    )
    decision_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "dataset_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "source_job_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("priority", decision_priority, nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("evidence", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("recommended_action", sa.Text, nullable=False),
        sa.Column("status", decision_status, nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_decisions_company_id", "decisions", ["company_id"])
    op.create_index("ix_decisions_dataset_id", "decisions", ["dataset_id"])
    op.create_index("ix_decisions_source_job_id", "decisions", ["source_job_id"])

    # --- reports --------------------------------------------------------
    report_type = postgresql.ENUM("executive", "raw_results", name="report_type", create_type=False)
    report_type.create(op.get_bind(), checkfirst=True)
    report_format = postgresql.ENUM("pdf", "xlsx", name="report_format", create_type=False)
    report_format.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("type", report_type, nullable=False),
        sa.Column("format", report_format, nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_company_id", "reports", ["company_id"])


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("decisions")
    op.drop_table("kpis")
    op.drop_table("segments")
    op.drop_table("forecasts")
    op.drop_table("models")
    op.drop_table("analysis_jobs")
    op.drop_table("cleaning_runs")
    op.drop_table("dataset_columns")
    op.drop_table("datasets")
    op.drop_table("users")
    op.drop_table("companies")

    bind = op.get_bind()
    for enum_name in [
        "report_format", "report_type", "decision_status", "decision_priority",
        "kpi_type", "job_status", "job_type", "cleaning_status", "dataset_status",
        "file_type", "user_role",
    ]:
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
