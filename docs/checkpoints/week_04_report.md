# Checkpoint Tuần 4 — Baseline A/B + Content Studio + R3

**Ngày:** 28/07/2026 · **Branch:** `tuan-04-baseline-ab` · **Người thực hiện:** Quang (+ Claude hỗ trợ)

Artefact kèm theo: [đánh giá retrieval R1–R3](week_04_retrieval_eval.md) · [baseline A vs B](week_04_ab_baseline.md) · [data card dataset_v1](week_03_data_card.md)

## Kết quả so với gate Tuần 4 ([Plan/01 §6](../../Plan/01_KE_HOACH_TONG_THE.md))

| Hạng mục gate | Trạng thái | Bằng chứng |
|---|---|---|
| Query router | ✅ | `app/services/query_router.py` — 5 ý định (fact/quan hệ/so sánh/thời gian/chung), nhận diện dự án trong câu hỏi, giao trọng số theo ý định |
| R3 context assembler (RRF) | ✅ | RRF **có trọng số** cho 3 nhánh (BM25 + vector + graph); trọng số chốt bằng sweep 6 cấu hình trên gold query |
| Prompt versions khóa | ✅ | `prompt_v1` + hash prompt lưu theo từng lần sinh; A và B dùng **đúng cùng prompt**, chỉ khác khối dữ kiện |
| Content Studio 4 kênh | ✅ | `/studio` — mô tả BĐS · Facebook · email · landing SEO × 3 persona, chạy A và B cạnh nhau |
| Evidence panel | ✅ | Hiển thị chunk kèm nguồn, nhánh truy xuất (bm25/vector/graph), đường đi graph và đối chiếu claim |
| Generation logging | ✅ | Bảng `generations`: cấu hình, retrieval, prompt version + hash, model, seed, context id, claim, metrics, latency |
| **A và B chạy end-to-end trên web** | ✅ | Qwen2.5 chạy **trên GPU máy local** (3B-4bit qua UI, 1.5B-fp16 cho batch), sinh thật qua UI và qua CLI; kết quả 4 brief × A/B ở §2.3 |
| **Bảng so sánh R1–R3 đầu tiên** | ✅ | [week_04_retrieval_eval.md](week_04_retrieval_eval.md) — 7 cấu hình × 72 gold query |
| **UI giải thích ≥1 graph path** | ✅ | Evidence panel in đường đi `Dự án → Tòa → Loại căn` kèm URL nguồn của từng cạnh |
| Staging URL (carry-over T1) | ⏳ **chưa** | Vẫn chờ Anh chọn nền tảng cloud + cấp tài khoản |

## 1. Kết quả retrieval R1–R3 (72 gold query, top-k = 10)

| Cấu hình | project precision@10 | listing recall@10 | hit@10 | MRR |
|---|---:|---:|---:|---:|
| R1-fts (tsvector thô — Tuần 3) | 0,090 | 0,117 | 0,431 | 0,132 |
| **R1-bm25 (mới Tuần 4)** | **0,964** | 0,848 | 1,000 | 0,993 |
| R1-vector (bge-m3) | 0,940 | 0,855 | 1,000 | 0,976 |
| R1-hybrid (BM25 + vector, RRF có trọng số) | 0,981 | 0,865 | 1,000 | 1,000 |
| R2-graph (≤2 hop) | 0,738 | 0,862 | 0,972 | 0,972 |
| R3-fixed (trọng số cố định) | 0,986 | 0,928 | 1,000 | 1,000 |
| **R3-router (production)** | **1,000** | **0,938** | 1,000 | 1,000 |

### 1.1. BM25 tiếng Việt đã sửa được negative result của Tuần 3

Tuần 3 kết luận "RRF làm giảm chất lượng" (0,551 so với 0,850). Tuần 4 tìm ra **nguyên nhân thật là nhánh lexical**, không phải bản thân RRF:

| Vấn đề của `ts_rank_cd` (Tuần 3) | Cách xử lý (Tuần 4) | Kết quả |
|---|---|---|
| Không có IDF → từ phổ biến ("căn", "hộ", "bán") lấn át | BM25 chuẩn với IDF thật (K1 = 1,5 · b = 0,75) | 0,090 → 0,964 |
| Cấu hình `simple` cắt theo âm tiết, "căn hộ" thành "can" + "ho" | Token = âm tiết **+ bigram âm tiết** (`can_ho`, `phong_ngu`) | Khôi phục nghĩa từ ghép mà không cần bộ tách từ ngoài |
| Trộn RRF trọng số bằng nhau | RRF **có trọng số**, chốt bằng sweep | 0,551 → 0,981 (R1-hybrid) |

