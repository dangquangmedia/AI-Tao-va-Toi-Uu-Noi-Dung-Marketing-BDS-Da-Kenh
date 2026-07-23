# Kế hoạch triển khai chi tiết Tuần 3

## Knowledge base và dataset v1

**Thời gian:** 29/07/2026 - 04/08/2026  
**Phụ thuộc:** checkpoint Tuần 2, batch crawler đã ingest trên staging, graph snapshot và knowledge snapshot có provenance.  
**Mục tiêu tuần:** biến dữ liệu đã ingest thành knowledge base có thể biên tập/kiểm chứng, khóa `dataset_v1` theo project split, tạo SFT draft v1 và bộ gold retrieval queries R1-R3 để chuẩn bị chạy prompt-only/RAG baseline ở Tuần 4.

> Tuần 3 không mặc định Tuần 2 đã hoàn thành. Ngày đầu tiên phải kiểm tra bằng chứng thật: staging URL, batch/job report, graph snapshot, retrieval smoke test, data-quality report và các blocker carry-over. Nếu ingestion Tuần 2 chưa đạt, ưu tiên sửa pipeline dữ liệu trước khi mở rộng SFT hoặc UI mới.

---

## 1. Demo bắt buộc cuối tuần

Đến cuối ngày 04/08, nhóm phải demo trên staging được luồng:

```text
Đăng nhập
→ mở project từ batch_01
→ xem source/fact/asset có provenance
→ reviewer chỉnh trạng thái fact hoặc ghi chú lỗi nguồn
→ mở queue entity resolution
→ merge alias chắc chắn hoặc đưa candidate mơ hồ vào pending
→ dựng graph snapshot đã audit
→ tạo chunks/index snapshot cho dataset_v1
→ chạy split train/validation/test theo project
→ chạy leakage audit
→ mở bộ retrieval queries R1-R3 có expected evidence
→ chạy R1 vector/FTS baseline và R2 graph-only smoke test
→ xuất data card + retrieval benchmark seed report
```

Điều kiện bắt buộc:

1. `dataset_v1` có version, data card, thống kê nguồn, thống kê field thiếu và danh sách records bị loại.
2. Split theo **project**, không random theo content sample.
3. Dedup và near-duplicate audit chạy trước khi freeze split.
4. Mỗi SFT draft sample liên kết đến `project_id`, `source_id`, `fact_id`, `brand_profile_id`, `persona_id`, `channel` và `quality_status`.
5. Fact/source editor không xóa lịch sử; mọi thay đổi tạo review log hoặc version.
6. Entity resolution không auto-merge candidate mơ hồ; trường hợp mơ hồ phải có queue và owner.
7. Graph snapshot có entity/edge counts, provenance coverage và path precision trên mẫu human-check.
8. Có 60-90 retrieval queries đã gán loại: fact đơn, 1-hop, 2-hop, so sánh, conflict, temporal và no-evidence.
9. R1 và R2 chạy được trên cùng query set seed; R3 có contract/context assembler skeleton nếu chưa đo đầy đủ.
10. Có checkpoint report Tuần 3, bao gồm blocker còn lại để đưa sang Tuần 4.

---

## 2. Điều kiện đầu vào và kiểm tra checkpoint Tuần 2

### 2.1. Artefact cần có

- `docs/checkpoints/week_02_report.md`.
- `docs/data/batch_01_quality_report.md`.
- Versioned crawler batch hoặc storage reference.
- `crawler_contract_v1` và compatibility rules đã dùng ở Tuần 2.
- Database migrations cho ingestion/source/asset/graph/chunk.
- Staging URL frontend/backend/worker.
- Graph snapshot hoặc ít nhất graph statistics từ batch thật.
- Knowledge chunks/index snapshot từ batch thật.
- Danh sách alias/entity merge candidates.
- Retrieval smoke results từ batch Tuần 2.

### 2.2. Ma trận quyết định carry-over

