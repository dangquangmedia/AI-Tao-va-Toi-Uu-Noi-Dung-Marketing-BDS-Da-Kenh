# Checkpoint Tuần 6 — Đánh giá đóng băng + dashboard so sánh

**Ngày:** 29/07/2026 · **Branch:** `tuan-06-frozen-eval-dashboard` · **Người thực hiện:** Quang (+ Claude hỗ trợ)

Artefact kèm theo: [bảng retrieval R1–R3](week_06_retrieval_eval.md) · [checkpoint Tuần 5](week_05_report.md)

> **Bối cảnh:** adapter QLoRA vẫn chưa có (chờ Hải train ở máy GPU/Colab — xem
> [training/README.md](../../training/README.md)), nên cấu hình C/D chưa thể có số. Tuần 6
> vì vậy làm **toàn bộ phần không phụ thuộc adapter**: hạ tầng chạy thí nghiệm đóng băng có
> snapshot, kiểm định thống kê, dashboard so sánh, và bộ câu hỏi khó để đo lại retrieval
> một cách trung thực. Khi adapter về, C/D chạy bằng đúng lệnh cũ, không sửa dòng nào.

## Kết quả so với gate Tuần 6 ([Plan/01 §6](../../Plan/01_KE_HOACH_TONG_THE.md))

| Hạng mục gate | Trạng thái | Bằng chứng |
|---|---|---|
| Model gateway | ✅ (từ Tuần 4–5) | `app/services/llm.py` — template/local/adapter chung một cổng |
| Cấu hình D | ⏳ hạ tầng xong, chờ adapter | Đường đi D thông trong test; run thật ghi rõ "bỏ qua vì chưa có adapter" |
| Chạy frozen A–D | ⚠️ **A/B có số thật (n = 12), C/D chờ adapter** | `app/experiment_cli.py`, bảng ở §3 — kết quả **bác bỏ** kết luận A/B của Tuần 4 |
| Chạy R1–R3 | ✅ | [week_06_retrieval_eval.md](week_06_retrieval_eval.md) — 108 query |
| Comparison dashboard | ✅ | `/experiments` — snapshot + chỉ số + so sánh cặp + từng bài |
| **Mọi run có snapshot version** | ✅ | Bảng `experiment_runs.snapshot` — commit, model, prompt, adapter fingerprint, kích thước split |
| **Bảng kết quả tái lập được từ script** | ✅ | Một lệnh sinh lại toàn bộ; số standard tái lập khớp Tuần 4 (§2.2) |
| Human evaluation mù | ❌ chưa | Chưa chốt được rater; xem §6 |

## 1. Bộ câu hỏi khó — sửa một chỗ tự đánh lừa mình

Tuần 4 báo cáo **R3-router đạt project precision 1,000**. Con số đó đúng nhưng gây hiểu lầm:
cả 72 gold query đều **nêu tên dự án**, router nhận ra tên rồi lọc thẳng theo `project_slug`,
nên phép đo thực chất đo *khả năng khớp tên*, không đo khả năng tìm kiếm. Người dùng thật gõ
"căn 2 phòng ngủ tầm 3 tỷ ở Quận 7", không gõ tên dự án.

Tuần 6 bổ sung **36 câu hỏi mô tả, tuyệt đối không nêu tên dự án**, ba nhóm:

| Nhóm | Mẫu câu | Số câu | Số đáp án đúng TB |
|---|---|---:|---:|
| `hard_attribute` | *"Tìm căn hộ 2 phòng ngủ, diện tích khoảng 75 m², tại Quận 7."* | 12 | 7,4 |
| `hard_budget` | *"Có căn hộ nào ở Quận 7 tầm giá từ 5 đến 10 tỷ không?"* | 12 | 11,8 |
| `hard_location` | *"Đang rao bán những bất động sản nào ở Tây Mỗ?"* | 12 | 41,2 |

Ba quyết định về nhãn, đều ảnh hưởng trực tiếp đến việc con số có trung thực hay không:

