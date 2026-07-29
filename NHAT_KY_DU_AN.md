# Nhật ký và bàn giao trạng thái ĐATN

> **File bắt đầu duy nhất cho phiên làm việc mới.** Khi mở lại dự án, hãy đọc file này trước. Chỉ mở các tài liệu hoặc mã nguồn được dẫn ở đây khi nhiệm vụ hiện tại thực sự cần chi tiết hơn.

**Dự án:** AI tạo và tối ưu nội dung marketing BĐS đa kênh
**Cập nhật gần nhất:** 29/07/2026 (tối)
**Trạng thái tổng thể:** Tuần 1–6 đã xong; **152/152 tests pass**.

| Tuần | Kết quả đã có bằng chứng |
|---|---|
| 1–2 | Monorepo FastAPI+Next.js, auth/RBAC/tenant, pipeline D1–D5 idempotent, 4.794 tin sạch + 31.167 facts + graph ≤2 hop |
| 3 | Knowledge base 9.656 chunk embed **bge-m3 trên GPU**, FTS tiếng Việt + pgvector HNSW, entity resolution 617 dự án, `dataset_v1` đóng băng (leakage audit **đạt**), 72 gold query |
| 4 | **BM25 tiếng Việt tự cài**: nhánh lexical 0,090 → **0,964** precision@10; **R3-router 1,000 · recall 0,938 · MRR 1,000**; Content Studio + Evidence panel; baseline A/B ~~RAG giảm claim vô căn cứ 55%~~ — **kết luận này đã bị Tuần 6 bác bỏ, xem mục 5e** |
| 5 | Ma trận **A–D đủ bốn ô** (C/D chỉ chờ adapter cắm vào — mục 5-0), **vòng duyệt nội dung** `/review` đầy đủ, gói training bàn giao Hải (`training/`), SFT export 237 mẫu đã lọc bằng claim checker |
| 6 | **36 câu hỏi khó không nêu tên dự án** → precision 1,000 của Tuần 4 phần lớn là công của khớp tên (bộ khó chỉ 0,273); **router có chế độ "tìm theo mô tả"** đưa bộ khó lên 0,339 mà không tụt bộ standard; **thí nghiệm đóng băng có snapshot + kiểm định thống kê**, dashboard `/experiments`; **n = 12 cho thấy RAG chưa có ưu thế đo được (mục 5e)** |

**Ba việc chặn tiến độ, đều cần quyết định ngoài code:** (1) Hải train adapter QLoRA đầu tiên, (2) staging URL chờ Anh cấp tài khoản cloud, (3) mô tả nguồn bị crawler cắt cụt (mục 5c).

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
- **Đã xử lý xong ở Tuần 2** bằng pipeline D1–D5 (`Plan/02` §4): 4.794/4.795 tin qua contract; giá khôi phục lên **52,5%**, dự án **347 dự án / 862 tin**, phường/xã 99,9%, pháp lý 28,8%, tiện ích 33,8%.
- Ước tính cũ "816 dự án / 1.919 tin" dùng regex thăm dò lỏng (lẫn tên phường); luật chính thức siết chặt hơn, đổi lại không có entity giả — nâng độ phủ bằng alias ở Tuần 3.
- Số liệu đầy đủ (sinh tự động từ DB): `docs/checkpoints/week_02_data_quality.md`.

## 4. Phân công đã chốt

- **Lê Văn Quang:** hệ thống + tích hợp — backend/frontend, database, auth/RBAC/tenant, graph storage/traversal, hybrid retrieval, CI/CD, dashboard, deployment.
- **Phạm Vũ Hải:** dữ liệu + mô hình — crawler/contract, làm sạch, SFT dataset, QLoRA, evaluation, vision data.

## 5-0. Hợp đồng bàn giao QLoRA — đọc trước khi Hải train

Quyết định 29/07 của Anh: **việc cần GPU giao cho Hải chạy máy khác hoặc Colab**, phần còn lại
làm trước sao cho "gắn vào là chạy thông". Đã dựng xong điểm ghép:

