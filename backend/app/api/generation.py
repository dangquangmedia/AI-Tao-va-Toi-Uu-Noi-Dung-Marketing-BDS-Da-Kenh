from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_roles
from app.models import Generation, User
from app.schemas import GenerateIn, GenerationOut, RetrieveIn
from app.services.adapters import adapters_root, default_adapter_name, list_adapters
from app.services.generation import run_generation
from app.services.query_router import route
from app.services.retrieval import retrieve_r1, retrieve_r2, retrieve_r3

router = APIRouter(prefix="/api/generation", tags=["generation"])


@router.post("/retrieve")
def retrieve(
    body: RetrieveIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chạy thử retrieval để xem hệ thống lấy gì trước khi sinh nội dung."""
    plan = route(db, user.tenant_id, body.query)
    if body.config == "R1":
        results = retrieve_r1(db, user.tenant_id, body.query, body.k, mode=body.mode)
    elif body.config == "R2":
        results = retrieve_r2(db, user.tenant_id, body.query, body.k)
    else:
        results, plan = retrieve_r3(db, user.tenant_id, body.query, body.k)
    return {"plan": plan, "results": results}


@router.get("/adapters")
def list_generation_adapters(user: User = Depends(get_current_user)):
    """Adapter QLoRA đang có trên máy chủ — UI dùng để bật/tắt cấu hình C và D.

    Trả cả adapter hỏng kèm lý do, để lúc bàn giao biết ngay thiếu file gì thay vì chỉ
    thấy "không có adapter nào".
    """
    items = list_adapters()
    return {
        "adapters": items,
        "default": default_adapter_name(),
        "dir": str(adapters_root()),
        "ready": any(a["loadable"] for a in items),
    }


@router.post("", response_model=GenerationOut)
def create_generation(
    body: GenerateIn,
    user: User = Depends(require_roles("admin", "marketer")),
    db: Session = Depends(get_db),
):
    """Sinh nội dung theo cấu hình A/B (model gốc) hoặc C/D (model + adapter QLoRA)."""
    try:
        return run_generation(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            brief=body.brief,
            channel=body.channel,
            persona=body.persona,
            config=body.config,
            retrieval_config=body.retrieval_config,
            project_slug=body.project_slug,
            brand=body.brand,
            k=body.k,
            adapter_name=body.adapter,
        )
    except (FileNotFoundError, ValueError) as exc:
        # Chưa bàn giao adapter, hoặc adapter thiếu file — lỗi cấu hình phía người dùng,
        # không phải lỗi hệ thống. Trả nguyên thông báo vì nó đã chứa hướng dẫn xử lý.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("", response_model=list[GenerationOut])
def list_generations(
    config: str | None = None,
    channel: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(Generation).where(Generation.tenant_id == user.tenant_id)
    if config:
        query = query.where(Generation.config == config)
    if channel:
        query = query.where(Generation.channel == channel)
    return db.scalars(
        query.order_by(Generation.created_at.desc()).limit(limit).offset(offset)
    ).all()


@router.get("/{generation_id}", response_model=GenerationOut)
def get_generation(
    generation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    record = db.get(Generation, generation_id)
    if record is None or record.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy bản sinh nội dung")
    return record
