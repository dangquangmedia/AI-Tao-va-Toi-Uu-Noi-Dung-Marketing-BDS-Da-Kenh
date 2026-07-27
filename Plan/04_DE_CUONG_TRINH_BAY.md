# 04 — Đề cương trình bày và chuẩn bị bảo vệ

> Tài liệu chuẩn bị cho buổi bảo vệ (dự kiến 10/10/2026): storyline slide, mapping chương báo cáo, kịch bản demo và **ngân hàng câu hỏi phản biện kèm hướng trả lời**. Cập nhật số liệu thật vào chỗ trống `[...]` sau Tuần 6–8.
>
> Tài liệu liên quan: [01 — Tổng thể](01_KE_HOACH_TONG_THE.md) · [02 — Dữ liệu](02_KE_HOACH_DU_LIEU.md) · [03 — Thực nghiệm](03_KE_HOACH_THUC_NGHIEM.md)

---

## 1. Storyline slide (~15 phút, ~16 slide)

| # | Slide | Ý chính (1 thông điệp/slide) |
|---|---|---|
| 1 | Bìa | Tên đề tài, nhóm, GVHD |
| 2 | Bài toán & động lực | Content marketing BĐS: tốn công, dễ sai fact, khó nhất quán thương hiệu → cần sinh nội dung **có căn cứ** |
| 3 | Khoảng trống | LLM thuần bịa fact (hallucination); chưa có dataset + benchmark tiếng Việt cho content BĐS đa kênh |
| 4 | Định vị & RQ | 1 câu định vị + 3 RQ chính (RAG? Fine-tune? Kết hợp?) |
| 5 | Tổng quan hệ thống | Workflow diagram (WORKFLOW_TONG_THE.svg) — 1 slide 1 hình |
| 6 | Dữ liệu | 4.795 tin + 37.349 ảnh tự crawl; pipeline làm sạch 5 giai đoạn; **chia split theo project chống leakage** |
| 7 | Property Knowledge Graph | Ontology cố định, ≤2 hop, provenance/temporal; ví dụ path thật `Căn 2PN → Tòa S2 → gần trường` |
| 8 | Hybrid RAG | FTS + vector + graph + RRF; query router |
| 9 | Fine-tuning | QLoRA trên [backbone đã chốt]; facts ở retrieval — style ở SFT |
| 10 | Kiểm soát chất lượng | Output JSON có claims→fact_id; critic + refine 1 vòng; reviewer flow |
| 11 | Thiết kế thực nghiệm | Ma trận A–D + R1–R3, frozen test, blind human eval |
| 12 | Kết quả chính | Bảng A–D: fact precision, unsupported claim rate, fit scores `[điền Tuần 6]` |
| 13 | Kết quả retrieval | R1 vs R3 theo nhóm query; latency `[điền Tuần 6]` |
| 14 | Demo | Chuyển sang demo live (hoặc video backup) |
| 15 | Đóng góp & hạn chế | 4 đóng góp ([01 §1](01_KE_HOACH_TONG_THE.md)) + hạn chế trung thực |
| 16 | Kết luận & hướng phát triển | DPO, online A/B, đa ngôn ngữ |

Nguyên tắc slide: số liệu thật từ script, không gõ tay; mỗi claim trên slide đều có nguồn trong báo cáo; screenshot UI lấy từ production.

## 2. Mapping chương báo cáo (theo format UIT — phụ lục 2)

