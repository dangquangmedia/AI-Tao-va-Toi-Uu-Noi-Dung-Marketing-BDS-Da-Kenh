"""QLoRA SFT — chạy trên máy GPU rời hoặc Colab, không cần backend/DB (Tuần 5).

Script này **cố ý độc lập hoàn toàn** với `backend/`: đầu vào là hai file JSONL do
`python -m app.sft_cli` xuất ra, đầu ra là một thư mục adapter copy thẳng về
`backend/models/adapters/` là dùng được. Nhờ vậy máy train không cần PostgreSQL, không
cần cài phụ thuộc của web app, và người train không phải hiểu kiến trúc backend.

Chỉ dùng `transformers` + `peft` + `bitsandbytes`, **không dùng TRL**: API của TRL đổi
nhiều giữa các bản, mà máy train là môi trường không kiểm soát được (Colab thay version
liên tục). Vòng huấn luyện tự viết ở đây ngắn và ổn định hơn.

Điểm kỹ thuật quan trọng: **loss chỉ tính trên phần trả lời**. Token của prompt bị gán
nhãn -100. Nếu tính loss cả trên prompt, model sẽ dành sức học thuộc prompt (vốn giống
nhau ở mọi mẫu) thay vì học cách viết.

Chạy:
    python qlora_train.py --train train.jsonl --val validation.jsonl \\
        --base-model Qwen/Qwen2.5-7B-Instruct --out ../backend/models/adapters/qwen25-7b-r16

    python qlora_train.py --smoke --out /tmp/smoke   # kiểm tra môi trường, ~2 phút
"""

import argparse
import json
import platform
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)

# Mặc định cho họ Qwen/Llama; model khác có tên module khác thì truyền --target-modules
DEFAULT_TARGET_MODULES = "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj"
IGNORE_INDEX = -100


class ChatSftDataset(Dataset):
    """Mẫu `messages` → input_ids + labels, che phần prompt khỏi loss."""

    def __init__(self, path: Path, tokenizer, max_len: int) -> None:
        self.rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.skipped = 0
        self.examples = [ex for ex in (self._encode(r) for r in self.rows) if ex is not None]

    def _encode(self, row: dict) -> dict | None:
        messages = row["messages"]
        prompt_text = self.tokenizer.apply_chat_template(
            messages[:-1], tokenize=False, add_generation_prompt=True
        )
        full_text = prompt_text + messages[-1]["content"] + (self.tokenizer.eos_token or "")

        prompt_ids = self.tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
        full_ids = self.tokenizer(full_text, add_special_tokens=False)["input_ids"][: self.max_len]
        if len(prompt_ids) >= len(full_ids):
            # Prompt dài hơn cả max_len → cắt xong không còn phần trả lời để học
            self.skipped += 1
            return None
        labels = [IGNORE_INDEX] * len(prompt_ids) + full_ids[len(prompt_ids) :]
        return {"input_ids": full_ids, "labels": labels[: len(full_ids)]}

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict:
        return self.examples[idx]


def collate(batch: list[dict], pad_id: int) -> dict:
    width = max(len(item["input_ids"]) for item in batch)
    input_ids, labels, attention = [], [], []
    for item in batch:
        pad = width - len(item["input_ids"])
        input_ids.append(item["input_ids"] + [pad_id] * pad)
        labels.append(item["labels"] + [IGNORE_INDEX] * pad)
        attention.append([1] * len(item["input_ids"]) + [0] * pad)
    return {
        "input_ids": torch.tensor(input_ids),
        "labels": torch.tensor(labels),
        "attention_mask": torch.tensor(attention),
    }


