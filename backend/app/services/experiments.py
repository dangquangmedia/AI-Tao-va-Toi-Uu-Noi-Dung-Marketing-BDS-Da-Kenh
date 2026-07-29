"""Chạy thí nghiệm đóng băng A–D trên frozen test set và chấm bằng kiểm định thống kê.

Ba thứ tách bạch trong file này:

1. **Snapshot** — trạng thái hệ thống lúc chạy (commit git, parser, embedding, prompt,
   trọng số retrieval, model + adapter fingerprint, kích thước split). Gate Tuần 6 đòi
   "mọi run có snapshot version"; không có nó thì bảng kết quả trong báo cáo không chứng
   minh được là chạy trên cùng điều kiện.
2. **Thống kê** — so sánh từng cặp cấu hình bằng **kiểm định hoán vị bắt cặp** (sign-flip)
   thay vì t-test: cỡ mẫu nhỏ, chỉ số là tỷ lệ nên không thể giả định phân phối chuẩn.
   Với n ≤ 18 kiểm định là **chính xác** (duyệt hết 2ⁿ tổ hợp dấu), lớn hơn thì Monte
   Carlo có seed cố định. Kèm khoảng tin cậy bootstrap và cỡ hiệu ứng Cohen's dz.
3. **Bộ chạy** — sinh nội dung cho từng brief × từng cấu hình rồi tổng hợp.

Nguyên tắc so sánh (Plan/03 §2): mọi cấu hình chạy trên **cùng bộ brief, cùng thứ tự,
cùng seed, cùng prompt version**. Mỗi cặp so sánh chỉ được khác đúng một biến — vì thế
`FACTOR_PAIRS` chỉ liệt kê bốn cặp hợp lệ, không so A với D.
"""

import itertools
import random
import statistics
import subprocess
import time
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Chunk,
    CleanListing,
    DatasetSplit,
    ExperimentRun,
    Fact,
    GraphEdge,
    Generation,
    RetrievalQuery,
)
from app.services.adapters import default_adapter_name, get_adapter
from app.services.generation import CONFIGS, USES_ADAPTER, USES_RETRIEVAL, run_generation
from app.services.prompts import CHANNEL_SPECS, PROMPT_VERSION
from app.services.query_router import DISCOVERY_WEIGHTS, INTENT_WEIGHTS
from app.services.retrieval import DEFAULT_WEIGHTS

# Cặp so sánh hợp lệ: mỗi cặp cô lập đúng một biến.
FACTOR_PAIRS = (
    ("A", "B", "retrieval"),
    ("C", "D", "retrieval"),
    ("A", "C", "adapter"),
    ("B", "D", "adapter"),
)

# Chỉ số so sánh: (khóa, nhãn, chiều tốt). "lower" = càng nhỏ càng tốt.
COMPARED_METRICS = (
    ("unsupported_claim_rate", "Tỷ lệ claim không có căn cứ", "lower"),
    ("structured_ok", "Đúng định dạng 3 phần", "higher"),
    ("length_ok", "Đúng khoảng độ dài của kênh", "higher"),
    ("n_claims", "Số claim mỗi bài", "higher"),
)
PRIMARY_METRIC = "unsupported_claim_rate"

EXACT_LIMIT = 14  # 2^14 = 16.384 tổ hợp × 16 phép so sánh — duyệt hết vẫn dưới một giây
BOOTSTRAP_ITERS = 10_000
PERMUTATION_ITERS = 20_000
STATS_SEED = 42


# ---------------------------------------------------------------- thống kê


