# Kế hoạch triển khai ĐATN

## AI tạo và tối ưu nội dung marketing bất động sản đa kênh

**Thời gian:** 15/07/2026 - 23/09/2026  
**Phạm vi triển khai chính:** 8 tuần (15/07 - 08/09/2026)  
**Định vị:** Hệ thống sinh nội dung marketing BĐS đa phương thức, có truy xuất dữ liệu làm căn cứ, điều khiển theo thương hiệu/persona/kênh và đánh giá thực nghiệm.

---

## 1. Quyết định phạm vi

### 1.1. Lõi sản phẩm bắt buộc

Web app online cho phép:

1. Đăng nhập và phân quyền `admin`, `marketer/editor`, `reviewer`.
2. Quản lý dự án BĐS, loại căn, tài liệu, ảnh, brand guideline và persona.
3. Tạo bốn loại nội dung:
   - mô tả dự án/căn hộ;
   - bài Facebook;
   - email nurturing;
   - nội dung landing page SEO.
4. Hiển thị nguồn/facts đã dùng để tạo nội dung.
5. Tự động kiểm tra claim, ràng buộc kênh, giọng thương hiệu và SEO cơ bản.
6. Cho phép sửa, duyệt, từ chối, lưu phiên bản và export.
7. Có màn hình so sánh kết quả của bốn cấu hình nghiên cứu.

### 1.2. Không đưa vào MVP

- Không huấn luyện foundation model từ đầu.
- Không fine-tune vision model trong giai đoạn chính.
- Không tự đăng nội dung lên Facebook/email platform.
- Không cam kết A/B test online bằng CTR thật nếu chưa có traffic.
- Không xử lý video hoàn chỉnh; video tour script là stretch goal.
- Không đưa DPO vào đường găng. Chỉ làm nếu SFT, RAG, app và đánh giá đã ổn định.

### 1.3. Đóng góp học thuật chốt

1. Bộ dữ liệu tiếng Việt có cấu trúc cho sinh nội dung marketing BĐS đa kênh.
2. Cơ chế sinh có kiểm soát theo `facts + brand + persona + channel + visual evidence`.
3. So sánh có kiểm soát bốn cấu hình:
   - A: Prompt-only;
   - B: RAG;
   - C: Fine-tuned model;
   - D: RAG + fine-tuned model.
4. Benchmark đa tiêu chí: factuality, hallucination, channel fit, persona fit, brand consistency, SEO, image-text alignment và human preference.

**Giả thuyết chính:** RAG chủ yếu cải thiện độ đúng dữ kiện; QLoRA chủ yếu cải thiện khả năng tuân thủ phong cách/cấu trúc; kết hợp hai kỹ thuật cho kết quả tổng thể tốt nhất.

---

## 2. Câu hỏi nghiên cứu

- **RQ1:** RAG có làm tăng tỷ lệ claim được hỗ trợ bởi dữ liệu nguồn và giảm hallucination so với prompt-only không?
- **RQ2:** QLoRA SFT có làm tăng channel fit, persona fit và brand consistency so với model gốc không?
- **RQ3:** RAG + fine-tuned model có tốt hơn từng kỹ thuật riêng lẻ không?
- **RQ4:** Bổ sung visual facts từ ảnh có cải thiện độ phù hợp ảnh - nội dung mà không làm tăng claim sai không?
- **RQ5:** Critic-refiner một vòng có cải thiện tỷ lệ vượt ràng buộc so với bản nháp đầu với chi phí/độ trễ chấp nhận được không?
- **RQ6:** PostgreSQL Property Knowledge Graph + hybrid vector RAG có cải thiện truy xuất câu hỏi quan hệ nhiều bước và khả năng giải thích so với hybrid vector RAG thuần không?
- **RQ7 (nghiên cứu mở rộng):** Microsoft GraphRAG Local/Global Search có cải thiện chất lượng câu hỏi khám phá hoặc tổng hợp toàn corpus đủ để bù chi phí index và độ trễ không?

Các câu hỏi và metric phải được khóa trước khi chạy thí nghiệm cuối để tránh chọn metric theo kết quả.

---

## 3. Nguồn dữ liệu và ranh giới công việc crawl

### 3.1. Các tầng dữ liệu

**Tầng 1 - dữ kiện dự án:** dữ liệu crawler của Hải từ nguồn công khai/được phép, brochure và dữ liệu nhập tay. Bao gồm tên dự án, vị trí, loại căn, diện tích, phòng ngủ, giá, tiện ích, pháp lý, mô tả, ảnh và URL nguồn.

**Tầng 2 - dữ liệu thương hiệu:** brand voice, từ nên dùng, từ cấm, CTA, thông điệp chính, disclaimer và quy tắc compliance. Đây là dữ liệu do nhóm tự xây dựng cho từng brand demo.

**Tầng 3 - dữ liệu gán nhãn/SFT:** nội dung marketing được biên tập hoặc duyệt thủ công, liên kết rõ với facts, persona và kênh. Có thể dùng synthetic draft nhưng bắt buộc review trước khi đưa vào tập `gold`.

