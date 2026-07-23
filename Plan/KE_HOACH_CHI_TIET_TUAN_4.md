# Kế hoạch triển khai chi tiết Tuần 4

## Prompt-only và RAG baseline

**Thời gian:** 05/08/2026 - 11/08/2026  
**Phụ thuộc:** checkpoint Tuần 3, `dataset_v1`, `knowledge_snapshot_v1`, query set R1-R3 đã có expected evidence, fact/source editor đủ ổn định và graph quality report đã được ghi số liệu.  
**Mục tiêu tuần:** đưa cấu hình A prompt-only và B RAG chạy end-to-end trên web, hoàn thiện query router + R3 hybrid graph/vector context assembler, hiển thị evidence path trong Content Studio, ghi log đầy đủ prompt/retrieval/output/latency/cost và tạo baseline metrics để chuẩn bị QLoRA ở Tuần 5.

> Tuần 4 không mặc định Tuần 3 đã hoàn thành. Ngày đầu tiên phải kiểm tra bằng chứng thật: `dataset_v1`, `knowledge_snapshot_v1`, leakage audit, retrieval queries R1-R3, R1/R2 seed report, graph quality report, staging URL và blocker carry-over. Nếu dataset/snapshot chưa khóa, không chạy baseline A/B như kết quả nghiên cứu; chỉ được chạy smoke demo và ghi rõ trạng thái `not_verified`.

---

## 1. Demo bắt buộc cuối tuần

Đến cuối ngày 11/08, nhóm phải demo trên staging được luồng:

```text
Đăng nhập
→ mở Content Studio
→ chọn project thuộc `dataset_v1`
→ chọn brand, persona, channel và brief
→ chạy cấu hình A prompt-only
→ chạy cấu hình B RAG
→ query router phân loại yêu cầu
→ R3 context assembler lấy chunks + graph paths có provenance
→ generator trả structured output + claims
→ evidence panel hiển thị fact/chunk/source/path đã dùng
→ generation log lưu prompt version, retrieval snapshot, model config, latency và cost
→ mở dashboard baseline so sánh A/B và R1/R2/R3 seed metrics
```

Điều kiện bắt buộc:

1. Cấu hình A và B dùng cùng brief, channel, persona, brand và decoding policy.
2. Prompt baseline có version cố định, không chỉnh thủ công sau khi thấy kết quả.
3. R3 context assembler trả cùng contract cho UI và evaluation script: chunks, graph paths, citations, warnings và retrieval scores.
4. Generator output dùng structured JSON gồm `headline`, `body`, `cta`, `claims`, `warnings`, `model_config_id`, `prompt_version`, `knowledge_snapshot_id`.
5. Bản B không được tạo claim ngoài retrieved facts/relationships; claim thiếu nguồn phải có warning hoặc bị loại.
6. Evidence panel cho phép đi từ claim sang fact/chunk/source và graph path tối đa 2 hop.
7. Retrieval dashboard hiển thị R1, R2, R3 trên cùng query set R1-R3 với Recall@k/MRR/path precision/latency.
8. Generation baseline chạy tối thiểu 12-20 briefs đại diện cho 4 channel; nếu dữ liệu chưa đủ thì ghi rõ giới hạn.
9. Mọi run lưu raw prompt, retrieved context, output, evaluator version, latency, token/cost và error nếu có.
10. Có checkpoint report Tuần 4, bao gồm metric thực tế và blocker đưa sang Tuần 5.

---

## 2. Điều kiện đầu vào và kiểm tra checkpoint Tuần 3

### 2.1. Artefact cần có

- `docs/checkpoints/week_03_report.md`.
- `docs/data/dataset_v1_data_card.md`.
- `docs/data/dataset_v1_split_report.md`.
- `docs/data/dataset_v1_leakage_audit.md`.
- `docs/data/graph_quality_report_v1.md`.
- `docs/evaluation/retrieval_queries_v1.md`.
- `docs/evaluation/retrieval_seed_report_r1_r2.md`.
- Frozen `dataset_v1` và `knowledge_snapshot_v1`.
- R3 context assembler contract từ bàn giao Tuần 3.
- Fact/source editor và Source Viewer trên staging.
- Danh sách blocker: ingestion còn lỗi, labels thiếu, graph quality thấp hoặc UI chưa đủ ổn định.

