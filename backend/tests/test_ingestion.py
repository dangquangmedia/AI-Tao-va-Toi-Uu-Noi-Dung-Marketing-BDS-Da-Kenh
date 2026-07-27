import json

from sqlalchemy import func, select

from app.models import QuarantineRecord, SourceListing
from app.services.ingestion import run_databds_import

VALID_RECORDS = [
    {"source_listing_id": "111", "title": "Căn hộ 2PN Vinhomes", "area_m2": 72.0},
    {"source_listing_id": "222", "title": "Nhà phố Bình Thạnh", "area_m2": 90.0},
    {"source_listing_id": "333", "title": "Đất nền 66m2", "area_m2": 66.0},
]
MISSING_ID = {"title": "Tin thiếu source_listing_id"}
NO_SOURCE_ROW = {"source_listing_id": "999", "title": "Tin không có dòng provenance"}

CSV_HEADER = '"id","source","source_listing_id","canonical_url","first_seen_at","last_seen_at","last_detail_crawled_at","status","summary_hash","content_hash"\n'


def make_fixture(tmp_path, hash_suffix=""):
    """Tạo kho DataBDS giả lập trong tmp: 3 tin hợp lệ + 2 tin lỗi."""
    rows = []
    for i, r in enumerate(VALID_RECORDS, start=1):
        slid = r["source_listing_id"]
        rows.append(
            f'{i},batdongsan,"{slid}",https://example.com/tin-{slid},"2026-07-17","2026-07-24","2026-07-24",EXPIRED,,hash-{slid}{hash_suffix}\n'
        )
    (tmp_path / "source_listing_202607250000.csv").write_text(
        CSV_HEADER + "".join(rows), encoding="utf-8"
    )
    lines = [json.dumps(r, ensure_ascii=False) for r in VALID_RECORDS + [MISSING_ID, NO_SOURCE_ROW]]
    (tmp_path / "listings.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def test_import_lan_dau_va_quarantine(db, seeded, tmp_path):
    fixture = make_fixture(tmp_path)
    job = run_databds_import(
        db, tenant_id=seeded["t1"].id, created_by=seeded["admin1"].id, databds_dir=fixture
    )
    assert job.status == "done"
    assert job.total_read == 5
    assert job.inserted == 3
    assert job.quarantined == 2
    assert job.error_summary == {"missing_source_listing_id": 1, "no_source_row": 1}

    # Raw zone giữ nguyên văn bản ghi
    listing = db.scalar(select(SourceListing).where(SourceListing.source_listing_id == "111"))
    assert listing.raw["title"] == "Căn hộ 2PN Vinhomes"
    assert listing.canonical_url == "https://example.com/tin-111"
    assert listing.content_hash == "hash-111"


def test_chay_lai_cung_batch_khong_sinh_duplicate(db, seeded, tmp_path):
    fixture = make_fixture(tmp_path)
    args = dict(tenant_id=seeded["t1"].id, created_by=seeded["admin1"].id, databds_dir=fixture)

    job1 = run_databds_import(db, **args)
    job2 = run_databds_import(db, **args)

    assert job1.inserted == 3
    assert job2.inserted == 0
    assert job2.unchanged == 3

    total = db.scalar(select(func.count()).select_from(SourceListing))
    assert total == 3  # không duplicate


def test_content_hash_doi_thi_update_khong_them_dong(db, seeded, tmp_path):
    fixture = make_fixture(tmp_path)
    args = dict(tenant_id=seeded["t1"].id, created_by=seeded["admin1"].id, databds_dir=fixture)
    run_databds_import(db, **args)

    make_fixture(tmp_path, hash_suffix="-v2")  # nguồn thay đổi nội dung
    job2 = run_databds_import(db, **args)

    assert job2.updated == 3
    assert job2.inserted == 0
    assert db.scalar(select(func.count()).select_from(SourceListing)) == 3


def test_tenant_isolation_trong_raw_zone(db, seeded, tmp_path):
    fixture = make_fixture(tmp_path)
    run_databds_import(
        db, tenant_id=seeded["t1"].id, created_by=seeded["admin1"].id, databds_dir=fixture
    )
    n_t2 = db.scalar(
        select(func.count())
        .select_from(SourceListing)
        .where(SourceListing.tenant_id == seeded["t2"].id)
    )
    assert n_t2 == 0

    # Cùng batch import cho tenant 2 vẫn được (khóa unique theo tenant)
    job = run_databds_import(
        db, tenant_id=seeded["t2"].id, created_by=seeded["admin2"].id, databds_dir=fixture
    )
    assert job.inserted == 3


def test_gioi_han_limit(db, seeded, tmp_path):
    fixture = make_fixture(tmp_path)
    job = run_databds_import(
        db, tenant_id=seeded["t1"].id, created_by=seeded["admin1"].id, databds_dir=fixture, limit=2
    )
    assert job.total_read == 2
    assert job.inserted == 2
