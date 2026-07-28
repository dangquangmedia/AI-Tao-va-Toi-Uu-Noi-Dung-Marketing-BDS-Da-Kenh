from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.deps import get_current_user, require_roles
from app.models import IngestionJob, User
from app.schemas import IndexRunIn, IngestionJobOut
from app.services.indexing import JOB_TYPE, run_index_build
from app.services.retrieval import retrieval_stats, retrieve_r1, retrieve_r2

router = APIRouter(prefix="/api/search", tags=["search"])

MODES = ("r1-fts", "r1-vector", "r1-hybrid", "r2-graph")


@router.get("")
def search(
    q: str = Query(min_length=1),
    mode: str = "r1-hybrid",
    k: int = Query(default=10, ge=1, le=50),
    project_slug: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Truy xuất theo cấu hình R1/R2 — mọi kết quả kèm nguồn (và đường đi nếu là graph)."""
    if mode not in MODES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"mode phải thuộc {MODES}")
    if mode == "r2-graph":
        results = retrieve_r2(db, user.tenant_id, q, k)
    else:
        results = retrieve_r1(db, user.tenant_id, q, k, mode=mode.split("-", 1)[1], project_slug=project_slug)
    return {"query": q, "mode": mode, "k": k, "count": len(results), "results": results}


@router.get("/stats")
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return retrieval_stats(db, user.tenant_id)


@router.post("/index", response_model=IngestionJobOut)
def build_index(
    body: IndexRunIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Dựng lại knowledge base (chunk + FTS + embedding). Idempotent."""
    if body.backend:
        settings.embedding_backend = body.backend
    return run_index_build(
        db,
        tenant_id=user.tenant_id,
        created_by=user.id,
        tiers=tuple(body.tiers),
        limit=body.limit,
        embed=body.embed,
    )


@router.get("/index/jobs", response_model=list[IngestionJobOut])
def index_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(IngestionJob)
        .where(IngestionJob.tenant_id == user.tenant_id, IngestionJob.job_type == JOB_TYPE)
        .order_by(IngestionJob.started_at.desc())
    ).all()
