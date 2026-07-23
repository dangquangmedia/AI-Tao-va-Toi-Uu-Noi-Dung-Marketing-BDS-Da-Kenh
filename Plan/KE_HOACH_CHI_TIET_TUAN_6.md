# Kế hoạch triển khai chi tiết Tuần 6

## Tích hợp D và đánh giá chính

**Thời gian:** 19/08/2026 - 25/08/2026  
**Phụ thuộc:** checkpoint Tuần 5, `C_FINE_TUNED_V1` hoặc adapter candidate có trạng thái rõ, reviewer/version/export flow ổn định, A/B/C raw outputs, R1-R3 reports, GraphRAG gate decision và frozen `dataset_v1`/`knowledge_snapshot_v1`.  
**Mục tiêu tuần:** tích hợp cấu hình D = RAG + fine-tuned model, chạy đánh giá chính A/B/C/D trên frozen test set, chạy R1-R3 và R4 nếu đủ điều kiện, dựng Comparison Dashboard, ghi cost/latency đầy đủ và tổ chức blind human evaluation.

> Tuần 6 không mặc định Tuần 5 đã hoàn thành. Ngày đầu tiên phải kiểm tra bằng chứng thật: adapter/model card, C validation, review/export smoke, GraphRAG gate, prompt/model/dataset/snapshot versions và raw baseline runs. Nếu C chưa đạt gate, Tuần 6 vẫn chạy A/B và R1-R3, còn C/D được ghi là `not_ready` thay vì ép số liệu.

---

## 1. Demo bắt buộc cuối tuần

Đến cuối ngày 25/08, nhóm phải demo được:

```text
Đăng nhập
→ mở Experiment Dashboard
→ chọn frozen test subset
→ chạy hoặc mở runs A/B/C/D
→ cấu hình D dùng R3 context assembler + QLoRA adapter
→ xem output, evidence, reviewer status và run metadata
→ mở Comparison Dashboard
→ so A/B/C/D theo factuality, unsupported claim, channel/persona/brand fit, latency, cost
→ mở retrieval dashboard R1/R2/R3 và R4 nếu qua gate
→ mở human evaluation assignments/scores ẩn tên cấu hình
→ xuất báo cáo đánh giá Tuần 6
```

Điều kiện bắt buộc:

1. A/B/C/D dùng cùng frozen brief subset, dataset version, prompt family và decoding policy tương ứng đã khóa.
2. D dùng cùng QLoRA adapter của C và cùng R3 context assembler của B.
3. Không thay đổi frozen test set sau khi chạy.
4. Mọi run có `dataset_version_id`, `knowledge_snapshot_id`, `prompt_version_id`, `model_config_id`, `adapter_artifact_id` nếu có, `retrieval_config_id` nếu có.
5. R4 chỉ chạy nếu GraphRAG gate Tuần 5 cho phép; nếu không, dashboard ghi `offline_only` hoặc `not_applicable`.
6. Human evaluation phải blind: reviewer không thấy tên cấu hình A/B/C/D khi chấm.
7. Có raw prompts, contexts, outputs, metrics, evaluator version, cost và latency cho từng run.
8. Comparison Dashboard hiển thị cả kết quả tốt và failure cases, không chỉ điểm trung bình.
9. Có checkpoint report Tuần 6 và danh sách issue đưa sang Tuần 7.

---

## 2. Điều kiện đầu vào và kiểm tra checkpoint Tuần 5

### 2.1. Artefact cần có

- `docs/checkpoints/week_05_report.md`.
- `docs/models/qlora_adapter_v1_model_card.md`.
- `docs/evaluation/generation_baseline_c_week05.md`.
- `docs/research/graphrag_gate_decision_week05.md`.
- `docs/research/graphrag_sandbox_report_v1.md`.
- `docs/runbooks/qlora_training.md`.
- `docs/runbooks/reviewer_version_export.md`.
- `C_FINE_TUNED_V1` hoặc failure report có trạng thái rõ.
- Frozen prompt versions `A_PROMPT_ONLY_V1`, `B_RAG_V1`, `C_FINE_TUNED_V1`.
- R3 context assembler contract, A/B baseline raw outputs và C raw outputs.
- Reviewer/version/export flow trên staging.

### 2.2. Ma trận quyết định carry-over