| Chương | Nội dung | Nguồn tài liệu | Người viết chính |
|---|---|---|---|
| 1. Giới thiệu | Bài toán, động lực, RQ, phạm vi, đóng góp | [01 §1–3](01_KE_HOACH_TONG_THE.md) | Cả nhóm |
| 2. Cơ sở lý thuyết & công trình liên quan | LLM, RAG, PEFT/LoRA/QLoRA, knowledge graph, controllable generation, đánh giá sinh ngôn ngữ | Khảo sát lại từ tài liệu gốc | Hải |
| 3. Dữ liệu | Thu thập, làm sạch, phân bổ, split, SFT dataset, data card | [02](02_KE_HOACH_DU_LIEU.md) toàn bộ | Hải |
| 4. Phương pháp & kiến trúc hệ thống | Kiến trúc, graph, hybrid RAG, QLoRA, critic, web app | [01 §4](01_KE_HOACH_TONG_THE.md) | Quang |
| 5. Thực nghiệm | Protocol, metric, human eval, kết quả A–D/R1–R3, ablation, error analysis | [03](03_KE_HOACH_THUC_NGHIEM.md) | Hải + Quang |
| 6. Sản phẩm & triển khai | Web app, RBAC, deployment, demo | Artefact thật Tuần 8 | Quang |
| 7. Đạo đức & giới hạn | License, PII, forbidden claims, hạn chế | [02 §9](02_KE_HOACH_DU_LIEU.md) | Cả nhóm |
| 8. Kết luận | Trả lời RQ, đóng góp, hướng phát triển | Kết quả thật | Cả nhóm |

## 3. Kịch bản demo

### 3.1. Happy path (5–7 phút)

1. Đăng nhập bằng tài khoản `marketer` trên **URL production** → dashboard dự án.
2. Mở một dự án thật từ DataBDS (ví dụ dự án nhiều tin nhất) → xem facts, nguồn, ảnh.
3. Content Studio: chọn kênh Facebook + persona `young_family` + cấu hình D → Generate.
4. Mở **Evidence panel**: chỉ từng claim map về fact nào, nguồn URL nào, graph path nào.
5. Reviewer sửa 1 câu → duyệt → version history → export.

### 3.2. Kịch bản chống hallucination (2 phút — điểm ăn tiền)

1. Chọn dự án **thiếu dữ liệu giá** → yêu cầu viết bài nhấn mạnh giá.
2. Cho hội đồng thấy: output **không bịa giá** — hoặc bỏ claim, hoặc hiện `warnings[]`; so sánh cùng brief trên cấu hình A (prompt-only) bịa giá như thế nào.

### 3.3. Màn hình so sánh A–D (1 phút)

Dashboard: cùng brief, 4 output A–D cạnh nhau + bảng metric — minh họa trực tiếp đóng góp thực nghiệm.

### 3.4. Dự phòng

Video demo 3–5 phút quay trước từ production + dataset demo offline + tài khoản dự phòng; kiểm demo trên máy khác/mạng khác trong Tuần 8.

## 4. Ngân hàng câu hỏi hội đồng (chuẩn bị trước — trả lời trong 30–60 giây/câu)

### Nhóm dữ liệu

**Q1. Dữ liệu crawl có hợp pháp không? License thế nào?**
→ Tin đăng công khai trên batdongsan.com.vn, crawl tôn trọng cơ chế bảo vệ (không vượt tường), chỉ dùng nghiên cứu trong đồ án, không tái phân phối dataset gốc, không dùng thương mại. Mọi fact giữ `canonical_url` làm citation. PII (tên/SĐT người bán) bị drop/mask ngay từ bước làm sạch. Ghi rõ ở chương Đạo đức.

**Q2. Dữ liệu bẩn thế nào và xử lý ra sao?**
→ Thẳng thắn: parser lần đầu dính boilerplate (project_name ~100% hỏng, chỉ 31,6% tin có giá parse được). Nhóm xử lý bằng pipeline re-parse 5 giai đoạn từ các trường sạch (title/description/URL — 100% sạch), có quarantine, không sửa tay, đo tỷ lệ khôi phục trước/sau. Chính việc này thể hiện năng lực data engineering — số liệu ở [02 §1](02_KE_HOACH_DU_LIEU.md).

