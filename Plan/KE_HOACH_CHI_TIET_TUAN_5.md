# Kế hoạch triển khai chi tiết Tuần 5

## QLoRA, reviewer flow và GraphRAG research gate

**Thời gian:** 12/08/2026 - 18/08/2026  
**Phụ thuộc:** checkpoint Tuần 4, `A_PROMPT_ONLY_V1`, `B_RAG_V1`, A/B baseline report, R1/R2/R3 retrieval report, Content Studio + Evidence Panel chạy trên staging, `dataset_v1`/`knowledge_snapshot_v1` và SFT draft đã có claim -> fact mapping.  
**Mục tiêu tuần:** chạy pilot và huấn luyện QLoRA adapter đầu tiên cho cấu hình C, tích hợp reviewer/version/export flow vào sản phẩm, đồng thời chạy Microsoft GraphRAG trong sandbox trên corpus con để ra quyết định bằng số liệu: tiếp tục làm endpoint discovery ở Tuần 6 hay dừng ở kết quả nghiên cứu offline.

> Tuần 5 không mặc định Tuần 4 đã hoàn thành. Ngày đầu tiên phải kiểm tra bằng chứng thật: A/B baseline report, raw generation runs, prompt/model versions, R1-R3 retrieval report, Content Studio/Evidence Panel staging, SFT sample quality và GPU/API budget. Nếu A/B baseline hoặc SFT data chưa đủ truy vết, không chạy QLoRA như kết quả nghiên cứu chính thức; chỉ chạy technical smoke và ghi trạng thái `not_verified`.

---

## 1. Demo bắt buộc cuối tuần

Đến cuối ngày 18/08, nhóm phải demo được:

```text
Đăng nhập
→ mở Content Studio
→ chọn project/brief thuộc frozen subset
→ chạy cấu hình C fine-tuned model
→ output C lưu cùng schema với A/B
→ reviewer mở output, xem evidence/warnings
→ sửa nội dung hoặc ghi note
→ approve/reject
→ lưu content version mới
→ export bản approved
→ mở model/training dashboard xem adapter, dataset version, seed, loss, validation metric
→ mở GraphRAG research report và quyết định stop/continue gate
```

Điều kiện bắt buộc:

1. QLoRA adapter có `adapter_id`, `base_model`, `dataset_version`, `sft_sample_filter`, `seed`, `hyperparameters`, `training_log_path`, `validation_report_path` và `model_card_path`.
2. Adapter load được độc lập qua model gateway hoặc offline evaluation script.
3. Cấu hình C dùng cùng brief subset, output schema và evaluation contract với A/B.
4. Không đưa retrieval vào C; C là fine-tuned model không RAG để giữ ma trận A-D sạch.
5. Reviewer flow có trạng thái `generated -> needs_review -> approved/rejected -> exported`.
6. Mọi chỉnh sửa tạo `content_version` mới, không overwrite output gốc.
7. Export chỉ cho content `approved`, kèm metadata prompt/model/dataset/snapshot/source.
8. Microsoft GraphRAG chạy trong sandbox/batch, không nằm trên request path production.
9. GraphRAG gate có số liệu: indexing time/cost, query latency/cost, global/local query score, failure cases và so sánh với R3 trên subset khóa trước.
10. Có checkpoint report Tuần 5 với quyết định: tiếp tục endpoint GraphRAG discovery hoặc dừng ở nghiên cứu offline/negative result.

---

## 2. Điều kiện đầu vào và kiểm tra checkpoint Tuần 4

### 2.1. Artefact cần có

- `docs/checkpoints/week_04_report.md`.
- `docs/evaluation/baseline_protocol_v1.md`.
- `docs/evaluation/prompt_baseline_v1.md`.
- `docs/evaluation/retrieval_report_r1_r2_r3_week04.md`.
- `docs/evaluation/generation_baseline_a_b_week04.md`.
- Frozen prompt versions `A_PROMPT_ONLY_V1` và `B_RAG_V1`.
- Model config baseline và raw generation run logs.
- R3 context assembler contract.
- Content Studio + Evidence Panel chạy trên staging.
- `dataset_v1`, SFT draft v1 và quality status `gold/silver/draft/rejected`.
- Failure cases ưu tiên cho QLoRA: hallucination, wrong channel, weak persona fit, malformed JSON, unsupported claim.
- GPU/API/budget note cho QLoRA và GraphRAG sandbox.

### 2.2. Ma trận quyết định carry-over

