"""Sinh embedding cho chunk và truy vấn (Tuần 3).

Hai backend cùng một giao diện:

- `sentence-transformers` — model thật (mặc định `BAAI/bge-m3`, ứng viên trong
  Plan/03 §3), tự dùng GPU nếu có. Đây là backend dùng cho mọi số liệu báo cáo.
- `hashing` — vector băm tất định, không phụ thuộc model/GPU/mạng. Chỉ dùng cho
  test và CI để pipeline chạy được ở mọi máy; **không dùng cho kết quả thí nghiệm**.

Model được ghi kèm từng chunk (`chunks.embedding_model`) nên khi đổi model, pipeline
biết chunk nào cần embed lại — bắt buộc cho yêu cầu tái lập của Plan/03 §7.
"""

import hashlib
import math

from app.core.config import settings

HASHING_BACKEND = "hashing"
_NGRAM = 3


class HashingEmbedder:
    """Vector băm tất định (hashing trick) — placeholder cho test, không có ngữ nghĩa."""

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.name = f"hashing-{dim}"
        self.device = "cpu"

    def _tokens(self, text: str) -> list[str]:
        words = text.lower().split()
        grams = [" ".join(words[i : i + _NGRAM]) for i in range(max(len(words) - _NGRAM + 1, 0))]
        return words + grams

    def encode(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        out = []
        for text in texts:
            vector = [0.0] * self.dim
            for token in self._tokens(text):
                digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
                value = int.from_bytes(digest, "big")
                vector[value % self.dim] += 1.0 if value >> 63 & 1 else -1.0
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            out.append([v / norm for v in vector])
        return out


class SentenceTransformerEmbedder:
    """Model thật. Tự chọn CUDA khi máy có GPU; chuẩn hóa L2 để dùng cosine."""

    def __init__(self, model_name: str, device: str, batch_size: int, max_length: int) -> None:
        from sentence_transformers import SentenceTransformer  # import chậm → để trong hàm

        if device == "auto":
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, device=device)
        self.model.max_seq_length = max_length
        self.name = model_name
        self.device = device
        self.batch_size = batch_size
        self.dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        # bge-m3 không cần prefix instruction; e5 thì cần → xử lý theo tên model
        if "e5" in self.name.lower():
            prefix = "query: " if is_query else "passage: "
            texts = [prefix + t for t in texts]
        vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return [v.tolist() for v in vectors]


_cache: dict[tuple[str, str, int], object] = {}


def get_embedder():
    """Trả embedder theo cấu hình hiện hành (cache theo backend+model+dim)."""
    key = (settings.embedding_backend, settings.embedding_model, settings.embedding_dim)
    if key not in _cache:
        if settings.embedding_backend == HASHING_BACKEND:
            _cache[key] = HashingEmbedder(settings.embedding_dim)
        else:
            _cache[key] = SentenceTransformerEmbedder(
                settings.embedding_model,
                settings.embedding_device,
                settings.embedding_batch_size,
                settings.embedding_max_length,
            )
    return _cache[key]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine cho đường SQLite (PostgreSQL dùng toán tử `<=>` của pgvector)."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
