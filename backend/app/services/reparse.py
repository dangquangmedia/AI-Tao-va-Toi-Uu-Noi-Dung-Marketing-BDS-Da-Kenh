"""D1 + D2 — luật re-parse và chuẩn hóa cho kho DataBDS (Plan/02 §4).

Bối cảnh: parser crawler bắt nhầm vùng DOM nên `project_name`, `legal_status`,
`price_raw`, `address_raw` dính rác menu/JS. Ba nguồn còn sạch 100% là `title`,
`description` và `canonical_url` — module này khôi phục lại các trường hỏng từ đó.

Nguyên tắc bắt buộc:
- Không suy diễn: không khôi phục được thì trả None + flag, tuyệt đối không đoán.
- Mọi giá trị khôi phục đều kèm **trích đoạn bằng chứng** để gắn provenance ở D4.
- Hàm thuần (không chạm DB) để test được độc lập và tái lập bằng `PARSER_VERSION`.
"""

import html
import re
import unicodedata

# v2 (Tuần 4): thêm luật chặn giá trị phi lý của crawler (số phòng, diện tích).
# Đổi version buộc pipeline re-parse lại toàn bộ thay vì giữ dữ liệu cũ.
PARSER_VERSION = "reparse_v2"

# --- D2: chuẩn hóa văn bản ------------------------------------------------

# Rác JS/analytics mà parser cũ nuốt vào các trường text
_BOILERPLATE = [
    re.compile(r"Sentry\.onLoad.*", re.S),
    re.compile(r"Sentry\.init.*", re.S),
    re.compile(r"window\.__\w+.*", re.S),
    re.compile(r"function\s*\(\s*\)\s*\{.*", re.S),
]
# Số điện thoại VN viết đủ kiểu: "0772 011 234", "077.201.1234", "+84 901234567"
_PHONE = re.compile(r"(?<!\d)(?:\+84|0)[\d.\- ]{7,14}")
_PHONE_MIN_DIGITS, _PHONE_MAX_DIGITS = 9, 11
_WS = re.compile(r"[ \t ]+")


def strip_boilerplate(text: str) -> str:
    for pat in _BOILERPLATE:
        text = pat.sub(" ", text)
    return text


def _mask_one(match: re.Match) -> str:
    chunk = match.group(0)
    core = chunk.rstrip(" .-")
    digits = re.sub(r"\D", "", core)
    if _PHONE_MIN_DIGITS <= len(digits) <= _PHONE_MAX_DIGITS:
        return "[SĐT đã ẩn]" + chunk[len(core) :]
    return chunk


def mask_pii(text: str) -> str:
    """Ẩn số điện thoại trong mô tả (Plan/02 §9 — không lưu PII)."""
    return _PHONE.sub(_mask_one, text)


