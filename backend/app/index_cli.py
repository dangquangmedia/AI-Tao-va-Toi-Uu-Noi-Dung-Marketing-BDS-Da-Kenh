"""CLI dựng knowledge base cho retrieval (chunk + FTS + embedding).

Chạy:
    python -m app.index_cli                          # tier A+B, embed bằng model trong cấu hình
    python -m app.index_cli --backend hashing        # nhanh, không cần model (chỉ để thử pipeline)
    python -m app.index_cli --no-embed               # chỉ chunk + FTS
    python -m app.index_cli --tiers A                # giới hạn tier
"""

import argparse
import time

from sqlalchemy import select

from app.core.config import settings
from app.db import SessionLocal
from app.models import Tenant, User
from app.services.indexing import DEFAULT_TIERS, run_index_build
from app.services.retrieval import retrieval_stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-slug", default="cancu-demo")
    parser.add_argument("--tiers", default=",".join(DEFAULT_TIERS))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--backend", default=None, help="ghi đè embedding_backend (hashing/sentence-transformers)")
    parser.add_argument("--model", default=None, help="ghi đè embedding_model")
    parser.add_argument("--no-embed", action="store_true")
    args = parser.parse_args()

    if args.backend:
        settings.embedding_backend = args.backend
    if args.model:
        settings.embedding_model = args.model

    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == args.tenant_slug))
        if tenant is None:
            raise SystemExit(f"Không thấy tenant '{args.tenant_slug}' — chạy python -m app.seed trước")
        admin = db.scalar(select(User).where(User.tenant_id == tenant.id, User.role == "admin"))

        started = time.time()
        job = run_index_build(
            db,
            tenant_id=tenant.id,
            created_by=admin.id,
            tiers=tuple(t.strip() for t in args.tiers.split(",") if t.strip()),
            limit=args.limit,
            embed=not args.no_embed,
        )
        print(
            f"Job {job.id}: status={job.status} listings={job.total_read} "
            f"chunk_moi={job.inserted} giu_nguyen={job.unchanged} cap_nhat={job.updated}"
        )
        print(f"  stats={job.stats}")
        print(f"  knowledge base={retrieval_stats(db, tenant.id)}")
        print(f"  thoi gian: {time.time() - started:.1f}s")
    finally:
        db.close()


if __name__ == "__main__":
    main()