### 2.2. Ma trận quyết định carry-over

| Checkpoint Tuần 3 | Nếu đạt | Nếu chưa đạt |
|---|---|---|
| `dataset_v1` frozen và có data card | Dùng làm input baseline | Chỉ chạy smoke; Quang + Hải freeze dataset trước trưa 05/08 |
| Split theo project + leakage audit pass | Chạy A/B trên test subset | Không báo metric nghiên cứu nếu còn leakage nghiêm trọng |
| `knowledge_snapshot_v1` có graph/chunk stats | Chạy R3 assembler | Chặn B/RAG baseline nếu snapshot không truy vết được |
| 60-90 retrieval queries có expected evidence | Đo R1-R3 | Hải hoàn thiện labels trước chiều 05/08 |
| R1/R2 seed eval có raw output | Mở rộng sang R3 | Quang sửa eval runner trước khi làm generation dashboard |
| Fact/source editor ổn định | Dùng Evidence panel liên kết source | Giữ evidence table đơn giản, cắt UI nâng cao |
| Graph quality đạt provenance coverage | Cho graph path vào prompt B | Loại edge thiếu source khỏi production context |

Nếu đến hết 05/08 còn blocker mức cao về dataset freeze, leakage, provenance hoặc tenant isolation, nhóm phải cắt Content Studio polish và dashboard đẹp để bảo vệ baseline tái lập.

---

## 3. Phạm vi Tuần 4

### Bắt buộc

- Audit checkpoint Tuần 3 và carry-over blocker.
- Prompt baseline versioning cho A/B.
- Model gateway tối thiểu cho generator API hoặc local model adapter demo.
- Query router v1.
- R3 hybrid graph + vector context assembler.
- Evidence citation contract: claim -> fact/chunk/relationship/source.
- Content Studio MVP: brief, channel, brand, persona, SEO fields, run A/B.
- Evidence panel hiển thị facts, chunks, sources và graph path.
- Generation logging và snapshot linkage.
- Retrieval eval R1/R2/R3 trên query set đã khóa.
- Generation baseline A/B trên subset test.
- Metrics report: retrieval, generation, latency, token/cost và failure cases.
- Staging demo và checkpoint report.

### Không làm trong Tuần 4

- QLoRA training hoặc chọn adapter cuối.
- Cấu hình C/D chính thức.
- Microsoft GraphRAG indexing.
- Vision extraction hàng loạt.
- Critic-refiner.
- Reviewer approve/reject/export production.
- Online A/B traffic thật.
- Auto-publish nội dung.
- Graph traversal sâu hơn 2 hop hoặc Neo4j.

---

## 4. Thiết kế baseline A/B và R3

### 4.1. Generation configs

```text
A_PROMPT_ONLY_V1
input: brief + channel + brand + persona + SEO
retrieval: none
generator: base generator configured through model gateway
output: structured JSON + claims + warnings

B_RAG_V1
input: same brief + channel + brand + persona + SEO
retrieval: R3 context assembler
generator: same base generator and decoding policy as A
output: structured JSON + claims + citations + warnings
```

Quy tắc:

- A và B dùng cùng model base trong Tuần 4.
- Không dùng fine-tuned adapter trong A/B.
- Không chỉnh temperature/max tokens giữa A và B trừ khi ghi thành config version.
- Nếu generator API ngoài thay đổi model, phải tạo `model_config_id` mới.
- Prompt không được chứa facts từ test answer hoặc expected evidence.

### 4.2. Query router v1

`query_router_v1` phân loại query thành:

```text
fact
one_hop
two_hop
comparison
conflict
temporal
global
no_evidence
mixed
```

Hành vi:

- `fact`: ưu tiên FTS/vector chunks.
- `one_hop` và `two_hop`: dùng entity detection + graph traversal tối đa 2 hop + chunks bổ trợ.
- `comparison`: lấy facts cùng schema cho các entity được so sánh.
- `conflict`: trả nhiều nguồn và gắn warning, không tự chọn nguồn nếu policy chưa chốt.
- `temporal`: filter `valid_from`/`valid_to` hoặc gắn `validity_unknown`.
- `no_evidence`: trả empty context + warning, không ép generation bịa.
- `global`: chưa dùng Microsoft GraphRAG trong Tuần 4; chỉ trả R1/R3 giới hạn hoặc warning.