def paired_permutation_test(diffs: list[float], seed: int = STATS_SEED) -> dict:
    """p-value hai phía cho giả thuyết "trung bình chênh lệch = 0".

    Giả thiết duy nhất: dưới giả thuyết không, dấu của mỗi chênh lệch có thể đảo mà phân
    phối không đổi (exchangeability) — đúng với thiết kế bắt cặp cùng brief. Không giả
    định phân phối chuẩn, nên dùng được cho tỷ lệ và cho n nhỏ.
    """
    values = [d for d in diffs if d is not None]
    n = len(values)
    if n == 0:
        return {"n": 0, "p_value": None, "method": "none"}
    observed = abs(statistics.fmean(values))
    if observed == 0:
        return {"n": n, "p_value": 1.0, "method": "exact" if n <= EXACT_LIMIT else "monte_carlo"}

    if n <= EXACT_LIMIT:
        extreme = sum(
            1
            for signs in itertools.product((1, -1), repeat=n)
            if abs(statistics.fmean([s * v for s, v in zip(signs, values)])) >= observed - 1e-12
        )
        return {"n": n, "p_value": round(extreme / 2**n, 5), "method": "exact"}

    rng = random.Random(seed)
    extreme = 0
    for _ in range(PERMUTATION_ITERS):
        flipped = [v if rng.random() < 0.5 else -v for v in values]
        if abs(statistics.fmean(flipped)) >= observed - 1e-12:
            extreme += 1
    # +1 ở tử/mẫu: ước lượng Monte Carlo không bao giờ được trả p = 0
    return {
        "n": n,
        "p_value": round((extreme + 1) / (PERMUTATION_ITERS + 1), 5),
        "method": "monte_carlo",
        "iters": PERMUTATION_ITERS,
    }


def bootstrap_ci(diffs: list[float], level: float = 0.95, seed: int = STATS_SEED) -> dict:
    """Khoảng tin cậy percentile cho trung bình chênh lệch (bootstrap có seed cố định)."""
    values = [d for d in diffs if d is not None]
    n = len(values)
    if n < 2:
        return {"low": None, "high": None, "level": level}
    rng = random.Random(seed)
    means = sorted(
        statistics.fmean([values[rng.randrange(n)] for _ in range(n)]) for _ in range(BOOTSTRAP_ITERS)
    )
    lo = means[int((1 - level) / 2 * BOOTSTRAP_ITERS)]
    hi = means[min(BOOTSTRAP_ITERS - 1, int((1 + level) / 2 * BOOTSTRAP_ITERS))]
    return {"low": round(lo, 4), "high": round(hi, 4), "level": level}


def cohens_dz(diffs: list[float]) -> float | None:
    """Cỡ hiệu ứng cho thiết kế bắt cặp: trung bình chênh lệch / độ lệch chuẩn chênh lệch."""
    values = [d for d in diffs if d is not None]
    if len(values) < 2:
        return None
    sd = statistics.stdev(values)
    if sd == 0:
        return None
    return round(statistics.fmean(values) / sd, 3)


def compare_paired(before: list[float], after: list[float], direction: str = "lower") -> dict:
    """So sánh hai cấu hình trên cùng bộ brief (bắt cặp theo chỉ số i)."""
    pairs = [(a, b) for a, b in zip(before, after) if a is not None and b is not None]
    if not pairs:
        return {"n": 0}
    diffs = [b - a for a, b in pairs]
    better = sum(1 for d in diffs if (d < 0 if direction == "lower" else d > 0))
    worse = sum(1 for d in diffs if (d > 0 if direction == "lower" else d < 0))
    return {
        "n": len(pairs),
        "mean_before": round(statistics.fmean([a for a, _ in pairs]), 4),
        "mean_after": round(statistics.fmean([b for _, b in pairs]), 4),
        "mean_diff": round(statistics.fmean(diffs), 4),
        "wins": better,
        "losses": worse,
        "ties": len(pairs) - better - worse,
        "cohens_dz": cohens_dz(diffs),
        "ci": bootstrap_ci(diffs),
        **{f"test_{k}": v for k, v in paired_permutation_test(diffs).items()},
    }


