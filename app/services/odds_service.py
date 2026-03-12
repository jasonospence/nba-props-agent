import requests
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed
from app.config import settings

BASE_URL = "https://api.the-odds-api.com/v4"

class OddsService:
    def __init__(self) -> None:
        self.session = requests.Session()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get(self, path: str, params: dict | None = None) -> dict | list:
        final_params = params or {}
        final_params["apiKey"] = settings.odds_api_key
        resp = self.session.get(f"{BASE_URL}{path}", params=final_params, timeout=30)
        if resp.status_code >= 400:
            error_code = None
            message = None
            try:
                payload = resp.json()
                error_code = payload.get("error_code")
                message = payload.get("message")
            except Exception:
                pass
            if error_code == "OUT_OF_USAGE_CREDITS":
                raise RuntimeError("Odds API out of usage credits. Recharge or wait for quota reset.")
            detail = f" ({error_code}: {message})" if error_code or message else ""
            raise requests.exceptions.HTTPError(
                f"{resp.status_code} error from Odds API{detail}",
                response=resp,
            )
        return resp.json()

    def get_nba_events(self) -> list[dict]:
        return self._get("/sports/basketball_nba/events")

    def get_event_props(self, event_id: str, markets: str = "player_points,player_rebounds,player_assists,player_threes") -> dict:
        return self._get(
            f"/sports/basketball_nba/events/{event_id}/odds",
            {
                "regions": settings.odds_region,
                "markets": markets,
                "oddsFormat": "american",
                "bookmakers": settings.odds_bookmaker
            }
        )

    def get_nba_props_snapshot(self, markets: str = "player_points,player_rebounds,player_assists,player_threes") -> list[dict]:
        try:
            data = self._get(
                "/sports/basketball_nba/odds",
                {
                    "regions": settings.odds_region,
                    "markets": markets,
                    "oddsFormat": "american",
                    "bookmakers": settings.odds_bookmaker,
                },
            )
            return data if isinstance(data, list) else []
        except RetryError as exc:
            last_exc = exc.last_attempt.exception() if exc.last_attempt else None
            if isinstance(last_exc, requests.exceptions.HTTPError):
                response = last_exc.response
                if response is not None and response.status_code in {401, 403, 422, 429}:
                    return []
            raise
        except requests.exceptions.HTTPError as exc:
            response = exc.response
            if response is not None and response.status_code in {401, 403, 422, 429}:
                return []
            raise

    def get_event_props_safe(self, event_id: str, markets: str = "player_points,player_rebounds,player_assists,player_threes") -> dict:
        try:
            return self.get_event_props(event_id, markets=markets)
        except RuntimeError:
            raise
        except RetryError as exc:
            last_exc = exc.last_attempt.exception() if exc.last_attempt else None
            if isinstance(last_exc, RuntimeError):
                raise last_exc
            if isinstance(last_exc, requests.exceptions.HTTPError):
                response = last_exc.response
                if response is not None and response.status_code in {401, 403, 422, 429}:
                    return {}
            raise
        except requests.exceptions.HTTPError as exc:
            response = exc.response
            if response is not None and response.status_code in {401, 403, 422, 429}:
                return {}
            raise

    def normalize_props(self, event_data: dict) -> list[dict]:
        records: list[dict] = []
        bookmakers = event_data.get("bookmakers", [])
        game_label = f'{event_data.get("away_team")} @ {event_data.get("home_team")}'

        for book in bookmakers:
            bookmaker = book.get("title", book.get("key"))
            for market in book.get("markets", []):
                market_key = market.get("key")
                grouped: dict[tuple[str, float], dict] = {}

                for outcome in market.get("outcomes", []):
                    player_name = outcome.get("description")
                    point = outcome.get("point")
                    side = outcome.get("name")  # Over / Under
                    price = outcome.get("price")

                    if not player_name or point is None:
                        continue

                    key = (player_name, float(point))
                    if key not in grouped:
                        grouped[key] = {
                            "game_id": event_data.get("id"),
                            "game_label": game_label,
                            "player_name": player_name,
                            "prop_type": market_key,
                            "line": float(point),
                            "bookmaker": bookmaker,
                            "over_price": None,
                            "under_price": None,
                        }

                    if str(side).lower() == "over":
                        grouped[key]["over_price"] = price
                    elif str(side).lower() == "under":
                        grouped[key]["under_price"] = price

                records.extend(grouped.values())

        return records
