"""Test index build và truy xuất R1/R2 (Tuần 3).

Chạy trên SQLite với embedder băm: kiểm chứng *luồng* và *hợp đồng dữ liệu* của
retrieval (idempotent, lọc theo tenant, trả nguồn, RRF, path của graph).
Chất lượng ngữ nghĩa được đo riêng bằng model thật qua `app.dataset_cli --eval`.
"""

from sqlalchemy import func, select

from app.models import Chunk
from app.services.embeddings import get_embedder
from app.services.indexing import run_index_build
from app.services.pipeline import run_clean_pipeline
from app.services.retrieval import (
    reciprocal_rank_fusion,
    retrieval_stats,
    retrieve_r1,
    retrieve_r2,
    search_fts,
    search_vector,
)
from tests.test_pipeline import databds, imported  # noqa: F401 — fixture dùng lại


def _indexed(db, imported):
    run_clean_pipeline(db, **imported)
    return run_index_build(db, tenant_id=imported["tenant_id"], created_by=imported["created_by"])


def test_index_build_sinh_chunk_va_provenance(db, imported):  # noqa: F811
    job = _indexed(db, imported)

    assert job.job_type == "index_build"
    assert job.inserted > 0
    chunks = db.scalars(select(Chunk)).all()
    assert {c.chunk_type for c in chunks} == {"facts", "title", "description"}
    for chunk in chunks:
        assert chunk.source_url.startswith("https://batdongsan.com.vn/")
        assert chunk.source_listing_id
        assert chunk.embedding is not None
        assert chunk.search_vector  # bản không dấu để tìm theo từ khóa
    assert job.stats["embedded"] == len(chunks)


def test_index_build_idempotent(db, imported):  # noqa: F811
    _indexed(db, imported)
    total = db.scalar(select(func.count()).select_from(Chunk))
    embedder_calls = db.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.embedding.is_not(None))
    )

    job2 = run_index_build(db, tenant_id=imported["tenant_id"], created_by=imported["created_by"])

    assert job2.inserted == 0
    assert job2.updated == 0
    assert job2.unchanged == total
    assert job2.stats["embedded"] == 0  # không embed lại chunk không đổi
    assert db.scalar(select(func.count()).select_from(Chunk)) == total
    assert embedder_calls == total


def test_doi_model_thi_embed_lai(db, imported):  # noqa: F811
    _indexed(db, imported)
    for chunk in db.scalars(select(Chunk)).all():
        chunk.embedding_model = "model-cu"
    db.flush()

    job = run_index_build(db, tenant_id=imported["tenant_id"], created_by=imported["created_by"])

    assert job.stats["embedded"] == db.scalar(select(func.count()).select_from(Chunk))
    assert job.stats["embedding_model"] == get_embedder().name


def test_r1_tra_ket_qua_kem_nguon(db, imported):  # noqa: F811
    _indexed(db, imported)
    tenant = imported["tenant_id"]

    fts = search_fts(db, tenant, "căn hộ Grand View sổ hồng", 5)
    vector = search_vector(db, tenant, "căn hộ hai phòng ngủ view sông", 5)
    hybrid = retrieve_r1(db, tenant, "căn hộ Grand View", 5)

    assert fts and vector and hybrid
    for item in fts + vector + hybrid:
        assert item["source_url"]
        assert item["text"]
    assert [item["rank"] for item in hybrid] == list(range(1, len(hybrid) + 1))


def test_rrf_gop_hai_danh_sach():
    a = [{"chunk_id": "x", "rank": 1, "retriever": "fts", "score": 1.0}]
    b = [
        {"chunk_id": "y", "rank": 1, "retriever": "vector", "score": 1.0},
        {"chunk_id": "x", "rank": 2, "retriever": "vector", "score": 0.5},
    ]
    fused = reciprocal_rank_fusion([a, b], k=5)

    assert fused[0]["chunk_id"] == "x"  # xuất hiện ở cả hai retriever
    assert fused[0]["retriever"] == "fts+vector"
    assert fused[0]["score"] > fused[1]["score"]


def test_r2_chi_dung_graph_va_giai_thich_duong_di(db, imported):  # noqa: F811
    _indexed(db, imported)
    results = retrieve_r2(db, imported["tenant_id"], "Dự án Grand View có gì?", 5)

    assert results
    assert all(item["project_slug"] == "grand-view" for item in results)
    assert all(item["retriever"] == "graph" and item["path"] for item in results)
    assert all(item["source_url"] for item in results)
    # Câu hỏi không có thực thể nào trong graph → graph-only không trả bừa
    assert retrieve_r2(db, imported["tenant_id"], "thời tiết hôm nay thế nào", 5) == []


def test_retrieval_ton_trong_tenant(db, seeded, imported):  # noqa: F811
    _indexed(db, imported)
    assert retrieve_r1(db, seeded["t2"].id, "căn hộ Grand View", 5) == []
    assert retrieve_r2(db, seeded["t2"].id, "Dự án Grand View", 5) == []
    assert retrieval_stats(db, seeded["t2"].id)["chunks"] == 0
