from datetime import datetime, timedelta
from typing import Optional


def now_ts() -> int:
    return int(datetime.now().timestamp())


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def parse_match_datetime(match_date: str, match_time: str = "") -> int:
    text = f"{match_date} {match_time}".strip()
    if not text:
        return 0
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(text, fmt).timestamp())
        except ValueError:
            pass
    try:
        return int(datetime.fromisoformat(text).timestamp())
    except ValueError:
        return 0


def sale_close_ts(kickoff_ts: int, minutes_before_match: int) -> int:
    if not kickoff_ts:
        return 0
    return int((datetime.fromtimestamp(kickoff_ts) - timedelta(minutes=minutes_before_match)).timestamp())


def format_ts(timestamp: Optional[int]) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
