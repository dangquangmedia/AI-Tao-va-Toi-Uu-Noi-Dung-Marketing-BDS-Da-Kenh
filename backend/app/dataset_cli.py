"""CLI đóng băng dataset và đánh giá retrieval (Tuần 3).

Chạy:
    python -m app.dataset_cli --build          # split + leakage audit + gold queries + SFT draft + data card
    python -m app.dataset_cli --eval           # chấm R1/R2 trên gold query, xuất bảng kết quả
    python -m app.dataset_cli --build --eval --version dataset_v1
"""

import argparse
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db import SessionLocal
from app.models import Tenant
from app.services import data_card
from app.services.dataset import build_dataset_split, leakage_audit
from app.services.gold_queries import generate_gold_queries
from app.services.retrieval import retrieval_stats
from app.services.retrieval_eval import evaluate, render_markdown
from app.services.sft_builder import build_sft_draft


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-slug", default="cancu-demo")
    parser.add_argument("--version", default=settings.dataset_version)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--eval", action="store_true")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--backend", default=None, help="ghi đè embedding_backend khi đánh giá")
    parser.add_argument("--card", default="../docs/checkpoints/week_03_data_card.md")
    parser.add_argument("--eval-out", default="../docs/checkpoints/week_03_retrieval_eval.md")
    parser.add_argument("--sft-out", default=None)
    args = parser.parse_args()

    if args.backend:
        settings.embedding_backend = args.backend
    if not args.build and not args.eval:
        args.build = True

    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == args.tenant_slug))
        if tenant is None:
            raise SystemExit(f"Không thấy tenant '{args.tenant_slug}' — chạy python -m app.seed trước")

        if args.build:
            summary = build_dataset_split(db, tenant.id, args.version)
            print(f"Split {args.version}: {summary}")

            audit = leakage_audit(db, tenant.id, args.version)
            print(
                f"Leakage audit: passed={audit['passed']} "
                f"cum_ro_ri={len(audit['leaking_clusters'])} du_an_ro_ri={len(audit['leaking_projects'])} "
                f"tin_chua_gan={audit['listings_unassigned']}"
            )

            gold = generate_gold_queries(db, tenant.id, args.version)
            print(f"Gold queries: {gold}")

            sft_path = Path(args.sft_out or Path(settings.artifacts_dir) / f"sft_draft_{args.version}.jsonl")
            sft_stats = build_sft_draft(db, tenant.id, args.version, sft_path)
            print(f"SFT draft: {sft_stats['samples']} mẫu → {sft_stats['path']}")

            card = data_card.collect(db, tenant.id, args.version, sft_stats)
            card_path = Path(args.card)
            card_path.parent.mkdir(parents=True, exist_ok=True)
            card_path.write_text(data_card.render_markdown(card), encoding="utf-8")
            print(f"Data card: {card_path}")

        if args.eval:
            stats = retrieval_stats(db, tenant.id)
            print(f"Knowledge base: {stats}")
            report = evaluate(db, tenant.id, args.version, k=args.k)
            out = Path(args.eval_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                render_markdown(report, stats["embedding_model"] or settings.embedding_model, args.version),
                encoding="utf-8",
            )
            for config, data in report.get("configs", {}).items():
                o = data["overall"]
                print(
                    f"  {config:<12} precision={o['project_precision']:.3f} "
                    f"recall={o['listing_recall']:.3f} hit={o['hit']:.3f} mrr={o['mrr']:.3f}"
                )
            print(f"Báo cáo đánh giá: {out}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