**Q3. Làm sao chống data leakage giữa train và test?**
→ Chia theo **project** (816 project khôi phục từ URL), không random theo sample; dedup exact + near-dup **trước** khi split rồi kiểm tra near-dup xuyên split lần cuối; test set đóng băng, có data card ghi phương pháp audit. Một dự án chỉ tồn tại trong đúng một split, kể cả ảnh và SFT sample của nó.

**Q4. Tin hết hạn (EXPIRED ~99,7%) thì dữ liệu còn giá trị không?**
→ Bài toán là sinh nội dung từ facts, không phải hiển thị tin còn hạn. Fact nhạy cảm thời gian (giá, khuyến mãi) có `valid_from/valid_to` — hệ thống không đưa giá hết hiệu lực vào claim, đây chính là minh chứng cho thiết kế temporal provenance.

**Q5. SFT ~1.000 mẫu có quá ít để fine-tune không?**
→ QLoRA chỉ học **style/format/persona conditioning**, không học facts (facts ở retrieval) — literature cho thấy vài trăm đến vài nghìn mẫu chất lượng cao là đủ cho task-specific SFT. Chất lượng (gold/silver có review, claim map fact) quan trọng hơn số lượng; và đây là biến kiểm soát được trong thí nghiệm C vs A.

### Nhóm phương pháp

**Q6. Sao chọn QLoRA mà không full fine-tune?**
→ (1) Tài nguyên sinh viên: 4-bit + adapter chạy được trên GPU đơn; (2) học thuật: LoRA/QLoRA là chuẩn PEFT hiện hành, kết quả tương đương full FT trên task hẹp; (3) tách vai trò: facts đã nằm ở retrieval nên không cần nhồi kiến thức vào trọng số.

**Q7. Sao dùng PostgreSQL làm knowledge graph mà không phải Neo4j?**
→ Traversal production giới hạn ≤2 hop → recursive CTE đáp ứng tốt; một hệ lưu trữ duy nhất cho transactional + vector + FTS + graph giảm độ phức tạp vận hành và tăng khả năng tái lập; ontology cố định không cần query graph tự do. Đã ghi thành quyết định kiến trúc có lý do; nếu benchmark cho thấy cần, đó là hướng phát triển.

**Q8. Vì sao giới hạn 2 hop?**
→ Kiểm soát latency và semantic drift: hầu hết câu hỏi marketing thực tế là 1–2 hop (căn → tòa → tiện ích); hop sâu hơn tăng nguy cơ kéo context nhiễu. Giới hạn được benchmark trong R2/R3.

**Q9. Khác gì việc gọi thẳng ChatGPT/Claude viết content?**
→ Bốn điểm: (1) mọi claim map về fact có nguồn — API thuần không có; (2) knowledge graph + temporal provenance cho câu hỏi quan hệ và dữ liệu hết hạn; (3) fine-tune open model tái lập được, không phụ thuộc black-box; (4) benchmark A–D chứng minh định lượng từng thành phần đóng góp gì. Demo chống hallucination minh họa trực tiếp.

**Q10. Hallucination đo bằng gì?**
→ Output là JSON có `claims[]` với `supported_fact_ids[]` → **unsupported claim rate** đo tự động được + spot-check người. Không dựa vào cảm nhận; định nghĩa và quy trình ở [03 §4](03_KE_HOACH_THUC_NGHIEM.md).

**Q11. LLM-as-judge có đáng tin không?**
→ Nhóm biết giới hạn (bias, inconsistency) nên: judge là model độc lập khác họ với generator, rubric cố định khóa version, không xem reference khi chấm factuality, và **chỉ là evaluator phụ** — kết luận chính dựa trên human eval mù + metric kiểm chứng tự động.

**Q12. Sao không dùng BLEU/ROUGE?**
→ Nội dung marketing có nhiều đáp án hợp lệ — n-gram overlap với một reference không phản ánh chất lượng. Thay bằng metric theo thuộc tính (factuality, constraint, fit) + human preference; BERTScore chỉ báo phụ.

### Nhóm thực nghiệm

