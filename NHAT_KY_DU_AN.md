# Nhật ký và bàn giao trạng thái ĐATN

> **File bắt đầu duy nhất cho phiên làm việc mới.** Khi mở lại dự án, hãy đọc file này trước. Chỉ mở các tài liệu hoặc mã nguồn được dẫn ở đây khi nhiệm vụ hiện tại thực sự cần chi tiết hơn.

**Dự án:** AI tạo và tối ưu nội dung marketing BĐS đa kênh  
**Cập nhật gần nhất:** 20/07/2026  
**Trạng thái tổng thể:** đã hoàn thành kế hoạch tổng thể và kế hoạch chi tiết Tuần 1-8; chưa có bằng chứng triển khai mã nguồn trong workspace hiện tại.

---

## 1. Mục tiêu đã chốt

Xây dựng web app online cho phép nhập dữ liệu dự án BĐS, truy xuất thông tin có nguồn và tạo nội dung marketing cho nhiều kênh. Sản phẩm cuối phải có:

- URL truy cập online, đăng nhập, RBAC và quản lý user/project.
- Bốn loại nội dung: mô tả BĐS, Facebook, nurturing email và SEO landing page.
- Evidence cho từng claim, review, version history và export.
- Dashboard so sánh các cấu hình thí nghiệm.
- Luồng có thể giải thích và đánh giá tái lập được.

## 2. Quyết định kiến trúc không được tự ý thay đổi

- Lõi production: PostgreSQL Property Knowledge Graph + PostgreSQL FTS + pgvector hybrid RAG.
- Property Graph được lưu bằng bảng quan hệ trong PostgreSQL; chưa cần Neo4j.
- Graph traversal production giới hạn tối đa 2 hop.
- Mỗi fact, relationship và claim phải có provenance; dữ liệu nhạy cảm theo thời gian phải có `valid_from`/`valid_to`.
- Microsoft GraphRAG chỉ là lớp nghiên cứu Local/Global discovery trên corpus con, không nằm trên critical path production. Có stop/continue gate ở Tuần 5; negative result vẫn hợp lệ.
- Vision dùng VLM/API để trích xuất tập visual facts hẹp, có confidence và human confirmation; không fine-tune vision trong critical path.
- Fine-tuning dùng QLoRA cho text generator 7B-8B; kiến thức thực tế vẫn nằm trong retrieval, không nhồi vào adapter.
- Ma trận generation bắt buộc: A prompt-only, B RAG, C fine-tuned, D RAG + fine-tuned.
- Ma trận retrieval bắt buộc: R1 vector/FTS, R2 graph-only, R3 graph + vector. R4 Microsoft GraphRAG chỉ chạy nếu qua gate.
- Chia dữ liệu theo project, deduplicate trước split, khóa frozen test set và version hóa dataset/model/prompt/graph snapshot.

## 3. Những việc đã hoàn thành

### Phân tích và thiết kế

- [x] Chốt đề tài, phạm vi sản phẩm và hướng nghiên cứu.
- [x] Chốt kiến trúc production và vai trò nghiên cứu của Microsoft GraphRAG.
- [x] Chốt flow crawler → canonical facts/graph → hybrid retrieval → generation → evidence → human review.
- [x] Chốt ma trận A-D và R1-R4, metric kỹ thuật và human evaluation.
- [x] Chốt phạm vi 8 tuần, thứ tự cắt scope và Definition of Done.
- [x] Thiết kế workflow tổng thể dạng SVG.
- [x] Tạo HTML mockup tổng quan UI sản phẩm cuối.
- [x] Viết kế hoạch triển khai tổng thể 8 tuần.
- [x] Viết kế hoạch chi tiết Tuần 1 theo ngày, đầu ra, gate, test và owner.
- [x] Viết kế hoạch chi tiết Tuần 2 theo production ingestion, staging, carry-over, test và Definition of Done.
- [x] Viết kế hoạch chi tiết Tuần 3 theo knowledge base, dataset v1, entity resolution, leakage audit và gold queries R1-R3.
- [x] Viết kế hoạch chi tiết Tuần 4 theo prompt-only/RAG baseline, query router, R3 context assembler, Content Studio, evidence UI và baseline metrics.
- [x] Viết kế hoạch chi tiết Tuần 5 theo QLoRA, reviewer/version/export flow, cấu hình C và Microsoft GraphRAG stop/continue gate.
- [x] Viết kế hoạch chi tiết Tuần 6 theo tích hợp D, đánh giá A-D/R1-R4, comparison UI, cost/latency và blind human evaluation.
- [x] Viết kế hoạch chi tiết Tuần 7 theo vision extraction, visual fact confirmation, critic panel và RBAC/UX hardening.
- [x] Viết kế hoạch chi tiết Tuần 8 theo release candidate, reproducibility, E2E/security, production deploy, demo và backup.

