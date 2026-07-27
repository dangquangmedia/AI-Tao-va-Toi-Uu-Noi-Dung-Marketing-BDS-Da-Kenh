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

    model_config = {"from_attributes": True}
