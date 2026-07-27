# 03 — Kế hoạch thực nghiệm và đánh giá

> Tài liệu này là căn cứ "chứng minh thuật toán + model" của đồ án: protocol thí nghiệm, lý do chọn model, metric, human evaluation, kiểm định thống kê và gói tái lập. Nguyên tắc xuyên suốt: **mọi ngưỡng và metric được khóa trước khi chạy thí nghiệm cuối; kết quả xấu vẫn báo cáo trung thực (negative result hợp lệ)**.
>
> Tài liệu liên quan: [01 — Kế hoạch tổng thể](01_KE_HOACH_TONG_THE.md) · [02 — Kế hoạch dữ liệu](02_KE_HOACH_DU_LIEU.md)

---

## 1. Giả thuyết và thiết kế thí nghiệm

**H1 (RQ1):** RAG tăng fact precision và giảm unsupported claim rate so với prompt-only (B > A, D > C).
**H2 (RQ2):** QLoRA SFT tăng channel/persona/brand fit so với model gốc (C > A, D > B).
**H3 (RQ3):** RAG + QLoRA cho composite tốt nhất (D > A, B, C).
**H4 (RQ6):** Graph + vector (R3) tăng evidence recall/path precision trên câu hỏi quan hệ so với vector thuần (R1), với latency chấp nhận được.
**H5–H6 (RQ4–RQ5, ablation nếu kịp):** vision facts và critic-refiner cải thiện tiêu chí tương ứng mà không tăng claim sai.

### Điều kiện kiểm soát (bắt buộc cho tính hợp lệ)

- Mọi cấu hình A–D dùng **cùng frozen test set** (40–60 briefs từ project held-out — [02 §8](02_KE_HOACH_DU_LIEU.md)), **cùng input, cùng decoding settings, cùng seed**.
- Prompt template khóa version; retrieval snapshot khóa version; thay đổi bất kỳ → tạo run mới, không ghi đè.
- Human rater **không biết output thuộc cấu hình nào** (blind, thứ tự xáo trộn).
- Metric và ngưỡng thành công khóa trong tài liệu này **trước** Tuần 6.

## 2. Ma trận thí nghiệm

### 2.1. Generation (chạy Tuần 6)

| ID | Retrieval | QLoRA | Trả lời |
|---|:---:|:---:|---|
| A | — | — | baseline |
| B | R3 | — | H1 |
| C | — | ✓ | H2 |
| D | R3 | ✓ | H3 |
| D+V / D+V+R | R3 | ✓ | H5/H6 — chỉ chạy nếu A–D hoàn tất (ablation Tuần 7) |

### 2.2. Retrieval (chạy Tuần 4, chốt lại Tuần 6)

| ID | Thành phần | Đo |
|---|---|---|
| R1 | pgvector + FTS + RRF | Recall@k, MRR, evidence recall |
| R2 | Graph traversal ≤2 hop (recursive CTE) | Path precision, entity recall |
| R3 | R1 + R2 hợp nhất bằng RRF | Toàn bộ + latency p50/p95 |

Benchmark: 60–90 queries có relevance label ([02 §8](02_KE_HOACH_DU_LIEU.md)), phân nhóm fact đơn / 1-hop / 2-hop / so sánh / mâu thuẫn / temporal — báo kết quả **theo từng nhóm**, vì kỳ vọng graph chỉ thắng ở nhóm quan hệ.

## 3. Lựa chọn model — có lý do, có pilot, không chọn theo cảm tính

| Thành phần | Ứng viên | Cách chốt |
|---|---|---|
| Embedding | `BAAI/bge-m3` (đa ngôn ngữ, văn bản dài, dense+sparse) | Benchmark trên 50–100 query tiếng Việt của chính dataset so với ≥1 ứng viên khác (vd `multilingual-e5-large`); chọn theo Recall@10/MRR |
| Generator nghiên cứu | Qwen3-8B (ứng viên đầu); 2–3 backbone 7B–8B khác trong pilot | Pilot 100–200 mẫu SFT: chất lượng tiếng Việt, structured output pass rate, VRAM, license → chọn 1 backbone chính thức (Tuần 5, Ngày 1–3) |
| Fine-tuning | QLoRA 4-bit, LoRA vào attention/projection | Search space: rank {8,16,32}, LR 1e-5→2e-4, epochs 2–4, seq len theo phân bố dữ liệu thật. Chọn theo **validation composite score**, không theo train loss |
| Số run | Tối thiểu 1 run chính + 2 run ngắn kiểm tra độ ổn định (3 seed nếu đủ GPU) | Báo cáo mean ± độ lệch giữa các seed |
| Generator demo | API OpenAI/Claude qua gateway | Chỉ phục vụ demo sản phẩm; **không** dùng thay kết quả thí nghiệm open model |
| LLM judge | Model độc lập với generator (khác họ model) | Judge không xem reference output khi chấm factuality; rubric cố định, khóa version |
| Vision | VLM API (structured extraction) | Schema hẹp: room type, visible objects, material/color + confidence; đo precision trên vision benchmark 200–300 ảnh |

Lưu cho mọi run: adapter, tokenizer, config, commit hash, dataset version, seed, log môi trường (đưa vào model card).

## 4. Metric tự động (khóa trước Tuần 6)

### 4.1. Chất lượng nội dung

