"""Test API tầng làm sạch/graph: RBAC, tenant isolation, dữ liệu trả về."""

from app.services.pipeline import run_clean_pipeline
from tests.conftest import login
from tests.test_pipeline import databds, imported  # noqa: F401 — fixture dùng lại


def test_chay_pipeline_chi_danh_cho_admin(client, db, imported):  # noqa: F811
    assert client.post("/api/pipeline/run", json={}, headers=login(client, "marketer@mot.vn")).status_code == 403
    assert client.post("/api/pipeline/run", json={}, headers=login(client, "reviewer@mot.vn")).status_code == 403

    res = client.post("/api/pipeline/run", json={}, headers=login(client, "admin@mot.vn"))
    assert res.status_code == 200
    body = res.json()
    assert body["job_type"] == "clean_pipeline"
    assert body["inserted"] == 3
    assert body["stats"]["entities"] > 0


def test_data_quality_va_quarantine(client, db, imported):  # noqa: F811
    admin = login(client, "admin@mot.vn")
    client.post("/api/pipeline/run", json={}, headers=admin)

    report = client.get("/api/pipeline/data-quality", headers=admin).json()
    assert report["clean"]["total"] == 3
    assert report["clean"]["by_tier"]["A"] == 2
    assert report["clean"]["field_coverage"]["ward"]["pct"] == 100.0
    assert report["facts"]["total"] > 0
    assert report["graph"]["top_projects"][0]["key"] == "grand-view"

    assert client.get("/api/pipeline/quarantine", headers=admin).json() == []
    assert client.get("/api/pipeline/jobs", headers=admin).json()[0]["job_type"] == "clean_pipeline"


def test_listings_va_facts_theo_tenant(client, db, seeded, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    admin1 = login(client, "admin@mot.vn")
    admin2 = login(client, "admin@hai.vn")

    listings = client.get("/api/listings?project_slug=grand-view", headers=admin1).json()
    assert len(listings) == 2
    assert {row["tier"] for row in listings} == {"A"}

    facts = client.get(f"/api/listings/{listings[0]['id']}/facts", headers=admin1).json()
    assert facts
    assert all(f["source_url"] and f["evidence"] for f in facts)

    # Tenant khác: không thấy dữ liệu, truy cập trực tiếp bằng ID → 404
    assert client.get("/api/listings", headers=admin2).json() == []
    assert client.get(f"/api/listings/{listings[0]['id']}", headers=admin2).status_code == 404
    assert client.get(f"/api/listings/{listings[0]['id']}/facts", headers=admin2).status_code == 404


def test_graph_api(client, db, imported):  # noqa: F811
    admin = login(client, "admin@mot.vn")
    client.post("/api/pipeline/run", json={}, headers=admin)

    projects = client.get("/api/graph/entities?entity_type=Project", headers=admin).json()
    assert projects[0]["key"] == "grand-view"
    # Lọc dự án đã nhận diện được tòa → đúng tập có đường 2 hop
    co_toa = client.get(
        "/api/graph/entities?entity_type=Project&with_building=true", headers=admin
    ).json()
    assert [p["key"] for p in co_toa] == ["grand-view"]
    assert client.get("/api/graph/entities?entity_type=Ward&with_building=true", headers=admin).json() == []

    paths = client.get("/api/graph/projects/grand-view/paths", headers=admin).json()
    assert paths["n_via_building"] == 2
    assert paths["paths"][0]["nodes"][1]["type"] == "Building"

    neighbors = client.get(
        f"/api/graph/entities/{projects[0]['id']}/neighbors?depth=2", headers=admin
    ).json()
    assert neighbors["entity"]["key"] == "grand-view"
    assert neighbors["paths"]

    assert client.get("/api/graph/projects/khong-co/paths", headers=admin).status_code == 404
    assert client.get("/api/graph/entities/khong-co-id/neighbors", headers=admin).status_code == 404


def test_can_dang_nhap_moi_xem_duoc(client, db, imported):  # noqa: F811
    for path in ("/api/pipeline/data-quality", "/api/listings", "/api/graph/entities"):
        assert client.get(path).status_code == 401
