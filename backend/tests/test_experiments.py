"""Test bộ chạy thí nghiệm đóng băng và phần thống kê (Tuần 6).

Phần thống kê được kiểm bằng các trường hợp có đáp án tính tay được — kiểm định hoán vị
với n nhỏ cho p chính xác, không phải xấp xỉ, nên khẳng định được số chứ không chỉ "chạy
không lỗi". Đây là phần sẽ bị hội đồng hỏi kỹ nhất nên không để nó không có test.
"""

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import ExperimentRun, Generation
from app.services.experiments import (
    available_configs,
    bootstrap_ci,
    cohens_dz,
    compare_paired,
    item_metrics,
    paired_permutation_test,
    pick_briefs,
    run_experiment,
    summarize_config,
)
from app.services.dataset import build_dataset_split
from app.services.indexing import run_index_build
from app.services.pipeline import run_clean_pipeline
from tests.conftest import login
from tests.test_pipeline import databds, imported  # noqa: F401 — fixture dùng lại


# --- Thống kê -------------------------------------------------------------


def test_hoan_vi_bat_cap_cho_p_chinh_xac_khi_moi_cap_deu_cung_chieu():
    """4 cặp đều giảm → chỉ 1 trong 2⁴ tổ hợp dấu cho trung bình xa bằng hoặc hơn.

    Đúng ra là 2/16: tổ hợp toàn dấu gốc và tổ hợp đảo hết đều cho |trung bình| như nhau.
    Con số này tính tay được nên nếu code sai là test đổ ngay.
    """
    result = paired_permutation_test([-0.2, -0.2, -0.2, -0.2])

    assert result["method"] == "exact"
    assert result["n"] == 4
    assert result["p_value"] == pytest.approx(2 / 16)


def test_hoan_vi_khong_the_dat_p_nho_voi_co_mau_be():
    """Giới hạn cứng phải nói rõ trong báo cáo: n = 4 thì p không bao giờ dưới 0,05."""
    assert paired_permutation_test([-1.0, -1.0, -1.0, -1.0])["p_value"] > 0.05
    assert paired_permutation_test([-1.0] * 10)["p_value"] < 0.05


def test_hoan_vi_chenh_lech_bang_khong_thi_p_bang_mot():
    assert paired_permutation_test([0.0, 0.0, 0.0])["p_value"] == 1.0
    assert paired_permutation_test([])["p_value"] is None


def test_khoang_tin_cay_va_co_hieu_ung_on_dinh_theo_seed():
    diffs = [-0.10, -0.08, -0.12, -0.05, -0.20]

    first = bootstrap_ci(diffs)
    second = bootstrap_ci(diffs)

    assert first == second, "bootstrap phải tái lập được: cùng dữ liệu → cùng khoảng"
    assert first["low"] < 0 and first["high"] < 0  # toàn bộ khoảng nằm dưới 0
    assert cohens_dz(diffs) < 0
    assert cohens_dz([0.5]) is None  # một cặp thì không có độ lệch chuẩn


def test_so_sanh_bat_cap_dem_dung_thang_thua_theo_chieu_tot():
    before = [0.4, 0.2, 0.1]
    after = [0.1, 0.3, 0.1]

    lower = compare_paired(before, after, "lower")
    higher = compare_paired(before, after, "higher")

    assert lower["wins"] == 1 and lower["losses"] == 1 and lower["ties"] == 1
    assert higher["wins"] == 1 and higher["losses"] == 1  # đảo chiều thì đảo vai
    assert lower["mean_diff"] == pytest.approx((-0.3 + 0.1 + 0.0) / 3, abs=1e-4)
    assert lower["n"] == 3


def test_so_sanh_bo_qua_cap_thieu_du_lieu():
    assert compare_paired([0.5, None, 0.2], [0.1, 0.3, None], "lower")["n"] == 1
    assert compare_paired([], [], "lower") == {"n": 0}


# --- Lọc cấu hình theo adapter --------------------------------------------


def test_thieu_adapter_thi_bo_qua_C_D_va_ghi_ro_ly_do(tmp_path):
    """A/B vẫn phải ra số. Ô trống trong báo cáo phải nói được là do thiếu adapter."""
    settings.adapter_dir = str(tmp_path / "trong")

    runnable, skipped = available_configs(("A", "B", "C", "D"), None)

    assert runnable == ["A", "B"]
    assert set(skipped) == {"C", "D"}
    assert all("adapter" in reason.lower() for reason in skipped.values())