### Artefact hiện có

| File | Vai trò |
|---|---|
| `Plan/KE_HOACH_TRIEN_KHAI_DATN.md` | Kế hoạch tổng thể, kiến trúc, nghiên cứu và lộ trình 8 tuần |
| `Plan/KE_HOACH_CHI_TIET_TUAN_1.md` | Kế hoạch thực thi chi tiết Tuần 1 |
| `Plan/KE_HOACH_CHI_TIET_TUAN_2.md` | Kế hoạch production ingestion và MVP staging Tuần 2 |
| `Plan/KE_HOACH_CHI_TIET_TUAN_3.md` | Kế hoạch knowledge base, dataset v1 và retrieval seed Tuần 3 |
| `Plan/KE_HOACH_CHI_TIET_TUAN_4.md` | Kế hoạch prompt-only/RAG baseline, Content Studio và evidence UI Tuần 4 |
| `Plan/KE_HOACH_CHI_TIET_TUAN_5.md` | Kế hoạch QLoRA, reviewer/version/export và GraphRAG gate Tuần 5 |
| `Plan/KE_HOACH_CHI_TIET_TUAN_6.md` | Kế hoạch tích hợp D, đánh giá A-D/R1-R4 và human evaluation Tuần 6 |
| `Plan/KE_HOACH_CHI_TIET_TUAN_7.md` | Kế hoạch vision, critic và hardening Tuần 7 |
| `Plan/KE_HOACH_CHI_TIET_TUAN_8.md` | Kế hoạch release candidate, reproducibility và production deploy Tuần 8 |
| `Plan/deep-research-report.md` | Tài liệu nghiên cứu nền |
| `WORKFLOW_TONG_THE_DATN.svg` | Sơ đồ workflow tổng thể |
| `UI_TONG_QUAN_SAN_PHAM.html` | Mockup UI đích của sản phẩm |

## 4. Những việc chưa hoàn thành hoặc chưa được xác minh

### Kế hoạch

- [x] Viết kế hoạch chi tiết riêng cho Tuần 2.
- [x] Viết kế hoạch chi tiết riêng cho Tuần 3.
- [x] Viết kế hoạch chi tiết riêng cho Tuần 4.
- [x] Viết kế hoạch chi tiết riêng cho Tuần 5.
- [x] Viết kế hoạch chi tiết riêng cho Tuần 6.
- [x] Viết kế hoạch chi tiết riêng cho Tuần 7.
- [x] Viết kế hoạch chi tiết riêng cho Tuần 8.
- [x] Liên kết các kế hoạch Tuần 2-8 từ kế hoạch tổng thể sau khi tạo.

### Triển khai Tuần 1

Chưa đánh dấu bất kỳ mục nào dưới đây là hoàn thành nếu chưa có file, test output hoặc URL chứng minh:

- [ ] Audit gói crawler Hải bàn giao và khóa `crawler_contract_v1`.
- [ ] Khởi tạo monorepo FastAPI + Next.js.
- [ ] PostgreSQL + pgvector, migrations và seed.
- [ ] Auth, RBAC, tenant isolation và project CRUD.
- [ ] Ingestion adapter idempotent và quarantine dữ liệu lỗi.
- [ ] Canonical entities, deterministic graph edges và traversal 1-2 hop.
- [ ] Knowledge chunks, embedding, FTS/vector search và RRF.
- [ ] UI vertical slice hiển thị facts, source và graph path.
- [ ] CI, automated tests và staging deployment.
- [ ] Báo cáo checkpoint Tuần 1 với metric thực tế.

## 5. Phân công đã chốt

### Lê Văn Quang

- Tích hợp toàn hệ thống, database, backend, frontend và deployment.
- Auth/RBAC/tenant isolation.
- Property Graph storage/traversal và hybrid retrieval.
- CI/CD, tests, experiment dashboard và runbooks.

### Phạm Vũ Hải

