# Checkpoint Tuần 5 — Điểm ghép QLoRA + vòng duyệt nội dung

**Ngày:** 29/07/2026 · **Branch:** `tuan-05-qlora-reviewer` · **Người thực hiện:** Quang (+ Claude hỗ trợ)

Artefact kèm theo: [hợp đồng bàn giao training](../../training/README.md) · [checkpoint Tuần 4](week_04_report.md)

> **Bối cảnh quyết định:** GPU máy phát triển (GTX 1650 Ti 4GB) không đủ fine-tune 7–8B, và
> việc thuê GPU chưa chốt. Thay vì chờ, Tuần 5 làm **toàn bộ phần không cần GPU** và định
> nghĩa sẵn điểm ghép, để khi Hải train xong ở máy khác/Colab thì chỉ copy thư mục adapter
> về là cấu hình C/D chạy — không sửa code, không chạy migration.

## Kết quả so với gate Tuần 5 ([Plan/01 §6](../../Plan/01_KE_HOACH_TONG_THE.md))

| Hạng mục gate | Trạng thái | Bằng chứng |
|---|---|---|
| Cấu hình C chạy được | ⏳ **hạ tầng xong, chờ adapter** | Đường đi C/D thông suốt end-to-end với adapter giả trong test; chưa có adapter thật vì chưa train |
| Adapter load độc lập | ✅ | `app/services/adapters.py` — quét thư mục, đọc `adapter_card.json`, kiểm tra file, vân tay SHA-256; `GET /api/generation/adapters` |
| Reviewer flow đầy đủ | ✅ | `/review` — nháp → gửi duyệt → duyệt/từ chối → xuất bản; version bất biến; RBAC theo vai trò |
| Editor / approve / reject | ✅ | Sửa tay tạo version mới và **bị chấm lại claim**; từ chối bắt buộc kèm lý do |
| Version + export | ✅ | Lịch sử phiên bản đầy đủ; xuất Markdown kèm khối truy vết (model, adapter, prompt, claim) |
| Pilot backbone → chốt model | ⏳ chưa | Cần GPU thuê; script pilot đã sẵn (`training/qlora_train.py` đổi `--base-model`) |
| Staging URL (carry-over T1) | ⏳ **chưa** | Vẫn chờ Anh chọn nền tảng cloud + cấp tài khoản |

## 1. Ma trận A–D đã đủ bốn ô

Trước Tuần 5 hệ thống chỉ chạy được A và B. Nay cả bốn cấu hình dùng chung một đường đi,
khác nhau đúng **hai biến** — bảng tra thay cho các nhánh `if` rải rác trong code:

| Cấu hình | Truy xuất | Adapter QLoRA |
|---|---|---|
| A — prompt-only | không | không |
| B — RAG | có | không |
| **C — QLoRA** | không | **có** |
| **D — RAG + QLoRA** | có | **có** |

Studio cho chọn **cặp so sánh** (A/B, C/D, A/C, B/D) thay vì cố định A/B — mỗi cặp cô lập
đúng một biến, đúng thiết kế thí nghiệm của [Plan/03 §2](../../Plan/03_KE_HOACH_THUC_NGHIEM.md).

Một chi tiết dễ sai đã được khóa lại: khi có adapter, **backbone lấy từ `adapter_card.json`
chứ không lấy từ cấu hình backend**. Adapter train trên Qwen-7B mà nạp lên Qwen-1.5B thì
transformers không báo lỗi — nó chạy và sinh ra văn rác. Sai lầm loại này rất khó phát hiện
khi đang vội, nên chặn bằng code chứ không bằng quy ước.

## 2. Hợp đồng bàn giao adapter

```
backend/models/adapters/<tên>/
    adapter_config.json          ← peft sinh
    adapter_model.safetensors    ← trọng số LoRA (vài chục MB)
    adapter_card.json            ← qlora_train.py sinh: backbone, siêu tham số, loss, phần cứng
```

Backend đọc thư mục này mỗi lần gọi API, nên **copy vào là dùng được ngay**, không cần
restart. Ba lớp bảo vệ:

