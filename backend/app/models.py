import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db import Base

try:  # pgvector chỉ cần khi chạy PostgreSQL; test SQLite dùng biến thể JSON
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    Vector = None

EMBEDDING_DIM = settings.embedding_dim
# pgvector trên PostgreSQL, JSON trên SQLite → cùng một model chạy được ở cả hai
_EMBEDDING_TYPE = Vector(EMBEDDING_DIM).with_variant(JSON, "sqlite") if Vector else JSON
_TSVECTOR_TYPE = TSVECTOR().with_variant(Text, "sqlite")


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


ROLES = ("admin", "marketer", "reviewer")


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(20))  # admin | marketer | reviewer
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped[Tenant] = relationship()


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_projects_tenant_slug"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class SourceListing(Base):
    """Raw zone: bản ghi tin đăng crawl, lưu nguyên văn, không sửa tay."""

    __tablename__ = "source_listings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source", "source_listing_id", name="uq_source_listing"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    source: Mapped[str] = mapped_column(String(50))  # batdongsan
    source_listing_id: Mapped[str] = mapped_column(String(50), index=True)
    canonical_url: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    listing_status: Mapped[str] = mapped_column(String(20), default="")  # ACTIVE | EXPIRED
    first_seen_at: Mapped[str] = mapped_column(String(30), default="")
    last_seen_at: Mapped[str] = mapped_column(String(30), default="")
    raw: Mapped[dict] = mapped_column(JSON)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ingestion_job_id: Mapped[str] = mapped_column(String(32), ForeignKey("ingestion_jobs.id"))


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|done|failed
    job_type: Mapped[str] = mapped_column(String(30), default="ingest_raw")  # ingest_raw | clean_pipeline
    source: Mapped[str] = mapped_column(String(50), default="databds")
    total_read: Mapped[int] = mapped_column(Integer, default=0)
    inserted: Mapped[int] = mapped_column(Integer, default=0)
    unchanged: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    quarantined: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)  # số liệu D1–D5 của job pipeline
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))


