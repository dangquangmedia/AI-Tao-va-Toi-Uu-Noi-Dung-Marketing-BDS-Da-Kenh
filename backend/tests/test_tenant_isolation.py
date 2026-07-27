from tests.conftest import login


def test_tenant_khac_khong_thay_project(client, seeded):
    """Dự án của tenant 1 không được lộ cho tenant 2 — kể cả khi biết ID."""
    admin1 = login(client, "admin@mot.vn")
    admin2 = login(client, "admin@hai.vn")

    created = client.post(
        "/api/projects", json={"name": "Bí mật T1", "slug": "bi-mat-t1"}, headers=admin1
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    # List của tenant 2 rỗng
    listing = client.get("/api/projects", headers=admin2)
    assert listing.status_code == 200
    assert listing.json() == []

    # Truy cập trực tiếp bằng ID → 404 (không lộ sự tồn tại)
    assert client.get(f"/api/projects/{project_id}", headers=admin2).status_code == 404
    assert (
        client.patch(
            f"/api/projects/{project_id}", json={"name": "hack"}, headers=admin2
        ).status_code
        == 404
    )
    assert client.delete(f"/api/projects/{project_id}", headers=admin2).status_code == 404

    # Tenant 1 vẫn thấy bình thường
    assert client.get(f"/api/projects/{project_id}", headers=admin1).status_code == 200


def test_slug_trung_trong_cung_tenant_bi_chan_nhung_khac_tenant_thi_duoc(client, seeded):
    admin1 = login(client, "admin@mot.vn")
    admin2 = login(client, "admin@hai.vn")
    body = {"name": "Trùng slug", "slug": "trung-slug"}
    assert client.post("/api/projects", json=body, headers=admin1).status_code == 201
    assert client.post("/api/projects", json=body, headers=admin1).status_code == 409
    assert client.post("/api/projects", json=body, headers=admin2).status_code == 201
