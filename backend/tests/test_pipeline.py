"""Test pipeline D1–D5: idempotency, provenance của facts, graph tất định.

Fixture mô phỏng đúng cấu trúc DataBDS thật (URL batdongsan có mã vùng, mô tả
dính rác Sentry, tin đăng lặp) để kiểm chứng gate Tuần 2 mà không cần Postgres.
"""

import json

import pytest
from sqlalchemy import func, select

from app.models import CleanListing, Fact, GraphEdge, GraphEntity, QuarantineRecord
from app.services.ingestion import run_databds_import
from app.services.reparse import PARSER_VERSION
from app.services.pipeline import run_clean_pipeline
from tests.test_ingestion import CSV_HEADER

URL_TEMPLATE = "https://batdongsan.com.vn/{path}/tin-pr{slid}"
DU_AN = "ban-can-ho-chung-cu-duong-pham-van-nghi-phuong-tan-phong-9-grand-view"
NHA_LE = "ban-nha-rieng-duong-binh-long-phuong-phu-tho-hoa-12"

RECORDS = [
    {
        "source_listing_id": "111",
        "title": "Bán căn hộ 2PN Grand View tòa S3 giá 4.9 tỷ có sổ hồng",
        "description": "Căn hộ tòa S3 dự án Grand View, view sông, gần công viên. "
        "Quận 7, TP HCM. Liên hệ 0901 234 567.",
        "property_type": "apartment",
        "bedrooms": 2,
        "area_m2": 72.0,
        "total_price_vnd": 4_900_000_000,
        "seller_display_name": "Nguyễn Văn A",
        "path": DU_AN,
    },
    {
        "source_listing_id": "222",
        "title": "Bán căn hộ 3PN Grand View tòa S3 giá 6 tỷ 500",
        "description": "Căn 3 phòng ngủ tòa S3 Grand View, nội thất đầy đủ, hồ bơi nội khu. Quận 7.",
        "property_type": "apartment",
        "bedrooms": 3,
        "area_m2": 95.0,
        "path": DU_AN,
    },
    {
        "source_listing_id": "333",
        "title": "Bán nhà riêng Bình Long, Tân Phú giá 6.45 tỷ",
        "description": "Nhà 2 tầng hẻm xe hơi, sổ hồng riêng, gần trường học. "
        "Sentry.onLoad(function () { Sentry.init({ environme",
        "property_type": "private_house",
        "area_m2": 76.0,
        "path": NHA_LE,
    },
]


