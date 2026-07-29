"""Truy xuất R1 / R2 / R3 — Plan/01 §5.2 (R1–R2 từ Tuần 3, R3 + BM25 từ Tuần 4).

- **R1** chạy trên `chunks`, không dùng graph: BM25 tiếng Việt (`services/lexical.py`),
  vector pgvector (bge-m3), hoặc `hybrid` = RRF có trọng số của hai nhánh.
  Chế độ `fts` (tsvector thô) giữ lại làm mốc so sánh cho báo cáo, không dùng production.
- **R2** không dùng so khớp văn bản: nhận diện thực thể trong câu hỏi, đi ≤2 hop trên
  Property Knowledge Graph ra tập dự án liên quan rồi lấy chunk của các dự án đó.
  Kết quả kèm **đường đi** để giải thích được vì sao tin này được chọn.
- **R3** (production): BM25 + vector + graph hợp nhất bằng **RRF có trọng số**, trọng số
  do `services/query_router.py` quyết theo ý định câu hỏi. Trọng số mặc định chốt bằng
  sweep trên 72 gold query (xem docs/checkpoints/week_04_retrieval_eval.md).

Bài học Tuần 3 giữ lại trong thiết kế: RRF **trọng số bằng nhau** làm kết quả tệ hơn cả
nhánh mạnh nhất khi có một nhánh yếu, nên mọi hàm hợp nhất ở đây đều nhận `weights`.
"""

import re

from sqlalchemy import func, select, text as sql_text
from sqlalchemy.orm import Session

from app.models import Chunk, GraphEntity
from app.services.embeddings import cosine, get_embedder
from app.services.graph import traverse
from app.services.lexical import bm25_scores
from app.services.reparse import deaccent

DEFAULT_K = 10
RRF_K = 60  # hằng số làm mượt của Reciprocal Rank Fusion
# Trọng số mặc định khi không qua router (chốt bằng sweep trên gold query, Tuần 4)
DEFAULT_WEIGHTS = {"vector": 1.0, "bm25": 0.6, "graph": 0.3}
CANDIDATE_MULTIPLIER = 3
MIN_ENTITY_TOKENS = 2
MAX_GRAPH_PROJECTS = 10  # số dự án tối đa lấy từ graph cho một câu hỏi
GRAPH_ENTITY_TYPES = ("Project", "Ward", "District", "City", "Amenity", "Building")


