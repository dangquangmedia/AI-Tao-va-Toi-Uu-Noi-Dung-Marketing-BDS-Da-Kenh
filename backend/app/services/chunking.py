"""Cắt chunk cho retrieval (Tuần 3).

Ba loại chunk cho mỗi tin, phục vụ hai mục đích khác nhau của RAG:

- `facts` — "thẻ dữ kiện" render từ canonical facts (giá, diện tích, PN, pháp lý,
  tiện ích, vị trí). Ngắn, dày thông tin, là nguồn chính để trả lời câu hỏi dữ kiện.
- `title` — tiêu đề, thường chứa tên dự án + mức giá.
- `description` — mô tả dài, cắt theo câu với phần chồng lấn để không đứt ngữ cảnh.

Mỗi chunk mở đầu bằng một dòng ngữ cảnh (dự án · phường · loại hình) để câu truy vấn
nhắc tên dự án vẫn khớp được chunk mô tả — cải thiện cả FTS lẫn vector.
"""

import hashlib
import re

CHUNK_CHARS = 700
CHUNK_OVERLAP_CHARS = 120
MIN_CHUNK_CHARS = 60
_SENTENCE = re.compile(r"(?<=[.!?…])\s+|\n+")

PREDICATE_LABELS = {
    "total_price_vnd": "Giá",
    "price_per_m2_vnd": "Giá/m²",
    "area_m2": "Diện tích",
    "bedrooms": "Phòng ngủ",
    "bathrooms": "Phòng tắm",
    "legal_status": "Pháp lý",
    "amenity": "Tiện ích",
    "property_type": "Loại hình",
    "building": "Tòa",
    "district": "Quận/huyện",
    "city": "Tỉnh/thành",
    "ward": "Phường/xã",
    "project": "Dự án",
}
_PRICE_PREDICATES = {"total_price_vnd", "price_per_m2_vnd"}


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    """Ước lượng token đủ dùng để giới hạn context (không cần tokenizer thật)."""
    return max(1, len(text) // 4)


def _format_price(value: float) -> str:
    """4_900_000_000 → '4.9 tỷ'; 850_000_000 → '850 triệu'."""
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}".rstrip("0").rstrip(".") + " tỷ"
    return f"{value / 1_000_000:.0f} triệu"


def context_header(listing) -> str:
    parts = []
    if listing.project_name or listing.project_slug:
        parts.append(f"Dự án {listing.project_name or listing.project_slug}")
    if listing.building_code:
        parts.append(f"tòa {listing.building_code}")
    if listing.ward:
        parts.append(listing.ward.replace("-", " ").title())
    if listing.district:
        parts.append(listing.district)
    if listing.city:
        parts.append(listing.city)
    if listing.property_type:
        parts.append(listing.property_type)
    return " · ".join(parts)


def render_fact_card(listing, facts) -> str:
    """Thẻ dữ kiện — chỉ gồm fact đã có provenance, không thêm chữ nào ngoài dữ liệu."""
    lines = [context_header(listing)]
    grouped: dict[str, list[str]] = {}
    for fact in facts:
        label = PREDICATE_LABELS.get(fact.predicate)
        if label is None:
            continue
        if fact.predicate in _PRICE_PREDICATES and fact.value_num:
            value = _format_price(fact.value_num)
        else:
            value = fact.value_text
        grouped.setdefault(label, [])
        if value not in grouped[label]:
            grouped[label].append(value)
    for label, values in grouped.items():
        lines.append(f"{label}: {', '.join(values)}")
    return "\n".join(line for line in lines if line.strip())


def split_description(text: str) -> list[str]:
    """Cắt mô tả theo câu, gộp tới ~700 ký tự, chồng lấn ~120 ký tự."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= CHUNK_CHARS:
        return [text]

    sentences = [s.strip() for s in _SENTENCE.split(text) if s.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > CHUNK_CHARS:
            chunks.append(current.strip())
            tail = current[-CHUNK_OVERLAP_CHARS:]
            current = f"{tail} {sentence}"
        else:
            current = f"{current} {sentence}".strip()
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) >= MIN_CHUNK_CHARS] or [text[:CHUNK_CHARS]]


def build_chunks(listing, facts) -> list[dict]:
    """Trả danh sách chunk (chưa có embedding) cho một tin đã làm sạch."""
    header = context_header(listing)
    out: list[dict] = []

    fact_card = render_fact_card(listing, facts)
    if fact_card.strip():
        out.append({"chunk_type": "facts", "seq": 0, "text": fact_card})

    if listing.title_clean.strip():
        text = f"{header}\n{listing.title_clean}" if header else listing.title_clean
        out.append({"chunk_type": "title", "seq": 0, "text": text})

    for i, part in enumerate(split_description(listing.description_clean)):
        text = f"{header}\n{part}" if header else part
        out.append({"chunk_type": "description", "seq": i, "text": text})

    for chunk in out:
        chunk["token_count"] = estimate_tokens(chunk["text"])
        chunk["content_hash"] = content_hash(chunk["text"])
    return out