**Tầng 4 - phản hồi:** bản user sửa, accept/reject, rating và lý do. Dữ liệu này phục vụ phân tích và có thể tạo preference pairs sau MVP.

### 3.2. Data contract Hải bàn giao

Crawler là module độc lập. Pipeline AI chỉ nhận bản ghi đạt contract sau:

```json
{
  "source_id": "stable-id",
  "source_url": "https://...",
  "crawled_at": "ISO-8601",
  "license_or_permission": "public/permission/note",
  "project_name": "...",
  "property_type": "apartment",
  "location": {
    "address": "...",
    "district": "...",
    "city": "...",
    "latitude": null,
    "longitude": null
  },
  "unit": {
    "unit_type": "2PN",
    "area_m2": 70.5,
    "bedrooms": 2,
    "bathrooms": 2,
    "price_vnd": null
  },
  "amenities": ["..."],
  "legal_facts": ["..."],
  "raw_title": "...",
  "raw_description": "...",
  "image_urls": ["..."],
  "content_hash": "sha256",
  "parser_version": "..."
}
```

### 3.3. Tiêu chí nghiệm thu dữ liệu crawl

- 100% bản ghi có `source_url`, thời điểm crawl và hash.
- Không có bản ghi thiếu tên dự án và location ở mức tối thiểu.
- Đơn vị diện tích/giá được chuẩn hóa nhưng vẫn giữ raw value.
- Có báo cáo tỷ lệ thiếu theo từng field.
- Dedup theo URL, hash nội dung và near-duplicate text.
- Ảnh lưu kèm quan hệ với đúng project/unit và trạng thái tải.
- Có danh sách nguồn được phép dùng và nguồn bị loại.

Phần của Hải dừng ở raw/normalized dataset. Pipeline AI chịu trách nhiệm validation lần hai, tạo knowledge chunks, SFT samples và benchmark splits.

---

## 4. Pipeline xử lý dữ liệu

```text
Crawler/Upload
    -> Raw zone (không sửa dữ liệu gốc)
    -> Validation + normalization
    -> Dedup + quality flags
    -> Canonical project facts
    -> Document chunks + embeddings
    -> SFT/benchmark builder
    -> Train/validation/test theo project
```

### 4.1. Các bước ETL bắt buộc

1. Lưu raw JSON/HTML metadata để truy vết.
2. Chuẩn Unicode tiếng Việt, whitespace, HTML và đơn vị.
3. Tách fact có schema; fact không chắc chắn phải có `confidence` và `needs_review`.
4. Loại trùng chính xác và gần trùng.
5. Gắn provenance cho từng fact: source, đoạn trích, thời gian và parser version.
6. Không tự suy diễn giá, pháp lý, khoảng cách hoặc tiện ích nếu nguồn không nêu.
7. Snapshot dataset theo version; không thay tập test sau khi đã đánh giá.

### 4.2. Chia dữ liệu chống leakage

- Chia theo **project**, không random theo content sample.
- Gợi ý tỷ lệ: 70% project train, 15% validation, 15% test.
- Cùng một project và các biến thể nội dung của nó chỉ thuộc một split.
- Tập test gồm cả project đầy đủ và project có dữ kiện thiếu để kiểm tra độ bền.
- Dedup phải chạy trước khi split, sau đó kiểm tra near-duplicate xuyên split.

### 4.3. Dataset SFT

Mỗi mẫu dùng schema thống nhất:

```json
{
  "sample_id": "...",
  "project_id": "...",
  "instruction": "Tạo bài Facebook...",
  "facts": [{"fact_id": "...", "text": "...", "source_id": "..."}],
  "visual_facts": [{"image_id": "...", "text": "...", "confidence": 0.0}],
  "brand": {"tone": [], "required_terms": [], "forbidden_terms": []},
  "persona": {"segment": "young_family", "needs": [], "objections": []},
  "channel": {"name": "facebook", "length": "...", "format_rules": []},
  "seo": {"primary_keyword": null, "secondary_keywords": []},
  "output": {"headline": "...", "body": "...", "cta": "..."},
  "claims": [{"claim": "...", "supported_by": ["fact_id"]}],
  "quality_status": "gold|silver|rejected",
  "reviewer_id": "..."
}
```

Mục tiêu khả thi trong 8 tuần: 800-1.500 mẫu đã kiểm tra, cân bằng theo bốn kênh và ba persona. Nếu không đủ mẫu gold, chỉ train trên phần gold/silver đã audit; không bù số lượng bằng dữ liệu synthetic chưa duyệt.

---

## 5. Kiến trúc AI chốt

### 5.1. Phân vai model