| Checkpoint Tuần 2 | Nếu đạt | Nếu chưa đạt |
|---|---|---|
| Batch crawler ingest end-to-end | Dùng `batch_01` làm input dataset | Quang + Hải sửa ingestion trước trưa 29/07 |
| Idempotency/replay pass | Freeze snapshot cho split | Không tạo `dataset_v1` trước khi duplicate policy rõ |
| Sources/facts/assets có provenance | Mở editor/review | Chặn SFT sample từ records thiếu source |
| Graph path production có source | Audit graph quality | Không dùng edge thiếu source trong retrieval queries |
| Tenant isolation/RBAC pass | Mở reviewer/editor UI | Chặn release staging nếu còn cross-tenant leak |
| Knowledge chunks/index có snapshot | Chạy R1 baseline | Dùng FTS trước, ghi rõ vector/index blocker |
| Data-quality report có missing/error taxonomy | Lọc dataset v1 | Hải bổ sung report trước khi freeze split |

Nếu đến hết 29/07 còn blocker mức cao về provenance, tenant isolation, duplicate hoặc source manifest, nhóm phải cắt UI nâng cao và SFT volume để bảo vệ correctness của dataset.

---

## 3. Phạm vi Tuần 3

### Bắt buộc

- Audit checkpoint Tuần 2 và carry-over blocker.
- Cleaned canonical dataset v1 từ batch đã ingest.
- Fact/source editor và review log.
- Entity resolution queue: alias, merge, split, reject.
- Graph quality audit và graph snapshot versioning.
- Chunk/index snapshot versioning.
- Brand/persona/channel schema tối thiểu để tạo SFT draft.
- Dataset builder cho SFT draft v1.
- Project-level train/validation/test split.
- Dedup và leakage audit trước khi freeze split.
- 60-90 gold retrieval queries R1-R3 với expected evidence.
- R1 vector/FTS baseline và R2 graph-only smoke/eval seed.
- Reports: data card, graph quality, leakage audit, retrieval seed report.

### Không làm trong Tuần 3

- Chạy QLoRA training chính thức.
- Kết luận A-D generation.
- Microsoft GraphRAG indexing.
- Vision extraction hàng loạt.
- Critic-refiner.
- Export DOCX/PDF production.
- Graph visualization nâng cao.
- Neo4j hoặc traversal sâu hơn 2 hop.
- Online A/B test hoặc auto-publish.

---

## 4. Thiết kế data và knowledge base Tuần 3

### 4.1. Dataset layers

```text
batch_01 raw reference
→ canonical facts/assets/sources
→ fact review + quality flags
→ entity resolution decisions
→ graph snapshot
→ knowledge chunks/index snapshot
→ dataset_v1 split by project
→ SFT draft samples
→ retrieval query set R1-R3
```

Quy tắc:

- Raw data không bị sửa tay; chỉ lưu correction/review ở lớp canonical hoặc review log.
- Fact thiếu nguồn hoặc confidence thấp không được đưa vào `gold`.
- Records có mâu thuẫn vẫn giữ lại nếu có source, nhưng phải gắn `conflict_group_id` hoặc flag tương đương.
- Giá, chính sách, tiến độ, ưu đãi và pháp lý phải có `valid_from`/`valid_to` hoặc flag `validity_unknown`.
- SFT draft có thể dùng synthetic draft, nhưng chỉ `gold/silver` đã review mới được dùng cho training sau này.

### 4.2. Quality statuses

```text
raw
→ canonical
→ needs_review
→ verified
→ rejected
→ archived
```

Áp dụng cho facts, entity candidates, aliases và SFT samples. Không xóa hard-delete các item đã dùng trong snapshot hoặc benchmark.

### 4.3. Entity resolution policy

Tự động merge chỉ khi thỏa ít nhất một điều kiện chắc chắn:

- cùng stable external key;
- cùng source canonical ID;
- cùng project + normalized name + entity type + source xác nhận;
- alias đã được reviewer verified.

