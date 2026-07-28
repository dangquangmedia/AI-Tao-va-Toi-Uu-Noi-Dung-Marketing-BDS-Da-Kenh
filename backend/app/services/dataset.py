"""Chia tập chống leakage và đóng băng `dataset_v1` (Tuần 3, Plan/02 §6).

Nguyên tắc học thuật quan trọng nhất ở đây: **chia theo dự án, không chia theo mẫu**.
Toàn bộ tin/ảnh/fact/mẫu SFT của một dự án chỉ thuộc đúng một split, nên model không
thể "thấy trước" dự án của test dưới bất kỳ dạng nào.

Chi tiết cài đặt:
- Đơn vị chia của Tier A là **dự án**; của tin lẻ (không thuộc dự án) là **cụm dedup**
  — cả cụm vào cùng split để bản đăng lại không rơi sang split khác.
- Stratify theo quy mô (số tin) để test không toàn dự án 1 tin.
- Gán split tất định bằng hash của khóa đơn vị: chạy lại cho đúng cùng kết quả, và
  thêm dữ liệu mới cũng không xáo trộn dự án cũ giữa các split.
- Sau khi chia, chạy **leakage audit**: kiểm tra không có cụm dedup nào nằm ở hai split.
"""

import hashlib
from collections import defaultdict

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import CleanListing, DatasetSplit

SPLIT_RATIOS = (("train", 0.70), ("validation", 0.15), ("test", 0.15))
HASH_BUCKETS = 10_000
STRATA = ((5, "large"), (2, "medium"), (1, "small"))


def _stratum(n_listings: int) -> str:
    for threshold, name in STRATA:
        if n_listings >= threshold:
            return name
    return "small"


def _bucket(key: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:{key}".encode()).hexdigest()
    return int(digest[:8], 16) % HASH_BUCKETS / HASH_BUCKETS


def assign_split(key: str, salt: str) -> str:
    """Gán split tất định theo hash khóa đơn vị (không phụ thuộc thứ tự hay thời điểm chạy)."""
    position = _bucket(key, salt)
    cumulative = 0.0
    for name, ratio in SPLIT_RATIOS:
        cumulative += ratio
        if position < cumulative:
            return name
    return SPLIT_RATIOS[-1][0]


def build_dataset_split(db: Session, tenant_id: str, dataset_version: str) -> dict:
    """Dựng (hoặc dựng lại) split cho một phiên bản dataset. Idempotent."""
    rows = db.scalars(select(CleanListing).where(CleanListing.tenant_id == tenant_id)).all()

    units: dict[tuple[str, str], list[CleanListing]] = defaultdict(list)
    for row in rows:
        if row.project_slug:
            units[("project", row.project_slug)].append(row)
        else:
            units[("cluster", row.dedup_cluster_id)].append(row)

    db.execute(
        delete(DatasetSplit).where(
            DatasetSplit.tenant_id == tenant_id, DatasetSplit.dataset_version == dataset_version
        )
    )

    summary: dict[str, dict[str, int]] = {
        split: {"units": 0, "listings": 0} for split, _ in SPLIT_RATIOS
    }
    for (unit_type, unit_key), members in sorted(units.items()):
        # Salt theo phiên bản dataset → đổi version thì chia lại, giữ version thì bất biến
        split = assign_split(f"{unit_type}:{unit_key}", dataset_version)
        db.add(
            DatasetSplit(
                tenant_id=tenant_id,
                dataset_version=dataset_version,
                unit_type=unit_type,
                unit_key=unit_key,
                split=split,
                stratum=_stratum(len(members)),
                n_listings=len(members),
            )
        )
        summary[split]["units"] += 1
        summary[split]["listings"] += len(members)
    db.commit()
    return summary


def split_of_listing(db: Session, tenant_id: str, dataset_version: str) -> dict[str, str]:
    """map clean_listing_id → split (dùng cho SFT builder và gold queries)."""
    assignments = {
        (row.unit_type, row.unit_key): row.split
        for row in db.scalars(
            select(DatasetSplit).where(
                DatasetSplit.tenant_id == tenant_id,
                DatasetSplit.dataset_version == dataset_version,
            )
        ).all()
    }
    out = {}
    for row in db.scalars(select(CleanListing).where(CleanListing.tenant_id == tenant_id)).all():
        key = ("project", row.project_slug) if row.project_slug else ("cluster", row.dedup_cluster_id)
        split = assignments.get(key)
        if split:
            out[row.id] = split
    return out


def leakage_audit(db: Session, tenant_id: str, dataset_version: str) -> dict:
    """Kiểm tra rò rỉ: cụm dedup hoặc dự án nằm ở nhiều split.

    Đây là bằng chứng bắt buộc cho hội đồng — không có audit thì không chứng minh
    được kết quả thí nghiệm không bị thổi phồng do trùng dữ liệu.
    """
    listing_split = split_of_listing(db, tenant_id, dataset_version)
    rows = db.scalars(select(CleanListing).where(CleanListing.tenant_id == tenant_id)).all()

    cluster_splits: dict[str, set[str]] = defaultdict(set)
    project_splits: dict[str, set[str]] = defaultdict(set)
    unassigned = 0
    for row in rows:
        split = listing_split.get(row.id)
        if split is None:
            unassigned += 1
            continue
        cluster_splits[row.dedup_cluster_id].add(split)
        if row.project_slug:
            project_splits[row.project_slug].add(split)

    leaking_clusters = sorted(k for k, v in cluster_splits.items() if len(v) > 1)
    leaking_projects = sorted(k for k, v in project_splits.items() if len(v) > 1)
    return {
        "listings_total": len(rows),
        "listings_assigned": len(listing_split),
        "listings_unassigned": unassigned,
        "clusters_checked": len(cluster_splits),
        "projects_checked": len(project_splits),
        "leaking_clusters": leaking_clusters,
        "leaking_projects": leaking_projects,
        "passed": not leaking_clusters and not leaking_projects and unassigned == 0,
    }


def split_report(db: Session, tenant_id: str, dataset_version: str) -> dict:
    """Số liệu split để đưa vào data card."""
    rows = db.execute(
        select(
            DatasetSplit.split,
            DatasetSplit.unit_type,
            DatasetSplit.stratum,
            func.count(),
            func.sum(DatasetSplit.n_listings),
        )
        .where(
            DatasetSplit.tenant_id == tenant_id, DatasetSplit.dataset_version == dataset_version
        )
        .group_by(DatasetSplit.split, DatasetSplit.unit_type, DatasetSplit.stratum)
    ).all()

    by_split: dict[str, dict] = {}
    for split, unit_type, stratum, units, listings in rows:
        entry = by_split.setdefault(
            split, {"units": 0, "listings": 0, "by_unit_type": {}, "by_stratum": {}}
        )
        entry["units"] += units
        entry["listings"] += listings or 0
        entry["by_unit_type"][unit_type] = entry["by_unit_type"].get(unit_type, 0) + units
        entry["by_stratum"][stratum] = entry["by_stratum"].get(stratum, 0) + units

    total_units = sum(e["units"] for e in by_split.values()) or 1
    total_listings = sum(e["listings"] for e in by_split.values()) or 1
    for entry in by_split.values():
        entry["unit_pct"] = round(100 * entry["units"] / total_units, 1)
        entry["listing_pct"] = round(100 * entry["listings"] / total_listings, 1)
    return by_split
