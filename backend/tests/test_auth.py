from tests.conftest import login


def test_login_dung_mat_khau(client, seeded):
    headers = login(client, "admin@mot.vn")
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "admin@mot.vn"
    assert me.json()["role"] == "admin"


def test_login_sai_mat_khau(client, seeded):
    res = client.post("/api/auth/login", json={"email": "admin@mot.vn", "password": "sai-roi"})
    assert res.status_code == 401


def test_chua_dang_nhap_bi_chan(client, seeded):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/projects").status_code == 401


def test_rbac_reviewer_khong_duoc_tao_project(client, seeded):
    headers = login(client, "reviewer@mot.vn")
    res = client.post(
        "/api/projects", json={"name": "Dự án X", "slug": "du-an-x"}, headers=headers
    )
    assert res.status_code == 403


def test_rbac_marketer_duoc_tao_nhung_khong_duoc_xoa(client, seeded):
    headers = login(client, "marketer@mot.vn")
    created = client.post(
        "/api/projects", json={"name": "Dự án Y", "slug": "du-an-y"}, headers=headers
    )
    assert created.status_code == 201
    res = client.delete(f"/api/projects/{created.json()['id']}", headers=headers)
    assert res.status_code == 403


def test_rbac_admin_duoc_xoa(client, seeded):
    admin = login(client, "admin@mot.vn")
    created = client.post(
        "/api/projects", json={"name": "Dự án Z", "slug": "du-an-z"}, headers=admin
    )
    assert created.status_code == 201
    res = client.delete(f"/api/projects/{created.json()['id']}", headers=admin)
    assert res.status_code == 204
