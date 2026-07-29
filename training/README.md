# Gói huấn luyện QLoRA — hợp đồng bàn giao giữa máy train và backend

Máy phát triển của Quang (GTX 1650 Ti 4GB) **không đủ VRAM để fine-tune 7–8B**, nên phần
huấn luyện chạy ở nơi khác: máy GPU của Hải, Colab, hoặc GPU thuê theo giờ. Thư mục này
là toàn bộ thứ cần mang sang — **không cần backend, không cần PostgreSQL, không cần cài
phụ thuộc của web app**.

Nguyên tắc: hai bên chỉ chạm nhau qua **hai loại file**. Ngoài hai loại đó ra không có
ràng buộc nào khác, nên đổi máy train không phải sửa code.

```
  máy có DB (Quang)                     máy GPU (Hải / Colab)
  ────────────────────                  ─────────────────────
  python -m app.sft_cli   ──train.jsonl──▶  python qlora_train.py
                            validation.jsonl        │
                                                    ▼
  backend/models/adapters/<tên>/  ◀──── copy thư mục adapter ────┘
      → cấu hình C/D chạy được ngay, không sửa dòng code nào
```

## 1. Chuẩn bị dữ liệu (chạy ở máy có DB)

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.sft_cli --out artifacts\sft
```

Sinh ra `artifacts/sft/train.jsonl`, `validation.jsonl` và `sft_export_card.json`.
Mỗi dòng là một mẫu `messages` (system / user / assistant) dựng bằng **đúng prompt mà
backend dùng lúc sinh nội dung** — nhờ vậy không lệch giữa lúc train và lúc chạy thật.

Đọc `sft_export_card.json` trước khi train, đặc biệt hai chỗ:

- `counts` — số mẫu. Plan/02 §7 đặt mục tiêu 800–1.500; ít hơn nhiều thì kết quả QLoRA
  khó có ý nghĩa, cần nới `--max-unsupported` hoặc duyệt thêm nội dung trong UI `/review`.
- `output_chars` — độ dài mẫu đầu ra. Mô tả trong DataBDS **bị crawler cắt cụt**
  (trung vị 166 ký tự), nên model học được văn phong nhưng không học được độ dài
  180–260 từ mà kênh `description` yêu cầu. Chi tiết ở đầu file `backend/app/sft_cli.py`.

## 2. Cài môi trường (máy GPU)

```bash
pip install -r requirements-train.txt
# Colab: torch đã có sẵn, chỉ cần peft/bitsandbytes/transformers
```

Kiểm tra môi trường trước khi tốn tiền GPU — chạy smoke test bằng dữ liệu giả, khoảng
2 phút:

```bash
python qlora_train.py --smoke --base-model Qwen/Qwen2.5-1.5B-Instruct --out /tmp/smoke
```

Chạy trót lọt nghĩa là torch + bitsandbytes + peft khớp nhau và GPU đủ. Adapter sinh ra
bị đánh dấu `smoke: true`, backend sẽ cảnh báo nếu ai đó lỡ dùng nó để lấy số.

## 3. Huấn luyện thật

```bash
python qlora_train.py \
    --train train.jsonl --val validation.jsonl \
    --base-model Qwen/Qwen2.5-7B-Instruct \
    --rank 16 --alpha 32 --lr 2e-4 --epochs 3 \
    --out qwen25-7b-r16
```

Không gian tìm kiếm siêu tham số theo Plan/03 §3: `rank ∈ {8, 16, 32}`, `lr` từ 1e-5 đến
2e-4, `epochs` 2–4. **Chọn theo eval loss trên validation, không chọn theo train loss** —
train loss thấp chỉ nói model thuộc bài.

Mỗi lần chạy đổi `--out` sang tên khác để giữ lại được cả loạt thí nghiệm mà so sánh.
Đặt tên theo kiểu `<backbone>-r<rank>-lr<lr>` cho dễ đọc.

## 4. Bàn giao ngược về backend

Copy **nguyên thư mục** adapter vào `backend/models/adapters/`:

```
backend/models/adapters/qwen25-7b-r16/
    adapter_config.json           ← peft sinh
    adapter_model.safetensors     ← trọng số LoRA (vài chục MB)
    adapter_card.json             ← script này sinh: backbone, siêu tham số, loss, phần cứng
    tokenizer* (tuỳ chọn)
```

Backend nhận ra ngay, **không phải sửa code, không phải chạy migration**:

- `GET /api/generation/adapters` liệt kê adapter kèm trạng thái và lỗi (nếu thiếu file).
- Cấu hình **C** (QLoRA, không RAG) và **D** (QLoRA + RAG) trong `/studio` tự bật.
- Nhiều adapter cùng lúc: chọn bằng trường `adapter` trong request, hoặc đặt biến môi
  trường `LLM_ADAPTER=<tên>` làm mặc định. Chỉ có đúng một adapter thì hệ thống tự chọn.

`base_model` lấy từ `adapter_card.json` chứ không lấy từ cấu hình backend — adapter train
trên backbone nào thì nạp đúng backbone đó. Nạp lệch backbone không báo lỗi mà ra output
rác, nên chỗ này được khóa lại có chủ đích.

## 5. Những lỗi đã gặp, ghi lại để khỏi mất thời gian

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `got an unexpected keyword argument 'dtype'` | transformers < 4.50 dùng `torch_dtype` | script này đã dùng `torch_dtype`; đừng đổi |
| CUDA OOM ngay bước đầu | `max_seq_len` quá lớn so với VRAM | hạ `--max-seq-len 1024`, giữ `--batch-size 1`, tăng `--grad-accum` |
| Loss = 0 hoặc NaN từ bước 1 | mẫu bị cắt hết phần trả lời | tăng `--max-seq-len`; xem `skipped_too_long` trong card |
| bitsandbytes báo không có GPU | bản CPU-only | cài lại đúng bản CUDA, hoặc `--no-4bit` nếu VRAM dư |
| Train xong sinh ra văn lặp | learning rate quá cao hoặc epochs quá nhiều | giảm `--lr` xuống 1e-4, `--epochs 2` |

## 6. Liên kết

- Kế hoạch thực nghiệm và ngưỡng thành công: [`Plan/03_KE_HOACH_THUC_NGHIEM.md`](../Plan/03_KE_HOACH_THUC_NGHIEM.md)
- Thiết kế dataset SFT: [`Plan/02_KE_HOACH_DU_LIEU.md`](../Plan/02_KE_HOACH_DU_LIEU.md) §7
- Sổ đăng ký adapter phía backend: `backend/app/services/adapters.py`