```
máy có DB (Quang)                         máy GPU (Hải / Colab)
  python -m app.sft_cli  ──train.jsonl──▶   python training/qlora_train.py
                           validation.jsonl              │
  backend/models/adapters/<tên>/  ◀── copy nguyên thư mục ┘
      → cấu hình C/D chạy ngay, KHÔNG sửa code, KHÔNG migration
```

- Toàn bộ hướng dẫn cho Hải: `training/README.md` (kèm bảng lỗi thường gặp và cách xử lý).
- Kiểm môi trường GPU trước khi tốn giờ: `python qlora_train.py --smoke` (~2 phút, dữ liệu giả).
- Adapter phải kèm `adapter_card.json` — backbone, siêu tham số, dataset version, loss. Thiếu
  card vẫn nạp được nhưng bị đánh dấu "không dùng cho số liệu báo cáo".
- **Backbone lấy từ card, không lấy từ cấu hình backend.** Nạp adapter lên sai base model thì
  transformers không báo lỗi mà sinh văn rác — đã chặn bằng code.
- Chưa có adapter mà chạy C/D thì API trả 400 kèm hướng dẫn, Studio hiện cảnh báo ngay.

## 5a. Kết quả baseline A/B — ⚠️ **đã bị bác bỏ ở Tuần 6, đọc mục 5e trước khi trích**

4 brief lấy từ dự án thuộc split test × 2 cấu hình, `Qwen2.5-1.5B-Instruct` fp16 trên GPU máy, greedy + seed 42, retrieval R3 với k = 3:

| Chỉ số | A (prompt-only) | B (RAG) |
|---|---:|---:|
| Tỷ lệ claim không có căn cứ | 0,2042 | 0,0917 (−55%) |
| Bài có ít nhất 1 claim vô căn cứ | 4/4 | 2/4 |
| Số claim trung bình mỗi bài | 5,00 | 5,25 |
| Thời gian sinh trung bình | 72,6 giây | 100,6 giây |

Bốn brief này **tái lập chính xác** ở run Tuần 6 (từng con số trùng khít), nhưng chạy tiếp 8 brief nữa thì ưu thế biến mất — xem mục 5e. **Không trích bảng này như kết luận.**

Bảng chi tiết: `docs/checkpoints/week_04_ab_baseline.md`; phân tích: `week_04_report.md` §2.3.

**Bằng chứng tái lập đã có:** cùng một brief sinh lại ở hai tiến trình khác nhau cách nhau 10,5 giờ cho **raw output trùng khít từng byte** (cùng `prompt_hash`, cùng SHA-256). Đây là câu trả lời sẵn cho câu hỏi hội đồng "kết quả có tái lập được không".

**Bài học vận hành:** batch tối 28/07 chết vì tắt Docker Desktop trước khi tiến trình Python xong → luôn `docker compose up -d` trước và để batch kết thúc rồi mới tắt máy.

**Chưa làm, cố ý bỏ qua:** chạy lại toàn bộ pipeline theo `reparse_v2`. Ảnh chụp DB hiện tại vẫn là bản **trước** `reparse_v2`, tức 31 tin phòng ngủ phi lý vẫn còn trong dữ liệu đang chạy; luật chặn đã có trong code, chỉ chờ lần rebuild kế tiếp (khoảng 15 phút GPU). **Phải ghi rõ điều này nếu trích số liệu từ DB hiện tại.**

## 5e. ⚠️ Tuần 6 bác bỏ kết luận A/B của Tuần 4 — chỗ này quan trọng nhất

Run `week6_frozen_ab`: **12 brief** × A/B, cùng model, cùng seed, cùng prompt (`docs/checkpoints/week_06_experiment.md`).

| Chỉ số | A | B |
|---|---:|---:|
| Tỷ lệ claim không có căn cứ | **0,1604** | 0,1747 |
| Bài có ≥1 claim vô căn cứ | 9/12 | **7/12** |
| Số claim mỗi bài | 5,58 | 6,08 |
| Đúng định dạng 3 phần | **0,583** | 0,333 |

