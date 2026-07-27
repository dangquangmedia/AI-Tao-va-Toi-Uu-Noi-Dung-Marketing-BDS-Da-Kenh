# Checkpoint Tuần 2 — Làm sạch + canonical facts + Property Knowledge Graph

**Ngày:** 27/07/2026 · **Branch:** `tuan-02-lam-sach-graph` · **Người thực hiện:** Quang (+ Claude hỗ trợ)

Số liệu chất lượng dữ liệu chi tiết (sinh tự động từ DB): [week_02_data_quality.md](week_02_data_quality.md).

## Kết quả so với gate Tuần 2 ([Plan/01 §6](../../Plan/01_KE_HOACH_TONG_THE.md))

| Hạng mục gate | Trạng thái | Bằng chứng |
|---|---|---|
| Pipeline D1 re-parse | ✅ | `app/services/reparse.py` — giá/dự án/pháp lý/tiện ích/địa danh từ title+description+URL |
| D2 chuẩn hóa | ✅ | NFC + gỡ HTML entity + bóc rác Sentry/JS + mask số điện thoại (PII) |
| D3 dedup | ✅ | SimHash 64-bit + union-find, ngưỡng 6 bit đo trên dữ liệu thật → **4.750 cụm, 44 tin trùng** |
| D4 canonical facts + provenance | ✅ | **30.820 fact**, 100% có `source_url` + `content_hash` + trích đoạn + `valid_from/valid_to` |
| D5 graph entities/edges tất định | ✅ | **1.102 node / 1.535 cạnh** (Project 347 · UnitType 542 · Ward 129 · District 31 · Building 24 · City 16 · Amenity 13) |
| **Chạy lại cùng batch không sinh duplicate** | ✅ | Lần 2 trên 4.795 tin: `inserted=0 unchanged=4794`, facts/node/cạnh **+0**, cluster id không đổi |
| **Query path Project → Building → UnitType bằng dữ liệu thật** | ✅ | `GET /api/graph/projects/sunshine-sky-city/paths` → `Sunshine Sky City → Tòa V8 → apartment-2pn` (PART_OF + HAS_UNIT_TYPE) kèm URL nguồn |
| Báo cáo data quality | ✅ | [week_02_data_quality.md](week_02_data_quality.md) sinh bằng `pipeline_cli --report`, không nhập tay |
| Quarantine UI | ✅ | `/data` — bảng quarantine + mã lỗi + link tin gốc |
| Ingestion jobs UI | ✅ | `/data` — lịch sử job kèm cột Thêm/Giữ nguyên/Cập nhật để nhìn thấy tính idempotent |
| Import toàn bộ DataBDS (carry-over T1) | ✅ | 4.795/4.795 tin trong raw zone (`inserted=4595 unchanged=200` ở lần import bù) |
| Staging URL (carry-over T1) | ⏳ **chưa** | Vẫn chờ Anh chọn nền tảng cloud + cấp tài khoản |

## Số liệu chính trên 4.795 tin thật

| Chỉ số | Trước (parser crawler) | Sau D1–D5 |
|---|---:|---:|
| Tin qua contract | — | **4.794 / 4.795** (1 quarantine) |
| Giá tổng khôi phục được | 31,6% | **52,5%** |
| Dự án nhận diện được | ~0% (trường hỏng) | **862 tin / 347 dự án** |
| Phường/xã | không có | **99,9%** |
| Pháp lý | ~0% (trường hỏng) | 28,8% |
| Tiện ích | không có | 33,8% |

Phân tier (Plan/02 §5): **A = 862** · B = 1.822 · C = 2.110.

## Quyết định kỹ thuật trong tuần

