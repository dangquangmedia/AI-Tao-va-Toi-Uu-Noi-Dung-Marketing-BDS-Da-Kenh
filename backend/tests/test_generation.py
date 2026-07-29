"""Test tầng sinh nội dung A/B, router và kiểm tra claim (Tuần 4).

Dùng generator `template` (tất định, không cần GPU) để test logic pipeline; chất lượng
văn bản của model thật được đánh giá riêng bằng bảng A/B trong báo cáo checkpoint.
"""

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import Generation
from app.services.claim_check import check_claims
from app.services.generation import parse_output, run_generation
from app.services.indexing import run_index_build
from app.services.pipeline import run_clean_pipeline
from app.services.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt, prompt_fingerprint
from app.services.query_router import (
    INTENT_COMPARE,
    INTENT_FACT,
    INTENT_RELATION,
    classify_intent,
    route,
)
from tests.test_pipeline import databds, imported  # noqa: F401 — fixture dùng lại


@pytest.fixture()
def indexed(db, imported):  # noqa: F811
    """Pipeline D1–D5 + knowledge base + generator mẫu."""
    settings.embedding_backend = "hashing"
    settings.llm_provider = "template"
    run_clean_pipeline(db, **imported)
    run_index_build(db, tenant_id=imported["tenant_id"], created_by=imported["created_by"])
    return imported


# --- Router ---------------------------------------------------------------


@pytest.mark.parametrize(
    "question,expected",
    [
        ("So sánh giá giữa dự án A và dự án B", INTENT_COMPARE),
        ("Dự án Grand View có tòa nào?", INTENT_RELATION),
        ("Căn 2 phòng ngủ giá bao nhiêu?", INTENT_FACT),
    ],
)
def test_phan_loai_y_dinh(question, expected):
    assert classify_intent(question) == expected


def test_router_nhan_dien_du_an_va_giao_trong_so(db, indexed):
    plan = route(db, indexed["tenant_id"], "Dự án Grand View có căn 2 phòng ngủ không?")

    assert plan["project_slug"] == "grand-view"
    assert plan["allowed_projects"] == ["grand-view"]
    assert set(plan["weights"]) == {"vector", "bm25", "graph"}
    assert "grand-view" in plan["explain"]


def test_router_chuyen_sang_che_do_tim_theo_mo_ta_khi_khong_neu_ten_du_an(db, indexed):
    """Câu hỏi mô tả cần trọng số khác hẳn — bằng chứng đo được ở Tuần 6.

    Trọng số của chế độ targeted hạ graph xuống 0,3–0,4, đúng nhánh mạnh nhất khi câu hỏi
    không có tên dự án để bám vào.
    """
    from app.services.query_router import DISCOVERY_WEIGHTS, MODE_DISCOVERY, MODE_TARGETED

    mo_ta = route(db, indexed["tenant_id"], "Tìm căn hộ 2 phòng ngủ khoảng 70 m² ở Quận 7")
    co_ten = route(db, indexed["tenant_id"], "Dự án Grand View có căn 2 phòng ngủ không?")

    assert mo_ta["mode"] == MODE_DISCOVERY
    assert mo_ta["weights"] == DISCOVERY_WEIGHTS
    assert mo_ta["project_slug"] is None and mo_ta["allowed_projects"] == []
    assert "không nêu tên dự án" in mo_ta["explain"]

    assert co_ten["mode"] == MODE_TARGETED
    assert co_ten["weights"]["graph"] < DISCOVERY_WEIGHTS["graph"]


def test_router_khong_loc_khi_cau_hoi_nhac_hai_du_an(db, indexed):
    """Câu so sánh nhắc hai dự án → không khóa vào một dự án, nhưng vẫn giới hạn cả hai."""
    from app.models import GraphEntity

    db.add(
        GraphEntity(
            tenant_id=indexed["tenant_id"],
            entity_type="Project",
            canonical_key="vista-verde",
            name="Vista Verde",
        )
    )
    db.flush()

    plan = route(db, indexed["tenant_id"], "So sánh dự án Grand View và dự án Vista Verde")

    assert plan["project_slug"] is None  # chỉ khóa khi chắc chắn một dự án
    assert set(plan["allowed_projects"]) == {"grand-view", "vista-verde"}


# --- Prompt ---------------------------------------------------------------


def test_prompt_A_va_B_chi_khac_khoi_du_kien():
    a = build_user_prompt("facebook", "investor", "Giới thiệu căn 2PN")
    b = build_user_prompt("facebook", "investor", "Giới thiệu căn 2PN", context_block="- Giá: 4.9 tỷ")

    assert "Không có dữ kiện truy xuất" in a
    assert "- Giá: 4.9 tỷ" in b
    # Phần yêu cầu (kênh, persona, brief) phải giống hệt nhau
    assert a.split("Không có dữ kiện")[0] == b.split("Dữ kiện được truy xuất")[0]
    assert prompt_fingerprint(SYSTEM_PROMPT, a) != prompt_fingerprint(SYSTEM_PROMPT, b)