| Checkpoint Tuần 4 | Nếu đạt | Nếu chưa đạt |
|---|---|---|
| A/B baseline có raw runs và metric | Dùng làm baseline so C | Không báo C improvement; chạy smoke adapter thôi |
| Content Studio/Evidence Panel ổn định | Tích hợp reviewer flow | Giữ reviewer flow table/form đơn giản, cắt polish |
| Prompt/model versions đã freeze | Dùng cùng output contract cho C | Khóa version trước khi train/eval |
| SFT draft có gold/silver đủ | Train QLoRA pilot | Chỉ train trên gold/silver đã audit; giảm volume nếu cần |
| Failure cases rõ | Dùng làm mục tiêu validation | Hải bổ sung taxonomy trước pilot |
| GPU/budget sẵn sàng | Chạy pilot + main run | Chốt rental/API fallback trước chiều 12/08 |
| R3 report có global/local subset | So GraphRAG với R3 | Giới hạn GraphRAG thành indexing/cost study |

Nếu đến hết 12/08 còn blocker mức cao về A/B baseline, SFT quality, GPU hoặc staging reviewer flow, nhóm phải cắt GraphRAG endpoint exploration và export polish để bảo vệ QLoRA + review/version core.

---

## 3. Phạm vi Tuần 5

### Bắt buộc

- Audit checkpoint Tuần 4 và carry-over blocker.
- SFT quality review và training subset lock.
- QLoRA pilot trên 1-2 backbone hoặc 1 backbone + nhiều hyperparameter nhỏ nếu tài nguyên hạn chế.
- Main QLoRA run đầu tiên có adapter load được.
- Model registry, training run tracking và model card.
- Cấu hình C fine-tuned generation chạy theo cùng contract A/B.
- Reviewer flow: review note, approve/reject, version history.
- Export bản approved tối thiểu Markdown/HTML hoặc DOCX/PDF nếu hạ tầng đã sẵn.
- Automatic validation C trên brief subset đã khóa.
- Microsoft GraphRAG sandbox trên corpus con, có stop/continue gate.
- Checkpoint report, runbook train/eval/reviewer/export.

### Không làm trong Tuần 5

- Cấu hình D RAG + fine-tuned chính thức.
- Chạy full frozen A-D evaluation.
- Vision extraction hàng loạt.
- Critic-refiner.
- Production GraphRAG endpoint nếu gate chưa đạt.
- DPO/preference training.
- Online A/B traffic thật.
- Auto-publish nội dung.
- Graph traversal production sâu hơn 2 hop.

---

## 4. Thiết kế QLoRA và cấu hình C

### 4.1. Training data policy

Chỉ dùng sample:

```text
dataset_version = dataset_v1
quality_status in ["gold", "silver"]
split_name in ["train", "validation"]
has_claim_mapping = true
has_forbidden_claim_violation = false
source_provenance_complete = true
```

Không dùng:

- `draft` chưa review;
- sample thuộc `test`;
- sample có project leak;
- output synthetic chưa có reviewer;
- sample thiếu claim -> fact mapping;
- claim pháp lý/giá/tiến độ không có validity/provenance.

### 4.2. Cấu hình thí nghiệm C

```text
C_FINE_TUNED_V1
retrieval: none
base_model: selected 7B-8B instruction model
adapter: qlora_adapter_v1
input: same brief + channel + brand + persona + SEO as A/B
output: same structured JSON schema
decoding: locked model_config, comparable with A/B where possible
```

Quy tắc:

- C không dùng RAG trong Tuần 5.
- C không được xem facts ngoài input theo sample schema.
- C dùng cùng brief subset để so với A/B smoke.
- C được đánh giá chủ yếu về structured output, channel fit, persona/brand fit, unsupported claim và malformed JSON.
- Nếu C chưa tốt hơn A/B, vẫn ghi negative/neutral result; không đổi test set để làm đẹp.

### 4.3. Pilot strategy

Ưu tiên:

1. Chọn 1 backbone chính bằng tiêu chí tiếng Việt, license, VRAM, JSON output và QLoRA support.
2. Chạy pilot 100-200 samples nếu dữ liệu đủ; nếu ít hơn, dùng toàn bộ gold/silver train và ghi số lượng.
3. Thử rank 8 và 16 trước; chỉ lên 32 nếu validation còn cải thiện và VRAM cho phép.
4. Learning rate thử trong khoảng `1e-5` đến `2e-4`.
5. Sequence length dựa trên percentile thực tế của SFT samples, không chọn quá dài gây OOM.
6. Lưu train/validation loss, structured output pass, channel rule pass và sample outputs.