1. **Nhãn là *mọi* tin khớp điều kiện, không phải riêng tin dùng để dựng câu.** Câu mô tả có
   nhiều đáp án đúng; chấm theo một tin nguồn sẽ phạt oan hệ thống mỗi khi nó trả về một tin
   khác cũng đúng.
2. **Nhãn tính trên toàn bộ corpus, không giới hạn split test.** Chỉ mục truy xuất chứa cả ba
   split nên một tin ở split train khớp đúng mô tả vẫn là đáp án đúng. Bộ standard không gặp
   chuyện này vì mọi tin của một dự án nằm cùng một split.
3. **Câu hỏi có đáp án toàn tin lẻ (không thuộc dự án nào) không bị chấm 0 ở nhóm chỉ số theo
   dự án** — các chỉ số đó trả về "không đo được" và bị loại khỏi trung bình. Nhà riêng, nhà
   mặt phố thường không thuộc dự án nào; tính chúng bằng 0 là bịa ra một điểm trừ.

Thêm hai chi tiết nhỏ nhưng ảnh hưởng số đo: tên phường trong DB là slug không dấu (lấy từ
URL), nên câu hỏi lấy lại **tên có dấu từ chính tin đăng** — hỏi "ở Me Tri" thay vì "ở Mễ Trì"
sẽ phạt oan nhánh vector; và slug phường chỉ có số ("12") bị loại vì câu hỏi sinh ra vô nghĩa.

## 2. Kết quả retrieval trên hai bộ

108 query (72 standard + 36 hard), top-k = 10, embedding `BAAI/bge-m3`. Bảng đầy đủ:
[week_06_retrieval_eval.md](week_06_retrieval_eval.md).

### 2.1. Chênh lệch giữa hai bộ

| Cấu hình | standard: proj. precision | **hard: proj. precision** | standard: recall | hard: recall |
|---|---:|---:|---:|---:|
| R1-fts | 0,090 | 0,073 | 0,117 | 0,015 |
| R1-bm25 | 0,964 | **0,115** | 0,848 | 0,130 |
| R1-vector | 0,940 | 0,242 | 0,855 | 0,194 |
| R1-hybrid | 0,981 | 0,269 | 0,865 | 0,235 |
| R2-graph | 0,738 | **0,465** | 0,862 | 0,101 |
| R3-fixed | 0,986 | 0,273 | 0,928 | 0,235 |
| **R3-router** | **1,000** | **0,339** | **0,938** | **0,248** |

Bốn điều đọc được, cái thứ ba là quan trọng nhất:

1. **Con số 1,000 của Tuần 4 là thật nhưng không phải điều nó có vẻ nói.** Cùng hệ thống, cùng
   ngày, chỉ đổi dạng câu hỏi: 1,000 → 0,339. Phần chênh lệch ấy là công của bước khớp tên dự
   án, không phải của bước tìm kiếm. Số standard vẫn phải báo cáo — nó đo đúng ca sử dụng
   "viết bài cho dự án X" — nhưng **báo cáo mà thiếu cột hard là để người đọc hiểu sai**.
2. **BM25 sụp mạnh nhất: 0,964 → 0,115.** Hợp lý: khi câu hỏi không có tên riêng, mọi từ trong
   câu ("căn hộ", "Quận 7", "3 tỷ") đều xuất hiện ở hàng nghìn tin nên không phân biệt được tin
   nào. Vector giữ được gấp đôi BM25 (0,242) vì nó khớp theo nghĩa của cả câu.
3. **Nhánh graph — yếu nhất ở bộ standard (0,738) — lại mạnh nhất ở bộ hard (0,465), riêng
   nhóm câu hỏi theo địa bàn đạt 0,855.** Đây là bằng chứng đầu tiên cho thấy Property Knowledge
   Graph đóng góp thứ mà hai nhánh văn bản không làm được: nó khớp thực thể phường/quận rồi đi
   theo cạnh về đúng nhóm tin, thay vì so khớp chuỗi ký tự. Trước Tuần 6 graph mới chỉ chứng
   minh được giá trị ở câu hỏi quan hệ.
