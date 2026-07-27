from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import CleanListing, Fact, User
from app.schemas import CleanListingOut, FactOut

router = APIRouter(prefix="/api/listings", tags=["listings"])


def _get_owned(listing_id: str, user: User, db: Session) -> CleanListing:
    row = db.get(CleanListing, listing_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy tin đã làm sạch")
    return row


@router.get("", response_model=list[CleanListingOut])
def list_clean_listings(
    project_slug: str | None = None,
    tier: str | None = None,
    only_representative: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(CleanListing).where(CleanListing.tenant_id == user.tenant_id)
    if project_slug:
        query = query.where(CleanListing.project_slug == project_slug)
    if tier:
        query = query.where(CleanListing.tier == tier)
    if only_representative:
        query = query.where(CleanListing.is_cluster_representative.is_(True))
    return db.scalars(
        query.order_by(CleanListing.processed_at.desc()).limit(limit).offset(offset)
    ).all()


@router.get("/{listing_id}", response_model=CleanListingOut)
def get_clean_listing(
    listing_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _get_owned(listing_id, user, db)


@router.get("/{listing_id}/facts", response_model=list[FactOut])
def get_listing_facts(
    listing_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Facts kèm provenance của một tin — nguồn cho Evidence panel ở các tuần sau."""
    row = _get_owned(listing_id, user, db)
    return db.scalars(
        select(Fact)
        .where(Fact.tenant_id == user.tenant_id, Fact.source_row_id == row.source_row_id)
        .order_by(Fact.predicate)
    ).all()
