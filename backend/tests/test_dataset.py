"""Test chia tập chống leakage, gold query và SFT draft (Tuần 3)."""

import json

from sqlalchemy import select

from app.models import DatasetSplit, RetrievalQuery
from app.services.dataset import (
    SPLIT_RATIOS,
    assign_split,
    build_dataset_split,
    leakage_audit,
    split_of_listing,
    split_report,
)
from app.services.gold_queries import generate_gold_queries
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
