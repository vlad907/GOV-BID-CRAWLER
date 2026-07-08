from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8100
    # Persistent Chrome profile dir so cookies/session survive between jobs
    # (fewer repeated logins/consent clicks, looks more like a normal user).
    chrome_profile_dir: str = "./chrome_profile"
    page_load_timeout_seconds: int = 30
    dibbs_base_url: str = "https://www.dibbs.bsm.dla.mil"
    sam_gov_base_url: str = "https://sam.gov"
    nsn_marketplace_base_url: str = "https://www.parttarget.com"


settings = Settings()