4. **Nhưng R3 lúc đầu không hưởng được lợi ích đó** (0,273 < 0,465 của graph đơn thuần): trọng
   số cố định hạ graph xuống 0,3 — đúng nhánh mạnh nhất ở dạng câu hỏi này. Xem 2.2.

### 2.2. Router học được từ chính bằng chứng đó: chế độ "tìm theo mô tả"

Router nay chia hai chế độ. Không nhận ra dự án nào trong câu hỏi ⇒ đây là câu tìm theo mô tả
⇒ dùng bộ trọng số riêng. Trọng số chốt bằng sweep trên chính bộ hard:

| vector | bm25 | graph | proj. precision | listing precision | listing recall | MRR |
|---:|---:|---:|---:|---:|---:|---:|
| 1,0 | 0,3 | 1,5 | **0,492** | 0,333 | 0,132 | 0,688 |
| 1,0 | 0,1 | 2,0 | 0,473 | 0,319 | 0,120 | 0,605 |
| 1,0 | 0,0 | 3,0 | 0,465 | 0,308 | 0,113 | 0,611 |
| **1,0** | **0,3** | **0,9** | 0,339 | **0,387** | **0,248** | 0,462 |
| 1,0 | 0,6 | 0,3 *(cũ)* | 0,273 | 0,350 | 0,235 | 0,453 |

*(Rút gọn 5/6 cấu hình đã quét — bảng đầy đủ ở [week_06_retrieval_eval.md](week_06_retrieval_eval.md).)*

**Không chọn dòng đầu bảng dù nó thắng ở project precision.** Đẩy graph lên 1,5 cho project
precision cao nhất nhưng *listing recall sụt gần một nửa* (0,248 → 0,132): graph kéo về đúng dự
án nhưng không đúng tin, và còn chiếm chỗ của hai nhánh văn bản trong top-k. Khâu sinh nội dung
cần đúng **tin** mới lấy được fact, nên trọng số chốt theo listing precision/recall. Đây là ví
dụ cụ thể cho nguyên tắc "chọn chỉ số theo việc hạ nguồn cần gì, không chọn theo số nào đẹp".

Kết quả sau khi chốt `vector 1,0 · bm25 0,3 · graph 0,9` cho chế độ discovery:

| | R3 trước (trọng số cố định) | R3 sau (có chế độ discovery) |
|---|---:|---:|
| Bộ hard — project precision | 0,273 | **0,339** (+24%) |
| Bộ hard — listing recall | 0,235 | **0,248** |
| Bộ hard — `hard_location` (chuẩn hóa) | 0,535 | **0,618** |
| Bộ standard — project precision | 0,986 | **1,000** (không tụt) |

Điều kiện quan trọng: trọng số discovery **chỉ áp cho câu không nêu tên dự án**. Sweep cho thấy
nếu áp graph ≥ 1,5 cho mọi câu thì bộ standard tụt 0,986 → 0,738. Đây chính là lý do phải có
router chứ không phải một bộ trọng số duy nhất.

### 2.3. Trần lý thuyết của precision — một cái bẫy khi đọc bảng

Câu hỏi chỉ có 3 đáp án đúng thì precision@10 không thể vượt 0,3 dù hệ thống hoàn hảo. Bộ
standard có trung bình 2,8–10,7 đáp án, bộ hard có 7,4–41,2 — so precision thô giữa hai bộ là so
hai thứ khác thang. Bảng vì thế có thêm cột **chuẩn hóa theo trần** (`precision ÷ min(1, số đáp
án đúng / số tin lấy về)`).

Một lỗi đã mắc và đã sửa trong tuần: bản đầu chia cho trần tính theo *tin* nhưng lại đếm
precision theo *chunk*. Mỗi tin sinh ba chunk (title/description/facts) nên một tin đúng chiếm
được ba ô trong top-k, và tỷ lệ chuẩn hóa vọt lên **2,16** — tức là "đúng 216%". Sửa bằng cách
đưa cả tử và mẫu về cùng cấp *tin phân biệt*.

