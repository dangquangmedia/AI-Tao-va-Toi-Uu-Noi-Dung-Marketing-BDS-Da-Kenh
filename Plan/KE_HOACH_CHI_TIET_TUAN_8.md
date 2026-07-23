# Kế hoạch triển khai chi tiết Tuần 8

## Release candidate, reproducibility và production deploy

**Thời gian:** 02/09/2026 - 08/09/2026  
**Phụ thuộc:** checkpoint Tuần 7, A-D evaluation report, retrieval report R1-R4/gate status, vision/critic/hardening reports, reviewer/export flow, staging release candidate và danh sách blocker severity high.  
**Mục tiêu tuần:** đóng gói release candidate cuối cùng, hoàn thiện model/data cards và reproducibility package, chạy E2E/security tests, deploy production, seed demo account/data, chuẩn bị runbook, rehearsal demo và backup video/data cho giai đoạn viết báo cáo/bảo vệ.

> Tuần 8 không thêm nghiên cứu mới nếu ảnh hưởng release. Ưu tiên tuyệt đối: URL production, auth/RBAC, bốn loại content, evidence graph/vector, review/version/export, dashboard A-D/R1-R3, reproducibility và demo ổn định. Microsoft GraphRAG không được là single point of failure.

---

## 1. Demo bắt buộc cuối tuần

Đến cuối ngày 08/09, nhóm phải demo được trên production hoặc production-like URL:

```text
Mở URL production
→ login bằng demo account
→ tạo/chọn project demo
→ xem facts/sources/assets/graph evidence
→ mở Content Studio
→ generate 4 content types
→ xem evidence panel claim -> fact/chunk/source/path
→ reviewer approve/reject và xem version history
→ export bản approved
→ mở Experiment Comparison Dashboard A-D/R1-R3
→ mở model/data cards và reproducibility package
→ chạy health/ready và demo fallback plan
```

Điều kiện bắt buộc:

1. Có URL production/staging-final truy cập được từ máy/mạng khác.
2. Auth/RBAC backend hoạt động, không chỉ ẩn nút ở frontend.
3. Có seed demo tenant, user, project, sources, facts, graph, assets và content outputs.
4. Bốn loại content chạy được: mô tả BĐS, Facebook, nurturing email, SEO landing page.
5. Evidence Panel hiển thị source và graph path; claim thiếu evidence có warning.
6. Review/version/export chạy từ đầu đến cuối.
7. Dashboard A-D và R1-R3 có metric/report/raw links; R4 hiển thị đúng gate status.
8. Model/data cards và reproducibility package đủ để tái lập kết quả chính.
9. Có runbook vận hành, rollback, demo fallback và backup video/data.
10. Có release checklist và checkpoint report Tuần 8.

---

## 2. Điều kiện đầu vào và kiểm tra checkpoint Tuần 7

### 2.1. Artefact cần có

- `docs/checkpoints/week_07_report.md`.
- `docs/vision/vision_benchmark_week07.md`.
- `docs/evaluation/critic_benchmark_week07.md`.
- `docs/checkpoints/week_07_hardening_report.md`.
- `docs/evaluation/generation_report_a_d_week06.md`.
- `docs/evaluation/retrieval_report_r1_r4_week06.md`.
- `docs/evaluation/human_eval_results_week06.md`.
- Model card QLoRA và adapter artifact.
- Data card `dataset_v1`.
- Staging URL và hardening findings.
- Reviewer/version/export smoke.
- Production deploy plan và secrets checklist.

### 2.2. Ma trận quyết định carry-over

