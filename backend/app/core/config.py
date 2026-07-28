from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình ứng dụng — override bằng biến môi trường hoặc file .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Can Cu API"
    database_url: str = "postgresql+psycopg://cancu:cancu_dev@localhost:5432/cancu"
    secret_key: str = "dev-secret-change-in-staging"
    access_token_expire_minutes: int = 60 * 8
    jwt_algorithm: str = "HS256"

    # Đường dẫn kho dữ liệu crawl (raw zone — chỉ đọc)
    databds_dir: str = "../DataBDS"

    # Retrieval / embedding (Tuần 3). Ứng viên chốt theo Plan/03 §3.
    embedding_backend: str = "sentence-transformers"  # sentence-transformers | hashing (test/CI)
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_device: str = "auto"  # auto | cuda | cpu
    embedding_batch_size: int = 8
    embedding_max_length: int = 512

    # Thư mục artefact sinh ra (dataset, SFT draft, báo cáo eval) — ngoài git
    artifacts_dir: str = "artifacts"
    dataset_version: str = "dataset_v1"


settings = Settings()
