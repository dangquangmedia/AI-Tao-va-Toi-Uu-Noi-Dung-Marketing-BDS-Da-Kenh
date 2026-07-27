# 02 — Kế hoạch dữ liệu (bám kho DataBDS thực tế)

> Tài liệu này là căn cứ "chứng minh data" của đồ án: hiện trạng kho dữ liệu đã crawl, kế hoạch làm sạch, phân bổ dữ liệu cho từng mục đích (Graph/RAG/SFT/benchmark) và cách chia tập chống leakage. Mọi con số bên dưới được đo bằng script trên dữ liệu thật ngày 27/07/2026, không ước lượng.
>
> Tài liệu liên quan: [01 — Kế hoạch tổng thể](01_KE_HOACH_TONG_THE.md) · [03 — Kế hoạch thực nghiệm](03_KE_HOACH_THUC_NGHIEM.md)

---

## 1. Hiện trạng kho dữ liệu `DataBDS/`

Crawl từ batdongsan.com.vn trong khoảng 17/07 → 25/07/2026, gồm 3 file:

| File | Nội dung | Quy mô |
|---|---|---|
| `listings.jsonl` | Bản ghi tin đăng đã parse (title, mô tả, giá, diện tích, phòng ngủ, hướng, pháp lý, project, người bán, ngày đăng/hết hạn…) | **4.795 tin** |
| `source_listing_202607251238.csv` | Bảng nguồn: `id`, `source`, `source_listing_id`, `canonical_url`, `first_seen_at`, `last_seen_at`, `status`, `content_hash` | 4.795 dòng |
| `listing_media_202607251238.csv` | Ảnh: `source_url`, `local_path`, `byte_size`, `downloaded`, `download_error` | **37.351 ảnh — 37.349 đã tải về local (99,99%)** |

### 1.1. Phân bố loại hình (100% tin bán — `transaction_type = sale`)

| Loại hình | Số tin | Tỷ lệ | Loại hình | Số tin | Tỷ lệ |
|---|---:|---:|---|---:|---:|
| apartment | 1.770 | 36,9% | project_land | 187 | 3,9% |
| private_house | 825 | 17,2% | shophouse | 122 | 2,5% |
| land | 780 | 16,3% | condotel | 45 | 0,9% |
| villa | 628 | 13,1% | warehouse | 32 | 0,7% |
| street_house | 392 | 8,2% | resort + other | 14 | 0,3% |

### 1.2. Độ đầy đủ và chất lượng trường dữ liệu

| Trường | Tình trạng | Tỷ lệ |
|---|---|---:|
| `title`, `description` | Sạch, dùng được | 100% |
| `area_m2` | Parse đúng | 99,6% (4.777) |
| `bedrooms` | Parse đúng | 66,9% (3.207) |
| `total_price_vnd` / `price_per_m2_vnd` | Parse được | **chỉ 31,6% (1.517)** |
| `price_raw` | Dính rác JS/boilerplate | 32,7% hỏng |
| `project_name` | **Dính rác text menu/navigation** | **~100% hỏng** |
| `legal_status` | Dính rác text menu | ~100% hỏng |
| `address_raw`, `seller_display_name` | Dính rác boilerplate | phần lớn hỏng |
| `canonical_url`, `content_hash`, timestamps | Sạch — nền tảng provenance | 100% |

**Chẩn đoán:** parser HTML bắt nhầm vùng DOM nên các trường "đọc từ trang chi tiết" dính rác; các trường số parse từ pattern cố định (diện tích) vẫn tốt. `title` + `description` + `canonical_url` sạch hoàn toàn → **đủ để khôi phục lại các trường hỏng bằng re-parse, không cần crawl lại**.

### 1.3. Khôi phục quan hệ tin ↔ dự án từ URL

URL batdongsan.com.vn chứa slug dự án (ví dụ `...vinhomes-ocean-park-gia-lam/...`). Thử nghiệm regex trên `canonical_url` khôi phục được:

- **816 project slug** khác nhau
- Phủ **1.919 tin** (chủ yếu apartment/condotel/shophouse thuộc dự án)
- Ví dụ top: Vinhomes Central Park (18), Vinhomes Smart City (16), Sunshine City (12), Mizuki Park (11), Masteri West Heights (10)…

