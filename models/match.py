from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

try:
    from utils.validators import money_text
except ImportError:
    from ..utils.validators import money_text


@dataclass
class LotteryMatch:
    match_id: str
    raw_match_id: str = ""
    match_num: str = ""
    business_date: str = ""
    league_name: str = ""
    home_team: str = ""
    away_team: str = ""
    match_date: str = ""
    match_time: str = ""
    kickoff_ts: int = 0
    sale_close_ts: int = 0
    status: str = ""
    pool_type: str = "had"
    goal_line: str = ""
    odds_h: Decimal = Decimal("0")
    odds_d: Decimal = Decimal("0")
    odds_a: Decimal = Decimal("0")
    odds_update_time: str = ""
    home_score: str = ""
    away_score: str = ""
    result: str = ""
    source: str = "china_lottery"
    fetched_at: int = 0
    is_world_cup: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LotteryMatch":
        return cls(
            match_id=str(data.get("match_id", "")),
            raw_match_id=str(data.get("raw_match_id", "")),
            match_num=str(data.get("match_num", "")),
            business_date=str(data.get("business_date", "")),
            league_name=str(data.get("league_name", "")),
            home_team=str(data.get("home_team", "")),
            away_team=str(data.get("away_team", "")),
            match_date=str(data.get("match_date", "")),
            match_time=str(data.get("match_time", "")),
            kickoff_ts=int(float(data.get("kickoff_ts") or 0)),
            sale_close_ts=int(float(data.get("sale_close_ts") or 0)),
            status=str(data.get("status", "")),
            pool_type=str(data.get("pool_type", "had") or "had"),
            goal_line=str(data.get("goal_line", "")),
            odds_h=Decimal(str(data.get("odds_h") or "0")),
            odds_d=Decimal(str(data.get("odds_d") or "0")),
            odds_a=Decimal(str(data.get("odds_a") or "0")),
            odds_update_time=str(data.get("odds_update_time", "")),
            home_score=str(data.get("home_score", "")),
            away_score=str(data.get("away_score", "")),
            result=str(data.get("result", "")),
            source=str(data.get("source", "china_lottery")),
            fetched_at=int(float(data.get("fetched_at") or 0)),
            is_world_cup=str(data.get("is_world_cup", "false")).lower() in ("1", "true", "yes"),
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "match_id": self.match_id,
            "raw_match_id": self.raw_match_id,
            "match_num": self.match_num,
            "business_date": self.business_date,
            "league_name": self.league_name,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "match_date": self.match_date,
            "match_time": self.match_time,
            "kickoff_ts": str(self.kickoff_ts),
            "sale_close_ts": str(self.sale_close_ts),
            "status": self.status,
            "pool_type": self.pool_type,
            "goal_line": self.goal_line,
            "odds_h": money_text(self.odds_h),
            "odds_d": money_text(self.odds_d),
            "odds_a": money_text(self.odds_a),
            "odds_update_time": self.odds_update_time,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "result": self.result,
            "source": self.source,
            "fetched_at": str(self.fetched_at),
            "is_world_cup": "true" if self.is_world_cup else "false",
        }

    def display_name(self) -> str:
        return f"{self.match_num} {self.home_team} vs {self.away_team}".strip()

    def is_open_for_betting(self, timestamp: Optional[int] = None) -> bool:
        if not self.sale_close_ts:
            return False
        if timestamp is None:
            import time
            timestamp = int(time.time())
        return timestamp < self.sale_close_ts

    def selection_odds(self, selection: str) -> Decimal:
        if selection == "H":
            return self.odds_h
        if selection == "D":
            return self.odds_d
        if selection == "A":
            return self.odds_a
        raise ValueError("无效投注选项")

    def compute_result(self) -> str:
        normalized = self._normalize_result(self.result)
        if normalized:
            return normalized
        if self.home_score == "" or self.away_score == "":
            return ""
        home = Decimal(str(self.home_score))
        away = Decimal(str(self.away_score))
        if self.pool_type == "hhad" and self.goal_line != "":
            home += Decimal(str(self.goal_line))
        if home > away:
            return "H"
        if home == away:
            return "D"
        return "A"

    def _normalize_result(self, result: str) -> str:
        text = str(result).strip().upper()
        if text in ("H", "D", "A"):
            return text
        mapping = {"主胜": "H", "胜": "H", "平": "D", "平局": "D", "客胜": "A", "负": "A"}
        return mapping.get(text, "")