### 4.4. Model card tối thiểu

`docs/models/qlora_adapter_v1_model_card.md` phải ghi:

- base model và license;
- dataset version và sample counts;
- preprocessing/template;
- hyperparameters;
- compute environment;
- intended use;
- limitations;
- known failure cases;
- evaluation summary;
- không dùng adapter để lưu kiến thức dự án thay retrieval.

---

## 5. Thiết kế reviewer/version/export flow

### 5.1. State machine content

```text
generated
→ needs_review
→ approved
→ exported
```

Nhánh khác:

```text
needs_review
→ rejected
→ revised
→ needs_review
```

Quy tắc:

- Generated output ban đầu không bị overwrite.
- Reviewer sửa nội dung thì tạo version mới.
- Export chỉ chạy với `approved`.
- Output có claim nhạy cảm hoặc unsupported warning không được approve nếu chưa có reviewer note xử lý.
- Reviewer note là audit artifact, không phải comment tạm.

### 5.2. Export scope Tuần 5

Bắt buộc:

- Markdown hoặc HTML export có metadata.
- File name ổn định: project, channel, content item, version.
- Metadata gồm: generation run, model config, prompt version, dataset version, knowledge snapshot, reviewer, approved time.

Nếu còn thời gian:

- DOCX hoặc PDF export.
- Export template theo channel.

Không bắt buộc Tuần 5:

- Auto-publish Facebook/email.
- Multi-language export.
- Brand-styled PDF đẹp.

---

## 6. Microsoft GraphRAG sandbox và gate

### 6.1. Corpus con

Chọn một corpus đại diện:

- 1 project lớn hoặc 2-3 project có nhiều source;
- có đủ facts/chunks/sources;
- không chứa dữ liệu thiếu license/provenance;
- có nhóm queries `global`, `comparison`, `entity-centric`, `community summary`.

### 6.2. So sánh với R3

Chạy cùng query subset:

```text
R3_GRAPH_VECTOR_V1
R4_GRAPHRAG_SANDBOX_V1
```

Metric bắt buộc:

- indexing duration;
- indexing token/cost;
- query latency p50/p95;
- query token/cost;
- answer comprehensiveness trên global queries;
- evidence/source traceability;
- entity/relationship extraction error;
- hallucinated community/entity rate;
- failure cases.

### 6.3. Stop/continue gate

Chỉ tiếp tục làm endpoint discovery Tuần 6 nếu:

1. R4 cải thiện rõ trên global/community queries so với R3 theo rubric đã khóa.
2. R4 không làm giảm source traceability dưới ngưỡng chấp nhận.
3. Indexing/query cost nằm trong budget demo đã công bố.
4. Không ảnh hưởng tiến độ A-D bắt buộc.
5. Có failure analysis và runbook tái lập.

Nếu không đạt, quyết định là:

```text
GraphRAG dừng ở nghiên cứu offline/negative result.
Production tiếp tục dùng PostgreSQL Property Knowledge Graph + FTS + pgvector R3.
```

---

## 7. Schema và migration cần bổ sung/khóa

### 7.1. `training_runs`

```text
id, tenant_id, dataset_version_id, run_name,
base_model, adapter_name, status, sample_filter_json,
hyperparameters_json, seed, train_sample_count,
validation_sample_count, started_at, finished_at,
training_log_path, metrics_json, error_summary_json,
created_by, created_at
```

### 7.2. `model_artifacts`

```text
id, tenant_id, training_run_id, artifact_type,
artifact_name, storage_key, checksum, base_model,
adapter_config_json, tokenizer_config_json,
model_card_path, status, created_at
```

`artifact_type`: `adapter`, `tokenizer`, `config`, `model_card`, `eval_report`.

### 7.3. `experiment_configs`

```text
id, tenant_id, config_name, config_type,
retrieval_mode, model_config_id, adapter_artifact_id,
prompt_version_id, dataset_version_id,
knowledge_snapshot_id, status, created_by, created_at
```

Trong Tuần 5 thêm `C_FINE_TUNED_V1`.

### 7.4. `content_items`

```text
id, tenant_id, project_id, channel,
title, current_version_id, status,
created_by, created_at, updated_at
```

### 7.5. `content_versions`

```text
id, tenant_id, content_item_id, generation_run_id,
version_number, headline, body, cta,
output_json, editor_id, change_summary,
created_at
```

### 7.6. `content_reviews`

```text
id, tenant_id, content_item_id, content_version_id,
reviewer_id, decision, note, reason_code,
created_at
```

`decision`: `approve`, `reject`, `request_changes`.

