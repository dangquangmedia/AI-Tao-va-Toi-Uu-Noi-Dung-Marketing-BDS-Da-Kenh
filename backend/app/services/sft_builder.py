"""Dựng bản nháp dataset SFT v1 theo schema Plan/02 §7.1 (Tuần 3).

Quan trọng về mặt học thuật: file này **chỉ dựng phần input** (instruction + facts +
brand + persona + kênh) từ dữ liệu thật đã có provenance. Trường `output` để trống và
`quality_status = "draft"`.

Vì sao không tự sinh output ở đây: mẫu huấn luyện mà do chính model sinh rồi đem train
lại thì kết quả thí nghiệm mất giá trị. Theo Plan/02 §7.2, output được sinh có kiểm soát
rồi **người review gắn gold/silver**; chỉ mẫu đã duyệt mới vào tập train (Tuần 5).

Mẫu chỉ lấy từ split train/validation — dự án thuộc test không bao giờ xuất hiện.
"""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CleanListing, Fact
from app.services.chunking import PREDICATE_LABELS, _format_price
from app.services.dataset import split_of_listing

CHANNELS = (
    {"name": "description", "length": "180-260 từ", "format_rules": ["mở bài nêu vị trí", "kết bằng CTA xem nhà"]},
    {"name": "facebook", "length": "80-140 từ", "format_rules": ["3-5 dòng ngắn", "tối đa 5 emoji", "hashtag cuối bài"]},
    {"name": "email", "length": "120-200 từ", "format_rules": ["có subject", "xưng hô lịch sự", "1 CTA duy nhất"]},
    {"name": "landing_seo", "length": "250-400 từ", "format_rules": ["có H1/H2", "từ khóa chính ở 100 từ đầu"]},
)
PERSONAS = (
    {"segment": "young_family", "needs": ["gần trường học", "an ninh", "không gian sinh hoạt"], "objections": ["giá vượt ngân sách", "xa nơi làm việc"]},
    {"segment": "investor", "needs": ["khả năng cho thuê", "pháp lý rõ ràng", "thanh khoản"], "objections": ["giá đã cao", "nguồn cung lớn"]},
    {"segment": "first_home", "needs": ["thanh toán linh hoạt", "diện tích vừa phải", "bàn giao sớm"], "objections": ["lo thủ tục vay", "sợ chậm bàn giao"]},
)
BRAND_DEMO = {
    "tone": ["tin cậy", "rõ ràng", "không thổi phồng"],
    "required_terms": ["diện tích", "vị trí"],
    "forbidden_terms": ["cam kết lợi nhuận", "chắc chắn sinh lời", "rẻ nhất thị trường"],
}
MIN_FACTS = 3
DRAFT_STATUS = "draft"


def _sample_id(listing_id: str, channel: str, persona: str) -> str:
    return hashlib.sha256(f"{listing_id}|{channel}|{persona}".encode()).hexdigest()[:24]


def _fact_payload(fact: Fact) -> dict:
    label = PREDICATE_LABELS.get(fact.predicate, fact.predicate)
    if fact.predicate in ("total_price_vnd", "price_per_m2_vnd") and fact.value_num:
        value = _format_price(fact.value_num)
    else:
        value = fact.value_text
    return {
        "fact_id": fact.id,
        "predicate": fact.predicate,
        "text": f"{label}: {value}",
        "source_id": fact.source_listing_id,
        "source_url": fact.source_url,
        "confidence": fact.confidence,
        "valid_from": fact.valid_from,
        "valid_to": fact.valid_to,
    }


def build_sft_draft(
    db: Session,
    tenant_id: str,
    dataset_version: str,
    out_path: Path,
    max_samples: int = 1500,
) -> dict:
    """Sinh file JSONL mẫu SFT nháp. Trả thống kê để đưa vào data card."""
    listing_split = split_of_listing(db, tenant_id, dataset_version)
    listings = db.scalars(
        select(CleanListing)
        .where(
            CleanListing.tenant_id == tenant_id,
            CleanListing.tier.in_(("A", "B")),
            CleanListing.is_cluster_representative.is_(True),
        )
        .order_by(CleanListing.id)
    ).all()

    facts_by_source: dict[str, list[Fact]] = defaultdict(list)
    for fact in db.scalars(select(Fact).where(Fact.tenant_id == tenant_id)).all():
        facts_by_source[fact.source_row_id].append(fact)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    stats = {
        "samples": 0,
        "by_split": defaultdict(int),
        "by_channel": defaultdict(int),
        "by_persona": defaultdict(int),
        "by_tier": defaultdict(int),
        "listings_used": 0,
        "skipped_missing_facts": 0,
        "skipped_test_split": 0,
    }

    with out_path.open("w", encoding="utf-8") as handle:
        for listing in listings:
            if stats["samples"] >= max_samples:
                break
            split = listing_split.get(listing.id)
            if split not in ("train", "validation"):
                stats["skipped_test_split"] += 1
                continue
            facts = facts_by_source.get(listing.source_row_id, [])
            if len(facts) < MIN_FACTS:
                stats["skipped_missing_facts"] += 1
                continue

            # Xoay vòng kênh × persona theo hash của tin → phân bố cân bằng và tất định
            seed = int(hashlib.sha256(listing.id.encode()).hexdigest()[:8], 16)
            channel = CHANNELS[seed % len(CHANNELS)]
            persona = PERSONAS[(seed // len(CHANNELS)) % len(PERSONAS)]
            place = listing.district or (listing.ward or "").replace("-", " ").title()
            subject = listing.project_name or listing.project_slug or listing.property_type

            sample = {
                "sample_id": _sample_id(listing.id, channel["name"], persona["segment"]),
                "dataset_version": dataset_version,
                "split": split,
                "tier": listing.tier,
                "project_id": listing.project_slug,
                "listing_id": listing.id,
                "instruction": (
                    f"Viết nội dung {channel['name']} giới thiệu "
                    f"{'căn ' + str(listing.bedrooms) + ' phòng ngủ' if listing.bedrooms else 'bất động sản'} "
                    f"tại {subject}{', ' + place if place else ''} cho nhóm khách {persona['segment']}. "
                    "Chỉ dùng dữ kiện được cung cấp, không suy đoán thông tin không có trong facts."
                ),
                "facts": [_fact_payload(f) for f in facts],
                "visual_facts": [],
                "brand": BRAND_DEMO,
                "persona": persona,
                "channel": channel,
                "seo": {"primary_keyword": None, "secondary_keywords": []},
                "output": {"headline": "", "body": "", "cta": ""},
                "claims": [],
                "quality_status": DRAFT_STATUS,
                "reviewer_id": None,
            }
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")

            stats["samples"] += 1
            stats["listings_used"] += 1
            stats["by_split"][split] += 1
            stats["by_channel"][channel["name"]] += 1
            stats["by_persona"][persona["segment"]] += 1
            stats["by_tier"][listing.tier] += 1

    stats["by_split"] = dict(stats["by_split"])
    stats["by_channel"] = dict(stats["by_channel"])
    stats["by_persona"] = dict(stats["by_persona"])
    stats["by_tier"] = dict(stats["by_tier"])
    stats["path"] = str(out_path)
    return stats
