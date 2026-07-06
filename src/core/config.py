from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "UTBookLM"
    app_version: str = "1.0.0"
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str | None = Field(None, alias="LOG_LEVEL")
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = Field("http://localhost:3000", alias="CORS_ORIGINS")

    database_url_override: str | None = Field(None, alias="DATABASE_URL")
    db_host: str = Field("localhost", alias="DB_HOST")
    db_port: int = Field(5432, alias="DB_PORT")
    db_user: str = Field("postgres", alias="DB_USER")
    db_password: str = Field("postgres", alias="DB_PASSWORD")
    db_name: str = Field("utbooklm", alias="DB_NAME")

    jwt_secret_key: str = Field("change-this-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        30,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expire_days: int = Field(7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    password_reset_token_expire_minutes: int = Field(
        30,
        alias="PASSWORD_RESET_TOKEN_EXPIRE_MINUTES",
    )
    auth_enabled: bool = Field(False, alias="AUTH_ENABLED")

    document_storage_backend: str = Field("local", alias="DOCUMENT_STORAGE_BACKEND")
    document_storage_dir: str = Field("storage/documents", alias="DOCUMENT_STORAGE_DIR")
    document_max_upload_mb: int = Field(50, alias="DOCUMENT_MAX_UPLOAD_MB")
    document_allowed_extensions: str = Field(
        "pdf,pptx",
        alias="DOCUMENT_ALLOWED_EXTENSIONS",
    )
    document_allowed_mime_types: str = Field(
        "application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation",
        alias="DOCUMENT_ALLOWED_MIME_TYPES",
    )

    minio_endpoint: str = Field("http://localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field("minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field("minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field("documents", alias="MINIO_BUCKET")

    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str | None = Field(None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(None, alias="CELERY_RESULT_BACKEND")

    chroma_persist_dir: str = Field("storage/chroma", alias="CHROMA_PERSIST_DIR")
    embedding_provider: str = Field("fake", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field("text-embedding-3-small", alias="EMBEDDING_MODEL")
    llm_provider: str = Field("fake", alias="LLM_PROVIDER")
    llm_model: str = Field("gpt-4o", alias="LLM_MODEL")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")

    smtp_host: str | None = Field(None, alias="SMTP_HOST")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_user: str | None = Field(None, alias="SMTP_USER")
    smtp_password: str | None = Field(None, alias="SMTP_PASSWORD")
    email_from: str = Field("noreply@example.com", alias="EMAIL_FROM")

    websocket_token_expire_minutes: int = Field(
        5,
        alias="WEBSOCKET_TOKEN_EXPIRE_MINUTES",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @computed_field
    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override

        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @computed_field
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field
    @property
    def allowed_document_extensions(self) -> set[str]:
        return {
            item.strip().lower().lstrip(".")
            for item in self.document_allowed_extensions.split(",")
            if item.strip()
        }

    @computed_field
    @property
    def allowed_document_mime_types(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.document_allowed_mime_types.split(",")
            if item.strip()
        }

    @computed_field
    @property
    def document_max_upload_bytes(self) -> int:
        return self.document_max_upload_mb * 1024 * 1024

    @computed_field
    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @computed_field
    @property
    def result_backend_url(self) -> str:
        return self.celery_result_backend or self.redis_url

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @computed_field
    @property
    def effective_log_level(self) -> str:
        if self.log_level:
            return self.log_level.upper()
        if self.is_production:
            return "WARNING"
        return "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
