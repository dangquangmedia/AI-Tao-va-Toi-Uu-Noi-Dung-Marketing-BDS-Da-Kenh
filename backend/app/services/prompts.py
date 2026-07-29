"""Prompt có version cho cấu hình A/B (Tuần 4, Plan/03 §2).

Điều kiện so sánh công bằng của thí nghiệm: **A và B dùng đúng cùng một prompt**, chỉ
khác ở chỗ B được chèn thêm khối dữ kiện truy xuất. Nếu prompt khác nhau thì chênh lệch
đo được không còn quy về đóng góp của RAG.

Mọi prompt gắn `PROMPT_VERSION` và được hash lại khi log — đổi prompt là đổi version,
không sửa lặng lẽ (yêu cầu tái lập của Plan/03 §7).
"""

import hashlib

PROMPT_VERSION = "prompt_v1"

CHANNEL_SPECS = {
    "description": {
        "label": "mô tả bất động sản",
        "length": "180–260 từ",
        "rules": [
            "Mở đầu bằng vị trí và loại hình",
            "Nêu diện tích, số phòng, mức giá nếu có trong dữ kiện",
            "Kết bằng lời mời xem nhà",
        ],
    },
    "facebook": {
        "label": "bài đăng Facebook",
        "length": "80–140 từ",
        "rules": ["Chia dòng ngắn dễ đọc", "Tối đa 5 emoji", "Kết bằng 3–5 hashtag"],
    },
    "email": {
        "label": "email chăm sóc khách hàng",
        "length": "120–200 từ",
        "rules": ["Có dòng tiêu đề email", "Xưng hô lịch sự", "Chỉ một lời kêu gọi hành động"],
    },
    "landing_seo": {
        "label": "nội dung landing page chuẩn SEO",
        "length": "250–400 từ",
        "rules": [
            "Có tiêu đề H1 và ít nhất hai mục H2",
            "Đưa từ khóa chính vào 100 từ đầu",
            "Không nhồi từ khóa",
        ],
    },
}

PERSONA_SPECS = {
    "young_family": "gia đình trẻ, quan tâm trường học, an ninh, không gian sinh hoạt",
    "investor": "nhà đầu tư, quan tâm khả năng cho thuê, pháp lý, thanh khoản",
    "first_home": "người mua nhà lần đầu, quan tâm ngân sách, thanh toán, thủ tục",
}

SYSTEM_PROMPT = """Bạn là chuyên viên viết nội dung marketing bất động sản tại Việt Nam.

Quy tắc bắt buộc:
1. CHỈ dùng dữ kiện được cung cấp. Không suy đoán, không thêm tiện ích, pháp lý, tiến độ hay mức giá không có trong dữ kiện.
2. Không hứa hẹn lợi nhuận, không dùng "cam kết sinh lời", "chắc chắn tăng giá", "rẻ nhất thị trường".
3. Nếu thiếu dữ kiện cho một ý, bỏ ý đó — không bịa.
4. Viết tiếng Việt tự nhiên, không sáo rỗng.

Định dạng đầu ra, đúng ba phần, không thêm gì khác:
HEADLINE: <một dòng>
BODY:
<nội dung>
CTA: <một dòng>"""

_NO_CONTEXT_NOTE = (
    "Không có dữ kiện truy xuất kèm theo. Chỉ viết dựa trên yêu cầu tóm tắt bên dưới, "
    "tuyệt đối không bịa số liệu cụ thể."
)


def build_user_prompt(
    channel: str,
    persona: str,
    brief: str,
    context_block: str | None = None,
    brand: dict | None = None,
) -> str:
    """Prompt người dùng. `context_block=None` ⇒ cấu hình A (prompt-only)."""
    spec = CHANNEL_SPECS[channel]
    brand = brand or {}
    forbidden = ", ".join(brand.get("forbidden_terms", [])) or "cam kết lợi nhuận, chắc chắn sinh lời"
    tone = ", ".join(brand.get("tone", [])) or "tin cậy, rõ ràng, không thổi phồng"

    parts = [
        f"Nhiệm vụ: viết {spec['label']}.",
        f"Độ dài: {spec['length']}.",
        "Yêu cầu định dạng: " + "; ".join(spec["rules"]) + ".",
        f"Khách hàng mục tiêu: {PERSONA_SPECS.get(persona, persona)}.",
        f"Giọng thương hiệu: {tone}.",
        f"Từ cấm dùng: {forbidden}.",
        "",
        f"Yêu cầu cụ thể: {brief}",
        "",
    ]
    if context_block:
        parts += [
            "Dữ kiện được truy xuất (chỉ dùng những dòng này làm thông tin thực tế):",
            context_block,
        ]
    else:
        parts.append(_NO_CONTEXT_NOTE)
    return "\n".join(parts)


def prompt_fingerprint(system: str, user: str) -> str:
    """Hash prompt để log — biết chắc hai lần chạy dùng đúng một prompt."""
    return hashlib.sha256(f"{system}\n---\n{user}".encode()).hexdigest()[:32]