| Checkpoint Tuần 5 | Nếu đạt | Nếu chưa đạt |
|---|---|---|
| Adapter QLoRA load được | Tạo D và chạy C/D | Ghi C/D `not_ready`, không làm giả số liệu |
| C output pass schema | Chạy A/B/C/D trên frozen subset | Chạy A/B chính, C chỉ smoke/failure analysis |
| Reviewer/version/export ổn định | Dùng output approved làm demo | Giữ review read-only, sửa state machine trước |
| GraphRAG gate `continue_endpoint_discovery` | Chạy R4 đủ điều kiện | R4 là offline/negative result, không chặn dashboard |
| A/B/C raw outputs đủ | Dựng comparison | Bổ sung raw output trước khi viết report |
| Human reviewer đã chốt lịch | Chạy blind eval | Giảm test subset nhưng giữ paired/blind protocol |

Nếu đến hết 19/08 còn blocker mức cao về adapter, frozen set, raw logging hoặc reviewer schedule, nhóm phải cắt R4 endpoint và dashboard polish để bảo vệ A-D reproducibility.

---

## 3. Phạm vi Tuần 6

### Bắt buộc

- Audit checkpoint Tuần 5.
- Tạo `D_RAG_FINE_TUNED_V1`.
- Chạy A/B/C/D trên frozen brief subset đủ điều kiện.
- Chạy R1/R2/R3 retrieval evaluation; R4 chỉ nếu gate cho phép.
- Automatic metrics cho generation và retrieval.
- Blind human evaluation workflow.
- Comparison Dashboard.
- Cost/latency logging và failure taxonomy.
- Báo cáo Tuần 6 với raw outputs và reproducibility notes.

### Không làm trong Tuần 6

- Vision facts chính thức trong A-D.
- Critic-refiner production.
- Online traffic A/B test.
- DPO/preference training.
- Auto-publish.
- Graph traversal production sâu hơn 2 hop.
- Thay đổi frozen test set sau khi chạy.

---

## 4. Thiết kế cấu hình D và evaluation matrix

### 4.1. Generation matrix chính

```text
A_PROMPT_ONLY_V1
retrieval: none
fine_tuned: no

B_RAG_V1
retrieval: R3_GRAPH_VECTOR_V1
fine_tuned: no

C_FINE_TUNED_V1
retrieval: none
fine_tuned: qlora_adapter_v1

D_RAG_FINE_TUNED_V1
retrieval: R3_GRAPH_VECTOR_V1
fine_tuned: qlora_adapter_v1
```

Quy tắc:

- A-D dùng cùng frozen brief IDs.
- B và D dùng cùng R3 context assembler version.
- C và D dùng cùng adapter artifact.
- Không dùng visual facts trong A-D chính Tuần 6.
- Nếu adapter chưa đạt, C/D không được đưa vào kết luận chính, chỉ ghi failure.

### 4.2. Retrieval matrix

```text
R1_VECTOR_FTS_V1
R2_GRAPH_ONLY_V1
R3_GRAPH_VECTOR_V1
R4_GRAPHRAG_SANDBOX_V1 hoặc not_applicable
```

R4 chỉ xuất hiện trong bảng nếu đã có gate decision rõ. Nếu gate `offline_only`, báo R4 trong phần nghiên cứu, không đưa vào production comparison.

### 4.3. Automatic metrics

Generation:

- structured output pass rate;
- unsupported claim rate;
- citation coverage;
- constraint pass rate theo channel;
- channel/persona/brand fit rule score;
- factual precision sample audit;
- latency p50/p95;
- prompt/completion tokens và estimated cost;
- failure taxonomy.

Retrieval:

- Recall@5/10;
- MRR;
- evidence recall;
- path precision;
- unsupported-edge rate;
- no-evidence false positive rate;
- latency p50/p95;
- indexing/query cost nếu có R4.

Human evaluation:

- factuality;
- naturalness;
- persuasiveness;
- channel fit;
- persona fit;
- brand fit;
- pairwise preference.

---

## 5. Schema và migration cần bổ sung/khóa

### 5.1. `evaluation_protocols`

```text
id, tenant_id, protocol_name, version,
dataset_version_id, brief_set_json, retrieval_query_set_json,
metrics_json, blind_review_enabled, status,
created_by, created_at
```

### 5.2. `experiment_runs`

```text
id, tenant_id, protocol_id, run_name,
experiment_config_id, dataset_version_id, knowledge_snapshot_id,
status, run_count, metrics_json, raw_output_path,
started_at, finished_at, created_by, created_at
```

### 5.3. `comparison_reports`

```text
id, tenant_id, protocol_id, report_name,
generation_metrics_json, retrieval_metrics_json,
cost_latency_json, failure_cases_json,
report_path, created_by, created_at
```

### 5.4. `human_eval_assignments`

```text
id, tenant_id, protocol_id, reviewer_id,
blind_item_id, content_version_id, channel,
status, assigned_at, completed_at
```

### 5.5. `human_eval_scores`