| Metric | Định nghĩa | Cách đo |
|---|---|---|
| **Fact precision** | Claim được nguồn hỗ trợ / tổng claim kiểm chứng được | Claims[] trong output JSON map về fact_id; kiểm tra tự động + spot-check người |
| **Unsupported claim rate** | Claim không căn cứ / tổng claim | Như trên — đây là metric hallucination chính |
| **Constraint pass rate** | Đáp ứng length, format, CTA, required/forbidden terms | Rule engine |
| **Channel fit** | Đúng quy tắc từng kênh | Rule score + LLM judge rubric |
| **Persona/brand fit** | Phù hợp persona + giọng thương hiệu | LLM judge rubric cố định + human đối chiếu |
| **SEO checks** | Keyword coverage tự nhiên, title/meta length, heading structure | Checklist tự động — *không* trình bày như bằng chứng xếp hạng thật |
| **Structured output pass rate** | Output JSON hợp lệ theo contract | Schema validation |
| **Image-text alignment** | Entity/attribute trong output nằm trong visual facts đã xác nhận | So khớp tập hợp; CLIPScore chỉ là metric phụ |

**Không dùng BLEU/ROUGE làm metric chính** (nội dung marketing có nhiều đáp án hợp lệ — sẽ nói rõ khi hội đồng hỏi); BERTScore báo cáo phụ khi có reference.

### 4.2. Retrieval/Graph

Recall@k, MRR, evidence recall · relationship/path precision · unsupported-edge rate · tỷ lệ path có provenance đầy đủ · latency p50/p95 · token/cost mỗi query.

### 4.3. Hệ thống

Latency p50/p95 end-to-end, error rate, token/cost mỗi output — ghi tự động vào `generation_runs`.

## 5. Human evaluation (Tuần 6)

- **Rater:** 3 người nếu có thể, tối thiểu 2 + quy trình xử lý bất đồng (thảo luận hoặc rater thứ 3 phân xử). Chốt danh sách rater từ Tuần 3.
- **Protocol:** blind (ẩn tên cấu hình, xáo thứ tự) · Likert 1–5 cho factuality, naturalness, persuasiveness, channel fit, persona fit, brand fit · **pairwise preference** giữa A/B/C/D trên cùng brief (kết luận mạnh hơn điểm tuyệt đối).
- **Độ tin cậy:** báo cáo inter-rater agreement — Cohen's kappa (2 rater) hoặc Krippendorff's alpha (≥3 rater).
- **Kiểm định:** paired test trên cùng brief (Wilcoxon signed-rank cho Likert; sign/binomial test cho pairwise) + **effect size**, không chỉ báo trung bình. Ngưỡng ý nghĩa α = 0.05, ghi rõ số so sánh và hiệu chỉnh nếu test nhiều cặp.
- **LLM-as-judge** chỉ là evaluator phụ trợ; kết luận chính dựa trên human + metric tự động kiểm chứng được.

## 6. Ngưỡng thành công (khóa trước — không chỉnh sau để "làm đẹp")

| Tiêu chí | Ngưỡng |
|---|---|
| D giảm unsupported claim rate so với A | Giảm rõ rệt, có ý nghĩa thống kê |
| C/D tăng channel/persona/brand fit so với A/B | Tăng có ý nghĩa thống kê |
| Fact precision cấu hình production | ≥ 90% trên test nội bộ |
| Structured output pass rate | ≥ 95% |
| R3 so với R1 trên nhóm query quan hệ | Cải thiện evidence recall hoặc factuality; latency p95 trong ngưỡng demo công bố trước |
| Graph path đưa vào prompt production | 100% có `source_id`; edge chưa duyệt không dùng cho claim nhạy cảm |
| Web app | Uptime demo ổn định, không lỗi luồng chính, có URL online |

Không đạt ngưỡng → báo cáo trung thực + phân tích lỗi (error taxonomy); tuyệt đối không đổi test set hoặc metric sau khi thấy kết quả.

## 7. Gói tái lập (reproducibility package — Tuần 8)

1. **Version hóa toàn bộ:** dataset (`dataset_v1`…), model/adapter, prompt template, graph snapshot, retrieval config — mọi run ghi đủ 4 version này + seed.
2. **Script chạy lại:** một lệnh tái tạo bảng A–D và R1–R3 từ snapshot; kết quả trong báo cáo sinh từ script, không gõ tay.
3. **Model card:** backbone, config QLoRA, dataset version, seed, hạ tầng, kết quả validation, giới hạn.
4. **Data card:** theo template [02 §10](02_KE_HOACH_DU_LIEU.md).
5. **Experiment log:** MLflow/W&B export kèm báo cáo.
6. **Error taxonomy:** phân loại lỗi generation (claim sai, sai persona, vi phạm format…) và lỗi graph (merge sai, edge thiếu nguồn…) kèm ví dụ thật.

## 8. Lịch thực nghiệm (đồng bộ [01 §6](01_KE_HOACH_TONG_THE.md))

| Tuần | Việc thực nghiệm |
|---|---|
| 3 | Khóa gold queries; benchmark embedding (chốt bge-m3 hay thay thế) |
| 4 | Chạy R1–R3 lần đầu; baseline A/B trên subset; khóa prompt version |
| 5 | Pilot backbone → chốt generator; QLoRA main run; validation C |
| 6 | **Frozen run A–D + R1–R3 full; human evaluation mù; thống kê + effect size** |
| 7 | Ablation D+V (và D+V+R nếu kịp); vision precision benchmark |
| 8 | Đóng gói tái lập; sinh bảng/figure cuối từ script |
