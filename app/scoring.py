from statistics import mean, median

def compute_hit_rate(values: list[float], line: float) -> int:
    return sum(1 for v in values if v > line)

def compute_minutes_stability(minutes: list[float]) -> tuple[float, float]:
    if not minutes:
        return 0.0, 999.0
    avg = mean(minutes)
    return avg, max(minutes) - min(minutes)

def score_record(record) -> None:
    values = record.last_6_played_values
    minutes = record.last_6_minutes

    if values:
        record.hit_rate_last_6 = compute_hit_rate(values, record.line)
        record.recent_average = round(mean(values), 2)
        record.recent_median = round(median(values), 2)

    if minutes:
        avg_min, min_range = compute_minutes_stability(minutes)
        record.minutes_average = round(avg_min, 2)
        record.minutes_range = round(min_range, 2)

    score = 0.0

    # recent hit rate: 30 pts
    score += (record.hit_rate_last_6 / 6.0) * 30 if values else 0

    # minutes stability: 20 pts
    if record.minutes_average >= 30 and record.minutes_range <= 6:
        score += 20
    elif record.minutes_average >= 28 and record.minutes_range <= 8:
        score += 15
    elif record.minutes_average >= 24:
        score += 10

    # injury confidence: 15 pts
    status = record.todays_injury_status.lower()
    if status in {"available", "active", "probable"}:
        score += 15
    elif status in {"questionable"}:
        score += 4
        record.risk_notes.append("Questionable status today")
    elif status in {"out", "doubtful"}:
        record.reject = True
        record.reject_reasons.append("Player not clean for today")
    else:
        score += 6
        record.risk_notes.append("Injury status unresolved")

    # line edge: 15 pts
    if record.recent_average >= record.line + 2:
        score += 15
    elif record.recent_average >= record.line + 1:
        score += 11
    elif record.recent_average >= record.line:
        score += 8

    # matchup/context placeholder: 10 pts
    score += 6

    # volatility penalty: 10 pts bucket
    if values:
        volatility = max(values) - min(values)
        if volatility <= 4:
            score += 10
        elif volatility <= 7:
            score += 6
        else:
            score += 2
            record.risk_notes.append("Recent stat range is wide")

    # reject rules
    if len(record.missed_recent_team_games) >= 2:
        record.reject = True
        record.reject_reasons.append("Missed 2+ of team’s recent games")

    if record.minutes_average and record.minutes_average < 24:
        record.reject = True
        record.reject_reasons.append("Minutes too low for safe profile")

    if record.hit_rate_last_6 < 4:
        record.risk_notes.append("Hit rate under 4/6")

    record.confidence_score = round(score, 1)