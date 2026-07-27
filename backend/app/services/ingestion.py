"""Adapter ingestion DataBDS → raw zone (source_listings).

Nguyên tắc (Plan/02 §3-4):
- Không sửa dữ liệu gốc: lưu nguyên văn bản ghi jsonl vào cột raw.
- Contract tối thiểu: source_listing_id + có dòng đối chiếu trong source_listing CSV
  (canonical_url + content_hash). Vi phạm → quarantine kèm error_code, không chặn batch.
- Idempotent: chạy lại cùng batch không sinh duplicate — khóa (tenant, source, source_listing_id);
  content_hash không đổi → unchanged, đổi → update bản raw.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IngestionJob, QuarantineRecord, SourceListing

SOURCE_NAME = "batdongsan"


def _load_source_index(source_csv: Path) -> dict[str, dict]:
    """Đọc source_listing CSV → index theo source_listing_id."""
    index: dict[str, dict] = {}
    with open(source_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            index[row["source_listing_id"]] = row
    return index


def find_databds_files(databds_dir: str | Path) -> tuple[Path, Path]:
    d = Path(databds_dir)
    jsonl = d / "listings.jsonl"
    csvs = sorted(d.glob("source_listing_*.csv"))
    if not jsonl.exists():
        raise FileNotFoundError(f"Không thấy {jsonl}")
    if not csvs:
        raise FileNotFoundError(f"Không thấy source_listing_*.csv trong {d}")
    return jsonl, csvs[-1]


def run_databds_import(
    db: Session,
    tenant_id: str,
    created_by: str,
    databds_dir: str | Path,
    limit: int | None = None,
) -> IngestionJob:
    jsonl_path, source_csv = find_databds_files(databds_dir)
    source_index = _load_source_index(source_csv)

    job = IngestionJob(tenant_id=tenant_id, created_by=created_by, status="running")
    db.add(job)
    db.flush()

    errors: dict[str, int] = {}

    def quarantine(code: str, ref: str, raw: dict) -> None:
        db.add(
            QuarantineRecord(
                tenant_id=tenant_id,
                ingestion_job_id=job.id,
                error_code=code,
                source_ref=ref,
                raw=raw,
            )
        )
        job.quarantined += 1
        errors[code] = errors.get(code, 0) + 1

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if limit is not None and job.total_read >= limit:
                break
            job.total_read += 1

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                quarantine("invalid_json", "", {"line": line[:500]})
                continue

            slid = str(record.get("source_listing_id") or "")
            if not slid:
                quarantine("missing_source_listing_id", "", record)
                continue

            src = source_index.get(slid)
            if src is None:
                quarantine("no_source_row", slid, record)
                continue
            if not src.get("canonical_url") or not src.get("content_hash"):
                quarantine("missing_provenance", slid, record)
                continue

            existing = db.scalar(
                select(SourceListing).where(
                    SourceListing.tenant_id == tenant_id,
                    SourceListing.source == SOURCE_NAME,
                    SourceListing.source_listing_id == slid,
                )
            )
            if existing is None:
                db.add(
                    SourceListing(
                        tenant_id=tenant_id,
                        source=SOURCE_NAME,
                        source_listing_id=slid,
                        canonical_url=src["canonical_url"],
                        content_hash=src["content_hash"],
                        listing_status=src.get("status", ""),
                        first_seen_at=src.get("first_seen_at", ""),
                        last_seen_at=src.get("last_seen_at", ""),
                        raw=record,
                        ingestion_job_id=job.id,
                    )
                )
                job.inserted += 1
            elif existing.content_hash == src["content_hash"]:
                job.unchanged += 1
            else:
                existing.content_hash = src["content_hash"]
                existing.raw = record
                existing.listing_status = src.get("status", "")
                existing.last_seen_at = src.get("last_seen_at", "")
                existing.ingestion_job_id = job.id
                job.updated += 1

    job.status = "done"
    job.error_summary = errors
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job
