from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.deps import get_current_user, require_roles
from app.models import IngestionJob, QuarantineRecord, SourceListing, User
from app.schemas import IngestionJobOut, IngestionRunIn
from app.services.ingestion import run_databds_import

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.post("/databds", response_model=IngestionJobOut)
def import_databds(
    body: IngestionRunIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return run_databds_import(
        db,
        tenant_id=user.tenant_id,
        created_by=user.id,
        databds_dir=settings.databds_dir,
        limit=body.limit,
    )


@router.get("/jobs", response_model=list[IngestionJobOut])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(IngestionJob)
        .where(IngestionJob.tenant_id == user.tenant_id)
        .order_by(IngestionJob.started_at.desc())
    ).all()


@router.get("/stats")
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n_listings = db.scalar(
        select(func.count()).select_from(SourceListing).where(SourceListing.tenant_id == user.tenant_id)
    )
    n_quarantine = db.scalar(
        select(func.count()).select_from(QuarantineRecord).where(QuarantineRecord.tenant_id == user.tenant_id)
    )
    return {"source_listings": n_listings, "quarantined": n_quarantine}
