"""Chạy baseline A/B trên bộ brief cố định và xuất bảng so sánh (Tuần 4).

Brief lấy tất định từ **dự án thuộc split test** của `dataset_v1` (không dùng dự án
train/validation) và xoay vòng 4 kênh × 3 persona. Cùng model, cùng seed, cùng decoding;
A và B chỉ khác khối dữ kiện truy xuất — đúng điều kiện so sánh của Plan/03 §2.

Chạy:
    python -m app.ab_cli --briefs 6 --out ../docs/checkpoints/week_04_ab_baseline.md
    python -m app.ab_cli --provider template     # thử nhanh, không cần GPU
"""

import argparse
import statistics
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.core.config import settings
from app.db import SessionLocal
from app.models import Tenant, User
from app.services.experiments import PERSONAS, pick_briefs  # noqa: F401 — giữ tên cũ cho script ngoài
from app.services.generation import run_generation


def summarize(records: list) -> dict:
    """Tổng hợp chỉ số của một cấu hình."""
    ok = [r for r in records if r.status == "done"]
    if not ok:
        return {"n": 0}
    rates = [r.metrics.get("unsupported_claim_rate", 0.0) for r in ok]
    claims = [r.metrics.get("n_claims", 0) for r in ok]
    forbidden = [r.metrics.get("n_forbidden", 0) for r in ok]
    lengths = [len(r.body or "") for r in ok]
    latency = [r.latency_ms for r in ok]
    return {
        "n": len(ok),
        "unsupported_claim_rate": round(statistics.mean(rates), 4),
        "claims_per_output": round(statistics.mean(claims), 2),
        "forbidden_total": sum(forbidden),
        "body_chars": int(statistics.mean(lengths)),
        "latency_s": round(statistics.mean(latency) / 1000, 1),
        "outputs_with_unsupported": sum(1 for r in rates if r > 0),
    }


def render_markdown(summary: dict, samples: list[dict], model_name: str, provider: str) -> str:
    now = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")
    lines = [
        "# Baseline A vs B — sinh nội dung có/không RAG",
        "",
        f"> Sinh tự động bằng `python -m app.ab_cli` lúc {now}. Model `{model_name}` "
        f"(provider `{provider}`), greedy decoding, cùng seed, cùng prompt version. "
        "Brief lấy từ dự án thuộc split test của `dataset_v1`.",
        "",
        "## Tổng hợp",
        "",
        "| Chỉ số | A (prompt-only) | B (RAG) |",
        "|---|---:|---:|",
    ]
    a, b = summary.get("A", {}), summary.get("B", {})
    rows = [
        ("Số bài", "n"),
        ("Tỷ lệ claim không có căn cứ", "unsupported_claim_rate"),
        ("Số claim trung bình mỗi bài", "claims_per_output"),
        ("Bài có ít nhất 1 claim vô căn cứ", "outputs_with_unsupported"),
        ("Câu chứa từ cấm", "forbidden_total"),
        ("Độ dài thân bài (ký tự)", "body_chars"),
        ("Thời gian sinh trung bình (giây)", "latency_s"),
    ]
    for label, key in rows:
        lines.append(f"| {label} | {a.get(key, '—')} | {b.get(key, '—')} |")

    lines += ["", "## Từng brief", "", "| Dự án | Kênh | Persona | A: claim vô căn cứ | B: claim vô căn cứ | B: số fact |", "|---|---|---|---:|---:|---:|"]
    for sample in samples:
        lines.append(
            f"| {sample['project_slug']} | {sample['channel']} | {sample['persona']} | "
            f"{sample['a_rate']} | {sample['b_rate']} | {sample['b_facts']} |"
        )

    lines += [
        "",
        "## Cách đọc",
        "",
        "- `claim` = câu có chứa số liệu hoặc thuộc tính (giá, diện tích, phòng ngủ, pháp lý…).",
        "- Một claim được coi là **có căn cứ** khi mọi con số trong câu đều xuất hiện trong "
        "facts đã truy xuất cho brief đó. Cả A và B đều chấm trên cùng tập fact tham chiếu — "
        "A không nhìn thấy facts, nhưng thước đo phải như nhau thì so sánh mới công bằng.",
        "- Đây là chỉ số tự động (rule-based). Human evaluation mù theo Plan/03 §5 làm ở Tuần 6.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-slug", default="cancu-demo")
    parser.add_argument("--version", default=settings.dataset_version)
    parser.add_argument("--briefs", type=int, default=6)
    parser.add_argument("--retrieval", default="R3")
    parser.add_argument("--provider", default=None, help="ghi đè llm_provider (local/template/openai)")
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument("--k", type=int, default=6, help="số chunk/fact đưa vào context của B")
    parser.add_argument(
        "--fp16",
        action="store_true",
        help="tắt lượng tử 4-bit — model nhỏ vừa VRAM thì fp16 nhanh hơn hẳn trên GPU cũ",
    )
    parser.add_argument("--out", default="../docs/checkpoints/week_04_ab_baseline.md")
    args = parser.parse_args()

    if args.provider:
        settings.llm_provider = args.provider
    if args.model:
        settings.llm_model = args.model
    if args.max_new_tokens:
        settings.llm_max_new_tokens = args.max_new_tokens
    if args.fp16:
        settings.llm_load_in_4bit = False

    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == args.tenant_slug))
        admin = db.scalar(select(User).where(User.tenant_id == tenant.id, User.role == "admin"))
        briefs = pick_briefs(db, tenant.id, args.version, args.briefs)
        print(f"Chạy {len(briefs)} brief × 2 cấu hình (A, B) — model {settings.llm_model}", flush=True)

        records: dict[str, list] = {"A": [], "B": []}
        samples = []
        for i, brief in enumerate(briefs, start=1):
            row = {"project_slug": brief["project_slug"], "channel": brief["channel"], "persona": brief["persona"]}
            for config in ("A", "B"):
                result = run_generation(
                    db,
                    tenant_id=tenant.id,
                    created_by=admin.id,
                    brief=brief["brief"],
                    channel=brief["channel"],
                    persona=brief["persona"],
                    config=config,
                    retrieval_config=args.retrieval,
                    project_slug=brief["project_slug"],
                    k=args.k,
                )
                records[config].append(result)
                rate = result.metrics.get("unsupported_claim_rate", "—")
                row[f"{config.lower()}_rate"] = rate
                if config == "B":
                    row["b_facts"] = result.metrics.get("n_context_facts", 0)
                print(
                    f"  [{i}/{len(briefs)}] {config} {brief['channel']:<12} "
                    f"claim_vo_can_cu={rate} latency={result.latency_ms / 1000:.0f}s status={result.status}",
                    flush=True,  # ghi ra ngay để theo dõi được batch dài
                )
            samples.append(row)

        summary = {config: summarize(rows) for config, rows in records.items()}
        first = records["B"][0] if records["B"] else None
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            render_markdown(
                summary,
                samples,
                first.model_name if first else settings.llm_model,
                first.provider if first else settings.llm_provider,
            ),
            encoding="utf-8",
        )
        print(f"A: {summary['A']}")
        print(f"B: {summary['B']}")
        print(f"Báo cáo: {out}")

        total = db.scalar(select(func.count()).select_from(type(records['A'][0])))
        print(f"Tổng số bản ghi generations trong DB: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
