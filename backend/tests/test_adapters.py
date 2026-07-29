"""Test hợp đồng bàn giao adapter QLoRA (Tuần 5).

Phần huấn luyện chạy ở máy GPU khác nên **điểm ghép mới là chỗ dễ hỏng nhất**: sai một
file là cấu hình C/D chết mà không ai biết cho tới lúc demo. Các test ở đây dựng thư mục
adapter giả trên đĩa đúng như lúc Hải copy về, rồi kiểm tra backend đọc được, báo lỗi
đúng chỗ, và ghi đủ vết vào `generations`.

Không nạp trọng số thật (cần GPU); phần nạp `peft` được kiểm bằng tay khi có adapter thật.
"""

import json

import pytest

from app.core.config import settings
from app.services import adapters
from app.services.generation import resolve_adapter, run_generation
from tests.test_generation import indexed  # noqa: F401 — fixture dùng lại
from tests.test_pipeline import databds, imported  # noqa: F401


def write_adapter(root, name: str, *, card: dict | None = None, weights: bool = True) -> str:
    """Dựng một thư mục adapter đúng hình dạng peft sinh ra."""
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    (path / "adapter_config.json").write_text(
        json.dumps({"base_model_name_or_path": "Qwen/Qwen2.5-1.5B-Instruct", "r": 16}),
        encoding="utf-8",
    )
    if weights:
        (path / "adapter_model.safetensors").write_bytes(b"trong-so-gia" * 100)
    if card is not None:
        (path / "adapter_card.json").write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    return str(path)


@pytest.fixture()
def adapter_dir(tmp_path, monkeypatch):
    root = tmp_path / "adapters"
    root.mkdir()
    monkeypatch.setattr(settings, "adapter_dir", str(root))
    monkeypatch.setattr(settings, "llm_adapter", "")
    return root


FULL_CARD = {
    "base_model": "Qwen/Qwen2.5-1.5B-Instruct",
    "dataset_version": "dataset_v1",
    "lora": {"r": 16, "alpha": 32},
    "training": {"epochs": 3, "learning_rate": 2e-4},
}


def test_doc_duoc_adapter_va_metadata(adapter_dir):
    write_adapter(adapter_dir, "qwen-r16", card=FULL_CARD)

    items = adapters.list_adapters()

    assert [a["name"] for a in items] == ["qwen-r16"]
    assert items[0]["loadable"] is True
    assert items[0]["base_model"] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert items[0]["problems"] == []
    assert items[0]["fingerprint"], "phải có vân tay để truy vết bản trọng số đã dùng"


def test_thieu_trong_so_thi_khong_nap_duoc_va_noi_ro_thieu_gi(adapter_dir):
    write_adapter(adapter_dir, "hong", card=FULL_CARD, weights=False)

    info = adapters.list_adapters()[0]

    assert info["loadable"] is False
    assert any("trọng số" in p for p in info["problems"])
    with pytest.raises(ValueError, match="không nạp được"):
        adapters.get_adapter("hong")


def test_thieu_card_van_nap_duoc_nhung_bi_canh_bao(adapter_dir):
    write_adapter(adapter_dir, "khong-card", card=None)

    info = adapters.get_adapter("khong-card")

    # base_model suy được từ adapter_config.json nên vẫn nạp được
    assert info["loadable"] is True and info["has_card"] is False
    assert any("adapter_card.json" in p for p in info["problems"])


def test_adapter_smoke_bi_danh_dau_khong_dung_cho_bao_cao(adapter_dir):
    write_adapter(adapter_dir, "smoke", card={**FULL_CARD, "smoke": True})

    info = adapters.get_adapter("smoke")

    assert any("không dùng cho số liệu" in p for p in info["problems"])


def test_tu_chon_khi_chi_co_mot_adapter(adapter_dir):
    assert adapters.default_adapter_name() == ""
    write_adapter(adapter_dir, "duy-nhat", card=FULL_CARD)
    assert adapters.default_adapter_name() == "duy-nhat"

    # Có hai cái thì không đoán bừa — phải chỉ định rõ
    write_adapter(adapter_dir, "them-mot", card=FULL_CARD)
    assert adapters.default_adapter_name() == ""


def test_bao_loi_co_huong_dan_khi_chua_ban_giao_adapter(adapter_dir):
    with pytest.raises(FileNotFoundError) as err:
        resolve_adapter("C")

    message = str(err.value)
    assert "chưa có adapter nào" in message.lower() or "Chưa có adapter" in message
    assert "training/README.md" in message


def test_cau_hinh_A_B_khong_dung_adapter(adapter_dir):
    write_adapter(adapter_dir, "qwen-r16", card=FULL_CARD)

    assert resolve_adapter("A") is None
    assert resolve_adapter("B") is None
    assert resolve_adapter("C")["name"] == "qwen-r16"
    assert resolve_adapter("D")["name"] == "qwen-r16"


def test_cau_hinh_C_va_D_ghi_lai_adapter_da_dung(db, indexed, adapter_dir):  # noqa: F811
    write_adapter(adapter_dir, "qwen-r16", card=FULL_CARD)
    args = dict(
        tenant_id=indexed["tenant_id"],
        created_by=indexed["created_by"],
        brief="Giới thiệu căn hộ 2 phòng ngủ tại Grand View",
        channel="facebook",
        persona="young_family",
        project_slug="grand-view",
    )

    gen_c = run_generation(db, config="C", **args)
    gen_d = run_generation(db, config="D", retrieval_config="R3", **args)

    assert gen_c.status == "done" and gen_d.status == "done"
    assert gen_c.adapter_name == gen_d.adapter_name == "qwen-r16"
    assert gen_c.adapter_fingerprint and gen_c.adapter_fingerprint == gen_d.adapter_fingerprint
    # C không truy xuất, D có — đúng hai biến của ma trận A–D
    assert gen_c.context_fact_ids == [] and gen_c.retrieval_config == "none"
    assert gen_d.context_fact_ids and gen_d.retrieval_config == "R3"
    # C vẫn được chấm claim trên tập fact tham chiếu để so sánh công bằng với D
    assert "unsupported_claim_rate" in gen_c.metrics


def test_api_liet_ke_adapter(client, db, seeded, adapter_dir):
    from tests.conftest import login

    write_adapter(adapter_dir, "qwen-r16", card=FULL_CARD)

    payload = client.get("/api/generation/adapters", headers=login(client, "admin@mot.vn")).json()

    assert payload["ready"] is True
    assert payload["default"] == "qwen-r16"
    assert payload["adapters"][0]["card"]["dataset_version"] == "dataset_v1"


def test_api_tra_400_co_huong_dan_khi_chay_C_ma_chua_co_adapter(client, db, indexed, adapter_dir):  # noqa: F811
    from tests.conftest import login

    response = client.post(
        "/api/generation",
        json={
            "brief": "Giới thiệu căn hộ 2 phòng ngủ",
            "channel": "facebook",
            "persona": "investor",
            "config": "C",
        },
        headers=login(client, "admin@mot.vn"),
    )

    assert response.status_code == 400
    assert "training/README.md" in response.json()["detail"]
