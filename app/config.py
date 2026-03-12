from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")

    balldontlie_api_key: str = os.getenv("BALLDONTLIE_API_KEY", "")

    odds_api_key: str = os.getenv("ODDS_API_KEY", "")
    odds_region: str = os.getenv("ODDS_REGION", "us")
    odds_bookmaker: str = os.getenv("ODDS_BOOKMAKER", "draftkings")
    oddsless_mode: bool = os.getenv("ODDSLESS_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}

    report_output_dir: str = os.getenv("REPORT_OUTPUT_DIR", "outputs/reports")
    min_confidence_score: int = int(os.getenv("MIN_CONFIDENCE_SCORE", "75"))
    max_players_per_game: int = int(os.getenv("MAX_PLAYERS_PER_GAME", "6"))
    max_props_to_process: int = int(os.getenv("MAX_PROPS_TO_PROCESS", "0"))
    progress_every_n_props: int = int(os.getenv("PROGRESS_EVERY_N_PROPS", "25"))
    openai_timeout_seconds: int = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "90"))

    telegram_enabled: bool = os.getenv("TELEGRAM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

settings = Settings()
