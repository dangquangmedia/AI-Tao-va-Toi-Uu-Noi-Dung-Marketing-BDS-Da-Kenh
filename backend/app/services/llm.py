"""Model gateway — một giao diện cho mọi generator (Tuần 4, Plan/01 §4.3).

Bốn provider, cùng một hàm `generate()`:

- `local` — model mở chạy bằng transformers trên GPU máy (mặc định
  `Qwen/Qwen2.5-3B-Instruct`, tải 4-bit để vừa 4GB VRAM). Đây là generator dùng cho
  **kết quả thí nghiệm** vì chạy được offline, cố định seed, không phụ thuộc nhà cung cấp.
- `openai` / `google` — API thương mại, chỉ dùng cho demo khi cần chất lượng cao.
- `template` — bộ sinh mẫu tất định, không cần model. Dùng cho test/CI và cho máy
  không có GPU; **không bao giờ dùng cho số liệu báo cáo** (được đánh dấu rõ trong
  `generations.model_name`).

Mọi lần gọi đều trả kèm `usage` (token, thời gian, chi phí ước tính) để log lại phục vụ
so sánh A–D và phần "chi phí/độ trễ" trong Plan/03 §4.
"""

import time
from dataclasses import dataclass, field

from app.core.config import settings

TEMPLATE_PROVIDER = "template"
LOCAL_PROVIDER = "local"


@dataclass
class LlmResponse:
    text: str
    model_name: str
    provider: str
    usage: dict = field(default_factory=dict)


class TemplateGenerator:
    """Sinh nội dung bằng ghép mẫu từ chính context — tất định, không cần model.

    Giữ đúng hình dạng đầu ra (headline/body/cta) để pipeline phía sau test được.
    """

    provider = TEMPLATE_PROVIDER

    def __init__(self, adapter_name: str = "") -> None:
        # Cấu hình C/D chạy ở chế độ template (test/CI) vẫn ghi tên adapter vào log để
        # không nhầm với A/B; trọng số thì đương nhiên không được nạp.
        self.name = f"template-v1+{adapter_name}" if adapter_name else "template-v1"

    def generate(self, system: str, user: str, max_new_tokens: int = 512, seed: int = 42) -> LlmResponse:
        started = time.time()
        lines = [line.strip() for line in user.splitlines() if line.strip()]
        facts = [line for line in lines if line.startswith("-")][:6]
        headline = next((line for line in lines if line.startswith("Tiêu đề gợi ý:")), "")
        body = "\n".join(facts) if facts else "\n".join(lines[:5])
        text = (
            f"HEADLINE: {headline.replace('Tiêu đề gợi ý:', '').strip() or 'Bất động sản phù hợp nhu cầu của bạn'}\n"
            f"BODY:\n{body}\n"
            "CTA: Liên hệ để được tư vấn và xem thực tế."
        )
        return LlmResponse(
            text=text,
            model_name=self.name,
            provider=self.provider,
            usage={
                "prompt_chars": len(system) + len(user),
                "completion_chars": len(text),
                "latency_ms": int((time.time() - started) * 1000),
                "cost_usd": 0.0,
            },
        )


