"""Vòng đời nội dung: biên tập → gửi duyệt → duyệt/từ chối → xuất bản (Tuần 5).

Đây là phần "review/version/export" trong danh sách **không được cắt** của Plan/01 §8.
Ba quy tắc chi phối toàn bộ module:

1. **Version bất biến.** Sửa nội dung không ghi đè bản cũ mà tạo `version_no` mới. Bản đã
   duyệt vì thế luôn truy được nguyên trạng, kể cả khi người dùng sửa tiếp sau đó.
2. **Người biên tập không tự duyệt bài của mình.** Reviewer duyệt bài do chính mình viết
   thì cơ chế duyệt mất ý nghĩa. Admin được phép (nhóm chỉ có hai người, cần lối thoát),
   nhưng hệ thống ghi rõ ai duyệt.
3. **Sửa tay vẫn bị chấm claim.** Người viết thêm một con số không có trong facts thì
   phải hiện ra ngay ở bản mới — nếu không, cơ chế chống bịa số chỉ chặn được model chứ
   không chặn được người.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ContentItem, ContentVersion, Fact, Generation, User
from app.services.chunking import PREDICATE_LABELS, value_label
from app.services.claim_check import check_claims

DRAFT, IN_REVIEW, APPROVED, REJECTED = "draft", "in_review", "approved", "rejected"


class ContentError(Exception):
    """Vi phạm quy tắc nghiệp vụ (chuyển trạng thái sai, tự duyệt…) → API trả 400/403."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _reference_facts(db: Session, tenant_id: str, generation: Generation | None) -> list[dict]:
    """Tập fact dùng để chấm claim, lấy đúng tập mà lần sinh gốc đã dùng."""
    if generation is None:
        return []
    fact_ids = generation.metrics.get("reference_fact_ids") or generation.context_fact_ids or []
    if not fact_ids:
        return []
    facts = db.scalars(
        select(Fact).where(Fact.tenant_id == tenant_id, Fact.id.in_(list(fact_ids)))
    ).all()
    return [
        {
            "fact_id": f.id,
            "predicate": f.predicate,
            "text": f"{PREDICATE_LABELS.get(f.predicate, f.predicate)}: {value_label(f.value_text)}",
            "value_text": f.value_text,
            "value_num": f.value_num,
            "source_url": f.source_url,
            "valid_from": f.valid_from,
            "valid_to": f.valid_to,
        }
        for f in facts
    ]


def _next_version_no(db: Session, item_id: str) -> int:
    current = db.scalar(
        select(func.max(ContentVersion.version_no)).where(ContentVersion.content_item_id == item_id)
    )
    return (current or 0) + 1


def create_from_generation(
    db: Session, tenant_id: str, user_id: str, generation: Generation, title: str = ""
) -> tuple[ContentItem, ContentVersion]:
    """Đưa một lần sinh vào vòng biên tập. Bản sinh gốc trong `generations` giữ nguyên."""
    if generation.status != "done":
        raise ContentError("Chỉ đưa được bản sinh thành công vào vòng duyệt")

    item = ContentItem(
        tenant_id=tenant_id,
        project_slug=generation.project_slug,
        channel=generation.channel,
        persona=generation.persona,
        title=(title or generation.headline or generation.brief)[:300],
        status=DRAFT,
        created_by=user_id,
    )
    db.add(item)
    db.flush()

    version = ContentVersion(
        tenant_id=tenant_id,
        content_item_id=item.id,
        version_no=1,
        generation_id=generation.id,
        config=generation.config,
        model_name=generation.model_name,
        adapter_name=generation.adapter_name,
        prompt_version=generation.prompt_version,
        headline=generation.headline,
        body=generation.body,
        cta=generation.cta,
        edited_by_human=False,
        claims=generation.claims,
        metrics=generation.metrics,
        status=DRAFT,
        created_by=user_id,
    )
    db.add(version)
    item.current_version = 1
    db.commit()
    db.refresh(item)
    db.refresh(version)
    return item, version


