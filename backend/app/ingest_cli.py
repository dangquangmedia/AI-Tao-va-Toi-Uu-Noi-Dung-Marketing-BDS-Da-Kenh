"""CLI import DataBDS vào raw zone.

Chạy: python -m app.ingest_cli --limit 200   (bỏ --limit để import toàn bộ)
"""

import argparse

from sqlalchemy import select

from app.core.config import settings
from app.db import SessionLocal
from app.models import Tenant, User
from app.services.ingestion import run_databds_import


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--tenant-slug", default="cancu-demo")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == args.tenant_slug))
        if tenant is None:
            raise SystemExit(f"Không thấy tenant '{args.tenant_slug}' — chạy python -m app.seed trước")
        admin = db.scalar(
            select(User).where(User.tenant_id == tenant.id, User.role == "admin")
        )
        job = run_databds_import(
            db,
            tenant_id=tenant.id,
            created_by=admin.id,
            databds_dir=settings.databds_dir,
            limit=args.limit,
        )
        print(
            f"Job {job.id}: status={job.status} read={job.total_read} "
            f"inserted={job.inserted} unchanged={job.unchanged} "
            f"updated={job.updated} quarantined={job.quarantined} errors={job.error_summary}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