| Checkpoint Tuần 7 | Nếu đạt | Nếu chưa đạt |
|---|---|---|
| Staging RC ổn định | Deploy production | Chỉ deploy khi E2E/security pass |
| RBAC severity high = 0 | Freeze release | Chặn release nếu còn cross-tenant leak |
| Evidence/review/export ổn định | Demo chính | Sửa trước, cắt visual/critic polish |
| A-D/R1-R3 dashboard ổn định | Đưa vào production | Giữ report Markdown nếu UI chưa ổn |
| Vision/critic ổn định | Đưa vào demo phụ | Nếu chưa ổn, giữ như ablation/report-only |
| Runbooks đầy đủ | Rehearsal demo | Viết runbook trước khi freeze |

Nếu đến hết 02/09 còn severity high về auth/RBAC/evidence/export/deploy, nhóm phải cắt visual/critic demo và dashboard polish để sửa release core.

---

## 3. Phạm vi Tuần 8

### Bắt buộc

- Audit checkpoint Tuần 7.
- Model card, data card, experiment card.
- Reproducibility package.
- E2E tests và security checks.
- Production deploy hoặc staging-final production-like URL.
- Seed demo account/data.
- Release checklist và runbooks.
- Demo rehearsal.
- Backup video/data/offline fallback.
- Final checkpoint report.

### Không làm trong Tuần 8

- Training mới trừ hotfix nhỏ có ghi version.
- Thay frozen test set.
- DPO/preference training.
- GraphRAG production dependency mới.
- Deep graph/Neo4j.
- Critic-refiner nhiều vòng.
- Auto-publish thật.
- Feature UI lớn chưa có test.

---

## 4. Release artifacts bắt buộc

### 4.1. Cards và reports

```text
docs/release/data_card_dataset_v1.md
docs/release/model_card_qlora_adapter_v1.md
docs/release/experiment_card_a_d_r1_r4.md
docs/release/security_and_ethics_note.md
docs/release/reproducibility_package.md
docs/release/final_release_checklist.md
```

### 4.2. Reproducibility package

Phải ghi:

- dataset version;
- split policy;
- prompt versions;
- model configs;
- adapter artifact checksum;
- graph/knowledge snapshot;
- retrieval configs R1-R4;
- evaluation protocol;
- run commands hoặc UI flow;
- raw output locations;
- random seeds;
- known non-determinism;
- expected metrics table.

### 4.3. Demo package

```text
docs/demo/demo_script_7_minutes.md
docs/demo/demo_account_and_seed_notes.md
docs/demo/fallback_plan.md
docs/demo/offline_backup_manifest.md
```

Không ghi secret thật vào docs. Demo credentials chia sẻ ngoài Git bằng kênh an toàn.

---

## 5. Production readiness checklist

### Product core

- Login/logout.
- Role admin/marketer/reviewer.
- Tenant isolation.
- Project CRUD.
- Sources/facts/assets.
- Graph path evidence.
- Content Studio 4 channel.
- Evidence Panel.
- Reviewer approve/reject/version history.
- Export approved-only.
- Comparison Dashboard.

### Operations

- `/health` và `/ready`.
- Database migrations sạch.
- Seed demo data.
- Structured logs.
- Request ID/run ID.
- Error handling.
- Rate limit/budget cap.
- Backup/restore note.
- Rollback plan.

### Security/ethics

- No secrets in repo/logs.
- Upload limits.
- Tenant storage namespace.
- Forbidden claims.
- Human approval before export.
- Audit log for prompt/model/review/export.
- PII/sensitive data policy.

---

## 6. Schema/API freeze

Tuần 8 hạn chế schema mới. Chỉ bổ sung nếu phục vụ release evidence.

### 6.1. `release_versions`

```text
id, tenant_id, release_name, version,
commit_sha, dataset_version_id, knowledge_snapshot_id,
status, release_notes_path, created_by, created_at
```

### 6.2. `demo_seed_runs`

```text
id, tenant_id, release_version_id,
seed_name, status, records_json,
created_by, created_at
```

### 6.3. API cần freeze

```text
GET /health
GET /ready
GET /auth/me
GET /projects
POST /projects
GET /projects/{project_id}
POST /projects/{project_id}/generation/runs
GET /projects/{project_id}/generation/runs/{run_id}/evidence
POST /content-items/{content_item_id}/reviews
POST /content-items/{content_item_id}/exports
GET /comparison-reports/{report_id}
```