## 3. Thí nghiệm đóng băng A–D — kết quả Tuần 4 **không lặp lại được**

Run `week6_frozen_ab`: 12 brief từ split test × cấu hình A và B, `Qwen2.5-1.5B-Instruct` fp16,
greedy + seed 42, k = 3, 200 token. C và D bị bỏ qua kèm lý do "chưa có adapter". Bảng đầy đủ +
snapshot: [week_06_experiment.md](week_06_experiment.md).

| Chỉ số | A (prompt-only) | B (RAG) |
|---|---:|---:|
| Số bài | 12 | 12 |
| **Tỷ lệ claim không có căn cứ** | **0,1604** | **0,1747** |
| Bài có ≥1 claim vô căn cứ | 9/12 | **7/12** |
| Số claim mỗi bài | 5,58 | 6,08 |
| Câu chứa từ cấm | 0 | 0 |
| Đúng định dạng 3 phần | **0,583** | 0,333 |
| Số từ trung bình | 145 | 122 |
| Thời gian sinh | 31,2 giây | 52,1 giây |

Kiểm định bắt cặp trên chỉ số chính:

| | Giá trị |
|---|---|
| Chênh lệch trung bình (B − A) | **+0,0142** (B *xấu hơn*) |
| Khoảng tin cậy 95% (bootstrap) | **[−0,111; +0,138]** — chứa 0 |
| Thắng / thua / hòa theo brief | **6 / 5 / 1** |
| Cohen's dz | 0,06 (không đáng kể) |
| p (hoán vị bắt cặp, chính xác) | **0,85** |

**Kết luận: ở cỡ mẫu 12, RAG không cho thấy ưu thế đo được về tỷ lệ claim vô căn cứ.**

### 3.1. Vì sao Tuần 4 nói ngược lại — và ai đúng

Tuần 4 chạy **4 brief** và ra kết quả rất đẹp: 0,2042 → 0,0917, B thắng 4/4. Run tuần này
**tái lập chính xác cả 4 brief đó** (cùng từng con số: 0,167→0; 0,2→0,167; 0,25→0,2; 0,2→0) rồi
chạy tiếp 8 brief nữa. Trên 8 brief mới: B thắng 2, thua 5, hòa 1.

Nguyên nhân không phải ngẫu nhiên xui rủi mà là **lỗi thiết kế chọn mẫu**: `pick_briefs` xếp dự
án theo số tin giảm dần, nên "4 brief đầu" chính là **4 dự án nhiều tin nhất** — nhóm mà truy
xuất có nhiều dữ kiện nhất để bám. Lấy 4 phần tử đầu của một danh sách đã sắp xếp không phải là
lấy mẫu, đó là chọn ca thuận lợi. Cảnh báo "n = 4, chưa kiểm định thống kê" ghi trong báo cáo
Tuần 4 là đúng, nhưng vẫn chưa đủ: vấn đề không chỉ nằm ở cỡ mẫu mà ở **cách mẫu được chọn**.

Chi tiết từng brief (8 brief mới nằm dưới vạch):

| Dự án | Kênh | A | B |
|---|---|---:|---:|
| sun-urban-city | description | 0,167 | **0,000** |
| mizuki-park | facebook | 0,200 | **0,167** |
| the-beverly-vinhomes-grand-park | email | 0,250 | **0,200** |
| the-marq | landing_seo | 0,200 | **0,000** |
| — | — | — | — |
| thanh-xuan-valley | description | **0,167** | 0,333 |
| aqua-city | facebook | **0,125** | 0,286 |
| celesta-rise | email | 0,167 | **0,000** |
| mandarin-garden | landing_seo | **0,000** | 0,182 |
| celestine-westlake | description | **0,250** | 0,500 |
| estella-heights | facebook | 0,000 | 0,000 |
| riviera-point | email | 0,400 | **0,000** |
| vinhomes-the-harmony | landing_seo | **0,000** | 0,429 |

### 3.2. Đọc kỹ hơn: hai chỉ số nói hai chuyện khác nhau

