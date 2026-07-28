# Data Card — dataset_v1

> Sinh tự động bằng `python -m app.dataset_cli --build` lúc 28/07/2026 15:46. Mọi số liệu đo trực tiếp trên PostgreSQL.

## 1. Nguồn và quy mô

| Mục | Giá trị |
|---|---:|
| Nguồn | batdongsan.com.vn, crawl 17–25/07/2026 |
| Tin raw | 4.795 |
| Tin qua contract v1 | 4.794 |
| Dự án trong graph | 617 |
| Canonical facts | 31.167 |
| Chunk index | 9.656 (đã embed 9.656) |
| Embedding model | `BAAI/bge-m3` |
| Cụm dedup | 4.750 |

## 2. Độ phủ trường sau re-parse

| Trường | Số tin | Tỷ lệ |
|---|---:|---:|
| project_slug | 1.539 | 32.1% |
| ward | 4.793 | 100.0% |
| district | 907 | 18.9% |
| city | 1.366 | 28.5% |
| area_m2 | 4.776 | 99.6% |
| bedrooms | 3.206 | 66.9% |
| total_price_vnd | 2.519 | 52.5% |
| legal_facts | 1.382 | 28.8% |
| amenities | 1.620 | 33.8% |

## 3. Chia tập (theo dự án / cụm dedup, không random theo mẫu)

| Split | Đơn vị | % đơn vị | Tin | % tin |
|---|---:|---:|---:|---:|
| train | 2.665 | 69.3% | 3.303 | 68.9% |
| validation | 567 | 14.7% | 695 | 14.5% |
| test | 615 | 16.0% | 796 | 16.6% |

Đơn vị chia: dự án (Tier A) và cụm dedup (tin lẻ). Stratify theo quy mô dự án (large ≥5 tin · medium 2–4 · small 1) để test không toàn dự án một tin.

## 4. Leakage audit

- Tin được gán split: **4.794/4.794**
- Cụm dedup kiểm tra: 4.750 — nằm ở nhiều split: **0**
- Dự án kiểm tra: 617 — nằm ở nhiều split: **0**
- Kết luận: **ĐẠT — không có rò rỉ**

## 5. Gold retrieval queries

| Nhóm câu hỏi | Số query |
|---|---:|
| compare | 12 |
| conflict | 12 |
| fact | 12 |
| one_hop | 12 |
| temporal | 12 |
| two_hop | 12 |
| **Tổng** | **72** |

Sinh bằng template trên dữ liệu split test, nhãn suy ra tất định từ DB; toàn bộ đang ở trạng thái `needs_review` chờ soát tay trước khi khóa benchmark.

## 6. SFT draft v1

- Số mẫu nháp: **1.500**
- Theo split: {'train': 1252, 'validation': 248}
- Theo kênh: {'description': 363, 'landing_seo': 376, 'facebook': 378, 'email': 383}
- Theo persona: {'young_family': 500, 'investor': 542, 'first_home': 458}
- Bỏ qua do thiếu fact: 0
- Bỏ qua vì thuộc split test: 305

Mẫu mới có phần input (instruction + facts có provenance + brand + persona + kênh); `output` để trống, `quality_status = draft` — chờ sinh có kiểm soát và review gắn gold/silver ở Tuần 5. Không train trên mẫu chưa duyệt.

## 7. License và giới hạn

- Tin đăng công khai, chỉ dùng cho nghiên cứu/đồ án; không tái phân phối dataset gốc.
- Giữ `canonical_url` cho mọi fact làm provenance và ghi công nguồn.
- Không lưu PII: `seller_display_name` bị drop, số điện thoại trong mô tả bị mask.
- Phần lớn tin ở trạng thái EXPIRED → fact giá có `valid_from`/`valid_to`, không dùng để khẳng định giá hiện hành.
- Hạn chế đã biết: giá chỉ khôi phục được ~52%, mã tòa/block thưa, quận/huyện chưa suy đầy đủ từ phường.
