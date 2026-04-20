from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "AI Answer Sheet Evaluation API"
    database_url: str = "sqlite:///./app.db"
    cors_allow_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    uploads_dir: str = "uploads"
    ocr_provider: str = "local"
    ocr_confidence_threshold: float = 0.75
    google_vision_api_key: str | None = None
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    llm_timeout_seconds: int = 30

    @property
    def normalized_database_url(self) -> str:
        # Some cloud providers still expose `postgres://`, while SQLAlchemy expects `postgresql://`.
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql://", 1)
        return self.database_url

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


settings = Settings()
