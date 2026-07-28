"""Test luật re-parse D1 + chuẩn hóa D2 (Plan/02 §4).

Các ca test lấy trực tiếp từ dữ liệu thật trong DataBDS: giá viết kiểu
"5 tỷ 100", rác Sentry trong price_raw, project_name dính menu, số điện thoại
trong mô tả.
"""

import pytest

from app.services.reparse import (
    assign_tier,
    extract_amenities,
    extract_building_code,
    extract_legal,
    extract_location,
    extract_project_slug,
    extract_ward,
    normalize_text,
    parse_price,
    project_confidence,
    reparse_record,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Đất 4m x 16m giá 5 tỷ 100", 5_100_000_000),  # 100 = trăm triệu
        ("Bán nhanh 2PN giá 4.9 tỷ có sổ hồng", 4_900_000_000),
        ("Căn hộ 3PN giá 18 tỷ", 18_000_000_000),
        ("Nhà nhỏ giá 850 triệu", 850_000_000),
        ("Giá 4,7 tỷ, 100m²", 4_700_000_000),
        ("Bán căn 5 tỷ 1 thương lượng", 5_100_000_000),
    ],
)
def test_parse_price_tu_title(text, expected):
    assert parse_price(text, "")["total_price_vnd"] == expected


def test_khong_bat_nham_so_phong_ngu_thanh_gia():
    assert parse_price("Bán căn 3 tỷ 2 phòng ngủ đẹp", "")["total_price_vnd"] == 3_000_000_000


def test_nhieu_muc_gia_thi_khong_doan():
    """Tin bán nhiều căn: 1.7 tỷ / 2.1 tỷ / 2.65 tỷ → để trống, không chọn bừa."""
    title = "Căn hộ C Sky View. 1PN 53m2 từ 1.7 tỷ, 2PN 80m2 từ 2.1 tỷ, 3PN 100m2 từ 2.65 tỷ"
    result = parse_price(title, "")
    assert result["total_price_vnd"] is None
    assert result["price_confidence"] == "missing"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Chi 490 triệu vốn tự có sở hữu căn hộ 3PN", None),  # vốn tự có ≠ giá bán
        ("Chiết khấu 500 triệu, giá còn 4.9 tỷ", 4_900_000_000),
        ("Hỗ trợ vay 70%, giá 3 tỷ 500", 3_500_000_000),  # "giá" ngay trước số → vẫn nhận
        ("Bán căn 4,45 tỷ, tặng gói nội thất 1 tỷ", 4_450_000_000),
    ],
)
def test_loai_so_tien_khong_phai_gia_ban(text, expected):
    assert parse_price(text, "")["total_price_vnd"] == expected


def test_gia_tren_m2_va_bang_chung():
    result = parse_price("Đất mặt tiền, 99tr/m2", "")
    assert result["price_per_m2_vnd"] == 99_000_000
    assert "99tr/m2" in result["price_evidence"]


def test_price_confidence_parsed_khi_khop_gia_tri_crawler():
    result = parse_price("Bán căn 4.9 tỷ", "", raw_total=4_900_000_000)
    assert result["price_confidence"] == "parsed"
    assert parse_price("Bán căn 5 tỷ 100", "", raw_total=5_000_000_000)["price_confidence"] == "reparsed"


def test_normalize_go_rac_js_va_mask_sdt():
    raw = "Nhà đẹp 5 tỷ Sentry.onLoad(function () { Sentry.init({ environme"
    assert normalize_text(raw) == "Nhà đẹp 5 tỷ"
    assert "[SĐT đã ẩn]" in normalize_text("Liên hệ Nam Tư: 0772 011 234 xem nhà")
    assert "0772" not in normalize_text("Liên hệ 0772 011 234")


URL_CO_MA_SO = (
    "https://batdongsan.com.vn/ban-can-ho-chung-cu-duong-pham-van-nghi-"
    "phuong-tan-phong-9-grand-view/tin-pr123"
)
URL_KHONG_MA_SO = (
    "https://batdongsan.com.vn/ban-can-ho-chung-cu-phuong-nhan-chinh-"
    "the-diamond-residence/tin-pr456"
)


def test_extract_project_slug():
    assert extract_project_slug(URL_CO_MA_SO) == "grand-view"
    # Tên dự án kết thúc bằng số ("Riverside 90") lẫn với mã vùng → bỏ qua có chủ đích,
    # thà mất độ phủ còn hơn tạo entity giả; alias Tuần 3 sẽ vét nốt.
    assert (
        extract_project_slug(
            "https://batdongsan.com.vn/ban-can-ho-chung-cu-duong-nguyen-huu-canh-"
            "phuong-22-riverside-90/tin-pr1"
        )
        is None
    )
    # Không có mã vùng → không đoán ranh giới tên phường (độ phủ để dành cho alias Tuần 3)
    assert extract_project_slug(URL_KHONG_MA_SO) is None
    # Đuôi chỉ còn mã vùng → không có dự án
    assert (
        extract_project_slug("https://batdongsan.com.vn/ban-dat-duong-x-phuong-phuoc-my-49/tin-pr1")
        is None
    )
    assert extract_project_slug("https://batdongsan.com.vn/tin-le-pr1") is None


