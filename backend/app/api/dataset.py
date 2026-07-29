from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.deps import get_current_user, require_roles
from app.models import Fact, RetrievalQuery, User
from app.schemas import FactOut, FactReviewIn, RetrievalQueryOut
from app.services.dataset import leakage_audit, split_report

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


@router.get("/summary")
def summary(
    version: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trạng thái dataset đã đóng băng: tỷ lệ split, kết quả leakage audit, gold query."""
    version = version or settings.dataset_version
    queries = db.scalars(
        select(RetrievalQuery).where(
            RetrievalQuery.tenant_id == user.tenant_id, RetrievalQuery.dataset_version == version
        )
    ).all()
    by_type: dict[str, int] = {}
    by_difficulty: dict[str, int] = {}
    for query in queries:
        by_type[query.query_type] = by_type.get(query.query_type, 0) + 1
        by_difficulty[query.difficulty] = by_difficulty.get(query.difficulty, 0) + 1
    return {
        "dataset_version": version,
        "splits": split_report(db, user.tenant_id, version),
        "leakage": leakage_audit(db, user.tenant_id, version),
        "gold_queries": {
            "total": len(queries),
            "by_type": by_type,
            "by_difficulty": by_difficulty,
            "needs_review": sum(1 for q in queries if q.needs_review),
        },
    }


@router.get("/queries", response_model=list[RetrievalQueryOut])
def list_queries(
    version: str | None = None,
    query_type: str | None = None,
    difficulty: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(RetrievalQuery).where(
        RetrievalQuery.tenant_id == user.tenant_id,
        RetrievalQuery.dataset_version == (version or settings.dataset_version),
    )
    if query_type:
        stmt = stmt.where(RetrievalQuery.query_type == query_type)
    if difficulty:  # tách bộ hard ra để Hải soát riêng — hai bộ có tiêu chí khác nhau
        stmt = stmt.where(RetrievalQuery.difficulty == difficulty)
    return db.scalars(stmt.order_by(RetrievalQuery.query_type, RetrievalQuery.query_key).limit(limit)).all()


@router.get("/facts/review", response_model=list[FactOut])
def facts_needing_review(
    predicate: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hàng đợi fact máy đánh dấu chưa chắc chắn — đầu vào của fact editor."""
    stmt = select(Fact).where(Fact.tenant_id == user.tenant_id, Fact.needs_review.is_(True))
    if predicate:
        stmt = stmt.where(Fact.predicate == predicate)
    return db.scalars(stmt.order_by(Fact.confidence, Fact.predicate).limit(limit)).all()


@router.patch("/facts/{fact_id}", response_model=FactOut)
def review_fact(
    fact_id: str,
    body: FactReviewIn,
    user: User = Depends(require_roles("admin", "marketer", "reviewer")),
    db: Session = Depends(get_db),
):
    """Người dùng xác nhận hoặc sửa giá trị fact; giữ lại giá trị máy sinh để đối chiếu."""
    fact = db.get(Fact, fact_id)
    if fact is None or fact.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy fact")

    if body.value_text is not None and body.value_text != fact.value_text:
        if not fact.original_value_text:
            fact.original_value_text = fact.value_text
        fact.value_text = body.value_text
        fact.value_num = None  # giá trị sửa tay không còn là số máy parse
    fact.needs_review = body.needs_review
    fact.review_note = body.note or fact.review_note
    fact.reviewed_by = user.id
    fact.reviewed_at = datetime.now(timezone.utc)
    if not body.needs_review:
        fact.confidence = 1.0  # đã có người xác nhận
    db.commit()
    db.refresh(fact)
    return fact