Chênh lệch **+0,0142 (B xấu hơn)**, KTC 95% **[−0,111; +0,138]** chứa 0, thắng/thua **6/5**, dz 0,06, **p = 0,85**. Tức là **ở n = 12, RAG không có ưu thế đo được**.

**Vì sao Tuần 4 ra kết quả ngược:** `pick_briefs` xếp dự án theo số tin giảm dần, nên "4 brief đầu" chính là **4 dự án nhiều tin nhất** — nhóm mà truy xuất có nhiều dữ kiện nhất. Lấy 4 phần tử đầu của danh sách đã sắp xếp không phải lấy mẫu, mà là chọn ca thuận lợi. Cảnh báo "n = 4" hồi đó đúng nhưng chưa đủ: vấn đề nằm ở **cách chọn mẫu**, không chỉ ở cỡ mẫu.

**Giả thuyết (chưa kiểm chứng):** model 1,5B không dùng nổi khối context ~2.000 token — nhiều số trước mắt thì viết nhiều câu có số hơn (6,08 so với 5,58) và chép sai nhiều hơn; bằng chứng gián tiếp là B tuân định dạng kém hẳn (0,333 so với 0,583). Ba cách kiểm chứng, rẻ đến đắt, ở `week_06_report.md` §3.2 — ưu tiên **chạy lại đúng 12 brief này trên model 7–8B**.

**Không đổi phạm vi đồ án:** đây chính là thứ thí nghiệm sinh ra để trả lời, và Plan/03 §7 đã khóa trước nguyên tắc báo cáo cả kết quả âm. Nhưng mọi số trích từ Tuần 4 phải kèm ghi chú này.

## 5d. Tuần 6 — hai phát hiện phải nhớ khi viết báo cáo

**1. Số đẹp của Tuần 4 đo nhầm thứ.** Cả 72 gold query đều nêu tên dự án nên router khớp tên rồi lọc thẳng — precision 1,000 đo *khả năng khớp tên*, không đo khả năng tìm kiếm. Thêm 36 câu hỏi mô tả (thuộc tính / ngân sách / địa bàn, **không nêu tên**) thì cùng hệ thống rơi xuống **0,273**. BM25 sụp mạnh nhất (0,964 → 0,115) vì không còn tên riêng để bám. **Trích số phải trích cả hai cột**, nếu không là để người đọc hiểu sai.

**2. Nhánh graph mạnh nhất đúng ở chỗ trước giờ chưa đo.** Bộ standard: graph yếu nhất (0,738). Bộ khó: graph **mạnh nhất (0,465)**, riêng câu hỏi theo địa bàn đạt 0,855 — nó khớp thực thể phường/quận rồi đi theo cạnh, thay vì so chuỗi ký tự. Nhưng R3 lúc đầu không hưởng được vì trọng số cố định hạ graph xuống 0,3. Đã sửa: router chia hai chế độ, **không nhận ra dự án nào ⇒ dùng trọng số riêng** (`vector 1,0 · bm25 0,3 · graph 0,9`, chốt bằng sweep) → bộ khó 0,273 → **0,339**, bộ standard giữ nguyên **1,000**. Sweep cũng cho thấy nếu áp trọng số đó cho *mọi* câu thì standard tụt 0,986 → 0,738 — đó là lý do phải có router chứ không phải một bộ trọng số duy nhất.

**Một lỗi đo lường đã mắc và đã sửa:** precision chuẩn hóa ra **2,16** ("đúng 216%") vì chia cho trần tính theo *tin* trong khi đếm theo *chunk* — mỗi tin có 3 chunk nên một tin đúng chiếm được 3 ô trong top-k. Sửa bằng cách đưa tử và mẫu về cùng cấp tin phân biệt. Bài học: chỉ số vượt 1,0 là dấu hiệu tử và mẫu khác đơn vị.

## 5. Việc cần làm tiếp theo (đầu Tuần 7)

