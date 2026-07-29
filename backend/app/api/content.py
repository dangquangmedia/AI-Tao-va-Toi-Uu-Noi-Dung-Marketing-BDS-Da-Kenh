"""API vòng duyệt nội dung (Tuần 5, gate Plan/01 §6).

Phân quyền theo đúng vai trò trong Plan/01 §3: marketer viết và gửi duyệt, reviewer
duyệt hoặc từ chối, admin làm được cả hai. Xuất bản chỉ mở cho nội dung **đã duyệt** —
đây là điểm chặn cuối cùng giữa nội dung do model sinh và nội dung ra ngoài thị trường.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_roles
from app.models import ContentItem, Generation, User
from app.schemas import (
    ContentCreateIn,
    ContentDetailOut,
    ContentEditIn,
    ContentItemOut,
    ContentReviewIn,
    ContentVersionOut,
)
from app.services import content as content_service

router = APIRouter(prefix="/api/content", tags=["content"])


def _get_item(db: Session, tenant_id: str, item_id: str) -> ContentItem:
    item = db.get(ContentItem, item_id)
    if item is None or item.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy nội dung")
    return item


def _detail(db: Session, item: ContentItem) -> ContentDetailOut:
    payload = ContentDetailOut.model_validate(item, from_attributes=True)
    payload.versions = [
        ContentVersionOut.model_validate(v, from_attributes=True)
        for v in content_service.versions(db, item)
    ]
    return payload


@router.post("", response_model=ContentDetailOut, status_code=status.HTTP_201_CREATED)
def create_content(
    body: ContentCreateIn,
    user: User = Depends(require_roles("admin", "marketer")),
    db: Session = Depends(get_db),
):
    """Đưa một bản sinh vào vòng biên tập (tạo phiên bản 1)."""
    generation = db.get(Generation, body.generation_id)
    if generation is None or generation.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy bản sinh nội dung")
    try:
        item, _ = content_service.create_from_generation(
            db, user.tenant_id, user.id, generation, body.title
        )
    except content_service.ContentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return _detail(db, item)


@router.get("", response_model=list[ContentItemOut])
def list_content(
    item_status: str | None = Query(default=None, alias="status"),
    channel: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(ContentItem).where(ContentItem.tenant_id == user.tenant_id)
    if item_status:
        query = query.where(ContentItem.status == item_status)
    if channel:
        query = query.where(ContentItem.channel == channel)
    return db.scalars(query.order_by(ContentItem.updated_at.desc()).limit(limit)).all()


@router.get("/{item_id}", response_model=ContentDetailOut)
def get_content(item_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _detail(db, _get_item(db, user.tenant_id, item_id))


@router.post("/{item_id}/versions", response_model=ContentVersionOut)
def edit_content(
    item_id: str,
    body: ContentEditIn,
    user: User = Depends(require_roles("admin", "marketer")),
    db: Session = Depends(get_db),
):
    """Lưu bản sửa tay thành phiên bản mới; claim được chấm lại trên cùng tập fact."""
    item = _get_item(db, user.tenant_id, item_id)
    try:
        return content_service.add_version(
            db, user.tenant_id, user.id, item, body.headline, body.body, body.cta
        )
    except content_service.ContentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post("/{item_id}/submit", response_model=ContentDetailOut)
def submit_content(
    item_id: str,
    user: User = Depends(require_roles("admin", "marketer")),
    db: Session = Depends(get_db),
):
    item = _get_item(db, user.tenant_id, item_id)
    try:
        content_service.submit(db, item)
    except content_service.ContentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return _detail(db, item)


@router.post("/{item_id}/review", response_model=ContentVersionOut)
def review_content(
    item_id: str,
    body: ContentReviewIn,
    user: User = Depends(require_roles("admin", "reviewer")),
    db: Session = Depends(get_db),
):
    """Duyệt hoặc từ chối. Từ chối bắt buộc kèm lý do."""
    item = _get_item(db, user.tenant_id, item_id)
    try:
        return content_service.review(db, item, user, body.approve, body.note)
    except content_service.ContentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/{item_id}/export")
def export_content(
    item_id: str,
    fmt: str = Query(default="md", pattern=r"^(md|json)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xuất nội dung **đã duyệt** kèm khối truy vết (model, adapter, prompt, claim)."""
    item = _get_item(db, user.tenant_id, item_id)
    version = content_service.current_version(db, item)
    if version is None or version.status != content_service.APPROVED:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Chỉ xuất được nội dung đã duyệt — hãy gửi duyệt trước"
        )
    if fmt == "json":
        return {
            "item": ContentItemOut.model_validate(item, from_attributes=True),
            "version": ContentVersionOut.model_validate(version, from_attributes=True),
        }
    return Response(
        content=content_service.export_markdown(item, version),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{item.id}-v{version.version_no}.md"'},
    )
