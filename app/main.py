import json
from pathlib import Path
from statistics import mean
from app.utils.dates import utc_today_str, safe_iso_date
from app.config import settings
from app.services.balldontlie_service import BallDontLieService
from app.services.odds_service import OddsService
from app.services.injury_service import InjuryService
from app.services.storage_service import StorageService
from app.services.telegram_service import TelegramService
from app.models import ResearchRecord, MissedGameInfo
from app.scoring import score_record
from app.report_writer import summarize_records_html

STAT_MAP = {
    "player_points": "points",
    "player_rebounds": "rebounds",
    "player_assists": "assists",
    "player_threes": "threes",
}

def extract_stat_value(stat_row: dict, prop_type: str) -> float:
    field = STAT_MAP.get(prop_type)
    if not field:
        return 0.0
    if field == "threes":
        return float(stat_row.get("fg3m", 0) or 0)
    # BallDontLie stats payload uses pts/reb/ast keys.
    if field == "points":
        return float(stat_row.get("pts", stat_row.get(field, 0)) or 0)
    if field == "rebounds":
        return float(stat_row.get("reb", stat_row.get(field, 0)) or 0)
    if field == "assists":
        return float(stat_row.get("ast", stat_row.get(field, 0)) or 0)
    return float(stat_row.get(field, 0) or 0)

def extract_minutes(stat_row: dict) -> float:
    val = stat_row.get("min") or stat_row.get("minutes") or 0
    if isinstance(val, str) and ":" in val:
        mm = val.split(":")[0]
        return float(mm)
    try:
        return float(val)
    except Exception:
        return 0.0


def build_oddsless_prop_rows(bdl: BallDontLieService, today: str, max_players_per_game: int) -> list[dict]:
    games = bdl.get_games_by_date(today)
    rows: list[dict] = []
    seen_players: set[int] = set()

    for game in games:
        home_team = game.get("home_team", {}) or {}
        away_team = game.get("visitor_team", {}) or {}
        game_label = f'{away_team.get("full_name") or away_team.get("name", "Away")} @ {home_team.get("full_name") or home_team.get("name", "Home")}'

        for team in [home_team, away_team]:
            team_id = team.get("id")
            if not team_id:
                continue
            try:
                players_data = bdl._get("/players", {"team_ids[]": team_id, "per_page": max(10, max_players_per_game)})
            except Exception:
                continue
            players = players_data.get("data", [])
            team_count = 0
            for p in players:
                pid = p.get("id")
                if not pid or pid in seen_players:
                    continue
                seen_players.add(pid)
                team_count += 1
                if team_count > max_players_per_game:
                    break
                player_name = f'{p.get("first_name", "").strip()} {p.get("last_name", "").strip()}'.strip()
                if not player_name:
                    continue
                for prop_type in STAT_MAP.keys():
                    rows.append({
                        "game_id": game.get("id"),
                        "game_label": game_label,
                        "player_name": player_name,
                        "player_id": pid,
                        "team_id": team_id,
                        "prop_type": prop_type,
                        "line": 0.0,  # model line is derived from recent sample later
                        "bookmaker": "model",
                        "over_price": None,
                        "under_price": None,
                    })
    return rows


def build_preview_text(rows: list[dict]) -> str:
    total = len(rows)
    rejected = sum(1 for r in rows if r.get("reject"))
    strong = sum(1 for r in rows if (not r.get("reject")) and float(r.get("confidence_score", 0) or 0) >= 70)
    playable = sum(
        1 for r in rows
        if (not r.get("reject")) and 50 <= float(r.get("confidence_score", 0) or 0) < 70
    )
    avoid = total - strong - playable
    return (
        f"Total reviewed: {total}\n"
        f"Strong: {strong}\n"
        f"Playable: {playable}\n"
        f"Avoid/Rejected: {avoid} (Rejected: {rejected})"
    )


