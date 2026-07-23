# Kế hoạch triển khai chi tiết Tuần 2

## Production ingestion và MVP staging

**Thời gian:** 22/07/2026 - 28/07/2026  
**Phụ thuộc:** checkpoint Tuần 1 và gói crawler do Hải bàn giao.  
**Mục tiêu tuần:** biến vertical slice Tuần 1 thành một pipeline ingestion có thể chạy lặp lại trên staging với batch dữ liệu thật, quản lý source/asset/job đầy đủ, giữ tenant isolation và provenance, đồng thời cung cấp Property Knowledge Graph truy vấn được bằng PostgreSQL.

> Tuần 2 không mặc định Tuần 1 đã hoàn thành. Ngày đầu tiên phải kiểm tra bằng chứng thật. Hạng mục Tuần 1 chưa đạt sẽ được carry-over với owner và deadline, không đánh dấu hoàn thành dựa trên tài liệu kế hoạch.

---

## 1. Demo bắt buộc cuối tuần

Đến cuối ngày 28/07, nhóm phải demo trên URL staging bằng một batch crawler thật:

```text
Đăng nhập
→ chọn/tạo project
→ upload hoặc chọn crawler batch
→ validate contract
→ tạo ingestion job
→ normalize + deduplicate + quarantine lỗi
→ upsert sources/facts/assets
→ dựng canonical entities + deterministic edges
→ tạo chunks/index
→ mở Project Detail
→ xem dữ liệu, nguồn, asset và job report
→ truy vấn Project → Zone → Building → UnitType
→ chạy lại cùng batch và chứng minh không phát sinh duplicate
```

Điều kiện bắt buộc:

1. Pipeline chạy trên staging, không cần sửa database hoặc JSON bằng tay.
2. Import được ít nhất một batch thật có tối thiểu 100 records hợp lệ; nếu crawler chưa đạt quy mô này, dùng toàn bộ batch đã bàn giao và ghi rõ giới hạn.
3. Invalid records được quarantine cùng error code và raw reference; không làm hỏng toàn batch.
4. Chạy lại cùng batch không tạo thêm project, source, fact, entity, edge hoặc asset trùng.
5. 100% fact/edge dùng trong retrieval có `source_id`; source truy ngược được URL và thời điểm thu thập.
6. Graph path `Project → Zone → Building → UnitType` trả bằng dữ liệu thật và giới hạn tối đa 2 hop mỗi lần traversal.
7. Asset được lưu qua object storage hoặc adapter tương đương; database chỉ giữ metadata/key, không nhét binary lớn.
8. Backend kiểm tra authentication, role và `tenant_id` cho upload, job, project, source, asset, graph và retrieval.
9. Có job status, progress/counts, error summary và khả năng retry có kiểm soát.
10. Có test report, data-quality report, staging smoke test và checkpoint Tuần 2.

---

## 2. Điều kiện đầu vào và kiểm tra checkpoint Tuần 1

### 2.1. Artefact cần có

- `docs/checkpoints/week_01_report.md`.
- `packages/contracts/crawler_contract_v1.json`.
- Fixture đã audit và data dictionary.
- Migrations PostgreSQL/pgvector.
- FastAPI/Next.js skeleton, auth/RBAC và project CRUD.
- Ingestion adapter mẫu, graph traversal và retrieval endpoint mẫu.
- Frontend/backend staging URL và runbook deploy.

### 2.2. Ma trận quyết định carry-over

| Checkpoint Tuần 1 | Nếu đạt | Nếu chưa đạt |
|---|---|---|
| Repo/app skeleton và CI | Tiếp tục productionize | Quang hoàn thành trước trưa 22/07 |
| Contract + fixture crawler | Dùng làm input batch | Hải khóa contract/fixture trước trưa 22/07 |
| DB migrations + pgvector | Mở rộng schema | Không làm UI mới trước khi migration sạch chạy được |
| Auth/RBAC/tenant isolation | Mở endpoint ingestion | Chặn deploy dữ liệu thật đến khi test isolation pass |
| Ingestion/graph vertical slice | Mở rộng batch | Giữ batch nhỏ, sửa correctness trước scale |
| Staging URL | Deploy incremental | Dựng staging trước cuối 23/07 |

