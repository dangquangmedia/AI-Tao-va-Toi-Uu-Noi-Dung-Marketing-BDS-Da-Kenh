# Kế hoạch triển khai chi tiết Tuần 7

## Vision, critic và hardening

**Thời gian:** 26/08/2026 - 01/09/2026  
**Phụ thuộc:** checkpoint Tuần 6, A-D generation report, R1-R4 retrieval report hoặc gate status, Comparison Dashboard, human evaluation results, failure cases và reviewer/version/export flow.  
**Mục tiêu tuần:** bổ sung visual facts có kiểm chứng người dùng, đánh giá image-text alignment, tạo critic panel để phát hiện claim/ràng buộc yếu, và harden RBAC/UX/observability trước release candidate. Critic-refiner chỉ làm smoke nếu A-D đã hoàn thành đủ điều kiện.

> Tuần 7 không được dùng vision hoặc critic để che kết quả A-D. A-D là kết quả chính của Tuần 6; Tuần 7 chỉ thêm ablation D+V hoặc D+V+R nếu không phá critical path, và mọi visual claim phải có provenance/confidence/human confirmation.

---

## 1. Demo bắt buộc cuối tuần

Đến cuối ngày 01/09, nhóm phải demo được:

```text
Đăng nhập
→ mở project có ảnh
→ chạy visual extraction trên ảnh
→ xem visual facts có confidence và source image
→ reviewer xác nhận/sửa/reject visual facts
→ tạo nội dung có dùng visual facts đã xác nhận
→ Evidence Panel hiển thị image evidence
→ Critic Panel chấm factuality, channel/persona/brand/SEO và unsupported claims
→ reviewer xử lý warnings
→ dashboard hiển thị D+V smoke metric và hardening status
```

Điều kiện bắt buộc:

1. Vision extractor chỉ sinh visual facts hẹp: room/scene, visible objects, material/color nhìn thấy được, image quality flags.
2. Không suy đoán giá, pháp lý, vị trí, view vĩnh viễn, chất lượng sống hoặc cam kết đầu tư từ ảnh.
3. Visual fact phải có `image_id`, `source_id`, `confidence`, `extractor_version`, `review_status`.
4. Generator chỉ dùng visual facts `verified` hoặc confidence đủ ngưỡng theo policy.
5. Critic Panel hiển thị rule failures và claim support status, không tự approve content.
6. D+V là ablation mở rộng, không thay thế A-D chính.
7. RBAC/UX hardening phải xử lý các lỗi severity cao trước khi bước sang Tuần 8.
8. Có checkpoint report Tuần 7, gồm vision benchmark, critic report và hardening checklist.

---

## 2. Điều kiện đầu vào và kiểm tra checkpoint Tuần 6

### 2.1. Artefact cần có

- `docs/checkpoints/week_06_report.md`.
- `docs/evaluation/generation_report_a_d_week06.md`.
- `docs/evaluation/retrieval_report_r1_r4_week06.md`.
- `docs/evaluation/human_eval_results_week06.md`.
- `docs/evaluation/week06_findings_summary.md`.
- Comparison Dashboard trên staging.
- Failure taxonomy: hallucination, evidence mismatch, weak style, malformed JSON, latency/cost.
- Reviewer/version/export flow ổn định.
- Asset/image metadata từ ingestion Tuần 2-3.

### 2.2. Ma trận quyết định carry-over

| Checkpoint Tuần 6 | Nếu đạt | Nếu chưa đạt |
|---|---|---|
| A-D report đủ | Làm D+V smoke | Không chạy D+V; sửa A-D evidence/logging trước |
| Evidence Panel ổn định | Thêm image evidence | Giữ visual facts report-only |
| Human eval có failure cases | Dùng làm critic targets | Bổ sung manual labels trước critic |
| Assets/images có metadata | Chạy visual extraction | Chỉ thiết kế UI confirmation và chờ assets |
| RBAC không lỗi cao | Hardening UX/observability | Chặn feature mới, sửa RBAC trước |
| Export/review ổn định | Critic warnings đi vào review flow | Giữ critic read-only nếu review còn lỗi |