def _postgres(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def _as_result(chunk: Chunk, score: float, rank: int, retriever: str, path=None) -> dict:
    return {
        "chunk_id": chunk.id,
        "clean_listing_id": chunk.clean_listing_id,
        "chunk_type": chunk.chunk_type,
        "project_slug": chunk.project_slug,
        "tier": chunk.tier,
        "text": chunk.text,
        "source_listing_id": chunk.source_listing_id,
        "source_url": chunk.source_url,
        "score": round(float(score), 6),
        "rank": rank,
        "retriever": retriever,
        "path": path,
    }


_TERM = re.compile(r"[a-z0-9]+")


def _or_tsquery(query: str) -> str:
    """Ghép từ khóa bằng OR để câu hỏi dài vẫn có kết quả.

    `plainto_tsquery` nối các từ bằng AND nên câu hỏi tự nhiên ("căn hộ 2 phòng ngủ có
    sổ hồng gần công viên") hầu như không khớp chunk nào. Dùng OR rồi để `ts_rank_cd`
    xếp hạng theo số từ khớp — đúng tinh thần baseline lexical của R1.
    """
    terms = [t for t in _TERM.findall(deaccent(query)) if len(t) > 1]
    return " | ".join(dict.fromkeys(terms))


def search_fts(db: Session, tenant_id: str, query: str, k: int = DEFAULT_K, project_slug=None) -> list[dict]:
    """Tìm theo từ khóa. PostgreSQL dùng tsvector; SQLite (test) dùng LIKE không dấu."""
    flat = deaccent(query)
    if _postgres(db):
        terms = _or_tsquery(query)
        if not terms:
            return []
        sql = (
            "SELECT id, ts_rank_cd(search_vector, to_tsquery('simple', :terms)) AS score "
            "FROM chunks WHERE tenant_id = :tenant "
            "AND search_vector @@ to_tsquery('simple', :terms) "
            + ("AND project_slug = :project " if project_slug else "")
            + "ORDER BY score DESC, id LIMIT :k"
        )
        params = {"terms": terms, "tenant": tenant_id, "k": k}
        if project_slug:
            params["project"] = project_slug
        rows = db.execute(sql_text(sql), params).all()
    else:
        tokens = [t for t in flat.split() if len(t) > 1]
        stmt = select(Chunk.id, Chunk.search_vector).where(Chunk.tenant_id == tenant_id)
        if project_slug:
            stmt = stmt.where(Chunk.project_slug == project_slug)
        scored = []
        for chunk_id, haystack in db.execute(stmt).all():
            if not haystack:
                continue
            hits = sum(1 for token in tokens if token in haystack)
            if hits:
                scored.append((chunk_id, hits / max(len(tokens), 1)))
        rows = sorted(scored, key=lambda r: (-r[1], r[0]))[:k]

    chunks = {c.id: c for c in db.scalars(select(Chunk).where(Chunk.id.in_([r[0] for r in rows]))).all()}
    return [
        _as_result(chunks[chunk_id], score, i + 1, "fts")
        for i, (chunk_id, score) in enumerate(rows)
        if chunk_id in chunks
    ]


def search_bm25(db: Session, tenant_id: str, query: str, k: int = DEFAULT_K, project_slug=None) -> list[dict]:
    """Nhánh lexical của Tuần 4: BM25 có IDF + bigram âm tiết (xem services/lexical.py).

    Lấy dư ứng viên rồi mới lọc theo dự án để việc lọc không làm mất top-k.
    """
    scored = bm25_scores(db, tenant_id, query, k * CANDIDATE_MULTIPLIER if project_slug else k)
    if not scored:
        return []
    chunks = {
        c.id: c
        for c in db.scalars(select(Chunk).where(Chunk.id.in_([cid for cid, _ in scored]))).all()
    }
    results = []
    for chunk_id, score in scored:
        chunk = chunks.get(chunk_id)
        if chunk is None or (project_slug and chunk.project_slug != project_slug):
            continue
        results.append(_as_result(chunk, score, len(results) + 1, "bm25"))
        if len(results) >= k:
            break
    return results


def search_vector(db: Session, tenant_id: str, query: str, k: int = DEFAULT_K, project_slug=None) -> list[dict]:
    """Tìm theo ngữ nghĩa bằng embedding (cosine)."""
    embedder = get_embedder()
    vector = embedder.encode([query], is_query=True)[0]

    if _postgres(db):
        stmt = (
            select(Chunk, Chunk.embedding.cosine_distance(vector).label("distance"))
            .where(Chunk.tenant_id == tenant_id, Chunk.embedding.is_not(None))
            .order_by("distance")
            .limit(k)
        )
        if project_slug:
            stmt = stmt.where(Chunk.project_slug == project_slug)
        rows = [(chunk, 1.0 - float(distance)) for chunk, distance in db.execute(stmt).all()]
    else:
        stmt = select(Chunk).where(Chunk.tenant_id == tenant_id, Chunk.embedding.is_not(None))
        if project_slug:
            stmt = stmt.where(Chunk.project_slug == project_slug)
        scored = [(chunk, cosine(vector, chunk.embedding)) for chunk in db.scalars(stmt).all()]
        rows = sorted(scored, key=lambda r: (-r[1], r[0].id))[:k]

    return [_as_result(chunk, score, i + 1, "vector") for i, (chunk, score) in enumerate(rows)]


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]], k: int = DEFAULT_K, weights: list[float] | None = None
) -> list[dict]:
    """RRF: điểm = Σ wᵢ/(RRF_K + hạng).

    `weights` cho phép hạ trọng số nhánh yếu — bài học từ Tuần 3: trọng số bằng nhau
    kéo kết quả xuống thấp hơn cả nhánh vector đơn thuần.
    """
    if weights is None:
        weights = [1.0] * len(ranked_lists)
    fused: dict[str, dict] = {}
    for weight, results in zip(weights, ranked_lists):
        for item in results:
            key = item["chunk_id"]
            entry = fused.setdefault(key, {**item, "score": 0.0, "retriever": ""})
            entry["score"] += weight / (RRF_K + item["rank"])
            sources = {s for s in entry["retriever"].split("+") if s}
            sources.add(item["retriever"])
            entry["retriever"] = "+".join(sorted(sources))
            if item.get("path") and not entry.get("path"):
                entry["path"] = item["path"]
    ordered = sorted(fused.values(), key=lambda r: (-r["score"], r["chunk_id"]))[:k]
    for i, item in enumerate(ordered, start=1):
        item["rank"] = i
        item["score"] = round(item["score"], 6)
    return ordered


