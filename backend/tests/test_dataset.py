"""Test chia tập chống leakage, gold query và SFT draft (Tuần 3)."""

import json

from sqlalchemy import select

from app.models import CleanListing, DatasetSplit, RetrievalQuery
from app.services.dataset import (
    SPLIT_RATIOS,
    assign_split,
    build_dataset_split,
    leakage_audit,
    split_of_listing,
    split_report,
)
from app.services.gold_queries import _hard_specs, generate_gold_queries
from app.services.pipeline import run_clean_pipeline
from app.services.sft_builder import build_sft_draft
from tests.test_pipeline import databds, imported  # noqa: F401 — fixture dùng lại

VERSION = "dataset_test"


def test_assign_split_tat_dinh_va_dung_ty_le():
    assert assign_split("project:abc", VERSION) == assign_split("project:abc", VERSION)
    keys = [f"project:du-an-{i}" for i in range(3000)]
    counts = {name: 0 for name, _ in SPLIT_RATIOS}
    for key in keys:
        counts[assign_split(key, VERSION)] += 1
    # Sai số ±3 điểm phần trăm là chấp nhận được với 3.000 đơn vị
    for name, ratio in SPLIT_RATIOS:
        assert abs(counts[name] / len(keys) - ratio) < 0.03


def test_doi_phien_ban_thi_chia_lai_nhung_cung_phien_ban_thi_bat_bien():
    key = "project:vinhomes-central-park"
    assert assign_split(key, "dataset_v1") == assign_split(key, "dataset_v1")
    khac = [assign_split(f"project:p{i}", "dataset_v1") != assign_split(f"project:p{i}", "dataset_v2") for i in range(50)]
    assert any(khac)  # salt theo version → version mới chia lại


