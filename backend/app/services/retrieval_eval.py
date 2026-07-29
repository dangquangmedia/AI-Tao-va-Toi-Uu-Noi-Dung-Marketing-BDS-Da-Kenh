"""Đánh giá retrieval R1/R2 trên bộ gold query (Tuần 3, protocol Plan/03 §4).

Bốn chỉ số, đều tính trên top-k và chỉ dùng nhãn suy ra tất định từ DB:

- **project_precision@k** — tỷ lệ kết quả trả về thuộc đúng dự án cần tìm. Đây là chỉ số
  quan trọng nhất với bài toán này: lấy nhầm dự án là sinh nội dung sai dữ kiện.
- **listing_recall@k** — bao nhiêu phần tin kỳ vọng được lấy về.
- **hit@k** — có ít nhất một kết quả đúng dự án hay không.
- **MRR** — nghịch đảo hạng của kết quả đúng đầu tiên.

Cùng một hàm chấm dùng cho mọi cấu hình (R1-fts, R1-vector, R1-hybrid, R2) nên bảng
so sánh giữa các cấu hình là so sánh công bằng — điều kiện của Plan/03 §2.
"""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RetrievalQuery
from app.services.retrieval import retrieve_r1, retrieve_r2, retrieve_r3

DEFAULT_K = 10
CONFIGS = (
    "R1-fts",
    "R1-bm25",
    "R1-vector",
    "R1-hybrid",
    "R2-graph",
    "R3-fixed",
    "R3-router",
)


def _run_config(
    db: Session, tenant_id: str, config: str, question: str, k: int, weights: dict | None = None
) -> list[dict]:
    if config.startswith("R1-"):
        return retrieve_r1(db, tenant_id, question, k, mode=config.split("-", 1)[1])
    if config == "R2-graph":
        return retrieve_r2(db, tenant_id, question, k)
    if config == "R3-fixed":  # trọng số cố định, không dùng router
        return retrieve_r3(db, tenant_id, question, k, weights=weights, use_router=False)[0]
    if config == "R3-router":  # trọng số do router quyết theo ý định câu hỏi
        return retrieve_r3(db, tenant_id, question, k, weights=weights, use_router=True)[0]
    raise ValueError(f"Cấu hình retrieval không hợp lệ: {config}")


def score_results(query: RetrievalQuery, results: list[dict]) -> dict:
    """Chấm một truy vấn. Không có kết quả → mọi chỉ số bằng 0 (không bỏ qua câu hỏi)."""
    expected_listings = set(query.expected_listing_ids)
    expected_projects = {query.project_slug} if query.project_slug else set()
    # Câu so sánh có hai dự án đúng: nhãn thứ hai nằm trong expected_entities dưới dạng
    # slug (không dấu, không khoảng trắng), khác với nhãn địa danh/tòa ("Quận 7", "Tòa V8").
    expected_projects |= {
        entity
        for entity in query.expected_entities
        if isinstance(entity, str) and " " not in entity and entity.islower()
    }

    correct_project = [r for r in results if r.get("project_slug") in expected_projects]
    retrieved_listings = {r.get("clean_listing_id") for r in results}

    mrr = 0.0
    for rank, item in enumerate(results, start=1):
        if item.get("project_slug") in expected_projects:
            mrr = 1.0 / rank
            break

    return {
        "n_results": len(results),
        "project_precision": len(correct_project) / len(results) if results else 0.0,
        "listing_recall": (
            len(expected_listings & retrieved_listings) / len(expected_listings)
            if expected_listings
            else 0.0
        ),
        "hit": 1.0 if correct_project else 0.0,
        "mrr": mrr,
    }


def evaluate(
    db: Session,
    tenant_id: str,
    dataset_version: str,
    configs: tuple[str, ...] = CONFIGS,
    k: int = DEFAULT_K,
    weights: dict | None = None,
) -> dict:
    """Chạy toàn bộ gold query trên các cấu hình và tổng hợp theo nhóm câu hỏi."""
    queries = db.scalars(
        select(RetrievalQuery)
        .where(
            RetrievalQuery.tenant_id == tenant_id,
            RetrievalQuery.dataset_version == dataset_version,
        )
        .order_by(RetrievalQuery.query_type, RetrievalQuery.query_key)
    ).all()
    if not queries:
        return {"queries": 0, "configs": {}}

    report: dict[str, dict] = {}
    for config in configs:
        per_type: dict[str, list[dict]] = defaultdict(list)
        for query in queries:
            results = _run_config(db, tenant_id, config, query.question, k, weights)
            per_type[query.query_type].append(score_results(query, results))

        by_type = {}
        for query_type, scores in per_type.items():
            by_type[query_type] = {
                metric: round(sum(s[metric] for s in scores) / len(scores), 4)
                for metric in ("project_precision", "listing_recall", "hit", "mrr")
            }
            by_type[query_type]["n"] = len(scores)

        flat = [s for scores in per_type.values() for s in scores]
        report[config] = {
            "overall": {
                metric: round(sum(s[metric] for s in flat) / len(flat), 4)
                for metric in ("project_precision", "listing_recall", "hit", "mrr")
            },
            "by_type": by_type,
        }
    return {"queries": len(queries), "k": k, "configs": report}