Không tự merge khi:

- tên gần giống nhưng khác tòa/phân khu;
- khác project hoặc tenant;
- thiếu source;
- entity type không chắc chắn;
- liên quan giá/pháp lý/tiến độ nhạy cảm.

Candidate mơ hồ phải vào queue với lý do: `AMBIGUOUS_NAME`, `CONFLICTING_SOURCE`, `MISSING_SOURCE`, `LOW_CONFIDENCE`, `POSSIBLE_DUPLICATE`, `TYPE_MISMATCH`.

---

## 5. Schema và migration cần bổ sung/khóa

### 5.1. `fact_reviews`

```text
id, tenant_id, project_id, fact_id, reviewer_id,
status, note, corrected_value_json, reason_code,
created_at
```

### 5.2. `entity_resolution_candidates`

```text
id, tenant_id, project_id, entity_a_id, entity_b_id,
candidate_type, score, reason_code, status,
reviewer_id, decision_note, created_at, decided_at
```

### 5.3. `entity_resolution_decisions`

```text
id, tenant_id, project_id, candidate_id,
decision, surviving_entity_id, rejected_entity_id,
before_json, after_json, decided_by, decided_at
```

### 5.4. `knowledge_snapshots`

```text
id, tenant_id, project_id, snapshot_name,
dataset_version, graph_builder_version, chunker_version,
embedding_model, source_batch_ids_json, stats_json,
created_by, created_at
```

### 5.5. `dataset_versions`

```text
id, tenant_id, version_name, description,
source_snapshot_ids_json, split_policy,
dedup_report_path, leakage_report_path,
data_card_path, status, created_by, created_at
```

### 5.6. `dataset_splits`

```text
id, tenant_id, dataset_version_id, project_id,
split_name, reason, record_count, created_at
```

`split_name` chỉ nhận `train`, `validation`, `test` hoặc `holdout`.

### 5.7. `sft_samples`

```text
id, tenant_id, dataset_version_id, project_id,
channel, persona_id, brand_profile_id, instruction,
facts_json, visual_facts_json, output_json,
claims_json, quality_status, reviewer_id,
created_at, updated_at
```

### 5.8. `retrieval_queries`

```text
id, tenant_id, dataset_version_id, project_id,
query_text, query_type, expected_fact_ids_json,
expected_relationship_ids_json, expected_source_ids_json,
difficulty, notes, created_by, created_at
```

`query_type` gồm: `fact`, `one_hop`, `two_hop`, `comparison`, `conflict`, `temporal`, `global`, `no_evidence`.

---

## 6. API và UI cần hoàn thiện trong Tuần 3

### Fact/source review

```text
GET  /projects/{project_id}/facts
PATCH /projects/{project_id}/facts/{fact_id}/review
GET  /projects/{project_id}/sources/{source_id}
GET  /projects/{project_id}/review-log
```

### Entity resolution

```text
GET  /projects/{project_id}/entity-resolution/candidates
POST /projects/{project_id}/entity-resolution/candidates/{candidate_id}/decision
GET  /projects/{project_id}/entity-resolution/decisions
```

### Dataset và benchmark

```text
POST /datasets/build
GET  /datasets/{dataset_version_id}
GET  /datasets/{dataset_version_id}/splits
GET  /datasets/{dataset_version_id}/sft-samples
GET  /datasets/{dataset_version_id}/retrieval-queries
POST /datasets/{dataset_version_id}/leakage-audit
POST /retrieval/evaluate
```

### UI tối thiểu

- Project Detail / Facts: filter theo status, source, field và confidence.
- Source Viewer: URL, retrieved time, parser version, extracted facts và raw reference.
- Entity Resolution Queue: compare hai entity, source evidence, quyết định merge/reject/pending.
- Dataset Admin: dataset version, split counts, data card link, leakage audit status.
- Retrieval Benchmark Seed: query list, expected evidence, kết quả R1/R2 smoke.

RBAC đề xuất:

- `admin`: build dataset, freeze split, xem toàn bộ audit.
- `marketer`: xem facts/sources, tạo SFT draft ở project được cấp quyền.
- `reviewer`: review facts, quyết định entity resolution nếu được assign.

---

## 7. Kế hoạch theo ngày

## Ngày 1 — 29/07: checkpoint audit và khóa dataset scope

### Công việc

1. Chạy checklist đóng Tuần 2 trên staging thật.
2. Thu bằng chứng: job report, replay counts, data-quality report, graph stats, retrieval smoke và staging URLs.
3. Lập `week_03_carry_over.md` với owner/deadline cho blocker.
4. Chọn batch/snapshot được phép đưa vào `dataset_v1`.
5. Khóa split policy theo project: train/validation/test/holdout.
6. Khóa quality criteria cho `gold`, `silver`, `rejected`.
7. Khóa query taxonomy R1-R3 và rubric gán expected evidence.

### Owner

- Quang: checkpoint kỹ thuật, split policy, dataset builder scope.
- Hải: source manifest, data-quality xác nhận và expected evidence seed.
- Cả nhóm: quyết định blocker/cut scope.

### Đầu ra

- `docs/checkpoints/week_02_actual_status.md` hoặc cập nhật report hiện có.
- `docs/checkpoints/week_03_carry_over.md`.
- `docs/data/dataset_v1_scope.md`.
- `docs/evaluation/retrieval_query_taxonomy_v1.md`.

### Gate Ngày 1

- Mọi artefact Tuần 2 có trạng thái `pass/fail/not_verified`.
- Dataset scope không chứa source thiếu license/provenance.
- Blocker mức cao có owner trước khi build dataset.

---

## Ngày 2 — 30/07: fact/source editor và review log

### Công việc

1. Bổ sung migration `fact_reviews` và review status còn thiếu.
2. Tạo API `PATCH /facts/{fact_id}/review`.
3. Tạo Source Viewer hiển thị source URL, parser version, raw reference và extracted facts.
4. Tạo Facts UI có filter: `verified`, `needs_review`, `rejected`, `missing_source`, `conflict`.
5. Ghi review log bất biến, không overwrite fact cũ mà không có dấu vết.
6. Hải review mẫu tối thiểu 50 facts, cân bằng field: location, unit, price, amenity, legal, description.
7. Chuẩn hóa reason code cho rejected/corrected facts.

### Owner

- Quang: migrations, API, UI và tests.
- Hải: review mẫu và xác nhận source/fact correctness.

### Đầu ra

- Fact/source editor chạy trên staging.
- `docs/data/fact_review_guideline_v1.md`.
- 50 facts được review có log.

### Gate Ngày 2

- Reviewer xem được source trước khi quyết định.
- Fact thiếu source không thể chuyển sang `verified`.
- Mọi correction có reviewer, reason và timestamp.

---

## Ngày 3 — 31/07: entity resolution và graph quality

### Công việc

1. Sinh entity resolution candidates từ alias/name/source rules.
2. Tạo migration/API cho candidates và decisions.
3. Tạo UI compare entity A/B: type, canonical name, aliases, source, edges liên quan.
4. Implement decision: `merge`, `reject`, `split_required`, `pending`.
5. Bảo đảm merge cập nhật alias/edge references trong transaction và giữ decision log.
6. Audit 30 candidates; không auto-merge case mơ hồ.
7. Tính graph quality metrics: entity duplicate rate sample, edge provenance coverage, unsupported-edge count, path precision.
8. Freeze `graph_snapshot_v1_candidate`.

### Owner

- Quang: candidate generator, API/UI, transaction và metrics.
- Hải: xác nhận 30 candidates và edge/path sample.

### Đầu ra

- Entity Resolution Queue trên staging.
- `docs/data/entity_resolution_report_v1.md`.
- `docs/data/graph_quality_report_v1.md`.

### Gate Ngày 3