Không đổi response contract public sau khi freeze release nếu không có bug severity high.

---

## 7. Kế hoạch theo ngày

## Ngày 1 — 02/09: checkpoint audit và release scope freeze

### Công việc

1. Kiểm tra checkpoint Tuần 7 bằng bằng chứng.
2. Phân loại open issues theo severity.
3. Freeze release scope: core, optional, cut.
4. Freeze API/schema surface cho demo.
5. Chốt production deploy target, domain, database, storage, env vars.
6. Lập release board với owner/deadline.

### Owner

- Quang: release scope, infra/deploy, issue severity.
- Hải: reports/cards/eval figures cần chốt.
- Cả nhóm: quyết định cut scope cuối.

### Đầu ra

- `docs/release/final_release_scope.md`.
- `docs/checkpoints/week_08_carry_over.md`.
- `docs/release/final_release_checklist.md`.

### Gate Ngày 1

- Không còn feature mới ngoài release scope.
- Severity high có owner và deadline trước deploy.
- Production target/env checklist rõ.

---

## Ngày 2 — 03/09: model/data/experiment cards

### Công việc

1. Hoàn thiện data card `dataset_v1`.
2. Hoàn thiện model card QLoRA.
3. Hoàn thiện experiment card A-D/R1-R4.
4. Ghi negative results và limitations.
5. Chốt bảng metric chính cho báo cáo.
6. Link cards từ dashboard hoặc release page.

### Owner

- Hải: metric/limitations/model/data content.
- Quang: artifact links, dashboard/report wiring.

### Đầu ra

- `docs/release/data_card_dataset_v1.md`.
- `docs/release/model_card_qlora_adapter_v1.md`.
- `docs/release/experiment_card_a_d_r1_r4.md`.

### Gate Ngày 2

- Cards ghi version/checksum/snapshot.
- Không giấu negative results.
- Metric khớp raw reports.

---

## Ngày 3 — 04/09: reproducibility và E2E tests

### Công việc

1. Viết reproducibility package.
2. Tạo E2E script/checklist cho happy path.
3. Tạo hallucination-control demo test.
4. Test migration trên database sạch.
5. Test seed demo data idempotent.
6. Test export metadata.
7. Test dashboard report links.

### Owner

- Quang: E2E, migration, seed, export/dashboard checks.
- Hải: verify metrics/reproducibility notes.

### Đầu ra

- `docs/release/reproducibility_package.md`.
- `docs/runbooks/e2e_release_test.md`.
- `docs/demo/demo_seed_manifest.md`.

### Gate Ngày 3

- E2E core pass trên staging-final.
- Seed chạy lại không tạo duplicate sai.
- Reproducibility doc đủ để người khác chạy lại.

---

## Ngày 4 — 05/09: security, ethics và production deploy

### Công việc

1. Chạy security checklist: secrets, RBAC, tenant isolation, upload, logs.
2. Hoàn thiện ethics/legal note.
3. Deploy production hoặc staging-final.
4. Chạy migrations production.
5. Seed demo tenant/user/project.
6. Kiểm tra `/health` và `/ready`.
7. Smoke test từ máy/mạng khác.
8. Ghi rollback plan.

### Owner

- Quang: deploy, security, smoke, rollback.
- Hải: source/license/ethics note review.

### Đầu ra

- Production/staging-final URL.
- `docs/release/security_and_ethics_note.md`.
- `docs/runbooks/production_deploy_and_rollback.md`.
- `docs/checkpoints/production_smoke_test.md`.

### Gate Ngày 4

- Auth/RBAC/tenant isolation pass.
- Không secret trong logs/docs.
- Production health/ready pass.
- Rollback path rõ.

---

## Ngày 5 — 06/09: demo data, runbook và fallback