Nếu đến hết 22/07 còn blocker mức cao về contract, database, tenant isolation hoặc staging, nhóm phải cắt UI nâng cao và asset preview để bảo vệ pipeline cốt lõi.

---

## 3. Phạm vi Tuần 2

### Bắt buộc

- Production ingestion flow theo batch/job.
- Schema validation và contract versioning.
- Normalize, canonical key, dedup, idempotent upsert.
- Quarantine và retry an toàn.
- Source/provenance và temporal metadata.
- Asset metadata + object-storage adapter.
- Canonical Property Graph và entity aliases ban đầu.
- Deterministic relationships từ structured crawler fields.
- Chunk/index update theo dữ liệu mới.
- Project detail, Sources, Assets, Jobs và Graph path trên UI.
- Tenant isolation/RBAC trên toàn bộ luồng.
- Observability, data-quality metrics và staging deployment.

### Không làm trong Tuần 2

- Fine-tuning/QLoRA hoặc tạo dataset SFT hoàn chỉnh.
- Microsoft GraphRAG indexing.
- LLM-based graph extraction hàng loạt.
- Content Studio A-D hoàn chỉnh.
- Vision caption/extraction tự động.
- Neo4j hoặc traversal sâu hơn 2 hop.
- Graph visualization phức tạp.
- Auto-publish nội dung hoặc tích hợp mạng xã hội.

---

## 4. Thiết kế pipeline production ingestion

### 4.1. State machine của job

```text
created
→ validating
→ processing
→ indexing
→ completed
```

Nhánh lỗi:

```text
validating/processing/indexing
→ partial_failed hoặc failed
→ retrying
→ completed/partial_failed/failed
```

Yêu cầu:

- Transition phải hợp lệ và lưu timestamp.
- Retry không tạo bản ghi trùng.
- `partial_failed` vẫn giữ records thành công và quarantine records lỗi.
- Không retry vô hạn; cấu hình `max_attempts` và backoff.
- Mỗi job khóa `contract_version`, `parser_version`, `normalizer_version`, `graph_builder_version`, `chunker_version`.

### 4.2. Các stage

1. **Register input:** ghi batch, checksum, project, tenant, uploader và storage key.
2. **Validate:** JSON Schema, required fields, encoding, URL, timestamp và enum.
3. **Normalize:** whitespace/Unicode, URL, names, unit/price/date và canonical keys.
4. **Deduplicate:** ưu tiên external key, canonical URL, content hash; ghi quyết định merge/skip.
5. **Persist:** upsert source, project domain data, facts và asset metadata trong transaction phù hợp.
6. **Build graph:** entity/alias/edge deterministic, provenance và validity.
7. **Chunk/index:** chỉ re-index record thay đổi; giữ version/snapshot.
8. **Finalize:** counts, warnings, errors, duration và quality report.

### 4.3. Nguyên tắc lỗi

- Lỗi contract ở record nào quarantine record đó.
- Lỗi hạ tầng toàn batch mới đánh `failed`.
- Không nuốt exception; map sang error code ổn định.
- Raw payload được tham chiếu bằng storage key/checksum, không copy vô hạn vào log.
- PII/secret không xuất hiện trong structured log.

---

## 5. Schema và migration cần bổ sung/khóa

### 5.1. `ingestion_batches`

```text
id, tenant_id, project_id, input_type, original_filename,
storage_key, checksum, contract_version, parser_version,
record_count, uploaded_by, created_at
```

Unique đề xuất: `(tenant_id, checksum, contract_version)`.

### 5.2. `ingestion_jobs`

```text
id, tenant_id, project_id, batch_id, status, current_stage,
attempt, max_attempts, total_count, valid_count, inserted_count,
updated_count, skipped_count, quarantined_count, error_count,
started_at, finished_at, versions_json, error_summary_json,
created_by, created_at, updated_at
```

### 5.3. `ingestion_errors`

```text
id, tenant_id, job_id, record_key, stage, error_code,
error_message, field_path, raw_reference, retryable,
resolved_at, created_at
```

