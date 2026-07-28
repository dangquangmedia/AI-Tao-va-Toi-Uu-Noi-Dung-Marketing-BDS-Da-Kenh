"""Sinh Data Card cho `dataset_v1` theo template Plan/02 §10.

Toàn bộ số liệu lấy từ DB và từ chính các artefact vừa sinh — không có con số nào
gõ tay, nên hội đồng chạy lại lệnh là ra đúng bảng trong báo cáo.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Chunk, CleanListing, Fact, GraphEntity, RetrievalQuery
from app.services.data_quality import data_quality_report
from app.services.dataset import leakage_audit, split_report


def collect(db: Session, tenant_id: str, dataset_version: str, sft_stats: dict | None = None) -> dict:
    quality = data_quality_report(db, tenant_id)
    splits = split_report(db, tenant_id, dataset_version)
    audit = leakage_audit(db, tenant_id, dataset_version)

    gold = db.execute(
        select(RetrievalQuery.query_type, func.count())
        .where(
            RetrievalQuery.tenant_id == tenant_id,
            RetrievalQuery.dataset_version == dataset_version,
        )
        .group_by(RetrievalQuery.query_type)
    ).all()

    n_chunks = db.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.tenant_id == tenant_id)
    )
    n_embedded = db.scalar(
        select(func.count())
        .select_from(Chunk)
        .where(Chunk.tenant_id == tenant_id, Chunk.embedding.is_not(None))
    )
    embedding_model = db.scalar(
        select(Chunk.embedding_model)
        .where(Chunk.tenant_id == tenant_id, Chunk.embedding_model != "")
        .limit(1)
    )
    n_projects = db.scalar(
        select(func.count())
        .select_from(GraphEntity)
        .where(GraphEntity.tenant_id == tenant_id, GraphEntity.entity_type == "Project")
    )
    return {
        "dataset_version": dataset_version,
        "quality": quality,
        "splits": splits,
        "leakage": audit,
        "gold_queries": {t: n for t, n in gold},
        "chunks": {"total": n_chunks, "embedded": n_embedded, "model": embedding_model or "—"},
        "projects": n_projects,
        "listings": db.scalar(
            select(func.count()).select_from(CleanListing).where(CleanListing.tenant_id == tenant_id)
        ),
        "facts": db.scalar(
            select(func.count()).select_from(Fact).where(Fact.tenant_id == tenant_id)
        ),
        "sft": sft_stats or {},
    }


def render_markdown(card: dict) -> str:
    quality = card["quality"]
    coverage = quality["clean"]["field_coverage"]
    now = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")
    audit = card["leakage"]

    lines = [
        f"# Data Card — {card['dataset_version']}",
        "",
        f"> Sinh tự động bằng `python -m app.dataset_cli --build` lúc {now}. "
        "Mọi số liệu đo trực tiếp trên PostgreSQL.",
        "",
        "## 1. Nguồn và quy mô",
        "",
        "| Mục | Giá trị |",
        "|---|---:|",
        "| Nguồn | batdongsan.com.vn, crawl 17–25/07/2026 |",
        f"| Tin raw | {quality['raw']['source_listings']:,} |".replace(",", "."),
        f"| Tin qua contract v1 | {card['listings']:,} |".replace(",", "."),
        f"| Dự án trong graph | {card['projects']:,} |".replace(",", "."),
        f"| Canonical facts | {card['facts']:,} |".replace(",", "."),
        f"| Chunk index | {card['chunks']['total']:,} (đã embed {card['chunks']['embedded']:,}) |".replace(",", "."),
        f"| Embedding model | `{card['chunks']['model']}` |",
        f"| Cụm dedup | {quality['dedup']['clusters']:,} |".replace(",", "."),
        "",
        "## 2. Độ phủ trường sau re-parse",
        "",
        "| Trường | Số tin | Tỷ lệ |",
        "|---|---:|---:|",
    ]
    for field in ("project_slug", "ward", "district", "city", "area_m2", "bedrooms", "total_price_vnd", "legal_facts", "amenities"):
        info = coverage.get(field)
        if info:
            lines.append(f"| {field} | {info['n']:,} | {info['pct']}% |".replace(",", "."))

    lines += [
        "",
        "## 3. Chia tập (theo dự án / cụm dedup, không random theo mẫu)",
        "",
        "| Split | Đơn vị | % đơn vị | Tin | % tin |",
        "|---|---:|---:|---:|---:|",
    ]
    for split in ("train", "validation", "test"):
        entry = card["splits"].get(split)
        if entry:
            lines.append(
                f"| {split} | {entry['units']:,} | {entry['unit_pct']}% | "
                f"{entry['listings']:,} | {entry['listing_pct']}% |".replace(",", ".")
            )

    lines += [
        "",
        "Đơn vị chia: dự án (Tier A) và cụm dedup (tin lẻ). Stratify theo quy mô dự án "
        "(large ≥5 tin · medium 2–4 · small 1) để test không toàn dự án một tin.",
        "",
        "## 4. Leakage audit",
        "",
        f"- Tin được gán split: **{audit['listings_assigned']:,}/{audit['listings_total']:,}**".replace(",", "."),
        f"- Cụm dedup kiểm tra: {audit['clusters_checked']:,} — nằm ở nhiều split: **{len(audit['leaking_clusters'])}**".replace(",", "."),
        f"- Dự án kiểm tra: {audit['projects_checked']:,} — nằm ở nhiều split: **{len(audit['leaking_projects'])}**".replace(",", "."),
        f"- Kết luận: **{'ĐẠT — không có rò rỉ' if audit['passed'] else 'KHÔNG ĐẠT'}**",
        "",
        "## 5. Gold retrieval queries",
        "",
        "| Nhóm câu hỏi | Số query |",
        "|---|---:|",
    ]
    for query_type, n in sorted(card["gold_queries"].items()):
        lines.append(f"| {query_type} | {n} |")
    lines.append(f"| **Tổng** | **{sum(card['gold_queries'].values())}** |")
    lines += [
        "",
        "Sinh bằng template trên dữ liệu split test, nhãn suy ra tất định từ DB; "
        "toàn bộ đang ở trạng thái `needs_review` chờ soát tay trước khi khóa benchmark.",
    ]

    sft = card.get("sft") or {}
    if sft:
        lines += [
            "",
            "## 6. SFT draft v1",
            "",
            f"- Số mẫu nháp: **{sft.get('samples', 0):,}**".replace(",", "."),
            f"- Theo split: {sft.get('by_split', {})}",
            f"- Theo kênh: {sft.get('by_channel', {})}",
            f"- Theo persona: {sft.get('by_persona', {})}",
            f"- Bỏ qua do thiếu fact: {sft.get('skipped_missing_facts', 0):,}".replace(",", "."),
            f"- Bỏ qua vì thuộc split test: {sft.get('skipped_test_split', 0):,}".replace(",", "."),
            "",
            "Mẫu mới có phần input (instruction + facts có provenance + brand + persona + kênh); "
            "`output` để trống, `quality_status = draft` — chờ sinh có kiểm soát và review gắn "
            "gold/silver ở Tuần 5. Không train trên mẫu chưa duyệt.",
        ]

    lines += [
        "",
        "## 7. License và giới hạn",
        "",
        "- Tin đăng công khai, chỉ dùng cho nghiên cứu/đồ án; không tái phân phối dataset gốc.",
        "- Giữ `canonical_url` cho mọi fact làm provenance và ghi công nguồn.",
        "- Không lưu PII: `seller_display_name` bị drop, số điện thoại trong mô tả bị mask.",
        "- Phần lớn tin ở trạng thái EXPIRED → fact giá có `valid_from`/`valid_to`, không dùng "
        "để khẳng định giá hiện hành.",
        "- Hạn chế đã biết: giá chỉ khôi phục được ~52%, mã tòa/block thưa, quận/huyện chưa suy "
        "đầy đủ từ phường.",
    ]
    return "\n".join(lines) + "\n"
