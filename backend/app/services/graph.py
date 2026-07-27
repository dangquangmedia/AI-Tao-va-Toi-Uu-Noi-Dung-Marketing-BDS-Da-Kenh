"""Truy vấn Property Knowledge Graph — traversal ≤2 hop bằng recursive CTE.

Vì sao ≤2 hop và vì sao PostgreSQL thay cho graph DB riêng: xem Plan/01 §4 và
ngân hàng câu hỏi hội đồng trong Plan/04. Ở tầng code, hệ quả là mọi truy vấn
quan hệ đều nằm trong một câu SQL đệ quy trên `graph_edges`, chạy được cả trên
PostgreSQL lẫn SQLite (test) mà không cần thư viện ngoài.
"""

from sqlalchemy import literal, select, union_all
from sqlalchemy.orm import Session

from app.models import GraphEdge, GraphEntity

MAX_DEPTH = 2


def find_entity(db: Session, tenant_id: str, entity_type: str, canonical_key: str) -> GraphEntity | None:
    return db.scalar(
        select(GraphEntity).where(
            GraphEntity.tenant_id == tenant_id,
            GraphEntity.entity_type == entity_type,
            GraphEntity.canonical_key == canonical_key,
        )
    )


def _adjacency(tenant_id: str):
    """Cạnh có hướng, nhưng duyệt được cả hai chiều (giữ nhãn chiều để giải thích path)."""
    forward = select(
        GraphEdge.src_id.label("a"),
        GraphEdge.dst_id.label("b"),
        GraphEdge.edge_type.label("t"),
        literal("out").label("d"),
    ).where(GraphEdge.tenant_id == tenant_id)
    backward = select(
        GraphEdge.dst_id.label("a"),
        GraphEdge.src_id.label("b"),
        GraphEdge.edge_type.label("t"),
        literal("in").label("d"),
    ).where(GraphEdge.tenant_id == tenant_id)
    return union_all(forward, backward).subquery("adj")


def traverse(db: Session, tenant_id: str, start_id: str, max_depth: int = MAX_DEPTH) -> list[dict]:
    """Trả mọi đường đi độ dài 1..max_depth từ `start_id`, kèm nhãn cạnh và nguồn.

    Không quay lại node đã đi qua (chống chu trình), không vượt quá `max_depth`.
    """
    max_depth = min(max_depth, MAX_DEPTH)
    adj = _adjacency(tenant_id)

    walk = select(
        literal(start_id).label("node"),
        literal(0).label("depth"),
        literal("").label("path"),
    ).cte("walk", recursive=True)

    step = (
        select(
            adj.c.b.label("node"),
            (walk.c.depth + 1).label("depth"),
            (walk.c.path + adj.c.a + literal("|") + adj.c.t + literal("|") + adj.c.d + literal("|") + adj.c.b + literal(";")).label("path"),
        )
        .select_from(adj.join(walk, adj.c.a == walk.c.node))
        .where(
            walk.c.depth < max_depth,
            adj.c.b != literal(start_id),
            walk.c.path.notlike(literal("%") + adj.c.b + literal("%")),
        )
    )
    walk = walk.union_all(step)

    rows = db.execute(
        select(walk.c.node, walk.c.depth, walk.c.path).where(walk.c.depth > 0)
    ).all()
    if not rows:
        return []

    node_ids = {start_id}
    parsed: list[list[tuple[str, str, str, str]]] = []
    for _, _, path in rows:
        hops = []
        for chunk in path.split(";"):
            if not chunk:
                continue
            a, edge_type, direction, b = chunk.split("|")
            node_ids.update((a, b))
            hops.append((a, edge_type, direction, b))
        parsed.append(hops)

    entities = {
        e.id: e
        for e in db.scalars(
            select(GraphEntity).where(
                GraphEntity.tenant_id == tenant_id, GraphEntity.id.in_(node_ids)
            )
        ).all()
    }
    edge_meta = {
        (e.src_id, e.dst_id, e.edge_type): e
        for e in db.scalars(select(GraphEdge).where(GraphEdge.tenant_id == tenant_id)).all()
    }

    def node_dict(entity_id: str) -> dict:
        entity = entities.get(entity_id)
        if entity is None:
            return {"id": entity_id, "type": "?", "key": "", "name": ""}
        return {
            "id": entity.id,
            "type": entity.entity_type,
            "key": entity.canonical_key,
            "name": entity.name,
            "support_count": entity.support_count,
        }

    results: list[dict] = []
    for hops in parsed:
        nodes = [node_dict(hops[0][0])] + [node_dict(h[3]) for h in hops]
        edges = []
        for a, edge_type, direction, b in hops:
            meta = edge_meta.get((a, b, edge_type)) or edge_meta.get((b, a, edge_type))
            edges.append(
                {
                    "type": edge_type,
                    "direction": direction,
                    "support_count": meta.support_count if meta else 0,
                    "source_url": meta.source_url if meta else "",
                    "valid_from": meta.valid_from if meta else "",
                    "valid_to": meta.valid_to if meta else "",
                }
            )
        results.append({"depth": len(hops), "nodes": nodes, "edges": edges})

    results.sort(key=lambda p: (p["depth"], [n["type"] for n in p["nodes"]], [n["key"] for n in p["nodes"]]))
    return results


def project_unit_paths(db: Session, tenant_id: str, project_key: str) -> dict:
    """Gate Tuần 2: đường đi `Project → Building → UnitType` trên dữ liệu thật.

    Trả cả path 2 hop qua Building lẫn path 1 hop `Project → UnitType`
    (dự án chưa nhận diện được mã tòa) để nói rõ độ phủ, không che dữ liệu thiếu.
    """
    project = find_entity(db, tenant_id, "Project", project_key)
    if project is None:
        return {"project": None, "paths": []}

    all_paths = traverse(db, tenant_id, project.id, MAX_DEPTH)
    via_building = [
        p
        for p in all_paths
        if p["depth"] == 2
        and p["nodes"][1]["type"] == "Building"
        and p["nodes"][2]["type"] == "UnitType"
    ]
    direct = [p for p in all_paths if p["depth"] == 1 and p["nodes"][1]["type"] == "UnitType"]
    return {
        "project": {
            "id": project.id,
            "key": project.canonical_key,
            "name": project.name,
            "support_count": project.support_count,
        },
        "paths": via_building + direct,
        "n_via_building": len(via_building),
        "n_direct": len(direct),
    }