- **Số bài dính ít nhất một claim bịa giảm: 9/12 → 7/12.** RAG có làm nhiều bài sạch hoàn toàn.
- **Nhưng tỷ lệ trung bình lại nhích lên**, vì B viết nhiều claim hơn (6,08 so với 5,58) và khi
  sai thì sai nặng (0,429; 0,500).

Thêm một dấu hiệu nhìn thấy trên `/experiments`: **mọi tiêu đề của B đều bắt đầu bằng `**`**
(model chèn dấu in đậm Markdown), còn A thì không cái nào. Prompt không hề yêu cầu Markdown —
đây là hành vi chỉ xuất hiện khi có khối dữ kiện dài phía trước.

Giả thuyết hàng đầu, **chưa kiểm chứng**: model 1,5B không đủ sức dùng khối context ~2.000 token.
Có nhiều con số trước mắt thì nó viết nhiều câu có số hơn, và mỗi lần chép sai hoặc tự suy ra
(giá/m² từ giá và diện tích) là một claim không truy được về fact. Bằng chứng gián tiếp ủng hộ:
**B tuân định dạng ba phần kém hơn hẳn A (0,333 so với 0,583)** — dấu hiệu của việc context dài
lấn át phần chỉ dẫn định dạng trong prompt.

Cách kiểm chứng giả thuyết này (Tuần 7 hoặc khi có GPU thuê), theo thứ tự rẻ đến đắt:

1. Chạy lại đúng 12 brief này với model 7–8B — nếu chênh lệch đảo chiều thì nguyên nhân là dung
   lượng model, không phải RAG.
2. Giảm `k` xuống 1–2 chunk để cắt bớt context — nếu B tốt lên thì nguyên nhân là độ dài context.
3. Tách riêng claim "chép trực tiếp" và claim "tự suy ra" trong claim checker để biết model bịa
   kiểu nào.

### 3.3. Điều này ảnh hưởng gì tới đồ án

Không ảnh hưởng tới phạm vi: ma trận A–D và giả thuyết của [Plan/03](../../Plan/03_KE_HOACH_THUC_NGHIEM.md)
vẫn giữ nguyên — đây chính là thứ thí nghiệm sinh ra để trả lời, và **kết quả âm cũng phải báo
cáo** (nguyên tắc đã khóa trước ở Plan/03 §7). Ảnh hưởng thật nằm ở chỗ khác: mọi số liệu trích
từ báo cáo Tuần 4 phải kèm ghi chú rằng bản n = 12 không lặp lại được, và **cỡ mẫu chính thức
40–60 brief là bắt buộc**, không phải "làm cho đẹp".

## 4. Kiểm định thống kê

Chỉ số của bài toán này là **tỷ lệ** (claim vô căn cứ trên tổng claim), cỡ mẫu nhỏ, phân phối
lệch — dùng t-test là sai giả định. Thay bằng ba thứ đi cùng nhau:

| Công cụ | Trả lời câu hỏi | Vì sao chọn |
|---|---|---|
| **Kiểm định hoán vị bắt cặp** (sign-flip) | Chênh lệch có thật không? | Giả thiết duy nhất là đảo dấu trong từng cặp không đổi phân phối — đúng với thiết kế cùng brief. Với n ≤ 14 duyệt hết 2ⁿ tổ hợp nên p **chính xác**, không xấp xỉ |
| **Bootstrap percentile 10.000 lần** | Chênh lệch lớn cỡ nào? | Cho khoảng tin cậy mà không giả định phân phối; seed cố định nên chạy lại ra đúng khoảng đó |
| **Cohen's dz** | Chênh lệch có đáng kể không? | Cỡ hiệu ứng cho thiết kế bắt cặp; p nhỏ do n lớn khác với hiệu ứng lớn |

**Giới hạn phải nói trước khi ai đó hỏi:** kiểm định hoán vị với n cặp chỉ đạt được p tối
thiểu `1/2ⁿ`. Với n = 4 như baseline Tuần 4, p không thể xuống dưới 0,05 **dù chênh lệch lớn
đến đâu** — đó là giới hạn của thiết kế, không phải của kết quả. Bảng kết quả tự in ra giới
hạn này ở mọi báo cáo để không ai trích số mà bỏ mất điều kiện.

