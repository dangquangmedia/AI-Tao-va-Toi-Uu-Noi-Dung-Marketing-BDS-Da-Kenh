"""Xuất dataset SFT sẵn sàng train (Tuần 5, Plan/02 §7).

Đây là **đầu vào của gói training** trong `training/` — file này chạy trên máy có DB
(máy Quang), file JSONL sinh ra được copy sang máy GPU của Hải hoặc lên Colab.

## Vì sao xuất ở dạng `messages`

Prompt lúc train phải **giống hệt** prompt lúc suy luận, nếu không adapter học một định
dạng rồi bị hỏi bằng định dạng khác — hiện tượng train/serve skew. Vì vậy mỗi mẫu được
dựng bằng đúng `SYSTEM_PROMPT` và `build_user_prompt()` mà backend dùng khi sinh nội
dung, rồi ghi kèm `prompt_version` để đối chiếu.

## Hai nguồn output, đều là **văn người viết**

Nguyên tắc bất di bất dịch (đã ghi ở `services/sft_builder.py`): không train model trên
chính output của model, vì kết quả thí nghiệm sẽ mất giá trị.

- `listings` — cặp *(facts → mô tả gốc do người đăng tin viết)*. Đây là văn người thật,
  có sẵn 4.794 bản. Chỉ dùng cho kênh `description`.
- `approved` — nội dung **đã qua vòng duyệt** trong hệ thống (`content_versions` trạng
  thái approved). Đây là văn do marketer viết/biên tập và reviewer duyệt, phủ đủ 4 kênh.

## ⚠ Giới hạn đã đo được của nguồn `listings`

Mô tả trong DataBDS **bị cắt cụt từ lúc crawl**: đo trên 4.795 tin raw cho trung vị 166
ký tự, p90 = 244, chỉ 228 tin (4,8%) đạt ≥300 ký tự, và nhiều bản đứt giữa chừng câu
("...Nam Tư: 0772 011 Zalo Hỗ trợ xem nhà nhanh"). Nghĩa là crawler lấy đoạn preview chứ
không lấy thân tin đầy đủ.

Hệ quả: mẫu từ nguồn này dạy được **văn phong và cách gắn dữ kiện**, nhưng không dạy được
độ dài 180–260 từ mà `CHANNEL_SPECS["description"]` yêu cầu. Trước khi chốt cấu hình C
phải hoặc (a) Hải crawl lại trường mô tả đầy đủ, hoặc (b) nêu rõ giới hạn này trong báo
cáo và hạ kỳ vọng về độ dài. Thống kê độ dài luôn được ghi vào `sft_export_card.json` để
không ai quên.

## Bộ lọc chất lượng bằng chính claim checker

Mô tả của người đăng tin hay chứa số liệu không nằm trong facts (bịa hoặc lấy từ chỗ
khác). Train nguyên xi lên đó là **dạy model bịa số**. Nên mỗi mẫu được chấm bằng
`check_claims()` và loại nếu `unsupported_claim_rate` vượt ngưỡng (mặc định 0 — mọi con
số trong bài phải truy được về fact có nguồn). Tỷ lệ giữ lại được ghi vào thẻ dataset.

Chạy:
    python -m app.sft_cli --out ../backend/artifacts/sft
    python -m app.sft_cli --source approved --max-unsupported 0.0
"""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db import SessionLocal
from app.models import CleanListing, ContentItem, ContentVersion, Fact, Generation, Tenant
from app.services.claim_check import check_claims
from app.services.dataset import split_of_listing
from app.services.generation import _fact_line, _fact_payload
from app.services.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt

MIN_FACTS = 3
# Ngưỡng mặc định đặt theo phân bố thật của dữ liệu (p25 ≈ 148 ký tự), không đặt theo
# mong muốn — xem cảnh báo "mô tả bị cắt cụt" ở phần đầu file.
MIN_BODY_CHARS = 140
MAX_BODY_CHARS = 4000
DEFAULT_PERSONA = "young_family"


