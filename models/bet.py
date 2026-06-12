from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

try:
    from utils.validators import money_text
except ImportError:
    from ..utils.validators import money_text


@dataclass
class BetOrder:
    bet_id: str
    user_id: str
    username: str
    session_id: str
    match_id: str
    match_num: str
    league_name: str
    home_team: str
    away_team: str
    match_time: str
    pool_type: str
    selection: str
    selection_text: str
    odds_locked: Decimal
    stake: Decimal
    potential_payout: Decimal
    goal_line: str = ""
    status: str = "pending"
    result: str = ""
    payout: Decimal = Decimal("0")
    created_at: int = 0
    updated_at: int = 0
    settled_at: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BetOrder":
        settled_at = data.get("settled_at")
        return cls(
            bet_id=str(data.get("bet_id", "")),
            user_id=str(data.get("user_id", "")),
            username=str(data.get("username", "")),
            session_id=str(data.get("session_id", "")),
            match_id=str(data.get("match_id", "")),
            match_num=str(data.get("match_num", "")),
            league_name=str(data.get("league_name", "")),
            home_team=str(data.get("home_team", "")),
            away_team=str(data.get("away_team", "")),
            match_time=str(data.get("match_time", "")),
            pool_type=str(data.get("pool_type", "had")),
            goal_line=str(data.get("goal_line", "")),
            selection=str(data.get("selection", "")),
            selection_text=str(data.get("selection_text", "")),
            odds_locked=Decimal(str(data.get("odds_locked") or "0")),
            stake=Decimal(str(data.get("stake") or "0")),
            potential_payout=Decimal(str(data.get("potential_payout") or "0")),
            status=str(data.get("status", "pending")),
            result=str(data.get("result", "")),
            payout=Decimal(str(data.get("payout") or "0")),
            created_at=int(data.get("created_at") or 0),
            updated_at=int(data.get("updated_at") or 0),
            settled_at=int(settled_at) if settled_at not in (None, "") else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bet_id": self.bet_id,
            "user_id": self.user_id,
            "username": self.username,
            "session_id": self.session_id,
            "match_id": self.match_id,
            "match_num": self.match_num,
            "league_name": self.league_name,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "match_time": self.match_time,
            "pool_type": self.pool_type,
            "goal_line": self.goal_line,
            "selection": self.selection,
            "selection_text": self.selection_text,
            "odds_locked": money_text(self.odds_locked),
            "stake": money_text(self.stake),
            "potential_payout": money_text(self.potential_payout),
            "status": self.status,
            "result": self.result,
            "payout": money_text(self.payout),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settled_at": self.settled_at,
        }
