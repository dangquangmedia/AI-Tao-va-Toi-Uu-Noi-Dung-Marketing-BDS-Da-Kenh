"""Pipeline dựng knowledge base cho retrieval: chunk → FTS → embedding (Tuần 3).

Idempotent theo đúng nguyên tắc của D1–D5:
- Chunk khóa theo (tenant, clean_listing, loại chunk, thứ tự); `content_hash` của text
  quyết định có phải ghi lại và embed lại hay không.
- Chunk không còn được sinh ra (tin bị sửa, mô tả ngắn lại) thì bị xóa.
- Chỉ embed chunk thiếu vector hoặc đang gắn model khác → đổi model chỉ embed lại,
  không phải dựng lại toàn bộ.
"""

from datetime import datetime, timezone

from sqlalchemy import delete, func, select, text as sql_text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Chunk, CleanListing, Fact, IngestionJob, LexicalPosting
from app.services.chunking import build_chunks
from app.services.embeddings import get_embedder
from app.services.lexical import rebuild_postings

JOB_TYPE = "index_build"
DEFAULT_TIERS = ("A", "B")
EMBED_BATCH = 64


def _postgres(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def refresh_search_vectors(db: Session, tenant_id: str) -> int:
    """Cập nhật cột FTS (PostgreSQL). Bỏ dấu tiếng Việt bằng `unaccent`, cấu hình `simple`."""
    if not _postgres(db):
        # SQLite (test): giữ bản không dấu để tìm kiếm bằng LIKE
        rows = db.scalars(
            select(Chunk).where(Chunk.tenant_id == tenant_id, Chunk.search_vector.is_(None))
        ).all()
        from app.services.reparse import deaccent

        for row in rows:
            row.search_vector = deaccent(row.text)
        return len(rows)

    result = db.execute(
        sql_text(
            "UPDATE chunks SET search_vector = to_tsvector('simple', unaccent(text)) "
            "WHERE tenant_id = :tenant AND search_vector IS NULL"
        ),
        {"tenant": tenant_id},
    )
    return result.rowcount


def run_index_build(
    db: Session,
    tenant_id: str,
    created_by: str,
    tiers: tuple[str, ...] = DEFAULT_TIERS,
    limit: int | None = None,
    embed: bool = True,
) -> IngestionJob:
    job = IngestionJob(
        tenant_id=tenant_id, created_by=created_by, status="running", job_type=JOB_TYPE
    )
    db.add(job)
    db.flush()

    query = (
        select(CleanListing)
        .where(CleanListing.tenant_id == tenant_id, CleanListing.tier.in_(tiers))
        .order_by(CleanListing.id)
    )
    if limit is not None:
        query = query.limit(limit)
    listings = db.scalars(query).all()
    listing_ids = [row.id for row in listings]

    facts_by_source: dict[str, list[Fact]] = {}
    if listing_ids:
        source_ids = [row.source_row_id for row in listings]
        for fact in db.scalars(
            select(Fact).where(Fact.tenant_id == tenant_id, Fact.source_row_id.in_(source_ids))
        ).all():
            facts_by_source.setdefault(fact.source_row_id, []).append(fact)

    existing = {}
    if listing_ids:
        for chunk in db.scalars(
            select(Chunk).where(
                Chunk.tenant_id == tenant_id, Chunk.clean_listing_id.in_(listing_ids)
            )
        ).all():
            existing[(chunk.clean_listing_id, chunk.chunk_type, chunk.seq)] = chunk

    wanted: set[tuple[str, str, int]] = set()
    touched: list[Chunk] = []  # chunk mới/đổi text → phải dựng lại posting BM25
    for listing in listings:
        job.total_read += 1
        for spec in build_chunks(listing, facts_by_source.get(listing.source_row_id, [])):
            key = (listing.id, spec["chunk_type"], spec["seq"])
            wanted.add(key)
            chunk = existing.get(key)
            if chunk is None:
                chunk = Chunk(
                    tenant_id=tenant_id,
                    clean_listing_id=listing.id,
                    source_row_id=listing.source_row_id,
                    source_listing_id="",
                    source_url="",
                    project_slug=listing.project_slug,
                    tier=listing.tier,
                    **spec,
                )
                db.add(chunk)
                touched.append(chunk)
                job.inserted += 1
            elif chunk.content_hash == spec["content_hash"]:
                chunk.project_slug = listing.project_slug
                chunk.tier = listing.tier
                job.unchanged += 1
            else:
                chunk.text = spec["text"]
                chunk.content_hash = spec["content_hash"]
                chunk.token_count = spec["token_count"]
                chunk.project_slug = listing.project_slug
                chunk.tier = listing.tier
                chunk.embedding = None  # text đổi → phải embed lại
                chunk.search_vector = None
                touched.append(chunk)
                job.updated += 1

    stale = [chunk.id for key, chunk in existing.items() if key not in wanted]
    if stale:
        db.execute(delete(Chunk).where(Chunk.id.in_(stale)))
    db.flush()

    # Provenance của chunk lấy từ tin nguồn (một câu UPDATE, không lặp Python)
    db.execute(
        sql_text(
            "UPDATE chunks SET source_listing_id = s.source_listing_id, source_url = s.canonical_url "
            "FROM source_listings s WHERE chunks.source_row_id = s.id AND chunks.tenant_id = :tenant "
            "AND (chunks.source_url = '' OR chunks.source_url IS NULL)"
        )
        if _postgres(db)
        else sql_text(
            "UPDATE chunks SET source_listing_id = (SELECT source_listing_id FROM source_listings s "
            "WHERE s.id = chunks.source_row_id), source_url = (SELECT canonical_url FROM source_listings s "
            "WHERE s.id = chunks.source_row_id) WHERE tenant_id = :tenant AND (source_url = '' OR source_url IS NULL)"
        ),
        {"tenant": tenant_id},
    )

    indexed = refresh_search_vectors(db, tenant_id)

    # Chỉ mục ngược BM25: dựng lại cho chunk vừa đổi; nếu tenant chưa có posting nào
    # (lần đầu chạy sau khi thêm BM25) thì dựng cho toàn bộ.
    has_postings = db.scalar(
        select(LexicalPosting.id).where(LexicalPosting.tenant_id == tenant_id).limit(1)
    )
    postings = rebuild_postings(
        db, tenant_id, [c.id for c in touched] if has_postings else None
    )

    embedded = 0
    model_name = ""
    if embed:
        embedder = get_embedder()
        model_name = embedder.name
        todo = db.scalars(
            select(Chunk)
            .where(
                Chunk.tenant_id == tenant_id,
                (Chunk.embedding.is_(None)) | (Chunk.embedding_model != model_name),
            )
            .order_by(Chunk.id)
        ).all()
        for start in range(0, len(todo), EMBED_BATCH):
            batch = todo[start : start + EMBED_BATCH]
            vectors = embedder.encode([chunk.text for chunk in batch])
            for chunk, vector in zip(batch, vectors):
                chunk.embedding = vector
                chunk.embedding_model = model_name
            embedded += len(batch)
            db.flush()

    total_chunks = db.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.tenant_id == tenant_id)
    )
    job.stats = {
        "chunks_total": total_chunks,
        "chunks_deleted": len(stale),
        "search_vectors_indexed": indexed,
        "bm25_postings_written": postings,
        "embedded": embedded,
        "embedding_model": model_name,
        "embedding_backend": settings.embedding_backend,
        "tiers": list(tiers),
    }
    job.status = "done"
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job
