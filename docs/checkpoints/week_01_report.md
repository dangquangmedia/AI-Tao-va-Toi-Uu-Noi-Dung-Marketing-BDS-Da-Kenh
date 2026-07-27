# Checkpoint Tuần 1 — Nền tảng + ingestion DataBDS

**Ngày:** 27/07/2026 · **Branch:** `tuan-01-nen-tang` · **Người thực hiện:** Quang (+ Claude hỗ trợ)

## Kết quả so với gate Tuần 1 ([Plan/01 §6](../../Plan/01_KE_HOACH_TONG_THE.md))

| Hạng mục gate | Trạng thái | Bằng chứng |
|---|---|---|
| Monorepo FastAPI + Next.js | ✅ | `backend/` (FastAPI + SQLAlchemy + Alembic), `frontend/` (Next.js 15.5.22) |
| PostgreSQL + pgvector + migrations | ✅ | Docker `pgvector/pg16`, extension vector 0.8.5, migration `8750eb3aca2c`, 7 bảng |
| Auth JWT + RBAC 3 role + tenant isolation | ✅ | `app/deps.py`, tests pass; E2E: reviewer bị 403, tenant khác thấy 0 dữ liệu |
| Project CRUD | ✅ | API + UI; E2E tạo "Vinhomes Central Park" |
| Import ≥100 tin DataBDS không sửa tay | ✅ | 200 tin import lần 1 `inserted=200`; **lần 2 `unchanged=200`, tổng vẫn 200 → idempotent** |
| Quarantine bản ghi lỗi | ✅ | Service + tests (missing id, thiếu provenance); batch thật 200 tin: 0 quarantine |
| Tests tự động | ✅ | **13/13 pass** — auth (6), tenant isolation (2), ingestion (5) |
| CI | ✅ | `.github/workflows/ci.yml` (pytest + next build) — chạy khi push |
| UI vertical slice sau đăng nhập | ✅ | Login → /projects: stats raw zone + danh sách + tạo dự án (screenshot trong report nhật ký) |
| Staging URL | ⏳ **chưa** | Cần tài khoản cloud của Quang (Vercel/Railway/...) — carry-over sang Tuần 2 |

## Cách chạy local

```powershell
docker compose up -d                      # Postgres + pgvector (cổng 5432)
cd backend
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m app.seed    # admin/marketer/reviewer@cancu.demo · mật khẩu cancu123
.\.venv\Scripts\python.exe -m app.ingest_cli --limit 200
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
cd ..\frontend
npm run dev                               # http://localhost:3000 (API base: .env.local)
```

Lưu ý môi trường: cổng 8000 trên máy này bị process `latcat.exe` (Go) chiếm → backend chạy cổng **8001**.

## Quyết định kỹ thuật trong tuần

- Tests API dùng SQLite in-memory (nhanh, không phụ thuộc Docker); hành vi trên Postgres thật được xác minh bằng E2E thủ công có log ở trên. Sang Tuần 3 (khi có vector search) sẽ thêm test chạy thẳng Postgres.
- Raw zone lưu nguyên văn JSON của từng tin (`source_listings.raw`); provenance lấy từ `source_listing_*.csv` (canonical_url + content_hash). Đúng nguyên tắc Plan/02: không sửa dữ liệu gốc.
- Next 15.1.6 dính CVE-2025-66478 → nâng 15.5.22 ngay khi cài.

## Carry-over sang Tuần 2

| Việc | Owner | Ghi chú |
|---|---|---|
| Deploy staging (frontend + backend + managed Postgres) | Quang | Cần Anh chọn nền tảng + cấp tài khoản |
| Import toàn bộ 4.795 tin (hiện mới 200 để demo) | Quang | Chạy `ingest_cli` không limit sau khi staging sẵn sàng |
| Re-parse D1 (giá/project/pháp lý từ title+description+URL) | Hải | Theo Plan/02 §4 — bắt đầu Tuần 2 |
| Khóa `crawler_contract_v1.json` chính thức | Hải | Contract nháp đang nằm trong Plan/02 §3 |