- **Vision extractor:** model/API đa phương thức có sẵn, chỉ xuất object/tags nhìn thấy được; không dùng để suy đoán pháp lý, vị trí, chất lượng sống hoặc giá.
- **Embedding:** `BAAI/bge-m3` là ứng viên mặc định vì hỗ trợ đa ngôn ngữ, văn bản dài và retrieval dense/sparse. Vẫn phải benchmark trên 50-100 query tiếng Việt của chính dataset.
- **Generator nghiên cứu:** shortlist model instruction 7B-8B; ứng viên đầu là Qwen3-8B. Chọn chính thức bằng pilot tiếng Việt, license, VRAM, structured output và khả năng chạy QLoRA.
- **Generator sản phẩm:** có thể dùng API OpenAI/Claude để demo ổn định. Không dùng kết quả API thay cho thí nghiệm fine-tuning open model.
- **Critic:** rule engine + một LLM judge độc lập. Critic không được xem reference output khi chấm factuality.

### 5.2. Nguyên tắc học thuật

- Facts thay đổi theo dự án nằm trong RAG.
- Style, format, persona conditioning và hành vi từ chối claim thiếu căn cứ được học bằng SFT.
- Vision tạo `visual_facts`; generator chỉ dùng các facts này khi có confidence đạt ngưỡng hoặc đã được người dùng xác nhận.
- Tất cả cấu hình thí nghiệm dùng cùng input, decoding settings và test set.

### 5.3. RAG pipeline

1. Filter theo `tenant_id`, `project_id`, loại tài liệu và version.
2. Query router phân loại yêu cầu thành fact đơn, quan hệ, tổng hợp toàn corpus hoặc mixed.
3. Hybrid retrieval: PostgreSQL full-text search + dense vector.
4. Với câu hỏi quan hệ, tìm entity gốc rồi traverse Property Knowledge Graph tối đa 2 hop.
5. Hợp nhất kết quả vector và graph bằng Reciprocal Rank Fusion hoặc rule score có version.
6. Rerank top candidates nếu latency cho phép.
7. Trả top-k chunks, graph paths và claims kèm `fact_id`, `source_id`, score và thời gian hiệu lực.
8. Xây prompt chỉ từ facts/relationships có nguồn và còn hiệu lực.
9. Generator trả structured JSON và mapping claim -> fact/relationship.

Với quy mô đồ án, PostgreSQL + pgvector vừa lưu transactional data, vector, node và edge. Bắt đầu exact vector search và recursive CTE tối đa 2 hop; chỉ bật HNSW hoặc thêm graph database riêng khi benchmark chứng minh cần thiết.

### 5.4. Property Knowledge Graph lõi production

Graph production sử dụng ontology cố định, không cho LLM tự do phát minh loại entity/relationship.

**Node MVP:** `Developer`, `Project`, `Zone`, `Building`, `UnitType`, `Amenity`, `Location`, `Transport`, `Persona`, `BrandRule`, `Claim`, `Source`, `DocumentChunk`, `Image`.

**Edge MVP:** `DEVELOPS`, `PART_OF`, `HAS_BUILDING`, `HAS_UNIT_TYPE`, `LOCATED_IN`, `NEAR`, `HAS_AMENITY`, `CONNECTED_BY`, `SUITABLE_FOR`, `SUPPORTED_BY`, `CONTRADICTS`, `MENTIONED_IN`, `DEPICTS`.

Mỗi node/edge AI trích xuất bắt buộc có:

```json
{
  "tenant_id": "...",
  "source_id": "...",
  "confidence": 0.0,
  "extraction_method": "deterministic|llm|human",
  "review_status": "pending|verified|rejected",
  "valid_from": null,
  "valid_to": null,
  "extractor_version": "..."
}
```

Quy tắc:

- Quan hệ cấu trúc từ crawler/schema được ưu tiên hơn quan hệ LLM-extracted.
- Giá, khuyến mãi, tiến độ và chính sách phải là record có thời gian hiệu lực, không ghi đè giá trị cũ.
- `SUITABLE_FOR` là suy luận marketing, không phải fact khách quan.
- `NEAR` chỉ được dùng khi có nguồn hoặc phép đo; lưu khoảng cách, phương thức di chuyển và cách đo nếu có.
- Graph traversal production giới hạn tối đa 2 hop để kiểm soát latency và semantic drift.
- Context luôn chứa source evidence; graph path một mình không đủ để cho phép generator tạo claim.

### 5.5. Microsoft GraphRAG lớp nghiên cứu

Microsoft GraphRAG chạy trong sandbox/batch trên một corpus con đại diện cho một dự án lớn. Nó không nằm trên đường request production và không là dependency của web app.

Mục tiêu nghiên cứu:

1. Dùng Local Search cho câu hỏi entity-centric và quan hệ chưa biết trước.
2. Dùng Global Search cho câu hỏi tổng hợp toàn dự án/hệ sinh thái.
3. So sánh với hybrid vector RAG và Property Knowledge Graph có ontology.
4. Đo chất lượng, indexing cost, query cost, latency và lỗi entity/relationship extraction.

**Gate tiếp tục:** chỉ tích hợp một endpoint discovery riêng nếu hết Tuần 5, Microsoft GraphRAG cải thiện rõ global-query score trên bộ test khóa trước và không ảnh hưởng tiến độ A-D. Nếu không đạt, giữ kết quả như negative/ablation study trong báo cáo.