- Không có merge xuyên tenant/project.
- Mọi edge trong graph snapshot có source hoặc bị loại khỏi production context.
- Path precision trên mẫu human-check được ghi bằng số liệu, không chỉ nhận xét.

---

## Ngày 4 — 01/08: dataset builder, SFT draft và split theo project

### Công việc

1. Tạo `dataset_versions` và `dataset_splits`.
2. Build `dataset_v1_candidate` từ verified/silver facts và source hợp lệ.
3. Dedup trước split theo URL, content hash, canonical project và near-duplicate text.
4. Split theo project: 70% train, 15% validation, 15% test; nếu số project ít, dùng holdout thủ công và ghi lý do.
5. Tạo brand/persona/channel seed tối thiểu:
   - 1 brand demo;
   - 3 persona: young family, investor, first-time buyer;
   - 4 channel: description, Facebook, nurturing email, SEO landing page.
6. Sinh SFT draft samples từ facts đã review, gắn claim -> fact mapping.
7. Gắn `quality_status`: synthetic chưa review chỉ là `draft`, không phải `gold`.
8. Xuất thống kê theo channel/persona/split/source.

### Owner

- Quang: dataset builder, split, sample schema và report.
- Hải: kiểm tra sample nội dung/fact mapping và ưu tiên project holdout.

### Đầu ra

- `dataset_v1_candidate`.
- `docs/data/dataset_v1_data_card.md`.
- `docs/data/dataset_v1_split_report.md`.
- `docs/data/sft_samples_v1_profile.md`.

### Gate Ngày 4

- Không có project xuất hiện ở nhiều split.
- SFT sample không chứa claim thiếu `supported_fact_ids`.
- Data card ghi rõ số lượng `gold/silver/draft/rejected`.

---

## Ngày 5 — 02/08: leakage audit và gold retrieval queries R1-R3

### Công việc

1. Chạy cross-split leakage audit theo exact duplicate, URL/hash, normalized title và near-duplicate text.
2. Sửa split nếu phát hiện leakage; ghi decision log.
3. Tạo 60-90 retrieval queries:
   - 15-20 fact đơn;
   - 15-20 câu 1-hop;
   - 10-15 câu 2-hop;
   - 8-10 comparison;
   - 5-10 conflict/temporal;
   - 5-10 no-evidence;
   - một nhóm global chỉ để chuẩn bị R4, không chặn R1-R3.
4. Gán expected facts/relationships/sources cho từng query.
5. Tạo script/API chạy R1 vector/FTS và R2 graph-only trên query set seed.
6. Lưu raw result, score, latency và evaluator version.
7. Ghi lỗi truy xuất thành taxonomy: `MISSING_CHUNK`, `WRONG_PROJECT`, `WRONG_ENTITY`, `NO_SOURCE`, `PATH_TOO_BROAD`, `STALE_FACT`.

### Owner

- Hải: viết/gán nhãn gold queries và expected evidence.
- Quang: leakage audit, retrieval eval runner và metrics.

### Đầu ra

- `docs/data/dataset_v1_leakage_audit.md`.
- `docs/evaluation/retrieval_queries_v1.md`.
- `docs/evaluation/retrieval_seed_report_r1_r2.md`.
- Raw eval output dưới `experiments/retrieval/runs/` nếu repo code đã tồn tại.

### Gate Ngày 5

- Leakage nghiêm trọng bằng 0 trước khi freeze test split.
- 100% query có `query_type`, `project_id` và expected evidence hoặc nhãn `no_evidence`.
- R1/R2 result không trả dữ liệu xuyên tenant/project.

---

## Ngày 6 — 03/08: freeze snapshot, hardening và staging RC

### Công việc