1. **Hải train adapter đầu tiên rồi bàn giao** — theo `training/README.md`, chạy `--smoke` kiểm môi trường trước. Đây là thứ duy nhất còn thiếu để cấu hình C/D có số thật. Khi có adapter: `python -m app.experiment_cli --briefs 12 --configs A,B,C,D` là điền đủ ma trận, không sửa code.
2. **Chọn nền tảng cloud + cấp tài khoản** → deploy staging (carry-over từ Tuần 1, vẫn chưa xong).
3. **Quyết định về mô tả bị cắt cụt** (mục 5c) — crawl lại hay hạ kỳ vọng độ dài; phải chốt trước khi train thật.
4. Hải: soát tay **108 gold query**, soát bộ hard riêng (`/dataset` có bộ lọc "Không nêu tên dự án"). Nhãn tự sinh chưa phải nhãn cuối.
5. **Vision + critic (Tuần 7 theo Plan/01 §6)** — VLM trích visual fact có confidence + UI xác nhận; ablation D+V.
6. Chốt danh sách human rater (Plan/03 §5) — đã trễ so với dự kiến Tuần 3; đây là nửa bằng chứng còn thiếu bên cạnh chỉ số tự động.
7. Tích lũy nội dung đã duyệt trong `/review` để có mẫu SFT cho 3 kênh còn lại.

Chi tiết + cách chạy local: `docs/checkpoints/week_01_report.md` → `week_06_report.md`.

## 5c. Mô tả trong DataBDS bị crawler cắt cụt — cần Hải quyết

Đo trên 4.795 tin raw: trung vị **166 ký tự**, p90 = 244, chỉ **228 tin (4,8%) đạt ≥300 ký tự**, nhiều bản đứt giữa câu (`"...Nam Tư: 0772 011 Zalo Hỗ trợ xem nhà nhanh"`). Crawler lấy đoạn preview chứ không lấy thân tin đầy đủ.

Hệ quả: kênh `description` yêu cầu 180–260 **từ**, mẫu train chỉ ~30 từ. Model học được cách gắn dữ kiện và văn phong nhưng **không học được độ dài**. Ba hướng: (1) Hải crawl lại trường mô tả — sửa tận gốc; (2) giữ nguyên và hạ kỳ vọng, ghi rõ giới hạn trong báo cáo; (3) dồn vào nguồn nội dung đã duyệt. Khuyến nghị làm (1) nếu crawler còn chạy được, (2) làm nền để không chặn tiến độ.

Số liệu đầy đủ: `week_05_report.md` §4.

## 5b. Bài học kỹ thuật (giữ lại để viết báo cáo)

**Tuần 5:**

- **Adapter nạp lên sai backbone không báo lỗi — nó sinh văn rác.** Vì vậy backbone được lấy từ `adapter_card.json` chứ không từ cấu hình backend. Loại sai lầm im lặng thì phải chặn bằng code, không chặn bằng quy ước.
- **Claim checker dùng được làm bộ lọc dữ liệu train.** Mô tả người đăng thường chứa số không có trong facts; train nguyên xi lên đó là dạy model bịa số. Lọc bằng chính công cụ đo giữ lại 237/3.191 mẫu sạch — công cụ đo và công cụ làm sạch là một.
- **Chống bịa số phải chặn cả người, không chỉ model.** Bản sửa tay được chấm lại claim trên đúng tập fact của lần sinh gốc; thử thêm "Giá bán 999 tỷ, chiết khấu 45%" thì hệ thống bắt đúng hai số.
- **Tách nhật ký thí nghiệm khỏi sản phẩm làm việc.** `generations` bất biến (ghi cả lần hỏng) để tái lập; `content_versions` sửa được, nhiều phiên bản. Trộn một bảng thì mất một trong hai.

**Tuần 4:**