### 5.4. `sources`

Phải có tối thiểu:

```text
id, tenant_id, project_id, source_type, canonical_url,
title, publisher, retrieved_at, published_at, content_hash,
parser_version, license_status, raw_storage_key,
valid_from, valid_to, created_at, updated_at
```

### 5.5. `assets`

```text
id, tenant_id, project_id, source_id, asset_type,
storage_key, original_url, mime_type, byte_size,
width, height, checksum, alt_text, metadata_json,
review_status, created_at, updated_at
```

### 5.6. Graph và aliases

- `graph_entities`: unique canonical/external key theo tenant/project/type.
- `graph_entity_aliases`: alias normalized, language, source, confidence và review status.
- `graph_relationships`: unique theo source node/type/target node/source/validity phù hợp.
- `graph_claims`: liên kết fact/edge với evidence source.
- Không merge entity mơ hồ chỉ vì tên gần giống; đưa vào review queue cho Tuần 3.

### 5.7. Ràng buộc bắt buộc

- Mọi bảng nghiệp vụ có `tenant_id` và index phù hợp.
- Foreign key không cho cross-tenant reference ở application/service checks; thêm composite constraint nếu khả thi.
- Soft delete hoặc status cho artefact cần audit; không xóa provenance khi source đổi.
- Migration phải chạy được từ database sạch và upgrade từ schema Tuần 1.

---

## 6. API cần hoàn thiện trong Tuần 2

### Ingestion

```text
POST /projects/{project_id}/ingestion/batches
POST /projects/{project_id}/ingestion/batches/{batch_id}/run
GET  /projects/{project_id}/ingestion/jobs
GET  /projects/{project_id}/ingestion/jobs/{job_id}
GET  /projects/{project_id}/ingestion/jobs/{job_id}/errors
POST /projects/{project_id}/ingestion/jobs/{job_id}/retry
```

### Sources và assets

```text
GET /projects/{project_id}/sources
GET /projects/{project_id}/sources/{source_id}
GET /projects/{project_id}/assets
GET /projects/{project_id}/assets/{asset_id}
```

### Knowledge

```text
GET  /projects/{project_id}/facts
GET  /projects/{project_id}/graph
POST /retrieval/search
```

### Contract response chung

Mọi response list có pagination. Job response phải trả:

```json
{
  "job_id": "...",
  "status": "partial_failed",
  "current_stage": "indexing",
  "counts": {
    "total": 120,
    "valid": 116,
    "inserted": 100,
    "updated": 10,
    "skipped": 6,
    "quarantined": 4
  },
  "versions": {
    "contract": "crawler_contract_v1",
    "normalizer": "normalizer_v1",
    "graph_builder": "graph_builder_v1",
    "chunker": "chunker_v1"
  },
  "errors_url": "/projects/.../jobs/.../errors"
}
```

RBAC đề xuất:

- `admin`: upload/run/retry và xem toàn bộ job trong tenant.
- `marketer`: upload/run và xem project được cấp quyền; không thay đổi system config.
- `reviewer`: read-only sources/assets/facts/graph trong Tuần 2.

---

## 7. Kế hoạch theo ngày

## Ngày 1 — 22/07: checkpoint audit và khóa batch contract

### Công việc

1. Chạy checklist đóng Tuần 1 trên repo/staging thật.
2. Thu bằng chứng: test output, migrations, URLs, fixture replay và provenance sample.
3. Tạo carry-over board: blocker, owner, deadline, impact và cut scope.
4. Hải bàn giao batch crawl đầu tiên, manifest nguồn và quality summary.
5. Kiểm tra checksum, encoding, duplicate, missing fields, image URLs và parser version.
6. Khóa compatibility rules giữa batch mới và `crawler_contract_v1`.
7. Khóa schema/state machine/API Tuần 2 và ADR nếu khác thiết kế cũ.

### Owner

- Hải: batch, manifest, missing/duplicate report và giải thích contract.
- Quang: checkpoint kỹ thuật, schema/API và staging audit.
- Cả nhóm: quyết định carry-over/cut.

### Đầu ra

