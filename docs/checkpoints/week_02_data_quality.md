# Báo cáo chất lượng dữ liệu sau pipeline D1–D5

> Sinh tự động bằng `python -m app.pipeline_cli --report` lúc 28/07/2026 15:37. Mọi con số đo trực tiếp trên PostgreSQL, không nhập tay.

## 1. Quy mô

| Chỉ số | Giá trị |
|---|---:|
| Tin trong raw zone | 4.795 |
| Tin qua được contract v1 (clean) | 4.794 |
| Bản ghi quarantine | 1 |
| Canonical facts | 31.167 |
| Fact cần review | 4.281 |
| Node graph | 1.941 |
| Cạnh graph | 2.653 |
| Cụm dedup | 4.750 |
| Tin bị coi là bản trùng | 44 |

## 2. Độ phủ trường sau re-parse

| Trường | Số tin có giá trị | Tỷ lệ |
|---|---:|---:|
| Dự án (từ canonical_url) | 1.539 | 32.1% |
| Mã tòa/block | 124 | 2.6% |
| Phường/xã (từ URL) | 4.793 | 100.0% |
| Quận/huyện | 907 | 18.9% |
| Tỉnh/thành | 1.366 | 28.5% |
| Diện tích | 4.776 | 99.6% |
| Số phòng ngủ | 3.206 | 66.9% |
| Giá tổng | 2.519 | 52.5% |
| Giá/m² | 249 | 5.2% |
| Pháp lý | 1.382 | 28.8% |
| Tiện ích | 1.620 | 33.8% |

## 3. Phân bố

**Theo tier (Plan/02 §5)**

| Giá trị | Số lượng |
|---|---:|
| B | 1.679 |
| C | 1.576 |
| A | 1.539 |

**Theo loại hình**

| Giá trị | Số lượng |
|---|---:|
| apartment | 1.769 |
| private_house | 825 |
| land | 780 |
| villa | 628 |
| street_house | 392 |
| project_land | 187 |
| shophouse | 122 |
| condotel | 45 |
| warehouse | 32 |
| resort | 7 |
| other | 7 |

**Theo độ tin của giá**

| Giá trị | Số lượng |
|---|---:|
| missing | 2.093 |
| reparsed | 1.755 |
| parsed | 946 |

## 4. Quarantine

**Theo mã lỗi**

| Giá trị | Số lượng |
|---|---:|
| no_project_no_location | 1 |

## 5. Facts và graph

**Fact theo predicate**

| Giá trị | Số lượng |
|---|---:|
| property_type | 4.794 |
| ward | 4.793 |
| area_m2 | 4.776 |
| bedrooms | 3.202 |
| bathrooms | 3.039 |
| total_price_vnd | 2.519 |
| amenity | 2.145 |
| legal_status | 1.714 |
| project | 1.539 |
| city | 1.366 |
| district | 907 |
| price_per_m2_vnd | 249 |
| building | 124 |

**Node theo loại**

| Giá trị | Số lượng |
|---|---:|
| UnitType | 958 |
| Project | 617 |
| Ward | 238 |
| Building | 56 |
| District | 43 |
| City | 16 |
| Amenity | 13 |

**Cạnh theo loại**

| Giá trị | Số lượng |
|---|---:|
| HAS_UNIT_TYPE | 1.016 |
| LOCATED_IN | 941 |
| HAS_AMENITY | 640 |
| PART_OF | 56 |

**Dự án nhiều tin nhất**

| Dự án | Slug | Số tin |
|---|---|---:|
| Vinhomes Central Park | `vinhomes-central-park` | 21 |
| S Light Tower | `s-light-tower` | 19 |
| Central Lakeside | `central-lakeside` | 16 |
| Sun Urban City | `sun-urban-city` | 15 |
| Mizuki Park | `mizuki-park` | 14 |
| Vinhomes Ocean Park | `vinhomes-ocean-park` | 13 |
| Green Skyline | `green-skyline` | 12 |
| Sunshine City | `sunshine-city` | 12 |
| Victoria Village | `victoria-village` | 12 |
| Noble Palace Tây Thăng Long | `noble-palace-tay-thang-long` | 11 |

## 6. Lần chạy pipeline gần nhất

- Job `8845c78f7fc04d45aa3a371c047bc37c` — trạng thái **done**
- Đọc 4.795 tin: thêm 4.794 · giữ nguyên 0 · cập nhật 0 · quarantine 1
- Chi tiết D3–D5: `{'clusters': 4750, 'duplicates': 44, 'facts_inserted': 31167, 'facts_deleted': 0, 'entities': 1941, 'entities_inserted': 1941, 'entities_deleted': 0, 'edges': 2653, 'edges_inserted': 2653, 'edges_deleted': 0}`

_Tỷ lệ tin sạch trên raw: 100.0%_
_Tỷ lệ đại diện cụm (sau dedup): 99.1%_
