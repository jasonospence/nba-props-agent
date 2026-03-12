from __future__ import annotations

from app.config import settings
from app.services.balldontlie_service import BallDontLieService
from app.services.odds_service import OddsService
from app.utils.dates import utc_today_str


def _is_placeholder(value: str) -> bool:
    return value.strip() in {"", "your_openai_key", "your_odds_api_key"}


def run_health_check() -> int:
    ok = True

    print("Health check: NBA Props Agent")
    print("-" * 40)

    if _is_placeholder(settings.openai_api_key):
        ok = False
        print("OPENAI_API_KEY: FAIL (missing or placeholder)")
    else:
        print("OPENAI_API_KEY: OK")

    if _is_placeholder(settings.odds_api_key):
        ok = False
        print("ODDS_API_KEY: FAIL (missing or placeholder)")
    else:
        print("ODDS_API_KEY: OK")

    if not settings.balldontlie_api_key.strip():
        ok = False
        print("BALLDONTLIE_API_KEY: FAIL (missing)")
    else:
        print("BALLDONTLIE_API_KEY: OK")

    print("-" * 40)

    odds = OddsService()
    bdl = BallDontLieService()

    try:
        events = odds.get_nba_events()
        print(f"Odds API /events: OK ({len(events)} events)")
    except Exception as exc:
        ok = False
        print(f"Odds API /events: FAIL ({type(exc).__name__}: {exc})")

    try:
        games = bdl.get_games_by_date(utc_today_str())
        print(f"BallDontLie /games by date: OK ({len(games)} games)")
    except Exception as exc:
        ok = False
        print(f"BallDontLie /games by date: FAIL ({type(exc).__name__}: {exc})")

    try:
        player = bdl.search_player("LeBron James")
        if player:
            print(f"BallDontLie /players search: OK ({player.get('first_name')} {player.get('last_name')})")
        else:
            ok = False
            print("BallDontLie /players search: FAIL (no player returned)")
    except Exception as exc:
        ok = False
        print(f"BallDontLie /players search: FAIL ({type(exc).__name__}: {exc})")

    print("-" * 40)
    if ok:
        print("Result: PASS")
        return 0
    print("Result: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(run_health_check())
