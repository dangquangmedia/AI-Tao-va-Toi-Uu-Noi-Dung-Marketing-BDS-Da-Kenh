"""Sinh bộ gold query cho benchmark retrieval R1–R3 (Plan/02 §8).

**Bộ standard** — sáu nhóm theo đúng kế hoạch: dữ kiện đơn · quan hệ 1-hop · quan hệ
2-hop · so sánh hai dự án · dữ liệu mâu thuẫn · dữ liệu hết hiệu lực (temporal). Mọi câu
đều **nêu tên dự án**.

**Bộ hard (Tuần 6)** — ba nhóm câu hỏi mô tả **không nêu tên dự án**: theo thuộc tính ·
theo khoảng giá · theo địa bàn. Lý do phải có: bộ standard nêu tên nên router nhận ra
dự án rồi lọc thẳng theo `project_slug`, đẩy precision lên 1,000 — con số đó đo khả năng
nhận diện tên chứ chưa đo khả năng tìm kiếm. Người dùng thật thường gõ "căn 2 phòng ngủ
tầm 3 tỷ ở Quận 7", không gõ tên dự án.

Câu hỏi sinh bằng **template trên dữ liệu thật** (không dùng LLM) nên:
- nhãn đúng/sai suy ra được tất định từ DB → đo lại lúc nào cũng ra cùng số;
- không rò rỉ tri thức của model sinh câu hỏi vào bộ đánh giá.

Câu hỏi mô tả có **nhiều đáp án đúng**: nhãn là *mọi* tin khớp điều kiện, không phải
riêng tin đã dùng để dựng câu. Chấm theo một tin nguồn sẽ phạt oan hệ thống khi nó trả
về một tin khác cũng đúng.

Mọi query gắn `needs_review=True`: Hải soát tay trước khi khóa bộ benchmark
(bước bắt buộc trong Plan/03 §4 — không lấy nhãn tự sinh làm nhãn cuối).
"""

import hashlib
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import CleanListing, GraphEdge, GraphEntity, RetrievalQuery
from app.services.alias import find_display_name
from app.services.dataset import split_of_listing

PER_TYPE = 12  # 6 nhóm × 12 ≈ 72 query, nằm giữa khoảng 60–90 của Plan/02 §8
PER_HARD_TYPE = 12  # 3 nhóm × 12 = 36 query mô tả, không nêu tên dự án
MIN_LISTINGS_FOR_COMPARE = 2
AREA_TOLERANCE = 0.15  # "khoảng 70 m²" chấp nhận ±15% — nhãn phải khớp cách người hỏi nghĩ

PROPERTY_TYPE_LABELS = {
    "apartment": "căn hộ",
    "private_house": "nhà riêng",
    "street_house": "nhà mặt phố",
    "villa": "biệt thự",
    "shophouse": "shophouse",
    "land": "đất nền",
    "project_land": "đất nền dự án",
    "condotel": "condotel",
    "warehouse": "nhà xưởng",
    "resort": "resort",
}

# Dải giá dùng cho câu hỏi theo ngân sách — biên tròn theo cách người mua nói.
PRICE_BANDS = (
    (0, 2_000_000_000, "dưới 2 tỷ"),
    (2_000_000_000, 3_000_000_000, "từ 2 đến 3 tỷ"),
    (3_000_000_000, 5_000_000_000, "từ 3 đến 5 tỷ"),
    (5_000_000_000, 10_000_000_000, "từ 5 đến 10 tỷ"),
    (10_000_000_000, float("inf"), "trên 10 tỷ"),
)


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


MIN_HARD_ANSWERS = 3  # dưới 3 đáp án đúng thì precision@10 bị trần quá thấp để đọc được


def _type_label(property_type: str) -> str:
    return PROPERTY_TYPE_LABELS.get(property_type, "bất động sản")


def _ward_label(ward: str, members: list[CleanListing]) -> str:
    """Tên phường **có dấu**, lấy từ chính tin đăng nhắc tới nó.

    `ward` trong DB là slug lấy từ URL nên không dấu. Hỏi "ở Me Tri" thay vì "ở Mễ Trì"
    sẽ phạt oan nhánh vector (BM25 bỏ dấu cả hai phía nên không ảnh hưởng) — chênh lệch
    đo được khi đó là do thiếu dấu chứ không phải do năng lực truy xuất.
    """
    for row in sorted(members, key=lambda r: r.id):
        found = find_display_name(ward, f"{row.title_clean} {row.description_clean}")
        if found:
            # Tin đăng hay viết hoa toàn bộ ("AN KHÁNH") — chuẩn hóa để câu hỏi đọc tự nhiên
            return found.title() if found.isupper() else found
    return ward.replace("-", " ").title()


def _hard_spec(query_type: str, question: str, matches: list[CleanListing], generator: str) -> dict:
    """Đóng gói một câu hỏi mô tả: nhãn là *mọi* tin trong corpus khớp điều kiện."""
    return {
        "query_type": query_type,
        "question": question,
        "difficulty": "hard",
        "project_slug": None,  # câu hỏi cố ý không nêu dự án nào
        "expected_listing_ids": sorted(r.id for r in matches),
        "expected_projects": sorted({r.project_slug for r in matches if r.project_slug}),
        "expected_entities": [],
        "generator": generator,
    }


