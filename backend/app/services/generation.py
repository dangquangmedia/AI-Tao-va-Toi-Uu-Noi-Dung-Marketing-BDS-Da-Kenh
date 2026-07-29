"""Sinh nội dung cấu hình A–D (Tuần 4–5, Plan/01 §5.1).

Ma trận thí nghiệm bắt buộc, khác nhau đúng **hai biến** — có retrieval hay không, có
QLoRA adapter hay không:

| Cấu hình | Retrieval | Adapter QLoRA |
|---|---|---|
| **A** — prompt-only | không | không |
| **B** — RAG | có | không |
| **C** — QLoRA | không | có |
| **D** — RAG + QLoRA | có | có |

Bốn cấu hình dùng **cùng prompt, cùng seed, cùng decoding** (greedy). Nhờ vậy chênh lệch
đo được quy về đúng đóng góp của từng biến, đúng điều kiện so sánh của Plan/03 §2.

Mỗi lần chạy ghi một dòng `generations` với đủ context id, prompt hash, model, adapter,
seed và kết quả chấm claim để tái lập và để dựng bảng A–D.
"""

import re
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CleanListing, Fact, Generation
from app.services.adapters import default_adapter_name, get_adapter
from app.services.chunking import PREDICATE_LABELS, _format_price, value_label
from app.services.claim_check import check_claims
from app.services.llm import get_generator
from app.services.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt, prompt_fingerprint
from app.services.retrieval import retrieve_r1, retrieve_r2, retrieve_r3

MAX_CONTEXT_CHUNKS = 6
MAX_CONTEXT_FACTS = 24
CHUNK_CHARS_IN_CONTEXT = 500
CONFIG_A, CONFIG_B, CONFIG_C, CONFIG_D = "A", "B", "C", "D"
CONFIGS = (CONFIG_A, CONFIG_B, CONFIG_C, CONFIG_D)
# Hai biến của ma trận, tra bằng bảng thay vì rải if rải rác cho khỏi lệch nhau
USES_RETRIEVAL = {CONFIG_A: False, CONFIG_B: True, CONFIG_C: False, CONFIG_D: True}
USES_ADAPTER = {CONFIG_A: False, CONFIG_B: False, CONFIG_C: True, CONFIG_D: True}
_PRICE_PREDICATES = {"total_price_vnd", "price_per_m2_vnd"}


def resolve_adapter(config: str, adapter_name: str | None = None) -> dict | None:
    """Adapter cho cấu hình C/D; A/B luôn chạy model gốc.

    Ném lỗi *có hướng dẫn* nếu C/D được gọi khi chưa bàn giao adapter — đây là ca xảy ra
    thường xuyên trong lúc Hải còn đang train.
    """
    if not USES_ADAPTER.get(config):
        return None
    name = adapter_name or default_adapter_name()
    if not name:
        raise FileNotFoundError(
            f"Cấu hình {config} cần LoRA adapter nhưng chưa có adapter nào được bàn giao. "
            "Copy thư mục adapter vào backend/models/adapters/ (xem training/README.md) "
            "hoặc đặt LLM_ADAPTER=<tên> nếu có nhiều adapter."
        )
    return get_adapter(name)


def _fact_line(fact: Fact) -> str:
    label = PREDICATE_LABELS.get(fact.predicate, fact.predicate)
    if fact.predicate in _PRICE_PREDICATES and fact.value_num:
        value = _format_price(fact.value_num)
    else:
        value = value_label(fact.value_text)
    suffix = f" (nguồn: {fact.source_url})" if fact.source_url else ""
    validity = f" [hiệu lực đến {fact.valid_to}]" if fact.valid_to else ""
    return f"- {label}: {value}{validity}{suffix}"


def _fact_payload(fact: Fact) -> dict:
    return {
        "fact_id": fact.id,
        "predicate": fact.predicate,
        "text": f"{PREDICATE_LABELS.get(fact.predicate, fact.predicate)}: {value_label(fact.value_text)}",
        "value_text": fact.value_text,
        "value_num": fact.value_num,
        "source_url": fact.source_url,
        "source_listing_id": fact.source_listing_id,
        "confidence": fact.confidence,
        "valid_from": fact.valid_from,
        "valid_to": fact.valid_to,
        "needs_review": fact.needs_review,
    }


def assemble_context(
    db: Session,
    tenant_id: str,
    query: str,
    retrieval_config: str = "R3",
    k: int = MAX_CONTEXT_CHUNKS,
) -> dict:
    """Lấy chunk + fact + đường đi graph cho cấu hình B, kèm khối text đưa vào prompt."""
    plan: dict = {}
    if retrieval_config == "R1":
        results = retrieve_r1(db, tenant_id, query, k, mode="hybrid")
    elif retrieval_config == "R2":
        results = retrieve_r2(db, tenant_id, query, k)
    else:
        results, plan = retrieve_r3(db, tenant_id, query, k)

    listing_ids = list(dict.fromkeys(r["clean_listing_id"] for r in results))[:k]
    listings = {
        row.id: row
        for row in db.scalars(
            select(CleanListing).where(
                CleanListing.tenant_id == tenant_id, CleanListing.id.in_(listing_ids)
            )
        ).all()
    }
    source_rows = [row.source_row_id for row in listings.values()]
    facts = (
        db.scalars(
            select(Fact)
            .where(Fact.tenant_id == tenant_id, Fact.source_row_id.in_(source_rows))
            .order_by(Fact.predicate)
        ).all()
        if source_rows
        else []
    )
    # Ngân sách context tỉ lệ với k: prompt dài làm chậm hẳn model 4-bit trên GPU nhỏ
    facts = facts[: min(MAX_CONTEXT_FACTS, max(k * 4, 8))]

    graph_paths = [r["path"] for r in results if r.get("path")][:3]

    blocks = []
    for fact in facts:
        blocks.append(_fact_line(fact))
    for result in results[:k]:
        snippet = result["text"][:CHUNK_CHARS_IN_CONTEXT].replace("\n", " ")
        blocks.append(f"- Trích tin đăng: {snippet} (nguồn: {result['source_url']})")
    for path in graph_paths:
        blocks.append(f"- Quan hệ trong knowledge graph: {' '.join(path)}")

    return {
        "results": results,
        "facts": facts,
        "fact_payloads": [_fact_payload(f) for f in facts],
        "graph_paths": graph_paths,
        "router_plan": plan,
        "context_block": "\n".join(blocks),
        "listings": listings,
    }


