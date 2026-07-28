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
from app.services.retrieval import retrieve_r1, retrieve_r2

DEFAULT_K = 10
CONFIGS = ("R1-fts", "R1-vector", "R1-hybrid", "R2-graph")


def _run_config(db: Session, tenant_id: str, config: str, question: str, k: int) -> list[dict]:
    if config == "R1-fts":
        return retrieve_r1(db, tenant_id, question, k, mode="fts")
    if config == "R1-vector":
        return retrieve_r1(db, tenant_id, question, k, mode="vector")
    if config == "R1-hybrid":
        return retrieve_r1(db, tenant_id, question, k, mode="hybrid")
    if config == "R2-graph":
        return retrieve_r2(db, tenant_id, question, k)
    raise ValueError(f"Cấu hình retrieval không hợp lệ: {config}")


def score_results(query: RetrievalQuery, results: list[dict]) -> dict:
    """Chấm một truy vấn. Không có kết quả → mọi chỉ số bằng 0 (không bỏ qua câu hỏi)."""
    expected_listings = set(query.expected_listing_ids)
    expected_projects = {query.project_slug} if query.project_slug else set()

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
            results = _run_config(db, tenant_id, config, query.question, k)
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


def render_markdown(report: dict, embedding_model: str, dataset_version: str) -> str:
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
    return "\n".join(lines) + "\n"
