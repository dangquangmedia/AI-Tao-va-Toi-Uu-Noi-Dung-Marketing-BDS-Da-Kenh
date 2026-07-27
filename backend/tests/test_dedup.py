"""Test D3 — dedup theo content_hash và near-duplicate SimHash."""

from app.services.dedup import build_clusters, hamming, simhash

MO_TA = (
    "Bán căn hộ 2 phòng ngủ view sông, diện tích 72m2, nội thất đầy đủ, "
    "gần công viên và trường học, sổ hồng chính chủ, giá tốt nhất khu vực"
)
MO_TA_SUA_NHE = MO_TA.replace("giá tốt nhất khu vực", "giá tốt nhất khu này")
MO_TA_KHAC = (
    "Cho thuê kho xưởng 500m2 tại khu công nghiệp, đường container ra vào, "
    "điện 3 pha, phòng cháy chữa cháy đầy đủ, hợp đồng dài hạn"
)


def test_simhash_on_dinh_va_nhay_voi_noi_dung():
    from app.services.dedup import HAMMING_THRESHOLD

    assert simhash(MO_TA) == simhash(MO_TA)  # tất định
    assert hamming(simhash(MO_TA), simhash(MO_TA_SUA_NHE)) <= HAMMING_THRESHOLD
    assert hamming(simhash(MO_TA), simhash(MO_TA_KHAC)) > 2 * HAMMING_THRESHOLD


def _rec(key, text, content_hash=None, length=None):
    return {
        "key": key,
        "content_hash": content_hash or f"hash-{key}",
        "simhash": simhash(text),
        "description_len": length if length is not None else len(text),
    }


def test_trung_chinh_xac_theo_content_hash():
    records = [_rec("100", MO_TA, "same"), _rec("200", MO_TA_KHAC, "same")]
    clusters = build_clusters(records)
    assert clusters["100"]["cluster_id"] == clusters["200"]["cluster_id"]


def test_gan_trung_gom_cung_cum_va_chon_dai_dien_dai_nhat():
    records = [
        _rec("300", MO_TA_SUA_NHE, length=500),  # mô tả đầy đủ hơn → làm đại diện
        _rec("100", MO_TA, length=120),
        _rec("200", MO_TA_KHAC),
    ]
    clusters = build_clusters(records)
    assert clusters["100"]["cluster_id"] == clusters["300"]["cluster_id"] == "100"
    assert clusters["200"]["cluster_id"] != clusters["100"]["cluster_id"]
    assert clusters["300"]["is_representative"] is True
    assert clusters["100"]["is_representative"] is False
    assert clusters["100"]["cluster_size"] == 2


def test_cum_khong_phu_thuoc_thu_tu_dau_vao():
    records = [_rec("300", MO_TA_SUA_NHE), _rec("100", MO_TA), _rec("200", MO_TA_KHAC)]
    assert build_clusters(records) == build_clusters(list(reversed(records)))