### 5.6. Vision pipeline

```text
Upload ảnh -> kiểm tra file -> VLM structured extraction
-> room/scene type + visible objects + material/color + confidence
-> human confirm/edit -> lưu visual facts -> đưa vào retrieval/generation
```

Không cho phép các claim như “view vĩnh viễn”, “vật liệu cao cấp”, “gần trung tâm” chỉ dựa vào ảnh.

### 5.7. QLoRA SFT

1. Pilot 100-200 mẫu trên 2-3 backbone, không chọn model theo cảm tính.
2. Chuẩn hóa chat template và output JSON.
3. Quantization 4-bit, LoRA adapter vào attention/projection modules phù hợp.
4. Chạy tối thiểu 3 seed hoặc, nếu tài nguyên hạn chế, 1 run chính + 2 run ngắn kiểm tra độ ổn định.
5. Theo dõi train/validation loss và metric task-level; early stopping theo validation.
6. Lưu adapter, tokenizer, config, commit hash, dataset version, seed và log môi trường.
7. Test adapter trên project chưa thấy trong train.

Hyperparameter không khóa cứng trước pilot. Phạm vi tìm kiếm ban đầu: rank 8/16/32, learning rate 1e-5 đến 2e-4, 2-4 epochs, sequence length theo phân bố dữ liệu thực. Chọn bằng validation composite score, không chọn bằng train loss.

---

## 6. Luồng chạy cốt lõi

```text
User đăng nhập
 -> tạo/chọn project
 -> nhập facts, brand, persona, SEO brief và ảnh
 -> validate + vision extraction + user xác nhận
 -> entity resolution + index chunks + upsert knowledge graph
 -> chọn channel và cấu hình model
 -> query router
 -> hybrid vector retrieval + graph traversal tối đa 2 hop
 -> context assembler trả chunks + graph paths + provenance
 -> generator tạo JSON draft + claim/relationship citations
 -> critic chấm rule/factuality/style/SEO
 -> refine tối đa 1 vòng nếu dưới ngưỡng
 -> reviewer sửa/duyệt/từ chối
 -> lưu version, feedback, latency, token/cost và nguồn
 -> export
```

### 6.1. Trạng thái nội dung

`draft -> generated -> needs_review -> approved/rejected -> exported`

Mọi lần chỉnh sửa tạo version mới. Không ghi đè output cũ vì dữ liệu versioning là bằng chứng đánh giá và nguồn tạo preference pairs.

### 6.2. Output contract

Generator trả JSON gồm tối thiểu:

- `headline`, `body`, `cta`;
- `channel`, `persona`, `tone`;
- `keywords_used`;
- `claims[]` với `supported_fact_ids[]`;
- `warnings[]`;
- `model_config_id`, `prompt_version`, `knowledge_snapshot_id`.

Nếu không có fact hỗ trợ, model phải bỏ claim hoặc đặt cảnh báo, không tự bổ sung.

---

## 7. Kiến trúc phần mềm

### 7.1. Stack đề xuất

- Frontend: Next.js, TypeScript, component library thống nhất.
- Backend: FastAPI, Pydantic, SQLAlchemy/Alembic.
- Database: PostgreSQL + pgvector.
- Object storage: S3-compatible storage cho ảnh/tài liệu.
- Background jobs: Redis + worker khi caption/index/generation lâu; MVP có thể dùng background task nhưng phải có job status.
- Training/evaluation: Python, Transformers, PEFT, TRL, bitsandbytes, MLflow hoặc Weights & Biases.
- Deploy: frontend managed hosting; FastAPI/worker bằng container; managed Postgres; CI/CD từ Git.

### 7.2. Module backend

- `auth/rbac`
- `users/tenants`
- `projects/units/assets`
- `brands/personas/campaigns`
- `ingestion/normalization`
- `vision`
- `retrieval`
- `knowledge_graph/entity_resolution`
- `knowledge_graph/traversal`
- `graphrag_research`
- `generation`
- `evaluation`
- `content_versions/reviews`
- `experiments/audit_logs`

### 7.3. Entity dữ liệu chính

`users`, `roles`, `projects`, `units`, `sources`, `facts`, `assets`, `visual_facts`, `brand_profiles`, `personas`, `campaigns`, `knowledge_chunks`, `graph_entities`, `graph_entity_aliases`, `graph_relationships`, `graph_claims`, `content_items`, `content_versions`, `reviews`, `generation_runs`, `experiment_configs`, `evaluation_scores`.

Mọi bảng nghiệp vụ có `tenant_id`; API kiểm tra quyền ở backend, không chỉ ẩn nút trên frontend.

### 7.4. Màn hình MVP

1. Login / quản lý user.
2. Dashboard dự án.
3. Project detail: facts, units, sources, assets.
4. Brand & persona editor.
5. Content studio: channel, brief, SEO, generate.
6. Evidence panel: facts/chunks/ảnh được dùng.
   - Hiển thị thêm đường đi giải thích, ví dụ `Căn 2PN -> thuộc Tòa S2 -> gần Vinschool`.