def _length_stats(lengths: list[int]) -> dict:
    if not lengths:
        return {"n": 0}
    ordered = sorted(lengths)
    return {
        "n": len(ordered),
        "min": ordered[0],
        "p50": ordered[len(ordered) // 2],
        "p90": ordered[int(len(ordered) * 0.9)],
        "max": ordered[-1],
    }


def _assistant_text(headline: str, body: str, cta: str) -> str:
    """Đầu ra mẫu — đúng định dạng ba phần mà SYSTEM_PROMPT yêu cầu."""
    return f"HEADLINE: {headline}\nBODY:\n{body}\nCTA: {cta}"


def _sample(
    *,
    sample_id: str,
    split: str,
    source: str,
    channel: str,
    persona: str,
    brief: str,
    context_block: str,
    headline: str,
    body: str,
    cta: str,
    project_slug: str | None,
    fact_ids: list[str],
    rate: float,
) -> dict:
    user = build_user_prompt(
        channel=channel, persona=persona, brief=brief, context_block=context_block or None
    )
    return {
        "sample_id": sample_id,
        "split": split,
        "source": source,
        "dataset_version": settings.dataset_version,
        "prompt_version": PROMPT_VERSION,
        "channel": channel,
        "persona": persona,
        "project_slug": project_slug,
        "fact_ids": fact_ids,
        "unsupported_claim_rate": rate,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": _assistant_text(headline, body, cta)},
        ],
    }


def from_listings(
    db,
    tenant_id: str,
    dataset_version: str,
    max_unsupported: float,
    limit: int | None,
    min_chars: int = MIN_BODY_CHARS,
) -> tuple[list[dict], dict]:
    """Cặp (facts → mô tả gốc của người đăng tin), đã lọc bằng claim check.

    Trả (mẫu, thống kê loại bỏ) — thống kê đi vào thẻ dataset để giải thích được vì sao
    từ 4.794 tin chỉ còn ngần này mẫu.
    """
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

    stats: Counter = Counter()
    samples: list[dict] = []
    for listing in listings:
        if limit and stats["kept"] >= limit:
            break
        split = listing_split.get(listing.id)
        if split not in ("train", "validation"):
            stats["bo_split_test"] += 1
            continue
        body = (listing.description_clean or "").strip()
        if not (min_chars <= len(body) <= MAX_BODY_CHARS):
            stats["bo_do_dai"] += 1
            continue
        facts = facts_by_source.get(listing.source_row_id, [])
        if len(facts) < MIN_FACTS:
            stats["bo_thieu_fact"] += 1
            continue

        headline = (listing.title_clean or "").strip()
        cta = "Liên hệ để được tư vấn và xem thực tế."
        checked = check_claims(f"{headline}\n{body}\n{cta}", [_fact_payload(f) for f in facts])
        if checked["unsupported_claim_rate"] > max_unsupported or checked["n_forbidden"]:
            stats["bo_claim_vo_can_cu"] += 1
            continue

        place = listing.district or (listing.ward or "").replace("-", " ").title()
        subject = listing.project_name or listing.project_slug or listing.property_type
        stats["kept"] += 1
        samples.append(
            _sample(
                sample_id=f"ls-{listing.id}",
                split=split,
                source="listings",
                channel="description",
                persona=DEFAULT_PERSONA,
                brief=f"Giới thiệu {subject}{', ' + place if place else ''}",
                context_block="\n".join(_fact_line(f) for f in facts),
                headline=headline,
                body=body,
                cta=cta,
                project_slug=listing.project_slug,
                fact_ids=[f.id for f in facts],
                rate=checked["unsupported_claim_rate"],
            )
        )
    return samples, dict(stats)


def from_approved(
    db, tenant_id: str, dataset_version: str, max_unsupported: float
) -> tuple[list[dict], dict]:
    """Nội dung đã qua vòng duyệt — văn của marketer, reviewer đã chấp nhận."""
    rows = db.execute(
        select(ContentVersion, ContentItem)
        .join(ContentItem, ContentItem.id == ContentVersion.content_item_id)
        .where(
            ContentVersion.tenant_id == tenant_id,
            ContentVersion.status == "approved",
        )
        .order_by(ContentVersion.created_at)
    ).all()

    stats: Counter = Counter()
    samples: list[dict] = []
    for version, item in rows:
        rate = float(version.metrics.get("unsupported_claim_rate", 0.0))
        if rate > max_unsupported:
            stats["bo_claim_vo_can_cu"] += 1
            continue
        generation = db.get(Generation, version.generation_id) if version.generation_id else None
        fact_ids = list((generation.metrics.get("reference_fact_ids") if generation else None) or [])
        facts = (
            db.scalars(select(Fact).where(Fact.tenant_id == tenant_id, Fact.id.in_(fact_ids))).all()
            if fact_ids
            else []
        )
        stats["kept"] += 1
        # Nội dung đã duyệt là mẫu quý (người duyệt bỏ công), luôn cho vào train
        samples.append(
            _sample(
                sample_id=f"cv-{version.id}",
                split="train",
                source="approved",
                channel=item.channel,
                persona=item.persona,
                brief=(generation.brief if generation else item.title),
                context_block="\n".join(_fact_line(f) for f in facts),
                headline=version.headline,
                body=version.body,
                cta=version.cta,
                project_slug=item.project_slug,
                fact_ids=fact_ids,
                rate=rate,
            )
        )
    return samples, dict(stats)