```text
id, tenant_id, assignment_id,
factuality, naturalness, persuasiveness,
channel_fit, persona_fit, brand_fit,
preference_group_id, preference_rank,
notes, created_at
```

### 5.6. `run_cost_logs`

```text
id, tenant_id, run_id, run_type,
provider, model_name, prompt_tokens,
completion_tokens, estimated_cost,
latency_ms, error_code, created_at
```

---

## 6. API và UI cần hoàn thiện trong Tuần 6

### Experiment/evaluation

```text
POST /evaluation/protocols
GET  /evaluation/protocols
POST /experiments/runs
GET  /experiments/runs/{run_id}
POST /experiments/compare
GET  /comparison-reports/{report_id}
```

### Human evaluation

```text
POST /human-eval/assignments
GET  /human-eval/assignments
POST /human-eval/assignments/{assignment_id}/scores
GET  /human-eval/protocols/{protocol_id}/summary
```

### UI tối thiểu

- Experiment Dashboard: chọn protocol, chạy/mở A-D, xem run status.
- Comparison Dashboard: metric table, charts đơn giản, raw report links.
- Human Evaluation UI: blind item, rubric, score form, notes.
- Cost/Latency panel: p50/p95, tokens, estimated cost, provider errors.

RBAC:

- `admin`: tạo protocol, chạy batch, xem cost/raw logs.
- `marketer`: xem comparison theo project được cấp quyền.
- `reviewer`: chỉ thấy blind eval assignment, không thấy config ID.

---

## 7. Kế hoạch theo ngày

## Ngày 1 — 19/08: checkpoint audit và khóa protocol đánh giá

### Công việc

1. Kiểm tra toàn bộ checkpoint Tuần 5 bằng bằng chứng.
2. Xác nhận adapter status, GraphRAG gate và reviewer/export contract.
3. Khóa `evaluation_protocol_week06_v1`.
4. Khóa frozen brief subset và retrieval query subset.
5. Khóa decoding/model configs cho A-D.
6. Chốt reviewer blind evaluation schedule.
7. Lập `docs/checkpoints/week_06_carry_over.md`.

### Owner

- Quang: protocol, config, logging và dashboard plan.
- Hải: adapter status, eval labels, human eval rubric.
- Cả nhóm: quyết định C/D/R4 đủ điều kiện hay không.

### Đầu ra

- `docs/evaluation/evaluation_protocol_week06_v1.md`.
- `docs/checkpoints/week_06_carry_over.md`.
- `docs/evaluation/human_eval_rubric_v1.md`.

### Gate Ngày 1

- Frozen set và metric khóa trước khi chạy batch.
- C/D/R4 có trạng thái đủ điều kiện hoặc loại khỏi main run.
- Reviewer không thấy tên cấu hình trong assignment.

---

## Ngày 2 — 20/08: tích hợp D và experiment runner

### Công việc

1. Tạo `D_RAG_FINE_TUNED_V1`.
2. Bảo đảm D dùng R3 context + QLoRA adapter.
3. Tạo experiment runner chạy A/B/C/D theo cùng brief IDs.
4. Lưu prompt, context, output, claims, citations, warnings và run cost.
5. Viết tests cho:
   - D gọi R3 và adapter;
   - C không gọi retrieval;
   - B không dùng adapter;
   - A không dùng retrieval/adapter;
   - run thiếu snapshot bị reject.
6. Chạy smoke 2-3 briefs cho A-D.

### Owner

- Quang: experiment config, runner, logs, tests.
- Hải: kiểm tra output D smoke và lỗi adapter.

### Đầu ra

- `D_RAG_FINE_TUNED_V1`.
- `docs/evaluation/d_integration_smoke_week06.md`.

### Gate Ngày 2

- D không lẫn config với B/C.
- Mọi run có dataset/model/prompt/graph snapshot version.
- Smoke output pass schema hoặc ghi failure rõ.

---

## Ngày 3 — 21/08: chạy retrieval R1-R4 và generation A-D

### Công việc

1. Chạy R1/R2/R3 trên frozen retrieval queries.
2. Chạy R4 nếu gate cho phép; nếu không, ghi `not_applicable`.
3. Chạy A/B/C/D trên frozen brief subset.
4. Ghi raw outputs, cost, latency, errors.
5. Tính automatic metrics v1.
6. Gắn failure taxonomy cho outputs lỗi.
7. Không rerun có chọn lọc để làm đẹp số liệu; rerun kỹ thuật phải ghi reason.

### Owner

- Quang: batch runner, metrics, raw output storage.
- Hải: kiểm tra labels, failure taxonomy và sample audit.

### Đầu ra