Đây là **xương sống của Property Knowledge Graph và của việc chia split theo project**.

> **Cập nhật sau khi cài đặt D1 (Tuần 2):** con số 816/1.919 ở trên đến từ regex thăm dò lỏng, có lẫn tên phường bị hiểu nhầm thành dự án. Luật chính thức trong `backend/app/services/reparse.py` siết lại (chỉ nhận phần sau mã vùng dạng số) nên cho **347 dự án / 862 tin** — ít hơn nhưng không tạo entity giả. Nâng độ phủ bằng alias/dictionary ở Tuần 3. Số liệu đo thật: [docs/checkpoints/week_02_data_quality.md](../docs/checkpoints/week_02_data_quality.md).

## 2. Nguyên tắc phân tầng dữ liệu (4 tầng)

| Tầng | Nội dung | Nguồn |
|---|---|---|
| T1 — Dữ kiện dự án/tin đăng | Facts đã chuẩn hóa từ DataBDS + dữ liệu nhập tay được phép | DataBDS + upload |
| T2 — Dữ liệu thương hiệu | Brand voice, từ nên dùng/cấm, CTA, disclaimer | Nhóm tự xây cho brand demo |
| T3 — Dữ liệu SFT | Instruction/input/output đã review, liên kết facts–persona–kênh | Sinh từ T1+T2, review thủ công |
| T4 — Phản hồi | Sửa/duyệt/từ chối/rating của reviewer | Sinh trong quá trình dùng app |

## 3. Data contract v1 (khóa ở Tuần 1)

Pipeline AI chỉ nhận bản ghi đạt contract; bản ghi vi phạm vào quarantine kèm error code, không làm hỏng batch:

```json
{
  "source_id": "source_listing.id",
  "source_url": "canonical_url",
  "crawled_at": "last_detail_crawled_at",
  "content_hash": "sha256",
  "property_type": "apartment|villa|...",
  "project_slug": "tu-URL-hoac-null",
  "location": {"district": "...", "city": "...", "raw": "..."},
  "unit": {"area_m2": 70.5, "bedrooms": 2, "bathrooms": 2, "price_vnd": null, "price_confidence": "parsed|reparsed|missing"},
  "amenities": ["..."], "legal_facts": ["..."],
  "raw_title": "...", "raw_description": "...",
  "image_local_paths": ["data/images/..."],
  "parser_version": "reparse_v1"
}
```

Tiêu chí nghiệm thu: 100% bản ghi có `source_url` + `content_hash` + thời điểm crawl; không bản ghi nào thiếu cả `project_slug` lẫn location tối thiểu; đơn vị chuẩn hóa nhưng giữ raw value; có báo cáo tỷ lệ thiếu theo field.

## 4. Pipeline làm sạch 5 giai đoạn (Tuần 1–2)

```text
DataBDS (raw, không sửa)  →  D1 Re-parse  →  D2 Chuẩn hóa  →  D3 Dedup  →  D4 Canonical facts  →  D5 Graph
```

| GĐ | Việc | Chi tiết | Đầu ra |
|---|---|---|---|
| **D1** | Re-parse trường hỏng | Giá: regex trên `title`/`description` ("5 tỷ 100", "99tr/m²") đối chiếu `price_raw` đã lọc rác; project: slug từ `canonical_url` + đối chiếu mô tả; pháp lý: từ khóa trong description ("sổ hồng", "HĐMB"…); trường không khôi phục được → `null` + flag, **không suy diễn** | `listings_reparsed.jsonl` + báo cáo tỷ lệ khôi phục |
| **D2** | Chuẩn hóa | Unicode NFC tiếng Việt, whitespace, HTML entities, đơn vị (m², tỷ/triệu VND), chuẩn địa danh quận/thành phố | Bản ghi chuẩn hóa |
| **D3** | Dedup | Trùng chính xác theo `content_hash`; near-duplicate theo MinHash/SimHash trên description (cùng căn đăng nhiều lần) | Cụm dedup + đại diện cụm |
| **D4** | Canonical facts + provenance | Tách fact có schema; mỗi fact gắn `source_id`, trích đoạn, `parser_version`; fact không chắc → `confidence` + `needs_review` | Bảng `facts` trong PostgreSQL |
| **D5** | Graph deterministic | Entity resolution project slug → node `Project` (alias table); edges `PART_OF`, `HAS_UNIT_TYPE`, `LOCATED_IN`, `HAS_AMENITY` từ structured fields — ưu tiên hơn mọi quan hệ LLM-extracted | `graph_entities`, `graph_relationships` |

