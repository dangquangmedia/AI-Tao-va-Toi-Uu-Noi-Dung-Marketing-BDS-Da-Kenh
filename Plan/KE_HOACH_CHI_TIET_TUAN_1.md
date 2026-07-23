# Kế hoạch triển khai chi tiết Tuần 1

## AI tạo và tối ưu nội dung marketing BĐS đa kênh

**Thời gian:** 15/07/2026 - 21/07/2026  
**Giả định đầu vào:** Hải đã bàn giao đầy đủ crawler, dữ liệu mẫu và tài liệu sử dụng dữ liệu.  
**Mục tiêu tuần:** tạo một vertical slice chạy online từ dữ liệu crawler đến PostgreSQL Property Knowledge Graph, truy xuất evidence và hiển thị project trên web sau khi đăng nhập.

---

## 1. Kết quả bắt buộc cuối tuần

Đến cuối ngày 21/07, nhóm phải demo được luồng:

```text
Crawler export
→ validate
→ import PostgreSQL
→ tạo canonical entities và deterministic relationships
→ tạo knowledge chunks + embeddings mẫu
→ truy xuất facts/path theo project
→ FastAPI trả evidence có source
→ Next.js hiển thị project, facts và graph path
```

Các điều kiện bắt buộc:

1. Có Git repository và quy trình branch/review rõ ràng.
2. Có môi trường local chạy bằng một quy trình thống nhất.
3. Có URL staging cho frontend và backend.
4. Đăng nhập được và backend thực sự kiểm tra role.
5. Tạo/xem project được.
6. Import được ít nhất 20-50 bản ghi crawler mà không sửa tay.
7. Truy vấn được ít nhất một graph path:

   ```text
   Project → Zone → Building → UnitType
   ```

8. Mỗi fact/relationship hiển thị được `source_id` hoặc `source_url`.
9. Có test tự động cho schema validation, tenant isolation và graph traversal cơ bản.
10. Có tài liệu checkpoint, danh sách lỗi và quyết định kiến trúc.

Tuần 1 chưa cần sinh content hoàn chỉnh, fine-tuning, Microsoft GraphRAG hoặc giao diện đẹp như bản mockup cuối.

---

## 2. Đầu vào crawler cần có trước khi bắt đầu

### 2.1. Gói bàn giao tối thiểu

```text
crawler/
data/
  raw/
  fixtures/
    crawler_sample.json
docs/
  crawler_readme.md
  source_policy.md
  field_dictionary.md
  known_issues.md
```

Gói bàn giao phải có:

- Source code và lệnh chạy crawler.
- Phiên bản dependency/runtime.
- 20-50 records fixture ổn định.
- Raw sample chưa normalize.
- Output sample đã normalize.
- Data dictionary.
- Danh sách nguồn và quy định sử dụng.
- Cách xác định `source_id`, `content_hash`, `parser_version`.
- Danh sách field có thể thiếu.
- Known issues và crawler failure cases.

### 2.2. Audit bàn giao

Không mặc định crawler đúng chỉ vì chạy được. Thực hiện:

- Chạy lại crawler hoặc replay fixture theo README.
- So schema thực tế với contract.
- Kiểm tra encoding tiếng Việt.
- Kiểm tra URL, timestamp, hash và parser version.
- Đếm missing rate theo field.
- Kiểm tra duplicate theo URL/hash.
- Kiểm tra ảnh có liên kết đúng project/unit.
- Chọn ngẫu nhiên 10 records đối chiếu với nguồn.
- Ghi mọi sai lệch vào `docs/crawler_handoff_audit.md`.

Nếu crawler có lỗi, không sửa trực tiếp contract một cách âm thầm. Tạo issue, ghi owner và quyết định compatibility ở ingestion adapter.

---

## 3. Phạm vi kỹ thuật Tuần 1

### Bắt buộc