Nếu đến hết 26/08 còn lỗi severity cao về A-D, RBAC hoặc evidence, nhóm phải cắt critic-refiner và D+V, chỉ làm hardening + visual fact confirmation.

---

## 3. Phạm vi Tuần 7

### Bắt buộc

- Audit checkpoint Tuần 6.
- Vision extraction schema và VLM adapter.
- Visual facts review/confirmation UI.
- Image evidence trong Evidence Panel.
- Image-text alignment metric smoke.
- Critic Panel rule-based + optional LLM judge read-only.
- Hardening RBAC, UX, logs, errors, budget guardrails.
- D+V smoke nếu A-D đủ điều kiện.
- Checkpoint report và runbooks.

### Không làm trong Tuần 7

- Fine-tune vision model.
- Production critic-refiner nhiều vòng.
- Auto-publish.
- Video processing hoàn chỉnh.
- Online A/B traffic.
- Thay đổi A-D frozen results.
- Graph traversal sâu hơn 2 hop.

---

## 4. Thiết kế vision pipeline

### 4.1. Luồng xử lý

```text
Image asset
→ validate file/metadata
→ VLM structured extraction
→ visual_facts pending
→ reviewer confirm/edit/reject
→ verified visual_facts
→ retrieval/generation context D+V
→ image evidence panel
```

### 4.2. Output schema visual fact

```json
{
  "image_id": "...",
  "source_id": "...",
  "fact_type": "visible_object",
  "text": "phòng khách có sofa và cửa kính lớn",
  "confidence": 0.82,
  "bbox_json": null,
  "review_status": "pending",
  "extractor_version": "vision_extractor_v1"
}
```

Allowed `fact_type`:

```text
room_type
visible_object
material
color
layout_hint
image_quality
style_hint
```

Forbidden:

- pháp lý;
- giá;
- cam kết lợi nhuận;
- vị trí/gần trung tâm;
- view vĩnh viễn;
- chất lượng sống;
- tiện ích ngoài ảnh nếu không có source khác.

### 4.3. D+V smoke

```text
D_PLUS_VISUAL_V1
base: D_RAG_FINE_TUNED_V1
additional_context: verified visual_facts only
scope: small ablation smoke
```

Không dùng D+V để thay thế kết quả D trong báo cáo chính. D+V chỉ trả lời RQ4 nếu đủ dữ liệu.

---

## 5. Thiết kế critic panel

### 5.1. Critic checks

Rule-based:

- structured JSON schema;
- channel length/format;
- required/forbidden terms;
- unsupported claims;
- missing citation;
- sensitive claim without review;
- SEO title/meta/heading basic rules;
- image-text mismatch.

Optional LLM judge:

- channel fit;
- persona fit;
- brand consistency;
- naturalness;
- persuasiveness.

### 5.2. Critic output

```json
{
  "critic_run_id": "...",
  "content_version_id": "...",
  "overall_status": "needs_review",
  "checks": [
    {
      "check_name": "unsupported_claim",
      "severity": "high",
      "message": "Claim không có fact/source hỗ trợ",
      "claim_id": "...",
      "suggested_action": "remove_or_add_evidence"
    }
  ]
}
```

Critic không được:

- tự approve;
- tự publish;
- sửa output mà không tạo version;
- dùng reference output khi chấm factuality.

---

## 6. Schema và migration cần bổ sung/khóa

### 6.1. `vision_extraction_runs`

```text
id, tenant_id, project_id, asset_id,
extractor_version, status, confidence_summary_json,
raw_output_path, error_summary_json,
started_at, finished_at, created_by, created_at
```

### 6.2. `visual_facts`

```text
id, tenant_id, project_id, asset_id, source_id,
fact_type, text, confidence, bbox_json,
review_status, reviewer_id, review_note,
extractor_version, created_at, updated_at
```

### 6.3. `visual_fact_reviews`

```text
id, tenant_id, visual_fact_id, reviewer_id,
decision, corrected_text, reason_code, created_at
```

### 6.4. `critic_runs`