- `docs/evaluation/retrieval_report_r1_r4_week06.md`.
- `docs/evaluation/generation_report_a_d_week06.md`.
- Raw run outputs.

### Gate Ngày 3

- A-D dùng cùng brief set.
- R1-R4 dùng cùng query set hoặc ghi rõ R4 ngoại lệ.
- Raw output đủ để tái lập metric.

---

## Ngày 4 — 22/08: Comparison Dashboard và cost/latency

### Công việc

1. Tạo comparison report service.
2. Tạo Comparison Dashboard table cho A-D.
3. Tạo Retrieval Comparison table cho R1-R4.
4. Tạo Cost/Latency panel.
5. Link từng metric về raw run và sample outputs.
6. Hiển thị failure cases theo taxonomy.
7. Test role access cho dashboard và raw logs.

### Owner

- Quang: dashboard, report service, RBAC.
- Hải: xác nhận cách diễn giải metric.

### Đầu ra

- Comparison Dashboard trên staging.
- `docs/evaluation/comparison_dashboard_notes_week06.md`.

### Gate Ngày 4

- Dashboard không che failure cases.
- Cost/latency có p50/p95 và provider errors.
- Reviewer/marketer không thấy raw secrets hoặc API keys.

---

## Ngày 5 — 23/08: blind human evaluation

### Công việc

1. Tạo blind assignment từ A-D outputs.
2. Ẩn config ID/model name khỏi reviewer.
3. Reviewer chấm rubric Likert và pairwise preference.
4. Kiểm tra assignment completeness.
5. Tính human score summary và agreement nếu có đủ reviewer.
6. Ghi disagreement cases và notes.
7. Không thay output sau khi reviewer đã chấm.

### Owner

- Hải: điều phối reviewer, rubric, quality check.
- Quang: assignment UI, data model, summary.

### Đầu ra

- `docs/evaluation/human_eval_results_week06.md`.
- Human evaluation raw scores.

### Gate Ngày 5

- Reviewer không thấy cấu hình.
- Mỗi item có đủ score hoặc ghi missing reason.
- Human score mapping không làm lộ A-D trong UI reviewer.

---

## Ngày 6 — 24/08: phân tích kết quả và hardening

### Công việc

1. Tổng hợp automatic + human metrics.
2. Phân tích RQ1/RQ2/RQ3/RQ6 sơ bộ.
3. Tạo failure analysis: hallucination, wrong evidence, style fail, JSON fail, high latency.
4. Hardening dashboard states: loading, empty, error, permission denied.
5. Test RBAC cho experiment/human eval/raw logs.
6. Chạy backend tests, frontend lint/type-check/build.
7. Deploy staging release candidate Tuần 6.

### Owner

- Quang: dashboard hardening, tests, deploy.
- Hải: analysis, RQ mapping, human eval interpretation.

### Đầu ra

- `docs/evaluation/week06_findings_summary.md`.
- `docs/checkpoints/week_06_rc_notes.md`.

### Gate Ngày 6

- Kết luận sơ bộ có số liệu và failure cases.
- Không có lỗi severity cao về raw log leak hoặc blind eval leak.
- Staging dashboard mở được từ máy khác.

---

## Ngày 7 — 25/08: E2E, demo và đóng tuần

### Kiểm thử cuối

1. Chạy full tests cho experiment runner, comparison, human eval, RBAC.
2. Chạy frontend lint/type-check/build.
3. Chạy migration trên database sạch.
4. Re-run một subset A-D để kiểm reproducibility.
5. Kiểm tra thủ công 12 outputs, 24 claims, 12 evidence links.
6. Smoke test staging từ máy/mạng khác.
7. Quay video demo dự phòng.

### Kịch bản demo 7 phút

1. Mở Experiment Dashboard.
2. Chọn protocol Tuần 6.
3. Mở A/B/C/D runs và một output D.
4. Hiển thị evidence của D.
5. Mở Comparison Dashboard.
6. Mở human evaluation summary.
7. Chỉ ra R4 status: chạy qua gate hoặc offline/not applicable.
8. Mở cost/latency panel.

### Đầu ra

- `docs/checkpoints/week_06_report.md`.
- `docs/evaluation/retrieval_report_r1_r4_week06.md`.
- `docs/evaluation/generation_report_a_d_week06.md`.
- `docs/evaluation/human_eval_results_week06.md`.
- `docs/evaluation/week06_findings_summary.md`.
- Video/screenshot demo dự phòng.

### Gate đóng Tuần 6

