import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential
from app.config import settings

BASE_URL = "https://api.balldontlie.io/v1"


def _is_retryable_api_error(exc: BaseException) -> bool:
    if not isinstance(exc, requests.exceptions.HTTPError):
        return True
    response = exc.response
    return response is None or response.status_code in {500, 502, 503, 504}

class BallDontLieService:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": settings.balldontlie_api_key
        })

    @retry(
        retry=retry_if_exception(_is_retryable_api_error),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        reraise=True,
    )
    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = self.session.get(f"{BASE_URL}{path}", params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_games_by_date(self, date_str: str) -> list[dict]:
        data = self._get("/games", {"dates[]": date_str, "per_page": 100})
        return data.get("data", [])

    def get_players(
        self,
        search: str | None = None,
        per_page: int = 25,
        cursor: int | None = None,
    ) -> dict:
        params: dict[str, int | str] = {"per_page": per_page}
        if search:
            params["search"] = search
        if cursor is not None:
            params["cursor"] = cursor
        return self._get("/players", params)

    def get_stats(
        self,
        player_id: int | None = None,
        game_id: int | None = None,
        per_page: int = 25,
        cursor: int | None = None,
    ) -> dict:
        params: dict[str, int] = {"per_page": per_page}
        if player_id is not None:
            params["player_ids[]"] = player_id
        if game_id is not None:
            params["game_ids[]"] = game_id
        if cursor is not None:
            params["cursor"] = cursor
        return self._get("/stats", params)

    def get_all_games(
        self,
        per_page: int = 100,
        cursor: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        params: dict[str, int | str] = {"per_page": per_page}
        if cursor is not None:
            params["cursor"] = cursor
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get("/games", params)

    def search_player(self, player_name: str) -> dict | None:
        normalized_name = player_name.strip().lower()
        queries = [player_name]
        if " " in player_name.strip():
            queries.extend(part for part in player_name.split(" ") if part)

        try:
            for query in queries:
                data = self.get_players(search=query, per_page=25)
                players = data.get("data", [])
                if not players:
                    continue

                for candidate in players:
                    full_name = f'{candidate.get("first_name", "")} {candidate.get("last_name", "")}'.strip().lower()
                    if full_name == normalized_name:
                        return candidate

                if len(queries) == 1:
                    return players[0]

            return None
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                return None
            raise

    def get_player_game_stats(self, player_id: int, per_page: int = 25) -> list[dict]:
        try:
            data = self.get_stats(player_id=player_id, per_page=per_page)
            return data.get("data", [])
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                return []
            raise

    def get_team_games(self, team_id: int, end_date: str, per_page: int = 10) -> list[dict]:
        try:
            data = self._get("/games", {
                "team_ids[]": team_id,
                "end_date": end_date,
                "per_page": per_page
            })
            return data.get("data", [])
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                return []
            raise

    def get_injuries(
        self,
        player_name: str | None = None,
        per_page: int = 25,
        cursor: int | None = None,
    ) -> dict:
        params: dict[str, int | str] = {"per_page": per_page}
        if player_name:
            params["player_name"] = player_name
        if cursor is not None:
            params["cursor"] = cursor
        return self._get("/injuries", params)

    def get_player_injuries(self, player_name: str) -> list[dict]:
        # Tier-gated in BALLDONTLIE
        try:
            data = self.get_injuries(player_name=player_name, per_page=10)
            return data.get("data", [])
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                return []
            return []
        except Exception:
            return []
