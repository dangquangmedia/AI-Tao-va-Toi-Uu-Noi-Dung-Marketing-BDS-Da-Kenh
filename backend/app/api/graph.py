from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import GraphEdge, GraphEntity, User
from app.services.graph import MAX_DEPTH, project_unit_paths, traverse

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/entities")
def list_entities(
    entity_type: str | None = None,
    q: str | None = None,
    with_building: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(GraphEntity).where(GraphEntity.tenant_id == user.tenant_id)
    if entity_type:
        query = query.where(GraphEntity.entity_type == entity_type)
    if q:
        query = query.where(func.lower(GraphEntity.name).like(f"%{q.lower()}%"))
    if with_building:
        # Chỉ dự án đã nhận diện được tòa/block → có đường Project → Building → UnitType
        has_building = select(GraphEdge.dst_id).where(
            GraphEdge.tenant_id == user.tenant_id, GraphEdge.edge_type == "PART_OF"
        )
        query = query.where(GraphEntity.id.in_(has_building))
    rows = db.scalars(
        query.order_by(GraphEntity.support_count.desc(), GraphEntity.canonical_key).limit(limit)
    ).all()
    return [
        {
            "id": e.id,
            "type": e.entity_type,
            "key": e.canonical_key,
            "name": e.name,
            "support_count": e.support_count,
            "attributes": e.attributes,
        }
        for e in rows
    ]


@router.get("/entities/{entity_id}/neighbors")
def neighbors(
    entity_id: str,
    depth: int = Query(default=MAX_DEPTH, ge=1, le=MAX_DEPTH),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entity = db.get(GraphEntity, entity_id)
    if entity is None or entity.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy thực thể")
    return {
        "entity": {"id": entity.id, "type": entity.entity_type, "key": entity.canonical_key, "name": entity.name},
        "paths": traverse(db, user.tenant_id, entity_id, depth),
    }


@router.get("/projects/{project_key}/paths")
def project_paths(
    project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Project → Building → UnitType (và Project → UnitType khi chưa có mã tòa)."""
    result = project_unit_paths(db, user.tenant_id, project_key)
    if result["project"] is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy dự án trong graph")
    return result