- A-D đủ điều kiện đã chạy hoặc trạng thái missing được ghi trung thực.
- R1-R3 chạy đầy đủ; R4 theo đúng gate.
- Comparison Dashboard có metric, cost, latency, raw links.
- Blind human evaluation có score hoặc missing reason.
- Không có lỗi severity cao về provenance, raw logs, RBAC hoặc frozen set drift.

---

## 8. Phân công và RACI rút gọn

| Hạng mục | Quang | Hải | Cả nhóm |
|---|---|---|---|
| Checkpoint Tuần 5 | R | C | A |
| D integration | R/A | C adapter | I |
| A-D/R1-R4 runner | R/A | C labels | A protocol |
| Comparison Dashboard | R/A | C | I |
| Human evaluation | C UI | R/A | A rubric |
| RQ/failure analysis | C data | R/A | A |
| Staging demo | R | R | A |

---

## 9. Test checklist

- [ ] D dùng đúng R3 + QLoRA adapter.
- [ ] A/B/C/D không lẫn retrieval/adapter.
- [ ] Frozen brief set không đổi sau khi chạy.
- [ ] R1-R3 dùng cùng query set.
- [ ] R4 chỉ chạy nếu gate cho phép.
- [ ] Human evaluation blind với reviewer.
- [ ] Comparison Dashboard link được raw run.
- [ ] Cost/latency logs đầy đủ.
- [ ] RBAC chặn raw logs cho role không đủ quyền.

---

## 10. Metrics phải ghi trong checkpoint

- A-D structured pass, unsupported claim, citation coverage, constraint pass.
- A-D channel/persona/brand fit và human preference.
- A-D latency p50/p95, token/cost, provider error.
- R1-R4 Recall@5/10, MRR, path precision, evidence recall.
- Human eval score trung bình, disagreement, missing assignments.
- Failure taxonomy counts theo config.
- Số run có đầy đủ dataset/model/prompt/snapshot version.

---

## 11. Rủi ro và phương án xử lý

| Rủi ro | Dấu hiệu sớm | Xử lý |
|---|---|---|
| Adapter Tuần 5 không đạt | C/D fail schema hoặc hallucinate nhiều | Ghi C/D `not_ready`, tập trung A/B/R1-R3 và failure report |
| D retrieval sai evidence | D claim không map source | Chặn D khỏi kết luận chính, sửa citation validation |
| Human eval thiếu reviewer | Không đủ score | Giảm subset nhưng giữ blind/paired protocol |
| R4 chậm/tốn phí | Cost/latency vượt budget | Chỉ báo offline research, không đưa vào production |
| Dashboard che lỗi | Chỉ hiện average | Bắt buộc failure table và raw links |
| Frozen set drift | Brief/query IDs thay đổi | Hủy run, freeze lại version mới và ghi reason |

---

## 12. Thứ tự cắt scope nếu thiếu thời gian

1. R4 endpoint research; giữ R4 report theo gate.
2. Dashboard chart đẹp; giữ table/report links.
3. Large A-D batch; giữ subset đại diện và raw logs.
4. Inter-rater agreement nâng cao; giữ score + disagreement notes.
5. Extra prompt variants; giữ frozen A-D.

Không được cắt: A-D protocol, R1-R3, frozen set, raw logs, cost/latency, provenance/evidence, blind human eval tối thiểu, checkpoint report.

---

## 13. Definition of Done Tuần 6

Tuần 6 chỉ hoàn thành khi:

- [ ] Checkpoint Tuần 5 đã được kiểm tra bằng bằng chứng.
- [ ] `D_RAG_FINE_TUNED_V1` được tạo hoặc có lý do `not_ready`.
- [ ] A-D đủ điều kiện chạy trên frozen subset và lưu raw outputs.
- [ ] R1-R3 chạy đầy đủ; R4 theo đúng gate.
- [ ] Comparison Dashboard hoạt động trên staging.
- [ ] Cost/latency logs đầy đủ.
- [ ] Blind human evaluation có kết quả hoặc missing reason.
- [ ] Báo cáo Tuần 6 ghi cả metric, failure cases và giới hạn.

---

## 14. Bàn giao sang Tuần 7

Tuần 6 phải bàn giao:

1. A-D generation report và raw outputs.
2. R1-R4 retrieval report hoặc R4 gate status.
3. Comparison Dashboard và cost/latency logs.
4. Human evaluation scores và failure cases.
5. Danh sách vấn đề cần hardening: hallucination, evidence mismatch, weak UI, RBAC gaps.
6. Quyết định có đủ điều kiện thêm vision/critic ở Tuần 7 hay phải sửa A-D trước.

Đầu vào này cho phép Tuần 7 tập trung vào visual facts, critic panel và hardening mà không làm méo kết quả A-D chính.
