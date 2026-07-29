from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import ExperimentRun, Generation, User
from app.services.experiments import item_metrics

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


def _run_or_404(db: Session, tenant_id: str, run_id: str) -> ExperimentRun:
    run = db.get(ExperimentRun, run_id)
    if run is None or run.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không thấy lượt chạy")
    return run


def _row(run: ExperimentRun) -> dict:
    return {
        "id": run.id,
        "run_key": run.run_key,
        "label": run.label,
        "dataset_version": run.dataset_version,
        "configs": run.configs,
        "skipped": run.skipped,
        "n_briefs": run.n_briefs,
        "status": run.status,
        "error": run.error,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "summary": run.summary,
    }


@router.get("")
def list_runs(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Các lượt chạy thí nghiệm — mới nhất trước. Không kèm snapshot cho nhẹ."""
    runs = db.scalars(
        select(ExperimentRun)
        .where(ExperimentRun.tenant_id == user.tenant_id)
        .order_by(ExperimentRun.started_at.desc())
        .limit(limit)
    ).all()
    return {"items": [_row(r) for r in runs]}


@router.get("/{run_id}")
def get_run(run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Chi tiết một lượt: snapshot điều kiện chạy + chỉ số + so sánh từng cặp."""
    run = _run_or_404(db, user.tenant_id, run_id)
    return {**_row(run), "snapshot": run.snapshot}


@router.get("/{run_id}/items")
def get_run_items(
    run_id: str,
    config: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Từng bài trong lượt chạy — để đối chiếu tay đúng bài nào tốt hơn bài nào."""
    run = _run_or_404(db, user.tenant_id, run_id)
    stmt = select(Generation).where(Generation.experiment_run_id == run.id)
    if config:
        stmt = stmt.where(Generation.config == config.upper())
    records = db.scalars(stmt.order_by(Generation.created_at)).all()
    return {
        "items": [
            {
                "id": r.id,
                "config": r.config,
                "retrieval_config": r.retrieval_config,
                "channel": r.channel,
                "persona": r.persona,
                "project_slug": r.project_slug,
                "brief": r.brief,
                "headline": r.headline,
                "body": r.body,
                "cta": r.cta,
                "status": r.status,
                "latency_ms": r.latency_ms,
                "adapter_name": r.adapter_name,
                "metrics": {**r.metrics, **item_metrics(r)},
                "claims": r.claims,
            }
            for r in records
        ]
    }
