"""Kiểm tra claim → fact (Tuần 4) — nền cho metric `unsupported claim rate`.

Cách làm tất định, không dùng LLM chấm LLM:

1. Cắt nội dung thành câu; câu nào chứa **con số** hoặc **từ khóa thuộc tính**
   (giá, diện tích, phòng ngủ, pháp lý, tiện ích…) thì coi là một *claim* cần căn cứ.
2. Dựng tập giá trị hợp lệ từ facts đã truy xuất (số đã chuẩn hóa + tên thực thể).
3. Claim được coi là **có căn cứ** khi mọi con số trong câu đều xuất hiện trong tập
   giá trị hợp lệ; ngược lại đánh dấu `unsupported` kèm lý do.
4. Câu chứa từ cấm (cam kết lợi nhuận…) bị đánh dấu `forbidden` bất kể có số hay không.

Đây là phiên bản rule-based của critic; bản đầy đủ (LLM judge + refine) làm ở Tuần 7,
nhưng metric đã đo được từ Tuần 4 để bảng A/B có số liệu hallucination.
"""

import re

from app.services.reparse import deaccent

_SENTENCE = re.compile(r"(?<=[.!?…])\s+|\n+")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
# URL trích dẫn chứa số (mã tin) — không phải số liệu người đọc nhìn thấy
_URL = re.compile(r"https?://\S+")
_ATTRIBUTE_HINTS = (
    "gia", "dien tich", "phong ngu", "phong tam", "so hong", "so do", "phap ly",
    "tien ich", "ho boi", "cong vien", "truong hoc", "thang may", "m2", "ty", "trieu",
)
DEFAULT_FORBIDDEN = (
    "cam kết lợi nhuận", "chắc chắn sinh lời", "chắc chắn tăng giá",
    "rẻ nhất thị trường", "lợi nhuận đảm bảo", "sinh lời chắc chắn",
)
MIN_CLAIM_CHARS = 12


def _normalize_number(token: str) -> str:
    value = token.replace(",", ".")
    if value.endswith(".0"):
        value = value[:-2]
    return value.rstrip("0").rstrip(".") if "." in value else value


def allowed_values(facts: list[dict]) -> set[str]:
    """Tập con số được phép xuất hiện trong nội dung, lấy từ facts đã truy xuất."""
    allowed: set[str] = set()
    for fact in facts:
        # Kèm cả mốc hiệu lực: ngày tháng in ra từ fact vẫn là số liệu có căn cứ
        text = " ".join(
            str(fact.get(field, ""))
            for field in ("text", "value_text", "valid_from", "valid_to")
        )
        for token in _NUMBER.findall(text):
            allowed.add(_normalize_number(token))
        value_num = fact.get("value_num")
        if value_num:
            allowed.add(_normalize_number(f"{value_num:.2f}"))
            for scale, _unit in ((1_000_000_000, "ty"), (1_000_000, "trieu")):
                if value_num >= scale:
                    allowed.add(_normalize_number(f"{value_num / scale:.2f}"))
    return allowed


def is_claim(sentence: str) -> bool:
    flat = deaccent(sentence)
    if len(sentence.strip()) < MIN_CLAIM_CHARS:
        return False
    return bool(_NUMBER.search(sentence)) or any(hint in flat for hint in _ATTRIBUTE_HINTS)


def check_claims(body: str, facts: list[dict], forbidden_terms=DEFAULT_FORBIDDEN) -> dict:
    """Chấm toàn bộ nội dung. Trả danh sách claim + tỷ lệ không có căn cứ."""
    allowed = allowed_values(facts)
    claims = []
    for raw in _SENTENCE.split(_URL.sub(" ", body or "")):
        sentence = raw.strip(" -•\t")
        if not sentence or not is_claim(sentence):
            continue
        flat = deaccent(sentence)
        hit_forbidden = [t for t in forbidden_terms if deaccent(t) in flat]
        numbers = [_normalize_number(n) for n in _NUMBER.findall(sentence)]
        missing = [n for n in numbers if n not in allowed]

        if hit_forbidden:
            status, reason = "forbidden", f"chứa từ cấm: {', '.join(hit_forbidden)}"
        elif missing:
            status, reason = "unsupported", f"số không có trong dữ kiện: {', '.join(missing)}"
        else:
            status, reason = "supported", ""
        claims.append(
            {"text": sentence, "status": status, "reason": reason, "numbers": numbers}
        )

    total = len(claims)
    unsupported = sum(1 for c in claims if c["status"] != "supported")
    return {
        "claims": claims,
        "n_claims": total,
        "n_unsupported": unsupported,
        "unsupported_claim_rate": round(unsupported / total, 4) if total else 0.0,
        "n_forbidden": sum(1 for c in claims if c["status"] == "forbidden"),
    }
