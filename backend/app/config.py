from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    crawler_agent_url: str = "http://localhost:8100"
    database_url: str = "sqlite:///./govbid.db"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # SBA Non-Manufacturer Rule thresholds (see FAR 19.505 / SBA guidance)
    nmr_general_set_aside_threshold: float = 250_000.0
    nmr_socioeconomic_set_aside_threshold: float = 10_000.0

    default_markup_pct: float = 0.20


settings = Settings()