- **Ưu tiên độ chính xác hơn độ phủ ở entity dự án.** Slug dự án chỉ lấy khi URL có mã vùng dạng số (`...-phuong-tan-phong-9-grand-view`). URL không có mã vùng (`...-phuong-nhan-chinh-the-diamond-residence`) bị bỏ qua thay vì đoán ranh giới tên phường → 347 dự án chắc chắn, không có entity giả. Độ phủ sẽ nâng ở Tuần 3 bằng alias/dictionary (đúng theo phân công "entity resolution + alias" của Tuần 3).
- **Không suy diễn giá.** Tin rao nhiều mức giá (bán nhiều căn) → để trống + flag `price_ambiguous`. Số tiền đứng cạnh "vốn tự có", "chiết khấu", "tiền cọc" bị loại (siết ngữ cảnh làm giảm 48 giá sai, từ 53,5% xuống 52,5% độ phủ nhưng sạch hơn).
- **Ward là mốc địa lý tối thiểu của contract.** Quận/thành phố chỉ suy được từ text (18,9%/37,4%), nhưng phường/xã có trong URL của 100% tin → dùng làm điều kiện tối thiểu, nhờ đó chỉ 1 tin bị quarantine thay vì ~50%.
- **Graph dựng lại toàn bộ mỗi lần chạy** rồi so khớp thêm/xóa, thay vì cập nhật gia tăng. Đơn giản hơn, và bảo đảm graph luôn đúng bằng dữ liệu clean hiện tại (idempotent theo định nghĩa).
- **Traversal ≤2 hop bằng recursive CTE** trên `graph_edges`, chạy cùng một câu SQL trên PostgreSQL và SQLite → test được không cần Docker.
- **`--rebuild`**: khi luật parser đổi thì xóa dữ liệu dẫn xuất và dựng lại từ raw, không backfill — bảo đảm dữ liệu luôn khớp `PARSER_VERSION` đang khai báo.

## Cách chạy local

```powershell
docker compose up -d
cd backend
.\.venv\Scripts\alembic.exe upgrade head            # migration 8032b6027123
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m app.ingest_cli        # 4.795 tin vào raw zone
.\.venv\Scripts\python.exe -m app.pipeline_cli --report ..\docs\checkpoints\week_02_data_quality.md
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
cd ..\frontend; npm run dev                          # /data và /graph
```

## Kiểm chứng đã chạy

- **56/56 test pass** — re-parse 23, dedup 4, pipeline 6, graph 5, API Tuần 2 5, cộng 13 test Tuần 1.
- **E2E trên Postgres thật:** data-quality (clean 4.794 · facts 30.820 · node 1.102 · cạnh 1.535), reviewer chạy pipeline → `403`, tenant khác → `list = []`, `clean = 0`, xem tin của tenant khác → `404`.
- **E2E trình duyệt:** đăng nhập → `/data` hiển thị đúng số liệu và 2 lần chạy pipeline (lần 2 Thêm = 0); `/graph` hiển thị đường đi `Sun Urban City → Tòa P7 → apartment` kèm nguồn và nhãn hết hiệu lực.

## Hạn chế đã biết (ghi để trả lời hội đồng)

| Hạn chế | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| Mã tòa/block chỉ nhận được 26 tin (0,5%) | Đường 2 hop qua Building còn thưa (19 dự án) | Luật chặt "tòa/block/tháp + mã ký hiệu"; Tuần 3 bổ sung alias, Tuần 7 dùng vision/mặt bằng |
| 347 dự án thay vì ~816 như ước tính ban đầu | Tier A nhỏ hơn dự kiến (862 vs ~1.919 tin) | Ước tính cũ dùng regex lỏng dễ tạo dự án giả; Tuần 3 dùng alias + đối chiếu text để nâng độ phủ có kiểm soát |
| Quận/huyện chỉ 18,9% | Truy vấn theo quận còn hạn chế | Tuần 3: dictionary phường→quận→tỉnh để suy ra từ ward |
| 47,5% tin không có giá | Mẫu SFT có giá ít hơn | Chấp nhận: không bịa giá; brief sinh nội dung sẽ dùng fact có sẵn |
| Tên dự án hiển thị không dấu (từ slug URL) | Ảnh hưởng trình bày | Tuần 3: lấy tên có dấu từ title/description qua alias |

## Carry-over sang Tuần 3

| Việc | Owner | Ghi chú |
|---|---|---|
| Deploy staging | Quang | Vẫn chờ Anh chọn nền tảng + cấp tài khoản |
| Chunking + embedding + FTS index | Quang | Trên `clean_listings` tier A/B |
| Entity resolution + alias (nâng độ phủ dự án) | Quang + Hải | Dictionary slug + đối chiếu title/description |
| Split 70/15/15 theo project + leakage audit | Hải | Trên 347 dự án hiện có (cập nhật sau khi alias xong) |
| SFT draft v1 + 60–90 gold retrieval queries | Hải | Theo Plan/02 §7–8 |
| Khóa `crawler_contract_v1.json` | Hải | Contract nháp ở Plan/02 §3, nay đã có cài đặt thực tế trong `reparse.py` |
