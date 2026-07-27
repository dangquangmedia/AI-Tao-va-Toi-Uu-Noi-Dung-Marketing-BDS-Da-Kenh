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
    source: str
    total_read: int
    inserted: int
    unchanged: int
    updated: int
    quarantined: int
    error_summary: dict
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}