### 7.7. `content_exports`

```text
id, tenant_id, content_item_id, content_version_id,
export_format, storage_key, filename, metadata_json,
exported_by, exported_at
```

### 7.8. `graphrag_research_runs`

```text
id, tenant_id, run_name, corpus_description,
dataset_version_id, knowledge_snapshot_id,
query_set_path, status, indexing_metrics_json,
query_metrics_json, comparison_report_path,
decision, created_by, created_at
```

`decision`: `continue_endpoint_discovery`, `offline_only`, `failed_not_reliable`.

---

## 8. API và UI cần hoàn thiện trong Tuần 5

### Training/model

```text
POST /training/runs
GET  /training/runs
GET  /training/runs/{run_id}
GET  /model-artifacts
GET  /model-artifacts/{artifact_id}
POST /experiment-configs
GET  /experiment-configs
```

### Generation C

```text
POST /projects/{project_id}/generation/runs
GET  /projects/{project_id}/generation/runs/{run_id}
POST /generation/evaluate
```

`POST /generation/runs` phải nhận `experiment_config = C_FINE_TUNED_V1`.

### Reviewer/version/export

```text
GET  /projects/{project_id}/content-items
POST /projects/{project_id}/content-items
GET  /content-items/{content_item_id}
GET  /content-items/{content_item_id}/versions
POST /content-items/{content_item_id}/versions
POST /content-items/{content_item_id}/reviews
POST /content-items/{content_item_id}/exports
GET  /content-items/{content_item_id}/exports
```

### GraphRAG research

```text
POST /research/graphrag/runs
GET  /research/graphrag/runs
GET  /research/graphrag/runs/{run_id}
POST /research/graphrag/runs/{run_id}/decision
```

### UI tối thiểu

- Model/Training Dashboard: run status, base model, dataset, seed, loss, validation metrics, adapter link.
- Content Review: generated output, evidence/warnings, reviewer notes, approve/reject/request changes.
- Version History: version list, diff summary, model/prompt/run metadata.
- Export Panel: approved version, format, generated file, metadata.
- GraphRAG Research Report: corpus, cost, latency, metric table, decision gate.

RBAC đề xuất:

- `admin`: tạo training run, tạo experiment config, export, xem GraphRAG cost.
- `marketer`: tạo content item, sửa version, gửi review.
- `reviewer`: approve/reject/request changes.
- `viewer`: chỉ xem approved content và reports nếu được cấp quyền.

---

## 9. Kế hoạch theo ngày

## Ngày 1 — 12/08: checkpoint audit, SFT quality và training protocol

### Công việc

1. Chạy checklist đóng Tuần 4 trên staging thật.
2. Thu bằng chứng: A/B baseline, R1-R3 report, raw runs, prompt/model versions, Content Studio/Evidence Panel.
3. Lập `docs/checkpoints/week_05_carry_over.md` với owner/deadline/impact.
4. Audit SFT samples:
   - sample counts theo channel/persona/split/status;
   - claim -> fact mapping;
   - forbidden claim violations;
   - malformed output;
   - duplicated prompts/outputs.
5. Khóa `sft_train_filter_v1`.
6. Chọn base model chính bằng bảng: license, Vietnamese quality, VRAM, JSON behavior, QLoRA support.
7. Khóa QLoRA protocol: sample filter, hyperparameter grid nhỏ, seed, validation metrics và artifact naming.
8. Khóa GraphRAG corpus con và query subset.

### Owner

- Hải: SFT quality review, base model shortlist, GraphRAG corpus/query subset.
- Quang: checkpoint kỹ thuật, training tracking schema, app carry-over.
- Cả nhóm: quyết định cut scope nếu thiếu GPU/data.

### Đầu ra

- `docs/checkpoints/week_04_actual_status.md` hoặc cập nhật report hiện có.
- `docs/checkpoints/week_05_carry_over.md`.
- `docs/models/qlora_training_protocol_v1.md`.
- `docs/data/sft_quality_report_v1.md`.
- `docs/research/graphrag_corpus_plan_v1.md`.

### Gate Ngày 1

- Không train trên sample `draft` hoặc test split.
- Base model được chọn bằng tiêu chí ghi rõ.
- GPU/budget có phương án trước khi chạy pilot.

---

## Ngày 2 — 13/08: training infrastructure và reviewer schema

### Công việc