def test_extract_ward():
    assert extract_ward(URL_CO_MA_SO) == "tan-phong"
    assert extract_ward(URL_KHONG_MA_SO) == "nhan-chinh"
    assert extract_ward("https://batdongsan.com.vn/ban-dat-duong-x-phuong-phuoc-my-49/tin") == "phuoc-my"
    assert extract_ward("https://batdongsan.com.vn/ban-can-ho-phuong-12-saigon-royal/tin") == "12"
    # Tên phường chứa chữ "quan" không được cắt nhầm ở mốc quận
    assert extract_ward("https://batdongsan.com.vn/ban-can-ho-phuong-xuan-quan-the-fibonan/tin") == "xuan-quan"
    assert extract_ward("https://batdongsan.com.vn/tin-le-pr1") is None


def test_project_confidence_doi_chieu_voi_text():
    assert project_confidence("grand-view", "Bán căn hộ Grand View quận 7") == 0.95
    assert project_confidence("grand-view", "Bán căn hộ giá tốt") == 0.6


def test_extract_building_code_chi_nhan_ky_hieu():
    assert extract_building_code("Bán căn tòa S3 Vinhomes") == "S3"
    assert extract_building_code("Bán căn tòa CT3 dự án X") == "CT3"
    assert extract_building_code("Tòa nhà văn phòng cho thuê") is None
    assert extract_building_code("Toà chung cư mới") is None


def test_extract_legal_va_amenities():
    text = "Căn hộ có sổ hồng, gần công viên và hồ bơi, nội thất đầy đủ"
    assert dict(extract_legal(text)).keys() == {"so_hong"}
    assert set(dict(extract_amenities(text))) == {"cong_vien", "ho_boi", "noi_that"}
    assert extract_legal("Nhà đẹp giá tốt") == []


def test_extract_location():
    loc = extract_location("Nhà tại Huỳnh Tấn Phát, Tân Mỹ, Quận 7, TP HCM")
    assert loc == {"district": "Quận 7", "city": "TP. Hồ Chí Minh"}
    assert extract_location("Bán đất Phường Phước Mỹ, Quận Sơn Trà, Đà Nẵng") == {
        "district": "Quận Sơn Trà",
        "city": "Đà Nẵng",
    }
    assert extract_location("Bán nhà đẹp") == {"district": None, "city": None}


def test_assign_tier():
    assert assign_tier("apartment", "grand-view", 500) == "A"
    assert assign_tier("villa", None, 100) == "B"
    assert assign_tier("land", None, 900) == "C"
    assert assign_tier("apartment", None, 50) == "C"


def test_reparse_record_drop_pii_va_gan_flag():
    raw = {
        "title": "Bán căn 2PN Grand View giá 4.9 tỷ có sổ hồng",
        "description": "Căn hộ tòa S3, gần công viên. Liên hệ 0901 234 567. Quận 7, TP HCM",
        "property_type": "apartment",
        "bedrooms": 2,
        "area_m2": 72.0,
        "seller_display_name": "Nguyễn Văn A",
        "project_name": "rác menu điều hướng",
        "legal_status": "rác menu",
    }
    out = reparse_record(raw, URL_CO_MA_SO)

    assert out["project_slug"] == "grand-view"
    assert out["ward"] == "tan-phong"
    assert out["building_code"] == "S3"
    assert out["unit_type_key"] == "apartment-2pn"
    assert out["total_price_vnd"] == 4_900_000_000
    assert out["legal_facts"] == ["so_hong"]
    assert out["district"] == "Quận 7"
    assert out["tier"] == "A"
    assert "seller_display_name" not in out  # PII bị drop hoàn toàn
    assert "0901" not in out["description_clean"]
    assert out["field_flags"]["project"] == "from_url"
    assert out["field_flags"]["price"] == "from_title"


def test_khong_gan_nham_tinh_thanh_vi_trung_chuoi_con():
    """Bug thật phát hiện qua UI: 'cho thuê' từng bị nhận là Thừa Thiên Huế."""
    assert extract_location("Cho thuê căn hộ 2PN tại Thuận Giao")["city"] is None
    assert extract_location("Bán nhà tại thành phố Huế")["city"] == "Thừa Thiên Huế"
    assert extract_location("Chuyển nhượng gấp, thuê lại dài hạn")["city"] is None