Quy tắc chung: **raw zone bất biến** — không sửa file gốc trong `DataBDS/`; mọi phép biến đổi có script + version để tái lập; chạy lại pipeline trên cùng batch không sinh duplicate (idempotent).

## 5. Phân bổ dữ liệu theo mục đích (3 tier)

| Tier | Phạm vi | Số lượng (ước tính từ số đo thật) | Dùng cho |
|---|---|---|---|
| **A — Lõi** | Tin gắn được project qua URL (apartment, condotel, shophouse thuộc dự án) | ~1.919 tin / 816 project + ảnh của chúng | **Property Knowledge Graph + hybrid RAG + SFT chính + frozen test.** Chỉ tier này có đủ cấu trúc Project → Building/UnitType để trả lời câu hỏi quan hệ (RQ6) |
| **B — Mở rộng** | villa, street_house, private_house, shophouse lẻ có description tốt (≥300 ký tự sau làm sạch) | ~1.800–2.200 tin (chốt sau D1–D3) | Corpus RAG mở rộng + đa dạng hóa SFT (nội dung nhà lẻ) + negative/distractor cho retrieval benchmark |
| **C — Phụ** | land, project_land, warehouse, resort, other | ~1.000 tin | Giữ trong raw zone làm dữ liệu phụ/thống kê; **không vào SFT chính** vì không phù hợp bài toán content marketing dự án |

Ảnh: 37.349 ảnh local map về tin qua `source_listing_fk` → tier theo tin. Vision extraction (Tuần 7) chỉ chạy trên **subset ảnh của project trong SFT/test** (ước ~3.000–5.000 ảnh) để kiểm soát chi phí; phần còn lại giữ làm kho.

## 6. Chia tập chống leakage (khóa ở Tuần 3)

Nguyên tắc quan trọng nhất về học thuật: **chia theo project, không random theo sample** — model không được "thấy" dự án của test trong train dưới bất kỳ dạng nào.

1. **Dedup chạy trước split** (D3), sau đó kiểm tra near-duplicate xuyên split lần cuối.
2. **Tier A:** chia 816 project theo tỷ lệ 70/15/15 → **~571 project train / ~122 validation / ~123 test**. Toàn bộ tin, ảnh, facts, SFT samples của một project chỉ thuộc đúng một split. Stratify theo quy mô project (số tin) để test không toàn dự án 1 tin.
3. **Tier B (tin lẻ không thuộc project):** chia theo cụm dedup (cả cụm vào cùng split), tỷ lệ 70/15/15.
4. **Test set gồm cả project đầy đủ facts lẫn project thiếu facts** để đo độ bền khi thiếu dữ liệu.
5. Split đóng băng thành `dataset_v1` với data card; **không thay tập test sau khi đã đánh giá** — mọi thay đổi tạo version mới.

## 7. Thiết kế SFT dataset (Tuần 3–5)

### 7.1. Schema mẫu (thống nhất toàn bộ)

```json
{
  "sample_id": "...", "project_id": "...",
  "instruction": "Tạo bài Facebook giới thiệu căn 2PN...",
  "facts": [{"fact_id": "...", "text": "...", "source_id": "..."}],
  "visual_facts": [{"image_id": "...", "text": "...", "confidence": 0.9}],
  "brand": {"tone": [], "required_terms": [], "forbidden_terms": []},
  "persona": {"segment": "young_family|investor|first_home", "needs": [], "objections": []},
  "channel": {"name": "description|facebook|email|landing_seo", "length": "...", "format_rules": []},
  "seo": {"primary_keyword": null, "secondary_keywords": []},
  "output": {"headline": "...", "body": "...", "cta": "..."},
  "claims": [{"claim": "...", "supported_by": ["fact_id"]}],
  "quality_status": "gold|silver|rejected", "reviewer_id": "..."
}
```

### 7.2. Quy mô và cân bằng

