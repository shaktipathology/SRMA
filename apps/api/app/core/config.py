from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://srma:srma_password@localhost:5432/srma_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "srma_minio"
    minio_secret_key: str = "srma_minio_secret"
    minio_bucket: str = "srma-papers"

    # Grobid
    grobid_url: str = "http://localhost:8070"

    # App
    secret_key: str = "dev-secret-key-change-in-production"
    debug: bool = True


settings = Settings()
