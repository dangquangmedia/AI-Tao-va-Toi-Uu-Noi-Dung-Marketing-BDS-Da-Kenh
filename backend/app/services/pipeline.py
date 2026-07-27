"""Pipeline làm sạch D1–D5 (Plan/02 §4): raw zone → clean → facts → graph.

Đặc tính bắt buộc: **idempotent**. Chạy lại trên cùng batch phải cho đúng cùng
một trạng thái — không thêm dòng, không đổi cluster id, không nhân đôi cạnh graph.
Cách đạt được:
- `clean_listings` khóa theo (tenant, source_row_id); bỏ qua nếu `content_hash` và
  `parser_version` không đổi.
- `facts` khóa theo `fact_key` = hash(nguồn|predicate|giá trị); fact cũ không còn
  được sinh ra thì bị xóa (tính lại đúng bằng dữ liệu hiện tại).
- Graph được **dựng lại toàn bộ** từ `clean_listings` mỗi lần chạy rồi so khớp:
  thêm node/cạnh thiếu, xóa node/cạnh không còn bằng chứng.
- Quarantine của tầng làm sạch thuộc về job mới nhất (quarantine của ingestion raw
  giữ nguyên lịch sử).
"""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    CleanListing,
    Fact,
    GraphEdge,
    GraphEntity,
    IngestionJob,
    QuarantineRecord,
    SourceListing,
)
from app.services.dedup import build_clusters, simhash
from app.services.reparse import PARSER_VERSION, deaccent, reparse_record, slug_to_name

JOB_TYPE = "clean_pipeline"

# Field của clean_listings được ghi từ kết quả re-parse
_CLEAN_FIELDS = (
    "parser_version",
    "property_type",
    "project_slug",
    "project_confidence",
    "building_code",
    "unit_type_key",
    "ward",
    "district",
    "city",
    "area_m2",
    "bedrooms",
    "bathrooms",
    "total_price_vnd",
    "price_per_m2_vnd",
    "price_confidence",
    "price_evidence",
    "legal_facts",
    "amenities",
    "title_clean",
    "description_clean",
    "description_len",
    "tier",
    "field_flags",
)


def _fact_key(source_listing_id: str, predicate: str, value_text: str) -> str:
    return hashlib.sha256(f"{source_listing_id}|{predicate}|{value_text}".encode()).hexdigest()


def _key_slug(text: str) -> str:
    return "-".join(t for t in deaccent(text).replace(".", " ").split() if t)


def _build_facts(clean: dict, source: SourceListing) -> list[dict]:
    """D4 — sinh canonical facts kèm provenance cho một tin.

    Fact từ trường có sẵn của crawler ghi rõ `crawler:<field>`; fact khôi phục ghi
    trích đoạn thật trong title/description để hội đồng kiểm chứng được.
    """
    valid_to = source.last_seen_at if source.listing_status == "EXPIRED" else ""
    base = {
        "subject_type": "listing",
        "subject_key": source.source_listing_id,
        "parser_version": PARSER_VERSION,
        "source_row_id": source.id,
        "source_listing_id": source.source_listing_id,
        "source_url": source.canonical_url,
        "content_hash": source.content_hash,
        "valid_from": source.first_seen_at,
        "valid_to": valid_to,
    }
    facts: list[dict] = []

    def add(predicate, value_text, *, value_num=None, unit="", confidence=1.0, evidence="", review=False):
        facts.append(
            {
                **base,
                "predicate": predicate,
                "value_text": str(value_text),
                "value_num": value_num,
                "unit": unit,
                "confidence": confidence,
                "evidence": evidence,
                "needs_review": review,
            }
        )

    if clean["property_type"]:
        add("property_type", clean["property_type"], confidence=0.95, evidence="crawler:property_type")
    if clean["area_m2"]:
        add("area_m2", clean["area_m2"], value_num=clean["area_m2"], unit="m2", confidence=0.9,
            evidence="crawler:area_m2")
    if clean["bedrooms"]:
        add("bedrooms", clean["bedrooms"], value_num=float(clean["bedrooms"]), unit="phòng",
            confidence=0.9, evidence="crawler:bedrooms")
    if clean["bathrooms"]:
        add("bathrooms", clean["bathrooms"], value_num=float(clean["bathrooms"]), unit="phòng",
            confidence=0.9, evidence="crawler:bathrooms")

    if clean["total_price_vnd"]:
        confidence = 0.95 if clean["price_confidence"] == "parsed" else 0.8
        add("total_price_vnd", int(clean["total_price_vnd"]), value_num=clean["total_price_vnd"],
            unit="VND", confidence=confidence, evidence=clean["price_evidence"],
            review=confidence < 0.85)
    if clean["price_per_m2_vnd"]:
        add("price_per_m2_vnd", int(clean["price_per_m2_vnd"]), value_num=clean["price_per_m2_vnd"],
            unit="VND/m2", confidence=0.8, evidence=clean["price_evidence"], review=True)

    if clean["project_slug"]:
        confidence = clean["project_confidence"]
        add("project", clean["project_slug"], confidence=confidence,
            evidence=f"canonical_url:{source.canonical_url}", review=confidence < 0.7)
    if clean["building_code"]:
        add("building", clean["building_code"], confidence=0.7,
            evidence=clean["title_clean"][:200], review=True)
    if clean["ward"]:
        add("ward", clean["ward"], confidence=0.9, evidence=f"canonical_url:{source.canonical_url}")
    if clean["district"]:
        add("district", clean["district"], confidence=0.8, evidence=clean["title_clean"][:200])
    if clean["city"]:
        add("city", clean["city"], confidence=0.8, evidence=clean["title_clean"][:200])

    for value in clean["legal_facts"]:
        add("legal_status", value, confidence=0.8,
            evidence=clean.get("legal_evidence", {}).get(value, ""))
    for value in clean["amenities"]:
        add("amenity", value, confidence=0.7,
            evidence=clean.get("amenity_evidence", {}).get(value, ""), review=True)
    return facts