### 4.3. R3 context assembler contract

Input:

```json
{
  "tenant_id": "...",
  "project_id": "...",
  "knowledge_snapshot_id": "knowledge_snapshot_v1",
  "query": "Tạo bài Facebook cho căn 2PN gần tiện ích trường học",
  "channel": "facebook",
  "persona_id": "...",
  "brand_profile_id": "...",
  "max_chunks": 8,
  "max_paths": 4,
  "max_hops": 2
}
```

Output:

```json
{
  "router": {
    "query_type": "mixed",
    "confidence": 0.82,
    "reason": "brief cần fact tiện ích và quan hệ căn hộ - tiện ích"
  },
  "chunks": [
    {
      "chunk_id": "...",
      "source_id": "...",
      "fact_ids": ["..."],
      "content": "...",
      "score": 0.91,
      "retriever": "fts_vector_rrf"
    }
  ],
  "paths": [
    {
      "path_id": "...",
      "nodes": ["UnitType", "Building", "Amenity"],
      "relationships": ["PART_OF", "HAS_AMENITY"],
      "relationship_ids": ["..."],
      "source_ids": ["..."],
      "score": 0.78
    }
  ],
  "citations": [
    {
      "citation_id": "...",
      "fact_id": "...",
      "source_id": "...",
      "relationship_id": null,
      "valid_from": null,
      "valid_to": null
    }
  ],
  "warnings": []
}
```

Không đưa vào prompt:

- fact/edge không có source;
- edge `pending` hoặc `rejected`;
- path vượt 2 hop;
- facts thuộc project/tenant khác;
- facts hết hiệu lực nếu query yêu cầu hiện tại.

---

## 5. Schema và migration cần bổ sung/khóa

### 5.1. `prompt_versions`

```text
id, tenant_id, name, version, config_type,
template_text, variables_json, output_schema_json,
status, created_by, created_at
```

`config_type`: `generation_a`, `generation_b`, `retrieval_router`, `context_assembler`, `judge`.

### 5.2. `model_configs`

```text
id, tenant_id, provider, model_name, config_name,
temperature, top_p, max_tokens, seed, json_mode,
cost_policy_json, status, created_by, created_at
```

### 5.3. `generation_briefs`

```text
id, tenant_id, project_id, dataset_version_id,
channel, persona_id, brand_profile_id,
brief_text, seo_json, constraints_json,
split_name, created_by, created_at
```

### 5.4. `generation_runs`

```text
id, tenant_id, project_id, brief_id, experiment_config,
dataset_version_id, knowledge_snapshot_id,
prompt_version_id, model_config_id,
retrieval_mode, status, input_hash,
latency_ms, prompt_tokens, completion_tokens,
estimated_cost, error_code, created_by, created_at
```

`experiment_config` trong Tuần 4 chỉ nhận `A_PROMPT_ONLY_V1` hoặc `B_RAG_V1`.

### 5.5. `generation_outputs`

```text
id, tenant_id, generation_run_id,
headline, body, cta, output_json,
warnings_json, raw_output, created_at
```

### 5.6. `generation_claims`

```text
id, tenant_id, generation_run_id,
claim_text, claim_type, supported_fact_ids_json,
supported_relationship_ids_json, source_ids_json,
support_status, created_at
```

`support_status`: `supported`, `unsupported`, `needs_review`, `not_applicable`.

### 5.7. `generation_context_items`

```text
id, tenant_id, generation_run_id,
context_type, chunk_id, fact_id, relationship_id,
source_id, path_id, score, position, metadata_json,
created_at
```

### 5.8. `retrieval_eval_runs`

```text
id, tenant_id, dataset_version_id, knowledge_snapshot_id,
retrieval_config, query_count, metrics_json,
latency_json, error_summary_json, raw_output_path,
created_by, created_at
```

### 5.9. `generation_eval_runs`

```text
id, tenant_id, dataset_version_id,
experiment_configs_json, brief_count,
metrics_json, raw_output_path,
evaluator_version, created_by, created_at
```

---

## 6. API và UI cần hoàn thiện trong Tuần 4

### Prompt/model config