- **Negative result Tuần 3 có nguyên nhân cụ thể, không phải lỗi của RRF.** Nhánh lexical `ts_rank_cd` thiếu IDF và cắt sai từ tiếng Việt. Thay bằng BM25 tự cài (IDF thật + bigram âm tiết) → 0,090 lên 0,964; RRF có trọng số → 0,981. Cả hai số đều đo trên cùng 72 gold query.
- **Router phải áp bộ lọc cho *mọi* nhánh.** Bản đầu chỉ lọc bm25/vector, để graph kéo dự án hàng xóm 2-hop vào nên kém hơn trọng số cố định (0,824 < 0,899); sau khi graph cũng tôn trọng `allowed_projects` thì đạt 1,000.
- **Model nhỏ hơn không cứu được VRAM thiếu.** Đổi từ Qwen2.5-3B 4-bit sang Qwen2.5-1.5B fp16 chỉ giảm 280–330 giây xuống 251 giây một bài — không phải bước nhảy như kỳ vọng, vì fp16 1.5B chiếm ~3,6/4 GB nên vẫn tràn sang RAM hệ thống. Kết luận: 4 GB là trần cứng cho khâu sinh nội dung, phải thuê GPU chứ không tối ưu tiếp được.
- **Evidence panel là công cụ soát dữ liệu, không chỉ để trình diễn.** Nhìn UI mới phát hiện fact "81 phòng ngủ"; truy ra 31 tin > 20 phòng ngủ và 30 tin > 20 phòng tắm (cao nhất 675) do parser nguồn. Đã thêm luật chặn ở D1 (`reparse_v2`).

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
| 27/07/2026 | **Tuần 1 — nền tảng + ingestion** | Commit `8a70cf1`, merge `8383865`; 13/13 tests; 200 tin import 2 lần → `inserted=200` rồi `unchanged=200` | Đạt gate trừ staging URL; `docs/checkpoints/week_01_report.md` |
| 27/07/2026 | **Tuần 2 — D1–D5 + graph** | Migration `8032b6027123`; 56/56 tests; 4.795 tin qua pipeline → 4.794 clean · 30.820 facts · 1.102 node · 1.535 cạnh · 1 quarantine | Chạy lại: `inserted=0 unchanged=4794`, facts/node/cạnh +0 → idempotent |
| 27/07/2026 | Gate query graph | `GET /api/graph/projects/sunshine-sky-city/paths` → `Sunshine Sky City → Tòa V8 → apartment-2pn` kèm URL nguồn | Đạt gate "query path Project → Building → UnitType" |
| 27/07/2026 | Báo cáo chất lượng dữ liệu | `docs/checkpoints/week_02_data_quality.md` sinh bằng `pipeline_cli --report` | Giá 31,6% → 52,5%; dự án 347; phường/xã 99,9% |
| 28/07/2026 | **Tuần 3 — knowledge base + dataset_v1** | Migration `4982a1adb98d` + `a7aad62eeea9`; 81/81 tests; 9.656 chunk embed bằng bge-m3 trên GPU (8,8 phút) | Index idempotent; FTS + pgvector HNSW chạy thật |
| 28/07/2026 | Entity resolution bằng từ điển phường | `app/services/alias.py` | Dự án 347 → **617**; tin Tier A 862 → **1.539**; tên dự án có dấu |
| 28/07/2026 | Đóng băng `dataset_v1` | `docs/checkpoints/week_03_data_card.md` | Split 69,3/14,7/16,0 theo đơn vị; **leakage audit đạt (0 rò rỉ)**; 72 gold query; 1.500 mẫu SFT nháp |
| 28/07/2026 | **Tuần 4 — BM25 + R3 + Content Studio** | Migration `98f8c5885510` + `d715c20e509f`; 108/108 tests; `week_04_report.md` | Nhánh lexical 0,090 → **0,964**; R3-router **precision 1,000 · recall 0,938 · MRR 1,000** |
| 28/07/2026 | Sweep trọng số RRF của R3 | 6 cấu hình × 72 query, bảng trong `week_04_retrieval_eval.md` | Chốt vector 1,0 · bm25 0,6 · graph 0,3; R3 không nhạy với trọng số (0,899–0,910) |
| 28/07/2026 | Generator chạy trên GPU máy | `Qwen/Qwen2.5-3B-Instruct` 4-bit NF4, GTX 1650 Ti | VRAM đỉnh **2,1GB**, ~3,2 token/giây, greedy + seed cố định → tái lập được |
| 28/07/2026 | Chặn dữ liệu phi lý phát hiện qua UI | `reparse_v2`: bedrooms/bathrooms 1–20, area 5–10.000 m² | Loại 31 tin > 20 phòng ngủ (max 92) và 30 tin > 20 phòng tắm (max 675) |
| 29/07/2026 | **Baseline A vs B** | `docs/checkpoints/week_04_ab_baseline.md` — 4 brief × 2 cấu hình, Qwen2.5-1.5B fp16 trên GPU | Claim vô căn cứ **0,2042 → 0,0917 (−55%)**; B thắng 4/4 brief; n = 4 nên chưa kiểm định thống kê |
| 29/07/2026 | Tái lập được kết quả sinh | Hai lượt chạy cách nhau 10,5 giờ, cùng `prompt_hash dddc1d863e7c`, seed 42 | Raw output **trùng khít từng byte** (SHA-256 `0156f6a9…`) |
| 29/07/2026 | **Tuần 5 — điểm ghép QLoRA + vòng duyệt** | Migration `804d7f4deca9`; 131/131 tests; `week_05_report.md` | Ma trận A–D đủ 4 ô; `/review` chạy E2E trên trình duyệt; adapter contract có 3 lớp bảo vệ |
| 29/07/2026 | Gói training bàn giao Hải | `training/` — `qlora_train.py`, README hợp đồng, requirements, notebook Colab | Độc lập hoàn toàn với backend; có `--smoke` kiểm môi trường GPU trước |
| 29/07/2026 | Dataset SFT sẵn sàng train | `python -m app.sft_cli` trên `dataset_v1` | **237 mẫu** (191 train · 46 val · 130 dự án) sau khi lọc bằng claim checker; loại 2.155 tin vì chứa số không có trong facts |
| 29/07/2026 | Phát hiện mô tả nguồn bị cắt cụt | Đo 4.795 tin raw: trung vị 166 ký tự, chỉ 4,8% đạt ≥300 | Mẫu SFT ngắn hơn yêu cầu kênh → cần Hải quyết (mục 5c) |
| 29/07/2026 | **Tuần 6 — frozen A/B n = 12** | Run `week6_frozen_ab` trong bảng `experiment_runs`; `docs/checkpoints/week_06_experiment.md` | **Bác bỏ kết luận Tuần 4**: chênh lệch +0,0142 (B xấu hơn), KTC 95% chứa 0, p = 0,85, thắng/thua 6/5 |
| 29/07/2026 | **Tuần 6 — bộ câu hỏi khó** | 36 câu mô tả không nêu tên dự án; `docs/checkpoints/week_06_retrieval_eval.md` (108 query) | R3-router: standard **1,000** nhưng hard chỉ **0,273** — chênh lệch là công của khớp tên |
| 29/07/2026 | Router chế độ "tìm theo mô tả" | Sweep 6 cấu hình trọng số trên bộ hard, chốt `vector 1,0 · bm25 0,3 · graph 0,9` | Hard 0,273 → **0,339**; standard giữ **1,000**; nhánh graph là nhánh mạnh nhất ở bộ hard (0,465) |
| 29/07/2026 | Dashboard so sánh + hạ tầng snapshot | Bảng `experiment_runs` (migration `377b71234a7d`); `/experiments`; 152/152 tests | Kiểm trên trình duyệt: snapshot, bảng chỉ số, so sánh cặp có KTC/p, 24 bài chi tiết, cảnh báo "chưa có adapter" cho C/D |
| 28/07/2026 | Đánh giá retrieval R1/R2 | `docs/checkpoints/week_03_retrieval_eval.md` | R1-vector precision@10 **0,850** · MRR 0,921; R2-graph recall **0,862**; R1-fts chỉ 0,087 và RRF không trọng số kém hơn vector → cần BM25 + RRF có trọng số ở Tuần 4 |

