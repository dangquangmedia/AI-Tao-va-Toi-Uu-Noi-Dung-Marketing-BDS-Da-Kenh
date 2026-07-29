# Thí nghiệm đóng băng `week6_frozen_ab`

> Frozen test A-D (Tuan 6) - 12 brief · dataset `dataset_v1` · 12 brief × 2 cấu hình · commit `5ac7912` · 2026-07-29T14:31:21+00:00.

## 1. Snapshot (điều kiện chạy)

| Thành phần | Giá trị |
|---|---|
| Commit | `5ac7912` |
| Dataset | `dataset_v1` — split {'validation': 567, 'train': 2665, 'test': 615} |
| Gold query | {'hard': 36, 'standard': 72} |
| Knowledge base | 9656 chunk (9656 đã embed) · 31167 fact · 2653 cạnh graph |
| Embedding | `BAAI/bge-m3` (backend `sentence-transformers`) |
| Model sinh | `Qwen/Qwen2.5-1.5B-Instruct` (provider `local`, seed 42, 4-bit False) |
| Prompt | `prompt_v1` |
| Trọng số RRF | `{'vector': 1.0, 'bm25': 0.6, 'graph': 0.3}` |
| Adapter | **chưa có** |

**Cấu hình bị bỏ qua:**

- `C`: chưa có adapter trong backend/models/adapters/ — xem training/README.md
- `D`: chưa có adapter trong backend/models/adapters/ — xem training/README.md

## 2. Kết quả theo cấu hình

| Chỉ số | A | B |
|---|---:|---:|
| Số bài chạy được | 12 | 12 |
| Tỷ lệ claim không có căn cứ | 0.1604 | 0.1747 |
| Bài có ≥1 claim vô căn cứ | 9 | 7 |
| Số claim mỗi bài | 5.5833 | 6.0833 |
| Câu chứa từ cấm | 0.0000 | 0.0000 |
| Đúng định dạng 3 phần | 0.5833 | 0.3333 |
| Đúng khoảng độ dài kênh | 0.0000 (4 bài) | 0.2500 (4 bài) |
| Số từ trung bình | 145.0833 | 121.5833 |
| Thời gian sinh (giây) | 31.2238 | 52.0951 |

## 3. So sánh từng cặp (bắt cặp theo brief)

Mỗi cặp chỉ khác **một biến**. `p` từ kiểm định hoán vị bắt cặp; `dz` là cỡ hiệu ứng Cohen cho thiết kế bắt cặp; khoảng tin cậy 95% từ bootstrap 10.000 lần, seed 42. Cột **số cặp** có thể nhỏ hơn số brief: cặp nào một bên không đo được chỉ số đó (ví dụ bài bị cắt vì hết token) thì bị loại khỏi phép so, không thay bằng 0.

| Cặp | Biến đổi | Chỉ số | Số cặp | Trước | Sau | Chênh lệch | KTC 95% | Thắng/Thua | dz | p |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| A→B | retrieval | Tỷ lệ claim không có căn cứ | 12 | 0.1604 | 0.1747 | 0.0142 | [-0.1106; 0.138] | 6/5 | 0.0620 | 0.8525 |
| A→B | retrieval | Đúng định dạng 3 phần | 12 | 0.5833 | 0.3333 | -0.2500 | [-0.5; 0.0] | 0/3 | -0.5530 | 0.2500 |
| A→B | retrieval | Đúng khoảng độ dài của kênh | 3 | 0.0000 | 0.0000 | 0.0000 | [0.0; 0.0] | 0/0 | — | 1.0000 |
| A→B | retrieval | Số claim mỗi bài | 12 | 5.5833 | 6.0833 | 0.5000 | [-0.8333; 2.0] | 5/4 | 0.1840 | 0.6484 |

**Cách đọc:** n = 12 brief. Kiểm định hoán vị với n nhỏ chỉ đạt được p tối thiểu 1/2^n = 0.0002 — với n dưới ~10 thì *không thể* đạt p < 0,05 dù chênh lệch lớn đến đâu, nên cột p ở cỡ mẫu nhỏ chỉ để tham chiếu, chưa phải bằng chứng thống kê. Kết luận chỉ được rút khi chạy đủ cỡ mẫu của Plan/03 §4 (40–60 brief).
