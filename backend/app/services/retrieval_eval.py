"""Đánh giá retrieval R1/R2/R3 trên bộ gold query (Tuần 3, mở rộng Tuần 6; Plan/03 §4).

Các chỉ số, đều tính trên top-k và chỉ dùng nhãn suy ra tất định từ DB:

- **project_precision@k** — tỷ lệ kết quả trả về thuộc đúng dự án cần tìm. Đây là chỉ số
  quan trọng nhất với bài toán này: lấy nhầm dự án là sinh nội dung sai dữ kiện.
- **listing_precision@k** — tỷ lệ **tin phân biệt** lấy về trùng đúng tin kỳ vọng. Chặt hơn
  chỉ số trên và là chỉ số chính của bộ câu hỏi mô tả, nơi nhãn định nghĩa theo tin chứ
  không theo dự án. Tính trên tin phân biệt vì mỗi tin sinh ba chunk.
- **listing_recall@k** — bao nhiêu phần tin kỳ vọng được lấy về.
- **hit@k** — có ít nhất một kết quả đúng dự án hay không.
- **MRR** — nghịch đảo hạng của kết quả đúng đầu tiên.

Precision có **trần lý thuyết** `min(1, số tin đúng / số tin lấy về)`: câu hỏi chỉ có 4 đáp
án đúng mà hệ thống trả về 10 tin thì precision không thể vượt 0,4 dù nó hoàn hảo. Vì thế
bảng có thêm `listing_precision_norm` = precision chia cho trần — so sánh giữa các nhóm câu
hỏi có số đáp án khác nhau phải nhìn cột này, nếu không sẽ kết luận sai rằng nhóm ít đáp án
"khó hơn".

Cùng một hàm chấm dùng cho mọi cấu hình (R1-fts, R1-vector, R1-hybrid, R2, R3) nên bảng
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


METRICS = ("project_precision", "listing_precision", "listing_precision_norm", "listing_recall", "hit", "mrr")


def expected_project_set(query: RetrievalQuery) -> set[str]:
    """Tập dự án được coi là đúng cho một câu hỏi.

    Ưu tiên cột `expected_projects` (ghi thẳng lúc sinh câu hỏi). Với các bộ sinh trước
    Tuần 6 chưa có cột này thì suy từ `project_slug` + `expected_entities` như cũ, để số
    cũ vẫn tái lập được nguyên vẹn.
    """
    explicit = {p for p in (query.expected_projects or []) if p}
    if explicit:
        return explicit
    expected = {query.project_slug} if query.project_slug else set()
    # Câu so sánh có hai dự án đúng: nhãn thứ hai nằm trong expected_entities dưới dạng
    # slug (không dấu, không khoảng trắng), khác với nhãn địa danh/tòa ("Quận 7", "Tòa V8").
    expected |= {
        entity
        for entity in query.expected_entities
        if isinstance(entity, str) and " " not in entity and entity.islower()
    }
    return expected


def score_results(query: RetrievalQuery, results: list[dict], k: int = DEFAULT_K) -> dict:
    """Chấm một truy vấn. Không có kết quả → mọi chỉ số bằng 0 (không bỏ qua câu hỏi)."""
    expected_listings = set(query.expected_listing_ids)
    expected_projects = expected_project_set(query)

    correct_project = [r for r in results if r.get("project_slug") in expected_projects]
    # Precision theo tin phải tính trên **tin phân biệt**, không trên chunk: mỗi tin sinh ra
    # ba chunk (title/description/facts) nên đếm theo chunk cho phép một tin đúng chiếm
    # nhiều ô trong top-k, và tỷ lệ khi đó vượt cả trần lý thuyết.
    retrieved_listings = {r.get("clean_listing_id") for r in results if r.get("clean_listing_id")}
    correct_listing = expected_listings & retrieved_listings

    mrr = 0.0
    for rank, item in enumerate(results, start=1):
        if item.get("project_slug") in expected_projects:
            mrr = 1.0 / rank
            break

    listing_precision = len(correct_listing) / len(retrieved_listings) if retrieved_listings else 0.0
    # Trần lý thuyết khi số đáp án đúng ít hơn số tin lấy về — chia cho nó mới so sánh được
    # giữa các nhóm câu hỏi có số đáp án chênh nhau.
    ceiling = (
        min(1.0, len(expected_listings) / len(retrieved_listings))
        if expected_listings and retrieved_listings
        else 0.0
    )
    # Có câu hỏi mô tả mà **mọi** đáp án đúng đều là tin lẻ không thuộc dự án nào (nhà
    # riêng, nhà mặt phố). Chấm chúng 0 điểm ở nhóm chỉ số theo dự án là phạt oan, nên các
    # chỉ số đó trả None và bị loại khỏi trung bình thay vì bị tính bằng 0.
    has_projects = bool(expected_projects)

    return {
        "n_results": len(results),
        "n_expected": len(expected_listings),
        "project_precision": (len(correct_project) / len(results) if results else 0.0) if has_projects else None,
        "listing_precision": listing_precision,
        "listing_precision_norm": listing_precision / ceiling if ceiling else 0.0,
        "listing_recall": (
            len(correct_listing) / len(expected_listings) if expected_listings else 0.0
        ),
        "hit": (1.0 if correct_project else 0.0) if has_projects else None,
        "mrr": mrr if has_projects else None,
    }


def _mean_metrics(scores: list[dict]) -> dict:
    """Trung bình từng chỉ số, bỏ qua câu hỏi không chấm được chỉ số đó (giá trị None)."""
    out: dict = {"n": len(scores)}
    for metric in METRICS:
        values = [s[metric] for s in scores if s.get(metric) is not None]
        out[metric] = round(sum(values) / len(values), 4) if values else 0.0
        if len(values) != len(scores):
            out[f"{metric}_n"] = len(values)  # số câu thực sự tham gia trung bình
    out["n_expected_avg"] = round(sum(s["n_expected"] for s in scores) / len(scores), 1)
    return out


def evaluate(
    db: Session,
    tenant_id: str,
    dataset_version: str,
    configs: tuple[str, ...] = CONFIGS,
    k: int = DEFAULT_K,
    weights: dict | None = None,
    difficulty: str | None = None,
) -> dict:
    """Chạy toàn bộ gold query trên các cấu hình và tổng hợp theo nhóm câu hỏi + độ khó."""
    stmt = select(RetrievalQuery).where(
        RetrievalQuery.tenant_id == tenant_id,
        RetrievalQuery.dataset_version == dataset_version,
    )
    if difficulty:
        stmt = stmt.where(RetrievalQuery.difficulty == difficulty)
    queries = db.scalars(stmt.order_by(RetrievalQuery.query_type, RetrievalQuery.query_key)).all()
    if not queries:
        return {"queries": 0, "configs": {}}

    report: dict[str, dict] = {}
    for config in configs:
        per_type: dict[str, list[dict]] = defaultdict(list)
        per_difficulty: dict[str, list[dict]] = defaultdict(list)
        for query in queries:
            results = _run_config(db, tenant_id, config, query.question, k, weights)
            score = score_results(query, results, k)
            per_type[query.query_type].append(score)
            per_difficulty[query.difficulty or "standard"].append(score)

        flat = [s for scores in per_type.values() for s in scores]
        report[config] = {
            "overall": _mean_metrics(flat),
            "by_type": {t: _mean_metrics(s) for t, s in per_type.items()},
            "by_difficulty": {d: _mean_metrics(s) for d, s in per_difficulty.items()},
        }
    return {
        "queries": len(queries),
        "k": k,
        "difficulties": sorted({q.difficulty or "standard" for q in queries}),
        "configs": report,
    }


SWEEP_GRID = (
    {"vector": 1.0, "bm25": 0.3, "graph": 0.3},
    {"vector": 1.0, "bm25": 0.3, "graph": 0.6},
    {"vector": 1.0, "bm25": 0.3, "graph": 0.9},
    {"vector": 1.0, "bm25": 0.6, "graph": 0.3},
    {"vector": 1.0, "bm25": 0.6, "graph": 0.6},
    {"vector": 1.0, "bm25": 0.6, "graph": 0.9},
)


# Lưới riêng cho câu hỏi mô tả: bằng chứng Tuần 6 cho thấy nhánh graph mạnh nhất ở đây
# (project precision 0,465 so với 0,242 của vector và 0,115 của bm25), nên phải quét tới
# vùng trọng số graph cao — vùng mà lưới gốc không chạm tới.
DISCOVERY_GRID = (
    {"vector": 1.0, "bm25": 0.6, "graph": 0.3},  # cấu hình production hiện tại, làm mốc
    {"vector": 1.0, "bm25": 0.3, "graph": 0.9},
    {"vector": 1.0, "bm25": 0.3, "graph": 1.5},
    {"vector": 1.0, "bm25": 0.1, "graph": 2.0},
    {"vector": 0.6, "bm25": 0.1, "graph": 2.0},
    {"vector": 1.0, "bm25": 0.0, "graph": 3.0},
)


def sweep_weights(
    db: Session,
    tenant_id: str,
    dataset_version: str,
    k: int = DEFAULT_K,
    grid=SWEEP_GRID,
    difficulty: str | None = None,
) -> list[dict]:
    """Quét trọng số RRF của R3 trên gold query — cơ sở để chốt cấu hình production.

    `difficulty` cho phép quét riêng từng bộ: trọng số tốt cho câu hỏi nêu tên dự án
    không nhất thiết tốt cho câu hỏi mô tả, và trộn hai bộ lại thì bộ lớn hơn át bộ kia.
    """
    rows = []
    for weights in grid:
        report = evaluate(
            db,
            tenant_id,
            dataset_version,
            configs=("R3-fixed",),
            k=k,
            weights=weights,
            difficulty=difficulty,
        )
        overall = report["configs"]["R3-fixed"]["overall"]
        rows.append({"weights": weights, **overall})
    return sorted(rows, key=lambda r: (-r["project_precision"], -r["mrr"]))


def _sweep_table(rows: list[dict], title: str, note: str) -> list[str]:
    lines = [
        "",
        f"## {title}",
        "",
        note,
        "",
        "| vector | bm25 | graph | project precision@k | listing precision@k | listing recall@k | MRR |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        w = row["weights"]
        lines.append(
            f"| {w['vector']} | {w['bm25']} | {w['graph']} | {row['project_precision']:.3f} | "
            f"{row['listing_precision']:.3f} | {row['listing_recall']:.3f} | {row['mrr']:.3f} |"
        )
    return lines


def render_markdown(
    report: dict,
    embedding_model: str,
    dataset_version: str,
    sweep: list[dict] | None = None,
    sweep_hard: list[dict] | None = None,
) -> str:
    """Bảng kết quả cho báo cáo checkpoint — sinh từ chính số đo, không nhập tay."""
    if not report.get("configs"):
        return "# Đánh giá retrieval\n\nChưa có gold query.\n"

    lines = [
        "# Đánh giá retrieval R1 / R2 / R3 trên gold query",
        "",
        f"> Dataset `{dataset_version}` · {report['queries']} query · top-k = {report['k']} · "
        f"embedding `{embedding_model}`. Sinh bằng `python -m app.dataset_cli --eval`.",
        "",
        "## Tổng hợp",
        "",
        "| Cấu hình | project precision@k | listing precision@k | listing recall@k | hit@k | MRR |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for config, data in report["configs"].items():
        o = data["overall"]
        lines.append(
            f"| {config} | {o['project_precision']:.3f} | {o['listing_precision']:.3f} | "
            f"{o['listing_recall']:.3f} | {o['hit']:.3f} | {o['mrr']:.3f} |"
        )

    difficulties = [d for d in report.get("difficulties", []) if d]
    if len(difficulties) > 1:
        lines += [
            "",
            "## Tách theo độ khó của câu hỏi",
            "",
            "`standard` = câu hỏi **nêu tên dự án** (bộ Tuần 3). `hard` = câu hỏi mô tả theo "
            "thuộc tính / ngân sách / địa bàn, **không nêu tên dự án** (bộ Tuần 6). Chênh lệch "
            "giữa hai cột là phần precision đến từ khớp tên chứ không từ tìm kiếm.",
            "",
            "| Cấu hình | " + " | ".join(f"{d}: proj.prec | {d}: recall | {d}: MRR" for d in difficulties) + " |",
            "|---" + "|---:" * (3 * len(difficulties)) + "|",
        ]
        for config, data in report["configs"].items():
            cells = []
            for difficulty in difficulties:
                entry = data["by_difficulty"].get(difficulty)
                if entry:
                    cells += [
                        f"{entry['project_precision']:.3f}",
                        f"{entry['listing_recall']:.3f}",
                        f"{entry['mrr']:.3f}",
                    ]
                else:
                    cells += ["—", "—", "—"]
            lines.append(f"| {config} | " + " | ".join(cells) + " |")
        counts = ", ".join(
            f"{d} n={next(iter(report['configs'].values()))['by_difficulty'][d]['n']}"
            for d in difficulties
            if d in next(iter(report["configs"].values()))["by_difficulty"]
        )
        lines += ["", f"Số câu mỗi bộ: {counts}."]

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

    lines += [
        "",
        "## Theo nhóm câu hỏi (listing precision@k chuẩn hóa theo trần)",
        "",
        "Chia cho trần `min(1, số đáp án đúng / k)` — cột này mới so sánh được giữa các nhóm "
        "có số đáp án chênh nhau. Nhóm nêu tên dự án thường chỉ có vài tin đúng nên precision "
        "thô luôn thấp dù hệ thống trả về đúng hết.",
        "",
        "| Nhóm | số đáp án TB | " + " | ".join(report["configs"]) + " |",
        "|---|---:|" + "---:|" * len(report["configs"]),
    ]
    for query_type in all_types:
        cells = []
        for data in report["configs"].values():
            entry = data["by_type"].get(query_type)
            cells.append(f"{entry['listing_precision_norm']:.3f}" if entry else "—")
        avg = next(
            (
                data["by_type"][query_type]["n_expected_avg"]
                for data in report["configs"].values()
                if query_type in data["by_type"]
            ),
            0,
        )
        lines.append(f"| {query_type} | {avg} | " + " | ".join(cells) + " |")

    if sweep:
        lines += _sweep_table(
            sweep,
            "Sweep trọng số RRF của R3 (toàn bộ gold query)",
            "Xếp theo project precision. Trọng số này áp cho câu hỏi **có nêu tên dự án**.",
        )
        lines += ["", f"Trọng số chốt cho chế độ targeted: `{sweep[0]['weights']}`."]

    if sweep_hard:
        lines += _sweep_table(
            sweep_hard,
            "Sweep trọng số cho câu hỏi mô tả (bộ hard)",
            "Bảng xếp theo project precision, nhưng **quyết định không lấy dòng đầu**: tăng "
            "trọng số graph lên 1,5 đẩy project precision lên cao nhất trong khi *listing "
            "recall sụt gần một nửa* — nhánh graph kéo về đúng dự án nhưng không đúng tin, và "
            "còn chiếm chỗ của hai nhánh văn bản. Khâu sinh nội dung cần đúng **tin** để lấy "
            "fact, nên trọng số chốt theo listing precision/recall.",
        )
        best_hard = max(sweep_hard, key=lambda r: (r["listing_precision"], r["listing_recall"]))
        lines += [
            "",
            f"Trọng số chốt cho chế độ discovery: `{best_hard['weights']}` "
            f"(listing precision {best_hard['listing_precision']:.3f}, "
            f"recall {best_hard['listing_recall']:.3f}).",
        ]
    return "\n".join(lines) + "\n"