7. Editor + review + version history.
8. Experiment comparison dashboard.
9. Admin: user, model config, prompt version và audit log.

---

## 8. Thiết kế đánh giá

### 8.1. Ma trận thí nghiệm chính

| ID | Retrieval | Fine-tuned | Vision facts | Critic-refiner |
|---|---:|---:|---:|---:|
| A | Không | Không | Không | Không |
| B | Có | Không | Không | Không |
| C | Không | Có | Không | Không |
| D | Có | Có | Không | Không |
| D+V | Có | Có | Có | Không |
| D+V+R | Có | Có | Có | Có |

Bốn dòng A-D là bắt buộc theo DCDATN. Hai dòng cuối là ablation mở rộng nếu tiến độ cho phép.

### 8.2. Ma trận thí nghiệm retrieval/graph

| ID | Vector/FTS | Property Graph | Microsoft communities | Mục tiêu |
|---|---:|---:|---:|---|
| R1 | Có | Không | Không | Baseline fact/chunk retrieval |
| R2 | Không | Có | Không | Đo graph-only và chất lượng path |
| R3 | Có | Có | Không | Cấu hình production chốt |
| R4 | Có | Không | Có | Microsoft GraphRAG Local/Global research |

R1-R3 là thí nghiệm bắt buộc nhưng dùng bộ query retrieval nhỏ nên không làm phình ma trận generation A-D. R4 là nghiên cứu có gate; không đạt gate vẫn báo cáo như negative result.

### 8.3. Test set

- 40-60 briefs từ project chưa xuất hiện trong train.
- Cân bằng bốn kênh và ba persona.
- Mỗi brief chạy cùng seed/decoding policy ở các cấu hình.
- Ẩn tên cấu hình khi human review.
- Lưu nguyên prompt, retrieval result, output và evaluator version.
- Tạo thêm 60-90 retrieval queries gồm fact đơn, 1-hop, 2-hop, so sánh, global summary, dữ liệu mâu thuẫn và dữ liệu hết hạn.

### 8.4. Metric tự động

- **Fact precision:** số claim được nguồn hỗ trợ / tổng claim kiểm chứng được.
- **Unsupported claim rate:** claim không có căn cứ / tổng claim.
- **Constraint pass rate:** tỷ lệ đáp ứng length, format, CTA, required/forbidden terms.
- **Channel fit:** rule score + judge rubric theo từng kênh.
- **Persona/brand fit:** LLM judge theo rubric cố định, kết hợp human review.
- **SEO:** keyword coverage tự nhiên, title/meta length, heading structure; không dùng “SEO score” như bằng chứng xếp hạng thật.
- **Image-text alignment:** kiểm tra entity/attribute trong output có nằm trong visual facts; CLIPScore chỉ là metric phụ.
- **System:** latency p50/p95, error rate, token/cost mỗi output.
- **Graph:** entity recall, relationship/path precision, evidence recall, unsupported-edge rate và tỷ lệ path có provenance đầy đủ.
- **GraphRAG research:** indexing token/cost/time, query token/cost/latency và global-query comprehensiveness.

Không dùng BLEU/ROUGE làm metric chính vì nội dung marketing có nhiều đáp án hợp lệ. BERTScore có thể báo cáo phụ khi có reference.

### 8.5. Human evaluation

- 3 người chấm nếu có thể; tối thiểu 2 người và xử lý bất đồng.
- Thang Likert 1-5 cho factuality, naturalness, persuasiveness, channel fit, persona fit và brand fit.
- Pairwise preference giữa A/B/C/D giúp kết luận dễ hơn điểm tuyệt đối.
- Báo cáo inter-rater agreement (Krippendorff's alpha hoặc Cohen's kappa tùy số người).
- Dùng kiểm định phù hợp cho paired samples và báo effect size, không chỉ báo điểm trung bình.

### 8.6. Điều kiện thành công dự kiến

- D giảm unsupported claim rate rõ rệt so với A.
- C/D tăng channel/persona/brand fit so với model gốc.
- Fact precision của cấu hình production đạt ít nhất 90% trên test nội bộ.
- Structured output pass rate >= 95%.
- R3 cải thiện evidence recall hoặc factuality trên nhóm query quan hệ so với R1 mà latency p95 vẫn nằm trong ngưỡng demo đã công bố.
- 100% graph path đưa vào prompt production có `source_id`; edge chưa duyệt không được dùng cho claim nhạy cảm.
- Tất cả output có claim nhạy cảm phải qua reviewer.
- Web app có uptime demo ổn định, không lỗi luồng chính và có URL online.

Các ngưỡng là mục tiêu kỹ thuật, không được điều chỉnh sau để làm đẹp kết quả; nếu không đạt, báo cáo trung thực và phân tích lỗi.

---

## 9. An toàn, pháp lý và đạo đức

