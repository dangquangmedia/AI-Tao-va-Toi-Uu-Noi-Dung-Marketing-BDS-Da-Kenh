"""Seed dữ liệu demo: 1 tenant + 3 user theo 3 role + 1 tenant phụ để test isolation.

Chạy: python -m app.seed
"""

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Tenant, User

DEMO_PASSWORD = "cancu123"

USERS = [
    ("admin@cancu.demo", "Quản trị viên", "admin"),
    ("marketer@cancu.demo", "Nhân viên marketing", "marketer"),
    ("reviewer@cancu.demo", "Người duyệt nội dung", "reviewer"),
]


def seed() -> None:
    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == "cancu-demo"))
        if tenant is None:
            tenant = Tenant(name="Căn Cứ Demo", slug="cancu-demo")
            db.add(tenant)
            db.flush()

        other = db.scalar(select(Tenant).where(Tenant.slug == "tenant-khac"))
        if other is None:
            other = Tenant(name="Tenant Khác (test isolation)", slug="tenant-khac")
            db.add(other)
            db.flush()

        for email, name, role in USERS:
            if db.scalar(select(User).where(User.email == email)) is None:
                db.add(
                    User(
                        tenant_id=tenant.id,
                        email=email,
                        full_name=name,
                        role=role,
                        hashed_password=hash_password(DEMO_PASSWORD),
                    )
                )
        if db.scalar(select(User).where(User.email == "admin@khac.demo")) is None:
            db.add(
                User(
                    tenant_id=other.id,
                    email="admin@khac.demo",
                    full_name="Admin tenant khác",
                    role="admin",
                    hashed_password=hash_password(DEMO_PASSWORD),
                )
            )
        db.commit()
        print("Seed xong: admin/marketer/reviewer@cancu.demo + admin@khac.demo, mật khẩu:", DEMO_PASSWORD)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
