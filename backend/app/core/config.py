from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "AI Answer Sheet Evaluation API"
    database_url: str = "sqlite:///./app.db"
    uploads_dir: str = "uploads"
    ocr_provider: str = "local"
    ocr_confidence_threshold: float = 0.75
    google_vision_api_key: str | None = None
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    llm_timeout_seconds: int = 30


settings = Settings()
