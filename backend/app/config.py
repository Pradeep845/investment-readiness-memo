from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Investment Readiness Memo API"
    app_env: str = "dev"
    log_level: str = "info"

    anakin_api_key: str = ""
    anakin_base_url: str = "https://api.anakin.io/v1"
    anakin_poll_seconds: int = 3
    anakin_poll_timeout_seconds: int = 120
    # Agentic Search is multi-stage and often exceeds general scrape timeouts (Anakin docs: several minutes).
    anakin_agentic_poll_seconds: int = 10
    anakin_agentic_poll_timeout_seconds: int = 600

    # Hard cap for the whole /analyze request. After this many seconds we cancel
    # whatever is still running (scrape / agentic / holocron) and return a partial memo
    # using results that finished in time. diagnostics.partial=true marks such responses.
    analyze_total_deadline_seconds: int = 120
    # Slice of the total budget reserved for the Map phase before the parallel phase begins.
    analyze_map_deadline_seconds: int = 35

    # Wire (Holocron) — GET /holocron/jobs/{id} is rate-limited (~60/min); keep interval >= 2s when polling few jobs.
    holocron_enabled: bool = True
    holocron_catalog_slugs: str = "wikipedia,google_news"
    holocron_poll_seconds: int = 2
    holocron_poll_timeout_seconds: int = 180
    holocron_between_catalog_seconds: float = 0.75

    # Gemini polish layer — optional. Rewrites memo summary / flags / catalysts into analyst tone.
    gemini_enabled: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    gemini_timeout_seconds: int = 20

    stock_history_days: int = 30

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
