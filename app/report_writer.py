from datetime import datetime
from app.config import settings


def _prop_label(prop_type: str) -> str:
    mapping = {
        "player_points": "Points",
        "player_rebounds": "Rebounds",
        "player_assists": "Assists",
        "player_threes": "3PM",
    }
    return mapping.get(prop_type, prop_type)


def _lean(row: dict) -> str:
    avg = float(row.get("recent_average", 0) or 0)
    line = float(row.get("line", 0) or 0)
    if avg >= line + 0.5:
        return "Over"
    if avg <= line - 0.5:
        return "Under"
    return "No edge"


def _risk_text(row: dict) -> str:
    if row.get("reject"):
        return '<span style="color:#c62828"><strong>REJECTED</strong></span>'
    notes = row.get("risk_notes", []) or []
    if notes:
        return "; ".join(str(n) for n in notes[:2])
    return "Low flagged risk"


def _limit_per_game(rows: list[dict], max_per_game: int) -> list[dict]:
    if max_per_game <= 0:
        return rows
    counts: dict[str, int] = {}
    kept: list[dict] = []
    for row in rows:
        game = str(row.get("game_label", "unknown"))
        current = counts.get(game, 0)
        if current >= max_per_game:
            continue
        kept.append(row)
        counts[game] = current + 1
    return kept


def _format_rows_table(rows: list[dict]) -> str:
    if not rows:
        return "_None_"

    header = (
        "| # | Player | Prop | Line | Lean | Avg(6) | Hit(6) | Min Avg | Score | Risk |\n"
        "|---:|---|---|---:|---|---:|---:|---:|---:|---|\n"
    )
    body_lines = []
    for idx, row in enumerate(rows, start=1):
        body_lines.append(
            f"| {idx} | {row.get('player_name','-')} | {_prop_label(str(row.get('prop_type','-')))} | "
            f"{float(row.get('line', 0) or 0):.1f} | {_lean(row)} | "
            f"{float(row.get('recent_average', 0) or 0):.2f} | {int(row.get('hit_rate_last_6', 0) or 0)}/6 | "
            f"{float(row.get('minutes_average', 0) or 0):.1f} | {float(row.get('confidence_score', 0) or 0):.1f} | "
            f"{_risk_text(row)} |"
        )
    return header + "\n".join(body_lines)


def _format_rows_table_html(rows: list[dict]) -> str:
    if not rows:
        return "<p><em>None</em></p>"

    lines = [
        "<table>",
        "<thead><tr>"
        "<th>#</th><th>Player</th><th>Prop</th><th>Line</th><th>Lean</th><th>Avg(6)</th>"
        "<th>Hit(6)</th><th>Min Avg</th><th>Score</th><th>Risk</th>"
        "</tr></thead>",
        "<tbody>",
    ]
    for idx, row in enumerate(rows, start=1):
        risk = _risk_text(row)
        risk_class = "risk-high" if row.get("reject") else "risk-normal"
        lines.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td>{row.get('player_name','-')}</td>"
            f"<td>{_prop_label(str(row.get('prop_type','-')))}</td>"
            f"<td>{float(row.get('line', 0) or 0):.1f}</td>"
            f"<td>{_lean(row)}</td>"
            f"<td>{float(row.get('recent_average', 0) or 0):.2f}</td>"
            f"<td>{int(row.get('hit_rate_last_6', 0) or 0)}/6</td>"
            f"<td>{float(row.get('minutes_average', 0) or 0):.1f}</td>"
            f"<td>{float(row.get('confidence_score', 0) or 0):.1f}</td>"
            f"<td class=\"{risk_class}\">{risk}</td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "".join(lines)


def summarize_records(records: list[dict]) -> str:
    if not records:
        return (
            "# NBA Props Report\n\n"
            '<span style="color:#c62828"><strong>No records were available for this run.</strong></span>\n'
        )

    sorted_rows = sorted(records, key=lambda r: float(r.get("confidence_score", 0) or 0), reverse=True)
    strong = [r for r in sorted_rows if not r.get("reject") and float(r.get("confidence_score", 0) or 0) >= 70]
    playable = [r for r in sorted_rows if not r.get("reject") and 50 <= float(r.get("confidence_score", 0) or 0) < 70]
    avoid = [r for r in sorted_rows if r.get("reject") or float(r.get("confidence_score", 0) or 0) < 50]

    strong = _limit_per_game(strong, settings.max_players_per_game)
    playable = _limit_per_game(playable, settings.max_players_per_game)
    avoid = _limit_per_game(avoid, settings.max_players_per_game)

    total = len(sorted_rows)
    rejected = sum(1 for r in sorted_rows if r.get("reject"))
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return f"""# NBA Props Report

Generated: `{now}`

## Summary
- Total reviewed: **{total}**
- Strong: **{len(strong)}**
- Playable: **{len(playable)}**
- Avoid/Rejected: **{len(avoid)}** (Rejected: **{rejected}**)
- <span style="color:#c62828"><strong>Red labels indicate elevated risk or rejected rows.</strong></span>

## Strong Candidates
{_format_rows_table(strong[:10])}

## Playable Candidates
{_format_rows_table(playable[:15])}

## Avoid List
{_format_rows_table(avoid[:15])}
"""


def summarize_records_html(records: list[dict]) -> str:
    if not records:
        return (
            "<html><body><h1>NBA Props Report</h1>"
            "<p style='color:#c62828'><strong>No records were available for this run.</strong></p>"
            "</body></html>"
        )

    sorted_rows = sorted(records, key=lambda r: float(r.get("confidence_score", 0) or 0), reverse=True)
    strong = [r for r in sorted_rows if not r.get("reject") and float(r.get("confidence_score", 0) or 0) >= 70]
    playable = [r for r in sorted_rows if not r.get("reject") and 50 <= float(r.get("confidence_score", 0) or 0) < 70]
    avoid = [r for r in sorted_rows if r.get("reject") or float(r.get("confidence_score", 0) or 0) < 50]

    strong = _limit_per_game(strong, settings.max_players_per_game)
    playable = _limit_per_game(playable, settings.max_players_per_game)
    avoid = _limit_per_game(avoid, settings.max_players_per_game)
    total = len(sorted_rows)
    rejected = sum(1 for r in sorted_rows if r.get("reject"))
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>NBA Props Report</title>
  <style>
    body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; color: #1f2937; }}
    h1 {{ margin-bottom: 8px; }}
    h2 {{ margin-top: 24px; }}
    .meta {{ color: #6b7280; margin-bottom: 16px; }}
    .alert {{ color: #c62828; font-weight: 700; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; font-size: 13px; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
    .risk-high {{ color: #c62828; font-weight: 700; }}
    .risk-normal {{ color: #374151; }}
  </style>
</head>
<body>
  <h1>NBA Props Report</h1>
  <div class="meta">Generated: {now}</div>
  <h2>Summary</h2>
  <ul>
    <li>Total reviewed: <strong>{total}</strong></li>
    <li>Strong: <strong>{len(strong)}</strong></li>
    <li>Playable: <strong>{len(playable)}</strong></li>
    <li>Avoid/Rejected: <strong>{len(avoid)}</strong> (Rejected: <strong>{rejected}</strong>)</li>
    <li class="alert">Red rows/labels indicate elevated risk or rejected entries.</li>
  </ul>

  <h2>Strong Candidates</h2>
  {_format_rows_table_html(strong[:10])}

  <h2>Playable Candidates</h2>
  {_format_rows_table_html(playable[:15])}

  <h2>Avoid List</h2>
  {_format_rows_table_html(avoid[:15])}
</body>
</html>
"""
