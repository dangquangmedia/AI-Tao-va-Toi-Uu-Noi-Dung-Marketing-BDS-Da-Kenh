"""Test vòng duyệt nội dung: version, phân quyền, chấm lại claim, xuất bản (Tuần 5).

Đây là hàng rào cuối trước khi nội dung do model sinh ra đi ra ngoài, nên test tập trung
vào các quy tắc *chặn*: không tự duyệt, không từ chối suông, không xuất bản khi chưa duyệt,
không ghi đè bản đã có.
"""

import pytest

from app.models import ContentItem, ContentVersion
from app.services import content as content_service
from app.services.generation import run_generation
from tests.conftest import login
from tests.test_generation import indexed  # noqa: F401 — fixture dùng lại
from tests.test_pipeline import databds, imported  # noqa: F401


@pytest.fixture()
def generation(db, indexed):  # noqa: F811
    return run_generation(
        db,
        tenant_id=indexed["tenant_id"],
        created_by=indexed["created_by"],
        brief="Giới thiệu căn hộ 2 phòng ngủ tại Grand View",
        channel="facebook",
        persona="young_family",
        config="B",
        project_slug="grand-view",
    )


@pytest.fixture()
def item(db, indexed, generation):  # noqa: F811
    created, _ = content_service.create_from_generation(
        db, indexed["tenant_id"], indexed["created_by"], generation
    )
    return created


def test_tao_tu_ban_sinh_giu_nguyen_vet_model(db, item, generation):
    version = content_service.current_version(db, item)

    assert item.status == "draft" and item.current_version == 1
    assert version.generation_id == generation.id
    assert version.config == "B" and version.model_name == generation.model_name
    assert version.edited_by_human is False
    assert version.body == generation.body


def test_sua_tay_tao_ban_moi_va_khong_dong_ban_cu(db, indexed, item):  # noqa: F811
    goc = content_service.current_version(db, item).body

    content_service.add_version(
        db, indexed["tenant_id"], indexed["created_by"], item, "Tiêu đề mới", "Thân bài đã sửa", "CTA"
    )

    versions = content_service.versions(db, item)
    assert [v.version_no for v in versions] == [1, 2]
    assert versions[0].body == goc, "bản cũ phải giữ nguyên"
    assert versions[1].edited_by_human is True
    assert item.current_version == 2


def test_sua_tay_bi_cham_lai_claim(db, indexed, item):  # noqa: F811
    version = content_service.add_version(
        db,
        indexed["tenant_id"],
        indexed["created_by"],
        item,
        "Căn hộ cao cấp",
        "Căn hộ có diện tích 999 m2 và giá 123 tỷ, hoàn toàn không có trong dữ kiện.",
        "Liên hệ ngay",
    )

    # Người viết thêm số bịa cũng phải bị bắt như model bịa
    assert version.metrics["unsupported_claim_rate"] > 0
    assert any(claim["status"] == "unsupported" for claim in version.claims)


def test_luong_gui_duyet_va_duyet(db, seeded, indexed, item):  # noqa: F811
    content_service.submit(db, item)
    assert item.status == "in_review"

    version = content_service.review(db, item, seeded["reviewer1"], approve=True, note="Đạt")

    assert version.status == "approved" and item.status == "approved"
    assert version.reviewed_by == seeded["reviewer1"].id and version.reviewed_at is not None


def test_nguoi_viet_khong_tu_duyet_bai_minh(db, seeded, indexed, item):  # noqa: F811
    content_service.submit(db, item)
    # created_by của version là admin1 (indexed dùng admin1) → admin được phép, reviewer thì không
    marketer = seeded["marketer1"]
    version = content_service.current_version(db, item)
    version.created_by = marketer.id
    marketer.role = "reviewer"  # giả lập người vừa viết vừa có quyền duyệt
    db.commit()

    with pytest.raises(content_service.ContentError, match="không tự duyệt"):
        content_service.review(db, item, marketer, approve=True)


