"""Sinh bộ gold query cho benchmark retrieval R1–R3 (Plan/02 §8).

Sáu nhóm câu hỏi theo đúng kế hoạch: dữ kiện đơn · quan hệ 1-hop · quan hệ 2-hop ·
so sánh hai dự án · dữ liệu mâu thuẫn · dữ liệu hết hiệu lực (temporal).

Câu hỏi sinh bằng **template trên dữ liệu thật của split test** (không dùng LLM) nên:
- nhãn đúng/sai suy ra được tất định từ DB → đo lại lúc nào cũng ra cùng số;
- không rò rỉ tri thức của model sinh câu hỏi vào bộ đánh giá.

Mọi query gắn `needs_review=True`: Hải soát tay trước khi khóa bộ benchmark
(bước bắt buộc trong Plan/03 §4 — không lấy nhãn tự sinh làm nhãn cuối).
"""

import hashlib
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import CleanListing, GraphEdge, GraphEntity, RetrievalQuery
from app.services.dataset import split_of_listing

PER_TYPE = 12  # 6 nhóm × 12 ≈ 72 query, nằm giữa khoảng 60–90 của Plan/02 §8
MIN_LISTINGS_FOR_COMPARE = 2


def _key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


def _price_text(value: float | None) -> str:
    if not value:
        return ""
    return f"{value / 1_000_000_000:.2f} tỷ".replace(".00", "")


def _project_display(rows: list[CleanListing]) -> str:
    for row in rows:
        if row.project_name:
            return row.project_name
    return rows[0].project_slug.replace("-", " ").title()


