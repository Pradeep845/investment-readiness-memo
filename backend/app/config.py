from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Investment Readiness Memo API"
    app_env: str = "dev"
    log_level: str = "info"

    anakin_api_key: str = ""
    anakin_base_url: str = "https://api.anakin.io/v1"
    anakin_poll_seconds: int = 3
    anakin_poll_timeout_seconds: int = 90

    stock_history_days: int = 30

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
