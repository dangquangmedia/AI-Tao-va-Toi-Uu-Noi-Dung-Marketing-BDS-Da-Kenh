# Nhật ký và bàn giao trạng thái ĐATN

> **File bắt đầu duy nhất cho phiên làm việc mới.** Khi mở lại dự án, hãy đọc file này trước. Chỉ mở các tài liệu hoặc mã nguồn được dẫn ở đây khi nhiệm vụ hiện tại thực sự cần chi tiết hơn.

**Dự án:** AI tạo và tối ưu nội dung marketing BĐS đa kênh
**Cập nhật gần nhất:** 27/07/2026 (tối)
**Trạng thái tổng thể:** Tuần 1 gần hoàn tất trên branch `tuan-01-nen-tang` — monorepo backend/frontend chạy local end-to-end, 13/13 tests pass, 200 tin DataBDS đã vào raw zone idempotent; còn thiếu duy nhất staging URL (chờ tài khoản cloud).

---

## 1. Bộ tài liệu hiện hành (sau tái cấu trúc 27/07)

| File | Vai trò |
|---|---|
| `Plan/01_KE_HOACH_TONG_THE.md` | Định vị học thuật, RQ, kiến trúc, ma trận A–D + R1–R3, lộ trình 8 tuần, phân công, rủi ro, DoD |
| `Plan/02_KE_HOACH_DU_LIEU.md` | Hiện trạng DataBDS (số liệu đo thật), pipeline làm sạch D1–D5, phân bổ tier, split chống leakage, SFT dataset, benchmark, license/đạo đức |
| `Plan/03_KE_HOACH_THUC_NGHIEM.md` | Giả thuyết, protocol A–D/R1–R3, lựa chọn model, metrics, human eval, ngưỡng thành công, gói tái lập |
| `Plan/04_DE_CUONG_TRINH_BAY.md` | Storyline slide, mapping chương báo cáo, kịch bản demo, ngân hàng 20 câu hỏi hội đồng |
| `Plan/WORKFLOW_TONG_THE.svg` | Sơ đồ workflow tổng thể (bản mới, 4 tầng) |
| `UI_TONG_QUAN_SAN_PHAM.html` | Mockup UI sản phẩm đích "Căn Cứ" — 5 màn hình (bản thiết kế lại 27/07) |
| `DataBDS/` | Kho dữ liệu crawl thật (raw zone — bất biến, không sửa tay) |
| `docs/` | Giấy tờ chính thức: đề cương DCDATN, đơn, biểu mẫu, phụ lục trình bày |

**Đã xóa 27/07 (còn trong git history nếu cần):** kế hoạch tổng thể cũ, 8 kế hoạch tuần chi tiết, deep-research-report, FLOWCHART csv, workflow SVG cũ, UI mockup cũ.

## 2. Quyết định kiến trúc không được tự ý thay đổi

- Lõi production: PostgreSQL Property Knowledge Graph + PostgreSQL FTS + pgvector hybrid RAG; một hệ lưu trữ duy nhất, không Neo4j.
- Graph traversal production giới hạn tối đa 2 hop; ontology cố định.
- Mỗi fact, relationship và claim phải có provenance; dữ liệu nhạy cảm theo thời gian có `valid_from`/`valid_to`.
- Facts sống trong retrieval; style/persona/format học bằng QLoRA (7B–8B, ứng viên Qwen3-8B, chốt bằng pilot).
- Vision dùng VLM/API trích xuất visual facts hẹp có confidence + human confirmation; không fine-tune vision.
- Ma trận bắt buộc: A/B/C/D (generation) và R1/R2/R3 (retrieval).
- **Đã cắt (quyết định 27/07):** Microsoft GraphRAG R4 — không nằm trong đề cương, tốn chi phí index, không phục vụ RQ chính. RQ7 cũ bị loại.
- Chia dữ liệu theo project, dedup trước split, frozen test set, version hóa dataset/model/prompt/graph snapshot.
- Lịch: 8 tuần **đánh số tương đối** (không gắn ngày cứng); mốc cứng duy nhất: nộp báo cáo 24/09/2026, bảo vệ 10/10/2026.

## 3. Trạng thái dữ liệu DataBDS (đo thật ngày 27/07)

- 4.795 tin bán từ batdongsan.com.vn (crawl 17–25/07); 37.349/37.351 ảnh đã tải về local; provenance đầy đủ (canonical_url + content_hash).
- Trường sạch: title, description (100%), area_m2 (99,6%), bedrooms (66,9%).
- **Trường hỏng do parser dính boilerplate:** project_name ~100%, legal_status ~100%, price chỉ parse được 31,6%.
- Khôi phục được 816 project slug từ URL (phủ 1.919 tin) → nền tảng cho graph + split theo project.
- Việc còn nợ: pipeline re-parse D1–D5 theo `Plan/02_KE_HOACH_DU_LIEU.md` §4.

## 4. Phân công đã chốt