1. Tạo migrations cho `training_runs`, `model_artifacts`, `experiment_configs`, `content_items`, `content_versions`, `content_reviews`, `content_exports`, `graphrag_research_runs`.
2. Tạo training run registry và model artifact registry.
3. Tạo script/runbook training nhận input:
   - dataset version;
   - sample filter;
   - base model;
   - hyperparameters;
   - output directory;
   - seed.
4. Tạo reviewer/version/export APIs skeleton.
5. Tạo state machine content và server-side permission checks.
6. Viết tests cho:
   - không export content chưa approved;
   - reviewer decision tạo audit record;
   - content edit tạo version mới;
   - marketer không approve thay reviewer;
   - training run lưu dataset/model/hyperparameter.

### Owner

- Quang: migrations, APIs, state machine, tests.
- Hải: xác nhận training script inputs và artifact naming.

### Đầu ra

- Training/model registry skeleton.
- Reviewer/version/export API skeleton.
- `docs/runbooks/qlora_training.md` bản đầu.

### Gate Ngày 2

- Migration clean/upgrade pass.
- Content state transition bất hợp lệ bị chặn.
- Training artifact không tồn tại nếu run failed.

---

## Ngày 3 — 14/08: QLoRA pilot và Content Review UI

### Công việc

1. Chạy QLoRA pilot trên training subset đã khóa.
2. Lưu training logs, memory usage, loss curve, sample outputs và validation summary.
3. Nếu pilot OOM, giảm sequence length/batch size/rank theo protocol và ghi quyết định.
4. Tạo `C_FINE_TUNED_V1_CANDIDATE` experiment config nếu adapter load được.
5. Tạo Content Review UI:
   - output;
   - evidence/warnings;
   - reviewer note;
   - approve/reject/request changes.
6. Tạo Version History UI: list versions, metadata, change summary.
7. Chạy smoke: lấy output A/B Tuần 4, tạo content item, gửi review, approve/reject.

### Owner

- Hải: QLoRA pilot, loss/output review, failure analysis.
- Quang: Content Review UI, Version History UI, experiment config integration.

### Đầu ra

- `docs/models/qlora_pilot_report_v1.md`.
- Adapter candidate hoặc failure report có nguyên nhân.
- Content Review UI trên staging.

### Gate Ngày 3

- Pilot có log và validation output.
- Adapter candidate chỉ được tạo nếu load thành công.
- Reviewer action tạo review record và không overwrite version cũ.

---

## Ngày 4 — 15/08: main QLoRA run, cấu hình C và export MVP

### Công việc

1. Chạy main QLoRA run theo hyperparameter được chọn từ pilot.
2. Lưu adapter, tokenizer/config, checksum và model card draft.
3. Tích hợp adapter vào model gateway hoặc offline generation runner.
4. Tạo `C_FINE_TUNED_V1` nếu main adapter load được.
5. Chạy C trên 5-10 briefs smoke, cùng schema A/B.
6. Tạo export MVP:
   - Markdown/HTML;
   - metadata block;
   - stable filename;
   - storage key.
7. Chặn export nếu content chưa approved.
8. Viết tests cho export metadata và approved-only policy.

### Owner

- Hải: main QLoRA run, adapter/model card, C smoke outputs.
- Quang: model gateway integration, C generation config, export service/UI.

### Đầu ra

- `qlora_adapter_v1` hoặc `qlora_adapter_v1_candidate` với trạng thái rõ.
- `docs/models/qlora_adapter_v1_model_card.md`.
- `C_FINE_TUNED_V1` generation smoke.
- Export MVP trên staging.

### Gate Ngày 4

- Adapter load được độc lập.
- C output pass structured schema trong smoke run.
- Export chỉ chạy với approved version.

---

## Ngày 5 — 16/08: GraphRAG sandbox và validation C

### Công việc

1. Chạy Microsoft GraphRAG indexing trên corpus con đã khóa.
2. Ghi indexing duration, token/cost, entity/community counts và errors.
3. Chạy query subset so R4 GraphRAG với R3.
4. Ghi query latency/cost, answer quality, source traceability và failure cases.
5. Chạy C validation trên 12-20 brief subset nếu adapter ổn định.
6. So C với A/B ở mức seed:
   - structured output pass;
   - channel/persona/brand rule pass;
   - unsupported claim rate;
   - malformed JSON;
   - latency/cost.
7. Lưu raw C outputs và evaluator version.

### Owner

- Hải: GraphRAG sandbox, C validation, model failure analysis.
- Quang: eval runner integration, storage raw outputs, dashboard/report wiring.

### Đầu ra

- `docs/research/graphrag_sandbox_report_v1.md`.
- `docs/evaluation/generation_baseline_c_week05.md`.
- Raw GraphRAG/C eval outputs.