- Lưu source/license/permission cho dữ liệu.
- Không thu thập hoặc suy luận dữ liệu cá nhân nhạy cảm.
- Không tạo claim pháp lý, cam kết lợi nhuận, tiến độ, giá hoặc ưu đãi khi thiếu nguồn.
- Có forbidden claims và disclaimer theo loại nội dung.
- Không dùng thuộc tính nhạy cảm để steering khách hàng.
- Ảnh và nội dung upload được cô lập theo tenant.
- Có human approval trước export; không auto-publish trong MVP.
- Log model/prompt/source/version để audit.

---

## 10. Kế hoạch 8 tuần chi tiết

### Tuần 1 - 15/07 đến 21/07: khóa thiết kế và dựng vertical slice

Kế hoạch thực thi theo ngày và tiêu chí nghiệm thu: xem [KE_HOACH_CHI_TIET_TUAN_1.md](KE_HOACH_CHI_TIET_TUAN_1.md).

**Hải:** chốt nguồn, crawler contract, raw schema, license log và 20-50 bản ghi mẫu.  
**Quang:** khởi tạo monorepo/app, database, auth/RBAC, project CRUD, CI/CD và môi trường staging.  
**Cả nhóm:** khóa RQ, metric, channel rules, persona schema, brand schema, Property Graph ontology v1 và definition of done.

**Checkpoint:** user đăng nhập trên URL staging, tạo project và nhập được một record đúng schema; crawler export được fixture đầu tiên; ontology v1 chỉ gồm node/edge cần cho query benchmark.

### Tuần 2 - 22/07 đến 28/07: ingestion và MVP deploy

Kế hoạch thực thi theo ngày và tiêu chí nghiệm thu: xem [KE_HOACH_CHI_TIET_TUAN_2.md](KE_HOACH_CHI_TIET_TUAN_2.md).

**Hải:** crawl batch đầu, dedup, normalize, báo cáo missing fields và provenance.  
**Quang:** upload JSON/tài liệu/ảnh, validation, project detail, asset storage, job status và migrations `graph_entities/graph_relationships`.  
**Phối hợp:** integration test từ crawler fixture đến canonical facts; dựng entity alias và deterministic edges đầu tiên.

**Checkpoint:** dữ liệu crawl đi xuyên suốt vào database trên staging; project -> zone -> building -> unit type truy vấn được bằng PostgreSQL; không chỉnh tay để “làm demo”.

### Tuần 3 - 29/07 đến 04/08: knowledge base và dataset v1

Kế hoạch thực thi theo ngày và tiêu chí nghiệm thu: xem [KE_HOACH_CHI_TIET_TUAN_3.md](KE_HOACH_CHI_TIET_TUAN_3.md).

**Hải:** hoàn thiện cleaned dataset, gán quality flags, tạo SFT draft.  
**Quang:** fact editor, source viewer, chunking/indexing pipeline, entity resolution, graph traversal 1-2 hop, brand/persona editor và versioning cơ bản.  
**Cả nhóm:** chia train/validation/test theo project, audit leakage và gán nhãn 60-90 retrieval queries R1-R3.

**Checkpoint:** `dataset_v1` có data card, thống kê, split cố định; R1 vector baseline và R2 graph-only trả facts/path đúng project kèm nguồn.

### Tuần 4 - 05/08 đến 11/08: prompt-only và RAG baseline

Kế hoạch thực thi theo ngày và tiêu chí nghiệm thu: xem [KE_HOACH_CHI_TIET_TUAN_4.md](KE_HOACH_CHI_TIET_TUAN_4.md).

**Hải:** bộ retrieval queries + relevance labels; prompt baseline khóa version.  
**Quang:** query router, R3 hybrid graph + vector context assembler, Content Studio, evidence path panel và generation logging.  
**Cả nhóm:** đo Recall@k/MRR, relationship/path precision, latency; chạy A/B baseline trên cùng test subset.

**Checkpoint:** A và B chạy end-to-end trên web; R1-R3 có bảng so sánh; UI giải thích được ít nhất một đường đi từ căn hộ đến tiện ích và source evidence.

### Tuần 5 - 12/08 đến 18/08: QLoRA và reviewer flow

Kế hoạch thực thi theo ngày và tiêu chí nghiệm thu: xem [KE_HOACH_CHI_TIET_TUAN_5.md](KE_HOACH_CHI_TIET_TUAN_5.md).

**Hải:** pilot backbone, train QLoRA, lưu adapter/log/config; đồng thời chạy Microsoft GraphRAG sandbox trên một corpus con và ghi indexing cost.  
**Quang:** editor, approve/reject, reviewer note, content version history, export.  
**Cả nhóm:** review chất lượng SFT, chọn checkpoint theo validation và áp dụng gate Microsoft GraphRAG.

**Checkpoint:** adapter load được độc lập; cấu hình C sinh được output test; reviewer flow chạy đầy đủ. Có quyết định bằng số liệu: tiếp tục endpoint GraphRAG discovery hoặc dừng ở nghiên cứu offline.

### Tuần 6 - 19/08 đến 25/08: tích hợp D và đánh giá chính

Kế hoạch thực thi theo ngày và tiêu chí nghiệm thu: xem [KE_HOACH_CHI_TIET_TUAN_6.md](KE_HOACH_CHI_TIET_TUAN_6.md).

