"""Query router — chọn cách truy xuất theo dạng câu hỏi (Tuần 4, Plan/01 §6).

Bằng chứng Tuần 3: hợp nhất RRF với trọng số bằng nhau **làm giảm** chất lượng
(0,551 so với 0,850 của vector đơn thuần) vì nhánh lexical yếu hơn hẳn. Router giải
quyết đúng chỗ đó: nhận diện ý định câu hỏi rồi giao trọng số khác nhau cho từng
nhánh, đồng thời phát hiện tên dự án trong câu hỏi để lọc theo `project_slug`.

Luật là rule-based, không dùng LLM: rẻ, tất định, và giải thích được từng quyết định
trên slide (mỗi truy vấn trả kèm `explain`).
"""

from sqlalchemy.orm import Session

from app.services.reparse import deaccent

INTENT_RELATION = "relation"
INTENT_COMPARE = "compare"
INTENT_FACT = "fact"
INTENT_TEMPORAL = "temporal"
INTENT_GENERAL = "general"

# Từ khóa đã bỏ dấu để khớp bất kể người dùng gõ có dấu hay không
_RELATION_HINTS = (
    "toa nao", "thuoc", "nam o", "quan nao", "phuong nao", "khu vuc", "gan ",
    "cung khu", "du an nao", "o dau", "loai can", "unittype", "tang nao",
)
_COMPARE_HINTS = ("so sanh", "khac nhau", "hon kem", " voi du an", "giua du an", "chenh lech")
_FACT_HINTS = (
    "gia bao nhieu", "bao nhieu", "gia ", "dien tich", "may phong", "phong ngu",
    "phap ly", "so hong", "so do", "tien ich",
)
_TEMPORAL_HINTS = ("con hieu luc", "thoi diem", "cap nhat", "het han", "con ban khong", "ghi nhan")

# Trọng số cho từng nhánh theo ý định. Nền là cấu hình thắng sweep trên 72 gold query
# (vector 1.0 · bm25 0.6 · graph 0.3), điều chỉnh theo ý định: câu hỏi quan hệ cần graph
# nặng hơn, câu hỏi dữ kiện thì lexical/vector là chính.
INTENT_WEIGHTS = {
    INTENT_FACT: {"vector": 1.0, "bm25": 0.6, "graph": 0.3},
    INTENT_RELATION: {"vector": 0.9, "bm25": 0.4, "graph": 0.8},
    INTENT_COMPARE: {"vector": 1.0, "bm25": 0.6, "graph": 0.5},
    INTENT_TEMPORAL: {"vector": 1.0, "bm25": 0.6, "graph": 0.3},
    INTENT_GENERAL: {"vector": 1.0, "bm25": 0.6, "graph": 0.4},
}
FACT_CHUNK_INTENTS = (INTENT_FACT, INTENT_TEMPORAL)


def classify_intent(query: str) -> str:
    """Phân loại ý định theo thứ tự ưu tiên: so sánh > quan hệ > thời gian > dữ kiện."""
    flat = deaccent(query)
    if any(hint in flat for hint in _COMPARE_HINTS):
        return INTENT_COMPARE
    if any(hint in flat for hint in _RELATION_HINTS):
        return INTENT_RELATION
    if any(hint in flat for hint in _TEMPORAL_HINTS):
        return INTENT_TEMPORAL
    if any(hint in flat for hint in _FACT_HINTS):
        return INTENT_FACT
    return INTENT_GENERAL


def route(db: Session, tenant_id: str, query: str) -> dict:
    """Trả kế hoạch truy xuất cho một câu hỏi.

    `project_slug` chỉ được đặt khi câu hỏi nhắc đúng **một** dự án — nhắc hai dự án
    (câu so sánh) thì không lọc, để cả hai cùng có cơ hội vào top-k.
    """
    from app.services.retrieval import match_entities  # tránh import vòng

    intent = classify_intent(query)
    entities = match_entities(db, tenant_id, query)
    projects = [e for e in entities if e.entity_type == "Project"]

    project_slug = projects[0].canonical_key if len(projects) == 1 else None
    allowed_projects = [e.canonical_key for e in projects]
    weights = dict(INTENT_WEIGHTS[intent])

    return {
        "intent": intent,
        "weights": weights,
        "project_slug": project_slug,
        # Mọi nhánh (kể cả graph) phải tôn trọng danh sách này. Bỏ qua bước đó là lý do
        # bản router đầu tiên kém hơn trọng số cố định: graph kéo dự án hàng xóm 2-hop vào.
        "allowed_projects": allowed_projects,
        "matched_entities": [
            {"type": e.entity_type, "key": e.canonical_key, "name": e.name} for e in entities
        ],
        "prefer_chunk_types": ["facts"] if intent in FACT_CHUNK_INTENTS else [],
        "explain": (
            f"Ý định: {intent}"
            + (f" · dự án nhận diện: {project_slug}" if project_slug else "")
            + (f" · {len(projects)} dự án được nhắc" if len(projects) > 1 else "")
            + f" · trọng số {weights}"
        ),
    }