def test_split_chia_theo_du_an_va_khong_ro_ri(db, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    summary = build_dataset_split(db, imported["tenant_id"], VERSION)

    assert sum(entry["listings"] for entry in summary.values()) == 3
    rows = db.scalars(select(DatasetSplit).where(DatasetSplit.dataset_version == VERSION)).all()
    assert {r.unit_type for r in rows} <= {"project", "cluster"}

    audit = leakage_audit(db, imported["tenant_id"], VERSION)
    assert audit["passed"] is True
    assert audit["listings_unassigned"] == 0
    assert audit["leaking_clusters"] == [] and audit["leaking_projects"] == []

    # Hai tin cùng dự án grand-view phải nằm cùng split
    listing_split = split_of_listing(db, imported["tenant_id"], VERSION)
    assert len(set(listing_split.values())) <= 3
    report = split_report(db, imported["tenant_id"], VERSION)
    assert sum(entry["units"] for entry in report.values()) == len(rows)


def test_chay_lai_khong_sinh_duplicate_split(db, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    build_dataset_split(db, imported["tenant_id"], VERSION)
    first = {(r.unit_key, r.split) for r in db.scalars(select(DatasetSplit)).all()}
    build_dataset_split(db, imported["tenant_id"], VERSION)
    second = {(r.unit_key, r.split) for r in db.scalars(select(DatasetSplit)).all()}
    assert first == second
    assert len(db.scalars(select(DatasetSplit)).all()) == len(first)


def test_gold_query_sinh_tu_split_test(db, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    build_dataset_split(db, imported["tenant_id"], VERSION)
    result = generate_gold_queries(db, imported["tenant_id"], VERSION)

    queries = db.scalars(select(RetrievalQuery)).all()
    assert len(queries) == result["total"]
    for query in queries:
        assert query.split == "test"
        assert query.needs_review is True  # chờ người soát trước khi khóa benchmark
        assert query.question.strip()
        assert query.generator

    # Chạy lại không nhân đôi
    generate_gold_queries(db, imported["tenant_id"], VERSION)
    assert len(db.scalars(select(RetrievalQuery)).all()) == len(queries)


def _listing(**kwargs) -> CleanListing:
    """Tin sạch tối thiểu để kiểm luật sinh câu hỏi (không cần ghi DB)."""
    base = dict(
        id=kwargs.pop("id"),
        tenant_id="t",
        source_row_id="s",
        parser_version="v",
        content_hash="h",
        property_type="apartment",
        title_clean="",
        description_clean="",
    )
    return CleanListing(**{**base, **kwargs})


def test_gold_query_kho_khong_neu_ten_du_an_va_gom_moi_dap_an_dung():
    """Bộ hard phải: (1) không nhắc tên dự án, (2) nhãn gồm *mọi* tin khớp điều kiện."""
    rows = [
        _listing(id=f"id{i}", district="Quận 7", bedrooms=2, area_m2=area, project_slug=slug,
                 project_name=name, total_price_vnd=price, ward="tan-phong")
        for i, (area, slug, name, price) in enumerate(
            [
                (70.0, "grand-view", "Grand View", 4_000_000_000),
                (72.0, "grand-view", "Grand View", 4_100_000_000),
                (75.0, "vista-verde", "Vista Verde", 4_200_000_000),
                (200.0, "xa-lac", "Xa Lắc", 9_000_000_000),  # lệch diện tích → ngoài nhãn
            ]
        )
    ]

    specs = _hard_specs(rows)
    attribute = [s for s in specs if s["query_type"] == "hard_attribute"]

    assert attribute, "phải sinh được câu hỏi theo thuộc tính"
    spec = attribute[0]
    assert spec["difficulty"] == "hard"
    assert spec["project_slug"] is None
    for name in ("Grand View", "Vista Verde", "Xa Lắc"):
        assert name not in spec["question"]
    # 3 tin trong ±15% quanh 70 m²; tin 200 m² bị loại
    assert set(spec["expected_listing_ids"]) == {"id0", "id1", "id2"}
    assert set(spec["expected_projects"]) == {"grand-view", "vista-verde"}


def test_gold_query_kho_bo_nhom_qua_it_dap_an():
    """Nhóm dưới 3 đáp án bị bỏ: precision@10 khi đó bị trần quá thấp để đọc được."""
    rows = [
        _listing(id="a", district="Quận 1", bedrooms=2, area_m2=50.0),
        _listing(id="b", district="Quận 1", bedrooms=2, area_m2=51.0),
    ]
    assert [s for s in _hard_specs(rows) if s["query_type"] == "hard_attribute"] == []


def test_gold_query_kho_ghi_nhan_tin_le_khong_thuoc_du_an():
    """Tin lẻ vẫn là đáp án đúng — bỏ chúng ra là tự tạo đáp án mà hệ thống bị chấm sai."""
    rows = [
        _listing(id=f"n{i}", district="Quận 8", property_type="private_house",
                 total_price_vnd=6_000_000_000 + i)
        for i in range(3)
    ]
    budget = [s for s in _hard_specs(rows) if s["query_type"] == "hard_budget"]

    assert len(budget) == 1
    assert len(budget[0]["expected_listing_ids"]) == 3
    assert budget[0]["expected_projects"] == []  # không tin nào thuộc dự án


def test_sft_draft_khong_lay_du_lieu_test_va_de_trong_output(db, imported, tmp_path):  # noqa: F811
    run_clean_pipeline(db, **imported)
    build_dataset_split(db, imported["tenant_id"], VERSION)
    listing_split = split_of_listing(db, imported["tenant_id"], VERSION)

    out = tmp_path / "sft.jsonl"
    stats = build_sft_draft(db, imported["tenant_id"], VERSION, out)

    samples = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(samples) == stats["samples"]
    for sample in samples:
        assert sample["split"] in ("train", "validation")
        assert listing_split[sample["listing_id"]] == sample["split"]
        assert sample["quality_status"] == "draft"
        assert sample["output"] == {"headline": "", "body": "", "cta": ""}
        assert sample["facts"] and all(f["source_url"] for f in sample["facts"])
        assert sample["channel"]["name"] and sample["persona"]["segment"]