- Mục tiêu: **800–1.500 mẫu đã review**, cân bằng 4 kênh × 3 persona (young_family / investor / first_home).
- Nguồn: ưu tiên ~150–250 project Tier A có ≥2 tin và facts đầy đủ (giá + diện tích + tiện ích) sau D1; bổ sung Tier B cho nội dung nhà lẻ.
- Quy trình: draft synthetic từ facts thật (generator + template) → **review thủ công gắn `gold`/`silver`** → chỉ train trên gold/silver đã audit. Không bù số lượng bằng synthetic chưa duyệt.
- Mỗi claim trong `output` phải map về `fact_id` — mẫu có claim không căn cứ bị `rejected`.

## 8. Benchmark sets (khóa ở Tuần 3–4, chi tiết protocol ở [03](03_KE_HOACH_THUC_NGHIEM.md))

| Bộ | Quy mô | Thành phần |
|---|---|---|
| **Frozen generation test** | 40–60 briefs | Từ project test (held-out); cân bằng 4 kênh × 3 persona; mỗi brief chạy cùng seed/decoding trên A–D |
| **Retrieval benchmark R1–R3** | 60–90 queries | fact đơn / quan hệ 1-hop / 2-hop / so sánh 2 dự án / dữ liệu mâu thuẫn / dữ liệu hết hạn; gán relevance label thủ công |
| **Vision benchmark** | 200–300 ảnh | Ảnh test-project, gán nhãn room type + visible objects để đo precision của VLM extraction |

## 9. License, đạo đức và giới hạn dữ liệu

- Nguồn: tin đăng **công khai** trên batdongsan.com.vn; dữ liệu chỉ dùng cho mục đích nghiên cứu/đồ án, không tái phân phối dataset gốc, không dùng thương mại. Ghi rõ trong data card + chương đạo đức của báo cáo.
- Giữ nguyên `canonical_url` làm citation cho mọi fact — vừa là provenance kỹ thuật vừa là ghi công nguồn.
- **Không thu thập/suy luận PII:** trường `seller_display_name` (đã hỏng) sẽ bị **drop hoàn toàn** ở D1, số điện thoại trong description bị mask.
- Ảnh có watermark của nguồn: chỉ dùng trích xuất visual facts và minh họa demo, không dùng làm asset marketing thật.
- Tin `EXPIRED` (99,7% kho): hợp lệ cho nghiên cứu vì bài toán là sinh nội dung từ facts, không phải hiển thị tin còn hạn; ghi rõ `valid_from`/`valid_to` cho fact giá để tránh claim giá đã hết hiệu lực — đây chính là use case của temporal provenance trong thiết kế graph.
- Không tạo claim pháp lý/lợi nhuận/tiến độ khi nguồn không nêu (quy tắc `forbidden claims` trong critic).

## 10. Data card v1 (template — điền ở Tuần 3)

```markdown
# Data Card — dataset_v1
- Nguồn & thời gian crawl: batdongsan.com.vn, 17–25/07/2026
- Quy mô: X tin hợp lệ / 4.795 raw · Y project · Z ảnh
- Pipeline version: reparse_v1 + normalize_v1 + dedup_v1 (commit ...)
- Split: train/val/test theo project = A/B/C project (danh sách ID kèm theo)
- Tỷ lệ khôi phục field sau re-parse: giá ...% · project ...% · pháp lý ...%
- Leakage audit: phương pháp + kết quả near-dup xuyên split
- Giới hạn đã biết: ...
- License & điều kiện sử dụng: nghiên cứu, không tái phân phối
```

## 11. Việc dữ liệu theo tuần (đồng bộ với [01 §6](01_KE_HOACH_TONG_THE.md))

| Tuần | Việc dữ liệu | Owner |
|---|---|---|
| 1 | Audit DataBDS, khóa contract v1, spec re-parse D1 | Hải |
| 2 | Chạy D1–D5, data quality report, canonical facts + graph đầu tiên | Hải (rules) + Quang (pipeline) |
| 3 | Split + leakage audit, `dataset_v1` + data card, SFT draft, gold queries | Cả nhóm |
| 4 | Retrieval benchmark hoàn chỉnh, relevance labels | Hải |
| 5 | SFT gold/silver hoàn tất cho QLoRA | Hải |
| 7 | Vision benchmark labels | Hải |
| 8 | Data card final + reproducibility package | Cả nhóm |