- Crawler và data contract.
- Giải thích source/field/parser, sửa output vi phạm contract.
- Hỗ trợ audit nguồn, gold evidence, SFT/QLoRA, model evaluation và vision data.

## 6. Việc cần làm tiếp theo

### Nếu bắt đầu triển khai thực tế

1. Trước hết kiểm tra checkpoint Tuần 1 thực tế; không mặc định kế hoạch đã được thực hiện.
2. Blocker Tuần 1 phải được carry-over vào Tuần 2, có owner và deadline.
3. Xác định Git repo/source app thật hoặc khởi tạo monorepo theo Tuần 1.
4. Khi triển khai, mỗi tuần bắt đầu bằng kiểm tra checkpoint tuần trước và kết thúc bằng staging/test/demo thật.
5. Sau mỗi buổi, cập nhật file log này bằng bằng chứng thật; không đánh dấu hoàn thành dựa trên kế hoạch.

### Hướng nội dung Tuần 2-8

- **Tuần 2:** production ingestion, canonical data/assets/jobs, idempotency, provenance, tenant isolation và MVP staging.
- **Tuần 3:** cleaned dataset/SFT v1, fact/source editor, entity resolution, graph quality, project split, leakage audit và gold queries R1-R3.
- **Tuần 4:** prompt-only/RAG baseline, query router, R3 context assembler, evidence UI, retrieval metrics và web flow A/B.
- **Tuần 5:** QLoRA, reviewer/version/export; Microsoft GraphRAG corpus con và stop/continue gate.
- **Tuần 6:** tích hợp D, chạy frozen A-D và R1-R4 đủ điều kiện, comparison UI, cost/latency và blind human evaluation.
- **Tuần 7:** vision extraction/image alignment, visual fact confirmation, critic panel và RBAC/UX hardening; critic-refiner chỉ làm sau khi A-D hoàn tất.
- **Tuần 8:** model/data cards, reproducibility, E2E/security, production deploy, demo, runbook và backup.

## 7. Nguyên tắc giữ phạm vi 8 tuần

Nếu trễ, cắt theo thứ tự: DPO → online A/B test → video/multilingual → deep graph/Neo4j → advanced visualization → production Microsoft GraphRAG → critic-refiner mở rộng.

Không được cắt: deployment online, auth/RBAC, user/project management, A-D, QLoRA, PostgreSQL Property Knowledge Graph + hybrid vector RAG, R1-R3, provenance/evidence, review/version và frozen evaluation.

## 8. Quy tắc cập nhật file log sau mỗi buổi

Trước khi kết thúc mỗi phiên làm việc, phải cập nhật file này:

1. Đổi `Cập nhật gần nhất` và `Trạng thái tổng thể`.
2. Chuyển mục hoàn thành từ `[ ]` sang `[x]` chỉ khi có bằng chứng.
3. Ghi file/URL/test/commit dùng làm bằng chứng vào bảng bên dưới.
4. Ghi rõ việc đang dở, blocker, owner và bước chạy tiếp theo.
5. Nếu thay đổi kiến trúc hoặc phạm vi, ghi quyết định và lý do; không xóa lịch sử quan trọng.
6. Giữ file ngắn, ưu tiên trạng thái hiện tại; chi tiết dài đặt trong tài liệu khác và chỉ dẫn link/path tại đây.

## 9. Bằng chứng thực thi gần nhất