### Gate Ngày 5

- GraphRAG không được gọi từ production request path.
- C validation dùng cùng frozen brief subset hoặc ghi rõ lý do nếu ít hơn.
- Không kết luận D trước Tuần 6.

---

## Ngày 6 — 17/08: gate decision, hardening và staging RC

### Công việc

1. Hoàn thiện Model/Training Dashboard.
2. Hoàn thiện Review/Version/Export UI states: loading, empty, error, permission denied.
3. Tạo GraphRAG gate decision doc:
   - continue endpoint discovery;
   - offline only;
   - failed/not reliable.
4. Review QLoRA result và quyết định adapter dùng cho Tuần 6.
5. Test RBAC:
   - marketer tạo/edit/send review;
   - reviewer approve/reject;
   - admin export và xem training/GraphRAG cost;
   - viewer không sửa content.
6. Test rollback:
   - disable bad adapter config;
   - rerun with baseline model;
   - export old approved version.
7. Chạy backend tests, frontend lint/type-check/build.
8. Deploy staging release candidate.

### Owner

- Quang: UI hardening, RBAC, rollback, staging deploy, runbook.
- Hải: gate recommendation, adapter recommendation, metric interpretation.
- Cả nhóm: quyết định GraphRAG gate và QLoRA checkpoint.

### Đầu ra

- `docs/research/graphrag_gate_decision_week05.md`.
- `docs/models/qlora_adapter_selection_week05.md`.
- `docs/runbooks/reviewer_version_export.md`.
- Staging release candidate Tuần 5.

### Gate Ngày 6

- Gate GraphRAG có số liệu và chữ ký quyết định nhóm.
- Bad adapter có thể bị disable mà không phá A/B.
- Reviewer/export RBAC không có lỗi severity cao.

---

## Ngày 7 — 18/08: E2E, demo và đóng tuần

### Kiểm thử cuối

1. Chạy backend unit/integration tests cho training registry, model artifacts, C generation, review/version/export, GraphRAG research record và RBAC.
2. Chạy frontend lint/type-check/build.
3. Chạy migration trên database sạch.
4. Load adapter độc lập và chạy 3 generation smoke prompts.
5. Chạy C validation trên frozen subset hoặc subset được ghi rõ.
6. Chạy reviewer flow end-to-end: generated -> needs_review -> approved/rejected -> exported.
7. Kiểm tra thủ công 10 content versions, 10 review records, 5 exports và metadata.
8. Kiểm tra GraphRAG report có cost/latency/failure cases/gate decision.
9. Smoke test staging từ máy/mạng khác.
10. Quay video demo dự phòng 5-7 phút.

### Kịch bản demo 7 phút

1. Login bằng admin, mở Model/Training Dashboard.
2. Mở QLoRA training run, xem dataset, base model, seed, loss và adapter.
3. Mở Content Studio, chạy C trên một brief đã khóa.
4. Mở Evidence/Warnings để nhắc C không dùng retrieval trong Tuần 5.
5. Login hoặc chuyển role reviewer, approve/reject output.
6. Sửa nội dung, xem version history không overwrite output gốc.
7. Export bản approved và mở metadata.
8. Mở GraphRAG gate report, trình bày continue/offline decision bằng số liệu.

### Tổng kết

1. Ghi số liệu thực tế vào checkpoint Tuần 5.
2. Ghi issue còn mở, owner và ảnh hưởng Tuần 6.
3. Freeze `C_FINE_TUNED_V1` nếu adapter đạt gate; nếu không, ghi `C_FINE_TUNED_V1_CANDIDATE_FAILED` và kế hoạch sửa.
4. Freeze reviewer/version/export contract cho Tuần 6.
5. Chốt input Tuần 6: tích hợp D, chạy frozen A-D, comparison UI, cost/latency và blind human evaluation.
6. Cập nhật nhật ký dự án và link tài liệu.

### Đầu ra

- `docs/checkpoints/week_05_report.md`.
- `docs/models/qlora_training_protocol_v1.md`.
- `docs/data/sft_quality_report_v1.md`.
- `docs/models/qlora_pilot_report_v1.md`.
- `docs/models/qlora_adapter_v1_model_card.md`.
- `docs/evaluation/generation_baseline_c_week05.md`.
- `docs/research/graphrag_sandbox_report_v1.md`.
- `docs/research/graphrag_gate_decision_week05.md`.
- `docs/runbooks/qlora_training.md`.
- `docs/runbooks/reviewer_version_export.md`.
- Video/screenshot demo dự phòng.

