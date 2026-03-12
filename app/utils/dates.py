from datetime import datetime, timezone

def utc_today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def safe_iso_date(value: str) -> str:
    return value[:10] if value else ""