1. **Thiếu file → nói rõ thiếu gì.** `GET /api/generation/adapters` trả cả adapter hỏng kèm
   lý do, thay vì im lặng bỏ qua khiến người bàn giao tưởng đã xong.
2. **Chạy C/D khi chưa có adapter → lỗi 400 có hướng dẫn**, chỉ đúng thư mục cần copy và
   trỏ tới `training/README.md`. Studio hiện cảnh báo ngay khi chọn cặp C/D.
3. **Vân tay SHA-256 của file trọng số** được ghi vào từng dòng `generations`. Cùng tên
   adapter nhưng train lại thì vân tay đổi, nên số cũ không bao giờ bị lẫn với số mới.

Adapter sinh từ `--smoke` (dữ liệu giả, dùng để kiểm tra môi trường GPU) bị đánh dấu và
backend cảnh báo — chặn khả năng lỡ tay đưa số của bản smoke vào báo cáo.

## 3. Vòng duyệt nội dung

Tách bảng có chủ đích: `generations` là **nhật ký thí nghiệm** (bất biến, ghi cả lần hỏng),
`content_items` + `content_versions` là **sản phẩm làm việc** (sửa được, nhiều phiên bản, có
người duyệt). Trộn hai thứ vào một bảng thì hoặc mất tính bất biến của log, hoặc không biên
tập được.

Bốn quy tắc được kiểm bằng test, không phải bằng quy ước:

| Quy tắc | Vì sao | Test |
|---|---|---|
| Version không bao giờ bị ghi đè | Bản đã duyệt phải truy được nguyên trạng | `test_sua_tay_tao_ban_moi_va_khong_dong_ban_cu` |
| **Sửa tay cũng bị chấm claim** | Chống bịa số phải chặn cả người, không chỉ model | `test_sua_tay_bi_cham_lai_claim` |
| Người viết không tự duyệt bài mình | Duyệt mà tự duyệt thì mất ý nghĩa | `test_nguoi_viet_khong_tu_duyet_bai_minh` |
| Từ chối phải kèm lý do | Người viết cần biết sửa gì | `test_tu_choi_phai_kem_ly_do` |
| Chỉ xuất bản nội dung đã duyệt | Hàng rào cuối trước khi ra thị trường | `test_api_khong_xuat_ban_duoc_khi_chua_duyet` |

Kiểm chứng trên trình duyệt thật: sinh bản B → gửi duyệt → sửa tay thêm câu *"Giá bán 999 tỷ,
chiết khấu 45%"* → hệ thống **bắt đúng hai số bịa** và tạo v2 trong khi v1 giữ nguyên → bấm
Từ chối không kèm lý do bị chặn → duyệt → xuất Markdown kèm khối truy vết.

## 4. Dataset SFT sẵn sàng train

`python -m app.sft_cli` xuất `train.jsonl` / `validation.jsonl` ở dạng `messages`, dựng bằng
**đúng prompt mà backend dùng lúc sinh nội dung** — nếu prompt lúc train khác lúc chạy thật
thì adapter học một định dạng rồi bị hỏi bằng định dạng khác.

Hai nguồn output, **đều là văn người viết** (không train model trên chính output của model):

- `listings` — mô tả gốc do người đăng tin viết, ghép với facts đã trích.
- `approved` — nội dung đã qua vòng duyệt trong hệ thống, phủ đủ 4 kênh × 3 persona.

**Bộ lọc chất lượng dùng chính claim checker:** mẫu nào có con số không truy được về fact thì
bị loại. Train nguyên xi lên mô tả người đăng chính là dạy model bịa số — bộ lọc này biến
công cụ đo thành công cụ làm sạch dữ liệu.

### 4.1. Kết quả đo thật (`dataset_v1`, ngưỡng 0 claim vô căn cứ)

| Bước lọc | Số tin |
|---|---:|
| Tin tier A/B, đại diện cụm | 3.191 |
| Loại vì thuộc split test | −552 |
| Loại vì mô tả quá ngắn/dài | −247 |
| **Loại vì chứa số không có trong facts** | **−2.155** |
| **Còn lại** | **237** (191 train · 46 validation · 130 dự án) |