1. Freeze `dataset_v1` nếu các gate Ngày 1-5 đạt.
2. Freeze `knowledge_snapshot_v1` gồm source batch, graph builder, chunker, embedding model và stats.
3. Hoàn thiện Dataset Admin và Retrieval Benchmark Seed UI.
4. Test RBAC cho reviewer/editor/admin dataset actions.
5. Test migration clean/upgrade cho schema Tuần 3.
6. Chạy backend tests, frontend lint/type-check/build.
7. Chạy smoke test staging từ đăng nhập đến dataset/retrieval report.
8. Cập nhật runbook: build dataset, run leakage audit, run retrieval seed eval.

### Owner

- Quang: freeze/versioning, UI hardening, tests, staging deploy.
- Hải: xác nhận final data card và retrieval query coverage.

### Đầu ra

- Frozen `dataset_v1`.
- Frozen `knowledge_snapshot_v1`.
- `docs/runbooks/dataset_build_and_eval.md`.
- Staging release candidate Tuần 3.

### Gate Ngày 6

- Dataset/snapshot immutable hoặc có status lock rõ.
- Test critical path pass.
- Reviewer không thể freeze dataset nếu không có quyền.

---

## Ngày 7 — 04/08: E2E, demo và đóng tuần

### Kiểm thử cuối

1. Chạy toàn bộ backend unit/integration tests liên quan ingestion, review, entity resolution, dataset và retrieval.
2. Chạy frontend lint/type-check/build.
3. Chạy migration trên database sạch.
4. Build lại `dataset_v1` trên input cố định và so checksum/report.
5. Chạy leakage audit.
6. Chạy R1/R2 seed eval trên query set đã khóa.
7. Kiểm tra thủ công 20 facts, 20 entity decisions, 10 graph paths và 20 retrieval query labels.
8. Smoke test staging từ máy/mạng khác.
9. Quay video demo dự phòng 5-7 phút.

### Kịch bản demo 7 phút

1. Login bằng reviewer.
2. Mở Project Detail và Source Viewer.
3. Review một fact có source đầy đủ và reject một fact thiếu source.
4. Mở Entity Resolution Queue, xử lý một alias chắc chắn và một candidate mơ hồ.
5. Mở Dataset Admin, xem split train/validation/test theo project.
6. Mở leakage audit report và chứng minh không có project trùng split.
7. Chạy retrieval seed query 1-hop và 2-hop, hiển thị expected evidence và kết quả R1/R2.
8. Mở data card và graph quality report.

### Tổng kết

1. Ghi số liệu thực tế vào checkpoint.
2. Ghi issue còn mở, owner và ảnh hưởng Tuần 4.
3. Freeze query set/snapshot dùng cho prompt-only/RAG baseline.
4. Cập nhật nhật ký dự án và link tài liệu.
5. Chốt input Tuần 4: prompt baseline, query router, R3 context assembler và Content Studio.

### Đầu ra

- `docs/checkpoints/week_03_report.md`.
- `docs/data/dataset_v1_data_card.md`.
- `docs/data/dataset_v1_split_report.md`.
- `docs/data/dataset_v1_leakage_audit.md`.
- `docs/data/graph_quality_report_v1.md`.
- `docs/evaluation/retrieval_queries_v1.md`.
- `docs/evaluation/retrieval_seed_report_r1_r2.md`.
- Video/screenshot demo dự phòng.

### Gate đóng Tuần 3

- Demo bắt buộc ở Mục 1 chạy liên tục trên staging.
- `dataset_v1` và `knowledge_snapshot_v1` được version hóa.
- Split theo project và leakage audit pass.
- Fact/source editor, entity resolution queue và review log hoạt động.
- Graph quality có số liệu provenance/path precision.
- 60-90 retrieval queries có expected evidence.
- R1/R2 seed eval chạy được; R3 contract sẵn sàng cho Tuần 4.
- Không có lỗi severity cao về provenance, tenant isolation, split leakage hoặc entity merge sai.

---

## 8. Phân công và RACI rút gọn