### Gate đóng Tuần 5

- Adapter QLoRA load được độc lập hoặc có failure report rõ và fallback.
- Cấu hình C chạy được smoke/eval theo cùng output schema A/B.
- Reviewer flow approve/reject/request changes hoạt động.
- Version history không overwrite output gốc.
- Export chỉ chạy với approved content và có metadata.
- GraphRAG sandbox có report và gate decision bằng số liệu.
- Không có lỗi severity cao về RBAC, content versioning, export metadata, adapter provenance hoặc nhầm GraphRAG vào production path.

---

## 10. Phân công và RACI rút gọn

| Hạng mục | Quang | Hải | Cả nhóm |
|---|---|---|---|
| Checkpoint Tuần 4 và carry-over | R | C | A |
| SFT quality review | C schema/logs | R/A | A criteria |
| QLoRA protocol/pilot/main run | C infra | R/A | I |
| Model registry và C integration | R/A | C artifact | I |
| Reviewer/version/export backend | R/A | C | I |
| Reviewer/version/export UI | R/A | C content | I |
| GraphRAG sandbox | C report wiring | R/A | A gate |
| C validation và failure analysis | C runner | R/A | A rubric |
| Staging demo/checkpoint | R | R | A |

`R`: thực hiện; `A`: chịu trách nhiệm cuối; `C`: tham vấn; `I`: được thông báo.

---

## 11. Test checklist

### QLoRA/model

- [ ] Training run ghi dataset version, sample filter, base model, seed và hyperparameters.
- [ ] Không train trên `draft` hoặc test split.
- [ ] Adapter artifact có checksum và model card.
- [ ] Adapter load được độc lập.
- [ ] C output pass structured schema hoặc run bị đánh failed.
- [ ] Bad adapter config có thể disable/rollback.

### Reviewer/version/export

- [ ] Generated output không bị overwrite.
- [ ] Reviewer action tạo audit record.
- [ ] Request changes tạo version mới khi editor sửa.
- [ ] Export bị chặn nếu content chưa approved.
- [ ] Export metadata có model/prompt/dataset/snapshot/reviewer.
- [ ] Role không đúng không approve/export được.

### GraphRAG research

- [ ] Corpus con có source/provenance/license hợp lệ.
- [ ] GraphRAG indexing lưu cost/time/errors.
- [ ] Query comparison dùng subset đã khóa.
- [ ] Report so R4 với R3 có source traceability và failure cases.
- [ ] Gate decision ghi `continue_endpoint_discovery`, `offline_only` hoặc `failed_not_reliable`.
- [ ] GraphRAG không nằm trên production request path.

### Staging/operations

- [ ] Training/model dashboard có loading/error/empty states.
- [ ] Review/export UI có permission denied state.
- [ ] Backend tests pass ở các module critical path.
- [ ] Frontend lint/type-check/build pass.
- [ ] Demo chạy từ máy/mạng khác.

---

## 12. Metrics phải ghi trong checkpoint

### SFT và QLoRA

- Sample counts theo split/channel/persona/status.
- Train/validation loss.
- Structured output pass rate của C.
- Channel/persona/brand rule pass rate của C.
- Unsupported claim rate của C.
- Malformed JSON rate.
- Training duration và GPU memory peak.
- Adapter size và load latency.

### Reviewer/version/export

- Số content items, versions, reviews, approved, rejected, request changes.
- Thời gian trung bình từ generated đến approved trong demo/sample.
- Số export thành công/thất bại.
- Số export bị chặn do chưa approved.
- Số lỗi evidence/warning chưa xử lý khi approve.

### GraphRAG

- Corpus size: documents/chunks/tokens.
- Indexing time, token/cost và errors.
- Query latency p50/p95.
- Query token/cost.
- Global/local query score so với R3.
- Source traceability rate.
- Hallucinated entity/community rate.
- Gate decision và lý do.

### System

- Test pass/fail/skip counts.
- API p50/p95 cho generation C, review, version, export.
- Provider/GPU failure count.
- Training/eval raw output completeness.
- Audit log completeness cho model/review/export actions.

Không sửa sample filter, validation set hoặc gate sau khi thấy kết quả để làm đẹp báo cáo. Nếu phải thay đổi do lỗi kỹ thuật, tạo version mới và ghi lý do.

---

## 13. Rủi ro và phương án xử lý