## 9. Blocker và câu hỏi mở

| Mức độ | Vấn đề | Owner | Hành động tiếp theo |
|---|---|---|---|
| Cao | **Chưa có adapter QLoRA thật** — C/D mới chứng minh được đường đi | Hải | Train ở máy GPU/Colab theo `training/README.md`, copy thư mục về `backend/models/adapters/`. Hạ tầng phía backend đã xong (mục 5-0) |
| Cao | **Chưa có staging URL** (carry-over từ Tuần 1) | Quang | Cần Anh chọn nền tảng cloud + cấp tài khoản; deploy ngay sau đó |
| Cao | **Mô tả nguồn bị crawler cắt cụt** (trung vị 166 ký tự) | Hải + Anh | Crawl lại trường mô tả, hoặc hạ kỳ vọng độ dài và ghi rõ trong báo cáo — mục 5c |
| Trung bình | Mẫu SFT mới có 237, dưới mục tiêu 800–1.500 | Hải | Nới ngưỡng lọc có kiểm soát + tích lũy nội dung đã duyệt trong `/review` |
| ~~Trung bình~~ | ~~Gold query đều nêu tên dự án → precision 1,000 chưa phản ánh ca khó~~ — **đã xử lý ở Tuần 6** | Quang | 36 câu hỏi mô tả không nêu tên; số thật của bộ khó là 0,339 (mục 5d) |
| **Cao** | **Ưu thế của RAG chưa chứng minh được** — n = 12 cho p = 0,85, KTC chứa 0 (mục 5e) | Hải + Quang | Chạy lại 12 brief trên model 7–8B; nếu vẫn không đảo chiều thì phải xem lại giả thuyết chính chứ không chỉ tăng cỡ mẫu |
| Trung bình | Bộ brief xếp theo số tin nên cắt n nhỏ là chọn ca thuận lợi | Quang | Lấy mẫu phân tầng theo quy mô dự án, hoặc chạy đủ 40–60 brief |
| Trung bình | Ảnh chụp DB đang chạy vẫn là bản **trước `reparse_v2`** | Quang | Chạy `pipeline_cli --rebuild` → `index_cli` → `dataset_cli --build --eval` (~15 phút GPU) trước khi lấy số liệu cuối |
| ~~Trung bình~~ | ~~R1-fts yếu (precision 0,086) kéo RRF xuống dưới vector~~ — **đã xử lý ở Tuần 4** | Quang | BM25 tự cài + RRF có trọng số → 0,964 / 0,981 |
| Trung bình | **108** gold query chưa soát tay (72 standard + 36 hard) | Hải | Soát và bỏ cờ `needs_review` trước khi khóa benchmark; `/dataset` có bộ lọc theo độ khó |
| Trung bình | Chưa chốt danh sách human rater | Cả nhóm | Chốt từ Tuần 3 theo `Plan/03` §5 |

