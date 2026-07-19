from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INVOS_", env_file=".env", extra="ignore")

    environment: str = "dev"
    log_json: bool = False
    repo_root: Path = _REPO_ROOT

    # "fixture" runs fully offline from the demo dataset; "live" pulls EOD
    # prices (Yahoo interim) and RSS news for the configured universe.
    data_mode: str = "fixture"
    fixtures_path: Path = _REPO_ROOT / "data" / "fixtures" / "idx_demo.json"
    universe_path: Path = _REPO_ROOT / "data" / "universe" / "lq45-demo.json"
    market_history_days: int = 120
    database_path: Path = _REPO_ROOT / "var" / "investment_os.db"

    telegram_bot_token: str | None = None
    telegram_poll_timeout_s: int = 30

    # "user:password" enables HTTP Basic auth on the REST API + dashboard
    # (all routes except /health). None leaves the API open — bind it to
    # localhost or a private network in that case.
    api_auth: str | None = None

    # Daily Market Brief broadcast (WIB wall clock, trading days only)
    brief_time_wib: str = "07:30"
    # Watchlist alert sweep, post-market WIB
    alert_time_wib: str = "17:15"
    # Realized-return sweep for calibration, post-market WIB
    outcome_time_wib: str = "17:45"
    outcome_horizon_days: int = 20
    # Live-mode KB rebuild cadence for the long-running bot
    refresh_interval_minutes: int = 60

    analysis_min_evidence: int = 3
    analysis_stale_after_days: float = 7.0
    low_confidence_threshold: float = 0.6

    # LLM narrative layer. Provider keys are read from their native env vars
    # (ANTHROPIC_API_KEY, OPENAI_API_KEY, ...); by default the first
    # configured provider wins. None disables the layer entirely.
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_max_tokens: int = 700
    # Opt-in: let the LLM take over the news seat in the committee (with the
    # deterministic lexicon analyst as automatic fallback). Off by default so
    # decisions stay reproducible unless explicitly enabled.
    llm_analysts: bool = False
    prompts_path: Path = _REPO_ROOT / "prompts"
    golden_path: Path = _REPO_ROOT / "eval" / "golden" / "decisions.json"


def load_settings() -> Settings:
    return Settings()