def test_cau_hinh_khong_hop_le_bi_loai_kem_ly_do(tmp_path):
    settings.adapter_dir = str(tmp_path / "trong")
    runnable, skipped = available_configs(("A", "X"), None)
    assert runnable == ["A"]
    assert "không hợp lệ" in skipped["X"]


# --- Chạy thật (generator template) ---------------------------------------


@pytest.fixture()
def ready(db, imported, tmp_path):  # noqa: F811
    settings.embedding_backend = "hashing"
    settings.llm_provider = "template"
    settings.adapter_dir = str(tmp_path / "khong-co-adapter")
    run_clean_pipeline(db, **imported)
    run_index_build(db, tenant_id=imported["tenant_id"], created_by=imported["created_by"])
    build_dataset_split(db, imported["tenant_id"], "dataset_test")
    return imported


def test_chay_thi_nghiem_ghi_snapshot_va_gan_generation_vao_run(db, ready):
    briefs = [
        {
            "project_slug": "grand-view",
            "channel": "facebook",
            "persona": "investor",
            "brief": "Giới thiệu căn 2 phòng ngủ tại dự án Grand View",
        },
        {
            "project_slug": "grand-view",
            "channel": "email",
            "persona": "young_family",
            "brief": "Giới thiệu căn 3 phòng ngủ tại dự án Grand View",
        },
    ]

    run = run_experiment(
        db,
        tenant_id=ready["tenant_id"],
        created_by=ready["created_by"],
        briefs=briefs,
        dataset_version="dataset_test",
        configs=("A", "B", "C", "D"),
        run_key="run_test",
    )

    assert run.status == "done"
    assert run.configs == ["A", "B"]  # C/D bị bỏ vì chưa có adapter
    assert set(run.skipped) == {"C", "D"}

    snapshot = run.snapshot
    assert snapshot["dataset_version"] == "dataset_test"
    assert snapshot["generation"]["prompt_version"]
    assert snapshot["generation"]["seed"] == settings.llm_seed
    assert snapshot["adapter"] is None
    assert snapshot["knowledge_base"]["chunks"] > 0

    records = db.scalars(select(Generation).where(Generation.experiment_run_id == run.id)).all()
    assert len(records) == 4  # 2 brief × 2 cấu hình
    assert {r.config for r in records} == {"A", "B"}

    summary = run.summary
    assert set(summary["by_config"]) == {"A", "B"}
    assert summary["by_config"]["A"]["n"] == 2
    # Chỉ so cặp khác đúng một biến và cả hai đều có số → chỉ còn A→B
    assert [c["pair"] for c in summary["comparisons"]] == ["A→B"]
    assert summary["comparisons"][0]["factor"] == "retrieval"


def test_moi_cau_hinh_chay_dung_cung_bo_brief(db, ready):
    """Điều kiện so sánh công bằng: bắt cặp theo brief chỉ đúng khi input trùng nhau."""
    briefs = [
        {
            "project_slug": "grand-view",
            "channel": "description",
            "persona": "first_home",
            "brief": "Giới thiệu căn hộ tại dự án Grand View",
        }
    ]

    run = run_experiment(
        db,
        tenant_id=ready["tenant_id"],
        created_by=ready["created_by"],
        briefs=briefs,
        dataset_version="dataset_test",
        configs=("A", "B"),
        run_key="run_pair",
    )
    records = db.scalars(select(Generation).where(Generation.experiment_run_id == run.id)).all()

    assert {r.brief for r in records} == {"Giới thiệu căn hộ tại dự án Grand View"}
    assert {r.channel for r in records} == {"description"}
    assert {r.seed for r in records} == {settings.llm_seed}
    assert {r.model_name for r in records} == {records[0].model_name}


def test_chi_so_moi_bai_do_dung_dinh_dang_va_do_dai(db, ready):
    run = run_experiment(
        db,
        tenant_id=ready["tenant_id"],
        created_by=ready["created_by"],
        briefs=[
            {
                "project_slug": "grand-view",
                "channel": "facebook",
                "persona": "investor",
                "brief": "Giới thiệu căn 2 phòng ngủ",
            }
        ],
        dataset_version="dataset_test",
        configs=("B",),
        run_key="run_metrics",
    )
    record = db.scalars(select(Generation).where(Generation.experiment_run_id == run.id)).one()
    metrics = item_metrics(record)

    assert metrics["structured_ok"] in (0.0, 1.0)
    assert metrics["length_ok"] in (0.0, 1.0)
    assert metrics["words"] > 0
    assert summarize_config([record])["n"] == 1