### Công việc

1. Hoàn thiện demo account/data notes.
2. Chuẩn bị 2 demo projects: one happy path, one missing-evidence path.
3. Viết demo script 7 phút.
4. Viết fallback plan nếu API/model/GPU lỗi.
5. Tạo offline backup manifest: screenshots, videos, raw reports, sample outputs.
6. Kiểm thử demo trên máy khác.

### Owner

- Quang: demo seed, runbook, fallback technical path.
- Hải: demo narrative, evidence/source checks.

### Đầu ra

- `docs/demo/demo_script_7_minutes.md`.
- `docs/demo/demo_account_and_seed_notes.md`.
- `docs/demo/fallback_plan.md`.
- `docs/demo/offline_backup_manifest.md`.

### Gate Ngày 5

- Demo không phụ thuộc localhost.
- Missing-evidence case thể hiện chống hallucination.
- Backup đủ dùng khi dịch vụ ngoài lỗi.

---

## Ngày 6 — 07/09: rehearsal và release hardening

### Công việc

1. Rehearsal demo 2 lần.
2. Ghi thời gian demo và lỗi phát sinh.
3. Fix lỗi severity high/medium ảnh hưởng demo.
4. Freeze release candidate.
5. Chụp screenshots UI chính.
6. Quay backup video 3-5 phút.
7. Kiểm tra cards/reports links lần cuối.

### Owner

- Quang: release hardening, screenshots/video technical.
- Hải: rehearsal feedback, narrative/eval explanation.
- Cả nhóm: freeze decision.

### Đầu ra

- `docs/demo/rehearsal_notes.md`.
- Backup video/screenshot set.
- `docs/release/release_candidate_notes.md`.

### Gate Ngày 6

- Demo chạy trong 5-7 phút.
- Không còn severity high.
- Release candidate không đổi sau freeze trừ hotfix có ghi log.

---

## Ngày 7 — 08/09: final E2E, checkpoint và bàn giao báo cáo

### Kiểm thử cuối

1. Chạy full release E2E checklist.
2. Chạy security smoke.
3. Kiểm tra production URL từ máy/mạng khác.
4. Kiểm tra demo account.
5. Kiểm tra 4 content types.
6. Kiểm tra evidence/review/version/export.
7. Kiểm tra dashboard A-D/R1-R3.
8. Kiểm tra model/data/experiment cards.
9. Kiểm tra backup video/data.

### Kịch bản demo 7 phút

1. Login production.
2. Mở project demo.
3. Generate Facebook hoặc SEO content.
4. Mở Evidence Panel và graph path.
5. Chạy missing-evidence brief để thấy warning.
6. Reviewer approve và export.
7. Mở Comparison Dashboard.
8. Mở release/reproducibility cards.

### Đầu ra

- `docs/checkpoints/week_08_report.md`.
- `docs/release/final_release_checklist.md`.
- `docs/release/release_candidate_notes.md`.
- `docs/demo/rehearsal_notes.md`.
- Production URL và smoke evidence.
- Backup video/data manifest.

### Gate đóng Tuần 8

- URL production/staging-final hoạt động.
- Auth/RBAC, project, generation, evidence, review/version/export chạy.
- Dashboard A-D/R1-R3 mở được.
- Model/data/reproducibility docs hoàn thiện.
- Security/ethics checklist có kết quả.
- Demo và fallback đã rehearsal.

---

## 8. Phân công và RACI rút gọn

| Hạng mục | Quang | Hải | Cả nhóm |
|---|---|---|---|
| Release scope/deploy | R/A | C | A cut |
| Model/data/experiment cards | C links | R/A | A review |
| Reproducibility package | R | C metrics | A |
| E2E/security | R/A | C | I |
| Demo script/fallback | R technical | R narrative | A |
| Production smoke | R/A | C | I |
| Final checkpoint | R | R | A |

---

## 9. Test checklist

