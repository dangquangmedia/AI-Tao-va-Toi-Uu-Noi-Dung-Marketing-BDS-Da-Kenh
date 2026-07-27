from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_roles
from app.models import IngestionJob, QuarantineRecord, User
from app.schemas import IngestionJobOut, PipelineRunIn, QuarantineOut
from app.services.data_quality import data_quality_report
from app.services.pipeline import JOB_TYPE, run_clean_pipeline

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run", response_model=IngestionJobOut)
def run_pipeline(
    body: PipelineRunIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Chạy D1–D5 trên raw zone của tenant. Chạy lại nhiều lần cho cùng kết quả."""
    return run_clean_pipeline(db, tenant_id=user.tenant_id, created_by=user.id, limit=body.limit)


@router.get("/jobs", response_model=list[IngestionJobOut])
def list_pipeline_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(IngestionJob)
        .where(IngestionJob.tenant_id == user.tenant_id, IngestionJob.job_type == JOB_TYPE)
        .order_by(IngestionJob.started_at.desc())
    ).all()


@router.get("/data-quality")
def data_quality(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return data_quality_report(db, user.tenant_id)


@router.get("/quarantine", response_model=list[QuarantineOut])
def list_quarantine(
    error_code: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(QuarantineRecord).where(QuarantineRecord.tenant_id == user.tenant_id)
    if error_code:
        query = query.where(QuarantineRecord.error_code == error_code)
    return db.scalars(
        query.order_by(QuarantineRecord.created_at.desc()).limit(limit).offset(offset)
    ).all()
