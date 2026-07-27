# Báo cáo chất lượng dữ liệu sau pipeline D1–D5

> Sinh tự động bằng `python -m app.pipeline_cli --report` lúc 27/07/2026 23:32. Mọi con số đo trực tiếp trên PostgreSQL, không nhập tay.

## 1. Quy mô

| Chỉ số | Giá trị |
|---|---:|
| Tin trong raw zone | 4.795 |
| Tin qua được contract v1 (clean) | 4.794 |
| Bản ghi quarantine | 1 |
| Canonical facts | 30.820 |
| Fact cần review | 4.183 |
| Node graph | 1.102 |
| Cạnh graph | 1.535 |
| Cụm dedup | 4.750 |
| Tin bị coi là bản trùng | 44 |

## 2. Độ phủ trường sau re-parse

| Trường | Số tin có giá trị | Tỷ lệ |
|---|---:|---:|
| Dự án (từ canonical_url) | 862 | 18.0% |
| Mã tòa/block | 26 | 0.5% |
| Phường/xã (từ URL) | 4.792 | 100.0% |
| Quận/huyện | 907 | 18.9% |
| Tỉnh/thành | 1.795 | 37.4% |
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
| C | 2.110 |
| B | 1.822 |
| A | 862 |

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
| ward | 4.792 |
| area_m2 | 4.776 |
| bedrooms | 3.202 |
| bathrooms | 3.039 |
| total_price_vnd | 2.519 |
| amenity | 2.145 |
| city | 1.795 |
| legal_status | 1.714 |
| district | 907 |
| project | 862 |
| price_per_m2_vnd | 249 |
| building | 26 |

**Node theo loại**

| Giá trị | Số lượng |
|---|---:|
| UnitType | 542 |
| Project | 347 |
| Ward | 129 |
| District | 31 |
| Building | 24 |
| City | 16 |
| Amenity | 13 |

**Cạnh theo loại**

| Giá trị | Số lượng |
|---|---:|
| LOCATED_IN | 579 |
| HAS_UNIT_TYPE | 566 |
| HAS_AMENITY | 366 |
| PART_OF | 24 |

**Dự án nhiều tin nhất**

| Dự án | Slug | Số tin |
|---|---|---:|
| Vinhomes Central Park | `vinhomes-central-park` | 21 |
| Sun Urban City | `sun-urban-city` | 15 |
| Mizuki Park | `mizuki-park` | 14 |
| Vinhomes Ocean Park | `vinhomes-ocean-park` | 13 |
| Noble Palace Tay Thang Long | `noble-palace-tay-thang-long` | 11 |
| The Beverly Vinhomes Grand Park | `the-beverly-vinhomes-grand-park` | 11 |
| Thanh Xuan Valley | `thanh-xuan-valley` | 10 |
| Akari City Nam Long | `akari-city-nam-long` | 9 |
| Imperia Sky Park | `imperia-sky-park` | 9 |
| Khu Do Thi Nam Thang Long Ciputra | `khu-do-thi-nam-thang-long-ciputra` | 9 |

## 6. Lần chạy pipeline gần nhất

- Job `ee128573870540fc9b3f4539b698b1b7` — trạng thái **done**
- Đọc 4.795 tin: thêm 4.794 · giữ nguyên 0 · cập nhật 0 · quarantine 1
- Chi tiết D3–D5: `{'clusters': 4750, 'duplicates': 44, 'facts_inserted': 30820, 'facts_deleted': 0, 'entities': 1102, 'entities_inserted': 1102, 'entities_deleted': 0, 'edges': 1535, 'edges_inserted': 1535, 'edges_deleted': 0}`

_Tỷ lệ tin sạch trên raw: 100.0%_
_Tỷ lệ đại diện cụm (sau dedup): 99.1%_