# ---------------------------------------------------------------- snapshot


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def build_snapshot(db: Session, tenant_id: str, dataset_version: str, adapter: dict | None) -> dict:
    """Ảnh chụp trạng thái hệ thống — mọi thứ có thể làm số đo đổi."""
    chunk_count = db.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.tenant_id == tenant_id)
    )
    embedded = db.scalar(
        select(func.count())
        .select_from(Chunk)
        .where(Chunk.tenant_id == tenant_id, Chunk.embedding.is_not(None))
    )
    facts = db.scalar(select(func.count()).select_from(Fact).where(Fact.tenant_id == tenant_id))
    edges = db.scalar(
        select(func.count()).select_from(GraphEdge).where(GraphEdge.tenant_id == tenant_id)
    )
    splits = dict(
        db.execute(
            select(DatasetSplit.split, func.count())
            .where(
                DatasetSplit.tenant_id == tenant_id,
                DatasetSplit.dataset_version == dataset_version,
            )
            .group_by(DatasetSplit.split)
        ).all()
    )
    gold = dict(
        db.execute(
            select(RetrievalQuery.difficulty, func.count())
            .where(
                RetrievalQuery.tenant_id == tenant_id,
                RetrievalQuery.dataset_version == dataset_version,
            )
            .group_by(RetrievalQuery.difficulty)
        ).all()
    )
    return {
        "git_commit": _git_commit(),
        "taken_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_version": dataset_version,
        "split_units": splits,
        "gold_queries": gold,
        "knowledge_base": {
            "chunks": chunk_count,
            "chunks_embedded": embedded,
            "facts": facts,
            "graph_edges": edges,
            "embedding_model": settings.embedding_model,
            "embedding_backend": settings.embedding_backend,
        },
        "retrieval": {
            "default_weights": dict(DEFAULT_WEIGHTS),
            # Router quyết trọng số theo việc câu hỏi có nêu tên dự án hay không (Tuần 6);
            # đổi hai bảng này là đổi context của cấu hình B/D nên phải nằm trong snapshot.
            "intent_weights": {k: dict(v) for k, v in INTENT_WEIGHTS.items()},
            "discovery_weights": dict(DISCOVERY_WEIGHTS),
        },
        "generation": {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "seed": settings.llm_seed,
            "max_new_tokens": settings.llm_max_new_tokens,
            "load_in_4bit": settings.llm_load_in_4bit,
            "prompt_version": PROMPT_VERSION,
        },
        "adapter": (
            {
                "name": adapter["name"],
                "base_model": adapter["base_model"],
                "fingerprint": adapter["fingerprint"],
                "card": adapter.get("card", {}),
            }
            if adapter
            else None
        ),
    }


# ---------------------------------------------------------------- chạy


def available_configs(requested: tuple[str, ...], adapter_name: str | None) -> tuple[list[str], dict]:
    """Lọc cấu hình chạy được. Thiếu adapter thì bỏ C/D **và ghi rõ lý do** vào run.

    Cố ý không làm sập cả lượt chạy: A/B vẫn có số, phần thiếu được ghi lại để báo cáo
    nói đúng rằng ô đó trống vì chưa có adapter chứ không phải vì kết quả xấu.
    """
    runnable, skipped = [], {}
    resolved = None
    for config in requested:
        if config not in CONFIGS:
            skipped[config] = "cấu hình không hợp lệ"
            continue
        if not USES_ADAPTER[config]:
            runnable.append(config)
            continue
        if resolved is None:
            try:
                name = adapter_name or default_adapter_name()
                if not name:
                    raise FileNotFoundError(
                        "chưa có adapter trong backend/models/adapters/ — xem training/README.md"
                    )
                resolved = get_adapter(name)
            except (FileNotFoundError, ValueError) as exc:
                resolved = exc
        if isinstance(resolved, Exception):
            skipped[config] = str(resolved)
        else:
            runnable.append(config)
    return runnable, skipped


PERSONAS = ("young_family", "investor", "first_home")


def pick_briefs(db: Session, tenant_id: str, dataset_version: str, n: int) -> list[dict]:
    """Bộ brief đóng băng: dự án thuộc split test có nhiều tin nhất, xoay vòng kênh × persona.

    Tất định theo (số tin giảm dần, slug) nên chạy lại lúc nào cũng ra đúng bộ đó —
    điều kiện để so sánh giữa hai lượt chạy khác thời điểm.
    """
    from app.services.dataset import split_of_listing  # tránh import vòng khi nạp module

    listing_split = split_of_listing(db, tenant_id, dataset_version)
    rows = db.scalars(
        select(CleanListing).where(
            CleanListing.tenant_id == tenant_id, CleanListing.project_slug.is_not(None)
        )
    ).all()

    by_project: dict[str, list[CleanListing]] = {}
    for row in rows:
        if listing_split.get(row.id) == "test":
            by_project.setdefault(row.project_slug, []).append(row)

    ranked = sorted(by_project.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:n]
    channels = list(CHANNEL_SPECS)
    briefs = []
    for i, (slug, members) in enumerate(ranked):
        name = next((m.project_name for m in members if m.project_name), slug)
        bedrooms = next((m.bedrooms for m in members if m.bedrooms), None)
        briefs.append(
            {
                "project_slug": slug,
                "channel": channels[i % len(channels)],
                "persona": PERSONAS[i % len(PERSONAS)],
                "brief": (
                    f"Giới thiệu {'căn ' + str(bedrooms) + ' phòng ngủ' if bedrooms else 'bất động sản'} "
                    f"tại dự án {name}"
                ),
            }
        )
    return briefs