def test_bai_hong_khong_lam_hong_ca_luot(db, ready):
    """Bài lỗi bị loại khỏi trung bình nhưng vẫn được đếm — không im lặng bỏ qua."""
    failed = Generation(tenant_id=ready["tenant_id"], created_by=ready["created_by"], config="A", channel="facebook", persona="investor", status="failed")

    summary = summarize_config([failed])

    assert summary == {"n": 0, "n_failed": 1}


def test_pick_briefs_tat_dinh(db, ready):
    first = pick_briefs(db, ready["tenant_id"], "dataset_test", 2)
    second = pick_briefs(db, ready["tenant_id"], "dataset_test", 2)
    assert first == second


# --- API ------------------------------------------------------------------


def test_api_tra_ve_run_kem_snapshot_va_tung_bai(client, db, ready):
    run = run_experiment(
        db,
        tenant_id=ready["tenant_id"],
        created_by=ready["created_by"],
        briefs=[
            {
                "project_slug": "grand-view",
                "channel": "facebook",
                "persona": "investor",
                "brief": "Giới thiệu căn 2 phòng ngủ",
            }
        ],
        dataset_version="dataset_test",
        configs=("A", "B"),
        run_key="run_api",
    )
    headers = login(client, "admin@mot.vn")

    listed = client.get("/api/experiments", headers=headers).json()
    assert [r["run_key"] for r in listed["items"]] == ["run_api"]
    assert "snapshot" not in listed["items"][0]  # danh sách không kèm snapshot cho nhẹ

    detail = client.get(f"/api/experiments/{run.id}", headers=headers).json()
    assert detail["snapshot"]["generation"]["prompt_version"]
    assert set(detail["summary"]["by_config"]) == {"A", "B"}

    items = client.get(f"/api/experiments/{run.id}/items?config=B", headers=headers).json()
    assert len(items["items"]) == 1 and items["items"][0]["config"] == "B"


def test_tenant_khac_khong_xem_duoc_run(client, db, ready):
    run = run_experiment(
        db,
        tenant_id=ready["tenant_id"],
        created_by=ready["created_by"],
        briefs=[
            {
                "project_slug": "grand-view",
                "channel": "facebook",
                "persona": "investor",
                "brief": "Giới thiệu căn 2 phòng ngủ",
            }
        ],
        dataset_version="dataset_test",
        configs=("A",),
        run_key="run_isolated",
    )
    other = login(client, "admin@hai.vn")

    assert client.get("/api/experiments", headers=other).json()["items"] == []
    assert client.get(f"/api/experiments/{run.id}", headers=other).status_code == 404


def test_bao_cao_markdown_ghi_ro_snapshot_va_gioi_han_co_mau(db, ready):
    """Báo cáo phải tự nói ra giới hạn của nó — người đọc không cần biết trước n bao nhiêu."""
    from app.services.experiments import render_markdown

    run = run_experiment(
        db,
        tenant_id=ready["tenant_id"],
        created_by=ready["created_by"],
        briefs=[
            {
                "project_slug": "grand-view",
                "channel": "facebook",
                "persona": "investor",
                "brief": "Giới thiệu căn 2 phòng ngủ",
            }
        ],
        dataset_version="dataset_test",
        configs=("A", "B", "C"),
        run_key="run_md",
    )
    text = render_markdown(run)

    assert "Snapshot (điều kiện chạy)" in text
    assert run.snapshot["git_commit"] in text
    assert "**chưa có**" in text  # adapter trống phải hiện rõ, không để dòng trắng
    assert "`C`:" in text  # cấu hình bị bỏ qua kèm lý do
    assert "chưa phải bằng chứng thống kê" in text


def test_run_duoc_luu_lai_de_truy_nguoc(db, ready):
    run_experiment(
        db,
        tenant_id=ready["tenant_id"],
        created_by=ready["created_by"],
        briefs=[
            {
                "project_slug": "grand-view",
                "channel": "facebook",
                "persona": "investor",
                "brief": "Giới thiệu căn 2 phòng ngủ",
            }
        ],
        dataset_version="dataset_test",
        configs=("A",),
        run_key="run_log",
    )
    stored = db.scalars(select(ExperimentRun)).all()

    assert len(stored) == 1
    assert stored[0].finished_at is not None
    assert stored[0].snapshot["git_commit"]
