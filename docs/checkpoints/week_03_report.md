# Checkpoint Tuần 3 — Knowledge base + dataset_v1

**Ngày:** 28/07/2026 · **Branch:** `tuan-03-knowledge-base` · **Người thực hiện:** Quang (+ Claude hỗ trợ)

Artefact kèm theo: [data card dataset_v1](week_03_data_card.md) · [kết quả đánh giá retrieval](week_03_retrieval_eval.md) · [chất lượng dữ liệu sau D1–D5](week_02_data_quality.md)

## Kết quả so với gate Tuần 3 ([Plan/01 §6](../../Plan/01_KE_HOACH_TONG_THE.md))

| Hạng mục gate | Trạng thái | Bằng chứng |
|---|---|---|
| Chunking | ✅ | 3 loại chunk/tin (facts · title · description có chồng lấn), mỗi chunk mang header ngữ cảnh dự án |
| Embeddings | ✅ | **BAAI/bge-m3 chạy trên GPU (GTX 1650 Ti, CUDA)** — 9.656 chunk, 8,8 phút, VRAM đỉnh 2,3GB |
| FTS index | ✅ | PostgreSQL `tsvector` + `unaccent` (tiếng Việt bỏ dấu) + GIN index; vector dùng HNSW cosine |
| Entity resolution + alias | ✅ | Từ điển tên phường học từ URL có mã vùng → **347 → 617 dự án, 862 → 1.539 tin Tier A**; tên dự án có dấu lấy từ text |
| Split 70/15/15 theo project | ✅ | `dataset_v1`: train 69,3% · validation 14,7% · test 16,0% (đơn vị chia); chia theo dự án và cụm dedup |
| Leakage audit | ✅ | **0 cụm dedup và 0 dự án nằm ở hai split**, 100% tin được gán split |
| `dataset_v1` có data card | ✅ | [week_03_data_card.md](week_03_data_card.md) sinh tự động từ DB |
| 60–90 gold retrieval queries | ✅ | **72 query** (12 mỗi nhóm: fact · 1-hop · 2-hop · so sánh · mâu thuẫn · temporal), nhãn suy ra tất định từ DB |
| SFT draft v1 | ✅ | 1.500 mẫu nháp theo schema Plan/02 §7.1, `output` để trống chờ review (không tự sinh rồi tự train) |
| **R1 và R2 trả kết quả đúng project kèm nguồn** | ✅ | R1-vector project precision@10 = **0,850**; R2-graph = **0,686**, MRR **0,889**; mọi kết quả có `source_url` |
| Fact/source editor | ✅ | `/dataset` — hàng đợi fact `needs_review`, sửa/xác nhận có lưu vết người duyệt và giá trị máy sinh |
| Staging URL (carry-over T1) | ⏳ **chưa** | Vẫn chờ Anh chọn nền tảng cloud + cấp tài khoản |

## Kết quả đánh giá retrieval (72 gold query, top-k = 10, bge-m3)

| Cấu hình | project precision@10 | listing recall@10 | hit@10 | MRR |
|---|---:|---:|---:|---:|
| R1-fts (từ khóa) | 0,087 | 0,117 | 0,403 | 0,127 |
| **R1-vector (bge-m3)** | **0,850** | 0,855 | **0,986** | **0,921** |
| R1-hybrid (RRF không trọng số) | 0,551 | 0,743 | 0,972 | 0,817 |
| **R2-graph (≤2 hop)** | 0,686 | **0,862** | 0,917 | 0,889 |

**Đọc kết quả (đưa vào báo cáo):**