def _hard_specs(corpus: list[CleanListing]) -> list[dict]:
    """Ba nhóm câu hỏi mô tả, không nêu tên dự án (Tuần 6).

    Không dùng `project_name` ở bất kỳ đâu trong câu hỏi — đó là điều kiện của bộ này.
    Router vì thế không nhận ra dự án nào, không lọc theo `project_slug`, nên số đo phản
    ánh đúng năng lực tìm kiếm chứ không phải năng lực khớp tên.

    Nhãn tính trên **toàn bộ corpus**, không giới hạn split test như bộ standard. Lý do:
    chỉ mục truy xuất chứa cả ba split, nên một tin ở split train khớp đúng mô tả vẫn là
    đáp án đúng; chấm nó là sai chỉ vì nó không thuộc test là tạo ra âm tính giả. Bộ
    standard không gặp chuyện này vì mọi tin của một dự án đều nằm cùng một split.
    """
    specs: list[dict] = []

    # 1) Theo thuộc tính — loại hình + số phòng ngủ + diện tích + quận
    groups: dict[tuple, list[CleanListing]] = defaultdict(list)
    for row in corpus:
        if row.district and row.property_type and row.bedrooms and row.area_m2:
            groups[(row.district, row.property_type, row.bedrooms)].append(row)
    count = 0
    for key, members in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if count >= PER_HARD_TYPE:
            break
        district, property_type, bedrooms = key
        anchor = min(members, key=lambda r: r.id)
        matches = [
            r for r in members if abs(r.area_m2 - anchor.area_m2) <= AREA_TOLERANCE * anchor.area_m2
        ]
        if len(matches) < MIN_HARD_ANSWERS:
            continue
        specs.append(
            _hard_spec(
                "hard_attribute",
                f"Tìm {_type_label(property_type)} {bedrooms} phòng ngủ, diện tích khoảng "
                f"{anchor.area_m2:.0f} m², tại {district}.",
                matches,
                "hard_attribute_bedrooms_area",
            )
        )
        count += 1

    # 2) Theo ngân sách — loại hình + quận + dải giá
    budget: dict[tuple, list[CleanListing]] = defaultdict(list)
    for row in corpus:
        if not (row.district and row.property_type and row.total_price_vnd):
            continue
        band = next(b for b in PRICE_BANDS if b[0] <= row.total_price_vnd < b[1])
        budget[(row.district, row.property_type, band[2])].append(row)
    count = 0
    for key, members in sorted(budget.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if count >= PER_HARD_TYPE:
            break
        if len(members) < MIN_HARD_ANSWERS:
            continue
        district, property_type, band_label = key
        specs.append(
            _hard_spec(
                "hard_budget",
                f"Có {_type_label(property_type)} nào ở {district} tầm giá {band_label} không?",
                members,
                "hard_budget_district_band",
            )
        )
        count += 1

    # 3) Theo địa bàn — phường/xã, không kèm thuộc tính nào khác
    by_ward: dict[tuple, list[CleanListing]] = defaultdict(list)
    for row in corpus:
        # Bỏ slug phường chỉ có số hoặc quá ngắn ("12") — hỏi "ở 12?" thì câu hỏi vô nghĩa
        # và không đo được gì; đây là rác còn lại của việc cắt slug từ URL.
        if row.ward and len(row.ward) >= 3 and not row.ward.isdigit():
            by_ward[(row.ward, row.district or "")].append(row)
    count = 0
    for (ward, district), members in sorted(by_ward.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if count >= PER_HARD_TYPE:
            break
        if len(members) < MIN_HARD_ANSWERS:
            continue
        place = _ward_label(ward, members) + (f", {district}" if district else "")
        specs.append(
            _hard_spec(
                "hard_location",
                f"Đang rao bán những bất động sản nào ở {place}?",
                members,
                "hard_location_ward",
            )
        )
        count += 1

    return specs


def generate_gold_queries(db: Session, tenant_id: str, dataset_version: str) -> dict:
    """Sinh lại toàn bộ gold query cho một phiên bản dataset (idempotent)."""
    listing_split = split_of_listing(db, tenant_id, dataset_version)
    rows = db.scalars(select(CleanListing).where(CleanListing.tenant_id == tenant_id)).all()

    # Bộ standard hỏi theo tên dự án nên chỉ lấy tin thuộc split test và đã gắn dự án —
    # giữ nguyên quy ước từ Tuần 3. Bộ hard dùng toàn bộ `rows` (xem `_hard_specs`).
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

    def add(
        query_type: str,
        question: str,
        project: str | None,
        listings: list[CleanListing],
        expected_entities: list[str],
        generator: str,
        difficulty: str = "standard",
        expected_projects: list[str] | None = None,
    ):
        if expected_projects is None:
            # Mặc định: dự án đích + mọi slug dự án khác được nhắc tới (câu so sánh có hai
            # dự án cùng đúng). Nhãn địa danh/tòa ("Quận 7", "Tòa V8") có khoảng trắng hoặc
            # chữ hoa nên bị loại — giữ đúng cách chấm đã dùng từ Tuần 3.
            expected_projects = ([project] if project else []) + [
                e for e in expected_entities if isinstance(e, str) and " " not in e and e.islower()
            ]
        specs.append(
            {
                "query_type": query_type,
                "question": question,
                "difficulty": difficulty,
                "project_slug": project,
                "expected_listing_ids": sorted(r.id for r in listings),
                "expected_projects": sorted(set(expected_projects)),
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

    specs += _hard_specs(rows)

    db.execute(
        delete(RetrievalQuery).where(
            RetrievalQuery.tenant_id == tenant_id,
            RetrievalQuery.dataset_version == dataset_version,
        )
    )
    counts: dict[str, int] = defaultdict(int)
    by_difficulty: dict[str, int] = defaultdict(int)
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
        by_difficulty[spec["difficulty"]] += 1
    db.commit()
    return {"total": len(specs), "by_type": dict(counts), "by_difficulty": dict(by_difficulty)}