def retrieve_r1(
    db: Session, tenant_id: str, query: str, k: int = DEFAULT_K, mode: str = "hybrid", project_slug=None
) -> list[dict]:
    """R1 — baseline không dùng graph.

    mode: `fts` (tsvector thô, giữ lại để so sánh) · `bm25` · `vector` ·
    `hybrid` (RRF có trọng số của bm25 + vector).
    """
    if mode == "fts":
        return search_fts(db, tenant_id, query, k, project_slug)
    if mode == "bm25":
        return search_bm25(db, tenant_id, query, k, project_slug)
    if mode == "vector":
        return search_vector(db, tenant_id, query, k, project_slug)
    wide = k * CANDIDATE_MULTIPLIER
    return reciprocal_rank_fusion(
        [
            search_bm25(db, tenant_id, query, wide, project_slug),
            search_vector(db, tenant_id, query, wide, project_slug),
        ],
        k,
        weights=[DEFAULT_WEIGHTS["bm25"], DEFAULT_WEIGHTS["vector"]],
    )


def retrieve_r3(
    db: Session,
    tenant_id: str,
    query: str,
    k: int = DEFAULT_K,
    weights: dict | None = None,
    use_router: bool = True,
) -> tuple[list[dict], dict]:
    """R3 — cấu hình production: BM25 + vector + graph, hợp nhất bằng RRF có trọng số.

    Trả thêm `plan` của router để UI/báo cáo giải thích được vì sao chọn cấu hình đó.
    """
    from app.services.query_router import route  # tránh import vòng

    plan = (
        route(db, tenant_id, query)
        if use_router
        else {
            "intent": "general",
            "weights": dict(DEFAULT_WEIGHTS),
            "project_slug": None,
            "allowed_projects": [],
            "matched_entities": [],
            "prefer_chunk_types": [],
            "explain": "router tắt",
        }
    )
    if weights:
        plan = {**plan, "weights": {**plan["weights"], **weights}}

    wide = k * CANDIDATE_MULTIPLIER
    project_slug = plan.get("project_slug")
    allowed = set(plan.get("allowed_projects") or [])

    def _restrict(results: list[dict]) -> list[dict]:
        """Giữ nguyên thứ hạng tương đối nhưng chỉ giữ dự án mà câu hỏi nhắc tới."""
        if not allowed:
            return results
        kept = [r for r in results if r.get("project_slug") in allowed]
        for rank, item in enumerate(kept, start=1):
            item["rank"] = rank
        return kept

    lists = [
        _restrict(search_bm25(db, tenant_id, query, wide, project_slug)),
        _restrict(search_vector(db, tenant_id, query, wide, project_slug)),
        _restrict(retrieve_r2(db, tenant_id, query, wide)),
    ]
    fused = reciprocal_rank_fusion(
        lists,
        k,
        weights=[plan["weights"]["bm25"], plan["weights"]["vector"], plan["weights"]["graph"]],
    )
    return fused, plan