Bốn cặp so sánh hợp lệ, mỗi cặp cô lập **đúng một biến**:

| Cặp | Biến thay đổi | Trả lời |
|---|---|---|
| A → B | thêm truy xuất | RAG đóng góp bao nhiêu khi không có QLoRA |
| C → D | thêm truy xuất | RAG đóng góp bao nhiêu khi đã có QLoRA |
| A → C | thêm adapter | QLoRA đóng góp bao nhiêu khi không có RAG |
| B → D | thêm adapter | QLoRA đóng góp bao nhiêu khi đã có RAG |

Không so A với D: hai biến đổi cùng lúc thì không quy được chênh lệch về nguyên nhân nào.

## 5. Snapshot — điều kiện để bảng số có nghĩa

Mỗi lượt chạy ghi lại toàn bộ trạng thái vào `experiment_runs.snapshot`:

```
commit git · dataset version + kích thước split · số gold query theo độ khó
số chunk / số chunk đã embed / số fact / số cạnh graph · model embedding
model sinh + provider + seed + max_new_tokens + 4bit · prompt version
trọng số RRF · adapter name + base model + fingerprint SHA-256
```

Đổi bất kỳ dòng nào trong đó là **một thí nghiệm khác**, không so trực tiếp được. Đây là câu
trả lời cho câu hỏi hội đồng "làm sao biết bảng này chạy trên cùng điều kiện".

## 6. Hạn chế đã biết

| Hạn chế | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| **C/D vẫn chưa có số** | Ma trận A–D mới điền được nửa | Hải train adapter; hạ tầng đã sẵn |
| **Ưu thế của RAG chưa chứng minh được** (§3) | Giả thuyết chính của đồ án chưa có bằng chứng | Ba bước kiểm chứng ở §3.2, ưu tiên chạy lại trên model 7–8B |
| Bộ brief xếp theo số tin, không lấy ngẫu nhiên | Cắt n nhỏ là chọn ca thuận lợi (§3.1) | Chạy đủ 40–60 brief, hoặc lấy mẫu phân tầng theo quy mô dự án |
| `length_ok` chỉ đo được 4/12 bài (3 cặp so được) | Trần 200 token cắt bài trước khi đủ độ dài | Tăng ngân sách token khi có GPU khỏe hơn |
| Tiêu đề của B dính `**` Markdown | Nội dung xuất ra cần hậu xử lý | Bỏ ký tự định dạng thừa ở `parse_output`, hoặc siết chỉ dẫn định dạng trong prompt (đổi prompt ⇒ đổi `PROMPT_VERSION`) |
| Human evaluation mù chưa chạy | Thiếu nửa bằng chứng chất lượng | Chốt rater (Plan/03 §5) |
| Gold query vẫn chưa được soát tay | Nhãn tự sinh chưa phải nhãn cuối | Hải soát cả 108 câu, bộ hard soát riêng |
| Ảnh chụp DB vẫn là bản trước `reparse_v2` | 31 tin phòng ngủ phi lý còn trong dữ liệu | Rebuild trước khi lấy số cuối |

## 7. Cách chạy local

```powershell
docker compose up -d
cd backend
.\.venv\Scripts\alembic.exe upgrade head                       # experiment_runs + cột độ khó
.\.venv\Scripts\python.exe -m app.dataset_cli --build          # sinh lại gold query (có bộ hard)
.\.venv\Scripts\python.exe -m app.dataset_cli --eval --eval-out ..\docs\checkpoints\week_06_retrieval_eval.md
.\.venv\Scripts\python.exe -m app.experiment_cli --briefs 12 --configs A,B,C,D --with-retrieval
.\.venv\Scripts\python.exe -m app.experiment_cli --list        # các lượt đã chạy
```

Xem kết quả trên web: `/experiments`. Máy không GPU thêm `--provider template` (chỉ để pipeline
chạy, **không dùng cho số liệu báo cáo**).