def parse_output(text: str) -> dict:
    """Tách HEADLINE / BODY / CTA. Model không tuân định dạng → coi toàn bộ là body."""
    headline = body = cta = ""
    head_match = re.search(r"HEADLINE\s*:\s*(.+)", text)
    cta_match = re.search(r"CTA\s*:\s*(.+)", text)
    body_match = re.search(r"BODY\s*:\s*(.*?)(?=\nCTA\s*:|\Z)", text, re.S)
    if head_match:
        headline = head_match.group(1).strip()
    if body_match:
        body = body_match.group(1).strip()
    if cta_match:
        cta = cta_match.group(1).strip()
    if not body:
        body = text.strip()
    return {"headline": headline, "body": body, "cta": cta}


def run_generation(
    db: Session,
    tenant_id: str,
    created_by: str,
    brief: str,
    channel: str,
    persona: str,
    config: str = CONFIG_B,
    retrieval_config: str = "R3",
    project_slug: str | None = None,
    brand: dict | None = None,
    k: int = MAX_CONTEXT_CHUNKS,
    adapter_name: str | None = None,
) -> Generation:
    if config not in CONFIGS:
        raise ValueError(f"Cấu hình không hợp lệ: {config} (phải là A, B, C hoặc D)")
    started = time.time()
    query = f"{project_slug or ''} {brief}".strip()
    adapter = resolve_adapter(config, adapter_name)

    context = (
        assemble_context(db, tenant_id, query, retrieval_config, k)
        if USES_RETRIEVAL[config]
        else {
            "results": [],
            "facts": [],
            "fact_payloads": [],
            "graph_paths": [],
            "router_plan": {},
            "context_block": "",
            "listings": {},
        }
    )

    user_prompt = build_user_prompt(
        channel=channel,
        persona=persona,
        brief=brief,
        context_block=context["context_block"] or None,
        brand=brand,
    )

    generator = get_generator(adapter)
    record = Generation(
        tenant_id=tenant_id,
        created_by=created_by,
        config=config,
        retrieval_config=retrieval_config if USES_RETRIEVAL[config] else "none",
        adapter_name=adapter["name"] if adapter else "",
        adapter_fingerprint=adapter["fingerprint"] if adapter else "",
        channel=channel,
        persona=persona,
        project_slug=project_slug,
        brief=brief,
        prompt_version=PROMPT_VERSION,
        prompt_hash=prompt_fingerprint(SYSTEM_PROMPT, user_prompt),
        model_name=getattr(generator, "name", "?"),
        provider=getattr(generator, "provider", "?"),
        seed=settings.llm_seed,
        context_chunk_ids=[r["chunk_id"] for r in context["results"]],
        context_fact_ids=[f.id for f in context["facts"]],
        graph_paths=context["graph_paths"],
        router_plan=context["router_plan"],
    )

    try:
        response = generator.generate(SYSTEM_PROMPT, user_prompt, seed=settings.llm_seed)
    except Exception as exc:  # model lỗi/OOM → ghi lại, không làm sập request
        record.status = "failed"
        record.error = f"{type(exc).__name__}: {exc}"[:500]
        record.latency_ms = int((time.time() - started) * 1000)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    parsed = parse_output(response.text)
    # Cấu hình không có retrieval (A, C) vẫn được chấm trên facts truy xuất được cho cùng
    # brief: chúng không "thấy" facts, nhưng để so sánh công bằng thì thước đo phải như nhau.
    reference_facts = context["fact_payloads"]
    if not USES_RETRIEVAL[config]:
        reference = assemble_context(db, tenant_id, query, "R3", k)
        reference_facts = reference["fact_payloads"]

    checked = check_claims(f"{parsed['headline']}\n{parsed['body']}\n{parsed['cta']}", reference_facts)

    record.headline = parsed["headline"]
    record.body = parsed["body"]
    record.cta = parsed["cta"]
    record.raw_output = response.text
    record.claims = checked["claims"]
    record.latency_ms = int((time.time() - started) * 1000)
    record.metrics = {
        **{k2: v for k2, v in checked.items() if k2 != "claims"},
        # Facts dùng làm chuẩn chấm claim. Với A/C (không truy xuất) đây không phải context
        # của prompt mà là tập tham chiếu để so sánh công bằng — lưu lại để lúc người biên
        # tập sửa nội dung còn chấm lại trên đúng tập fact đó.
        "reference_fact_ids": [f["fact_id"] for f in reference_facts],
        "n_context_chunks": len(context["results"]),
        "n_context_facts": len(context["facts"]),
        "n_graph_paths": len(context["graph_paths"]),
        "output_chars": len(response.text),
        "usage": response.usage,
    }
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