```text
GET  /prompt-versions
POST /prompt-versions
GET  /model-configs
POST /model-configs
```

### Retrieval

```text
POST /retrieval/route
POST /retrieval/context
POST /retrieval/evaluate
GET  /retrieval/evaluation-runs/{run_id}
```

### Generation

```text
POST /projects/{project_id}/generation/briefs
GET  /projects/{project_id}/generation/briefs
POST /projects/{project_id}/generation/runs
GET  /projects/{project_id}/generation/runs/{run_id}
GET  /projects/{project_id}/generation/runs/{run_id}/evidence
POST /generation/evaluate
GET  /generation/evaluation-runs/{run_id}
```

### UI tối thiểu

- Content Studio:
  - chọn project;
  - chọn channel;
  - chọn brand/persona;
  - nhập brief và SEO keywords;
  - chọn cấu hình A hoặc B;
  - nút generate;
  - hiển thị output structured.
- Evidence Panel:
  - claim list;
  - linked facts/chunks/sources;
  - graph path table;
  - warnings cho unsupported/no-evidence.
- Baseline Dashboard:
  - bảng R1/R2/R3 retrieval metrics;
  - bảng A/B generation metrics;
  - latency/cost/error summary;
  - link raw runs.

RBAC đề xuất:

- `admin`: tạo prompt/model config, chạy eval batch, xem raw logs.
- `marketer`: tạo brief và generation run trong project được cấp quyền.
- `reviewer`: xem output/evidence/log, chưa approve/export trong Tuần 4.

---

## 7. Kế hoạch theo ngày

## Ngày 1 — 05/08: checkpoint audit và khóa baseline protocol

### Công việc

1. Chạy checklist đóng Tuần 3 trên staging thật.
2. Thu bằng chứng: data card, leakage audit, graph quality, R1/R2 report, query labels và snapshot IDs.
3. Lập `docs/checkpoints/week_04_carry_over.md` với owner/deadline/impact.
4. Chọn 12-20 briefs test subset cân bằng 4 channel và 3 persona nếu dữ liệu cho phép.
5. Khóa prompt baseline protocol:
   - A không retrieval;
   - B dùng R3;
   - cùng model/decoding;
   - cùng input;
   - cùng output schema.
6. Khóa metrics Tuần 4: retrieval Recall@k/MRR/path precision/latency và generation structured pass/unsupported claim/constraint pass/latency/cost.
7. Khóa rule không chỉnh prompt/model config sau khi thấy metric nếu không tạo version mới.

### Owner

- Quang: checkpoint kỹ thuật, baseline protocol, config schema.
- Hải: xác nhận query labels, brief subset và prompt baseline nội dung.
- Cả nhóm: quyết định blocker/cut scope.

### Đầu ra

- `docs/checkpoints/week_03_actual_status.md` hoặc cập nhật report hiện có.
- `docs/checkpoints/week_04_carry_over.md`.
- `docs/evaluation/baseline_protocol_v1.md`.
- `docs/evaluation/generation_briefs_v1.md`.

### Gate Ngày 1

- Dataset/snapshot/query set có trạng thái `pass/fail/not_verified`.
- Baseline protocol được khóa trước khi chạy hàng loạt.
- Nếu còn leakage/provenance blocker, không gọi kết quả là baseline nghiên cứu.

---

## Ngày 2 — 06/08: query router và R3 context assembler

### Công việc

1. Tạo `query_router_v1` theo taxonomy Tuần 3.
2. Tạo API `POST /retrieval/route`.
3. Tạo `context_assembler_r3_v1` hợp nhất FTS/vector chunks và graph paths.
4. Áp dụng filter bắt buộc: tenant, project, snapshot, review status, validity.
5. Implement Reciprocal Rank Fusion hoặc rule score có version cho R3.
6. Tạo `POST /retrieval/context` trả contract ở Mục 4.3.
7. Viết tests cho:
   - query fact chỉ lấy chunk đúng project;
   - query 1-hop/2-hop trả path đúng max 2 hop;
   - query no-evidence trả warning;
   - edge thiếu source không vào context;
   - tenant A không thấy context tenant B.
8. Chạy R1/R2/R3 eval seed trên query set đã khóa.

### Owner