- Repo structure.
- Docker/local development.
- PostgreSQL + pgvector.
- Database migrations.
- Auth và RBAC cơ bản.
- Project CRUD tối thiểu.
- Ingestion adapter từ crawler fixture.
- Canonical entities và deterministic graph edges.
- Knowledge chunks và embedding cho tập nhỏ.
- API retrieval minh họa.
- UI project/evidence tối thiểu.
- Staging deployment.
- Test và documentation.

### Chưa làm trong Tuần 1

- Fine-tuning/QLoRA.
- Microsoft GraphRAG indexing.
- Global/DRIFT Search.
- Critic-refiner.
- Vision extraction hoàn chỉnh.
- Export DOCX/PDF.
- Dashboard thí nghiệm hoàn chỉnh.
- Neo4j.
- Graph traversal sâu hơn 2 hop.

---

## 4. Cấu trúc repository đề xuất

```text
estate-ai/
  apps/
    web/                    # Next.js
    api/                    # FastAPI
  workers/                  # ingestion/indexing jobs; có thể để skeleton
  packages/
    contracts/              # JSON Schema/OpenAPI/types dùng chung
  data/
    fixtures/               # sample nhỏ, được phép commit
  database/
    migrations/
    seeds/
  experiments/
    retrieval/
    graphrag/               # để trống/skeleton trong tuần 1
  tests/
    integration/
  docs/
    architecture/
    data/
    runbooks/
  docker-compose.yml
  .env.example
  README.md
```

Không commit raw dataset lớn, ảnh lớn, secret hoặc API key.

---

## 5. Schema cần khóa trong Tuần 1

### 5.1. Transactional entities

- `users`
- `roles`
- `user_roles`
- `tenants`
- `projects`
- `sources`
- `assets`
- `ingestion_jobs`

### 5.2. Canonical knowledge

- `facts`
- `knowledge_chunks`
- `graph_entities`
- `graph_entity_aliases`
- `graph_relationships`
- `graph_claims`

### 5.3. Trường graph bắt buộc

`graph_entities`:

```text
id, tenant_id, entity_type, canonical_name, normalized_name,
external_key, properties_json, source_id, confidence,
review_status, valid_from, valid_to, created_at, updated_at
```

`graph_relationships`:

```text
id, tenant_id, source_entity_id, relationship_type,
target_entity_id, properties_json, source_id, confidence,
extraction_method, review_status, valid_from, valid_to,
created_at, updated_at
```

`knowledge_chunks`:

```text
id, tenant_id, project_id, source_id, content,
metadata_json, embedding, chunker_version, created_at
```

### 5.4. Ontology v1

Chỉ khóa các node/edge cần cho vertical slice.

Node:

```text
Developer, Project, Zone, Building, UnitType, Amenity, Source
```

Relationship:

```text
DEVELOPS, PART_OF, HAS_ZONE, HAS_BUILDING,
HAS_UNIT_TYPE, HAS_AMENITY, SUPPORTED_BY
```

Không thêm loại quan hệ mới nếu chưa có query/use case chứng minh cần thiết.

---

## 6. API tối thiểu cuối Tuần 1

### System

```text
GET /health
GET /ready
```

### Auth

```text
POST /auth/login
GET  /auth/me
```

### Projects

```text
GET  /projects
POST /projects
GET  /projects/{project_id}
```

### Ingestion

```text
POST /ingestion/fixtures
GET  /ingestion/jobs/{job_id}
```

### Knowledge

```text
GET  /projects/{project_id}/facts
GET  /projects/{project_id}/graph
POST /retrieval/search
```

`POST /retrieval/search` phải trả tối thiểu:

```json
{
  "query": "căn 2PN thuộc tòa nào",
  "project_id": "...",
  "chunks": [
    {
      "content": "...",
      "source_id": "...",
      "score": 0.91
    }
  ],
  "paths": [
    {
      "nodes": ["Project", "Zone", "Building", "UnitType"],
      "relationships": ["HAS_ZONE", "HAS_BUILDING", "HAS_UNIT_TYPE"],
      "source_ids": ["..."]
    }
  ]
}
```

---

## 7. Kế hoạch theo ngày