def match_entities(db: Session, tenant_id: str, query: str, limit: int = 5) -> list[GraphEntity]:
    """Nhận diện thực thể trong câu hỏi bằng khớp tên (không dấu), ưu tiên tên dài nhất."""
    flat = deaccent(query)
    candidates = db.scalars(
        select(GraphEntity).where(
            GraphEntity.tenant_id == tenant_id, GraphEntity.entity_type.in_(GRAPH_ENTITY_TYPES)
        )
    ).all()
    matched = []
    for entity in candidates:
        names = [entity.name, entity.canonical_key.replace("-", " "), *entity.aliases]
        for name in names:
            key = deaccent(name).replace("-", " ").strip()
            if len(key.split()) < MIN_ENTITY_TOKENS:
                continue
            if key in flat:
                matched.append((len(key), entity))
                break
    matched.sort(key=lambda pair: (-pair[0], pair[1].canonical_key))
    return [entity for _, entity in matched[:limit]]


def retrieve_r2(db: Session, tenant_id: str, query: str, k: int = DEFAULT_K) -> list[dict]:
    """R2 — graph-only: thực thể trong câu hỏi → ≤2 hop → chunk của dự án liên quan.

    Không dùng similarity văn bản, nên đo được đóng góp riêng của graph (RQ6).
    """
    entities = match_entities(db, tenant_id, query)
    if not entities:
        return []

    # dự án → (độ sâu, mô tả đường đi)
    projects: dict[str, tuple[int, list[str]]] = {}
    for entity in entities:
        if entity.entity_type == "Project":
            projects.setdefault(entity.canonical_key, (0, [entity.name]))
        for path in traverse(db, tenant_id, entity.id):
            for index, node in enumerate(path["nodes"][1:], start=1):
                if node["type"] != "Project":
                    continue
                depth = index
                if node["key"] not in projects or depth < projects[node["key"]][0]:
                    labels = [path["nodes"][0]["name"]]
                    for i, hop in enumerate(path["nodes"][1 : index + 1], start=0):
                        labels.append(f"--{path['edges'][i]['type']}-->")
                        labels.append(hop["name"])
                    projects[node["key"]] = (depth, labels)
    if not projects:
        return []

    # Dự án nhận diện trực tiếp (depth 0) phải đứng trước dự án chỉ "cùng phường/quận"
    # (depth 1–2), nếu không một phường đông dự án sẽ nhấn chìm dự án được hỏi.
    ordered = sorted(projects.items(), key=lambda kv: (kv[1][0], kv[0]))[:MAX_GRAPH_PROJECTS]
    depth_of = {slug: depth for slug, (depth, _) in ordered}

    rows = db.scalars(
        select(Chunk)
        .where(
            Chunk.tenant_id == tenant_id,
            Chunk.project_slug.in_(list(depth_of)),
            Chunk.chunk_type == "facts",  # thẻ dữ kiện đại diện cho tin
        )
        .order_by(Chunk.project_slug, Chunk.id)
    ).all()

    scored = [
        (1.0 / (1 + depth_of[chunk.project_slug]), chunk, projects[chunk.project_slug][1])
        for chunk in rows
    ]
    scored.sort(key=lambda r: (-r[0], r[1].id))
    return [
        _as_result(chunk, score, i + 1, "graph", path=path)
        for i, (score, chunk, path) in enumerate(scored[:k])
    ]


def retrieval_stats(db: Session, tenant_id: str) -> dict:
    """Số liệu knowledge base để hiển thị/kiểm tra nhanh."""
    total = db.scalar(select(func.count()).select_from(Chunk).where(Chunk.tenant_id == tenant_id))
    embedded = db.scalar(
        select(func.count())
        .select_from(Chunk)
        .where(Chunk.tenant_id == tenant_id, Chunk.embedding.is_not(None))
    )
    by_type = db.execute(
        select(Chunk.chunk_type, func.count())
        .where(Chunk.tenant_id == tenant_id)
        .group_by(Chunk.chunk_type)
    ).all()
    model = db.scalar(
        select(Chunk.embedding_model)
        .where(Chunk.tenant_id == tenant_id, Chunk.embedding_model != "")
        .limit(1)
    )
    return {
        "chunks": total,
        "embedded": embedded,
        "by_type": {t: n for t, n in by_type},
        "embedding_model": model or "",
    }
