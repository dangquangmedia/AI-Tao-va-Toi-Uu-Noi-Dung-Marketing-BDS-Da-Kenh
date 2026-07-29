"""BM25 tiếng Việt tự cài trên PostgreSQL (Tuần 4).

Vì sao phải làm: đo ở Tuần 3 cho thấy nhánh lexical bằng `ts_rank_cd` chỉ đạt
project precision@10 = 0,087. Hai nguyên nhân:

1. **Không có IDF.** `ts_rank_cd` chấm theo tần suất trong tài liệu, nên câu hỏi tự nhiên
   bị các từ phổ biến ("căn", "hộ", "bán", "giá") kéo về những tin không liên quan.
2. **Không tách từ tiếng Việt.** Cấu hình `simple` cắt theo âm tiết, "căn hộ" thành
   "can" + "ho" — mất nghĩa.

Cách xử lý: dựng chỉ mục ngược riêng (`lexical_postings`) với token = **âm tiết + bigram
âm tiết** (bigram khôi phục lại từ ghép: "can_ho", "phong_ngu"), rồi chấm bằng công thức
BM25 chuẩn (Robertson/Sparck Jones) với IDF thật. Không dùng thư viện ngoài — điểm số
tính được bằng tay nên giải thích được trước hội đồng.
"""

import math
import re
from collections import defaultdict

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Chunk, LexicalPosting
from app.services.reparse import deaccent

K1 = 1.5  # bão hòa tần suất từ — giá trị chuẩn của BM25
B = 0.75  # mức chuẩn hóa theo độ dài tài liệu
MAX_TERM_LEN = 60
POSTING_BATCH = 5000
_SYLLABLE = re.compile(r"[a-z0-9]+")


def tokenize_vi(text: str) -> list[str]:
    """Âm tiết + bigram âm tiết (đã bỏ dấu). Bigram thay cho bộ tách từ tiếng Việt."""
    syllables = [s for s in _SYLLABLE.findall(deaccent(text)) if len(s) <= MAX_TERM_LEN]
    bigrams = [f"{a}_{b}" for a, b in zip(syllables, syllables[1:])]
    return syllables + bigrams


def term_frequencies(text: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for token in tokenize_vi(text):
        counts[token] += 1
    return counts


def rebuild_postings(db: Session, tenant_id: str, chunk_ids: list[str] | None = None) -> int:
    """Dựng lại chỉ mục ngược cho các chunk chỉ định (None = toàn bộ tenant).

    Idempotent: xóa posting cũ của đúng những chunk đó rồi ghi lại.
    """
    query = select(Chunk).where(Chunk.tenant_id == tenant_id)
    if chunk_ids is not None:
        if not chunk_ids:
            return 0
        query = query.where(Chunk.id.in_(chunk_ids))
    chunks = db.scalars(query).all()
    if not chunks:
        return 0

    ids = [c.id for c in chunks]
    for start in range(0, len(ids), POSTING_BATCH):
        db.execute(
            delete(LexicalPosting).where(
                LexicalPosting.tenant_id == tenant_id,
                LexicalPosting.chunk_id.in_(ids[start : start + POSTING_BATCH]),
            )
        )

    rows = []
    for chunk in chunks:
        counts = term_frequencies(chunk.text)
        chunk.lexical_len = sum(counts.values())
        rows.extend(
            {"tenant_id": tenant_id, "chunk_id": chunk.id, "term": term, "tf": tf}
            for term, tf in counts.items()
        )
    for start in range(0, len(rows), POSTING_BATCH):
        db.bulk_insert_mappings(LexicalPosting, rows[start : start + POSTING_BATCH])
    db.flush()
    return len(rows)


def corpus_stats(db: Session, tenant_id: str) -> tuple[int, float]:
    """(số chunk, độ dài trung bình) — hai tham số của BM25."""
    total = db.scalar(select(func.count()).select_from(Chunk).where(Chunk.tenant_id == tenant_id)) or 0
    avg = db.scalar(
        select(func.avg(Chunk.lexical_len)).where(
            Chunk.tenant_id == tenant_id, Chunk.lexical_len > 0
        )
    )
    return total, float(avg or 1.0)


def bm25_scores(db: Session, tenant_id: str, query: str, limit: int) -> list[tuple[str, float]]:
    """Chấm BM25 cho truy vấn, trả [(chunk_id, score)] đã sắp xếp giảm dần."""
    terms = list(dict.fromkeys(tokenize_vi(query)))
    if not terms:
        return []

    total_docs, avg_len = corpus_stats(db, tenant_id)
    if not total_docs:
        return []

    rows = db.execute(
        select(LexicalPosting.term, LexicalPosting.chunk_id, LexicalPosting.tf, Chunk.lexical_len)
        .join(Chunk, Chunk.id == LexicalPosting.chunk_id)
        .where(LexicalPosting.tenant_id == tenant_id, LexicalPosting.term.in_(terms))
    ).all()
    if not rows:
        return []

    doc_freq: dict[str, int] = defaultdict(int)
    for term, _chunk_id, _tf, _length in rows:
        doc_freq[term] += 1

    scores: dict[str, float] = defaultdict(float)
    for term, chunk_id, tf, length in rows:
        df = doc_freq[term]
        idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
        norm = tf * (K1 + 1) / (tf + K1 * (1 - B + B * (length or 1) / avg_len))
        scores[chunk_id] += idf * norm

    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