class LocalTransformersGenerator:
    """Model mở chạy tại chỗ. Ưu tiên 4-bit (bitsandbytes) để vừa GPU 4GB.

    Nạp thêm được **LoRA adapter** (cấu hình C/D): base model giữ nguyên, chỉ chồng
    trọng số adapter lên — đúng cách QLoRA phục vụ, và cho phép đổi adapter mà không
    tải lại backbone.
    """

    provider = LOCAL_PROVIDER

    def __init__(
        self,
        model_name: str,
        device: str,
        load_in_4bit: bool,
        max_new_tokens: int,
        adapter_path: str | None = None,
        adapter_name: str = "",
    ) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.name = f"{model_name}+{adapter_name}" if adapter_name else model_name
        self.base_model_name = model_name
        self.adapter_name = adapter_name
        self.device = device
        self.default_max_new_tokens = max_new_tokens
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        kwargs: dict = {"torch_dtype": torch.float16 if device == "cuda" else torch.float32}
        if load_in_4bit and device == "cuda":
            from transformers import BitsAndBytesConfig

            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            kwargs["device_map"] = {"": 0}
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
        if "quantization_config" not in kwargs:
            self.model = self.model.to(device)
        if adapter_path:
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, adapter_path, is_trainable=False)
        self.model.eval()

    def generate(self, system: str, user: str, max_new_tokens: int | None = None, seed: int = 42) -> LlmResponse:
        import torch

        torch.manual_seed(seed)
        started = time.time()
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens or self.default_max_new_tokens,
                do_sample=False,  # greedy → tái lập được, đúng yêu cầu Plan/03 §7
                pad_token_id=self.tokenizer.eos_token_id,
            )
        completion = output[0][inputs["input_ids"].shape[1] :]
        text = self.tokenizer.decode(completion, skip_special_tokens=True).strip()
        return LlmResponse(
            text=text,
            model_name=self.name,
            provider=self.provider,
            usage={
                "prompt_tokens": int(inputs["input_ids"].shape[1]),
                "completion_tokens": int(completion.shape[0]),
                "latency_ms": int((time.time() - started) * 1000),
                "cost_usd": 0.0,
                "device": self.device,
            },
        )


class OpenAiGenerator:
    provider = "openai"

    def __init__(self, model_name: str, api_key: str, base_url: str | None = None) -> None:
        self.name = model_name
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def generate(self, system: str, user: str, max_new_tokens: int = 800, seed: int = 42) -> LlmResponse:
        import httpx

        started = time.time()
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.name,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0,
                "seed": seed,
                "max_tokens": max_new_tokens,
            },
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        usage = payload.get("usage", {})
        return LlmResponse(
            text=payload["choices"][0]["message"]["content"].strip(),
            model_name=self.name,
            provider=self.provider,
            usage={
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "latency_ms": int((time.time() - started) * 1000),
            },
        )


_cache: dict[tuple, object] = {}


def get_generator(adapter: dict | None = None):
    """Trả generator theo cấu hình hiện hành (cache theo provider + model + adapter).

    `adapter` là bản mô tả lấy từ `services/adapters.py`. Khi có adapter, **backbone lấy
    theo adapter** chứ không theo `settings.llm_model`: adapter chỉ đúng với đúng base
    model nó được train, nạp lệch sẽ ra output rác mà không báo lỗi.
    """
    if adapter and settings.llm_provider not in (LOCAL_PROVIDER, TEMPLATE_PROVIDER):
        raise ValueError(
            f"Provider '{settings.llm_provider}' không nạp được LoRA adapter — "
            "cấu hình C/D phải chạy bằng model mở tại chỗ (llm_provider=local)"
        )
    adapter_name = adapter["name"] if adapter else ""
    base_model = adapter.get("base_model") if adapter else None
    model_name = base_model or settings.llm_model
    key = (settings.llm_provider, model_name, adapter_name)
    if key in _cache:
        return _cache[key]

    provider = settings.llm_provider
    if provider == TEMPLATE_PROVIDER:
        generator = TemplateGenerator(adapter_name)
    elif provider == LOCAL_PROVIDER:
        generator = LocalTransformersGenerator(
            model_name,
            settings.llm_device,
            settings.llm_load_in_4bit,
            settings.llm_max_new_tokens,
            adapter_path=adapter["path"] if adapter else None,
            adapter_name=adapter_name,
        )
    elif provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("Thiếu OPENAI_API_KEY cho provider openai")
        generator = OpenAiGenerator(
            settings.llm_model, settings.openai_api_key, settings.openai_base_url
        )
    else:
        raise ValueError(f"Provider LLM không hỗ trợ: {provider}")

    _cache[key] = generator
    return generator