def build_error_html(title: str, message: str) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; color: #1f2937; }}
    .error {{ color: #c62828; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p class="error">{message}</p>
  <p>Action: check Odds API usage credits / plan access, then rerun.</p>
</body>
</html>
"""


def load_latest_research_records(output_dir: str) -> list[dict]:
    base = Path(output_dir)
    if not base.exists():
        return []
    files = sorted(base.glob("*_research_records.json"), reverse=True)
    for fp in files:
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(payload, list) and payload:
                return payload
        except Exception:
            continue
    return []

def main() -> None:
    today = utc_today_str()
    print(f"Run started for date: {today}")

    bdl = BallDontLieService()
    odds = OddsService()
    injuries = InjuryService()
    storage = StorageService()
    telegram = TelegramService()

    print("Fetching NBA events from Odds API...")
    all_prop_rows = []
    skipped_events = 0
    odds_error: str | None = None

    if settings.oddsless_mode:
        print("ODDSLESS_MODE is enabled: building model props from BallDontLie only")
        try:
            all_prop_rows = build_oddsless_prop_rows(bdl, today, settings.max_players_per_game)
        except Exception as exc:
            error_message = f"BallDontLie data source error: {type(exc).__name__}: {exc}"
            print(error_message)
            report_html_path = storage.save_html(
                "daily_report_error",
                build_error_html("NBA Props Report - Data Source Error", error_message),
            )
            print(f"Saved html report to: {report_html_path}")
            if telegram.should_send():
                try:
                    telegram.send_report(report_html_path, preview_text=error_message)
                    print("Telegram delivery: sent")
                except Exception as send_exc:
                    print(f"Telegram delivery: failed ({type(send_exc).__name__}: {send_exc})")
            return
        print(f"Model props generated: {len(all_prop_rows)}")
    else:
        events = odds.get_nba_events()
        print(f"Events fetched: {len(events)}")
        try:
            snapshot = odds.get_nba_props_snapshot()
        except RuntimeError as exc:
            raise SystemExit(str(exc))

        if snapshot:
            for event_data in snapshot:
                all_prop_rows.extend(odds.normalize_props(event_data))
        else:
            for event in events:
                event_id = event.get("id")
                if not event_id:
                    continue
                try:
                    event_props = odds.get_event_props_safe(event_id)
                except RuntimeError as exc:
                    odds_error = str(exc)
                    break
                if not event_props:
                    skipped_events += 1
                    continue
                all_prop_rows.extend(odds.normalize_props(event_props))

    # Limit V1 to core stat markets only
    all_prop_rows = [r for r in all_prop_rows if r["prop_type"] in STAT_MAP]
    max_props = settings.max_props_to_process
    if max_props > 0:
        all_prop_rows = all_prop_rows[:max_props]
    print(f"Props queued: {len(all_prop_rows)}")
    if skipped_events:
        print(f"Events skipped (restricted/empty props): {skipped_events}")
    if not all_prop_rows:
        cached_rows = load_latest_research_records(settings.report_output_dir)
        if cached_rows:
            print("No live odds props available; using latest cached research_records dataset")
            cached_html = summarize_records_html(cached_rows)
            report_html_path = storage.save_html("daily_report_cached", cached_html)
            preview = (
                "Using cached data (latest saved research_records).\n"
                f"Rows: {len(cached_rows)}\n"
                f"Reason: {odds_error or 'No props returned from odds source'}"
            )
            print(f"Saved html report to: {report_html_path}")
            if telegram.should_send():
                try:
                    telegram.send_report(report_html_path, preview_text=preview)
                    print("Telegram delivery: sent")
                except Exception as exc:
                    print(f"Telegram delivery: failed ({type(exc).__name__}: {exc})")
            return

        print(f"Odds API error: {odds_error or 'No props returned'}")
        report_html_path = storage.save_html(
            "daily_report_error",
            build_error_html("NBA Props Report - Data Source Error", odds_error or "No props returned from odds source"),
        )
        print(f"Saved html report to: {report_html_path}")
        if telegram.should_send():
            try:
                telegram.send_report(report_html_path, preview_text=f"Run failed: {odds_error or 'No props returned'}")
                print("Telegram delivery: sent")
            except Exception as exc:
                print(f"Telegram delivery: failed ({type(exc).__name__}: {exc})")
        return

    research_records = []
    player_cache: dict[str, dict | None] = {}
    stats_cache: dict[int, list[dict]] = {}
    team_games_cache: dict[int, list[dict]] = {}
    injuries_cache: dict[str, list[dict]] = {}
    todays_status_cache: dict[str, dict] = {}
    skipped_props = 0

    for idx, prop in enumerate(all_prop_rows, start=1):
        if idx % max(1, settings.progress_every_n_props) == 0:
            print(f"Progress: {idx}/{len(all_prop_rows)} props processed, {len(research_records)} records built")

        player_name = prop["player_name"]
        try:
            preset_player_id = prop.get("player_id")
            preset_team_id = prop.get("team_id")

            if preset_player_id:
                player_id = int(preset_player_id)
                team_id = int(preset_team_id) if preset_team_id is not None else None
            else:
                if player_name not in player_cache:
                    player_cache[player_name] = bdl.search_player(player_name)
                player = player_cache[player_name]
                if not player:
                    skipped_props += 1
                    continue
                player_id = player["id"]
                team = player.get("team", {})
                team_id = team.get("id")

            if player_id not in stats_cache:
                stats_cache[player_id] = bdl.get_player_game_stats(player_id, per_page=20)
            stats = stats_cache[player_id]
            played_rows = []
            for row in stats:
                value = extract_stat_value(row, prop["prop_type"])
                minutes = extract_minutes(row)
                played_rows.append({
                    "date": safe_iso_date(row.get("game", {}).get("date", "")),
                    "value": value,
                    "minutes": minutes,
                    "game_id": str(row.get("game", {}).get("id", "")),
                })

            played_rows = sorted(played_rows, key=lambda x: x["date"], reverse=True)[:6]
            if len(played_rows) < 4:
                skipped_props += 1
                continue

            model_line = float(prop.get("line", 0) or 0)
            if str(prop.get("bookmaker", "")).lower() == "model":
                avg_val = sum(r["value"] for r in played_rows) / len(played_rows)
                model_line = round(avg_val * 2) / 2
                if model_line <= 0:
                    model_line = 0.5

            if team_id and team_id not in team_games_cache:
                team_games_cache[team_id] = bdl.get_team_games(team_id, end_date=today, per_page=8)
            team_games = team_games_cache.get(team_id, []) if team_id else []
            # Ignore legacy seasons from provider (e.g., 1940s) to avoid false missed-game rejects.
            modern_team_games = [
                g for g in team_games
                if str(g.get("date", ""))[:4].isdigit() and int(str(g.get("date", ""))[:4]) >= 2010
            ]
            recent_team_game_ids = {
                str(g["id"]): g for g in sorted(modern_team_games, key=lambda x: x.get("date", ""), reverse=True)[:6]
            }
            played_ids = {r["game_id"] for r in played_rows}
            missed_ids = [gid for gid in recent_team_game_ids.keys() if gid not in played_ids]

            missed_recent = []
            if player_name not in injuries_cache:
                injuries_cache[player_name] = bdl.get_player_injuries(player_name)
            bdl_injuries = injuries_cache[player_name]
            inferred_reason = injuries.infer_recent_missed_game_reason(bdl_injuries)

            for gid in missed_ids:
                missed_recent.append(MissedGameInfo(
                    game_id=gid,
                    date=safe_iso_date(recent_team_game_ids[gid].get("date", "")),
                    reason=inferred_reason
                ))

            if player_name not in todays_status_cache:
                todays_status_cache[player_name] = injuries.get_todays_status(player_name)
            today_status = todays_status_cache[player_name]

            record = ResearchRecord(
                game_label=prop["game_label"],
                player_name=prop["player_name"],
                prop_type=prop["prop_type"],
                line=model_line,
                bookmaker=prop["bookmaker"],
                over_price=prop["over_price"],
                under_price=prop["under_price"],
                last_6_played_values=[r["value"] for r in played_rows],
                last_6_minutes=[r["minutes"] for r in played_rows],
                missed_recent_team_games=missed_recent,
                todays_injury_status=today_status["status"],
                todays_injury_note=today_status["note"],
            )

            score_record(record)
            research_records.append(record)
        except Exception as exc:
            skipped_props += 1
            print(f"Prop skipped ({player_name}): {type(exc).__name__}")

    structured = [r.model_dump() for r in research_records]
    storage.save_json("research_records", structured)
    print(f"Research records saved: {len(structured)} (skipped props: {skipped_props})")

    ranked = sorted(
        research_records,
        key=lambda x: (x.reject, -x.confidence_score)
    )

    report_rows = [r.model_dump() for r in ranked]
    print(f"Rows sent to report writer: {len(report_rows)}")

    report_html = summarize_records_html(report_rows)
    report_html_path = storage.save_html("daily_report", report_html)
    preview_text = build_preview_text(report_rows)

    print(f"Saved html report to: {report_html_path}")
    if telegram.should_send():
        try:
            telegram.send_report(report_html_path, preview_text=preview_text)
            print("Telegram delivery: sent")
        except Exception as exc:
            print(f"Telegram delivery: failed ({type(exc).__name__}: {exc})")
    elif telegram.enabled:
        print("Telegram delivery: skipped (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)")

if __name__ == "__main__":
    main()