## Ngày 1 — 15/07: audit bàn giao và khóa quyết định

### Buổi sáng

1. Tạo repository và issue board.
2. Tạo các nhãn: `data`, `backend`, `frontend`, `infra`, `research`, `bug`, `blocked`.
3. Import hoặc liên kết module crawler đúng ranh giới; không copy code không kiểm soát.
4. Chạy crawler/replay fixture theo README.
5. Sinh báo cáo thống kê:
   - số records;
   - missing rate;
   - duplicate URL/hash;
   - ảnh thành công/thất bại;
   - danh sách parser version.

### Buổi chiều

1. Đối chiếu 10 records với nguồn.
2. Khóa `crawler_contract_v1`.
3. Khóa ontology v1.
4. Khóa research questions và ma trận A-D/R1-R4 ở mức proposal.
5. Tạo Architecture Decision Records:
   - ADR-001: PostgreSQL + pgvector.
   - ADR-002: Property Graph dùng relational tables.
   - ADR-003: traversal production tối đa 2 hop.
   - ADR-004: Microsoft GraphRAG ngoài critical path.
6. Chốt Definition of Done Tuần 1.

### Đầu ra

- `docs/crawler_handoff_audit.md`
- `packages/contracts/crawler_contract_v1.json`
- `docs/data/data_dictionary.md`
- `docs/architecture/ontology_v1.md`
- `docs/architecture/adr/*.md`
- Issue board có owner và deadline.

### Gate Ngày 1

- Fixture parse được 100% hoặc có quarantine rõ ràng.
- Không còn field quan trọng chưa định nghĩa.
- Mọi nguồn có policy note.
- Ontology v1 được cả nhóm đồng ý.

---

## Ngày 2 — 16/07: skeleton ứng dụng và database

### Backend/Database

1. Khởi tạo FastAPI.
2. Thiết lập config theo environment, tuyệt đối không hard-code secret.
3. Khởi tạo SQLAlchemy và Alembic.
4. Tạo PostgreSQL + pgvector bằng Docker Compose.
5. Viết migration cho bảng transactional và knowledge.
6. Thêm unique/index constraints:
   - tenant + external key;
   - content hash;
   - graph source/target/type;
   - project/source lookup.
7. Tạo seed cho tenant, admin user và project demo.
8. Tạo `/health` và `/ready`.

### Frontend

1. Khởi tạo Next.js + TypeScript.
2. Tạo design tokens cơ bản theo mockup.
3. Tạo layout sidebar/topbar.
4. Tạo route login, dashboard, projects.
5. Tạo API client và environment config.

### DevOps

1. Tạo `.env.example`.
2. Tạo `docker-compose.yml`.
3. Tạo lint/type-check/test scripts.
4. Tạo CI bước đầu: backend lint/test, frontend lint/type-check/build.

### Đầu ra

- App frontend/backend chạy local.
- Migration up/down chạy được.
- `/health` và `/ready` trả đúng trạng thái.
- CI được kích hoạt.

### Gate Ngày 2

- Một thành viên khác clone repo và chạy được bằng README.
- Database không phụ thuộc dữ liệu tạo tay ngoài seed/migration.

---

## Ngày 3 — 17/07: auth, RBAC và project CRUD

### Auth/RBAC

1. Tạo role `admin`, `marketer`, `reviewer`.
2. Triển khai login và current-user endpoint.
3. Chọn một cơ chế session/token nhất quán.
4. Backend kiểm tra role trên endpoint; frontend chỉ phản ánh quyền, không phải lớp bảo vệ chính.
5. Hash password, thiết lập expiry và cấu hình CORS đúng staging origin.

### Project vertical slice

1. Tạo project/list/detail endpoints.
2. Thêm tenant filtering bắt buộc.
3. Tạo project list UI.
4. Tạo project detail shell gồm tabs Facts, Graph, Sources, Assets.
5. Thêm trạng thái loading, empty và error.

### Tests

