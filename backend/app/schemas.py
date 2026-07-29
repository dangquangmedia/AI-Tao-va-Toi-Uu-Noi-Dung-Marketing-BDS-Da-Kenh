from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: str

    model_config = {"from_attributes": True}


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ProjectOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IngestionRunIn(BaseModel):
    limit: int | None = Field(default=None, ge=1, description="Giới hạn số tin đọc từ jsonl (None = tất cả)")


class IngestionJobOut(BaseModel):
    id: str
    status: str
    job_type: str
    source: str
    total_read: int
    inserted: int
    unchanged: int
    updated: int
    quarantined: int
    error_summary: dict
    stats: dict
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class PipelineRunIn(BaseModel):
    limit: int | None = Field(default=None, ge=1, description="Giới hạn số tin raw đưa vào D1–D5")


class QuarantineOut(BaseModel):
    id: str
    ingestion_job_id: str
    error_code: str
    source_ref: str
    raw: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class CleanListingOut(BaseModel):
    id: str
    source_row_id: str
    parser_version: str
    property_type: str
    project_slug: str | None
    project_name: str | None
    project_confidence: float
    building_code: str | None
    unit_type_key: str | None
    ward: str | None
    district: str | None
    city: str | None
    area_m2: float | None
    bedrooms: int | None
    bathrooms: int | None
    total_price_vnd: float | None
    price_per_m2_vnd: float | None
    price_confidence: str
    price_evidence: str
    legal_facts: list
    amenities: list
    title_clean: str
    description_len: int
    tier: str
    dedup_cluster_id: str
    is_cluster_representative: bool
    field_flags: dict

    model_config = {"from_attributes": True}


class FactOut(BaseModel):
    id: str
    subject_type: str
    subject_key: str
    predicate: str
    value_text: str
    value_num: float | None
    unit: str
    confidence: float
    needs_review: bool
    parser_version: str
    source_listing_id: str
    source_url: str
    evidence: str
    valid_from: str
    valid_to: str
    review_note: str
    original_value_text: str

    model_config = {"from_attributes": True}


class IndexRunIn(BaseModel):
    tiers: list[str] = Field(default=["A", "B"], description="Tier dữ liệu đưa vào index")
    limit: int | None = Field(default=None, ge=1)
    embed: bool = True
    backend: str | None = Field(default=None, description="Ghi đè embedding backend cho lần chạy này")


class FactReviewIn(BaseModel):
    value_text: str | None = None
    needs_review: bool = False
    note: str | None = None


class RetrievalQueryOut(BaseModel):
    id: str
    dataset_version: str
    query_type: str
    difficulty: str
    question: str
    split: str
    project_slug: str | None
    expected_listing_ids: list
    expected_projects: list
    expected_entities: list
    generator: str
    needs_review: bool

    model_config = {"from_attributes": True}


class RetrieveIn(BaseModel):
    query: str = Field(min_length=2)
    config: str = Field(default="R3", pattern=r"^(R1|R2|R3)$")
    mode: str = Field(default="hybrid", pattern=r"^(fts|bm25|vector|hybrid)$")
    k: int = Field(default=10, ge=1, le=50)


class GenerateIn(BaseModel):
    brief: str = Field(min_length=5, max_length=1000)
    channel: str = Field(pattern=r"^(description|facebook|email|landing_seo)$")
    persona: str = Field(pattern=r"^(young_family|investor|first_home)$")
    config: str = Field(default="B", pattern=r"^(A|B|C|D)$")
    retrieval_config: str = Field(default="R3", pattern=r"^(R1|R2|R3)$")
    project_slug: str | None = None
    brand: dict | None = None
    k: int = Field(default=6, ge=1, le=20)
    adapter: str | None = None  # C/D: tên adapter QLoRA; None = lấy mặc định


class GenerationOut(BaseModel):
    id: str
    config: str
    retrieval_config: str
    channel: str
    persona: str
    project_slug: str | None
    brief: str
    prompt_version: str
    prompt_hash: str
    model_name: str
    provider: str
    seed: int
    adapter_name: str
    adapter_fingerprint: str
    context_chunk_ids: list
    context_fact_ids: list
    graph_paths: list
    router_plan: dict
    headline: str
    body: str
    cta: str
    claims: list
    metrics: dict
    latency_ms: int
    status: str
    error: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentCreateIn(BaseModel):
    generation_id: str
    title: str = Field(default="", max_length=300)


class ContentEditIn(BaseModel):
    headline: str = Field(default="", max_length=300)
    body: str = Field(min_length=1)
    cta: str = Field(default="", max_length=300)


class ContentReviewIn(BaseModel):
    approve: bool
    note: str = Field(default="", max_length=1000)


class ContentVersionOut(BaseModel):
    id: str
    version_no: int
    generation_id: str | None
    config: str
    model_name: str
    adapter_name: str
    prompt_version: str
    headline: str
    body: str
    cta: str
    edited_by_human: bool
    claims: list
    metrics: dict
    status: str
    review_note: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentItemOut(BaseModel):
    id: str
    project_slug: str | None
    channel: str
    persona: str
    title: str
    status: str
    current_version: int
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentDetailOut(ContentItemOut):
    versions: list[ContentVersionOut] = []