1. **Vector thắng áp đảo FTS trên tiếng Việt** (0,850 so với 0,087). FTS cấu hình `simple` + bỏ dấu không có trọng số IDF nên câu hỏi tự nhiên dài bị nhiễu bởi từ phổ biến ("căn hộ", "bán", "giá"). Đây là số liệu thật cho phần "vì sao cần embedding", không phải suy đoán.
2. **RRF không trọng số làm giảm chất lượng** so với vector đơn thuần (0,551 < 0,850) vì cho hai retriever trọng số ngang nhau trong khi một nhánh yếu hẳn. Tuần 4 phải dùng RRF có trọng số hoặc thay lexical bằng BM25 có IDF + tách từ tiếng Việt — đây chính là nội dung R3. **Đây là một negative result có ích, sẽ báo cáo trung thực** theo nguyên tắc Plan/03 §7.
3. **Graph đạt recall 0,862 và MRR 0,889 mà không dùng một phép so khớp văn bản nào.** Precision thấp hơn vector vì graph trả thêm dự án "cùng phường/quận" ở hop 2. Đúng như giả thuyết H6 — graph bổ sung khả năng trả lời quan hệ chứ không thay thế vector, và là cơ sở để R3 hợp nhất hai nguồn.

## Số liệu knowledge base

| Chỉ số | Giá trị |
|---|---:|
| Chunk index (tier A+B) | 9.656 (facts 3.218 · title 3.218 · description 3.220) |
| Đã embed | 9.656 (100%) — `BAAI/bge-m3`, 1024 chiều |
| Canonical facts | 31.167 |
| Node / cạnh graph | 1.941 / 2.653 |
| Dự án trong graph | 617 |
| Tin Tier A (gắn dự án) | 1.539 (32,1%) |
| Gold query | 72 (đang chờ soát tay) |
| Mẫu SFT nháp | 1.500 (train 1.252 · validation 248) |

Sau khi sửa lỗi gán tỉnh/thành, độ phủ `city` giảm từ 37,4% xuống **28,5%** — con số cũ bị thổi lên bởi các tin chứa chữ "cho thuê". Đây là ví dụ cho thấy vì sao mọi số liệu trong báo cáo đều phải sinh lại từ pipeline chứ không chép tay.

## Quyết định kỹ thuật trong tuần

- **Entity resolution bằng từ điển tên phường, không dùng LLM.** URL có mã vùng cho biết chắc chắn tên phường; dùng chính tập đó cắt ranh giới phường ↔ dự án cho URL không có mã vùng, rồi **bắt buộc tên dự án phải xuất hiện trong title/description** mới gán. Vừa tăng độ phủ 78% vừa giữ nguyên tắc "không tạo entity giả".
- **Embedder có hai backend.** `sentence-transformers` (bge-m3, GPU) cho mọi số liệu báo cáo; `hashing` tất định cho test/CI để pipeline chạy được trên máy không GPU. Model được ghi kèm từng chunk nên đổi model chỉ embed lại phần cần thiết.
- **Chia split bằng hash của khóa đơn vị**, không random theo thứ tự. Thêm dữ liệu mới không xáo trộn dự án cũ giữa các split — điều kiện để test set giữ nguyên qua các lần cập nhật dữ liệu.
- **Gold query sinh bằng template, không dùng LLM.** Nhãn suy ra tất định từ DB nên đo lại lúc nào cũng ra cùng số và không rò rỉ tri thức của model sinh câu hỏi vào bộ đánh giá. Tất cả đang ở trạng thái `needs_review` — Hải soát tay trước khi khóa benchmark.
- **SFT draft chỉ dựng phần input.** Không tự sinh output rồi train lại trên chính output đó; `quality_status = draft` cho tới khi có review gắn gold/silver (Tuần 5).
- **FTS dùng OR + `ts_rank_cd`** thay cho `plainto_tsquery` (vốn nối AND nên câu hỏi dài không khớp gì). Đây là baseline lexical trung thực để so sánh, không phải cấu hình production.

## Lỗi phát hiện và đã sửa trong tuần