Nới ngưỡng lên 0,34 được 397 mẫu — vẫn xa mục tiêu 800–1.500 của Plan/02 §7.

### 4.2. ⚠ Mô tả trong DataBDS bị crawler cắt cụt

Đo trên 4.795 tin raw: trung vị **166 ký tự**, p90 = 244, chỉ **228 tin (4,8%) đạt ≥300 ký tự**,
nhiều bản đứt giữa câu (`"...Nam Tư: 0772 011 Zalo Hỗ trợ xem nhà nhanh"`). Crawler lấy đoạn
preview chứ không lấy thân tin đầy đủ.

Hệ quả trực tiếp: kênh `description` đặt mục tiêu 180–260 **từ**, trong khi mẫu train chỉ
khoảng 30 từ. Model học được cách gắn dữ kiện và văn phong, **không học được độ dài yêu cầu**.

Ba hướng, phải chọn trước khi chốt cấu hình C:

1. **Hải crawl lại trường mô tả đầy đủ** — sửa tận gốc, tốn thời gian crawl lại.
2. Giữ nguyên và **hạ kỳ vọng độ dài trong báo cáo**, nêu rõ giới hạn dữ liệu.
3. Dồn sức vào nguồn `approved` — chất lượng cao nhưng phải review tay từng bài.

Khuyến nghị: (1) nếu crawler còn chạy được, (2) làm nền để không chặn tiến độ.

## 5. Kiểm chứng đã chạy

- **Tests:** 131/131 pass (thêm `test_adapters.py` 10 test, `test_content.py` 13 test).
- **Frontend:** `npx tsc --noEmit` sạch; `npm run build` ra 9 route (thêm `/review`).
- **E2E trình duyệt:** luồng ở §3, kèm kiểm tra cảnh báo "chưa có adapter" khi chọn cặp C/D.
- **Migration:** `804d7f4deca9` đã áp lên DB local (2 bảng mới + 2 cột adapter).
- **SFT export:** chạy thật trên `dataset_v1`, số liệu ở §4.1.

## 6. Cách chạy local

```powershell
docker compose up -d
cd backend
.\.venv\Scripts\alembic.exe upgrade head                 # content_items + content_versions
.\.venv\Scripts\python.exe -m app.sft_cli --out artifacts\sft
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
cd ..\frontend; npm run dev                               # /studio, /review
```

Máy GPU (Hải/Colab) chỉ cần `training/` — xem [training/README.md](../../training/README.md).

## 7. Hạn chế đã biết

| Hạn chế | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| **Chưa có adapter thật** | C/D mới chứng minh được đường đi, chưa có số | Hải train ở Colab/máy GPU, copy về theo hợp đồng §2 |
| Mô tả nguồn bị cắt cụt (§4.2) | Mẫu SFT ngắn hơn yêu cầu kênh | Crawl lại, hoặc hạ kỳ vọng và ghi rõ trong báo cáo |
| Chỉ 237 mẫu train ở ngưỡng khắt khe | Dưới mục tiêu 800–1.500 | Nới ngưỡng có kiểm soát + tích lũy nội dung đã duyệt |
| Nguồn `listings` chỉ phủ kênh `description` | 3 kênh còn lại chưa có mẫu người viết | Dồn từ nội dung đã duyệt trong `/review` |
| Nạp `peft` chưa chạy trên GPU thật | Rủi ro lỗi môi trường lúc bàn giao | `qlora_train.py --smoke` kiểm môi trường trước |

## 8. Carry-over sang Tuần 6

| Việc | Owner | Ghi chú |
|---|---|---|
| **Train adapter đầu tiên + bàn giao** | Hải | Theo `training/README.md`; smoke test trước |
| Deploy staging | Quang | Vẫn chờ Anh chọn nền tảng + cấp tài khoản |
| Quyết định về mô tả bị cắt cụt | Hải + Anh | Ba hướng ở §4.2 |
| Chạy frozen A–D + R1–R3, dashboard so sánh | Quang + Hải | Gate Tuần 6 |
| Human evaluation mù + chốt rater | Cả nhóm | Plan/03 §5 |
| Hard set gold query không nêu tên dự án | Hải | Carry-over từ Tuần 4 |
