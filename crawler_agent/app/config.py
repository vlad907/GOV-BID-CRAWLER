from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Must be absolute: Chrome resolves a relative --user-data-dir against
# whatever process's cwd actually launches it, and the worker subprocess
# (see worker_process.py) can end up with a different effective cwd than
# expected. A relative path silently falling through to Chrome's default
# profile location (and colliding with a real, already-open Chrome) is
# exactly what caused an opaque "Chrome instance exited" failure here.
_DEFAULT_CHROME_PROFILE_DIR = str(Path(__file__).resolve().parent.parent / "chrome_profile")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8100
    # Persistent Chrome profile dir so cookies/session survive between jobs
    # (fewer repeated logins/consent clicks, looks more like a normal user).
    chrome_profile_dir: str = _DEFAULT_CHROME_PROFILE_DIR
    page_load_timeout_seconds: int = 30
    dibbs_base_url: str = "https://www.dibbs.bsm.dla.mil"
    sam_gov_base_url: str = "https://sam.gov"
    nsn_marketplace_base_url: str = "https://www.parttarget.com"


settings = Settings()