def test_parse_output_tach_dung_ba_phan():
    parsed = parse_output("HEADLINE: Căn 2PN đẹp\nBODY:\nNội dung chi tiết.\nCTA: Gọi ngay")
    assert parsed == {"headline": "Căn 2PN đẹp", "body": "Nội dung chi tiết.", "cta": "Gọi ngay"}
    # Model không tuân định dạng → giữ nguyên toàn bộ làm body, không mất nội dung
    assert parse_output("Chỉ là một đoạn văn")["body"] == "Chỉ là một đoạn văn"


# --- Kiểm tra claim -------------------------------------------------------


def test_claim_co_can_cu_va_khong_can_cu():
    facts = [{"text": "Giá: 4.9 tỷ", "value_num": 4_900_000_000}, {"text": "Diện tích: 72 m2"}]

    result = check_claims("Căn hộ 72 m2 giá 4.9 tỷ. Dự án có 15 bể bơi vô cực.", facts)

    assert result["n_claims"] == 2
    assert result["claims"][0]["status"] == "supported"
    assert result["claims"][1]["status"] == "unsupported"
    assert "15" in result["claims"][1]["reason"]
    assert result["unsupported_claim_rate"] == 0.5


def test_claim_chua_tu_cam_bi_danh_dau():
    result = check_claims("Cam kết lợi nhuận 15% mỗi năm.", [{"text": "Giá: 4.9 tỷ"}])
    assert result["claims"][0]["status"] == "forbidden"
    assert result["n_forbidden"] == 1


# --- Sinh nội dung A/B ----------------------------------------------------


def test_cau_hinh_B_co_context_con_A_thi_khong(db, indexed):
    args = dict(
        tenant_id=indexed["tenant_id"],
        created_by=indexed["created_by"],
        brief="Giới thiệu căn hộ 2 phòng ngủ tại Grand View",
        channel="facebook",
        persona="young_family",
        project_slug="grand-view",
    )
    gen_a = run_generation(db, config="A", **args)
    gen_b = run_generation(db, config="B", retrieval_config="R3", **args)

    assert gen_a.status == "done" and gen_b.status == "done"
    assert gen_a.context_fact_ids == [] and gen_a.retrieval_config == "none"
    assert gen_b.context_fact_ids, "B phải có fact trong context"
    assert gen_b.context_chunk_ids
    assert gen_b.prompt_version == PROMPT_VERSION
    assert gen_a.prompt_hash != gen_b.prompt_hash
    assert gen_a.model_name == gen_b.model_name  # cùng model → so sánh công bằng
    assert gen_a.seed == gen_b.seed
    # Cả hai đều được chấm claim trên cùng tập fact tham chiếu
    assert "unsupported_claim_rate" in gen_a.metrics
    assert "unsupported_claim_rate" in gen_b.metrics


def test_generation_duoc_log_day_du(db, indexed):
    run_generation(
        db,
        tenant_id=indexed["tenant_id"],
        created_by=indexed["created_by"],
        brief="Giới thiệu căn hộ 3 phòng ngủ",
        channel="email",
        persona="investor",
        config="B",
        project_slug="grand-view",
    )
    record = db.scalars(select(Generation)).first()

    assert record.channel == "email" and record.persona == "investor"
    assert record.prompt_hash and record.model_name and record.provider == "template"
    assert record.latency_ms >= 0
    assert record.metrics["n_context_facts"] >= 1


def test_tenant_khac_khong_thay_generation(client, db, seeded, indexed):
    from tests.conftest import login

    run_generation(
        db,
        tenant_id=indexed["tenant_id"],
        created_by=indexed["created_by"],
        brief="Giới thiệu căn hộ",
        channel="description",
        persona="first_home",
        config="A",
    )
    assert client.get("/api/generation", headers=login(client, "admin@hai.vn")).json() == []
    assert len(client.get("/api/generation", headers=login(client, "admin@mot.vn")).json()) == 1


def test_reviewer_khong_duoc_sinh_noi_dung(client, db, indexed):
    from tests.conftest import login

    body = {
        "brief": "Giới thiệu căn hộ 2 phòng ngủ",
        "channel": "facebook",
        "persona": "investor",
        "config": "A",
    }
    assert client.post("/api/generation", json=body, headers=login(client, "reviewer@mot.vn")).status_code == 403
    assert client.post("/api/generation", json=body, headers=login(client, "marketer@mot.vn")).status_code == 200