class QuarantineRecord(Base):
    """Bản ghi vi phạm contract — giữ nguyên raw để truy vết, không chặn batch."""

    __tablename__ = "quarantine_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    ingestion_job_id: Mapped[str] = mapped_column(String(32), ForeignKey("ingestion_jobs.id"), index=True)
    error_code: Mapped[str] = mapped_column(String(50))
    source_ref: Mapped[str] = mapped_column(String(100), default="")
    raw: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CleanListing(Base):
    """Đầu ra D1–D3: bản ghi đã re-parse, chuẩn hóa và gắn cụm dedup.

    Raw zone (source_listings) không bao giờ bị sửa; mọi giá trị ở đây đều
    tái tạo được từ raw bằng parser_version tương ứng.
    """

    __tablename__ = "clean_listings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_row_id", name="uq_clean_listing_source"),
        Index("ix_clean_listings_project", "tenant_id", "project_slug"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    source_row_id: Mapped[str] = mapped_column(String(32), ForeignKey("source_listings.id"), index=True)
    parser_version: Mapped[str] = mapped_column(String(30))
    content_hash: Mapped[str] = mapped_column(String(64))  # hash raw lúc xử lý → phát hiện cần chạy lại

    property_type: Mapped[str] = mapped_column(String(30), default="")
    project_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)  # tên có dấu
    project_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    building_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unit_type_key: Mapped[str | None] = mapped_column(String(60), nullable=True)

    ward: Mapped[str | None] = mapped_column(String(120), nullable=True)  # từ canonical_url
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_price_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_per_m2_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_confidence: Mapped[str] = mapped_column(String(20), default="missing")  # parsed|reparsed|missing
    price_evidence: Mapped[str] = mapped_column(Text, default="")

    legal_facts: Mapped[list] = mapped_column(JSON, default=list)
    amenities: Mapped[list] = mapped_column(JSON, default=list)

    title_clean: Mapped[str] = mapped_column(Text, default="")
    description_clean: Mapped[str] = mapped_column(Text, default="")
    description_len: Mapped[int] = mapped_column(Integer, default=0)

    tier: Mapped[str] = mapped_column(String(1), default="C")  # A | B | C — xem Plan/02 §5
    dedup_cluster_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    is_cluster_representative: Mapped[bool] = mapped_column(default=True)
    simhash: Mapped[str] = mapped_column(String(16), default="")

    field_flags: Mapped[dict] = mapped_column(JSON, default=dict)  # nguồn/độ tin của từng field
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Fact(Base):
    """D4 — canonical fact. Mọi fact bắt buộc có provenance (nguồn + trích đoạn)."""

    __tablename__ = "facts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "fact_key", name="uq_facts_tenant_key"),
        Index("ix_facts_subject", "tenant_id", "subject_type", "subject_key"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    fact_key: Mapped[str] = mapped_column(String(64))  # hash xác định → chạy lại không sinh trùng

    subject_type: Mapped[str] = mapped_column(String(20))  # listing | project
    subject_key: Mapped[str] = mapped_column(String(120))
    predicate: Mapped[str] = mapped_column(String(40), index=True)
    value_text: Mapped[str] = mapped_column(Text)
    value_num: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), default="")

    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    needs_review: Mapped[bool] = mapped_column(default=False)
    parser_version: Mapped[str] = mapped_column(String(30))

    # Provenance bắt buộc
    source_row_id: Mapped[str] = mapped_column(String(32), ForeignKey("source_listings.id"), index=True)
    source_listing_id: Mapped[str] = mapped_column(String(50), default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    valid_from: Mapped[str] = mapped_column(String(30), default="")
    valid_to: Mapped[str] = mapped_column(String(30), default="")  # rỗng = còn hiệu lực

    # Vết review của người dùng (fact editor, Tuần 3) — sửa tay không làm mất giá trị máy
    reviewed_by: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str] = mapped_column(Text, default="")
    original_value_text: Mapped[str] = mapped_column(Text, default="")  # giá trị máy sinh trước khi sửa

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GraphEntity(Base):
    """D5 — node của Property Knowledge Graph (deterministic, không do LLM sinh)."""

    __tablename__ = "graph_entities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", "canonical_key", name="uq_graph_entity"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(30), index=True)  # Project|Building|UnitType|District|City|Amenity
    canonical_key: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(200))
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    support_count: Mapped[int] = mapped_column(Integer, default=0)  # số tin làm bằng chứng
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GraphEdge(Base):
    """D5 — cạnh có provenance và khoảng hiệu lực (temporal)."""

    __tablename__ = "graph_edges"
    __table_args__ = (
        UniqueConstraint("tenant_id", "src_id", "dst_id", "edge_type", name="uq_graph_edge"),
        Index("ix_graph_edges_src", "tenant_id", "src_id"),
        Index("ix_graph_edges_dst", "tenant_id", "dst_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    src_id: Mapped[str] = mapped_column(String(32), ForeignKey("graph_entities.id"))
    dst_id: Mapped[str] = mapped_column(String(32), ForeignKey("graph_entities.id"))
    edge_type: Mapped[str] = mapped_column(String(30))  # PART_OF|HAS_UNIT_TYPE|LOCATED_IN|HAS_AMENITY
    support_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_row_id: Mapped[str] = mapped_column(String(32), default="")  # 1 tin đại diện làm bằng chứng
    source_url: Mapped[str] = mapped_column(Text, default="")
    valid_from: Mapped[str] = mapped_column(String(30), default="")
    valid_to: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Chunk(Base):
    """Đơn vị index cho retrieval (Tuần 3).

    Mỗi chunk giữ nguyên provenance của tin nguồn để câu trả lời nào cũng trích được
    nguồn. `embedding` dùng pgvector trên PostgreSQL; trên SQLite (test) lưu JSON để
    cùng một code chạy được ở cả hai nơi. `search_vector` là FTS tiếng Việt đã bỏ dấu.
    """

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("tenant_id", "clean_listing_id", "chunk_type", "seq", name="uq_chunk_unit"),
        Index("ix_chunks_project", "tenant_id", "project_slug"),
        # Khai báo ngay trong model để autogenerate không xóa nhầm ở migration sau.
        # Tùy chọn postgresql_* bị SQLite bỏ qua → test vẫn tạo index thường.
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    clean_listing_id: Mapped[str] = mapped_column(String(32), ForeignKey("clean_listings.id"), index=True)
    source_row_id: Mapped[str] = mapped_column(String(32), ForeignKey("source_listings.id"))
    source_listing_id: Mapped[str] = mapped_column(String(50), default="")
    source_url: Mapped[str] = mapped_column(Text, default="")

    project_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tier: Mapped[str] = mapped_column(String(1), default="C")
    chunk_type: Mapped[str] = mapped_column(String(20))  # title | description | facts
    seq: Mapped[int] = mapped_column(Integer, default=0)

    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    lexical_len: Mapped[int] = mapped_column(Integer, default=0)  # số token BM25 (Tuần 4)
    content_hash: Mapped[str] = mapped_column(String(64), default="")  # hash text → biết khi cần embed lại

    embedding: Mapped[list | None] = mapped_column(_EMBEDDING_TYPE, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(60), default="")
    search_vector: Mapped[str | None] = mapped_column(_TSVECTOR_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class DatasetSplit(Base):
    """Chia tập theo project/cụm dedup — đóng băng theo `dataset_version` (Plan/02 §6)."""

    __tablename__ = "dataset_splits"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "dataset_version", "unit_type", "unit_key", name="uq_dataset_split_unit"
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    dataset_version: Mapped[str] = mapped_column(String(30), index=True)
    unit_type: Mapped[str] = mapped_column(String(20))  # project | cluster
    unit_key: Mapped[str] = mapped_column(String(160))
    split: Mapped[str] = mapped_column(String(12), index=True)  # train | validation | test
    stratum: Mapped[str] = mapped_column(String(20), default="")  # nhóm quy mô để chia cân đối
    n_listings: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RetrievalQuery(Base):
    """Gold query cho benchmark R1–R3 (Plan/02 §8, protocol ở Plan/03)."""

    __tablename__ = "retrieval_queries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dataset_version", "query_key", name="uq_retrieval_query"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    dataset_version: Mapped[str] = mapped_column(String(30), index=True)
    query_key: Mapped[str] = mapped_column(String(64))
    query_type: Mapped[str] = mapped_column(String(20), index=True)
    question: Mapped[str] = mapped_column(Text)
    split: Mapped[str] = mapped_column(String(12), default="test")
    project_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expected_listing_ids: Mapped[list] = mapped_column(JSON, default=list)
    expected_entities: Mapped[list] = mapped_column(JSON, default=list)
    generator: Mapped[str] = mapped_column(String(30), default="")  # template sinh ra query
    needs_review: Mapped[bool] = mapped_column(default=True)  # chờ Hải soát tay
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LexicalPosting(Base):
    """Chỉ mục ngược cho BM25 (Tuần 4) — một dòng cho mỗi (chunk, token).

    Tách khỏi `chunks.search_vector` vì tsvector không giữ được tần suất theo cách
    BM25 cần, và không cho phép tính IDF trên corpus của riêng tenant.
    """

    __tablename__ = "lexical_postings"
    __table_args__ = (
        Index("ix_lexical_postings_term", "tenant_id", "term"),
        Index("ix_lexical_postings_chunk", "chunk_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"))
    chunk_id: Mapped[str] = mapped_column(String(32), ForeignKey("chunks.id"))
    term: Mapped[str] = mapped_column(String(80))
    tf: Mapped[int] = mapped_column(Integer, default=1)


class Generation(Base):
    """Một lần sinh nội dung — log đủ để tái lập và để so sánh A–D (Plan/03 §7).

    Lưu cả cấu hình (A/B/C/D + retrieval), prompt version + hash, model, seed, context
    đã dùng (chunk/fact/graph path) và kết quả chấm claim. Không có bảng này thì bảng
    kết quả thực nghiệm không chứng minh được là chạy trên cùng điều kiện.
    """

    __tablename__ = "generations"
    __table_args__ = (Index("ix_generations_tenant_created", "tenant_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), index=True)
    created_by: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))

    config: Mapped[str] = mapped_column(String(4), index=True)  # A | B | C | D
    retrieval_config: Mapped[str] = mapped_column(String(10), default="none")  # none|R1|R2|R3
    channel: Mapped[str] = mapped_column(String(20))
    persona: Mapped[str] = mapped_column(String(20))
    project_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    clean_listing_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    brief: Mapped[str] = mapped_column(Text, default="")

    prompt_version: Mapped[str] = mapped_column(String(30), default="")
    prompt_hash: Mapped[str] = mapped_column(String(64), default="")
    model_name: Mapped[str] = mapped_column(String(120), default="")
    provider: Mapped[str] = mapped_column(String(30), default="")
    seed: Mapped[int] = mapped_column(Integer, default=0)

    context_chunk_ids: Mapped[list] = mapped_column(JSON, default=list)
    context_fact_ids: Mapped[list] = mapped_column(JSON, default=list)
    graph_paths: Mapped[list] = mapped_column(JSON, default=list)
    router_plan: Mapped[dict] = mapped_column(JSON, default=dict)

    headline: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    cta: Mapped[str] = mapped_column(Text, default="")
    raw_output: Mapped[str] = mapped_column(Text, default="")

    claims: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="done")  # done | failed
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
