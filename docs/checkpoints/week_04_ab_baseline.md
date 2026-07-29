# Baseline A vs B — sinh nội dung có/không RAG

> Sinh tự động bằng `python -m app.ab_cli` lúc 29/07/2026 09:35. Model `Qwen/Qwen2.5-1.5B-Instruct` (provider `local`), greedy decoding, cùng seed, cùng prompt version. Brief lấy từ dự án thuộc split test của `dataset_v1`.

## Tổng hợp

| Chỉ số | A (prompt-only) | B (RAG) |
|---|---:|---:|
| Số bài | 4 | 4 |
| Tỷ lệ claim không có căn cứ | 0.2042 | 0.0917 |
| Số claim trung bình mỗi bài | 5 | 5.25 |
| Bài có ít nhất 1 claim vô căn cứ | 4 | 2 |
| Câu chứa từ cấm | 0 | 0 |
| Độ dài thân bài (ký tự) | 574 | 559 |
| Thời gian sinh trung bình (giây) | 72.6 | 100.6 |

## Từng brief

| Dự án | Kênh | Persona | A: claim vô căn cứ | B: claim vô căn cứ | B: số fact |
|---|---|---|---:|---:|---:|
| sun-urban-city | description | young_family | 0.1667 | 0.0 | 12 |
| mizuki-park | facebook | investor | 0.2 | 0.1667 | 12 |
| the-beverly-vinhomes-grand-park | email | first_home | 0.25 | 0.2 | 12 |
| the-marq | landing_seo | young_family | 0.2 | 0.0 | 12 |

## Cách đọc

- `claim` = câu có chứa số liệu hoặc thuộc tính (giá, diện tích, phòng ngủ, pháp lý…).
- Một claim được coi là **có căn cứ** khi mọi con số trong câu đều xuất hiện trong facts đã truy xuất cho brief đó. Cả A và B đều chấm trên cùng tập fact tham chiếu — A không nhìn thấy facts, nhưng thước đo phải như nhau thì so sánh mới công bằng.
- Đây là chỉ số tự động (rule-based). Human evaluation mù theo Plan/03 §5 làm ở Tuần 6.