Chỉ mục ngược tự cài: bảng `lexical_postings`, **595.337 posting** cho 9.656 chunk. Không dùng thư viện search ngoài — công thức tính tay được, giải thích được trước hội đồng.

### 1.2. Sweep trọng số RRF (R3, không router)

| vector | bm25 | graph | precision@10 | recall@10 | MRR |
|---:|---:|---:|---:|---:|---:|
| 1,0 | **0,6** | **0,3** | **0,910** | 0,928 | 0,931 |
| 1,0 | 0,6 | 0,6 | 0,906 | 0,931 | 0,927 |
| 1,0 | 0,6 | 0,9 | 0,903 | 0,935 | 0,922 |
| 1,0 | 0,3 | 0,9 | 0,903 | 0,938 | 0,914 |
| 1,0 | 0,3 | 0,3 | 0,901 | 0,932 | 0,935 |
| 1,0 | 0,3 | 0,6 | 0,899 | 0,938 | 0,915 |

*(Sweep chạy trước khi sửa nhãn của nhóm câu so sánh nên tuyệt đối thấp hơn bảng §1, nhưng thứ hạng giữa các cấu hình không đổi.)*

Đọc kết quả: R3 **không nhạy với trọng số** (0,899–0,910) — khác hẳn RRF không trọng số của Tuần 3. Nghĩa là khi cả ba nhánh đều mạnh thì việc trộn an toàn; vấn đề trước đây nằm ở nhánh yếu chứ không ở cơ chế trộn.

### 1.3. Router: sửa một lỗi thiết kế nhờ đo

Bản router đầu tiên **kém hơn** trọng số cố định (0,824 < 0,899). Chẩn đoán bằng số: bộ lọc dự án chạy đúng 55/72 truy vấn, **0 truy vấn lọc sai** — vậy lỗi không nằm ở nhận diện thực thể. Nguyên nhân thật: bộ lọc chỉ áp cho nhánh BM25 và vector, còn **nhánh graph vẫn kéo dự án hàng xóm 2-hop vào**. Sau khi bắt cả ba nhánh tôn trọng `allowed_projects`, router vượt lên 1,000.

### 1.4. Giới hạn của con số 1,000 (phải nói rõ khi bảo vệ)

Bộ gold query hiện tại **luôn nêu đích danh tên dự án** (sinh bằng template từ dữ liệu test). Router nhận ra tên dự án và lọc, nên precision gần như tất yếu đạt trần. Con số này chứng minh **pipeline hoạt động đúng**, chưa chứng minh hệ thống mạnh với câu hỏi khó. Việc bắt buộc ở Tuần 5:

- Hải soát tay 72 query và **viết thêm nhóm câu hỏi không nêu tên dự án** ("căn 2PN dưới 5 tỷ có sổ hồng gần công viên ở quận 7") — đây mới là ca thật của người dùng.
- Giữ nguyên bộ hiện tại làm *sanity set*, tách riêng bộ khó làm *hard set*, báo cáo cả hai.

## 2. Sinh nội dung A/B

### 2.1. Model chạy trên GPU máy local

Cả hai model đều là **mã nguồn mở, đa ngôn ngữ** — đúng phát biểu của đề cương ("sử dụng một mô hình ngôn ngữ mã nguồn mở phù hợp với tiếng Việt hoặc đa ngôn ngữ, áp dụng LoRA/QLoRA").

| Hạng mục | Qwen2.5-3B-Instruct | Qwen2.5-1.5B-Instruct |
|---|---|---|
| Nạp | 4-bit NF4 (bitsandbytes) | fp16 |
| VRAM đỉnh | **2,1 GB** | ~3,7 GB |
| Tốc độ (prompt ngắn) | ~3,2 token/giây | **~4,1 token/giây** |
| Một bài A (200 token) | ~280–330 giây | **48–49 giây** |
| Một bài B (có context) | **675 giây** | **90–107 giây** |

*(Bài đầu tiên của mỗi lượt chạy tốn thêm ~90 giây nạp trọng số vào VRAM; các số trên là trạng thái ổn định.)*