def test_tu_choi_phai_kem_ly_do(db, seeded, indexed, item):  # noqa: F811
    content_service.submit(db, item)

    with pytest.raises(content_service.ContentError, match="kèm lý do"):
        content_service.review(db, item, seeded["reviewer1"], approve=False, note="  ")

    version = content_service.review(
        db, item, seeded["reviewer1"], approve=False, note="Thiếu thông tin pháp lý"
    )
    assert version.status == "rejected" and item.status == "rejected"


def test_sua_sau_khi_bi_tu_choi_thi_phai_gui_duyet_lai(db, seeded, indexed, item):  # noqa: F811
    content_service.submit(db, item)
    content_service.review(db, item, seeded["reviewer1"], approve=False, note="Sửa lại tiêu đề")

    content_service.add_version(
        db, indexed["tenant_id"], indexed["created_by"], item, "Tiêu đề khác", "Thân bài mới", ""
    )

    assert item.status == "draft", "sửa xong phải quay lại nháp, không tự vào hàng chờ duyệt"


def test_khong_sua_duoc_noi_dung_da_duyet(db, seeded, indexed, item):  # noqa: F811
    content_service.submit(db, item)
    content_service.review(db, item, seeded["reviewer1"], approve=True)

    with pytest.raises(content_service.ContentError, match="đã duyệt"):
        content_service.add_version(
            db, indexed["tenant_id"], indexed["created_by"], item, "x", "y", "z"
        )


def test_xuat_ban_kem_khoi_truy_vet(db, seeded, indexed, item):  # noqa: F811
    content_service.submit(db, item)
    version = content_service.review(db, item, seeded["reviewer1"], approve=True)

    markdown = content_service.export_markdown(item, version)

    assert version.model_name in markdown
    assert "Claim chưa có căn cứ" in markdown
    assert f"phiên bản {version.version_no}" in markdown


# --- API + phân quyền ------------------------------------------------------


def test_api_marketer_gui_duyet_reviewer_duyet(client, db, seeded, generation):
    marketer = login(client, "marketer@mot.vn")
    reviewer = login(client, "reviewer@mot.vn")

    created = client.post(
        "/api/content", json={"generation_id": generation.id}, headers=marketer
    )
    assert created.status_code == 201
    item_id = created.json()["id"]

    assert client.post(f"/api/content/{item_id}/submit", headers=marketer).status_code == 200
    approved = client.post(
        f"/api/content/{item_id}/review", json={"approve": True, "note": "Đạt"}, headers=reviewer
    )
    assert approved.status_code == 200 and approved.json()["status"] == "approved"

    export = client.get(f"/api/content/{item_id}/export", headers=marketer)
    assert export.status_code == 200 and "Claim chưa có căn cứ" in export.text


def test_api_reviewer_khong_duoc_viet_marketer_khong_duoc_duyet(client, db, seeded, generation):
    marketer = login(client, "marketer@mot.vn")
    reviewer = login(client, "reviewer@mot.vn")

    assert (
        client.post("/api/content", json={"generation_id": generation.id}, headers=reviewer).status_code
        == 403
    )
    item_id = client.post(
        "/api/content", json={"generation_id": generation.id}, headers=marketer
    ).json()["id"]
    client.post(f"/api/content/{item_id}/submit", headers=marketer)

    assert (
        client.post(
            f"/api/content/{item_id}/review", json={"approve": True}, headers=marketer
        ).status_code
        == 403
    )


def test_api_khong_xuat_ban_duoc_khi_chua_duyet(client, db, seeded, generation):
    marketer = login(client, "marketer@mot.vn")
    item_id = client.post(
        "/api/content", json={"generation_id": generation.id}, headers=marketer
    ).json()["id"]

    response = client.get(f"/api/content/{item_id}/export", headers=marketer)

    assert response.status_code == 409
    assert "đã duyệt" in response.json()["detail"]


def test_api_tenant_khac_khong_thay_noi_dung(client, db, seeded, generation):
    client.post(
        "/api/content", json={"generation_id": generation.id}, headers=login(client, "marketer@mot.vn")
    )

    assert client.get("/api/content", headers=login(client, "admin@hai.vn")).json() == []
    assert len(client.get("/api/content", headers=login(client, "admin@mot.vn")).json()) == 1