def generate_gold_queries(db: Session, tenant_id: str, dataset_version: str) -> dict:
    """Sinh lại toàn bộ gold query cho một phiên bản dataset (idempotent)."""
    listing_split = split_of_listing(db, tenant_id, dataset_version)
    rows = db.scalars(select(CleanListing).where(CleanListing.tenant_id == tenant_id)).all()

    test_rows = [r for r in rows if listing_split.get(r.id) == "test" and r.project_slug]
    by_project: dict[str, list[CleanListing]] = defaultdict(list)
    for row in test_rows:
        by_project[row.project_slug].append(row)
    # Ưu tiên dự án nhiều tin → câu hỏi có đủ dữ kiện để chấm
    ranked = sorted(by_project.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    edges = db.scalars(select(GraphEdge).where(GraphEdge.tenant_id == tenant_id)).all()
    buildings_of: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.edge_type != "PART_OF":
            continue
        src = db.get(GraphEntity, edge.src_id)
        dst = db.get(GraphEntity, edge.dst_id)
        if src is not None and dst is not None and src.entity_type == "Building":
            buildings_of[dst.canonical_key].append(src.name)

    specs: list[dict] = []

    def add(query_type: str, question: str, project: str, listings: list[CleanListing], expected_entities: list[str], generator: str):
        specs.append(
            {
                "query_type": query_type,
                "question": question,
                "project_slug": project,
                "expected_listing_ids": sorted(r.id for r in listings),
                "expected_entities": expected_entities,
                "generator": generator,
            }
        )

    # 1) Dữ kiện đơn — giá của một loại căn trong dự án
    count = 0
    for slug, members in ranked:
        if count >= PER_TYPE:
            break
        priced = [r for r in members if r.total_price_vnd and r.bedrooms]
        if not priced:
            continue
        target = min(priced, key=lambda r: r.id)
        name = _project_display(members)
        add(
            "fact",
            f"Căn {target.bedrooms} phòng ngủ tại dự án {name} giá bao nhiêu?",
            slug,
            [r for r in priced if r.bedrooms == target.bedrooms],
            [slug],
            "fact_price_by_bedrooms",
        )
        count += 1

    # 2) Quan hệ 1-hop — dự án nằm ở phường/quận nào
    count = 0
    for slug, members in ranked:
        if count >= PER_TYPE:
            break
        located = next((r for r in members if r.ward or r.district), None)
        if located is None:
            continue
        name = _project_display(members)
        place = located.district or located.ward.replace("-", " ").title()
        add(
            "one_hop",
            f"Dự án {name} nằm ở khu vực nào?",
            slug,
            members,
            [slug, place],
            "one_hop_location",
        )
        count += 1

    # 3) Quan hệ 2-hop — tòa nào của dự án có loại căn nào / dự án thuộc quận-thành phố nào
    count = 0
    for slug, members in ranked:
        if count >= PER_TYPE:
            break
        name = _project_display(members)
        if buildings_of.get(slug):
            add(
                "two_hop",
                f"Dự án {name} có những tòa nào và mỗi tòa có loại căn gì?",
                slug,
                [r for r in members if r.building_code],
                [slug, *sorted(buildings_of[slug])],
                "two_hop_building_unittype",
            )
            count += 1
            continue
        located = next((r for r in members if r.district and r.city), None)
        if located is None:
            continue
        add(
            "two_hop",
            f"Dự án {name} thuộc quận nào của tỉnh/thành nào?",
            slug,
            members,
            [slug, located.district, located.city],
            "two_hop_ward_district_city",
        )
        count += 1

    # 4) So sánh hai dự án cùng khu vực
    count = 0
    by_city: dict[str, list[tuple[str, list[CleanListing]]]] = defaultdict(list)
    for slug, members in ranked:
        city = next((r.city for r in members if r.city), None)
        if city:
            by_city[city].append((slug, members))
    for city, group in sorted(by_city.items()):
        for i in range(0, len(group) - 1, 2):
            if count >= PER_TYPE:
                break
            (slug_a, members_a), (slug_b, members_b) = group[i], group[i + 1]
            if len(members_a) < MIN_LISTINGS_FOR_COMPARE and len(members_b) < MIN_LISTINGS_FOR_COMPARE:
                continue
            add(
                "compare",
                f"So sánh giá và diện tích căn hộ giữa dự án {_project_display(members_a)} "
                f"và dự án {_project_display(members_b)} tại {city}.",
                slug_a,
                members_a + members_b,
                [slug_a, slug_b],
                "compare_two_projects",
            )
            count += 1

    # 5) Dữ liệu mâu thuẫn — cùng dự án, cùng số phòng ngủ nhưng giá lệch nhau
    count = 0
    for slug, members in ranked:
        if count >= PER_TYPE:
            break
        grouped: dict[int, list[CleanListing]] = defaultdict(list)
        for row in members:
            if row.bedrooms and row.total_price_vnd:
                grouped[row.bedrooms].append(row)
        conflict = next(
            (
                (bedrooms, group)
                for bedrooms, group in sorted(grouped.items())
                if len({round(r.total_price_vnd) for r in group}) > 1
            ),
            None,
        )
        if conflict is None:
            continue
        bedrooms, group = conflict
        prices = ", ".join(sorted({_price_text(r.total_price_vnd) for r in group}))
        add(
            "conflict",
            f"Căn {bedrooms} phòng ngủ tại dự án {_project_display(members)} đang được rao ở "
            f"nhiều mức giá ({prices}) — dữ liệu nào là nguồn nào?",
            slug,
            group,
            [slug],
            "conflict_price_same_unit",
        )
        count += 1

    # 6) Temporal — tin đã hết hạn, giá chỉ còn giá trị tham chiếu
    count = 0
    for slug, members in ranked:
        if count >= PER_TYPE:
            break
        priced = [r for r in members if r.total_price_vnd]
        if not priced:
            continue
        add(
            "temporal",
            f"Thông tin giá của dự án {_project_display(members)} được ghi nhận vào thời điểm nào "
            "và còn hiệu lực không?",
            slug,
            priced,
            [slug],
            "temporal_price_validity",
        )
        count += 1

    db.execute(
        delete(RetrievalQuery).where(
            RetrievalQuery.tenant_id == tenant_id,
            RetrievalQuery.dataset_version == dataset_version,
        )
    )
    counts: dict[str, int] = defaultdict(int)
    for spec in specs:
        db.add(
            RetrievalQuery(
                tenant_id=tenant_id,
                dataset_version=dataset_version,
                query_key=_key(dataset_version, spec["query_type"], spec["question"]),
                split="test",
                needs_review=True,
                **spec,
            )
        )
        counts[spec["query_type"]] += 1
    db.commit()
    return {"total": len(specs), "by_type": dict(counts)}