- `docs/checkpoints/week_01_actual_status.md` hoặc cập nhật report hiện có.
- `docs/data/batch_01_profile.md`.
- `docs/checkpoints/week_02_carry_over.md`.
- Contract compatibility tests/fixtures.

### Gate Ngày 1

- Mọi checkpoint Tuần 1 có trạng thái `pass/fail/not_verified` và bằng chứng.
- Batch có checksum, source manifest, parser version và contract version.
- Blocker mức cao có owner trước khi bắt đầu tính năng mới.

---

## Ngày 2 — 23/07: schema, storage và job orchestration

### Công việc

1. Viết migrations cho batch/job/error/source/asset và constraints còn thiếu.
2. Chạy migration từ database sạch và upgrade từ snapshot Tuần 1.
3. Tạo object-storage interface: put/get metadata/presigned URL hoặc local adapter cho test.
4. Tạo batch registration với checksum/idempotency key.
5. Triển khai state machine và job repository/service.
6. Tạo worker/background execution có timeout, retry giới hạn và structured logs.
7. Bổ sung request ID, job ID, tenant ID vào log context.

### Owner

- Quang: database, storage adapter, orchestration và tests.
- Hải: cung cấp payload lỗi/biên để test.

### Đầu ra

- Migrations và rollback note.
- Storage adapter + test double.
- Job state machine và API skeleton.

### Gate Ngày 2

- Migration sạch/upgrade đều pass.
- Cùng checksum không tạo batch trùng ngoài policy đã chốt.
- Invalid state transition bị từ chối.
- Worker lỗi không để job kẹt vô thời hạn.

---

## Ngày 3 — 24/07: validation, normalization và quarantine

### Công việc

1. Validate streaming/batch theo JSON Schema, không load file quá lớn thiếu kiểm soát.
2. Chuẩn hóa Unicode tiếng Việt, whitespace, URL, ngày, số, đơn vị và canonical name.
3. Tạo stable external/canonical keys theo entity type.
4. Deduplicate theo thứ tự: external key → canonical URL → content hash → review candidate.
5. Ghi invalid records vào `ingestion_errors`/quarantine.
6. Thêm error taxonomy: `SCHEMA_INVALID`, `MISSING_SOURCE`, `INVALID_DATE`, `DUPLICATE`, `ASSET_UNREACHABLE`, `UNKNOWN_ENTITY_REFERENCE`, `SYSTEM_ERROR`.
7. Sinh data-quality summary theo batch.

### Owner

- Hải: xác nhận rules nghiệp vụ và đối chiếu 15 records với nguồn.
- Quang: validator, normalizer, dedup, quarantine và metrics.

### Đầu ra

- `normalizer_v1` và versioned rules.
- Quarantine UI/API dữ liệu tối thiểu.
- `docs/data/batch_01_quality_report.md`.

### Gate Ngày 3

- 100% record được phân loại valid/quarantined, không mất âm thầm.
- UTF-8 tiếng Việt và canonical keys ổn định qua hai lần chạy.
- Báo cáo missing/duplicate khớp counts trong job.

---

## Ngày 4 — 25/07: canonical persistence và Property Graph

### Công việc

1. Upsert sources, project data, facts và assets theo transaction boundary rõ.
2. Gắn source, validity, confidence, extraction method và review status.
3. Dựng entities thuộc ontology v1: Developer, Project, Zone, Building, UnitType, Amenity, Source.
4. Dựng deterministic edges: DEVELOPS, PART_OF, HAS_ZONE, HAS_BUILDING, HAS_UNIT_TYPE, HAS_AMENITY, SUPPORTED_BY.
5. Ghi aliases chắc chắn; alias mơ hồ vào review candidate, không auto-merge.
6. Bảo đảm graph builder chạy lại idempotent.
7. Tạo traversal/query methods có project/tenant filter và tối đa 2 hop.

### Owner

- Quang: persistence, graph builder, traversal và tests.
- Hải: xác nhận entity/edge trên sample nguồn thật.

### Đầu ra

- Canonical batch trong PostgreSQL staging.
- Graph statistics theo entity/relationship type.
- 10 evidence paths đã human-check.

