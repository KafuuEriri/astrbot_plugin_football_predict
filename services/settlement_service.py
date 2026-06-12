from decimal import Decimal
from typing import Any, Dict, Optional

try:
    from models import BetOrder, LotteryMatch
    from utils.storage import DataStorage
    from utils.time_utils import now_ts
    from utils.validators import money_text, parse_selection
except ImportError:
    from ..models import BetOrder, LotteryMatch
    from ..utils.storage import DataStorage
    from ..utils.time_utils import now_ts
    from ..utils.validators import money_text, parse_selection


class SettlementService:
    def __init__(self, storage: DataStorage, config: Optional[Dict[str, Any]] = None):
        self.storage = storage
        self.config = config or {}

    def settle_pending(self, timestamp: Optional[int] = None) -> Dict[str, int]:
        timestamp = timestamp or now_ts()
        summary = {"scanned": 0, "settled": 0, "won": 0, "lost": 0, "void": 0, "skipped": 0}
        manual_results = self._manual_result_map()

        for bet in self.storage.get_pending_bets():
            summary["scanned"] += 1
            result = self._result_for_bet(bet, manual_results)
            if not result:
                summary["skipped"] += 1
                continue
            user = self.storage.get_user(bet.user_id)
            if not user:
                summary["skipped"] += 1
                continue

            if result == "VOID":
                user.add_balance(bet.stake)
                user.voids += 1
                bet.status = "void"
                bet.payout = bet.stake
                self.storage.append_transaction(user.user_id, user.session_id, "void_refund", bet.stake, user.balance, bet.bet_id, "无效比赛退款", timestamp)
                summary["void"] += 1
            elif bet.selection == result:
                payout = Decimal(money_text(bet.stake * bet.odds_locked))
                user.add_balance(payout)
                user.total_payout += payout
                user.wins += 1
                bet.status = "won"
                bet.payout = payout
                self.storage.append_transaction(user.user_id, user.session_id, "payout", payout, user.balance, bet.bet_id, "投注中奖", timestamp)
                summary["won"] += 1
            else:
                user.losses += 1
                bet.status = "lost"
                bet.payout = Decimal("0")
                summary["lost"] += 1

            bet.result = result
            bet.updated_at = timestamp
            bet.settled_at = timestamp
            user.updated_at = timestamp
            self.storage.save_user(user)
            self.storage.save_bet(bet)
            summary["settled"] += 1

        return summary

    def record_manual_result(
        self,
        match_key: str,
        result_value: str,
        entered_by: str = "",
        score: str = "",
        note: str = "",
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        timestamp = timestamp or now_ts()
        result = self._parse_result_or_void(result_value)
        match = self.storage.find_match(match_key)
        home_score, away_score = self._parse_score(score)
        row = {
            "match_id": match.match_id if match else match_key,
            "match_num": match.match_num if match else match_key,
            "result": result,
            "home_score": home_score,
            "away_score": away_score,
            "entered_by": entered_by,
            "entered_at": str(timestamp),
            "note": note,
        }
        self.storage.save_manual_result(row)
        return row

    def _result_for_bet(self, bet: BetOrder, manual_results: Dict[str, Dict[str, str]]) -> str:
        manual = manual_results.get(bet.match_id) or manual_results.get(bet.match_num)
        if manual:
            return manual.get("result", "")
        match = self.storage.find_match(bet.match_id)
        if not match:
            return ""
        return match.compute_result()

    def _manual_result_map(self) -> Dict[str, Dict[str, str]]:
        results = {}
        for row in self.storage.get_manual_results():
            if row.get("match_id"):
                results[row["match_id"]] = row
            if row.get("match_num"):
                results[row["match_num"]] = row
        return results

    def _parse_result_or_void(self, value: str) -> str:
        text = str(value).strip().lower()
        if text in ("void", "无效", "取消", "延期"):
            return "VOID"
        return parse_selection(value)

    def _parse_score(self, score: str):
        if not score:
            return "", ""
        normalized = score.replace(":", "-").replace("：", "-")
        parts = normalized.split("-", 1)
        if len(parts) != 2:
            return "", ""
        return parts[0].strip(), parts[1].strip()