**Q13. Human eval có mấy người, tin được không?**
→ Tối thiểu 2 (mục tiêu 3) rater, chấm mù, Likert + pairwise trên cùng brief; báo cáo inter-rater agreement (kappa/alpha) và kiểm định paired + effect size. Cỡ mẫu 40–60 brief × 4 cấu hình cho đủ sức mạnh thống kê ở mức so sánh cặp.

**Q14. Nếu fine-tune không tốt hơn baseline thì sao?**
→ Báo cáo trung thực như negative result kèm phân tích lỗi — protocol khóa metric trước nên không có chuyện đổi test set để làm đẹp. Negative result có phân tích vẫn là đóng góp học thuật hợp lệ.

**Q15. Kết quả có tái lập được không?**
→ Có gói tái lập: mọi run ghi dataset/model/prompt/graph snapshot version + seed; một script tái tạo toàn bộ bảng kết quả; model card + data card đầy đủ ([03 §7](03_KE_HOACH_THUC_NGHIEM.md)).

### Nhóm sản phẩm & phạm vi

**Q16. Hệ thống chạy thật ở đâu?**
→ URL production [điền Tuần 8], HTTPS, RBAC 3 vai trò, demo được trên máy hội đồng; có video dự phòng nếu mạng lỗi.

**Q17. Vision đóng vai trò gì, có fine-tune vision không?**
→ Không fine-tune vision (ngoài phạm vi 8 tuần). VLM chỉ trích visual facts hẹp (loại phòng, vật thể, vật liệu) có confidence + người xác nhận trước khi dùng; cấm suy đoán giá/pháp lý/vị trí từ ảnh. Đo precision trên benchmark ảnh có nhãn.

**Q18. Ai làm phần nào?** *(hội đồng hay hỏi để chấm cá nhân)*
→ Quang: kiến trúc hệ thống, database/graph storage, backend/frontend, RBAC, retrieval tích hợp, deployment. Hải: crawler/data contract, làm sạch, SFT dataset, QLoRA, evaluation, vision data. Cả hai nắm được toàn pipeline; trả lời chéo được câu hỏi cơ bản của phần còn lại.

**Q19. Sao không so sánh với sản phẩm thương mại (Jasper, Copy.ai)?**
→ Không cùng điều kiện so sánh công bằng (black-box, không kiểm soát retrieval/model, không tiếng Việt BĐS chuyên biệt); phạm vi đồ án là so sánh **có kiểm soát** các kỹ thuật (A–D) trên cùng dữ liệu — đúng chuẩn ablation học thuật.

**Q20. Hướng phát triển sau đồ án?**
→ DPO từ preference data T4 đã thu trong app; online A/B với traffic thật; đa ngôn ngữ; mở rộng graph khi quy mô dữ liệu tăng (khi đó mới cân nhắc graph DB riêng).

### Quy tắc ứng xử khi bị hỏi khó

1. Không biết → nói thẳng "nhóm chưa thử nghiệm điểm này, xin ghi nhận là hạn chế/hướng phát triển" — không bịa.
2. Câu hỏi về số liệu → chỉ trả lời số đã có trong báo cáo/log, mở đúng bảng.
3. Câu hỏi thuộc phần người kia → người phụ trách trả lời chính, người còn lại bổ sung.

## 5. Checklist trước bảo vệ (Tuần 8 → 10/10)

- [ ] Slide theo storyline §1, số liệu điền từ script
- [ ] Demo chạy thử trên **máy khác + mạng khác** ít nhất 2 lần
- [ ] Video backup 3–5 phút + dataset offline
- [ ] Mỗi thành viên tự trả lời trơn tru 20 câu §4 (tập vấn đáp chéo)
- [ ] In sẵn: bảng kết quả A–D, R1–R3, sơ đồ kiến trúc, data card
- [ ] Tài khoản demo + seed data production kiểm tra lần cuối trước 1 ngày