| Rủi ro | Dấu hiệu sớm | Xử lý |
|---|---|---|
| SFT data ít/chất lượng thấp | Gold/silver ít hoặc nhiều claim thiếu mapping | Giảm scope pilot, chỉ train data đã audit, báo giới hạn |
| Không đủ GPU | OOM hoặc chạy quá lâu | Giảm rank/sequence/batch, thuê GPU theo giờ, lưu failure report |
| Adapter không hơn A/B | C không cải thiện channel/persona hoặc JSON | Báo negative/neutral, phân tích data/hyperparameter, không đổi test set |
| C hallucinate nhiều | Unsupported claim rate cao | Không đưa C vào D nếu chưa có warning/guard; dùng failure cases cho Tuần 6 |
| Reviewer flow phức tạp | Version/export lỗi hoặc overwrite | Giữ state machine nhỏ, test approved-only và immutable original output |
| Export thiếu metadata | File đẹp nhưng không audit được | Chặn export release, ưu tiên metadata hơn template đẹp |
| GraphRAG tốn chi phí | Indexing/query cost vượt budget | Dừng ở offline report, không làm endpoint |
| GraphRAG source traceability yếu | Answer tổng hợp nhưng không truy được source | Gate `offline_only`, giữ R3 production |
| Tuần 5 quá tải | QLoRA, review flow, GraphRAG đều chậm | Cắt DOCX/PDF đẹp và GraphRAG endpoint exploration trước; giữ QLoRA + review/version |

---

## 14. Thứ tự cắt scope nếu thiếu thời gian

1. DOCX/PDF đẹp; giữ Markdown/HTML export có metadata.
2. Multiple QLoRA backbone; giữ một backbone chính có pilot rõ.
3. Nhiều hyperparameter runs; giữ một main run + một sanity run.
4. Training dashboard đẹp; giữ report Markdown/JSON và artifact registry.
5. GraphRAG endpoint discovery; giữ sandbox report + gate decision.
6. Large C evaluation; giữ 12-20 briefs hoặc subset nhỏ có ghi giới hạn.
7. Reviewer diff UI nâng cao; giữ version list + change summary.

Không được cắt:

- QLoRA adapter/protocol hoặc failure report rõ.
- C output schema compatibility với A/B.
- Reviewer approve/reject/version history.
- Export approved-only có metadata.
- Model/dataset/prompt/artifact provenance.
- GraphRAG stop/continue gate.
- RBAC/tenant isolation.
- Staging demo và checkpoint report.

---

## 15. Definition of Done Tuần 5

Tuần 5 chỉ hoàn thành khi:

- [ ] Checkpoint Tuần 4 đã được kiểm tra bằng bằng chứng và blocker được carry-over rõ.
- [ ] SFT quality report và `sft_train_filter_v1` đã khóa.
- [ ] QLoRA pilot có log, metric và failure analysis.
- [ ] Main adapter load được hoặc có failure report đủ để bảo vệ hướng xử lý.
- [ ] `C_FINE_TUNED_V1` chạy smoke/eval theo cùng output schema A/B nếu adapter đạt gate.
- [ ] Model card ghi base model, license, dataset, hyperparameters, limitation và eval summary.
- [ ] Reviewer flow approve/reject/request changes hoạt động trên staging.
- [ ] Version history không overwrite output gốc.
- [ ] Export chỉ chạy với approved content và có metadata audit.
- [ ] GraphRAG sandbox report có cost/latency/quality/failure cases.
- [ ] GraphRAG gate decision đã được ghi rõ.
- [ ] RBAC/tenant isolation pass cho training dashboard, review, version, export và research reports.
- [ ] Có staging demo, checkpoint report và video/screenshot dự phòng.

---

## 16. Bàn giao sang Tuần 6

Tuần 5 phải bàn giao:

1. `C_FINE_TUNED_V1` hoặc failure report + adapter candidate status.
2. QLoRA model card, training logs, adapter artifact và validation report.
3. Reviewer/version/export contract đã ổn định.
4. C validation raw outputs và baseline report để so A/B/C.
5. GraphRAG gate decision:
   - nếu `continue_endpoint_discovery`: chỉ làm endpoint research riêng, không chặn A-D;
   - nếu `offline_only`: đưa vào báo cáo như ablation/negative result.
6. Danh sách failure cases cho Tuần 6: C hallucination, weak style, JSON lỗi, graph evidence yếu, review/export pain points.
7. Runbook train/eval/reviewer/export để tái lập.

Đầu vào này cho phép Tuần 6 tập trung vào tích hợp D = RAG + fine-tuned, chạy frozen A-D và R1-R4 đủ điều kiện, Comparison Dashboard, cost/latency logging và blind human evaluation.