```text
id, tenant_id, content_version_id,
critic_version, status, overall_status,
checks_json, latency_ms, cost_json,
created_by, created_at
```

### 6.5. `hardening_findings`

```text
id, tenant_id, area, severity, title,
description, owner, status, evidence_path,
created_at, resolved_at
```

---

## 7. API và UI cần hoàn thiện trong Tuần 7

### Vision

```text
POST /projects/{project_id}/assets/{asset_id}/vision/extract
GET  /projects/{project_id}/visual-facts
PATCH /projects/{project_id}/visual-facts/{visual_fact_id}/review
```

### Critic

```text
POST /content-versions/{version_id}/critic-runs
GET  /content-versions/{version_id}/critic-runs
GET  /critic-runs/{critic_run_id}
```

### Hardening

```text
GET  /admin/hardening-findings
POST /admin/hardening-findings
PATCH /admin/hardening-findings/{finding_id}
```

### UI tối thiểu

- Visual Fact Review: image preview, extracted facts, confidence, approve/edit/reject.
- Evidence Panel mở rộng: image evidence + visual fact status.
- Critic Panel: severity, check name, affected claim, suggested action.
- Hardening Dashboard: RBAC/security/UX/performance findings.

RBAC:

- `admin`: chạy extraction batch, xem hardening dashboard.
- `marketer`: xem visual facts verified, dùng trong Content Studio.
- `reviewer`: approve/edit/reject visual facts và xử lý critic warnings.

---

## 8. Kế hoạch theo ngày

## Ngày 1 — 26/08: checkpoint audit và vision/critic protocol

### Công việc

1. Kiểm tra checkpoint Tuần 6 bằng bằng chứng.
2. Chọn image assets đủ source/provenance.
3. Khóa `vision_extractor_v1` schema và forbidden claims.
4. Khóa critic check list v1.
5. Lập hardening backlog từ lỗi Tuần 6.
6. Chốt D+V chỉ chạy smoke nếu A-D đủ điều kiện.

### Owner

- Quang: schema/API/hardening backlog.
- Hải: visual fact guideline, critic rubric, sample images.

### Đầu ra

- `docs/vision/visual_fact_policy_v1.md`.
- `docs/evaluation/critic_protocol_v1.md`.
- `docs/checkpoints/week_07_carry_over.md`.

### Gate Ngày 1

- Không có asset thiếu source đưa vào vision benchmark.
- Forbidden visual claims được khóa.
- Critical A-D/RBAC lỗi có owner.

---

## Ngày 2 — 27/08: vision extraction và visual facts

### Công việc

1. Tạo migrations vision/visual facts.
2. Tạo VLM adapter có timeout, retry, cost logging.
3. Chạy extraction trên sample ảnh.
4. Lưu raw VLM output và structured visual facts.
5. Tạo tests cho forbidden claims và tenant isolation.
6. Hải review 30-50 visual facts sample.

### Owner

- Quang: VLM adapter, persistence, tests.
- Hải: review visual facts và error taxonomy.

### Đầu ra

- `vision_extractor_v1`.
- `docs/vision/vision_extraction_report_v1.md`.

### Gate Ngày 2

- Visual facts có confidence/source/image.
- Forbidden claim bị reject hoặc chuyển warning.
- Không có cross-tenant asset leak.

---

## Ngày 3 — 28/08: visual confirmation UI và image evidence

### Công việc

1. Tạo Visual Fact Review UI.
2. Cho phép approve/edit/reject visual facts.
3. Mở rộng Evidence Panel thêm image evidence.
4. Cho Content Studio đọc verified visual facts.
5. Chạy smoke: extract -> approve -> generate D+V smoke.
6. Ghi image-text alignment failure cases.

### Owner

- Quang: UI/API integration.
- Hải: review smoke outputs.

### Đầu ra

- Visual Fact Review trên staging.
- Image Evidence Panel.
- `docs/evaluation/d_plus_visual_smoke_week07.md`.

### Gate Ngày 3

- Generator không dùng visual fact pending/rejected.
- Claim từ ảnh link được image evidence.
- D+V không thay đổi A-D report chính.