### Gate Ngày 4

- 100% edge production có source/provenance.
- Không có entity/edge cross-tenant hoặc cross-project ngoài quan hệ được thiết kế.
- Replay cùng batch không tăng counts sai dự kiến.
- Path Project → Zone → Building → UnitType truy vấn được từ dữ liệu thật.

---

## Ngày 5 — 26/07: incremental indexing và project UI

### Công việc

1. Tạo/update chunks chỉ cho source/fact thay đổi.
2. Gắn `knowledge_snapshot_id`, chunker version và source metadata.
3. Cập nhật FTS/pgvector index; xử lý embedding provider timeout/rate limit.
4. Hoàn thiện Project Detail tabs: Overview, Facts, Graph, Sources, Assets, Jobs.
5. Jobs UI hiển thị stage, progress, counts, lỗi và retry action theo role.
6. Sources/Assets UI hiển thị provenance, validity, parser/retrieval time và preview an toàn.
7. Graph UI ưu tiên path/table; chỉ thêm visualization nếu còn thời gian.

### Owner

- Quang: indexing, API và UI.
- Hải: kiểm tra nội dung/source mapping của sample hiển thị.

### Đầu ra

- Incremental index và snapshot metadata.
- Project/Source/Asset/Job UI trên staging.
- Retrieval smoke results cho batch mới.

### Gate Ngày 5

- Unchanged records không bị embed/index lại ngoài policy.
- Search result luôn có project/tenant/source filters.
- User có thể đi từ fact/path đến source tương ứng trên UI.

---

## Ngày 6 — 27/07: bảo mật, observability và staging hardening

### Công việc

1. Test RBAC cho upload/run/retry/read.
2. Test tenant isolation ở database service, API và storage key namespace.
3. Giới hạn file size/type, chống path traversal và kiểm tra MIME/checksum.
4. Thêm pagination, timeout và rate limit cơ bản cho endpoint nặng.
5. Dashboard/log tối thiểu: job duration, record counts, quarantine rate, API errors, indexing duration.
6. Chạy load smoke với batch mục tiêu và nhiều lần replay.
7. Deploy migrations/backend/worker/frontend lên staging.
8. Cập nhật deploy/rollback/retry runbook.

### Owner

- Quang: security, observability, deploy và runbooks.
- Hải: replay crawler batch và xác nhận data report.

### Đầu ra

- Security/integration test report.
- Staging release candidate Tuần 2.
- Updated runbooks.

### Gate Ngày 6

- Không có lỗi severity cao về auth, tenant isolation, upload hoặc provenance.
- Worker restart không làm mất job state hoặc tạo duplicate.
- Frontend staging không gọi localhost; storage/database đều là staging services.

---

## Ngày 7 — 28/07: E2E, demo và đóng tuần

### Kiểm thử cuối

1. Chạy backend unit/integration tests và frontend lint/type-check/build.
2. Chạy migrations trên database sạch.
3. Upload và ingest batch thật từ đầu trên staging.
4. Replay cùng batch ít nhất hai lần, so sánh counts/checksum.
5. Kiểm tra thủ công 15 facts, 15 edges và 10 assets với nguồn.
6. Chạy tenant isolation negative tests.
7. Đo ingestion duration, quarantine rate, indexing duration và API/retrieval p50/p95.
8. Demo từ máy/mạng khác và quay video dự phòng.

### Kịch bản demo 6 phút

1. Login bằng marketer và mở project.
2. Upload crawler batch và chạy ingestion.
3. Xem job chuyển stage, counts và quarantine errors.
4. Mở fact/source/asset vừa nhập.
5. Mở graph path Project → Zone → Building → UnitType.
6. Search một câu fact và một câu relation, hiển thị source/path.
7. Replay batch và chứng minh counts không tăng sai.
8. Login bằng role không đủ quyền để chứng minh backend chặn retry/admin action.

### Tổng kết