- Quang: router, assembler, API, tests và eval runner.
- Hải: kiểm tra 20 query labels và phân tích lỗi truy xuất.

### Đầu ra

- `query_router_v1`.
- `context_assembler_r3_v1`.
- `docs/evaluation/retrieval_report_r1_r2_r3_week04.md`.
- Raw retrieval eval output.

### Gate Ngày 2

- R3 không dùng path thiếu source hoặc vượt 2 hop.
- R3 không trả dữ liệu xuyên tenant/project.
- R1/R2/R3 chạy cùng query set và lưu raw output.

---

## Ngày 3 — 07/08: prompt versions, model gateway và generation contract

### Công việc

1. Tạo migrations `prompt_versions`, `model_configs`, `generation_briefs`, `generation_runs`, `generation_outputs`, `generation_claims`, `generation_context_items`.
2. Seed `A_PROMPT_ONLY_V1` và `B_RAG_V1`.
3. Tạo model gateway có timeout, retry giới hạn, JSON-mode hoặc structured parsing.
4. Tạo output schema validator cho `headline`, `body`, `cta`, `claims`, `warnings`.
5. Tạo prompt renderer nhận variables: brief, channel, brand, persona, SEO, context.
6. Tạo generation service cho A:
   - không gọi retrieval;
   - lưu prompt/raw output/run metadata.
7. Tạo generation service cho B:
   - gọi R3 context assembler;
   - đưa context có citations vào prompt;
   - lưu context items và evidence.
8. Viết tests cho structured output, unsupported claim warnings, prompt version lock và error handling.

### Owner

- Quang: migrations, model gateway, generation service và tests.
- Hải: review prompt baseline tiếng Việt và channel rules.

### Đầu ra

- Prompt/model config seed.
- Generation service A/B.
- `docs/evaluation/prompt_baseline_v1.md`.
- Structured output validation report.

### Gate Ngày 3

- A và B dùng cùng model config trừ retrieval context.
- Mọi generation run có prompt version và model config.
- Invalid JSON output không được lưu như run thành công.

---

## Ngày 4 — 08/08: Content Studio và Evidence Panel

### Công việc

1. Tạo Content Studio page trong web app.
2. Form nhập brief gồm channel, persona, brand, SEO keywords và constraints.
3. Cho phép chọn cấu hình `A_PROMPT_ONLY_V1` hoặc `B_RAG_V1`.
4. Hiển thị generation output structured theo channel.
5. Tạo Evidence Panel:
   - claim list;
   - fact/chunk/source table;
   - graph path table;
   - warnings.
6. Tạo link từ evidence sang Source Viewer của Tuần 3.
7. Tạo loading/error/empty states cho generation và retrieval.
8. Chạy smoke test UI: tạo brief, chạy A, chạy B, mở evidence.

### Owner

- Quang: UI, API integration, state handling và smoke tests.
- Hải: kiểm tra nội dung output/evidence trên 5 briefs.

### Đầu ra

- Content Studio MVP trên staging.
- Evidence Panel có source/path.
- `docs/checkpoints/week_04_ui_smoke.md`.

### Gate Ngày 4

- User đi được từ output claim sang source evidence.
- Bản B hiển thị context/evidence; bản A hiển thị rõ không dùng retrieval.
- Frontend không gọi localhost trên staging.

---

## Ngày 5 — 09/08: baseline evaluation A/B và retrieval metrics

### Công việc

1. Chạy R1/R2/R3 trên toàn bộ retrieval queries đã khóa.
2. Tính Recall@5, Recall@10, MRR, path precision, unsupported-edge rate, no-evidence behavior và latency p50/p95.
3. Chạy A/B trên 12-20 generation briefs đã khóa.
4. Tính automatic generation metrics:
   - structured output pass rate;
   - unsupported claim rate;
   - constraint pass rate;
   - citation coverage cho B;
   - latency p50/p95;
   - token/cost mỗi output.
5. Lưu raw prompt, context, output và evaluator version.
6. Phân tích 10 failure cases ưu tiên: wrong project, no source, stale fact, malformed JSON, unsupported claim, long output, wrong channel.
7. Không kết luận C/D hoặc fine-tuning ở Tuần 4.

### Owner

- Quang: eval runner, metrics, raw logs và dashboard data.
- Hải: review failure cases và xác nhận unsupported claim labels.

