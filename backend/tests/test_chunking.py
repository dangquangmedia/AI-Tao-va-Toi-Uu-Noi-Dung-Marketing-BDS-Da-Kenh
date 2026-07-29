"""Test cắt chunk và thẻ dữ kiện (Tuần 3)."""

from types import SimpleNamespace

from app.services.chunking import (
    CHUNK_CHARS,
    build_chunks,
    content_hash,
    context_header,
    render_fact_card,
    split_description,
)


def _listing(**kwargs):
    base = dict(
        project_slug="grand-view",
        project_name="Grand View",
        building_code="S3",
        ward="tan-phong",
        district="Quận 7",
        city="TP. Hồ Chí Minh",
        property_type="apartment",
        bedrooms=2,
        title_clean="Bán căn 2PN Grand View giá 4.9 tỷ",
        description_clean="Căn hộ tầng cao, view sông. Nội thất đầy đủ.",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _fact(predicate, value_text, value_num=None):
    return SimpleNamespace(predicate=predicate, value_text=value_text, value_num=value_num)


def test_context_header_gom_du_boi_canh():
    header = context_header(_listing())
    assert "Grand View" in header and "S3" in header and "Quận 7" in header


def test_fact_card_chi_chua_du_kien_va_dinh_dang_gia():
    card = render_fact_card(
        _listing(),
        [
            _fact("total_price_vnd", "4900000000", 4_900_000_000),
            _fact("area_m2", "72.0", 72.0),
            _fact("legal_status", "so_hong"),
            _fact("khong_biet", "bo qua"),
        ],
    )
    assert "Giá: 4.9 tỷ" in card
    assert "Diện tích: 72.0" in card
    assert "Pháp lý: sổ hồng" in card  # slug được đổi sang nhãn tiếng Việt (Tuần 4)
    assert "bo qua" not in card  # predicate lạ bị bỏ, không bịa nhãn


def test_split_description_giu_nguyen_doan_ngan():
    assert split_description("Căn hộ đẹp.") == ["Căn hộ đẹp."]
    assert split_description("") == []


def test_split_description_cat_va_chong_lan():
    sentence = "Căn hộ tầng cao view sông thoáng mát, nội thất đầy đủ, gần trường học. "
    parts = split_description(sentence * 20)
    assert len(parts) > 1
    assert all(len(p) <= CHUNK_CHARS + 200 for p in parts)
    # Phần chồng lấn: cuối chunk trước xuất hiện lại ở đầu chunk sau
    assert parts[0][-40:].split()[-1] in parts[1][:200]


def test_build_chunks_du_ba_loai_va_hash_on_dinh():
    listing = _listing()
    facts = [_fact("total_price_vnd", "4900000000", 4_900_000_000)]
    chunks = build_chunks(listing, facts)

    types = [c["chunk_type"] for c in chunks]
    assert "facts" in types and "title" in types and "description" in types
    assert all(c["token_count"] > 0 for c in chunks)
    assert build_chunks(listing, facts) == chunks  # tất định
    assert chunks[0]["content_hash"] == content_hash(chunks[0]["text"])


def test_chunk_mo_ta_luon_mang_theo_boi_canh_du_an():
    chunks = build_chunks(_listing(), [])
    description = next(c for c in chunks if c["chunk_type"] == "description")
    assert description["text"].startswith("Dự án Grand View")