def write_split(samples: list[dict], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {"train": 0, "validation": 0}
    handles = {
        name: (out_dir / f"{name}.jsonl").open("w", encoding="utf-8") for name in counts
    }
    try:
        for sample in samples:
            split = sample["split"] if sample["split"] in counts else "train"
            handles[split].write(json.dumps(sample, ensure_ascii=False) + "\n")
            counts[split] += 1
    finally:
        for handle in handles.values():
            handle.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-slug", default="cancu-demo")
    parser.add_argument("--version", default=settings.dataset_version)
    parser.add_argument("--source", default="both", choices=("listings", "approved", "both"))
    parser.add_argument(
        "--max-unsupported",
        type=float,
        default=0.0,
        help="ngưỡng tỷ lệ claim không có căn cứ được phép giữ lại (0 = khắt khe nhất)",
    )
    parser.add_argument("--limit", type=int, default=None, help="giới hạn số mẫu từ listings")
    parser.add_argument(
        "--min-chars",
        type=int,
        default=MIN_BODY_CHARS,
        help="độ dài tối thiểu của mô tả gốc (mặc định bám phân bố thật của dữ liệu)",
    )
    parser.add_argument("--out", default=str(Path(settings.artifacts_dir) / "sft"))
    args = parser.parse_args()

    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == args.tenant_slug))
        if tenant is None:
            raise SystemExit(f"Không tìm thấy tenant '{args.tenant_slug}'")

        samples: list[dict] = []
        stats: dict[str, dict] = {}
        if args.source in ("listings", "both"):
            rows, stats["listings"] = from_listings(
                db, tenant.id, args.version, args.max_unsupported, args.limit, args.min_chars
            )
            samples += rows
        if args.source in ("approved", "both"):
            rows, stats["approved"] = from_approved(
                db, tenant.id, args.version, args.max_unsupported
            )
            samples += rows

        out_dir = Path(args.out)
        counts = write_split(samples, out_dir)
        card = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset_version": args.version,
            "prompt_version": PROMPT_VERSION,
            "source": args.source,
            "max_unsupported_claim_rate": args.max_unsupported,
            "counts": counts,
            "by_source": dict(Counter(s["source"] for s in samples)),
            "by_channel": dict(Counter(s["channel"] for s in samples)),
            "by_persona": dict(Counter(s["persona"] for s in samples)),
            "projects": len({s["project_slug"] for s in samples if s["project_slug"]}),
            "filters": stats,
            # Độ dài đầu ra mẫu — số này phải nằm trong thẻ dataset vì nó quyết định
            # model học viết dài hay ngắn (xem cảnh báo mô tả bị cắt cụt ở đầu file).
            "output_chars": _length_stats(
                [len(s["messages"][-1]["content"]) for s in samples]
            ),
            "min_chars_filter": args.min_chars,
        }
        (out_dir / "sft_export_card.json").write_text(
            json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        print(f"Đã ghi {counts['train']} mẫu train · {counts['validation']} mẫu validation → {out_dir}")
        for source, detail in stats.items():
            print(f"  {source}: {detail}")
        if counts["train"] < 50:
            print(
                "\nCẢNH BÁO: quá ít mẫu để QLoRA có ý nghĩa (Plan/02 §7 đặt mục tiêu 800–1.500).\n"
                "  - Nới `--max-unsupported` (ví dụ 0.1) nếu bộ lọc claim quá chặt;\n"
                "  - Hoặc duyệt thêm nội dung trong UI /review để có mẫu nguồn `approved`."
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