@pytest.fixture()
def databds(tmp_path):
    """Kho DataBDS giả lập đúng định dạng file thật."""
    rows = []
    lines = []
    for i, record in enumerate(RECORDS, start=1):
        record = dict(record)
        path = record.pop("path")
        slid = record["source_listing_id"]
        url = URL_TEMPLATE.format(path=path, slid=slid)
        rows.append(
            f'{i},batdongsan,"{slid}",{url},"2026-07-17","2026-07-24","2026-07-24",'
            f"EXPIRED,,hash-{slid}\n"
        )
        lines.append(json.dumps(record, ensure_ascii=False))
    (tmp_path / "source_listing_202607250000.csv").write_text(
        CSV_HEADER + "".join(rows), encoding="utf-8"
    )
    (tmp_path / "listings.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def imported(db, seeded, databds):
    run_databds_import(
        db, tenant_id=seeded["t1"].id, created_by=seeded["admin1"].id, databds_dir=databds
    )
    return {"tenant_id": seeded["t1"].id, "created_by": seeded["admin1"].id}


def test_pipeline_sinh_clean_facts_va_graph(db, imported):
    job = run_clean_pipeline(db, **imported)

    assert job.status == "done"
    assert job.job_type == "clean_pipeline"
    assert job.total_read == 3
    assert job.inserted == 3
    assert job.quarantined == 0

    clean = db.scalars(select(CleanListing).order_by(CleanListing.tier)).all()
    by_id = {c.title_clean[:20]: c for c in clean}
    assert len(clean) == 3

    can_ho = db.scalar(select(CleanListing).where(CleanListing.bedrooms == 2))
    assert can_ho.project_slug == "grand-view"
    assert can_ho.ward == "tan-phong"
    assert can_ho.building_code == "S3"
    assert can_ho.unit_type_key == "apartment-2pn"
    assert can_ho.total_price_vnd == 4_900_000_000
    assert can_ho.price_confidence == "parsed"  # khớp giá parser gốc
    assert can_ho.tier == "A"
    assert "0901" not in can_ho.description_clean  # PII đã mask
    assert "so_hong" in can_ho.legal_facts

    nha_le = db.scalar(select(CleanListing).where(CleanListing.property_type == "private_house"))
    assert nha_le.project_slug is None
    assert nha_le.tier == "B"
    assert "Sentry" not in nha_le.description_clean  # rác JS đã bị bóc
    assert nha_le.total_price_vnd == 6_450_000_000
    assert by_id  # bảo đảm fixture có dữ liệu như mong đợi


def test_moi_fact_deu_co_provenance(db, imported):
    run_clean_pipeline(db, **imported)
    facts = db.scalars(select(Fact)).all()

    assert facts
    for fact in facts:
        assert fact.source_url.startswith("https://batdongsan.com.vn/")
        assert fact.source_listing_id
        assert fact.content_hash
        assert fact.parser_version == PARSER_VERSION
        assert fact.evidence  # không có fact nào thiếu bằng chứng
        assert fact.valid_from and fact.valid_to  # tin EXPIRED có khoảng hiệu lực

    gia = db.scalar(select(Fact).where(Fact.predicate == "total_price_vnd", Fact.subject_key == "111"))
    assert gia.value_num == 4_900_000_000
    assert "4.9 tỷ" in gia.evidence
    assert gia.confidence >= 0.9


def test_chay_lai_khong_sinh_duplicate(db, imported):
    """Gate Tuần 2: chạy lại cùng batch cho đúng cùng một trạng thái."""
    job1 = run_clean_pipeline(db, **imported)
    snapshot = {
        "clean": db.scalar(select(func.count()).select_from(CleanListing)),
        "facts": db.scalar(select(func.count()).select_from(Fact)),
        "entities": db.scalar(select(func.count()).select_from(GraphEntity)),
        "edges": db.scalar(select(func.count()).select_from(GraphEdge)),
        "quarantine": db.scalar(select(func.count()).select_from(QuarantineRecord)),
    }
    cluster_ids = {c.id: c.dedup_cluster_id for c in db.scalars(select(CleanListing)).all()}

    job2 = run_clean_pipeline(db, **imported)

    assert job1.inserted == 3 and job2.inserted == 0
    assert job2.unchanged == 3
    assert job2.stats["facts_inserted"] == 0
    assert job2.stats["entities_inserted"] == 0
    assert job2.stats["edges_inserted"] == 0
    assert snapshot == {
        "clean": db.scalar(select(func.count()).select_from(CleanListing)),
        "facts": db.scalar(select(func.count()).select_from(Fact)),
        "entities": db.scalar(select(func.count()).select_from(GraphEntity)),
        "edges": db.scalar(select(func.count()).select_from(GraphEdge)),
        "quarantine": db.scalar(select(func.count()).select_from(QuarantineRecord)),
    }
    # Cụm dedup ổn định giữa hai lần chạy
    assert cluster_ids == {c.id: c.dedup_cluster_id for c in db.scalars(select(CleanListing)).all()}


def test_graph_deterministic_va_co_provenance(db, imported):
    run_clean_pipeline(db, **imported)

    types = {
        e.entity_type: e
        for e in db.scalars(select(GraphEntity).order_by(GraphEntity.entity_type)).all()
    }
    assert types["Project"].canonical_key == "grand-view"
    assert types["Project"].name == "Grand View"
    assert types["Project"].support_count == 2  # hai tin cùng dự án
    assert types["Building"].canonical_key == "grand-view::S3"
    assert types["Ward"].canonical_key == "tan-phong"

    edges = {e.edge_type for e in db.scalars(select(GraphEdge)).all()}
    assert {"PART_OF", "HAS_UNIT_TYPE", "LOCATED_IN"} <= edges
    for edge in db.scalars(select(GraphEdge)).all():
        assert edge.source_url  # cạnh nào cũng truy được về tin nguồn


def test_tin_khong_du_contract_bi_quarantine(db, seeded, tmp_path):
    """Tin không có nội dung → quarantine, không chặn batch."""
    rows = [
        f'1,batdongsan,"901",https://batdongsan.com.vn/ban-dat-phuong-binh-an-12/tin-pr901,'
        f'"2026-07-17","2026-07-24","2026-07-24",EXPIRED,,hash-901\n',
        f'2,batdongsan,"902",https://batdongsan.com.vn/ban-dat-phuong-binh-an-12/tin-pr902,'
        f'"2026-07-17","2026-07-24","2026-07-24",EXPIRED,,hash-902\n',
    ]
    (tmp_path / "source_listing_202607250000.csv").write_text(
        CSV_HEADER + "".join(rows), encoding="utf-8"
    )
    (tmp_path / "listings.jsonl").write_text(
        json.dumps({"source_listing_id": "901", "title": "", "description": ""}, ensure_ascii=False)
        + "\n"
        + json.dumps(
            {"source_listing_id": "902", "title": "Bán đất Bình An 3 tỷ", "property_type": "land"},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    run_databds_import(
        db, tenant_id=seeded["t1"].id, created_by=seeded["admin1"].id, databds_dir=tmp_path
    )

    job = run_clean_pipeline(db, tenant_id=seeded["t1"].id, created_by=seeded["admin1"].id)

    assert job.total_read == 2
    assert job.quarantined == 1
    assert job.error_summary == {"empty_content": 1}
    assert job.inserted == 1  # tin còn lại vẫn qua được
    record = db.scalar(select(QuarantineRecord).where(QuarantineRecord.error_code == "empty_content"))
    assert record.source_ref == "901"


def test_tenant_khac_khong_thay_du_lieu_sach(db, seeded, imported):
    run_clean_pipeline(db, **imported)
    for model in (CleanListing, Fact, GraphEntity, GraphEdge):
        n = db.scalar(
            select(func.count()).select_from(model).where(model.tenant_id == seeded["t2"].id)
        )
        assert n == 0