1. Login đúng/sai.
2. Endpoint yêu cầu authentication.
3. Marketer không gọi được admin-only endpoint.
4. User tenant A không đọc project tenant B.
5. Project create/list/detail happy path.

### Đầu ra

- Login UI hoạt động.
- Project CRUD tối thiểu hoạt động.
- RBAC và tenant isolation có test.

### Gate Ngày 3

- Không endpoint nghiệp vụ nào bỏ tenant filter.
- Demo login → project list → project detail chạy liên tục.

---

## Ngày 4 — 18/07: ingestion adapter và canonical graph

### Ingestion adapter

1. Đọc fixture đúng `crawler_contract_v1`.
2. Validate bằng schema trước khi ghi database.
3. Record lỗi đưa vào quarantine, không làm fail toàn batch.
4. Upsert `sources`, `projects`, `facts`, `assets`.
5. Chuẩn hóa canonical key.
6. Ghi `ingestion_job` với counts và lỗi.
7. Bảo đảm chạy lại cùng fixture không tạo duplicate.

### Property Graph

1. Tạo entity theo ontology v1.
2. Tạo deterministic relationships từ structured fields.
3. Gắn `source_id`, confidence, extraction method và review status.
4. Không dùng LLM extraction trong bước bắt buộc này.
5. Viết recursive CTE hoặc repository method cho traversal tối đa 2 hop.
6. Tạo endpoint graph và facts.

### UI

1. Hiển thị ingestion job status.
2. Hiển thị facts kèm nguồn.
3. Hiển thị graph dưới dạng danh sách path trước; visualization nâng cao chưa bắt buộc.

### Tests

1. Schema invalid bị reject/quarantine.
2. Import idempotent.
3. Entity không bị duplicate.
4. Edge có source.
5. Traversal không vượt 2 hop.
6. Project filter không lấy graph của project khác.

### Đầu ra

- Fixture đi xuyên suốt vào canonical tables.
- Có graph path thật từ dữ liệu crawler.
- Có ingestion report.

### Gate Ngày 4

- 20-50 records được import tự động.
- 100% edge production có provenance.
- Import cùng file lần hai không tăng số node/edge ngoài dự kiến.

---

## Ngày 5 — 19/07: knowledge chunks và hybrid retrieval mẫu

### Chunking

1. Xác định chunk theo logical unit, không chỉ cắt mỗi N ký tự.
2. Mỗi chunk giữ project, source, document type và field provenance.
3. Version hóa chunker.
4. Tạo chunks cho fixture.

### Embedding và search

1. Tạo embedding adapter; model/provider cấu hình được.
2. Index tập fixture vào pgvector.
3. Triển khai PostgreSQL full-text search.
4. Triển khai vector search.
5. Hợp nhất kết quả ban đầu bằng RRF.
6. Với query relation, bổ sung graph paths.
7. Tạo `/retrieval/search`.

### Gold queries đầu tiên

Chuẩn bị tối thiểu 15 queries:

- 5 fact đơn.
- 5 câu 1-hop.
- 3 câu 2-hop.
- 2 câu không đủ evidence.

Ví dụ:

```text
Căn 2PN thuộc tòa nào?
Tòa S2 thuộc phân khu nào?
Căn 2PN tại S2 liên quan đến tiện ích nào có nguồn xác nhận?
Dự án có chính sách thanh toán nào đang còn hiệu lực?
```

### Tests

1. Search bắt buộc filter tenant/project.
2. Kết quả có source.
3. Query không đủ evidence trả empty/warning, không bịa.
4. Graph path có thứ tự node/edge đúng.

### Đầu ra

- Hybrid retrieval mẫu chạy được.
- File gold queries và expected evidence.
- Báo cáo thủ công kết quả 15 queries.

### Gate Ngày 5

- Ít nhất 12/15 query lấy được evidence mong đợi ở top-k.
- Không có kết quả xuyên tenant/project.
- Query thiếu evidence không tạo fact giả.

---

## Ngày 6 — 20/07: tích hợp UI, deploy staging và hardening

### UI vertical slice

