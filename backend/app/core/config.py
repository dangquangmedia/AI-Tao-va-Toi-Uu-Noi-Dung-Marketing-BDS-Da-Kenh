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


settings = Settings()
