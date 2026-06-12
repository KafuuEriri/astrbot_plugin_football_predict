import asyncio
import inspect
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

try:
    from china_lottery_spider import ChinaLotterySpider
    from models import LotteryMatch
    from utils.time_utils import now_ts, parse_match_datetime, sale_close_ts
    from utils.storage import DataStorage
except ImportError:
    from ..china_lottery_spider import ChinaLotterySpider
    from ..models import LotteryMatch
    from ..utils.time_utils import now_ts, parse_match_datetime, sale_close_ts
    from ..utils.storage import DataStorage


class LotteryDataService:
    def __init__(self, storage: DataStorage, config: Optional[Dict[str, Any]] = None, spider=None, logger=None):
        self.storage = storage
        self.config = config or {}
        self.spider = spider or ChinaLotterySpider(logger_instance=logger)
        self.logger = logger

    async def fetch_and_cache(self) -> List[LotteryMatch]:
        fetched_at = now_ts()
        try:
            raw_matches = await asyncio.to_thread(
                self._get_formatted_matches,
                self._config_int("days_ahead", 7),
                self._config_int("result_lookback_days", 2),
            )
            matches = self.normalize_matches(raw_matches, fetched_at)
            self.storage.write_matches(matches)
            self.storage.append_odds_history(matches)
            self.storage.save_fetch_state({
                "last_fetch_at": fetched_at,
                "last_fetch_ok": True,
                "last_error": "",
                "last_match_count": len(matches),
                "last_world_cup_match_count": sum(1 for match in matches if match.is_world_cup),
                "last_had_count": sum(1 for match in matches if match.pool_type == "had"),
                "last_hhad_count": sum(1 for match in matches if match.pool_type == "hhad"),
            })
            return matches
        except Exception as exc:
            self.storage.save_fetch_state({
                "last_fetch_at": fetched_at,
                "last_fetch_ok": False,
                "last_error": str(exc),
            })
            raise

    def _get_formatted_matches(self, days_ahead: int, result_lookback_days: int):
        parameters = inspect.signature(self.spider.get_formatted_matches).parameters
        supports_lookback = len(parameters) >= 2 or any(
            parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in parameters.values()
        )
        if supports_lookback:
            return self.spider.get_formatted_matches(days_ahead, result_lookback_days)
        return self.spider.get_formatted_matches(days_ahead)

    def normalize_matches(self, raw_matches: Iterable[Dict[str, Any]], fetched_at: Optional[int] = None) -> List[LotteryMatch]:
        fetched_at = fetched_at or now_ts()
        return [self.normalize_match(raw, fetched_at) for raw in raw_matches]

    def normalize_match(self, raw: Dict[str, Any], fetched_at: int) -> LotteryMatch:
        odds = raw.get("odds", {})
        compatibility_odds = odds.get("hhad", {})
        odds_h = odds.get("odds_h") or compatibility_odds.get("h") or "0"
        odds_d = odds.get("odds_d") or compatibility_odds.get("d") or "0"
        odds_a = odds.get("odds_a") or compatibility_odds.get("a") or "0"
        match_time = str(raw.get("match_time", ""))
        match_date = str(raw.get("match_date", ""))
        time_part = match_time.replace(match_date, "", 1).strip() if match_date else match_time
        kickoff_ts = parse_match_datetime(match_date, time_part) or parse_match_datetime(match_time)
        close_ts = sale_close_ts(kickoff_ts, self._config_int("bet_close_minutes_before_match", 5))
        pool_type = str(odds.get("pool_type") or odds.get("type") or "had").lower()
        league_name = str(raw.get("league_name", ""))
        return LotteryMatch(
            match_id=str(raw.get("match_id", "")),
            raw_match_id=str(raw.get("raw_match_id", "")),
            match_num=str(raw.get("match_num", "")),
            business_date=str(raw.get("business_date", "")),
            league_name=league_name,
            home_team=str(raw.get("home_team", "")),
            away_team=str(raw.get("away_team", "")),
            match_date=match_date,
            match_time=match_time,
            kickoff_ts=kickoff_ts,
            sale_close_ts=close_ts,
            status=str(raw.get("status", "")),
            pool_type=pool_type,
            goal_line=str(odds.get("goal_line", "")),
            odds_h=Decimal(str(odds_h)),
            odds_d=Decimal(str(odds_d)),
            odds_a=Decimal(str(odds_a)),
            odds_update_time=str(odds.get("update_time", "")),
            home_score=str(raw.get("home_score", "")),
            away_score=str(raw.get("away_score", "")),
            result=str(raw.get("result", "")),
            source=str(raw.get("source", "china_lottery")),
            fetched_at=fetched_at,
            is_world_cup=self.is_world_cup(league_name),
        )

    def get_cached_matches(
        self,
        world_cup_only: bool = False,
        open_only: bool = False,
        timestamp: Optional[int] = None,
        max_days_ahead: Optional[int] = None,
    ) -> List[LotteryMatch]:
        matches = self.storage.get_matches()
        if world_cup_only:
            matches = [match for match in matches if match.is_world_cup]
        if open_only or max_days_ahead is not None:
            timestamp = timestamp or now_ts()
        if open_only:
            matches = [match for match in matches if match.is_open_for_betting(timestamp)]
        if max_days_ahead is not None:
            end_ts = timestamp + max(0, int(max_days_ahead)) * 86400
            matches = [match for match in matches if match.kickoff_ts and timestamp <= match.kickoff_ts <= end_ts]
        return sorted(matches, key=lambda match: (match.kickoff_ts, match.match_num, match.match_id))

    def get_natural_bet_candidates(
        self,
        days: Optional[int] = None,
        max_count: Optional[int] = None,
        timestamp: Optional[int] = None,
    ) -> List[LotteryMatch]:
        days = self._config_int("public_match_days", 2) if days is None else days
        matches = self.get_cached_matches(world_cup_only=True, open_only=True, timestamp=timestamp, max_days_ahead=days)
        return matches[:max_count] if max_count else matches

    def find_open_matches_by_team(
        self,
        team_text: str,
        days: Optional[int] = None,
        timestamp: Optional[int] = None,
    ) -> List[LotteryMatch]:
        needle = self._normalize_team_text(team_text)
        if not needle:
            return []
        return [
            match for match in self.get_natural_bet_candidates(days=days, timestamp=timestamp)
            if needle in self._normalize_team_text(match.home_team) or needle in self._normalize_team_text(match.away_team)
        ]

    def team_side(self, match: LotteryMatch, team_text: str) -> str:
        needle = self._normalize_team_text(team_text)
        if not needle:
            return ""
        if needle in self._normalize_team_text(match.home_team):
            return "home"
        if needle in self._normalize_team_text(match.away_team):
            return "away"
        return ""

    def find_match(self, key: str) -> Optional[LotteryMatch]:
        return self.storage.find_match(key)

    def is_world_cup(self, league_name: str) -> bool:
        keywords = [item.strip() for item in str(self.config.get("competition_keywords", "世界杯,World Cup")).split(",") if item.strip()]
        if not keywords:
            return True
        return any(keyword.lower() in league_name.lower() for keyword in keywords)

    def _normalize_team_text(self, value: str) -> str:
        return "".join(str(value).lower().split())

    def _config_int(self, key: str, default: int) -> int:
        try:
            return int(self.config.get(key, default))
        except (TypeError, ValueError):
            return default