1. Login.
2. Dashboard project count và ingestion state.
3. Project list/detail.
4. Facts table kèm source.
5. Graph paths.
6. Search box gọi retrieval endpoint.
7. Evidence result hiển thị score/source/path.

### Deployment

1. Tạo backend container.
2. Deploy managed PostgreSQL có pgvector.
3. Chạy migration staging.
4. Deploy FastAPI.
5. Deploy Next.js.
6. Thiết lập domain/origin/environment variables.
7. Seed demo tenant/user/project.
8. Thực hiện smoke test từ trình duyệt.

### Hardening

1. Không log token/password/API key.
2. Upload/input có giới hạn kích thước.
3. API có request ID và structured error.
4. Database connection failure thể hiện ở `/ready`.
5. Có timeout/retry giới hạn cho embedding provider.
6. Có fallback fixture/cache cho demo nếu provider ngoài lỗi.

### Đầu ra

- Frontend staging URL.
- Backend staging URL.
- Demo credentials được chia sẻ an toàn, không commit.
- Runbook deploy/rollback.

### Gate Ngày 6

- Một máy khác mở URL, login và xem evidence được.
- Frontend không gọi localhost.
- Backend không dùng database local.

---

## Ngày 7 — 21/07: kiểm thử, demo và đóng tuần

### Kiểm thử cuối

1. Chạy toàn bộ unit/integration tests.
2. Chạy frontend lint/type-check/build.
3. Chạy migration trên database sạch.
4. Replay crawler fixture.
5. Smoke test staging.
6. Kiểm tra tenant isolation thủ công.
7. Kiểm tra provenance của 10 facts và 10 edges.
8. Đo latency sơ bộ retrieval p50/p95 trên 15 queries.

### Demo checkpoint

Kịch bản demo 5 phút:

1. Login bằng marketer.
2. Mở Vinhomes Grand Park.
3. Xem dữ liệu crawler vừa ingest.
4. Mở Facts và source.
5. Tìm “căn 2PN thuộc tòa/phân khu nào”.
6. Hiển thị chunk evidence và graph path.
7. Chứng minh query không đủ dữ liệu trả warning.
8. Mở ingestion report và audit log.

### Tổng kết

1. Đóng các issue hoàn thành.
2. Chuyển issue chưa xong, ghi lý do và ảnh hưởng.
3. Ghi metric thực tế.
4. Cập nhật architecture diagram nếu implementation khác thiết kế.
5. Tạo kế hoạch Tuần 2 dựa trên số liệu thật.

### Đầu ra

- `docs/checkpoints/week_01_report.md`
- `docs/runbooks/local_setup.md`
- `docs/runbooks/staging_deploy.md`
- Test report.
- Retrieval baseline report.
- Video/screenshot demo dự phòng.

### Gate đóng Tuần 1

- Tất cả kết quả bắt buộc ở Mục 1 đạt.
- Không có lỗi severity cao về auth, tenant isolation hoặc provenance.
- Staging hoạt động trên máy/mạng khác.
- Nhóm thống nhất scope Tuần 2.

---

## 8. Phân công trách nhiệm

### Lê Văn Quang

- Kiến trúc repository và application.
- PostgreSQL schema/migrations.
- FastAPI và Next.js.
- Auth/RBAC/tenant isolation.
- Property Graph storage và traversal.
- Hybrid retrieval integration.
- CI/CD và staging deployment.
- Integration tests và runbooks.

### Phạm Vũ Hải

Dù crawler đã bàn giao, Hải vẫn chịu trách nhiệm hỗ trợ contract:

- Giải thích field/source/parser behavior.
- Xác nhận fixture và data dictionary.
- Sửa crawler khi output vi phạm contract.
- Hỗ trợ audit 10 records.
- Tạo gold evidence cho retrieval queries.
- Xác nhận entity/relationship được dựng đúng với dữ liệu nguồn.

### Cả nhóm

- Khóa ontology và research protocol.
- Review ADR.
- Duyệt source/license policy.
- Chấm gold queries.
- Demo và retrospective cuối tuần.

