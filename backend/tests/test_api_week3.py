"""Test API Tuần 3: search, index, dataset summary, fact editor."""

from sqlalchemy import select

from app.models import Fact
from app.services.dataset import build_dataset_split
from app.services.gold_queries import generate_gold_queries
from app.services.indexing import run_index_build
from app.services.pipeline import run_clean_pipeline
from tests.conftest import login
from tests.test_pipeline import databds, imported  # noqa: F401 — fixture dùng lại

# Chọn version mà hash đưa dự án của fixture vào split test → chắc chắn có gold query
VERSION = "ds_gold_1"


def _ready(db, imported):
    run_clean_pipeline(db, **imported)
    run_index_build(db, tenant_id=imported["tenant_id"], created_by=imported["created_by"])
    build_dataset_split(db, imported["tenant_id"], VERSION)
    generate_gold_queries(db, imported["tenant_id"], VERSION)


def test_search_api_cac_che_do(client, db, imported):  # noqa: F811
    _ready(db, imported)
    headers = login(client, "marketer@mot.vn")

    for mode in ("r1-fts", "r1-vector", "r1-hybrid", "r2-graph"):
        res = client.get(f"/api/search?q=Dự án Grand View&mode={mode}&k=5", headers=headers)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["mode"] == mode
        assert all(item["source_url"] for item in body["results"])

    assert client.get("/api/search?q=abc&mode=khong-co", headers=headers).status_code == 400
    assert client.get("/api/search?q=abc").status_code == 401


def test_index_api_chi_admin(client, db, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    assert client.post("/api/search/index", json={}, headers=login(client, "reviewer@mot.vn")).status_code == 403

    res = client.post("/api/search/index", json={}, headers=login(client, "admin@mot.vn"))
    assert res.status_code == 200
    assert res.json()["job_type"] == "index_build"
    assert client.get("/api/search/stats", headers=login(client, "admin@mot.vn")).json()["chunks"] > 0


def test_dataset_summary_va_gold_queries(client, db, imported):  # noqa: F811
    _ready(db, imported)
    headers = login(client, "admin@mot.vn")

    summary = client.get(f"/api/dataset/summary?version={VERSION}", headers=headers).json()
    assert summary["dataset_version"] == VERSION
    assert summary["leakage"]["passed"] is True
    assert summary["gold_queries"]["total"] > 0
    assert summary["gold_queries"]["total"] == summary["gold_queries"]["needs_review"]

    queries = client.get(f"/api/dataset/queries?version={VERSION}&limit=5", headers=headers).json()
    assert queries and all(q["split"] == "test" for q in queries)
    assert all(q["project_slug"] == "grand-view" for q in queries)


def test_fact_editor_giu_gia_tri_may_sinh(client, db, imported):  # noqa: F811
    _ready(db, imported)
    headers = login(client, "reviewer@mot.vn")

    pending = client.get("/api/dataset/facts/review?limit=5", headers=headers).json()
    assert pending, "phải có fact cần soát (amenity/giá độ tin thấp)"
    fact_id = pending[0]["id"]
    goc = pending[0]["value_text"]

    res = client.patch(
        f"/api/dataset/facts/{fact_id}",
        json={"value_text": "gia tri da sua", "needs_review": False, "note": "soát tay"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["value_text"] == "gia tri da sua"
    assert body["original_value_text"] == goc  # giữ lại giá trị máy sinh
    assert body["needs_review"] is False
    assert body["confidence"] == 1.0

    fact = db.get(Fact, fact_id)
    assert fact.reviewed_by and fact.reviewed_at and fact.review_note == "soát tay"


def test_fact_cua_tenant_khac_tra_404(client, db, seeded, imported):  # noqa: F811
    _ready(db, imported)
    fact = db.scalars(select(Fact).limit(1)).first()
    res = client.patch(
        f"/api/dataset/facts/{fact.id}",
        json={"needs_review": False},
        headers=login(client, "admin@hai.vn"),
    )
    assert res.status_code == 404
