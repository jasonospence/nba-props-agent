from app.services.balldontlie_service import BallDontLieService


class InjuryService:
    def __init__(self) -> None:
        self.bdl = BallDontLieService()

    @staticmethod
    def _normalize_status(raw_status: str) -> str:
        status = (raw_status or "").strip().lower()
        if any(token in status for token in ["available", "active", "healthy", "cleared"]):
            return "active"
        if "probable" in status:
            return "probable"
        if "questionable" in status:
            return "questionable"
        if "doubtful" in status:
            return "doubtful"
        if "out" in status:
            return "out"
        return "unknown"

    def get_todays_status(self, player_name: str) -> dict:
        try:
            injuries = self.bdl.get_player_injuries(player_name)
        except Exception:
            injuries = []

        if not injuries:
            return {"status": "unknown", "note": ""}

        latest = injuries[0]
        raw_status = str(latest.get("status") or latest.get("designation") or "")
        status = self._normalize_status(raw_status)
        note = (
            latest.get("description")
            or latest.get("comment")
            or latest.get("injury")
            or raw_status
            or ""
        )
        return {"status": status, "note": str(note)}

    def infer_recent_missed_game_reason(self, injuries: list[dict]) -> str:
        if not injuries:
            return "unknown"
        latest = injuries[0]
        reason_text = str(
            latest.get("description")
            or latest.get("comment")
            or latest.get("injury")
            or latest.get("status")
            or latest.get("designation")
            or ""
        ).strip()
        reason = reason_text.lower()

        if any(token in reason for token in ["ankle", "knee", "hamstring", "back", "shoulder", "wrist", "foot"]):
            return reason_text or "injury"
        if "rest" in reason:
            return "rest"
        if any(token in reason for token in ["illness", "sick", "flu"]):
            return "illness"
        if "personal" in reason:
            return "personal reasons"

        return reason_text or "unknown"
