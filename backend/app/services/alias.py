"""Entity resolution cho dự án — pha 2 của D1 (Tuần 3, Plan/01 §6).

Pha 1 (`reparse.extract_project_slug`) chỉ nhận slug khi URL có mã vùng dạng số
(`...-phuong-tan-phong-9-grand-view`) nên bỏ sót các URL không có mã vùng
(`...-phuong-nhan-chinh-the-diamond-residence`) — không biết tên phường kết thúc ở đâu.

Pha 2 giải đúng chỗ đó bằng **từ điển tên phường học từ chính các URL có mã vùng**:

1. URL có mã vùng → phần trước số chắc chắn là tên phường → gom thành từ điển.
2. URL không có mã vùng → cắt tiền tố phường dài nhất trong từ điển; phần dư là ứng viên dự án.
3. Chỉ chấp nhận khi tên ứng viên **xuất hiện trong title/description** — vừa kiểm chứng
   vừa tạo bằng chứng (provenance) cho fact `project`, và lấy luôn tên có dấu để hiển thị.

Từ điển dựng lại từ chính batch đang chạy nên kết quả tất định (chạy lại không đổi).
Không dùng LLM, không fuzzy match mờ: gán nhầm một dự án là hỏng cả nhánh graph.
"""

import re

from app.services.reparse import _url_tail, deaccent, slug_to_name

MIN_PROJECT_TOKENS = 2  # ứng viên 1 token quá dễ trùng tên đường → bỏ
MAX_NAME_TOKENS = 8
ALIAS_CONFIDENCE = 0.75
_WORD = re.compile(r"[0-9A-Za-zÀ-ỹĐđ]+")


def _tail_tokens(canonical_url: str) -> list[str]:
    return _url_tail(canonical_url)


def build_ward_dictionary(urls) -> set[str]:
    """Tên phường/xã chắc chắn: phần đứng trước mã vùng dạng số trong URL."""
    wards: set[str] = set()
    for url in urls:
        tokens = _tail_tokens(url)
        digits = [i for i, t in enumerate(tokens) if t.isdigit()]
        if not digits:
            continue
        ward = tokens[:1] if digits[0] == 0 else tokens[: digits[0]]
        if ward:
            wards.add("-".join(ward))
    return wards


def split_ward_and_project(tokens: list[str], wards: set[str]) -> tuple[str | None, str | None]:
    """Cắt đuôi URL thành (phường, ứng viên dự án) bằng tiền tố phường dài nhất."""
    for size in range(min(len(tokens), 4), 0, -1):
        ward = "-".join(tokens[:size])
        if ward in wards:
            rest = tokens[size:]
            if len(rest) >= MIN_PROJECT_TOKENS:
                return ward, "-".join(rest)
            return ward, None
    return None, None


def _token_windows(text: str) -> list[tuple[str, str]]:
    """Các cụm từ liên tiếp trong text kèm dạng không dấu để đối chiếu với slug."""
    words = _WORD.findall(text)
    flat = [deaccent(w) for w in words]
    out = []
    for size in range(MIN_PROJECT_TOKENS, MAX_NAME_TOKENS + 1):
        for i in range(len(words) - size + 1):
            out.append(("-".join(flat[i : i + size]), " ".join(words[i : i + size])))
    return out


def find_display_name(slug: str, text: str) -> str | None:
    """Tên có dấu xuất hiện trong text ứng với slug — None nếu text không nhắc tới."""
    for flat, original in _token_windows(text):
        if flat == slug:
            return original
    return None


def resolve_project(
    canonical_url: str,
    text: str,
    slug_from_url: str | None,
    wards: set[str],
) -> dict:
    """Entity resolution cho một tin.

    - Pha 1 thắng nếu có; chỉ bổ sung tên hiển thị có dấu.
    - Pha 2 chỉ chạy khi pha 1 không ra, và bắt buộc có bằng chứng trong text.
    """
    if slug_from_url:
        display = find_display_name(slug_from_url, text)
        return {
            "project_slug": slug_from_url,
            "project_name": display or slug_to_name(slug_from_url),
            "project_source": "url_code_confirmed" if display else "url_code",
            "ward": None,
        }

    tokens = _tail_tokens(canonical_url)
    if not tokens:
        return {"project_slug": None, "project_name": None, "project_source": "missing", "ward": None}

    ward, candidate = split_ward_and_project(tokens, wards)
    if candidate is None:
        return {"project_slug": None, "project_name": None, "project_source": "missing", "ward": ward}

    display = find_display_name(candidate, text)
    if display is None:  # URL gợi ý nhưng nội dung không nhắc tới → không gán
        return {"project_slug": None, "project_name": None, "project_source": "missing", "ward": ward}

    return {
        "project_slug": candidate,
        "project_name": display,
        "project_source": "ward_dictionary",
        "ward": ward,
    }


def apply_resolution(clean: dict, resolution: dict, assign_tier) -> dict:
    """Ghi kết quả entity resolution vào bản ghi clean và tính lại tier/flag."""
    clean["project_slug"] = resolution["project_slug"]
    clean["project_name"] = resolution["project_name"]
    if resolution["project_source"] == "ward_dictionary":
        clean["project_confidence"] = ALIAS_CONFIDENCE
    if resolution["ward"]:  # phường cắt bằng từ điển chính xác hơn luật đoán 2 token
        clean["ward"] = resolution["ward"]
    clean["field_flags"] = {**clean["field_flags"], "project": resolution["project_source"]}
    clean["tier"] = assign_tier(
        clean["property_type"], clean["project_slug"], clean["description_len"]
    )
    return clean