---

**Lệnh nhắc cho phiên mới:** "Đọc `NHAT_KY_DU_AN.md`, báo lại trạng thái hiện tại trong 5–10 dòng, rồi tiếp tục đúng mục 'Việc cần làm tiếp theo'. Không quét toàn bộ dự án trừ khi task yêu cầu hoặc log có dấu hiệu lỗi thời."

## Current State & Hand-off

- 29/07/2026: xong Tuần 1–5 (Tuần 5 trừ phần cần GPU), tất cả đã ở `main`.
- Code hiện có: `backend/` (FastAPI + SQLAlchemy + Alembic; auth/RBAC/tenant, ingestion raw, pipeline D1–D5, facts + graph ≤2 hop, chunking/FTS/embedding, **BM25 tự cài**, retrieval R1–R3 + query router, dataset split + gold query + SFT builder + **SFT export sẵn sàng train**, model gateway + prompt có version + claim check + logging generations, **adapter registry + cấu hình C/D**, **vòng duyệt nội dung**) · `frontend/` (Next.js 15: login, `/projects`, `/data`, `/graph`, `/search`, `/studio`, `/review`, `/dataset`) · `training/` (gói QLoRA độc lập cho máy GPU).
- Dữ liệu trên PostgreSQL local (`docker compose up -d`): 4.795 tin raw · 4.794 tin sạch · 31.167 facts · graph 1.941 node / 2.653 cạnh · 9.656 chunk đã embed bằng `BAAI/bge-m3` · `dataset_v1` đã đóng băng · **108 gold query** (72 standard + 36 hard) · 1.500 mẫu SFT nháp · 50 bản ghi `generations` · **1 lượt `experiment_runs`** (`week6_frozen_ab`, 12 brief × A/B) · **0 nội dung trong vòng duyệt** (dữ liệu thử E2E đã xóa sạch sau khi kiểm).
- Thư mục `backend/models/adapters/` đang **trống** (chỉ có README) — đó là lý do cấu hình C/D chưa có số. Trọng số adapter cố ý không đưa vào git.
- Từ Tuần 6, mọi số thí nghiệm phải chạy qua `experiment_cli` chứ không phải `ab_cli`: nó ghi lại **snapshot** (commit git, model, prompt version, trọng số router, adapter fingerprint, kích thước split) vào bảng `experiment_runs`. Không có snapshot thì bảng số trong báo cáo không chứng minh được là chạy cùng điều kiện. `ab_cli` giữ lại để tái lập đúng số Tuần 4.
- Lệnh hay dùng (chạy trong `backend/`):
  - `python -m app.pipeline_cli --rebuild --report ..\docs\checkpoints\week_02_data_quality.md` — chạy lại D1–D5 khi đổi luật parser
  - `python -m app.index_cli` — chunk + FTS + embed bge-m3 trên GPU (~9 phút cho 9.656 chunk)
  - `python -m app.dataset_cli --build --eval --sweep` — split + gold query + SFT + data card + bảng R1–R3 + sweep trọng số
  - `python -m app.experiment_cli --briefs 12 --configs A,B,C,D --model Qwen/Qwen2.5-1.5B-Instruct --fp16 --k 3 --max-new-tokens 200` — **thí nghiệm đóng băng có snapshot**; thiếu adapter thì C/D bị bỏ qua kèm lý do, A/B vẫn ra số
  - `python -m app.experiment_cli --list` — liệt kê các lượt đã chạy; xem chi tiết ở `/experiments`
  - `python -m app.ab_cli --briefs 4 --k 3 --max-new-tokens 200` — bản Tuần 4, giữ để tái lập số cũ
  - `python -m app.sft_cli --out artifacts\sft` — xuất `train.jsonl`/`validation.jsonl` + thẻ dataset để mang sang máy GPU
  - Máy không GPU: thêm `--backend hashing` (index) và `--provider template` (sinh nội dung) — chỉ để pipeline chạy, **không dùng cho số liệu báo cáo**. Test tự động luôn chạy ở chế độ này (`tests/conftest.py`).
- Phụ thuộc nặng (torch/transformers/bitsandbytes/sentence-transformers) nằm ở `backend/requirements-ml.txt`, tách khỏi `requirements.txt` để CI không phải tải model.
- Môi trường: backend cổng **8001** (cổng 8000 bị `latcat.exe` chiếm), frontend 3000, tài khoản demo `admin@cancu.demo` / `cancu123`. GPU: GTX 1650 Ti 4GB, torch 2.6.0+cu124, CUDA hoạt động.
- Việc đầu tiên phiên tới: Tuần 7 theo `Plan/01` §6 — vision (VLM trích visual fact có confidence + UI xác nhận) + critic panel + ablation D+V. Phần này **không phụ thuộc adapter** nên làm được ngay. Ma trận A–D vẫn khuyết C/D cho tới khi Hải bàn giao adapter (mục 5-0); lúc đó chỉ cần chạy lại `experiment_cli` là điền đủ.
- Nhớ bật `docker compose up -d` trước mọi lệnh CLI — batch tối 28/07 chết vì Docker tắt trước tiến trình Python.