| Ngày | Hạng mục | Bằng chứng | Kết quả |
|---|---|---|---|
| 17/07/2026 | Kiểm tra workspace | Chỉ thấy `Plan/`, `docs/`, SVG và HTML mockup; chưa thấy source app | Chưa thể xác nhận triển khai Tuần 1 |
| 17/07/2026 | Kiểm tra Git | `git status` báo thư mục hiện tại không phải Git repository hợp lệ | Cần khởi tạo/xác định đúng repo khi bắt đầu code |
| 17/07/2026 | Lập kế hoạch Tuần 2 | `Plan/KE_HOACH_CHI_TIET_TUAN_2.md` và link trong kế hoạch tổng thể | Hoàn thành tài liệu; chưa phải bằng chứng triển khai |
| 20/07/2026 | Lập kế hoạch Tuần 3 | `Plan/KE_HOACH_CHI_TIET_TUAN_3.md` và link trong kế hoạch tổng thể | Hoàn thành tài liệu; chưa phải bằng chứng triển khai |
| 20/07/2026 | Lập kế hoạch Tuần 4 | `Plan/KE_HOACH_CHI_TIET_TUAN_4.md` và link trong kế hoạch tổng thể | Hoàn thành tài liệu; chưa phải bằng chứng triển khai |
| 20/07/2026 | Lập kế hoạch Tuần 5 | `Plan/KE_HOACH_CHI_TIET_TUAN_5.md` và link trong kế hoạch tổng thể | Hoàn thành tài liệu; chưa phải bằng chứng triển khai |
| 20/07/2026 | Lập kế hoạch Tuần 6 | `Plan/KE_HOACH_CHI_TIET_TUAN_6.md` và link trong kế hoạch tổng thể | Hoàn thành tài liệu; chưa phải bằng chứng triển khai |
| 20/07/2026 | Lập kế hoạch Tuần 7 | `Plan/KE_HOACH_CHI_TIET_TUAN_7.md` và link trong kế hoạch tổng thể | Hoàn thành tài liệu; chưa phải bằng chứng triển khai |
| 20/07/2026 | Lập kế hoạch Tuần 8 | `Plan/KE_HOACH_CHI_TIET_TUAN_8.md` và link trong kế hoạch tổng thể | Hoàn thành tài liệu; chưa phải bằng chứng triển khai |

## 10. Blocker và câu hỏi mở

| Mức độ | Vấn đề | Owner | Hành động tiếp theo |
|---|---|---|---|
| Cao | Chưa có/xác minh gói crawler bàn giao trong workspace | Hải + Quang | Đặt fixture, contract và tài liệu crawler vào đúng cấu trúc rồi audit |
| Cao | Chưa có source app/repo triển khai | Quang | Xác định repo thật hoặc khởi tạo monorepo theo kế hoạch Tuần 1 |
| Trung bình | Chưa có checkpoint thực tế Tuần 1 | Cả nhóm | Chạy checklist Tuần 1 và ghi metric/bằng chứng |
| Trung bình | Toàn bộ kế hoạch Tuần 1-8 đã viết nhưng chưa có bằng chứng triển khai | Quang | Bắt đầu bằng xác định repo/source app thật và chạy checkpoint Tuần 1 |

---

**Lệnh nhắc cho Codex ở phiên mới:** “Đọc `NHAT_KY_DU_AN.md`, báo lại trạng thái hiện tại trong 5-10 dòng, rồi tiếp tục đúng mục ‘Việc cần làm tiếp theo’. Không quét toàn bộ dự án trừ khi task yêu cầu hoặc log có dấu hiệu lỗi thời.”

## Current State & Hand-off

- Vừa hoàn thành chuỗi kế hoạch chi tiết Tuần 1-8; mới nhất là `Plan/KE_HOACH_CHI_TIET_TUAN_6.md`, `Plan/KE_HOACH_CHI_TIET_TUAN_7.md`, `Plan/KE_HOACH_CHI_TIET_TUAN_8.md`.
- Kế hoạch tổng thể `Plan/KE_HOACH_TRIEN_KHAI_DATN.md` đã link đủ Tuần 2-8; `NHAT_KY_DU_AN.md` ghi rõ đây là tài liệu kế hoạch, chưa phải bằng chứng triển khai.
- Workspace hiện vẫn chỉ có tài liệu/kế hoạch/mockup; chưa có bằng chứng triển khai source app, checkpoint Tuần 1 hoặc Git repo hợp lệ.
- File quan trọng đang thao tác: `NHAT_KY_DU_AN.md`, `Plan/KE_HOACH_TRIEN_KHAI_DATN.md`, `Plan/KE_HOACH_CHI_TIET_TUAN_1.md` đến `Plan/KE_HOACH_CHI_TIET_TUAN_8.md`.
- Quy ước cần giữ: mỗi tuần là một file riêng trong `Plan/`, tiếng Việt, có đầu vào, demo cuối tuần, scope, schema/API, kế hoạch theo ngày, owner, gate, test, metrics, risk, cut scope và Definition of Done.
- Việc đầu tiên phiên tiếp theo: xác định Git repo/source app thật hoặc khởi tạo monorepo theo Tuần 1, rồi chạy checkpoint Tuần 1 bằng bằng chứng thật trước khi đánh dấu bất kỳ mục triển khai nào hoàn thành.