def add_version(
    db: Session,
    tenant_id: str,
    user_id: str,
    item: ContentItem,
    headline: str,
    body: str,
    cta: str,
) -> ContentVersion:
    """Lưu bản biên tập tay thành version mới và **chấm lại claim** trên cùng tập fact."""
    if item.status == APPROVED:
        raise ContentError("Nội dung đã duyệt — tạo bản sao mới nếu muốn sửa tiếp")

    latest = current_version(db, item)
    generation = db.get(Generation, latest.generation_id) if latest and latest.generation_id else None
    checked = check_claims(f"{headline}\n{body}\n{cta}", _reference_facts(db, tenant_id, generation))

    version = ContentVersion(
        tenant_id=tenant_id,
        content_item_id=item.id,
        version_no=_next_version_no(db, item.id),
        generation_id=latest.generation_id if latest else None,
        config=latest.config if latest else "",
        model_name=latest.model_name if latest else "",
        adapter_name=latest.adapter_name if latest else "",
        prompt_version=latest.prompt_version if latest else "",
        headline=headline,
        body=body,
        cta=cta,
        edited_by_human=True,
        claims=checked["claims"],
        metrics={k: v for k, v in checked.items() if k != "claims"},
        status=DRAFT,
        created_by=user_id,
    )
    db.add(version)
    item.current_version = version.version_no
    item.status = DRAFT  # sửa sau khi bị từ chối → quay lại nháp, phải gửi duyệt lại
    db.commit()
    db.refresh(version)
    return version


def submit(db: Session, item: ContentItem) -> ContentItem:
    if item.status == APPROVED:
        raise ContentError("Nội dung đã được duyệt")
    if item.current_version == 0:
        raise ContentError("Chưa có phiên bản nào để gửi duyệt")
    version = current_version(db, item)
    version.status = IN_REVIEW
    item.status = IN_REVIEW
    db.commit()
    db.refresh(item)
    return item


def review(
    db: Session, item: ContentItem, reviewer: User, approve: bool, note: str = ""
) -> ContentVersion:
    """Duyệt hoặc từ chối phiên bản hiện tại."""
    if item.status != IN_REVIEW:
        raise ContentError("Chỉ duyệt được nội dung đang ở trạng thái chờ duyệt")
    version = current_version(db, item)
    if version.created_by == reviewer.id and reviewer.role != "admin":
        raise ContentError("Người viết không tự duyệt bài của mình")
    if not approve and not note.strip():
        raise ContentError("Từ chối phải kèm lý do để người viết sửa được")

    version.status = APPROVED if approve else REJECTED
    version.review_note = note
    version.reviewed_by = reviewer.id
    version.reviewed_at = _now()
    item.status = version.status
    db.commit()
    db.refresh(version)
    return version


def current_version(db: Session, item: ContentItem) -> ContentVersion | None:
    return db.scalar(
        select(ContentVersion)
        .where(ContentVersion.content_item_id == item.id)
        .order_by(ContentVersion.version_no.desc())
        .limit(1)
    )


def versions(db: Session, item: ContentItem) -> list[ContentVersion]:
    return list(
        db.scalars(
            select(ContentVersion)
            .where(ContentVersion.content_item_id == item.id)
            .order_by(ContentVersion.version_no)
        ).all()
    )


def export_markdown(item: ContentItem, version: ContentVersion) -> str:
    """Xuất bản đã duyệt kèm khối truy vết — bản xuất ra vẫn nói rõ nó từ đâu mà có."""
    unsupported = [c for c in version.claims if c.get("status") != "supported"]
    lines = [
        f"# {version.headline or item.title}",
        "",
        version.body,
        "",
        f"**{version.cta}**" if version.cta else "",
        "",
        "---",
        "",
        "<!-- Truy vết (không đăng kèm) -->",
        f"- Nội dung: `{item.id}` · phiên bản {version.version_no} · trạng thái {version.status}",
        f"- Kênh: {item.channel} · persona: {item.persona} · dự án: {item.project_slug or '—'}",
        f"- Sinh bằng: cấu hình {version.config or '—'} · model `{version.model_name or '—'}`"
        + (f" · adapter `{version.adapter_name}`" if version.adapter_name else ""),
        f"- Prompt version: {version.prompt_version or '—'}"
        + (f" · bản sinh gốc `{version.generation_id}`" if version.generation_id else ""),
        f"- Người biên tập sửa tay: {'có' if version.edited_by_human else 'không'}",
        f"- Claim chưa có căn cứ: {len(unsupported)}/{len(version.claims)}",
    ]
    return "\n".join(line for line in lines if line is not None) + "\n"
