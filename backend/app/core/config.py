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

    # Generator cho cấu hình A/B (Tuần 4). Xem services/llm.py.
    llm_provider: str = "local"  # local | openai | template
    llm_model: str = "Qwen/Qwen2.5-3B-Instruct"
    llm_device: str = "auto"
    llm_load_in_4bit: bool = True  # vừa GPU 4GB
    llm_max_new_tokens: int = 600
    llm_seed: int = 42
    openai_api_key: str = ""
    openai_base_url: str = ""
    prompt_version: str = "prompt_v1"

    # QLoRA adapter cho cấu hình C/D (Tuần 5). Adapter do Hải train ở máy/Colab GPU rồi
    # copy nguyên thư mục vào `adapter_dir`; backend tự nhận, không phải sửa code.
    # Hợp đồng bàn giao: xem training/README.md.
    adapter_dir: str = "models/adapters"
    llm_adapter: str = ""  # tên thư mục adapter mặc định cho C/D; rỗng = chưa có


settings = Settings()