- [ ] Production/staging-final URL mở từ máy khác.
- [ ] `/health` và `/ready` pass.
- [ ] Login/logout pass.
- [ ] RBAC backend pass.
- [ ] Tenant isolation negative tests pass.
- [ ] 4 content types generate được.
- [ ] Evidence links không broken.
- [ ] Review/version/export pass.
- [ ] Dashboard A-D/R1-R3 pass.
- [ ] Seed data idempotent.
- [ ] No secrets in docs/logs.
- [ ] Backup video/data có sẵn.

---

## 10. Metrics phải ghi trong checkpoint

- E2E pass/fail count.
- Security findings open/resolved.
- Production smoke latency p50/p95.
- API error rate trong demo smoke.
- Content generation success rate theo channel.
- Evidence link broken count.
- Export success/failure count.
- Dashboard load time.
- Release artifact completeness.

---

## 11. Rủi ro và phương án xử lý

| Rủi ro | Dấu hiệu sớm | Xử lý |
|---|---|---|
| Deploy trễ | Production chưa lên ngày 05/09 | Dùng staging-final URL, ghi rõ, ưu tiên demo ổn định |
| Secrets/env lỗi | Health fail hoặc log lộ secret | Chặn release, sửa env/log, rotate nếu cần |
| E2E fail sát giờ | Luồng chính lỗi | Cắt optional vision/critic, sửa core generation/evidence/review/export |
| API/model ngoài lỗi | Timeout/rate limit | Fallback cached output/demo video, budget cap |
| Dashboard chậm | Load lâu hoặc crash | Giữ static report links, cắt chart nặng |
| Demo quá dài | Vượt 7 phút | Rút script còn happy path + hallucination guard + dashboard |
| Report links lệch | Cards không khớp metrics | Freeze artifact index, kiểm link trước rehearsal |

---

## 12. Thứ tự cắt scope nếu thiếu thời gian

1. Vision/critic live demo; giữ report.
2. DOCX/PDF đẹp; giữ Markdown/HTML export có metadata.
3. GraphRAG endpoint; giữ offline result/gate.
4. Dashboard chart nâng cao; giữ table/static report.
5. Extra demo projects; giữ one happy path và one missing-evidence path.
6. UI polish nhỏ.

Không được cắt: URL demo, auth/RBAC, project/content generation 4 channel, evidence, review/version/export, A-D/R1-R3 reports, model/data cards, reproducibility, security checklist, backup demo.

---

## 13. Definition of Done Tuần 8

Tuần 8 chỉ hoàn thành khi:

- [ ] Checkpoint Tuần 7 đã được kiểm tra.
- [ ] Release scope đã freeze.
- [ ] Production/staging-final URL hoạt động.
- [ ] Demo account/data được seed và kiểm thử.
- [ ] 4 content types chạy được.
- [ ] Evidence/review/version/export chạy được.
- [ ] Dashboard A-D/R1-R3 mở được.
- [ ] Model/data/experiment cards hoàn thiện.
- [ ] Reproducibility package hoàn thiện.
- [ ] Security/ethics checklist có kết quả.
- [ ] Demo rehearsal và backup video/data đã chuẩn bị.
- [ ] Week 08 report ghi rõ remaining limitations.

---

## 14. Bàn giao sang giai đoạn báo cáo/bảo vệ

Tuần 8 phải bàn giao:

1. URL production/staging-final và demo flow.
2. Release checklist và smoke evidence.
3. Model/data/experiment cards.
4. Reproducibility package.
5. A-D/R1-R3/R4 reports và raw links.
6. Screenshots UI chính.
7. Backup video/data.
8. Runbooks deploy/rollback/demo.
9. Danh sách limitations và negative results để viết báo cáo trung thực.

Đầu vào này cho phép giai đoạn 09/09-23/09 tập trung viết báo cáo, chụp UI, dựng sơ đồ, luyện bảo vệ và chuẩn bị phương án demo dự phòng.