---

## 9. Test checklist

### Data

- [ ] Fixture đúng schema.
- [ ] UTF-8 tiếng Việt không lỗi.
- [ ] Có source/hash/timestamp/parser version.
- [ ] Import idempotent.
- [ ] Invalid records được quarantine.

### Database/Graph

- [ ] Migration chạy trên database sạch.
- [ ] pgvector extension hoạt động.
- [ ] Entity unique đúng tenant/external key.
- [ ] Edge có provenance.
- [ ] Traversal giới hạn 2 hop.
- [ ] Temporal fields đã tồn tại dù chưa khai thác đầy đủ.

### Security

- [ ] Password được hash.
- [ ] Endpoint nghiệp vụ yêu cầu authentication.
- [ ] Role được kiểm tra ở backend.
- [ ] Tenant A không đọc tenant B.
- [ ] Secret không nằm trong Git/log.

### Retrieval

- [ ] Full-text search chạy.
- [ ] Vector search chạy.
- [ ] RRF/hợp nhất có version.
- [ ] Result có source.
- [ ] Query thiếu evidence trả warning/empty.

### Deployment

- [ ] Frontend staging hoạt động.
- [ ] Backend health/ready hoạt động.
- [ ] Managed database và migration hoạt động.
- [ ] Demo trên máy khác thành công.
- [ ] Có runbook và fallback.

---

## 10. Metric cần ghi ngay từ Tuần 1

- Tổng records crawler và tỷ lệ hợp lệ.
- Missing rate theo field.
- Duplicate rate.
- Số entities theo type.
- Số relationships theo type.
- Tỷ lệ edge có source.
- Ingestion duration.
- Embedding/indexing duration.
- Retrieval hit rate trên 15 gold queries.
- Retrieval p50/p95.
- API error rate trong smoke test.
- Test pass count.

Các số liệu này là baseline kỹ thuật, không phải kết quả cuối của luận văn.

---

## 11. Rủi ro riêng Tuần 1

| Rủi ro | Xử lý ngay |
|---|---|
| Crawler output không đúng contract | Adapter compatibility + quarantine; issue cho Hải, không sửa tay dataset |
| Quá nhiều loại entity/edge | Giữ ontology v1 chỉ 7 node và 7 edge |
| Auth làm mất nhiều thời gian | Chọn cơ chế chuẩn, chỉ ba role; không tự xây identity platform |
| pgvector/deploy chưa sẵn sàng | Exact search trên tập nhỏ; xác nhận extension trước khi chọn provider |
| Embedding API lỗi | Adapter + fixture embedding/cache cho staging demo |
| Graph visualization tốn thời gian | Hiển thị path/table trước, visualization nâng cao sang tuần sau |
| UI quá cầu kỳ | Chỉ làm vertical slice chức năng theo mockup |
| Thiếu provenance | Chặn edge khỏi production context nếu không có source |

---

## 12. Thứ tự ưu tiên khi thiếu thời gian

1. Data contract và ingestion đúng.
2. Database schema/migration.
3. Auth/RBAC/tenant isolation.
4. Project CRUD.
5. Canonical graph + provenance.
6. Retrieval API.
7. Staging deployment.
8. UI evidence tối thiểu.
9. UI graph đẹp và dashboard nâng cao.

Không được đánh đổi correctness, tenant isolation hoặc provenance để làm UI đẹp.

---

## 13. Definition of Done Tuần 1

Tuần 1 chỉ được đánh dấu hoàn thành khi:

- Crawler fixture được audit và import bằng pipeline.
- PostgreSQL schema và migration tái lập được.
- Property Graph ontology v1 tồn tại bằng dữ liệu thật.
- Hybrid retrieval mẫu trả chunks/path có source.
- Login/RBAC/project UI chạy trên staging.
- Tenant isolation có test.
- Demo trên máy khác thành công.
- Có test report, runbook và checkpoint report.
- Không phụ thuộc Microsoft GraphRAG, Neo4j hoặc fine-tuned model để chạy vertical slice.