def write_smoke_data(path: Path, n: int = 24) -> None:
    """Dữ liệu giả để kiểm tra môi trường GPU trước khi chạy thật.

    Adapter sinh ra từ đây bị đánh dấu `smoke: true` trong card và backend sẽ cảnh báo —
    tránh việc lỡ tay đưa số đo của bản smoke vào báo cáo.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for i in range(n):
            handle.write(
                json.dumps(
                    {
                        "sample_id": f"smoke-{i}",
                        "split": "train",
                        "messages": [
                            {"role": "system", "content": "Bạn là trợ lý viết nội dung bất động sản."},
                            {"role": "user", "content": f"Viết mô tả ngắn cho căn hộ {i + 1} phòng ngủ."},
                            {
                                "role": "assistant",
                                "content": f"HEADLINE: Căn hộ {i + 1} phòng ngủ\nBODY:\nCăn hộ {i + 1} phòng ngủ, "
                                "phù hợp gia đình nhỏ.\nCTA: Liên hệ để xem nhà.",
                            },
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def build_card(args, train_ds, eval_ds, metrics: dict, elapsed: float, target_modules: list[str]) -> dict:
    return {
        "name": Path(args.out).name,
        "base_model": args.base_model,
        "dataset_version": args.dataset_version,
        "prompt_version": args.prompt_version,
        "train_samples": len(train_ds),
        "val_samples": len(eval_ds) if eval_ds else 0,
        "skipped_too_long": train_ds.skipped + (eval_ds.skipped if eval_ds else 0),
        "quantization": "nf4-4bit" if args.load_in_4bit else "fp16/bf16",
        "lora": {
            "r": args.rank,
            "alpha": args.alpha,
            "dropout": args.dropout,
            "target_modules": target_modules,
        },
        "training": {
            "epochs": args.epochs,
            "learning_rate": args.lr,
            "batch_size": args.batch_size,
            "grad_accum": args.grad_accum,
            "max_seq_len": args.max_seq_len,
            "seed": args.seed,
            "warmup_ratio": args.warmup_ratio,
        },
        "metrics": metrics,
        "elapsed_minutes": round(elapsed / 60, 1),
        "hardware": torch.cuda.get_device_name(0) if torch.cuda.is_available() else platform.processor(),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "versions": {"torch": torch.__version__, "python": platform.python_version()},
        "smoke": bool(args.smoke),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="train.jsonl")
    parser.add_argument("--val", default="validation.jsonl")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--out", required=True, help="thư mục adapter đầu ra")
    parser.add_argument("--rank", type=int, default=16, help="Plan/03 §3: tìm trong {8,16,32}")
    parser.add_argument("--alpha", type=int, default=32)
    parser.add_argument("--dropout", type=float, default=0.05)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=16)
    parser.add_argument("--max-seq-len", type=int, default=1536)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target-modules", default=DEFAULT_TARGET_MODULES)
    parser.add_argument("--no-4bit", dest="load_in_4bit", action="store_false")
    parser.add_argument("--dataset-version", default="dataset_v1")
    parser.add_argument("--prompt-version", default="prompt_v1")
    parser.add_argument("--smoke", action="store_true", help="chạy thử bằng dữ liệu giả")
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    out_dir = Path(args.out)
    if args.smoke:
        smoke_path = out_dir / "_smoke_train.jsonl"
        write_smoke_data(smoke_path)
        args.train, args.val = str(smoke_path), ""
        args.epochs, args.max_seq_len = 1.0, 512

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    train_ds = ChatSftDataset(Path(args.train), tokenizer, args.max_seq_len)
    eval_ds = (
        ChatSftDataset(Path(args.val), tokenizer, args.max_seq_len)
        if args.val and Path(args.val).exists()
        else None
    )
    if not len(train_ds):
        raise SystemExit(f"Không có mẫu train nào đọc được từ {args.train}")
    print(f"Train {len(train_ds)} mẫu · validation {len(eval_ds) if eval_ds else 0} mẫu", flush=True)

    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    compute_dtype = torch.bfloat16 if bf16 else torch.float16
    load_kwargs: dict = {"torch_dtype": compute_dtype}
    if args.load_in_4bit and torch.cuda.is_available():
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )
        load_kwargs["device_map"] = {"": 0}

    model = AutoModelForCausalLM.from_pretrained(args.base_model, **load_kwargs)
    if "quantization_config" in load_kwargs:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.config.use_cache = False  # bắt buộc tắt khi bật gradient checkpointing

    target_modules = [m.strip() for m in args.target_modules.split(",") if m.strip()]
    model = get_peft_model(
        model,
        LoraConfig(
            r=args.rank,
            lora_alpha=args.alpha,
            lora_dropout=args.dropout,
            target_modules=target_modules,
            bias="none",
            task_type="CAUSAL_LM",
        ),
    )
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=str(out_dir / "_checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="cosine",
        logging_steps=5,
        save_strategy="no",  # chỉ lưu adapter cuối; checkpoint giữa chừng tốn đĩa Colab
        bf16=bf16,
        fp16=not bf16 and torch.cuda.is_available(),
        gradient_checkpointing=True,
        optim="paged_adamw_8bit" if args.load_in_4bit else "adamw_torch",
        report_to=[],
        seed=args.seed,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        data_collator=lambda batch: collate(batch, tokenizer.pad_token_id),
    )

    started = time.time()
    result = trainer.train()
    metrics = {"train_loss": round(float(result.training_loss), 4)}
    if eval_ds is not None and len(eval_ds):
        evaluation = trainer.evaluate(eval_dataset=eval_ds)
        metrics["eval_loss"] = round(float(evaluation.get("eval_loss", 0.0)), 4)
    elapsed = time.time() - started

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    card = build_card(args, train_ds, eval_ds, metrics, elapsed, target_modules)
    (out_dir / "adapter_card.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nXong sau {card['elapsed_minutes']} phút — {metrics}")
    print(f"Adapter: {out_dir}")
    print("Copy nguyên thư mục này vào backend/models/adapters/ là cấu hình C/D chạy được.")
    if args.smoke:
        print("LƯU Ý: đây là bản smoke bằng dữ liệu giả — không dùng cho số liệu báo cáo.")


if __name__ == "__main__":
    main()
