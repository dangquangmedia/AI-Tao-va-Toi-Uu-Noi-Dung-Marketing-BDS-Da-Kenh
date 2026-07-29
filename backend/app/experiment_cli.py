"""Chạy thí nghiệm đóng băng A–D (+ R1–R3) trên frozen test set — gate Tuần 6.

Khác `ab_cli` (Tuần 4, chỉ A/B, chỉ in bảng): lượt chạy ở đây được **ghi vào DB kèm
snapshot** — commit git, model, prompt version, adapter fingerprint, kích thước split —
nên bảng số trong báo cáo truy được về đúng điều kiện đã chạy. Thiếu adapter thì C/D bị
bỏ qua **có ghi lý do**, A/B vẫn ra số.

Chạy:
    python -m app.experiment_cli --briefs 12 --configs A,B,C,D --with-retrieval
    python -m app.experiment_cli --provider template --briefs 4   # thử nhanh, không GPU
    python -m app.experiment_cli --list                            # xem các lượt đã chạy
"""

import argparse
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db import SessionLocal
from app.models import ExperimentRun, Tenant, User
from app.services.experiments import pick_briefs, render_markdown, run_experiment
from app.services.retrieval_eval import evaluate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-slug", default="cancu-demo")
    parser.add_argument("--version", default=settings.dataset_version)
    parser.add_argument("--briefs", type=int, default=12)
    parser.add_argument("--configs", default="A,B,C,D")
    parser.add_argument("--retrieval", default="R3")
    parser.add_argument("--adapter", default=None, help="tên thư mục adapter cho C/D")
    parser.add_argument("--k", type=int, default=6, help="số chunk/fact đưa vào context")
    parser.add_argument("--provider", default=None, help="ghi đè llm_provider")
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument("--fp16", action="store_true", help="tắt lượng tử 4-bit")
    parser.add_argument("--run-key", default=None)
    parser.add_argument("--label", default="Frozen test A–D (Tuần 6)")
    parser.add_argument("--with-retrieval", action="store_true", help="chấm luôn R1–R3 vào cùng báo cáo")
    parser.add_argument("--eval-k", type=int, default=10)
    parser.add_argument("--list", action="store_true", help="chỉ liệt kê các lượt đã chạy")
    parser.add_argument("--out", default="../docs/checkpoints/week_06_experiment.md")
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
        if tenant is None:
            raise SystemExit(f"Không thấy tenant '{args.tenant_slug}' — chạy python -m app.seed trước")

        if args.list:
            runs = db.scalars(
                select(ExperimentRun)
                .where(ExperimentRun.tenant_id == tenant.id)
                .order_by(ExperimentRun.started_at.desc())
            ).all()
            for run in runs:
                by_config = (run.summary or {}).get("by_config", {})
                rates = " · ".join(
                    f"{c}={v.get('unsupported_claim_rate', '—')}" for c, v in by_config.items()
                )
                print(
                    f"{run.run_key:<24} {run.status:<8} {run.n_briefs:>3} brief  "
                    f"{','.join(run.configs):<8} {rates}"
                )
            if not runs:
                print("Chưa có lượt chạy nào.")
            return

        admin = db.scalar(select(User).where(User.tenant_id == tenant.id, User.role == "admin"))
        briefs = pick_briefs(db, tenant.id, args.version, args.briefs)
        if not briefs:
            raise SystemExit("Không lấy được brief nào — kiểm tra split test của dataset")
        configs = tuple(c.strip().upper() for c in args.configs.split(",") if c.strip())

        def progress(i, total, config, record):
            print(
                f"  [{i}/{total}] {config} {record.channel:<12} "
                f"claim_vo_can_cu={record.metrics.get('unsupported_claim_rate', '—')} "
                f"latency={record.latency_ms / 1000:.0f}s status={record.status}",
                flush=True,
            )

        print(
            f"Chạy {len(briefs)} brief × {len(configs)} cấu hình yêu cầu ({','.join(configs)}) "
            f"— model {settings.llm_model}",
            flush=True,
        )
        run = run_experiment(
            db,
            tenant_id=tenant.id,
            created_by=admin.id,
            briefs=briefs,
            dataset_version=args.version,
            configs=configs,
            retrieval_config=args.retrieval,
            k=args.k,
            adapter_name=args.adapter,
            run_key=args.run_key,
            label=args.label,
            progress=progress,
        )
        if run.skipped:
            for config, reason in run.skipped.items():
                print(f"  bỏ qua {config}: {reason}")

        retrieval_report = None
        if args.with_retrieval:
            print("Chấm retrieval R1–R3 trên gold query…", flush=True)
            retrieval_report = evaluate(db, tenant.id, args.version, k=args.eval_k)

        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_markdown(run, retrieval_report), encoding="utf-8")

        for config, data in (run.summary or {}).get("by_config", {}).items():
            print(f"{config}: {data}")
        print(f"Run `{run.run_key}` ({run.status}) — báo cáo: {out}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