| Hạng mục | Quang | Hải | Cả nhóm |
|---|---|---|---|
| Checkpoint Tuần 2 và carry-over | R | C | A |
| Fact/source editor | R/A | C review | I |
| Entity resolution | R | C/A evidence | A policy |
| Graph quality report | R | C | A |
| Dataset builder và split | R/A | C | I |
| SFT draft sample review | C schema | R | A |
| Retrieval queries/gold labels | C runner | R/A | A rubric |
| Leakage audit và retrieval seed eval | R/A | C | I |
| Staging demo/checkpoint | R | R | A |

`R`: thực hiện; `A`: chịu trách nhiệm cuối; `C`: tham vấn; `I`: được thông báo.

---

## 9. Test checklist

### Data và dataset

- [ ] Dataset chỉ lấy records có source/provenance hợp lệ.
- [ ] Split theo project, không theo sample ngẫu nhiên.
- [ ] Dedup chạy trước split.
- [ ] Leakage audit pass và có report.
- [ ] Data card ghi số lượng theo source/channel/persona/split/status.
- [ ] SFT sample có claim -> fact mapping.

### Review và provenance

- [ ] Fact thiếu source không chuyển được sang `verified`.
- [ ] Review log không bị overwrite.
- [ ] Correction có reviewer, reason và timestamp.
- [ ] Source Viewer truy được raw reference hoặc storage key.

### Entity/graph

- [ ] Candidate mơ hồ vào queue, không auto-merge.
- [ ] Merge không xuyên tenant/project.
- [ ] Decision log giữ before/after.
- [ ] Edge production có source.
- [ ] Traversal vẫn giới hạn tối đa 2 hop.

### Retrieval benchmark

- [ ] Query set có đủ loại fact/1-hop/2-hop/comparison/conflict/temporal/no-evidence.
- [ ] Expected evidence gồm fact/relationship/source IDs.
- [ ] R1/R2 runner lưu raw result, score và latency.
- [ ] Query no-evidence không bị ép ra claim giả.
- [ ] Không có kết quả xuyên tenant/project.

### UI và deployment

- [ ] Facts/Source Viewer có loading/empty/error states.
- [ ] Entity Resolution Queue xử lý được merge/reject/pending.
- [ ] Dataset Admin hiển thị split/report/status.
- [ ] Backend/frontend/worker staging hoạt động.
- [ ] Demo được từ máy/mạng khác.

---

## 10. Metrics phải ghi trong checkpoint

### Dataset

- Tổng projects, sources, facts, assets đưa vào `dataset_v1`.
- Tỷ lệ `verified`, `silver`, `draft`, `rejected`.
- Missing rate theo field quan trọng.
- Duplicate và near-duplicate rate.
- Split counts theo project/sample/channel/persona.
- Leakage findings theo loại và số lỗi còn lại.

### Graph và entity resolution

- Entity counts theo type.
- Relationship counts theo type.
- Số alias/candidates sinh ra, merged, rejected, pending.
- Edge provenance coverage, mục tiêu 100% cho production context.
- Path precision trên sample human-check.
- Unsupported-edge count.

### Retrieval

- Số queries theo type.
- Evidence coverage của query labels.
- R1 Recall@k, MRR seed và latency p50/p95.
- R2 path precision/recall seed và latency p50/p95.
- Tỷ lệ query trả sai project/source.
- Error taxonomy counts.

### System

- Test pass/fail/skip counts.
- API p50/p95 cho fact/source/entity/dataset/retrieval endpoints.
- Dataset build duration.
- Leakage audit duration.
- Retrieval eval duration.

Không sửa metric hoặc split sau khi thấy kết quả để làm đẹp báo cáo. Nếu kết quả xấu, giữ làm failure analysis và ưu tiên sửa ở Tuần 4.

---

## 11. Rủi ro và phương án xử lý