| Lỗi | Phát hiện qua | Cách sửa |
|---|---|---|
| `hue` khớp bên trong "cho **thuê**" → hàng loạt tin bị gán tỉnh Thừa Thiên Huế | Nhìn kết quả tìm kiếm trên UI | Khớp tỉnh/thành theo ranh giới từ; thêm test hồi quy |
| R2-graph trả dự án khác cùng phường thay vì dự án được hỏi | Debug gold query | Xếp hạng theo độ sâu đường đi (dự án nhận diện trực tiếp trước), giới hạn 10 dự án/câu hỏi |
| FTS trả 0 kết quả với câu hỏi tự nhiên | Test tay trên dữ liệu thật | Chuyển từ AND (`plainto_tsquery`) sang OR + `ts_rank_cd` |
| Migration autogenerate xóa mất 2 index tự viết (GIN + HNSW) | Đọc file migration trước khi apply | Khai báo index trong model để autogenerate biết; migration tạo lại index |
| Lần tìm kiếm đầu tiên chờ ~80s vì tải model | Chụp màn hình E2E | Nạp model ở nền lúc khởi động API (`lifespan`) |

## Cách chạy local

```powershell
docker compose up -d
cd backend
.\.venv\Scripts\alembic.exe upgrade head              # tới a7aad62eeea9
.\.venv\Scripts\python.exe -m app.pipeline_cli --rebuild    # D1–D5
.\.venv\Scripts\python.exe -m app.index_cli                 # chunk + FTS + embed bge-m3 (GPU)
.\.venv\Scripts\python.exe -m app.dataset_cli --build --eval # split + gold query + SFT + data card + đánh giá
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
cd ..\frontend; npm run dev                                  # /search và /dataset
```

Chạy không GPU: thêm `--backend hashing` cho `index_cli`/`dataset_cli` (chỉ để pipeline chạy được, **không dùng cho số liệu báo cáo**).

## Kiểm chứng đã chạy

- **80/80 test pass** — bổ sung Tuần 3: chunking 6, dataset/split/gold/SFT 6, index+retrieval 7, API 5, hồi quy re-parse 5.
- **Trên PostgreSQL thật:** index 9.656 chunk idempotent (chạy lại `chunk_moi=0`, `embedded=0`); leakage audit `passed=True`.
- **E2E trình duyệt:** đăng nhập → `/search` chạy 4 cấu hình R1/R2 trên 9.656 chunk, mỗi kết quả có nhãn retriever, điểm, dự án, tier và link nguồn.

## Hạn chế đã biết

| Hạn chế | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| RRF chưa có trọng số → hybrid kém hơn vector | R3 chưa đạt kỳ vọng | Tuần 4: RRF có trọng số + BM25/tách từ tiếng Việt |
| Gold query do template sinh, chưa soát tay | Nhãn có thể lệch ở nhóm "compare"/"conflict" | Hải soát 72 câu trước khi khóa benchmark |
| SFT draft chưa có output | Chưa train được | Tuần 5: sinh có kiểm soát + review gold/silver |
| GPU 4GB không đủ QLoRA 7–8B | Tuần 5 không train được trên máy này | Thuê GPU giờ (≥12GB) hoặc chọn backbone nhỏ hơn trong pilot |
| Quận/huyện mới phủ ~19% | Câu hỏi theo quận còn yếu | Dictionary phường → quận → tỉnh (Tuần 4) |

## Carry-over sang Tuần 4

| Việc | Owner | Ghi chú |
|---|---|---|
| Deploy staging | Quang | Vẫn chờ Anh chọn nền tảng + cấp tài khoản |
| R3 = RRF có trọng số (R1 + R2) + query router | Quang | Dùng lại `reciprocal_rank_fusion` đã có |
| Cải thiện lexical: BM25 + tách từ tiếng Việt | Quang | Mục tiêu kéo R1-fts lên mức có ý nghĩa |
| Soát tay 72 gold query, chốt relevance label | Hải | Bỏ `needs_review` sau khi soát |
| Content Studio 4 kênh + Evidence panel | Quang | Dùng chunk + facts đã có provenance |
| Prompt baseline + chạy A/B | Hải | Theo Plan/03 §2 |