1. Ghi số liệu thực tế, issue còn mở và technical debt.
2. Freeze `batch_01`/snapshot phù hợp làm đầu vào Tuần 3.
3. Chuyển alias/entity mơ hồ sang entity-resolution backlog Tuần 3.
4. Cập nhật nhật ký dự án và kế hoạch Tuần 3 dựa trên kết quả thật.

### Đầu ra

- `docs/checkpoints/week_02_report.md`.
- `docs/data/batch_01_quality_report.md`.
- `docs/runbooks/ingestion_operations.md`.
- Test/metric report và staging URLs.
- Video/screenshot demo dự phòng.

### Gate đóng Tuần 2

- Demo bắt buộc ở Mục 1 chạy liên tục trên staging.
- Không sửa dữ liệu/database bằng tay để đạt demo.
- Không có lỗi severity cao về tenant isolation, idempotency hoặc provenance.
- Batch và knowledge snapshot được version hóa cho Tuần 3.

---

## 8. Phân công và RACI rút gọn

| Hạng mục | Quang | Hải | Cả nhóm |
|---|---|---|---|
| Checkpoint Tuần 1 | R | C | A |
| Crawler batch/contract/source manifest | C | R/A | I |
| Schema/migration/job/worker | R/A | C | I |
| Normalize/dedup/quarantine | R | C/A rules | I |
| Canonical graph/traversal | R | C evidence | A ontology |
| UI/API/storage/deploy | R/A | C | I |
| Data-quality report | C | R | A |
| E2E/demo/checkpoint | R | R | A |

`R`: thực hiện; `A`: chịu trách nhiệm cuối; `C`: tham vấn; `I`: được thông báo.

---

## 9. Test checklist

### Contract và data quality

- [ ] Batch đúng contract/version hoặc có compatibility rule rõ.
- [ ] UTF-8 tiếng Việt, date/unit/URL normalization pass.
- [ ] Missing/duplicate/quarantine counts khớp report.
- [ ] Raw source truy ngược được bằng checksum/storage reference.

### Idempotency và recovery

- [ ] Upload cùng checksum xử lý theo policy, không tạo batch ngoài ý muốn.
- [ ] Replay job không tạo canonical records trùng.
- [ ] Partial failure giữ records thành công.
- [ ] Retry chỉ chạy stage/records phù hợp.
- [ ] Worker restart không mất trạng thái.

### Database và graph

- [ ] Migration clean/upgrade pass.
- [ ] Entity/alias/edge unique constraints đúng.
- [ ] 100% edge production có provenance.
- [ ] Traversal tối đa 2 hop và filter project/tenant.
- [ ] Alias mơ hồ không bị auto-merge.

### Security

- [ ] Auth bắt buộc trên mọi endpoint nghiệp vụ.
- [ ] Backend kiểm tra role upload/run/retry/read.
- [ ] Tenant A không đọc job/source/asset/graph tenant B.
- [ ] Storage key/presigned access không xuyên tenant.
- [ ] File size/type/MIME/checksum được kiểm tra.
- [ ] Secret/raw sensitive payload không nằm trong log.

### UI và deployment

- [ ] Project tabs có loading/empty/error states.
- [ ] Job progress/count/error/retry hiển thị đúng.
- [ ] Fact/path liên kết được source.
- [ ] Frontend/backend/worker/database/storage staging hoạt động.
- [ ] Demo được từ máy/mạng khác.

---

## 10. Metrics phải ghi trong checkpoint

### Ingestion

- Tổng records, valid, inserted, updated, skipped và quarantined.
- Missing rate theo field và duplicate rate.
- Throughput records/phút.
- Tổng duration và duration từng stage.
- Retry count và failure rate.
- Tỷ lệ replay tạo duplicate: mục tiêu 0%.

### Knowledge Graph và provenance

- Entity/edge counts theo type.
- Tỷ lệ edge có source: mục tiêu 100% cho production context.
- Tỷ lệ fact có source.
- Số alias/merge candidates cần review.
- Path validation precision trên 10 path human-check.

### Index/retrieval/system

- Số chunks mới/cập nhật/bỏ qua.
- Embedding/index duration và provider error rate.
- Retrieval evidence hit rate trên bộ query Tuần 1 với batch mới.
- API/job p50/p95 và error rate.
- Test pass/fail/skip counts.

