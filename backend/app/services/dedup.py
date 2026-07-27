"""D3 — khử trùng lặp (Plan/02 §4).

Hai mức:
1. **Trùng chính xác** theo `content_hash` của nguồn.
2. **Gần trùng** theo SimHash 64-bit trên shingle của mô tả đã chuẩn hóa
   (cùng một căn được đăng lại nhiều lần, đổi vài từ).

Cụm được đặt tên theo `source_listing_id` nhỏ nhất trong cụm nên kết quả
**không phụ thuộc thứ tự xử lý** — chạy lại pipeline cho cùng cụm, cùng đại diện.
"""

import hashlib
import re

from app.services.reparse import deaccent

SIMHASH_BITS = 64
# Đo trên 4.795 mô tả thật: sửa vài từ trong một tin → khoảng cách ~6 bit;
# hai tin ngẫu nhiên → trung vị 32 bit (1% thấp nhất vẫn ~23). Ngưỡng 6 tách sạch
# hai phân bố; nới lên 12 cũng chỉ thêm ~10 tin nên kết quả không nhạy với ngưỡng.
HAMMING_THRESHOLD = 6
# 8 băng × 8 bit: theo nguyên lý chuồng bồ câu, hai chuỗi lệch ≤7 bit chắc chắn
# trùng ít nhất một băng → lọc ứng viên mà không bỏ sót ở ngưỡng 6.
BAND_BITS = 8
SHINGLE_SIZE = 3
MIN_TOKENS_FOR_SIMHASH = SHINGLE_SIZE

_TOKEN = re.compile(r"[a-z0-9]+")


def _shingles(text: str) -> list[str]:
    tokens = _TOKEN.findall(deaccent(text))
    if len(tokens) < MIN_TOKENS_FOR_SIMHASH:
        return tokens
    return [" ".join(tokens[i : i + SHINGLE_SIZE]) for i in range(len(tokens) - SHINGLE_SIZE + 1)]


def simhash(text: str) -> str:
    """SimHash 64-bit → chuỗi hex 16 ký tự (rỗng nếu text quá ngắn)."""
    shingles = _shingles(text)
    if not shingles:
        return ""
    vector = [0] * SIMHASH_BITS
    for shingle in shingles:
        digest = int.from_bytes(hashlib.blake2b(shingle.encode(), digest_size=8).digest(), "big")
        for bit in range(SIMHASH_BITS):
            vector[bit] += 1 if digest >> bit & 1 else -1
    value = 0
    for bit in range(SIMHASH_BITS):
        if vector[bit] > 0:
            value |= 1 << bit
    return f"{value:016x}"


def hamming(a: str, b: str) -> int:
    if not a or not b:
        return SIMHASH_BITS
    return bin(int(a, 16) ^ int(b, 16)).count("1")


class _Union:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # Gốc là key nhỏ hơn → tên cụm ổn định, không phụ thuộc thứ tự
            lo, hi = sorted((ra, rb))
            self.parent[hi] = lo


def build_clusters(records: list[dict]) -> dict[str, dict]:
    """records: [{key, content_hash, simhash, description_len}] → {key: {cluster_id, is_representative}}.

    `key` là `source_listing_id` (ổn định giữa các lần chạy, khác với id UUID trong DB).
    """
    union = _Union()
    by_hash: dict[str, str] = {}
    buckets: dict[tuple[int, int], list[dict]] = {}

    for rec in sorted(records, key=lambda r: r["key"]):
        key = rec["key"]
        union.find(key)

        content_hash = rec.get("content_hash") or ""
        if content_hash:
            if content_hash in by_hash:
                union.union(by_hash[content_hash], key)
            else:
                by_hash[content_hash] = key

        sim = rec.get("simhash") or ""
        if not sim:
            continue
        value = int(sim, 16)
        for band in range(SIMHASH_BITS // BAND_BITS):
            slot = (band, value >> (band * BAND_BITS) & ((1 << BAND_BITS) - 1))
            for other in buckets.setdefault(slot, []):
                if hamming(sim, other["simhash"]) <= HAMMING_THRESHOLD:
                    union.union(other["key"], key)
            buckets[slot].append(rec)

    members: dict[str, list[dict]] = {}
    for rec in records:
        members.setdefault(union.find(rec["key"]), []).append(rec)

    out: dict[str, dict] = {}
    for cluster_id, group in members.items():
        # Đại diện: mô tả dài nhất; hòa thì lấy key nhỏ nhất → tất định
        representative = min(group, key=lambda r: (-r.get("description_len", 0), r["key"]))["key"]
        for rec in group:
            out[rec["key"]] = {
                "cluster_id": cluster_id,
                "is_representative": rec["key"] == representative,
                "cluster_size": len(group),
            }
    return out