def normalize_text(text: str | None) -> str:
    """NFC + gỡ HTML entity + bỏ boilerplate + gộp khoảng trắng + mask PII."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", html.unescape(str(text)))
    text = strip_boilerplate(text)
    text = mask_pii(text)
    text = _WS.sub(" ", text.replace("\r", "\n"))
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def deaccent(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower()).replace("đ", "d")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _evidence(text: str, start: int, end: int, pad: int = 40) -> str:
    return text[max(0, start - pad) : min(len(text), end + pad)].strip()


# --- D1.1: giá -------------------------------------------------------------

# "5 tỷ 100" = 5,1 tỷ · "4.9 tỷ" · "4ty9" · phần đuôi không được là m²/PN/tầng…
_TY = re.compile(
    r"(\d{1,4}(?:[.,]\d{1,3})?)\s*(?:tỷ|tỉ|ty)"
    r"(?:\s*(\d{1,3})(?!\s*(?:m|tr|%|,|\.|\d|phòng|pn|ngủ|wc|tầng|lầu|triệu|nghìn|tỷ|tỉ)))?",
    re.IGNORECASE,
)
_TRIEU = re.compile(r"(\d{2,5}(?:[.,]\d{1,2})?)\s*(?:triệu|tr)\b(?!\s*/)", re.IGNORECASE)
_PER_M2 = re.compile(r"(\d{1,4}(?:[.,]\d{1,2})?)\s*(?:triệu|tr)\s*/\s*m", re.IGNORECASE)

MIN_TOTAL_VND = 100_000_000
MAX_TOTAL_VND = 1_000_000_000_000
MIN_PER_M2_VND = 1_000_000
MAX_PER_M2_VND = 1_000_000_000


def _num(token: str) -> float:
    return float(token.replace(",", "."))


def _ty_to_vnd(base: str, tail: str | None) -> float:
    """'5 tỷ 100' → 5,1 tỷ (100 = trăm triệu); '5 tỷ 1' → 5,1 tỷ."""
    value = _num(base) * 1_000_000_000
    if tail and "." not in base and "," not in base:
        scale = {1: 100, 2: 10, 3: 1}[len(tail)]
        value += int(tail) * scale * 1_000_000
    return value


# Số tiền đứng sau các từ này không phải giá bán (vốn tự có, chiết khấu, tiền cọc…)
_NOT_PRICE_CONTEXT = (
    "vốn", "cọc", "trả trước", "vay", "hỗ trợ", "chiết khấu", " ck ", "thuế",
    "phí", "lãi", "tặng", "giảm", "tiết kiệm", "lợi nhuận", "doanh thu",
)
# Số tiền đứng TRƯỚC các từ này cũng không phải giá bán ("490 triệu vốn tự có")
_NOT_PRICE_SUFFIX = ("vốn", "cọc", "lợi nhuận", "lãi")
# Tín hiệu dương mạnh: ngay trước số là chữ "giá"/"bán"/"chỉ" → chắc chắn là giá bán
_PRICE_CONTEXT = ("giá", "bán", "chỉ")
_CONTEXT_WINDOW = 25
_NEAR_WINDOW = 10
_SUFFIX_WINDOW = 15


def _is_price_context(text: str, start: int, end: int) -> bool:
    if any(word in text[end : end + _SUFFIX_WINDOW].lower() for word in _NOT_PRICE_SUFFIX):
        return False
    if any(word in text[max(0, start - _NEAR_WINDOW) : start].lower() for word in _PRICE_CONTEXT):
        return True
    before = text[max(0, start - _CONTEXT_WINDOW) : start].lower()
    return not any(word in before for word in _NOT_PRICE_CONTEXT)


def _total_candidates(text: str) -> list[tuple[float, str]]:
    out: list[tuple[float, str]] = []
    for m in _TY.finditer(text):
        value = _ty_to_vnd(m.group(1), m.group(2))
        if MIN_TOTAL_VND <= value <= MAX_TOTAL_VND and _is_price_context(text, m.start(), m.end()):
            out.append((value, _evidence(text, m.start(), m.end())))
    if not out:  # chỉ xét "triệu" khi không có "tỷ" — tránh bắt nhầm "5 tỷ 100 triệu"
        for m in _TRIEU.finditer(text):
            value = _num(m.group(1)) * 1_000_000
            if MIN_TOTAL_VND <= value <= MAX_TOTAL_VND and _is_price_context(text, m.start(), m.end()):
                out.append((value, _evidence(text, m.start(), m.end())))
    return out


def _per_m2_candidates(text: str) -> list[tuple[float, str]]:
    out = []
    for m in _PER_M2.finditer(text):
        value = _num(m.group(1)) * 1_000_000
        if MIN_PER_M2_VND <= value <= MAX_PER_M2_VND:
            out.append((value, _evidence(text, m.start(), m.end())))
    return out


def _pick_unique(cands: list[tuple[float, str]]) -> tuple[float | None, str, bool]:
    """Trả (giá trị, bằng chứng, có mơ hồ không). Nhiều giá khác nhau → không chọn."""
    if not cands:
        return None, "", False
    distinct = {round(v) for v, _ in cands}
    if len(distinct) > 1:
        return None, "", True
    return cands[0][0], cands[0][1], False


def parse_price(title: str, description: str, raw_total: float | None = None) -> dict:
    """Khôi phục giá từ title (ưu tiên) rồi description.

    price_confidence: parsed (khớp giá trị parser gốc) | reparsed | missing.
    Nhiều mức giá khác nhau trong cùng tin (tin bán nhiều căn) → để None +
    flag `price_ambiguous`, không chọn bừa.
    """
    result: dict = {
        "total_price_vnd": None,
        "price_per_m2_vnd": None,
        "price_confidence": "missing",
        "price_evidence": "",
        "price_flag": "",
    }

    for source, text in (("title", title), ("description", description)):
        total, evidence, ambiguous = _pick_unique(_total_candidates(text))
        if ambiguous and not result["price_flag"]:
            result["price_flag"] = "price_ambiguous"
        if total is not None:
            result["total_price_vnd"] = total
            result["price_evidence"] = evidence
            result["price_flag"] = f"from_{source}"
            break

    per_m2, evidence_m2, _ = _pick_unique(_per_m2_candidates(f"{title} {description}"))
    if per_m2 is not None:
        result["price_per_m2_vnd"] = per_m2
        if result["total_price_vnd"] is None:
            result["price_evidence"] = evidence_m2

    if result["total_price_vnd"] is not None or result["price_per_m2_vnd"] is not None:
        matched = (
            raw_total is not None
            and result["total_price_vnd"] is not None
            and abs(raw_total - result["total_price_vnd"]) < 1_000_000
        )
        result["price_confidence"] = "parsed" if matched else "reparsed"
    return result


# --- D1.2: dự án từ URL ----------------------------------------------------

# Ưu tiên mốc phường/xã; chỉ khi không có mới dùng mốc quận/huyện — nếu không
# regex sẽ cắt nhầm ở tên phường có chữ "quan" (vd "xuan-quan").
_WARD_MARKER = re.compile(r"-(?:phuong|xa|thi-tran)-")
_DISTRICT_MARKER = re.compile(r"-(?:quan|huyen|thi-xa|thanh-pho)-")
_SLUG_STOPWORDS = {"nha", "dat", "ban", "cho", "thue", "can", "ho", "chung", "cu"}
_MAX_WARD_TOKENS = 2


def _url_tail(canonical_url: str) -> list[str]:
    """Phần đuôi segment địa chỉ, sau mốc phường/xã (hoặc quận/huyện)."""
    try:
        segment = canonical_url.split("/")[3]
    except IndexError:
        return []
    markers = list(_WARD_MARKER.finditer(segment)) or list(_DISTRICT_MARKER.finditer(segment))
    if not markers:
        return []
    return [t for t in segment[markers[-1].end() :].replace("_", "-").split("-") if t]


def extract_project_slug(canonical_url: str) -> str | None:
    """Lấy slug dự án từ segment địa chỉ của URL batdongsan.

    Cấu trúc: `ban-<loại>-duong-<đường>-phuong-<phường>-<mã vùng>-<slug dự án>`.
    Chỉ nhận phần **sau token số cuối cùng** (mã vùng) — luật ưu tiên độ chính xác:
    URL không có mã vùng (vd `...-phuong-nhan-chinh-the-diamond-residence`) bị bỏ qua
    thay vì đoán ranh giới tên phường. Nâng độ phủ bằng alias/dictionary ở Tuần 3.
    """
    tokens = _url_tail(canonical_url)
    digits = [i for i, t in enumerate(tokens) if t.isdigit()]
    if not digits:
        return None
    rest = [t for t in tokens[digits[-1] + 1 :]]
    if not rest or all(t in _SLUG_STOPWORDS for t in rest):
        return None
    return "-".join(rest)


def extract_ward(canonical_url: str) -> str | None:
    """Tên phường/xã từ URL — có ở 100% tin nên là mốc địa lý tối thiểu của contract."""
    tokens = _url_tail(canonical_url)
    if not tokens:
        return None
    digits = [i for i, t in enumerate(tokens) if t.isdigit()]
    if digits and digits[0] == 0:
        ward = tokens[:1]  # "Phường 12"
    elif digits:
        ward = tokens[: digits[0]]  # tên phường đứng trước mã vùng
    else:
        ward = tokens[:_MAX_WARD_TOKENS]
    ward = [t for t in ward if t not in _SLUG_STOPWORDS]
    return "-".join(ward) or None


def project_confidence(slug: str, text: str) -> float:
    """Đối chiếu slug với title+description: ≥60% token xuất hiện → 0.95, ngược lại 0.6."""
    tokens = [t for t in slug.split("-") if len(t) > 1]
    if not tokens:
        return 0.0
    flat = deaccent(text)
    hit = sum(1 for t in tokens if t in flat)
    return 0.95 if hit / len(tokens) >= 0.6 else 0.6


def slug_to_name(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.split("-"))


# --- D1.3: tòa/block và loại căn ------------------------------------------

_BUILDING = re.compile(r"\b(?:tòa|toà|block|tháp|tower)\s+([A-Za-z]{0,3}\d{1,2}|[A-Ha-h])\b")
_BUILDING_STOP = {"nha", "chung", "can", "van", "cao", "the", "ho"}


def extract_building_code(text: str) -> str | None:
    """Chỉ nhận mã tòa dạng ký hiệu (S3, CT3, OC3, A, B2…), bỏ 'tòa nhà', 'tòa chung cư'."""
    for m in _BUILDING.finditer(text):
        code = m.group(1).upper()
        if deaccent(code) in _BUILDING_STOP:
            continue
        return code
    return None


def unit_type_key(property_type: str, bedrooms: int | None) -> str | None:
    if not property_type:
        return None
    return f"{property_type}-{bedrooms}pn" if bedrooms else property_type


# --- D1.4: pháp lý và tiện ích --------------------------------------------

LEGAL_KEYWORDS = {
    "sổ hồng": "so_hong",
    "sổ đỏ": "so_do",
    "sổ riêng": "so_rieng",
    "sổ hồng riêng": "so_hong_rieng",
    "hđmb": "hdmb",
    "hợp đồng mua bán": "hdmb",
    "công chứng": "cong_chung",
    "vi bằng": "vi_bang",
    "giấy tờ tay": "giay_to_tay",
    "chính chủ": "chinh_chu",
}

AMENITY_KEYWORDS = {
    "hồ bơi": "ho_boi",
    "bể bơi": "ho_boi",
    "gym": "gym",
    "công viên": "cong_vien",
    "trường học": "truong_hoc",
    "siêu thị": "sieu_thi",
    "trung tâm thương mại": "ttmt",
    "thang máy": "thang_may",
    "an ninh": "an_ninh",
    "bãi đỗ xe": "bai_do_xe",
    "hầm để xe": "ham_de_xe",
    "sân vườn": "san_vuon",
    "ban công": "ban_cong",
    "view sông": "view_song",
    "nội thất": "noi_that",
}


def _match_keywords(text: str, mapping: dict[str, str]) -> list[tuple[str, str]]:
    """Trả danh sách (giá trị chuẩn hóa, trích đoạn) theo thứ tự ổn định."""
    lowered = text.lower()
    found: dict[str, str] = {}
    for keyword, value in mapping.items():
        idx = lowered.find(keyword)
        if idx >= 0 and value not in found:
            found[value] = _evidence(text, idx, idx + len(keyword), pad=30)
    return sorted(found.items())


def extract_legal(text: str) -> list[tuple[str, str]]:
    return _match_keywords(text, LEGAL_KEYWORDS)


def extract_amenities(text: str) -> list[tuple[str, str]]:
    return _match_keywords(text, AMENITY_KEYWORDS)


# --- D1.5: địa danh --------------------------------------------------------

_DISTRICT_NUM = re.compile(r"\b(?:quận|q\.)\s*(\d{1,2})\b", re.IGNORECASE)
_DISTRICT_NAME = re.compile(
    r"\b[Qq]uận\s+((?:[A-ZÀ-Ỹ][a-zà-ỹ]+)(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){0,2})"
    r"|\b[Hh]uyện\s+((?:[A-ZÀ-Ỹ][a-zà-ỹ]+)(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){0,2})"
)

CITY_ALIASES = {
    "ho chi minh": "TP. Hồ Chí Minh",
    "tphcm": "TP. Hồ Chí Minh",
    "tp hcm": "TP. Hồ Chí Minh",
    "hcm": "TP. Hồ Chí Minh",
    "ha noi": "Hà Nội",
    "da nang": "Đà Nẵng",
    "binh duong": "Bình Dương",
    "dong nai": "Đồng Nai",
    "hai phong": "Hải Phòng",
    "can tho": "Cần Thơ",
    "khanh hoa": "Khánh Hòa",
    "nha trang": "Khánh Hòa",
    "vung tau": "Bà Rịa - Vũng Tàu",
    "ba ria": "Bà Rịa - Vũng Tàu",
    "long an": "Long An",
    "quang ninh": "Quảng Ninh",
    "lam dong": "Lâm Đồng",
    "da lat": "Lâm Đồng",
    "hung yen": "Hưng Yên",
    "bac ninh": "Bắc Ninh",
    "thanh hoa": "Thanh Hóa",
    "nghe an": "Nghệ An",
    "hue": "Thừa Thiên Huế",
    "binh thuan": "Bình Thuận",
    "phan thiet": "Bình Thuận",
    "kien giang": "Kiên Giang",
    "phu quoc": "Kiên Giang",
}


def extract_location(text: str) -> dict:
    """Rút quận/huyện + tỉnh/thành từ text sạch. Không thấy → None."""
    district = None
    m = _DISTRICT_NUM.search(text)
    if m:
        district = f"Quận {int(m.group(1))}"
    else:
        m = _DISTRICT_NAME.search(text)
        if m:
            district = m.group(0).strip()

    flat = deaccent(text)
    city = None
    position = len(flat) + 1
    for alias, name in CITY_ALIASES.items():
        # Bắt buộc khớp trọn từ: "hue" không được khớp trong "cho thue",
        # "hcm" không được khớp trong một chuỗi ký tự dài hơn.
        found = re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", flat)
        if found and found.start() < position:
            position, city = found.start(), name
    return {"district": district, "city": city}


# --- Phân tier (Plan/02 §5) ------------------------------------------------

# --- D1.6: chặn giá trị phi lý của crawler ---------------------------------

# Phát hiện khi soi Evidence panel ở Tuần 4: có tin ghi 92 phòng ngủ, 675 phòng tắm.
# Đây là lỗi parser nguồn, không phải dữ liệu thật → bỏ giá trị và gắn flag thay vì
# để fact rác chảy vào prompt sinh nội dung.
MAX_ROOMS = 20
MIN_AREA_M2, MAX_AREA_M2 = 5.0, 10_000.0


def sanitize_rooms(value) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 1 <= number <= MAX_ROOMS else None


def sanitize_area(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if MIN_AREA_M2 <= number <= MAX_AREA_M2 else None


TIER_B_TYPES = {"villa", "street_house", "private_house", "shophouse", "condotel"}
TIER_C_TYPES = {"land", "project_land", "warehouse", "resort", "other"}
TIER_B_MIN_DESC = 300


def assign_tier(property_type: str, project_slug: str | None, description_len: int) -> str:
    if project_slug:
        return "A"
    if property_type in TIER_C_TYPES:
        return "C"
    if property_type in TIER_B_TYPES or description_len >= TIER_B_MIN_DESC:
        return "B"
    return "C"


# --- Điểm vào D1 + D2 ------------------------------------------------------


def reparse_record(raw: dict, canonical_url: str) -> dict:
    """Chuyển 1 bản ghi raw DataBDS thành bản ghi sạch theo data contract v1.

    `seller_display_name` bị **drop hoàn toàn** (PII, Plan/02 §9).
    """
    title = normalize_text(raw.get("title"))
    description = normalize_text(raw.get("description"))
    text = f"{title}\n{description}"

    price = parse_price(title, description, raw.get("total_price_vnd"))
    slug = extract_project_slug(canonical_url)
    ward = extract_ward(canonical_url)
    location = extract_location(text)
    legal = extract_legal(text)
    amenities = extract_amenities(text)
    bedrooms = sanitize_rooms(raw.get("bedrooms"))
    bathrooms = sanitize_rooms(raw.get("bathrooms"))
    area_m2 = sanitize_area(raw.get("area_m2"))
    property_type = raw.get("property_type") or ""
    building = extract_building_code(text)

    if location["district"] or location["city"]:
        location_flag = "from_text"
    elif ward:
        location_flag = "ward_from_url"
    else:
        location_flag = "missing"
    flags = {
        "project": "from_url" if slug else "missing",
        "price": price["price_flag"] or "missing",
        "legal": "from_text" if legal else "missing",
        "location": location_flag,
        "pii": "seller_dropped_phone_masked",
        "outliers": ";".join(
            name
            for name, ok in (
                ("bedrooms", raw.get("bedrooms") and bedrooms is None),
                ("bathrooms", raw.get("bathrooms") and bathrooms is None),
                ("area_m2", raw.get("area_m2") and area_m2 is None),
            )
            if ok
        ),
    }

    return {
        "parser_version": PARSER_VERSION,
        "property_type": property_type,
        "project_slug": slug,
        "project_name": None,  # tên có dấu do entity resolution điền (services/alias.py)
        "project_confidence": project_confidence(slug, text) if slug else 0.0,
        "building_code": building,
        "unit_type_key": unit_type_key(property_type, bedrooms),
        "ward": ward,
        "district": location["district"],
        "city": location["city"],
        "area_m2": area_m2,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "total_price_vnd": price["total_price_vnd"],
        "price_per_m2_vnd": price["price_per_m2_vnd"],
        "price_confidence": price["price_confidence"],
        "price_evidence": price["price_evidence"],
        "legal_facts": [v for v, _ in legal],
        "legal_evidence": dict(legal),
        "amenities": [v for v, _ in amenities],
        "amenity_evidence": dict(amenities),
        "title_clean": title,
        "description_clean": description,
        "description_len": len(description),
        "tier": assign_tier(property_type, slug, len(description)),
        "field_flags": flags,
    }