---

## Ngày 4 — 29/08: Critic Panel

### Công việc

1. Tạo migrations/API cho `critic_runs`.
2. Implement rule-based critic checks.
3. Tích hợp optional LLM judge nếu budget cho phép.
4. Tạo Critic Panel UI.
5. Link critic findings vào reviewer flow.
6. Test: unsupported claim high severity, forbidden term, missing citation, visual mismatch.

### Owner

- Quang: critic service, UI, tests.
- Hải: rubric, judge prompt, failure labels.

### Đầu ra

- `critic_v1`.
- Critic Panel trên staging.
- `docs/evaluation/critic_report_week07.md`.

### Gate Ngày 4

- Critic không tự approve/export.
- Critic findings có severity/action rõ.
- Factuality critic không xem reference output.

---

## Ngày 5 — 30/08: RBAC/UX/security hardening

### Công việc

1. Audit RBAC cho assets, visual facts, critic, review, export, reports.
2. Audit UX states: loading, empty, error, permission denied, retry.
3. Audit logs: request ID, run ID, user ID, tenant ID.
4. Kiểm tra secret/raw output không lộ trong UI/log.
5. Fix severity high findings trước.
6. Chạy smoke multi-role.

### Owner

- Quang: hardening, tests, logging.
- Hải: review UX/evidence correctness.

### Đầu ra

- `docs/checkpoints/week_07_hardening_report.md`.
- Hardening findings dashboard.

### Gate Ngày 5

- Không còn severity high về RBAC/evidence/export.
- Permission denied rõ ràng cho role sai.
- Logs đủ audit nhưng không lộ secret.

---

## Ngày 6 — 31/08: benchmark vision/critic và staging RC

### Công việc

1. Chạy visual extraction benchmark sample.
2. Tính visual fact precision sample, rejection rate, confidence distribution.
3. Chạy critic trên outputs A-D/D+V sample.
4. Tính critic pass/fail counts và false positive sample.
5. Cập nhật dashboard summary.
6. Chạy backend tests, frontend lint/type-check/build.
7. Deploy staging release candidate Tuần 7.

### Owner

- Quang: benchmark runners, dashboard, tests, deploy.
- Hải: metric interpretation, error taxonomy.

### Đầu ra

- `docs/vision/vision_benchmark_week07.md`.
- `docs/evaluation/critic_benchmark_week07.md`.
- Staging RC Tuần 7.

### Gate Ngày 6

- Vision/critic metrics có sample size rõ.
- False positives/false negatives được ghi.
- Staging không lỗi luồng chính.

---

## Ngày 7 — 01/09: E2E, demo và đóng tuần

### Kiểm thử cuối

1. Chạy tests cho vision, visual fact review, critic, RBAC, export.
2. Chạy frontend lint/type-check/build.
3. Chạy migration trên database sạch.
4. Smoke test: visual extract -> review -> generate -> critic -> review -> export.
5. Kiểm tra thủ công 20 visual facts, 10 critic runs, 5 exports.
6. Smoke test staging từ máy/mạng khác.
7. Quay video demo dự phòng.

### Kịch bản demo 7 phút

1. Mở project có ảnh.
2. Chạy visual extraction và review visual facts.
3. Generate output có verified visual facts.
4. Mở Image Evidence.
5. Chạy Critic Panel.
6. Reviewer xử lý warning.
7. Mở Hardening Dashboard.
8. Mở report D+V/critic/vision.

### Đầu ra

- `docs/checkpoints/week_07_report.md`.
- `docs/vision/vision_benchmark_week07.md`.
- `docs/evaluation/d_plus_visual_smoke_week07.md`.
- `docs/evaluation/critic_benchmark_week07.md`.
- `docs/checkpoints/week_07_hardening_report.md`.
- Video/screenshot demo dự phòng.

### Gate đóng Tuần 7

- Visual facts có confidence/provenance/review status.
- Generator chỉ dùng visual facts verified.
- Critic Panel phát hiện unsupported/forbidden/missing citation cases.
- Không còn severity high về RBAC/export/evidence.
- D+V smoke hoặc lý do không chạy được ghi rõ.