Không sửa ngưỡng sau khi đo để làm đẹp báo cáo. Nếu không đạt, ghi failure analysis và kế hoạch sửa Tuần 3.

---

## 11. Rủi ro và phương án xử lý

| Rủi ro | Dấu hiệu sớm | Xử lý |
|---|---|---|
| Tuần 1 chưa đạt | Thiếu repo/staging/contract sáng 22/07 | Carry-over trước tính năng mới; cắt UI nâng cao |
| Batch crawler đổi schema | Validation fail hàng loạt | Compatibility adapter có version; không sửa raw data âm thầm |
| Dữ liệu trùng/merge sai | Counts tăng sau replay | Stable keys, unique constraints, merge log và review queue |
| Worker/job không ổn định | Job kẹt hoặc chạy hai lần | State machine, lease/lock, idempotency key, bounded retry |
| Asset tải lỗi/tốn dung lượng | Nhiều broken URL/timeout | Metadata trước, retry giới hạn, placeholder; không chặn text ingestion |
| Cross-tenant leak | Test negative trả dữ liệu | Chặn release; sửa filter/storage namespace trước mọi demo |
| Graph edge thiếu nguồn | Path đẹp nhưng không audit được | Loại edge khỏi production context; đưa quarantine/review |
| Embedding API lỗi | Index stage thất bại | Cache, retry giới hạn, index text/FTS trước; job `partial_failed` rõ |
| Staging quá yếu | Batch timeout | Chunk batch, background worker, đo limit và giảm batch demo có ghi rõ |

---

## 12. Thứ tự cắt scope nếu thiếu thời gian

1. Thumbnail/preview asset nâng cao.
2. Drag-and-drop nhiều định dạng upload.
3. Realtime progress bằng WebSocket; dùng polling.
4. Graph visualization; giữ path/table.
5. Retry từng record trên UI; giữ retry theo job/stage.
6. Embedding lại toàn batch; ưu tiên FTS + incremental records.

Không được cắt:

- Contract validation và quarantine.
- Idempotency/dedup.
- Tenant isolation/RBAC.
- Source/provenance.
- Canonical graph và path thật.
- Job status và staging deployment.
- Test/checkpoint report.

---

## 13. Definition of Done Tuần 2

Tuần 2 chỉ hoàn thành khi:

- [ ] Checkpoint Tuần 1 đã được kiểm tra bằng bằng chứng và blocker được carry-over rõ.
- [ ] Một batch crawler thật chạy end-to-end trên staging.
- [ ] Validation, normalize, dedup, quarantine và retry có test.
- [ ] Replay cùng batch không tạo duplicate ngoài policy.
- [ ] Sources/facts/assets/entities/edges có tenant và provenance đúng.
- [ ] Property Graph trả được path mục tiêu từ dữ liệu thật.
- [ ] Project UI hiển thị Sources, Assets, Jobs, Facts và Graph path.
- [ ] RBAC và tenant isolation pass ở API, database service và storage.
- [ ] Migrations chạy được trên database sạch và upgrade path.
- [ ] Có metrics ingestion/graph/index/system thực tế.
- [ ] Có staging URLs, smoke test, runbook và video demo dự phòng.
- [ ] `batch_01` và knowledge snapshot được khóa làm đầu vào Tuần 3.

---

## 14. Bàn giao sang Tuần 3

Tuần 2 phải bàn giao:

1. Versioned canonical dataset và source manifest.
2. Data-quality report cùng quarantine/error taxonomy.
3. Graph snapshot, ontology/graph-builder version và danh sách alias/merge candidates.
4. Knowledge chunks/index snapshot và retrieval smoke results.
5. Stable staging APIs/UI cho fact/source editor và entity resolution Tuần 3.
6. Danh sách technical debt có owner, không giấu lỗi bằng chỉnh dữ liệu tay.

Đầu vào này cho phép Tuần 3 tập trung vào chất lượng knowledge base, entity resolution, dataset SFT v1, split chống leakage và bộ retrieval benchmark R1-R3 thay vì quay lại sửa hạ tầng cơ bản.