**Hải:** chạy A/B/C/D và R1-R4 đủ điều kiện trên frozen test set; tổng hợp automatic metrics.  
**Quang:** model gateway, experiment config, comparison UI, graph evidence visualization, latency/cost logs.  
**Cả nhóm:** human evaluation mù và thống kê kết quả.

**Checkpoint:** bảng generation và retrieval tái lập được từ script; mọi run có dataset/model/prompt/graph snapshot version.

### Tuần 7 - 26/08 đến 01/09: vision, critic và hardening

Kế hoạch thực thi theo ngày và tiêu chí nghiệm thu: xem [KE_HOACH_CHI_TIET_TUAN_7.md](KE_HOACH_CHI_TIET_TUAN_7.md).

**Hải:** vision extraction benchmark, image-text consistency, error taxonomy.  
**Quang:** UI xác nhận visual facts, critic panel, dashboard, hoàn thiện RBAC/UX.  
**Cả nhóm:** chỉ thêm critic-refiner nếu A-D đã hoàn thành.

**Checkpoint:** ảnh tạo facts có confidence/provenance; output không dùng visual claim chưa xác nhận.

### Tuần 8 - 02/09 đến 08/09: release candidate

Kế hoạch thực thi theo ngày và tiêu chí nghiệm thu: xem [KE_HOACH_CHI_TIET_TUAN_8.md](KE_HOACH_CHI_TIET_TUAN_8.md).

**Hải:** chốt figures/tables, model card, data card, reproducibility package.  
**Quang:** end-to-end tests, security check, deploy production, seed demo account/data, runbook.  
**Cả nhóm:** rehearsal demo, backup plan khi API/model lỗi, freeze release.

**Checkpoint:** URL production, auth/RBAC, 4 loại content, graph + vector evidence, review/version/export và dashboard A-D/R1-R3 đều chạy được. Microsoft GraphRAG không được là single point of failure.

### 09/09 đến 23/09: báo cáo và bảo vệ

- Viết chương dữ liệu, phương pháp, hệ thống, thí nghiệm, kết quả, đạo đức và hạn chế.
- Sinh sơ đồ kiến trúc, data flow, sequence diagram và bảng ablation từ artefact thật.
- Chụp ảnh UI từ production.
- Kiểm thử demo trên máy khác và mạng khác.
- Chuẩn bị video backup 3-5 phút và dữ liệu offline nếu dịch vụ ngoài lỗi.

---

## 11. Definition of Done

### Data

- Raw/clean/SFT/benchmark dataset có version và data card.
- Source provenance và license note đầy đủ.
- Split theo project, có báo cáo leakage/dedup.
- Property Graph snapshot có ontology version, entity aliases, temporal fields và provenance.

### Model

- Adapter QLoRA, config, tokenizer, seed, log và model card.
- Script train/eval chạy lại được.
- A/B/C/D dùng cùng frozen test set.

### Product

- URL online, HTTPS, login và RBAC backend.
- Quản lý user/project/asset/brand/persona.
- Generate bốn kênh, evidence, review, version, export.
- Production retrieval chạy PostgreSQL Property Knowledge Graph + hybrid vector RAG; evidence panel hiển thị source và graph path.
- Audit log, error handling và loading/job status rõ ràng.

### Research

- RQ, giả thuyết, baseline, metric và protocol rõ.
- Automatic + human evaluation.
- Có so sánh R1 vector, R2 graph-only, R3 graph + vector; Microsoft GraphRAG R4 được báo cáo nếu chạy qua gate.
- Báo cáo indexing/query cost, latency và error taxonomy của graph extraction/entity resolution.
- Báo cáo cả negative results, failure cases và giới hạn.

### Demo

- Một kịch bản happy path 5-7 phút.
- Một kịch bản chứng minh chống hallucination.
- Một màn hình so sánh A/B/C/D.
- Video và dataset demo dự phòng.

---

## 12. Rủi ro và phương án giảm thiểu