def _rebuild_graph(db: Session, tenant_id: str) -> dict:
    """D5 — dựng lại graph tất định từ toàn bộ clean_listings của tenant."""
    rows = db.scalars(select(CleanListing).where(CleanListing.tenant_id == tenant_id)).all()
    sources = {
        s.id: s
        for s in db.scalars(select(SourceListing).where(SourceListing.tenant_id == tenant_id)).all()
    }

    entities: dict[tuple[str, str], dict] = {}
    edges: dict[tuple[str, str, str, str, str], dict] = {}

    def add_entity(entity_type: str, key: str, name: str, attributes: dict | None = None):
        node = entities.setdefault(
            (entity_type, key),
            {"name": name, "attributes": attributes or {}, "support": 0},
        )
        node["support"] += 1
        return (entity_type, key)

    def add_edge(src, dst, edge_type, row):
        source = sources.get(row.source_row_id)
        edge = edges.setdefault(
            (*src, *dst, edge_type),
            {
                "support": 0,
                "source_row_id": row.source_row_id,
                "source_url": source.canonical_url if source else "",
                "valid_from": source.first_seen_at if source else "",
                "valid_to": source.last_seen_at if source and source.listing_status == "EXPIRED" else "",
            },
        )
        edge["support"] += 1

    for row in rows:
        if not row.project_slug:
            continue  # graph dựng trên Tier A (tin gắn được dự án) — Plan/02 §5
        project = add_entity("Project", row.project_slug, slug_to_name(row.project_slug),
                             {"property_type": row.property_type})
        building = None
        if row.building_code:
            building = add_entity(
                "Building",
                f"{row.project_slug}::{row.building_code}",
                f"Tòa {row.building_code}",
                {"project_slug": row.project_slug},
            )
            add_edge(building, project, "PART_OF", row)
        if row.unit_type_key:
            unit = add_entity(
                "UnitType",
                f"{row.project_slug}::{row.unit_type_key}",
                row.unit_type_key,
                {"project_slug": row.project_slug, "bedrooms": row.bedrooms},
            )
            add_edge(project, unit, "HAS_UNIT_TYPE", row)
            if building:
                add_edge(building, unit, "HAS_UNIT_TYPE", row)
        # Phân cấp địa lý: Project → Ward → District → City (bỏ mắt xích nào thiếu)
        district = None
        city = None
        if row.district:
            district = add_entity("District", _key_slug(row.district), row.district)
        if row.city:
            city = add_entity("City", _key_slug(row.city), row.city)
        if row.ward:
            ward = add_entity("Ward", row.ward, slug_to_name(row.ward))
            add_edge(project, ward, "LOCATED_IN", row)
            if district:
                add_edge(ward, district, "LOCATED_IN", row)
            elif city:
                add_edge(ward, city, "LOCATED_IN", row)
        elif district:
            add_edge(project, district, "LOCATED_IN", row)
        elif city:
            add_edge(project, city, "LOCATED_IN", row)
        if district and city:
            add_edge(district, city, "LOCATED_IN", row)
        for amenity in row.amenities:
            node = add_entity("Amenity", amenity, amenity)
            add_edge(project, node, "HAS_AMENITY", row)

    existing_entities = {
        (e.entity_type, e.canonical_key): e
        for e in db.scalars(select(GraphEntity).where(GraphEntity.tenant_id == tenant_id)).all()
    }
    id_by_key: dict[tuple[str, str], str] = {}
    entities_inserted = 0
    for key, data in entities.items():
        row = existing_entities.get(key)
        if row is None:
            row = GraphEntity(
                tenant_id=tenant_id,
                entity_type=key[0],
                canonical_key=key[1],
                name=data["name"],
                attributes=data["attributes"],
                support_count=data["support"],
            )
            db.add(row)
            db.flush()
            entities_inserted += 1
        else:
            row.name = data["name"]
            row.attributes = data["attributes"]
            row.support_count = data["support"]
        id_by_key[key] = row.id

    stale_entities = [e.id for key, e in existing_entities.items() if key not in entities]

    existing_edges = {
        (e.src_id, e.dst_id, e.edge_type): e
        for e in db.scalars(select(GraphEdge).where(GraphEdge.tenant_id == tenant_id)).all()
    }
    wanted_edges: set[tuple[str, str, str]] = set()
    edges_inserted = 0
    for (src_type, src_key, dst_type, dst_key, edge_type), data in edges.items():
        src_id = id_by_key[(src_type, src_key)]
        dst_id = id_by_key[(dst_type, dst_key)]
        wanted_edges.add((src_id, dst_id, edge_type))
        row = existing_edges.get((src_id, dst_id, edge_type))
        if row is None:
            db.add(
                GraphEdge(
                    tenant_id=tenant_id,
                    src_id=src_id,
                    dst_id=dst_id,
                    edge_type=edge_type,
                    support_count=data["support"],
                    source_row_id=data["source_row_id"],
                    source_url=data["source_url"],
                    valid_from=data["valid_from"],
                    valid_to=data["valid_to"],
                )
            )
            edges_inserted += 1
        else:
            row.support_count = data["support"]
            row.source_row_id = data["source_row_id"]
            row.source_url = data["source_url"]

    stale_edges = [e.id for key, e in existing_edges.items() if key not in wanted_edges]
    if stale_edges:
        db.execute(delete(GraphEdge).where(GraphEdge.id.in_(stale_edges)))
    if stale_entities:
        db.execute(delete(GraphEdge).where(
            (GraphEdge.src_id.in_(stale_entities)) | (GraphEdge.dst_id.in_(stale_entities))
        ))
        db.execute(delete(GraphEntity).where(GraphEntity.id.in_(stale_entities)))
    db.flush()

    return {
        "entities": len(entities),
        "entities_inserted": entities_inserted,
        "entities_deleted": len(stale_entities),
        "edges": len(edges),
        "edges_inserted": edges_inserted,
        "edges_deleted": len(stale_edges),
    }


