"""Sổ đăng ký LoRA adapter — điểm ghép giữa máy train và backend (Tuần 5).

Bài toán thực tế của nhóm: GPU 4GB của Quang không đủ chạy QLoRA 7–8B, nên **Hải train
ở máy khác hoặc Colab**. Nếu quy trình ghép không được định nghĩa trước thì mỗi lần bàn
giao lại phải sửa code — chậm và dễ sai.

Hợp đồng bàn giao (chi tiết ở `training/README.md`):

    backend/models/adapters/<ten-adapter>/
        adapter_config.json          ← peft sinh ra
        adapter_model.safetensors    ← trọng số LoRA (vài chục MB)
        adapter_card.json            ← `training/qlora_train.py` ghi: backbone, siêu tham
                                       số, dataset version, seed, loss, phần cứng

Copy nguyên thư mục vào `adapter_dir` là backend nhận ra ngay — **không phải sửa code,
không phải restart để đổi cấu hình**. Module này chỉ đọc đĩa và kiểm tra tính hợp lệ;
việc nạp trọng số nằm ở `services/llm.py`.

Vì sao phải có `adapter_card.json`: Plan/03 §7 bắt buộc mỗi kết quả thí nghiệm phải truy
được về backbone + siêu tham số + dataset version. Adapter không kèm card thì vẫn nạp
được nhưng bị đánh dấu thiếu metadata, và số đo từ nó không đưa vào báo cáo.
"""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

CARD_NAME = "adapter_card.json"
PEFT_CONFIG_NAME = "adapter_config.json"
WEIGHT_NAMES = ("adapter_model.safetensors", "adapter_model.bin")
# Trường bắt buộc trong card để số đo dùng được cho báo cáo
REQUIRED_CARD_FIELDS = ("base_model", "dataset_version", "lora", "training")


def adapters_root() -> Path:
    """Thư mục chứa adapter (tương đối tính từ `backend/`)."""
    root = Path(settings.adapter_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root
    return root


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


@lru_cache(maxsize=32)
def _fingerprint(path_str: str, size: int, mtime_ns: int) -> str:
    """SHA-256 của file trọng số — định danh chính xác adapter đã dùng cho một lần sinh.

    Cache theo (đường dẫn, kích thước, mtime) để không băm lại file vài chục MB mỗi
    request; file bị thay thì mtime đổi nên cache tự hỏng.
    """
    digest = hashlib.sha256()
    with Path(path_str).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()[:16]


def describe(path: Path) -> dict:
    """Mô tả một thư mục adapter: metadata + có nạp được không + thiếu gì."""
    problems: list[str] = []
    card = _read_json(path / CARD_NAME)
    peft_config = _read_json(path / PEFT_CONFIG_NAME)
    weight = next((path / name for name in WEIGHT_NAMES if (path / name).exists()), None)

    if peft_config is None:
        problems.append(f"thiếu {PEFT_CONFIG_NAME}")
    if weight is None:
        problems.append("thiếu file trọng số adapter_model.safetensors|.bin")

    if card is None:
        problems.append(f"thiếu {CARD_NAME} — nạp được nhưng số đo không dùng cho báo cáo")
    else:
        missing = [f for f in REQUIRED_CARD_FIELDS if not card.get(f)]
        if missing:
            problems.append(f"{CARD_NAME} thiếu trường: {', '.join(missing)}")
        if card.get("smoke"):
            # `qlora_train.py --smoke` train trên dữ liệu giả để kiểm tra môi trường GPU.
            # Vẫn nạp được (đúng mục đích), nhưng phải hiện cảnh báo để không ai lỡ tay
            # lấy số đo của nó đưa vào báo cáo.
            problems.append("adapter chạy thử bằng dữ liệu giả — không dùng cho số liệu báo cáo")

    # Backbone lấy từ card, thiếu thì lấy từ chính cấu hình peft — cách nào cũng phải có,
    # vì nạp adapter lên sai base model sẽ ra output rác chứ không báo lỗi.
    base_model = (card or {}).get("base_model") or (peft_config or {}).get("base_model_name_or_path")
    if not base_model:
        problems.append("không xác định được base_model")

    fingerprint = ""
    if weight is not None:
        stat = weight.stat()
        fingerprint = _fingerprint(str(weight), stat.st_size, stat.st_mtime_ns)

    return {
        "name": path.name,
        "path": str(path),
        "base_model": base_model,
        "fingerprint": fingerprint,
        "card": card or {},
        "has_card": card is not None,
        "loadable": weight is not None and peft_config is not None and bool(base_model),
        "problems": problems,
        "size_mb": round(weight.stat().st_size / 1e6, 1) if weight else 0.0,
    }


def list_adapters() -> list[dict]:
    """Mọi adapter tìm thấy trên đĩa, sắp theo tên. Thư mục trống → danh sách rỗng."""
    root = adapters_root()
    if not root.is_dir():
        return []
    return [describe(child) for child in sorted(root.iterdir()) if child.is_dir()]


def get_adapter(name: str) -> dict:
    """Lấy adapter theo tên, báo lỗi *nói rõ phải làm gì* nếu chưa có.

    Thông báo lỗi ở đây là thứ người dùng UI nhìn thấy khi bấm chạy cấu hình C/D lúc
    chưa bàn giao adapter, nên phải chỉ đúng thư mục cần copy vào.
    """
    root = adapters_root()
    path = root / name
    if not name or not path.is_dir():
        available = [a["name"] for a in list_adapters()]
        raise FileNotFoundError(
            f"Chưa có adapter '{name}' trong {root}. "
            f"Adapter đang có: {', '.join(available) if available else '(chưa có cái nào)'}. "
            "Copy thư mục adapter đã train vào đó — xem training/README.md."
        )
    info = describe(path)
    if not info["loadable"]:
        raise ValueError(f"Adapter '{name}' không nạp được: {'; '.join(info['problems'])}")
    return info


def default_adapter_name() -> str:
    """Adapter dùng cho C/D khi request không chỉ định.

    Ưu tiên cấu hình `llm_adapter`; nếu để trống mà trên đĩa chỉ có đúng một adapter thì
    dùng luôn cái đó — trường hợp phổ biến nhất sau khi Hải bàn giao lần đầu.
    """
    if settings.llm_adapter:
        return settings.llm_adapter
    loadable = [a["name"] for a in list_adapters() if a["loadable"]]
    return loadable[0] if len(loadable) == 1 else ""