| Rủi ro | Dấu hiệu sớm | Phương án |
|---|---|---|
| Crawl trễ/không ổn định | Tuần 2 chưa có fixture chuẩn | Dùng fixture và dữ liệu nhập tay được phép để không chặn app; giữ contract không đổi |
| Dữ liệu SFT ít/chất lượng thấp | Validation không cải thiện | Giảm số task fine-tune, ưu tiên 1-2 kênh cho train nhưng vẫn dùng RAG/API cho app |
| Không đủ GPU | Pilot OOM/chạy quá lâu | Model nhỏ hơn, giảm sequence length, QLoRA 4-bit, thuê GPU theo giờ, khóa budget |
| Fine-tune không hơn baseline | Channel fit không tăng | Báo negative result, phân tích dữ liệu/label; không che kết quả bằng đổi test set |
| RAG lấy sai project | Evidence mismatch | Metadata filter bắt buộc, retrieval eval trước generation, tenant isolation test |
| Entity resolution merge sai | Một node chứa dữ liệu nhiều tòa/dự án | Canonical key + alias table + confidence + human review; không auto-merge trường hợp mơ hồ |
| Graph chứa edge bịa/cũ | Claim có path nhưng source yếu/hết hạn | Mọi edge có provenance/validity; edge pending không dùng cho claim nhạy cảm |
| Graph traversal quá rộng | Context dài, latency tăng, semantic drift | Giới hạn 2 hop, whitelist edge theo query type, context/token budget |
| Microsoft GraphRAG tốn chi phí | Indexing vượt budget hoặc tuần 5 chưa có benchmark | Chỉ chạy corpus con; áp dụng stop gate; giữ như nghiên cứu offline/negative result |
| VLM bịa chi tiết ảnh | Visual fact precision thấp | Schema hẹp, confidence threshold, human confirmation |
| Deploy muộn | Hết tuần 2 chưa có staging | Deploy skeleton từ tuần 1, không chờ AI pipeline hoàn tất |
| API ngoài lỗi/chi phí cao | Timeout/rate limit | Model gateway, retry có giới hạn, cache, budget cap, fallback và demo video |
| Human evaluation thiếu người | Tuần 6 chưa chốt reviewer | Chốt lịch từ tuần 3; giảm test set nhưng giữ paired/blind protocol |

---

## 13. Việc cần làm ngay trong 72 giờ

1. Chốt Git repo, branching, issue board và owners.
2. Hải bàn giao `crawler_contract_v1.json` + 20 record fixture + danh sách nguồn/license.
3. Tạo `data_dictionary.md`, `data_card_v0.md`, `experiment_protocol_v0.md`.
4. Chốt bốn kênh, ba persona và một brand demo chuẩn.
5. Dựng Postgres schema và migrations đầu tiên.
   - Bổ sung `graph_entities`, `graph_entity_aliases`, `graph_relationships`, `graph_claims`.
6. Deploy Next.js + FastAPI health check lên staging.
7. Hoàn thành login/RBAC và project CRUD vertical slice.
8. Chuẩn bị 60-90 retrieval questions chia fact/1-hop/2-hop/global/conflict/temporal và 12 gold outputs để benchmark sớm.
9. Kiểm tra GPU/budget/API keys; chạy pilot model nhỏ trước khi cam kết backbone.
10. Họp checkpoint cuối Tuần 1 bằng demo chạy thật, không chỉ báo cáo tiến độ.

---

## 14. Tiêu chí cắt scope

Nếu trễ tiến độ, cắt theo thứ tự:

1. DPO/preference training.
2. A/B online/traffic thật.
3. Video script/storyboard.
4. Reranker riêng và agent nhiều bước.
5. Đa ngôn ngữ.
6. Critic-refiner tự động nhiều vòng.
7. Microsoft GraphRAG endpoint trong production; vẫn giữ benchmark offline nếu đã có kết quả.
8. Graph traversal sâu hơn 2 hop, Neo4j và graph visualization nâng cao.

Không được cắt: deploy online, auth/RBAC, user/project management, bốn cấu hình A-D, QLoRA, PostgreSQL Property Knowledge Graph + hybrid vector RAG, R1-R3, source/path evidence, version/review flow và đánh giá trên frozen test set.

---

## 15. Kết luận chốt phương án

Đồ án không nên được trình bày như một “AI viết content”, mà là một nghiên cứu về **multimodal retrieval-grounded controllable generation** cho marketing BĐS tiếng Việt. Kiến trúc hợp lý nhất trong 8 tuần là:

**Crawler/Upload -> canonical facts -> PostgreSQL Property Knowledge Graph + hybrid vector RAG + visual facts -> open 7B/8B QLoRA generator -> critic -> human review -> versioned content**, được bao quanh bởi một web app online có auth/RBAC và hai benchmark: A-D cho generation, R1-R3 cho retrieval.

Microsoft GraphRAG là lớp nghiên cứu batch cho Local/Global discovery trên corpus con, có stop gate ở Tuần 5 và không nằm trên critical path production. Cách phân tầng này bảo đảm:

- **Tính ứng dụng:** tạo nội dung theo căn/tòa/dự án/persona từ dữ liệu thật.
- **Khả năng deploy:** chỉ cần PostgreSQL + pgvector ở lõi, không bắt buộc Neo4j hoặc GraphRAG service.
- **Luồng giải thích được:** mỗi claim hiển thị fact, graph path và source evidence.
- **Đóng góp học thuật:** ontology BĐS, graph-augmented retrieval, temporal/provenance và benchmark GraphRAG.
- **Thí nghiệm rõ:** A-D tách tác động RAG/fine-tuning; R1-R4 tách vector/property graph/Microsoft GraphRAG.
- **Kiểm soát 8 tuần:** graph production tối đa 2 hop, ontology hẹp, Microsoft GraphRAG có gate và các phần mở rộng được cắt trước.

Phần khó và có giá trị học thuật nhất không phải gọi model, mà là provenance của dữ liệu, thiết kế SFT đúng, split chống leakage, kiểm soát claim và protocol đánh giá có thể tái lập.