**Quyết định kỹ thuật:** GTX 1650 Ti (compute capability 7.5) không có nhân tính toán cho int4 nên bitsandbytes phải giải lượng tử từng bước — bản 3B tuy tốn ít VRAM hơn nhưng **chậm hơn 6–7 lần**: 675 giây cho một bài có context, không dùng được cho batch lẫn demo. Baseline Tuần 4 vì vậy chạy bằng **1.5B fp16**; bản 3B giữ lại làm đối chứng chất lượng (kết quả vẫn nằm trong bảng `generations`).

Đây là kết quả trái trực giác đáng ghi lại: **lượng tử 4-bit chỉ có lợi khi phần cứng hỗ trợ nó**. Trên GPU không có nhân int4, 4-bit đổi VRAM lấy tốc độ theo tỷ lệ rất xấu.

Ràng buộc chung cho cả hai: greedy (`do_sample=False`), seed cố định 42.

**Bằng chứng tái lập:** brief `description` của `sun-urban-city` được sinh lại ở hai lượt chạy khác nhau (28/07 15:54 và 29/07 02:26, hai tiến trình riêng, cách nhau 10,5 giờ) → cùng `prompt_hash` `dddc1d863e7c`, **raw output trùng khít từng byte** (SHA-256 `0156f6a9816304ee…`). Đúng yêu cầu gói tái lập của [Plan/03 §6](../../Plan/03_KE_HOACH_THUC_NGHIEM.md).

Ràng buộc so sánh công bằng (Plan/03 §2): A và B dùng **cùng model, cùng seed, cùng decoding, cùng prompt**; khác biệt duy nhất là khối dữ kiện truy xuất trong prompt của B.

### 2.2. Kiểm tra claim → fact (rule-based, không dùng LLM chấm LLM)

- Câu chứa **số** hoặc **thuộc tính** (giá/diện tích/phòng ngủ/pháp lý/tiện ích) được coi là một *claim*.
- Claim **có căn cứ** khi mọi con số trong câu đều xuất hiện trong facts đã truy xuất (đã chuẩn hóa đơn vị tỷ/triệu, có tính cả mốc `valid_from`/`valid_to`).
- Câu chứa từ cấm ("cam kết lợi nhuận", "chắc chắn sinh lời"…) bị đánh dấu `forbidden`.
- URL trích dẫn được bóc trước khi đếm số — mã tin trong link không phải số liệu.

### 2.3. Kết quả A vs B (4 brief × 2 cấu hình, Qwen2.5-1.5B fp16)

Brief lấy tất định từ **dự án thuộc split test** của `dataset_v1`, xoay vòng 4 kênh × 3 persona. A và B dùng cùng model, cùng seed, cùng decoding, cùng prompt — khác biệt duy nhất là khối dữ kiện truy xuất (R3, k = 3).

| Chỉ số | A (prompt-only) | B (RAG) | Chênh lệch |
|---|---:|---:|---|
| **Tỷ lệ claim không có căn cứ** | 0,2042 | **0,0917** | **−55%** |
| Bài có ít nhất 1 claim vô căn cứ | 4/4 | **2/4** | −2 bài |
| Số claim trung bình mỗi bài | 5,00 | 5,25 | +0,25 |
| Câu chứa từ cấm | 0 | 0 | — |
| Độ dài thân bài (ký tự) | 574 | 559 | −15 |
| Thời gian sinh trung bình (giây) | 72,6 | 100,6 | +28 |

Từng brief:

| Dự án | Kênh | Persona | A | B |
|---|---|---|---:|---:|
| sun-urban-city | description | young_family | 0,1667 | **0,0** |
| mizuki-park | facebook | investor | 0,2 | 0,1667 |
| the-beverly-vinhomes-grand-park | email | first_home | 0,25 | 0,2 |
| the-marq | landing_seo | young_family | 0,2 | **0,0** |

**Đọc kết quả:** B tốt hơn A ở **cả 4/4 brief**, không có ca nào RAG làm xấu đi. Tỷ lệ bịa số giảm hơn một nửa, trong khi số claim không giảm — nghĩa là B **không né tránh nói số** để đạt điểm, mà nói số đúng hơn. Giá phải trả là +28 giây mỗi bài do prompt dài hơn.

Cảnh báo khi trích dẫn: **n = 4 brief, chưa đủ để kiểm định thống kê**. Đây là baseline xác nhận hướng đi, không phải kết luận. Cỡ mẫu thật theo [Plan/03 §5](../../Plan/03_KE_HOACH_THUC_NGHIEM.md) là frozen test 40–60 brief + human eval mù, chạy khi đã có GPU thuê (Tuần 5–6). Ngoài ra chỉ số này là rule-based: nó bắt được sai số liệu, **không** bắt được câu văn sai sự thật mà không chứa số.

