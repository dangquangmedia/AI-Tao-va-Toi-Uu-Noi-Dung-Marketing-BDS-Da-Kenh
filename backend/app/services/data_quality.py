"""Báo cáo chất lượng dữ liệu sau D1–D5 (deliverable Tuần 2).

Toàn bộ số liệu được **đo trực tiếp trên DB**, không nhập tay — báo cáo trong
`docs/checkpoints/` được sinh từ chính hàm này để hội đồng kiểm chứng lại được.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    CleanListing,
    Fact,
    GraphEdge,
    GraphEntity,
    IngestionJob,
    QuarantineRecord,
    SourceListing,
)

TOP_PROJECTS = 10


def _count(db: Session, model, tenant_id: str, *conditions) -> int:
    return db.scalar(
        select(func.count()).select_from(model).where(model.tenant_id == tenant_id, *conditions)
    )


def _group(db: Session, column, tenant_id: str, model, *conditions) -> dict:
    rows = db.execute(
        select(column, func.count())
        .select_from(model)
        .where(model.tenant_id == tenant_id, *conditions)
        .group_by(column)
        .order_by(func.count().desc())
    ).all()
    return {str(k): v for k, v in rows}


def data_quality_report(db: Session, tenant_id: str) -> dict:
    raw_total = _count(db, SourceListing, tenant_id)
    clean_total = _count(db, CleanListing, tenant_id)

    def coverage(*conditions) -> dict:
        n = _count(db, CleanListing, tenant_id, *conditions)
        return {"n": n, "pct": round(100 * n / clean_total, 1) if clean_total else 0.0}

    fields = {
        "project_slug": coverage(CleanListing.project_slug.is_not(None)),
        "building_code": coverage(CleanListing.building_code.is_not(None)),
        "ward": coverage(CleanListing.ward.is_not(None)),
        "district": coverage(CleanListing.district.is_not(None)),
        "city": coverage(CleanListing.city.is_not(None)),
        "area_m2": coverage(CleanListing.area_m2.is_not(None)),
        "bedrooms": coverage(CleanListing.bedrooms.is_not(None)),
        "total_price_vnd": coverage(CleanListing.total_price_vnd.is_not(None)),
        "price_per_m2_vnd": coverage(CleanListing.price_per_m2_vnd.is_not(None)),
    }
    # Cột JSON: đếm trong Python để câu lệnh chạy giống nhau trên PostgreSQL và SQLite
    for field in ("legal_facts", "amenities"):
        rows = db.scalars(
            select(getattr(CleanListing, field)).where(CleanListing.tenant_id == tenant_id)
        ).all()
        n = sum(1 for r in rows if r)
        fields[field] = {"n": n, "pct": round(100 * n / clean_total, 1) if clean_total else 0.0}

    n_representative = _count(db, CleanListing, tenant_id, CleanListing.is_cluster_representative.is_(True))
    n_clusters = db.scalar(
        select(func.count(func.distinct(CleanListing.dedup_cluster_id))).where(
            CleanListing.tenant_id == tenant_id
        )
    )

    top_projects = db.execute(
        select(GraphEntity.canonical_key, GraphEntity.name, GraphEntity.support_count)
        .where(GraphEntity.tenant_id == tenant_id, GraphEntity.entity_type == "Project")
        .order_by(GraphEntity.support_count.desc(), GraphEntity.canonical_key)
        .limit(TOP_PROJECTS)
    ).all()

    last_clean_job = db.scalar(
        select(IngestionJob)
        .where(IngestionJob.tenant_id == tenant_id, IngestionJob.job_type == "clean_pipeline")
        .order_by(IngestionJob.started_at.desc())
        .limit(1)
    )

    return {
        "raw": {"source_listings": raw_total},
        "clean": {
            "total": clean_total,
            "by_tier": _group(db, CleanListing.tier, tenant_id, CleanListing),
            "by_property_type": _group(db, CleanListing.property_type, tenant_id, CleanListing),
            "by_price_confidence": _group(db, CleanListing.price_confidence, tenant_id, CleanListing),
            "field_coverage": fields,
        },
        "dedup": {
            "clusters": n_clusters,
            "representatives": n_representative,
            "duplicates": clean_total - n_representative,
        },
        "quarantine": {
            "total": _count(db, QuarantineRecord, tenant_id),
            "by_error": _group(db, QuarantineRecord.error_code, tenant_id, QuarantineRecord),
        },
        "facts": {
            "total": _count(db, Fact, tenant_id),
            "by_predicate": _group(db, Fact.predicate, tenant_id, Fact),
            "needs_review": _count(db, Fact, tenant_id, Fact.needs_review.is_(True)),
        },
        "graph": {
            "entities": _count(db, GraphEntity, tenant_id),
            "by_entity_type": _group(db, GraphEntity.entity_type, tenant_id, GraphEntity),
            "edges": _count(db, GraphEdge, tenant_id),
            "by_edge_type": _group(db, GraphEdge.edge_type, tenant_id, GraphEdge),
            "top_projects": [
                {"key": key, "name": name, "listings": support} for key, name, support in top_projects
            ],
        },
        "last_pipeline_job": {
            "id": last_clean_job.id,
            "status": last_clean_job.status,
            "total_read": last_clean_job.total_read,
            "inserted": last_clean_job.inserted,
            "unchanged": last_clean_job.unchanged,
            "updated": last_clean_job.updated,
            "quarantined": last_clean_job.quarantined,
            "stats": last_clean_job.stats,
        }
        if last_clean_job
        else None,
    }


FIELD_LABELS = {
    "project_slug": "Dự án (từ canonical_url)",
    "building_code": "Mã tòa/block",
    "ward": "Phường/xã (từ URL)",
    "district": "Quận/huyện",
    "city": "Tỉnh/thành",
    "area_m2": "Diện tích",
    "bedrooms": "Số phòng ngủ",
    "total_price_vnd": "Giá tổng",
    "price_per_m2_vnd": "Giá/m²",
    "legal_facts": "Pháp lý",
    "amenities": "Tiện ích",
}


def _table(title: str, mapping: dict) -> str:
    lines = [f"**{title}**", "", "| Giá trị | Số lượng |", "|---|---:|"]
    lines += [f"| {k} | {v:,} |".replace(",", ".") for k, v in mapping.items()]
    return "\n".join(lines) + "\n"


def render_markdown(report: dict) -> str:
    """Sinh báo cáo chất lượng dữ liệu dạng Markdown từ số đo thật trong DB."""
    clean = report["clean"]
    total = clean["total"] or 1
    now = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")

    lines = [
        "# Báo cáo chất lượng dữ liệu sau pipeline D1–D5",
        "",
        f"> Sinh tự động bằng `python -m app.pipeline_cli --report` lúc {now}. "
        "Mọi con số đo trực tiếp trên PostgreSQL, không nhập tay.",
        "",
        "## 1. Quy mô",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---:|",
        f"| Tin trong raw zone | {report['raw']['source_listings']:,} |".replace(",", "."),
        f"| Tin qua được contract v1 (clean) | {clean['total']:,} |".replace(",", "."),
        f"| Bản ghi quarantine | {report['quarantine']['total']:,} |".replace(",", "."),
        f"| Canonical facts | {report['facts']['total']:,} |".replace(",", "."),
        f"| Fact cần review | {report['facts']['needs_review']:,} |".replace(",", "."),
        f"| Node graph | {report['graph']['entities']:,} |".replace(",", "."),
        f"| Cạnh graph | {report['graph']['edges']:,} |".replace(",", "."),
        f"| Cụm dedup | {report['dedup']['clusters']:,} |".replace(",", "."),
        f"| Tin bị coi là bản trùng | {report['dedup']['duplicates']:,} |".replace(",", "."),
        "",
        "## 2. Độ phủ trường sau re-parse",
        "",
        "| Trường | Số tin có giá trị | Tỷ lệ |",
        "|---|---:|---:|",
    ]
    for field, label in FIELD_LABELS.items():
        info = clean["field_coverage"].get(field)
        if info:
            lines.append(f"| {label} | {info['n']:,} | {info['pct']}% |".replace(",", "."))

    lines += [
        "",
        "## 3. Phân bố",
        "",
        _table("Theo tier (Plan/02 §5)", clean["by_tier"]),
        _table("Theo loại hình", clean["by_property_type"]),
        _table("Theo độ tin của giá", clean["by_price_confidence"]),
        "## 4. Quarantine",
        "",
        _table("Theo mã lỗi", report["quarantine"]["by_error"]),
        "## 5. Facts và graph",
        "",
        _table("Fact theo predicate", report["facts"]["by_predicate"]),
        _table("Node theo loại", report["graph"]["by_entity_type"]),
        _table("Cạnh theo loại", report["graph"]["by_edge_type"]),
        "**Dự án nhiều tin nhất**",
        "",
        "| Dự án | Slug | Số tin |",
        "|---|---|---:|",
    ]
    for project in report["graph"]["top_projects"]:
        lines.append(f"| {project['name']} | `{project['key']}` | {project['listings']} |")

    job = report.get("last_pipeline_job")
    if job:
        lines += [
            "",
            "## 6. Lần chạy pipeline gần nhất",
            "",
            f"- Job `{job['id']}` — trạng thái **{job['status']}**",
            f"- Đọc {job['total_read']:,} tin: thêm {job['inserted']:,} · giữ nguyên "
            f"{job['unchanged']:,} · cập nhật {job['updated']:,} · quarantine {job['quarantined']:,}".replace(",", "."),
            f"- Chi tiết D3–D5: `{job['stats']}`",
        ]
    lines += [
        "",
        f"_Tỷ lệ tin sạch trên raw: {round(100 * clean['total'] / max(report['raw']['source_listings'], 1), 1)}%_",
        f"_Tỷ lệ đại diện cụm (sau dedup): {round(100 * report['dedup']['representatives'] / total, 1)}%_",
    ]
    return "\n".join(lines) + "\n"