### Đầu ra

- `docs/evaluation/retrieval_report_r1_r2_r3_week04.md`.
- `docs/evaluation/generation_baseline_a_b_week04.md`.
- Raw eval output dưới `experiments/generation/runs/` nếu repo code đã tồn tại.

### Gate Ngày 5

- R1/R2/R3 metrics dùng cùng query set và snapshot.
- A/B metrics dùng cùng brief subset và model config.
- Raw run đủ để tái lập hoặc audit từng output.

---

## Ngày 6 — 10/08: Baseline Dashboard, logging và staging hardening

### Công việc

1. Tạo Baseline Dashboard hiển thị:
   - R1/R2/R3 retrieval metrics;
   - A/B generation metrics;
   - latency/cost/error summary;
   - links đến raw runs/reports.
2. Bổ sung audit log cho prompt/model config changes.
3. Bổ sung request ID/run ID trong log generation và retrieval.
4. Test RBAC:
   - marketer tạo run trong project được cấp quyền;
   - reviewer xem evidence nhưng không sửa prompt config;
   - admin chạy eval batch.
5. Test budget guardrail: max tokens, timeout, retry limit và provider error.
6. Chạy backend tests, frontend lint/type-check/build.
7. Deploy staging release candidate.
8. Cập nhật runbook: run A/B baseline, run retrieval eval, inspect evidence, rollback prompt version.

### Owner

- Quang: dashboard, logging, RBAC, hardening, deploy và runbook.
- Hải: xác nhận dashboard metric interpretation.

### Đầu ra

- Baseline Dashboard trên staging.
- `docs/runbooks/baseline_generation_and_retrieval.md`.
- Staging release candidate Tuần 4.

### Gate Ngày 6

- Prompt/model config có audit trail.
- Role không đủ quyền không chạy được eval batch hoặc sửa config.
- Provider timeout/rate-limit không làm mất run metadata.

---

## Ngày 7 — 11/08: E2E, demo và đóng tuần

### Kiểm thử cuối

1. Chạy backend unit/integration tests cho router, R3 assembler, generation service, evidence contract, RBAC và eval runner.
2. Chạy frontend lint/type-check/build.
3. Chạy migration trên database sạch.
4. Chạy R1/R2/R3 eval từ đầu trên query set đã khóa.
5. Chạy A/B generation eval từ đầu trên brief subset đã khóa.
6. Kiểm tra thủ công 10 outputs A, 10 outputs B, 20 claims và 20 evidence links.
7. Smoke test staging từ máy/mạng khác.
8. Quay video demo dự phòng 5-7 phút.

### Kịch bản demo 7 phút

1. Login bằng marketer.
2. Mở Content Studio và chọn một project trong `dataset_v1`.
3. Nhập brief Facebook cho một persona cụ thể.
4. Chạy A prompt-only và xem output không có retrieval evidence.
5. Chạy B RAG và mở Evidence Panel.
6. Click một claim để xem fact, source và graph path tối đa 2 hop.
7. Mở Baseline Dashboard, xem R1/R2/R3 và A/B metrics.
8. Mở generation run log để thấy prompt version, model config, snapshot, latency và cost.

### Tổng kết

1. Ghi số liệu thực tế vào checkpoint Tuần 4.
2. Ghi issue còn mở, owner và ảnh hưởng Tuần 5.
3. Freeze `A_PROMPT_ONLY_V1`, `B_RAG_V1`, retrieval config R1-R3 và brief subset dùng cho so sánh sau.
4. Chốt input Tuần 5: SFT quality review, QLoRA pilot, reviewer/version/export flow và Microsoft GraphRAG sandbox gate.
5. Cập nhật nhật ký dự án và link tài liệu.

### Đầu ra

- `docs/checkpoints/week_04_report.md`.
- `docs/evaluation/baseline_protocol_v1.md`.
- `docs/evaluation/prompt_baseline_v1.md`.
- `docs/evaluation/retrieval_report_r1_r2_r3_week04.md`.
- `docs/evaluation/generation_baseline_a_b_week04.md`.
- `docs/runbooks/baseline_generation_and_retrieval.md`.
- Video/screenshot demo dự phòng.

### Gate đóng Tuần 4

