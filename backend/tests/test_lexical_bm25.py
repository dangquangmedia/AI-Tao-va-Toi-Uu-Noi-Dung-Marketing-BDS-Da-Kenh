"""Test BM25 tiếng Việt (Tuần 4) — tách từ, IDF và xếp hạng."""

import math

from sqlalchemy import delete, select

from app.models import Chunk, CleanListing, LexicalPosting, SourceListing
from app.services.lexical import (
    B,
    K1,
    bm25_scores,
    rebuild_postings,
    term_frequencies,
    tokenize_vi,
)
from app.services.pipeline import run_clean_pipeline
from tests.test_pipeline import databds, imported  # noqa: F401 — fixture dùng lại


def test_tokenize_sinh_ca_am_tiet_va_bigram():
    tokens = tokenize_vi("Căn hộ 2 phòng ngủ")
    assert "can" in tokens and "ho" in tokens
    assert "can_ho" in tokens  # bigram khôi phục từ ghép
    assert "phong_ngu" in tokens


def test_term_frequencies_dem_dung():
    counts = term_frequencies("nhà nhà nhà")
    assert counts["nha"] == 3
    assert counts["nha_nha"] == 2


def _make_chunks(db, tenant_id, texts):
    """Thay toàn bộ chunk của tenant bằng vài đoạn văn kiểm soát được."""
    listing = db.scalars(select(CleanListing).limit(1)).first()
    source = db.scalars(select(SourceListing).limit(1)).first()
    assert listing is not None and source is not None

    db.execute(delete(LexicalPosting))
    db.execute(delete(Chunk))
    for i, text in enumerate(texts):
        db.add(
            Chunk(
                tenant_id=tenant_id,
                clean_listing_id=listing.id,
                source_row_id=source.id,
                chunk_type="description",
                seq=i,
                text=text,
                content_hash=f"h{i}",
            )
        )
    db.flush()
    return db.scalars(select(Chunk)).all()


def test_bm25_uu_tien_tu_hiem_hon_tu_pho_bien(db, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    tenant_id = imported["tenant_id"]
    _make_chunks(
        db,
        tenant_id,
        [
            "Căn hộ bán giá tốt tại trung tâm",  # chỉ chứa từ phổ biến
            "Căn hộ có hồ bơi vô cực hiếm có",  # chứa từ hiếm "hồ bơi vô cực"
            "Nhà phố bán giá tốt khu dân cư",
        ],
    )
    rebuild_postings(db, tenant_id)

    scored = bm25_scores(db, tenant_id, "hồ bơi vô cực", limit=3)
    assert scored, "phải có kết quả"
    best_id = scored[0][0]
    best_text = db.get(Chunk, best_id).text
    assert "hồ bơi vô cực" in best_text


def test_bm25_khong_co_tu_khop_thi_rong(db, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    tenant_id = imported["tenant_id"]
    _make_chunks(db, tenant_id, ["Căn hộ trung tâm"])
    rebuild_postings(db, tenant_id)
    assert bm25_scores(db, tenant_id, "xyzzy plugh", limit=5) == []


def test_cong_thuc_bm25_dung_tham_so():
    """Chốt tham số chuẩn — đổi giá trị là đổi kết quả thí nghiệm, phải cố ý."""
    assert (K1, B) == (1.5, 0.75)
    # IDF luôn dương với df < N (không cho điểm âm như biến thể IDF cũ)
    total, df = 100, 99
    assert math.log(1 + (total - df + 0.5) / (df + 0.5)) > 0