def _word_count(text: str) -> int:
    return len(text.split())


def item_metrics(record: Generation) -> dict:
    """Chỉ số của một bài, tính lại từ bản ghi để không phụ thuộc thứ tự chạy."""
    if record.status != "done":
        return {}
    words = _word_count(f"{record.headline} {record.body} {record.cta}")
    lo, hi = CHANNEL_SPECS[record.channel]["words"]
    usage = record.metrics.get("usage") or {}
    budget = usage.get("completion_tokens")
    # Bài chạm trần token bị cắt giữa chừng: không thể kết luận model viết sai độ dài hay
    # chỉ là hết ngân sách sinh. Trả None để nó bị loại khỏi trung bình thay vì tính 0 —
    # kênh landing_seo (250–400 từ) luôn chạm trần khi chạy với 200 token.
    truncated = isinstance(budget, int) and budget >= settings.llm_max_new_tokens
    return {
        "unsupported_claim_rate": float(record.metrics.get("unsupported_claim_rate", 0.0)),
        "n_claims": float(record.metrics.get("n_claims", 0)),
        "n_forbidden": float(record.metrics.get("n_forbidden", 0)),
        # Đúng định dạng = tách được cả ba phần. Ngưỡng Plan/03: ≥ 95%.
        "structured_ok": 1.0 if (record.headline and record.body and record.cta) else 0.0,
        "length_ok": None if truncated else (1.0 if lo <= words <= hi else 0.0),
        "words": float(words),
        "latency_s": record.latency_ms / 1000,
    }


SUMMARY_KEYS = (
    "unsupported_claim_rate",
    "n_claims",
    "n_forbidden",
    "structured_ok",
    "length_ok",
    "words",
    "latency_s",
)


def summarize_config(records: list[Generation]) -> dict:
    ok = [r for r in records if r.status == "done"]
    if not ok:
        return {"n": 0, "n_failed": len(records)}
    scores = [item_metrics(r) for r in ok]
    summary = {"n": len(ok), "n_failed": len(records) - len(ok)}
    for key in SUMMARY_KEYS:
        values = [s[key] for s in scores if s.get(key) is not None]
        summary[key] = round(statistics.fmean(values), 4) if values else None
        if len(values) != len(scores):
            summary[f"{key}_n"] = len(values)  # số bài thực sự đo được chỉ số này
    summary["outputs_with_unsupported"] = sum(1 for s in scores if s["unsupported_claim_rate"] > 0)
    return summary


def compare_all(records_by_config: dict[str, list[Generation]]) -> list[dict]:
    """So sánh mọi cặp hợp lệ trên mọi chỉ số — chỉ khi cả hai cấu hình đều có số."""
    comparisons = []
    for left, right, factor in FACTOR_PAIRS:
        if left not in records_by_config or right not in records_by_config:
            continue
        left_scores = [item_metrics(r) for r in records_by_config[left]]
        right_scores = [item_metrics(r) for r in records_by_config[right]]
        entry = {"pair": f"{left}→{right}", "factor": factor, "metrics": {}}
        for metric, label, direction in COMPARED_METRICS:
            entry["metrics"][metric] = {
                "label": label,
                "direction": direction,
                **compare_paired(
                    [s.get(metric) for s in left_scores],
                    [s.get(metric) for s in right_scores],
                    direction,
                ),
            }
        comparisons.append(entry)
    return comparisons


