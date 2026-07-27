"""CLI chạy pipeline làm sạch D1–D5 và xuất báo cáo chất lượng dữ liệu.

Chạy:
    python -m app.pipeline_cli                       # D1–D5 trên toàn bộ raw zone
    python -m app.pipeline_cli --limit 200           # giới hạn khi thử nghiệm
    python -m app.pipeline_cli --report ../docs/checkpoints/week_02_data_quality.md
    python -m app.pipeline_cli --report-only ...     # chỉ xuất báo cáo, không chạy lại
"""

import argparse
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Tenant, User
from app.services.data_quality import data_quality_report, render_markdown
from app.services.pipeline import reset_derived_data, run_clean_pipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--tenant-slug", default="cancu-demo")
    parser.add_argument("--report", default=None, help="Đường dẫn file Markdown xuất báo cáo")
    parser.add_argument("--report-only", action="store_true", help="Không chạy pipeline, chỉ xuất báo cáo")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Xóa dữ liệu dẫn xuất rồi dựng lại từ raw (dùng khi đổi luật parser)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == args.tenant_slug))
        if tenant is None:
            raise SystemExit(f"Không thấy tenant '{args.tenant_slug}' — chạy python -m app.seed trước")

        if args.rebuild and not args.report_only:
            print(f"Đã xóa dữ liệu dẫn xuất: {reset_derived_data(db, tenant.id)}")

        if not args.report_only:
            admin = db.scalar(select(User).where(User.tenant_id == tenant.id, User.role == "admin"))
            job = run_clean_pipeline(
                db, tenant_id=tenant.id, created_by=admin.id, limit=args.limit
            )
            print(
                f"Job {job.id}: status={job.status} read={job.total_read} "
                f"inserted={job.inserted} unchanged={job.unchanged} updated={job.updated} "
                f"quarantined={job.quarantined} errors={job.error_summary}"
            )
            print(f"  D3–D5: {job.stats}")

        report = data_quality_report(db, tenant.id)
        if args.report:
            path = Path(args.report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_markdown(report), encoding="utf-8")
            print(f"Đã ghi báo cáo chất lượng dữ liệu: {path}")
        else:
            print(
                f"Clean={report['clean']['total']} facts={report['facts']['total']} "
                f"nodes={report['graph']['entities']} edges={report['graph']['edges']}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
