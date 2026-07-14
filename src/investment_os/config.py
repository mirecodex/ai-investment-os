from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INVOS_", env_file=".env", extra="ignore")

    environment: str = "dev"
    log_json: bool = False

    fixtures_path: Path = _REPO_ROOT / "data" / "fixtures" / "idx_demo.json"
    database_path: Path = _REPO_ROOT / "var" / "investment_os.db"

    telegram_bot_token: str | None = None
    telegram_poll_timeout_s: int = 30

    analysis_min_evidence: int = 3
    analysis_stale_after_days: float = 7.0
    low_confidence_threshold: float = 0.6


def load_settings() -> Settings:
    return Settings()