def run_experiment(
    db: Session,
    tenant_id: str,
    created_by: str,
    briefs: list[dict],
    dataset_version: str,
    configs: tuple[str, ...] = CONFIGS,
    retrieval_config: str = "R3",
    k: int = 6,
    adapter_name: str | None = None,
    run_key: str | None = None,
    label: str = "",
    progress=None,
) -> ExperimentRun:
    """Chạy toàn bộ brief × cấu hình trong một lượt, ghi lại kèm snapshot.

    Thứ tự chạy là brief-ngoài / cấu hình-trong: mỗi brief được các cấu hình xử lý sát
    nhau nên nếu máy có trôi trạng thái (nhiệt, VRAM) thì trôi đều cho cả cặp bắt cặp.
    """
    runnable, skipped = available_configs(configs, adapter_name)
    if not runnable:
        raise ValueError(f"Không cấu hình nào chạy được: {skipped}")

    adapter = None
    if any(USES_ADAPTER[c] for c in runnable):
        adapter = get_adapter(adapter_name or default_adapter_name())

    run = ExperimentRun(
        tenant_id=tenant_id,
        created_by=created_by,
        run_key=run_key or f"run_{int(time.time())}",
        label=label,
        dataset_version=dataset_version,
        configs=runnable,
        skipped=skipped,
        snapshot=build_snapshot(db, tenant_id, dataset_version, adapter),
        n_briefs=len(briefs),
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    records: dict[str, list[Generation]] = {c: [] for c in runnable}
    try:
        for i, brief in enumerate(briefs, start=1):
            for config in runnable:
                record = run_generation(
                    db,
                    tenant_id=tenant_id,
                    created_by=created_by,
                    brief=brief["brief"],
                    channel=brief["channel"],
                    persona=brief["persona"],
                    config=config,
                    retrieval_config=retrieval_config if USES_RETRIEVAL[config] else "none",
                    project_slug=brief.get("project_slug"),
                    k=k,
                    adapter_name=adapter_name,
                )
                record.experiment_run_id = run.id
                db.add(record)
                db.commit()
                records[config].append(record)
                if progress:
                    progress(i, len(briefs), config, record)
    except Exception as exc:  # ghi lại lượt hỏng thay vì để mất toàn bộ tiến độ
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc}"[:500]
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise

    run.summary = {
        "by_config": {c: summarize_config(rows) for c, rows in records.items()},
        "comparisons": compare_all(records),
        "primary_metric": PRIMARY_METRIC,
    }
    run.status = "done"
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


def _fmt(value) -> str:
    return "—" if value is None else (f"{value:.4f}" if isinstance(value, float) else str(value))