- **Lê Văn Quang:** hệ thống + tích hợp — backend/frontend, database, auth/RBAC/tenant, graph storage/traversal, hybrid retrieval, CI/CD, dashboard, deployment.
- **Phạm Vũ Hải:** dữ liệu + mô hình — crawler/contract, làm sạch, SFT dataset, QLoRA, evaluation, vision data.

## 5. Việc cần làm tiếp theo (đầu Tuần 2)

1. **Quang chọn nền tảng cloud + cấp tài khoản** → deploy staging (carry-over duy nhất của Tuần 1).
2. Import toàn bộ 4.795 tin (hiện 200 tin demo): `python -m app.ingest_cli` không limit.
3. Hải bắt đầu re-parse D1 (giá/project/pháp lý từ title+description+URL) theo `Plan/02` §4; khóa `crawler_contract_v1.json`.
4. Tuần 2 theo `Plan/01` §6: canonical facts + provenance + graph entities/edges deterministic.
5. Sau mỗi buổi: cập nhật file log này bằng bằng chứng thật (file/test/URL/commit).

Chi tiết Tuần 1 + cách chạy local: `docs/checkpoints/week_01_report.md`.

## 6. Nguyên tắc giữ phạm vi

Nếu trễ, cắt theo thứ tự: DPO → ablation D+V+R → video/đa ngôn ngữ → reranker/agent → graph visualization nâng cao → ablation D+V.

**Không được cắt:** deploy online, auth/RBAC, user/project management, A–D, QLoRA, Property Knowledge Graph + hybrid RAG (R1–R3), provenance/evidence, review/version/export, frozen evaluation.

## 7. Quy tắc cập nhật file log sau mỗi buổi

1. Đổi `Cập nhật gần nhất` và `Trạng thái tổng thể`.
2. Chỉ đánh dấu hoàn thành khi có bằng chứng (file/URL/test/commit) ghi vào bảng mục 8.
3. Ghi rõ việc đang dở, blocker, owner và bước chạy tiếp theo.
4. Thay đổi kiến trúc/phạm vi phải ghi quyết định + lý do; không xóa lịch sử quan trọng.
5. Giữ file ngắn; chi tiết dài đặt trong `Plan/01–04` và chỉ dẫn link tại đây.

## 8. Bằng chứng thực thi gần nhất

| Ngày | Hạng mục | Bằng chứng | Kết quả |
|---|---|---|---|
| 25/07/2026 | Hải bàn giao dữ liệu crawl | `DataBDS/listings.jsonl` (4.795 tin), 2 CSV source/media, 37.349 ảnh local | Có dữ liệu thật; chất lượng parse có vấn đề (mục 3) |
| 27/07/2026 | Phân tích chất lượng DataBDS | Script Python đo trên dữ liệu thật; số liệu ghi trong `Plan/02` §1 | Xác định trường hỏng + chiến lược re-parse |
| 27/07/2026 | Tái cấu trúc bộ kế hoạch | `Plan/01–04`, `Plan/WORKFLOW_TONG_THE.svg`, `UI_TONG_QUAN_SAN_PHAM.html` mới; xóa 13 file cũ | Hoàn thành tài liệu; chưa phải bằng chứng triển khai code |

## 9. Blocker và câu hỏi mở

| Mức độ | Vấn đề | Owner | Hành động tiếp theo |
|---|---|---|---|
| Cao | Chưa có source app/repo triển khai | Quang | Khởi tạo monorepo theo Tuần 1 (`Plan/01` §6) |
| Cao | Dữ liệu DataBDS cần re-parse trước khi dùng | Hải | Chạy D1–D5 theo `Plan/02` §4, có báo cáo tỷ lệ khôi phục |
| Trung bình | Chưa chốt GPU/budget cho QLoRA | Hải | Kiểm tra trước Tuần 5; pilot model nhỏ sớm |
| Trung bình | Chưa chốt danh sách human rater | Cả nhóm | Chốt từ Tuần 3 theo `Plan/03` §5 |

---

**Lệnh nhắc cho phiên mới:** "Đọc `NHAT_KY_DU_AN.md`, báo lại trạng thái hiện tại trong 5–10 dòng, rồi tiếp tục đúng mục 'Việc cần làm tiếp theo'. Không quét toàn bộ dự án trừ khi task yêu cầu hoặc log có dấu hiệu lỗi thời."

## Current State & Hand-off

- 27/07/2026: hoàn tất tổng hợp bộ kế hoạch mới 4 file + workflow SVG + UI mockup "Căn Cứ"; xóa 13 file kế hoạch/mockup cũ (khôi phục được qua git).
- Toàn bộ kế hoạch đã bám số liệu DataBDS thật; quyết định mới: bỏ GraphRAG R4, lịch 8 tuần tương đối.
- Workspace: `Plan/01–04` + SVG, `UI_TONG_QUAN_SAN_PHAM.html`, `NHAT_KY_DU_AN.md`, `DataBDS/`, `docs/`.
- Chưa có code — việc đầu tiên phiên tới: bắt đầu Tuần 1 (monorepo + ingestion DataBDS) và chỉ đánh dấu hoàn thành bằng bằng chứng thật.