SWEEP_GRID = (
    {"vector": 1.0, "bm25": 0.3, "graph": 0.3},
    {"vector": 1.0, "bm25": 0.3, "graph": 0.6},
    {"vector": 1.0, "bm25": 0.3, "graph": 0.9},
    {"vector": 1.0, "bm25": 0.6, "graph": 0.3},
    {"vector": 1.0, "bm25": 0.6, "graph": 0.6},
    {"vector": 1.0, "bm25": 0.6, "graph": 0.9},
)


def sweep_weights(
    db: Session, tenant_id: str, dataset_version: str, k: int = DEFAULT_K, grid=SWEEP_GRID
) -> list[dict]:
    """Quét trọng số RRF của R3 trên gold query — cơ sở để chốt cấu hình production.

    Chỉ quét trên tập gold hiện có (split test của `dataset_v1`); trọng số chốt được
    ghi vào code kèm bảng số này để tái lập.
    """
    rows = []
    for weights in grid:
        report = evaluate(db, tenant_id, dataset_version, configs=("R3-fixed",), k=k, weights=weights)
        overall = report["configs"]["R3-fixed"]["overall"]
        rows.append({"weights": weights, **overall})
    return sorted(rows, key=lambda r: (-r["project_precision"], -r["mrr"]))


def render_markdown(report: dict, embedding_model: str, dataset_version: str, sweep: list[dict] | None = None) -> str:
    """Bảng kết quả cho báo cáo checkpoint — sinh từ chính số đo, không nhập tay."""
    if not report.get("configs"):
        return "# Đánh giá retrieval\n\nChưa có gold query.\n"

    lines = [
        "# Đánh giá retrieval R1 / R2 trên gold query",
        "",
        f"> Dataset `{dataset_version}` · {report['queries']} query · top-k = {report['k']} · "
        f"embedding `{embedding_model}`. Sinh bằng `python -m app.dataset_cli --eval`.",
        "",
        "## Tổng hợp",
        "",
        "| Cấu hình | project precision@k | listing recall@k | hit@k | MRR |",
        "|---|---:|---:|---:|---:|",
    ]
    for config, data in report["configs"].items():
        o = data["overall"]
        lines.append(
            f"| {config} | {o['project_precision']:.3f} | {o['listing_recall']:.3f} | "
            f"{o['hit']:.3f} | {o['mrr']:.3f} |"
        )

    lines += ["", "## Theo nhóm câu hỏi (project precision@k)", "", "| Nhóm | " + " | ".join(report["configs"]) + " |", "|---|" + "---:|" * len(report["configs"])]
    all_types = sorted({t for data in report["configs"].values() for t in data["by_type"]})
    for query_type in all_types:
        cells = []
        for data in report["configs"].values():
            entry = data["by_type"].get(query_type)
            cells.append(f"{entry['project_precision']:.3f}" if entry else "—")
        n = next(
            (
                data["by_type"][query_type]["n"]
                for data in report["configs"].values()
                if query_type in data["by_type"]
            ),
            0,
        )
        lines.append(f"| {query_type} (n={n}) | " + " | ".join(cells) + " |")

    if sweep:
        lines += [
            "",
            "## Sweep trọng số RRF của R3",
            "",
            "| vector | bm25 | graph | project precision@k | listing recall@k | MRR |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
        for row in sweep:
            w = row["weights"]
            lines.append(
                f"| {w['vector']} | {w['bm25']} | {w['graph']} | {row['project_precision']:.3f} | "
                f"{row['listing_recall']:.3f} | {row['mrr']:.3f} |"
            )
        best = sweep[0]["weights"]
        lines.append("")
        lines.append(f"Trọng số chốt cho production: `{best}`.")
    return "\n".join(lines) + "\n"