- Demo bắt buộc ở Mục 1 chạy liên tục trên staging.
- A và B chạy end-to-end trên web với cùng input/model config.
- R3 context assembler trả chunks + graph paths + citations có provenance.
- Evidence Panel link claim -> fact/chunk/source/path hoạt động.
- R1/R2/R3 metrics có raw output và snapshot version.
- A/B baseline có raw prompt/context/output và automatic metrics.
- Không có lỗi severity cao về tenant isolation, provenance, prompt versioning hoặc unsupported claim không cảnh báo.

---

## 8. Phân công và RACI rút gọn

| Hạng mục | Quang | Hải | Cả nhóm |
|---|---|---|---|
| Checkpoint Tuần 3 và carry-over | R | C | A |
| Baseline protocol và prompt versions | R | C/A review | A |
| Query router và R3 context assembler | R/A | C labels | I |
| Retrieval eval R1-R3 | R | C/A evidence | A rubric |
| Model gateway và generation A/B | R/A | C prompt/content | I |
| Content Studio và Evidence Panel | R/A | C | I |
| Generation baseline labels/failure cases | C runner | R/A review | A |
| Dashboard/logging/staging | R/A | C | I |
| Demo/checkpoint | R | R | A |

`R`: thực hiện; `A`: chịu trách nhiệm cuối; `C`: tham vấn; `I`: được thông báo.

---

## 9. Test checklist

### Retrieval và R3

- [ ] Query router phân loại đúng query set seed theo taxonomy.
- [ ] R3 context filter theo tenant/project/snapshot.
- [ ] Graph traversal không vượt 2 hop.
- [ ] Edge thiếu source/pending/rejected không vào context.
- [ ] Query no-evidence trả warning/empty context.
- [ ] R1/R2/R3 eval lưu raw output và latency.

### Generation

- [ ] A không gọi retrieval.
- [ ] B gọi R3 và lưu context items.
- [ ] A/B dùng cùng model config và decoding policy.
- [ ] Output JSON pass schema hoặc run bị đánh failed.
- [ ] Claims có `supported_fact_ids` hoặc warning.
- [ ] Prompt/model config được version hóa.

### Evidence và UI

- [ ] Content Studio có loading/error/empty states.
- [ ] Evidence Panel link claim -> fact/chunk/source/path.
- [ ] Source Viewer mở được từ evidence.
- [ ] Bản A hiển thị rõ không có retrieval context.
- [ ] Baseline Dashboard hiển thị metric và link raw report.

### Security và operations

- [ ] Auth bắt buộc cho Content Studio và eval endpoints.
- [ ] Marketer không tạo/sửa prompt config.
- [ ] Reviewer không chạy eval batch nếu không có quyền.
- [ ] Admin actions có audit log.
- [ ] Provider timeout/rate-limit được lưu error code.
- [ ] Secret/API key không xuất hiện trong prompt/raw logs.

---

## 10. Metrics phải ghi trong checkpoint

### Retrieval

- Query count theo type.
- R1/R2/R3 Recall@5 và Recall@10.
- R1/R2/R3 MRR.
- R2/R3 path precision và unsupported-edge rate.
- No-evidence false positive rate.
- Retrieval latency p50/p95 theo config.
- Tỷ lệ result sai project/source.

### Generation A/B

- Brief count theo channel/persona.
- Structured output pass rate.
- Unsupported claim rate.
- Citation coverage của B.
- Constraint pass rate theo channel.
- Prompt tokens, completion tokens và estimated cost.
- Generation latency p50/p95.
- Provider error/rate-limit count.

### System và UI

- Test pass/fail/skip counts.
- API p50/p95 cho retrieval/context/generation/evidence.
- Dashboard load time.
- Số run có đầy đủ prompt/model/dataset/snapshot version.
- Số lỗi evidence link broken.

Không điều chỉnh prompt, metric hoặc sample sau khi thấy kết quả để làm đẹp báo cáo. Nếu thay đổi là cần thiết, tạo version mới và ghi trong report.

---

## 11. Rủi ro và phương án xử lý

