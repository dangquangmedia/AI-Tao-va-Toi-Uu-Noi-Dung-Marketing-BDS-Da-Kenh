import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import Tenant, User

# Test không tải model thật: dùng embedder băm tất định (xem services/embeddings.py).
# Số liệu thí nghiệm luôn chạy bằng model thật qua CLI, không lấy từ test.
settings.embedding_backend = "hashing"

# Tests API dùng SQLite in-memory cho tốc độ và độc lập với Docker;
# E2E trên Postgres thật được chạy riêng (xem docs/checkpoints/week_01_report.md).
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def _offline_models():
    """Test luôn chạy offline: embedder băm + generator mẫu.

    Bảo đảm CI không cần GPU/model và không tải gì từ mạng; số liệu thí nghiệm
    thật được chạy riêng bằng CLI với bge-m3 + Qwen (xem docs/checkpoints).
    """
    from app.core.config import settings

    settings.embedding_backend = "hashing"
    settings.llm_provider = "template"
    yield


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded(db):
    """2 tenant, mỗi tenant 1 admin; tenant chính thêm marketer + reviewer."""
    t1 = Tenant(name="Tenant Một", slug="tenant-mot")
    t2 = Tenant(name="Tenant Hai", slug="tenant-hai")
    db.add_all([t1, t2])
    db.flush()
    pw = hash_password("matkhau123")
    users = {
        "admin1": User(tenant_id=t1.id, email="admin@mot.vn", role="admin", hashed_password=pw),
        "marketer1": User(tenant_id=t1.id, email="marketer@mot.vn", role="marketer", hashed_password=pw),
        "reviewer1": User(tenant_id=t1.id, email="reviewer@mot.vn", role="reviewer", hashed_password=pw),
        "admin2": User(tenant_id=t2.id, email="admin@hai.vn", role="admin", hashed_password=pw),
    }
    db.add_all(users.values())
    db.commit()
    return {"t1": t1, "t2": t2, **users}


def login(client, email: str, password: str = "matkhau123") -> dict:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
