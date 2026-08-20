# backend/app/models/__init__.py
"""
Import every ORM model here so that:
1. `Base.metadata` is fully populated for Alembic autogenerate.
2. Other modules can `from app.models import User, Company, ...`.
"""
from app.models.analysis_job import AnalysisJob, JobStatus, JobType
from app.models.analysis_model import AnalysisModel
from app.models.cleaning_run import CleaningRun, CleaningStatus
from app.models.company import Company
from app.models.dataset import Dataset, DatasetColumn, DatasetStatus, FileType
from app.models.decision import Decision, DecisionPriority, DecisionStatus
from app.models.forecast import Forecast
from app.models.kpi import KPI, KPIType
from app.models.report import Report, ReportFormat, ReportType
from app.models.segment import Segment
from app.models.user import User, UserRole

__all__ = [
    "AnalysisJob",
    "JobStatus",
    "JobType",
    "AnalysisModel",
    "CleaningRun",
    "CleaningStatus",
    "Company",
    "Dataset",
    "DatasetColumn",
    "DatasetStatus",
    "FileType",
    "Decision",
    "DecisionPriority",
    "DecisionStatus",
    "Forecast",
    "KPI",
    "KPIType",
    "Report",
    "ReportFormat",
    "ReportType",
    "Segment",
    "User",
    "UserRole",
]