| Rủi ro | Dấu hiệu sớm | Xử lý |
|---|---|---|
| Tuần 3 chưa freeze dataset/snapshot | Không có data card/leakage audit/snapshot ID | Carry-over freeze trước; chỉ smoke demo nếu chưa đủ bằng chứng |
| R3 context sai project | Evidence mismatch hoặc query trả fact tenant khác | Chặn release; bắt buộc metadata filter và tenant tests |
| Graph path yếu | R2/R3 path precision thấp | Giữ path trong evidence nhưng giảm trọng số hoặc warning; không cho claim nhạy cảm dùng edge yếu |
| Prompt-only A sinh nhiều hallucination | Unsupported claim rate cao | Báo đúng như baseline; không sửa output tay |
| B vẫn hallucinate dù có RAG | Claims không map source | Siết output schema, citation validation và warning; đưa failure sang Tuần 5 |
| Provider API lỗi/chi phí cao | Timeout/rate-limit hoặc token cost vượt budget | Cache/dev fixture, retry giới hạn, budget cap và fallback run nhỏ |
| Content Studio quá rộng | UI chậm, nhiều form chưa cần | Giữ 4 channel tối thiểu và evidence table; cắt polish/dashboard nâng cao |
| Metrics chưa ổn | Eval runner khác snapshot hoặc thiếu raw logs | Không báo kết quả nghiên cứu; sửa reproducibility trước |

---

## 12. Thứ tự cắt scope nếu thiếu thời gian

1. Baseline Dashboard đẹp; giữ Markdown/JSON reports.
2. Multiple prompt variants; giữ `A_PROMPT_ONLY_V1` và `B_RAG_V1`.
3. Channel-specific UI polish; giữ form chung cho 4 channel.
4. Reranker riêng; giữ FTS/vector/RRF + graph paths.
5. Batch generation lớn; giữ 12-20 briefs đại diện.
6. Advanced evidence visualization; giữ table/path/source links.
7. Judge LLM scoring sâu; giữ rule-based metrics và manual failure labels.

Không được cắt:

- Prompt/model versioning.
- A/B cùng input/model/decoding.
- R3 context assembler có provenance.
- R1/R2/R3 retrieval metrics.
- Evidence Panel claim -> source/path.
- Generation logging raw prompt/context/output.
- Tenant isolation/RBAC.
- Staging demo và checkpoint report.

---

## 13. Definition of Done Tuần 4

Tuần 4 chỉ hoàn thành khi:

- [ ] Checkpoint Tuần 3 đã được kiểm tra bằng bằng chứng và blocker được carry-over rõ.
- [ ] `A_PROMPT_ONLY_V1` và `B_RAG_V1` được version hóa.
- [ ] Query router v1 và R3 context assembler chạy với tenant/project/snapshot filters.
- [ ] R3 trả chunks, graph paths, citations và warnings theo contract.
- [ ] Content Studio chạy được A và B trên staging.
- [ ] Evidence Panel link claim -> fact/chunk/source/path hoạt động.
- [ ] Generation runs lưu prompt, model config, dataset, snapshot, context, output, latency và cost.
- [ ] R1/R2/R3 eval chạy trên query set đã khóa và có report.
- [ ] A/B generation baseline chạy trên brief subset đã khóa và có report.
- [ ] RBAC/tenant isolation pass cho prompt config, generation, evidence và eval endpoints.
- [ ] Có staging demo, checkpoint report và video/screenshot dự phòng.

---

## 14. Bàn giao sang Tuần 5

Tuần 4 phải bàn giao:

1. Frozen prompt versions `A_PROMPT_ONLY_V1` và `B_RAG_V1`.
2. Model config baseline và generation run logs.
3. R3 context assembler contract + retrieval report R1/R2/R3.
4. A/B generation baseline report và raw outputs.
5. Content Studio + Evidence Panel đủ ổn định để reviewer flow Tuần 5 dùng lại.
6. Failure cases ưu tiên cho QLoRA: hallucination, wrong channel, weak persona fit, malformed JSON, unsupported claim.
7. Danh sách blocker có owner: graph quality thấp, labels thiếu, provider không ổn định, UI evidence lỗi hoặc chi phí vượt budget.

Đầu vào này cho phép Tuần 5 tập trung vào QLoRA pilot/training, reviewer/version/export flow và Microsoft GraphRAG sandbox gate mà không phải quay lại khóa prompt baseline hoặc tranh luận RAG có đang dùng đúng evidence hay không.