| Rủi ro | Dấu hiệu sớm | Xử lý |
|---|---|---|
| Tuần 2 chưa có batch/snapshot ổn định | Không có `week_02_report` hoặc replay fail | Carry-over ingestion; chỉ build dataset candidate từ fixture hợp lệ và ghi blocker |
| Fact thiếu nguồn nhiều | Nhiều record không có `source_id`/URL | Loại khỏi gold, đưa `needs_review`, Hải bổ sung source manifest |
| Entity merge sai | Candidate cùng tên nhưng khác tòa/dự án | Không auto-merge; bắt reviewer quyết định; log before/after |
| Split leakage | Project hoặc near-duplicate xuất hiện ở nhiều split | Re-split theo project; freeze lại và ghi decision |
| SFT sample ít | Gold/silver thấp hơn kỳ vọng | Giữ draft/silver tách biệt; không train trên synthetic chưa review |
| Retrieval labels yếu | Query không có expected evidence rõ | Giảm số query nhưng tăng chất lượng nhãn; mỗi query phải có source/fact/path |
| UI editor tốn thời gian | Fact/source page chưa ổn | Ưu tiên table + source viewer, cắt visualization đẹp |
| Graph quality thấp | Path precision thấp hoặc edge thiếu source | Chặn edge khỏi production context; đưa vào graph audit backlog |

---

## 12. Thứ tự cắt scope nếu thiếu thời gian

1. Dataset Admin UI đẹp; giữ report Markdown/JSON.
2. Batch edit fact trên UI; giữ review từng fact.
3. Entity graph visualization; giữ compare table.
4. SFT sample volume; giữ schema và sample ít nhưng đúng.
5. R3 full metric trong Tuần 3; giữ R3 contract và chuyển đo chính sang Tuần 4.
6. Global query labels cho R4; giữ note chuẩn bị, không chặn R1-R3.

Không được cắt:

- Provenance và review log.
- Entity resolution an toàn.
- Dataset split theo project.
- Dedup/leakage audit.
- Data card.
- Gold retrieval queries R1-R3.
- R1/R2 seed eval.
- Tenant isolation/RBAC.
- Staging checkpoint.

---

## 13. Definition of Done Tuần 3

Tuần 3 chỉ hoàn thành khi:

- [ ] Checkpoint Tuần 2 đã được kiểm tra bằng bằng chứng và blocker được carry-over rõ.
- [ ] Fact/source editor hoạt động, có review log và rule chặn fact thiếu source.
- [ ] Entity resolution queue hoạt động, không auto-merge candidate mơ hồ.
- [ ] Graph quality report có số liệu provenance, duplicate/merge và path precision.
- [ ] `dataset_v1` được build từ data có provenance và có data card.
- [ ] Split train/validation/test theo project đã freeze.
- [ ] Leakage audit pass hoặc mọi lỗi còn lại có owner/deadline trước Tuần 4.
- [ ] SFT draft v1 có schema đúng và claim -> fact mapping.
- [ ] 60-90 retrieval queries R1-R3 có expected evidence.
- [ ] R1/R2 seed eval chạy được và lưu raw result/metric/latency.
- [ ] RBAC/tenant isolation pass cho review, entity resolution và dataset endpoints.
- [ ] Có staging demo, checkpoint report và video/screenshot dự phòng.

---

## 14. Bàn giao sang Tuần 4

Tuần 3 phải bàn giao:

1. Frozen `dataset_v1` và data card.
2. Frozen `knowledge_snapshot_v1`, graph quality report và entity resolution decisions.
3. Retrieval query set R1-R3 cùng expected evidence.
4. R1/R2 seed report và raw outputs.
5. Fact/source editor và Source Viewer đủ ổn định để hỗ trợ evidence UI Tuần 4.
6. R3 context assembler contract: input query/project/snapshot, output chunks + graph paths + citations + warnings.
7. Danh sách blocker có owner: ingestion còn lỗi, labels thiếu, graph quality thấp hoặc UI chưa đủ cho Content Studio.

Đầu vào này cho phép Tuần 4 tập trung vào prompt-only/RAG baseline, query router, R3 graph + vector context assembler, Content Studio, evidence panel và generation logging mà không phải quay lại tranh luận về split hoặc nguồn dữ liệu.