Bảng gốc do máy sinh: [week_04_ab_baseline.md](week_04_ab_baseline.md).

## 3. Lỗi dữ liệu phát hiện qua UI (và đã sửa)

Soi Evidence panel thấy thẻ dữ kiện ghi **"Phòng ngủ: 81"**. Truy ra: crawler có 31 tin ghi > 20 phòng ngủ (cao nhất 92) và 30 tin ghi > 20 phòng tắm (cao nhất **675**). Đây là lỗi parser nguồn, không phải dữ liệu thật.

Đã bổ sung luật D1: `bedrooms`/`bathrooms` ngoài khoảng 1–20 và `area_m2` ngoài 5–10.000 m² thì **bỏ giá trị + gắn flag `outliers`**, thay vì để fact rác chảy vào prompt. Bài học ghi vào báo cáo: *Evidence panel không chỉ để trình diễn — nó là công cụ soát dữ liệu.*

## 4. Kiểm chứng đã chạy

- **Tests:** 108/108 pass (thêm test BM25, router, prompt A/B, claim check, sinh nội dung, chặn giá trị phi lý); `npx tsc --noEmit` sạch.
- **E2E trình duyệt:** đăng nhập → `/studio` → chọn dự án Vinhomes Central Park → "Xem trước dữ kiện" trả 6 chunk kèm nguồn, nhãn nhánh `bm25+graph+vector`, router in rõ ý định và trọng số.
- **CLI:** `python -m app.ab_cli` chạy batch A/B trên brief cố định lấy từ split test.

## 5. Cách chạy local

```powershell
docker compose up -d
cd backend
.\.venv\Scripts\alembic.exe upgrade head              # thêm lexical_postings + generations
.\.venv\Scripts\python.exe -m app.index_cli           # dựng BM25 postings (lần đầu ~3 phút)
.\.venv\Scripts\python.exe -m app.dataset_cli --eval --sweep --eval-out ..\docs\checkpoints\week_04_retrieval_eval.md
.\.venv\Scripts\python.exe -m app.ab_cli --briefs 6 --max-new-tokens 350
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
cd ..\frontend; npm run dev                            # /studio
```

Máy không GPU: thêm `--provider template` cho `ab_cli` và `--backend hashing` cho `index_cli` (chỉ để pipeline chạy, **không dùng cho số liệu báo cáo**).

## 6. Hạn chế đã biết

| Hạn chế | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| Gold query đều nêu tên dự án | precision 1,000 chưa phản ánh ca khó | Tuần 5: Hải viết *hard set* không nêu tên dự án |
| Sinh chậm trên GTX 1650 Ti: 1.5B fp16 mất 50–107 giây/bài, 3B 4-bit mất 5–11 phút | Demo trực tiếp phải chờ; batch lớn không khả thi | Dùng 1.5B cho demo tương tác; số liệu chính thức chạy trên GPU thuê từ Tuần 5 |
| Baseline A/B chỉ có **n = 4 brief** | Chưa kiểm định thống kê được | Frozen test 40–60 brief + human eval mù (Plan/03 §5) khi có GPU thuê |
| Claim check chỉ đối chiếu **số**, chưa đối chiếu mệnh đề định tính | Bỏ sót loại bịa "gần trường học quốc tế" | Tuần 7: critic LLM + refine 1 vòng (Plan/01 §6) |
| Chưa có cấu hình C/D | Chưa trả lời được RQ2/RQ3 | Tuần 5: QLoRA (cần GPU thuê ≥12GB) |

## 7. Carry-over sang Tuần 5

| Việc | Owner | Ghi chú |
|---|---|---|
| Deploy staging | Quang | Vẫn chờ Anh chọn nền tảng + cấp tài khoản |
| **Thuê GPU ≥12GB cho QLoRA** | Quang + Hải | GTX 1650 Ti không đủ; chốt trước khi vào Tuần 5 |
| Hard set gold query + soát tay 72 query hiện có | Hải | Khóa benchmark sau khi soát |
| Pilot 2–3 backbone → chốt model chính thức | Hải | Theo Plan/03 §3 |
| Reviewer flow: duyệt/từ chối/version/export | Quang | Gate Tuần 5 |
| SFT gold/silver từ 1.500 mẫu nháp | Hải | Cần cho QLoRA |