---

## 9. Phân công và RACI rút gọn

| Hạng mục | Quang | Hải | Cả nhóm |
|---|---|---|---|
| Checkpoint Tuần 6 | R | C | A |
| Vision adapter/schema | R/A | C policy | I |
| Visual fact review | R | R/A labels | A |
| Critic Panel | R/A | C rubric | A |
| D+V smoke | R runner | C review | A |
| RBAC/UX hardening | R/A | C | I |
| Demo/checkpoint | R | R | A |

---

## 10. Test checklist

- [ ] Visual facts có image/source/confidence/extractor version.
- [ ] Pending/rejected visual facts không vào generation.
- [ ] Forbidden visual claims bị chặn.
- [ ] Critic không tự approve/export.
- [ ] Critic findings link được claim/content version.
- [ ] RBAC pass cho assets/visual facts/critic/review/export.
- [ ] Evidence Panel không có broken image/source links.
- [ ] Hardening findings severity high được xử lý hoặc có blocker rõ.

---

## 11. Metrics phải ghi trong checkpoint

- Số images processed, visual facts extracted, verified, rejected, edited.
- Visual fact precision sample.
- Confidence distribution.
- Image-text alignment pass/fail sample.
- Critic checks count theo severity.
- Critic false positive/false negative sample.
- D+V smoke metrics nếu chạy.
- RBAC/security findings open/resolved.
- API latency p50/p95 cho vision/critic.

---

## 12. Rủi ro và phương án xử lý

| Rủi ro | Dấu hiệu sớm | Xử lý |
|---|---|---|
| VLM bịa chi tiết ảnh | Claim không thấy trong ảnh | Schema hẹp, confidence threshold, human confirmation |
| Visual facts làm tăng hallucination | D+V unsupported claims tăng | Không dùng D+V trong main conclusion, sửa policy |
| Critic false positive cao | Reviewer mất thời gian xử lý | Giảm severity, ghi false positive taxonomy |
| Critic-refiner phá output | Refine làm mất source | Giữ critic read-only, không bật auto-refine |
| RBAC còn lỗi | Role sai xem/sửa được data | Chặn release candidate, sửa trước Tuần 8 |
| Quá tải tuần | Vision + critic + hardening đều rộng | Cắt D+V/critic-refiner, giữ hardening và verified visual facts |

---

## 13. Thứ tự cắt scope nếu thiếu thời gian

1. Critic-refiner tự động.
2. D+V batch lớn.
3. LLM judge sâu.
4. Image bounding boxes chi tiết.
5. Visual dashboard đẹp.
6. Multi-image reasoning.

Không được cắt: visual fact provenance/review, forbidden visual claim policy, RBAC hardening, critic read-only checks, staging demo, checkpoint report.

---

## 14. Definition of Done Tuần 7

Tuần 7 chỉ hoàn thành khi:

- [ ] Checkpoint Tuần 6 đã được kiểm tra.
- [ ] Visual extraction pipeline chạy smoke trên staging.
- [ ] Visual Fact Review hoạt động.
- [ ] Generator chỉ dùng visual facts verified.
- [ ] Evidence Panel hiển thị image evidence.
- [ ] Critic Panel chạy read-only với severity/action.
- [ ] RBAC/UX hardening không còn severity high chưa xử lý.
- [ ] Có vision/critic/hardening reports và demo dự phòng.

---

## 15. Bàn giao sang Tuần 8

Tuần 7 phải bàn giao:

1. Visual fact policy và benchmark.
2. Critic protocol và benchmark.
3. Hardening report với severity high đã xử lý hoặc blocker rõ.
4. D+V smoke result hoặc lý do không chạy.
5. Staging release candidate đủ ổn định cho production release.
6. Danh sách việc Tuần 8: model/data cards, reproducibility, security/E2E, production deploy, seed demo, runbook, rehearsal và backup video/data.

Đầu vào này cho phép Tuần 8 tập trung đóng gói release, không thêm nghiên cứu mới.