def render_markdown(run: ExperimentRun, retrieval_report: dict | None = None) -> str:
    """Bảng kết quả cho báo cáo — sinh từ chính bản ghi run, không nhập tay."""
    snapshot = run.snapshot or {}
    gen = snapshot.get("generation", {})
    kb = snapshot.get("knowledge_base", {})
    lines = [
        f"# Thí nghiệm đóng băng `{run.run_key}`",
        "",
        f"> {run.label or 'Chạy frozen test set A–D'} · dataset `{run.dataset_version}` · "
        f"{run.n_briefs} brief × {len(run.configs)} cấu hình · commit `{snapshot.get('git_commit')}` · "
        f"{snapshot.get('taken_at')}.",
        "",
        "## 1. Snapshot (điều kiện chạy)",
        "",
        "| Thành phần | Giá trị |",
        "|---|---|",
        f"| Commit | `{snapshot.get('git_commit')}` |",
        f"| Dataset | `{run.dataset_version}` — split {snapshot.get('split_units')} |",
        f"| Gold query | {snapshot.get('gold_queries')} |",
        f"| Knowledge base | {kb.get('chunks')} chunk ({kb.get('chunks_embedded')} đã embed) · "
        f"{kb.get('facts')} fact · {kb.get('graph_edges')} cạnh graph |",
        f"| Embedding | `{kb.get('embedding_model')}` (backend `{kb.get('embedding_backend')}`) |",
        f"| Model sinh | `{gen.get('model')}` (provider `{gen.get('provider')}`, seed {gen.get('seed')}, "
        f"4-bit {gen.get('load_in_4bit')}) |",
        f"| Prompt | `{gen.get('prompt_version')}` |",
        f"| Trọng số RRF | `{snapshot.get('retrieval', {}).get('default_weights')}` |",
        f"| Adapter | {('`' + snapshot['adapter']['name'] + '` — fingerprint `' + snapshot['adapter']['fingerprint'] + '`') if snapshot.get('adapter') else '**chưa có**'} |",
    ]
    if run.skipped:
        lines += ["", "**Cấu hình bị bỏ qua:**", ""]
        lines += [f"- `{config}`: {reason}" for config, reason in run.skipped.items()]

    summary = run.summary or {}
    by_config = summary.get("by_config", {})
    lines += [
        "",
        "## 2. Kết quả theo cấu hình",
        "",
        "| Chỉ số | " + " | ".join(by_config) + " |",
        "|---|" + "---:|" * len(by_config),
    ]
    rows = [
        ("Số bài chạy được", "n"),
        ("Tỷ lệ claim không có căn cứ", "unsupported_claim_rate"),
        ("Bài có ≥1 claim vô căn cứ", "outputs_with_unsupported"),
        ("Số claim mỗi bài", "n_claims"),
        ("Câu chứa từ cấm", "n_forbidden"),
        ("Đúng định dạng 3 phần", "structured_ok"),
        ("Đúng khoảng độ dài kênh", "length_ok"),
        ("Số từ trung bình", "words"),
        ("Thời gian sinh (giây)", "latency_s"),
    ]
    for label, key in rows:
        cells = []
        for config in by_config:
            value = _fmt(by_config[config].get(key))
            measured = by_config[config].get(f"{key}_n")
            cells.append(f"{value} ({measured} bài)" if measured is not None else value)
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## 3. So sánh từng cặp (bắt cặp theo brief)",
        "",
        "Mỗi cặp chỉ khác **một biến**. `p` từ kiểm định hoán vị bắt cặp; `dz` là cỡ hiệu "
        "ứng Cohen cho thiết kế bắt cặp; khoảng tin cậy 95% từ bootstrap 10.000 lần, seed 42. "
        "Cột **số cặp** có thể nhỏ hơn số brief: cặp nào một bên không đo được chỉ số đó "
        "(ví dụ bài bị cắt vì hết token) thì bị loại khỏi phép so, không thay bằng 0.",
        "",
        "| Cặp | Biến đổi | Chỉ số | Số cặp | Trước | Sau | Chênh lệch | KTC 95% | Thắng/Thua | dz | p |",
        "|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for entry in summary.get("comparisons", []):
        for metric, data in entry["metrics"].items():
            if not data.get("n"):
                continue
            ci = data.get("ci", {})
            ci_text = (
                f"[{ci['low']}; {ci['high']}]" if ci.get("low") is not None else "—"
            )
            lines.append(
                f"| {entry['pair']} | {entry['factor']} | {data['label']} | {data['n']} | "
                f"{_fmt(data['mean_before'])} | {_fmt(data['mean_after'])} | {_fmt(data['mean_diff'])} | "
                f"{ci_text} | {data['wins']}/{data['losses']} | {_fmt(data.get('cohens_dz'))} | "
                f"{_fmt(data.get('test_p_value'))} |"
            )

    n = run.n_briefs
    lines += [
        "",
        f"**Cách đọc:** n = {n} brief. Kiểm định hoán vị với n nhỏ chỉ đạt được p tối thiểu "
        f"1/2^n = {1 / 2**n:.4f} — với n dưới ~10 thì *không thể* đạt p < 0,05 dù chênh lệch "
        "lớn đến đâu, nên cột p ở cỡ mẫu nhỏ chỉ để tham chiếu, chưa phải bằng chứng thống kê. "
        "Kết luận chỉ được rút khi chạy đủ cỡ mẫu của Plan/03 §4 (40–60 brief).",
    ]

    if retrieval_report and retrieval_report.get("configs"):
        lines += [
            "",
            "## 4. Truy xuất R1–R3 trên cùng snapshot",
            "",
            "| Cấu hình | project precision@k | listing recall@k | hit@k | MRR |",
            "|---|---:|---:|---:|---:|",
        ]
        for config, data in retrieval_report["configs"].items():
            o = data["overall"]
            lines.append(
                f"| {config} | {o['project_precision']:.3f} | {o['listing_recall']:.3f} | "
                f"{o['hit']:.3f} | {o['mrr']:.3f} |"
            )
    return "\n".join(lines) + "\n"