def reset_derived_data(db: Session, tenant_id: str) -> dict:
    """Xóa toàn bộ dữ liệu dẫn xuất (clean/facts/graph) của tenant — raw zone giữ nguyên.

    Dùng khi luật parser đổi: thay vì backfill, dựng lại từ raw để dữ liệu luôn khớp
    với `PARSER_VERSION` hiện hành (yêu cầu tái lập của Plan/02 §4).
    """
    counts = {}
    for model in (GraphEdge, GraphEntity, Fact, CleanListing):
        result = db.execute(delete(model).where(model.tenant_id == tenant_id))
        counts[model.__tablename__] = result.rowcount
    db.commit()
    return counts


def run_clean_pipeline(
    db: Session,
    tenant_id: str,
    created_by: str,
    limit: int | None = None,
) -> IngestionJob:
    job = IngestionJob(
        tenant_id=tenant_id,
        created_by=created_by,
        status="running",
        job_type=JOB_TYPE,
    )
    db.add(job)
    db.flush()

    # Quarantine tầng làm sạch được tính lại mỗi lần chạy → không phình theo số lần chạy
    old_clean_jobs = select(IngestionJob.id).where(
        IngestionJob.tenant_id == tenant_id, IngestionJob.job_type == JOB_TYPE
    )
    db.execute(
        delete(QuarantineRecord).where(
            QuarantineRecord.tenant_id == tenant_id,
            QuarantineRecord.ingestion_job_id.in_(old_clean_jobs),
        )
    )

    errors: dict[str, int] = {}

    def quarantine(code: str, source: SourceListing) -> None:
        db.add(
            QuarantineRecord(
                tenant_id=tenant_id,
                ingestion_job_id=job.id,
                error_code=code,
                source_ref=source.source_listing_id,
                raw={"canonical_url": source.canonical_url, "title": source.raw.get("title")},
            )
        )
        job.quarantined += 1
        errors[code] = errors.get(code, 0) + 1

    query = select(SourceListing).where(SourceListing.tenant_id == tenant_id).order_by(
        SourceListing.source_listing_id
    )
    if limit is not None:
        query = query.limit(limit)
    sources = db.scalars(query).all()

    existing_clean = {
        c.source_row_id: c
        for c in db.scalars(select(CleanListing).where(CleanListing.tenant_id == tenant_id)).all()
    }

    processed: list[tuple[CleanListing, SourceListing, dict]] = []
    rejected_rows: list[str] = []  # source_row_id bị quarantine ở lần chạy này

    for source in sources:
        job.total_read += 1
        clean = reparse_record(source.raw, source.canonical_url)

        # Contract v1: phải có nội dung text và tối thiểu project hoặc location
        if not clean["title_clean"] and not clean["description_clean"]:
            quarantine("empty_content", source)
            rejected_rows.append(source.id)
            continue
        if not clean["project_slug"] and not clean["ward"] and not clean["district"] and not clean["city"]:
            quarantine("no_project_no_location", source)
            rejected_rows.append(source.id)
            continue

        row = existing_clean.get(source.id)
        if row is not None and row.content_hash == source.content_hash and row.parser_version == PARSER_VERSION:
            job.unchanged += 1
            continue

        if row is None:
            row = CleanListing(
                tenant_id=tenant_id, source_row_id=source.id, content_hash=source.content_hash
            )
            db.add(row)
            job.inserted += 1
        else:
            row.content_hash = source.content_hash
            job.updated += 1
        for field in _CLEAN_FIELDS:
            setattr(row, field, clean[field])
        row.simhash = simhash(clean["description_clean"])
        processed.append((row, source, clean))

    # Tin trượt contract ở lần chạy này không được để lại clean/fact cũ
    if rejected_rows:
        db.execute(
            delete(Fact).where(Fact.tenant_id == tenant_id, Fact.source_row_id.in_(rejected_rows))
        )
        db.execute(
            delete(CleanListing).where(
                CleanListing.tenant_id == tenant_id,
                CleanListing.source_row_id.in_(rejected_rows),
            )
        )
    db.flush()

    # --- D3: gom cụm trùng trên toàn bộ clean_listings của tenant ---
    all_clean = db.scalars(select(CleanListing).where(CleanListing.tenant_id == tenant_id)).all()
    source_by_id = {s.id: s for s in sources}
    for row in all_clean:
        if row.source_row_id not in source_by_id:
            source_by_id[row.source_row_id] = db.get(SourceListing, row.source_row_id)

    cluster_input = [
        {
            "key": source_by_id[row.source_row_id].source_listing_id,
            "content_hash": row.content_hash,
            "simhash": row.simhash,
            "description_len": row.description_len,
        }
        for row in all_clean
    ]
    clusters = build_clusters(cluster_input)
    duplicates = 0
    for row in all_clean:
        info = clusters[source_by_id[row.source_row_id].source_listing_id]
        row.dedup_cluster_id = info["cluster_id"]
        row.is_cluster_representative = info["is_representative"]
        if not info["is_representative"]:
            duplicates += 1

    # --- D4: canonical facts cho các tin vừa xử lý ---
    facts_inserted = facts_deleted = 0
    if processed:
        source_row_ids = [source.id for _, source, _ in processed]
        existing_facts = {
            f.fact_key: f
            for f in db.scalars(
                select(Fact).where(
                    Fact.tenant_id == tenant_id, Fact.source_row_id.in_(source_row_ids)
                )
            ).all()
        }
        wanted: set[str] = set()
        for _, source, clean in processed:
            for fact in _build_facts(clean, source):
                key = _fact_key(source.source_listing_id, fact["predicate"], fact["value_text"])
                wanted.add(key)
                if key in existing_facts:
                    continue
                db.add(Fact(tenant_id=tenant_id, fact_key=key, **fact))
                facts_inserted += 1
        stale = [f.id for key, f in existing_facts.items() if key not in wanted]
        if stale:
            db.execute(delete(Fact).where(Fact.id.in_(stale)))
            facts_deleted = len(stale)
    db.flush()

    graph_stats = _rebuild_graph(db, tenant_id)

    job.stats = {
        "clusters": len({info["cluster_id"] for info in clusters.values()}),
        "duplicates": duplicates,
        "facts_inserted": facts_inserted,
        "facts_deleted": facts_deleted,
        **graph_stats,
    }
    job.status = "done"
    job.error_summary = errors
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job
