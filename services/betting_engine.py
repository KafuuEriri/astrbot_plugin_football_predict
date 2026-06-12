from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

try:
    from models import BetOrder, LotteryMatch, UserAccount
    from utils.storage import DataStorage
    from utils.time_utils import now_ts, today_str
    from utils.validators import money, money_text, parse_selection, selection_text, validate_bet_amount
except ImportError:
    from ..models import BetOrder, LotteryMatch, UserAccount
    from ..utils.storage import DataStorage
    from ..utils.time_utils import now_ts, today_str
    from ..utils.validators import money, money_text, parse_selection, selection_text, validate_bet_amount


class BettingEngine:
    def __init__(self, storage: DataStorage, config: Optional[Dict[str, Any]] = None):
        self.storage = storage
        self.config = config or {}

    def get_or_create_user(self, context: Dict[str, str], timestamp: Optional[int] = None) -> UserAccount:
        user = self.storage.get_user(context["user_id"])
        if user:
            if context.get("username"):
                user.username = context["username"]
            return user
        timestamp = timestamp or now_ts()
        user = UserAccount(
            user_id=context["user_id"],
            username=context.get("username", ""),
            platform_name=context.get("platform_name", ""),
            sender_id=context.get("sender_id", ""),
            session_id=context.get("session_id", ""),
            balance=Decimal(str(self.config.get("initial_balance", 0))).quantize(Decimal("0.01")),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.storage.save_user(user)
        return user

    def get_or_create_user_from_event(self, event, timestamp: Optional[int] = None) -> UserAccount:
        return self.get_or_create_user(self.storage.get_event_context(event), timestamp)

    def checkin(self, event, date: Optional[str] = None, timestamp: Optional[int] = None) -> Tuple[bool, UserAccount, Decimal]:
        context = self.storage.get_event_context(event)
        timestamp = timestamp or now_ts()
        date = date or today_str()
        user = self.get_or_create_user(context, timestamp)
        if user.last_checkin_date == date:
            return False, user, Decimal("0")
        amount = Decimal(str(self.config.get("daily_checkin_amount", 20000))).quantize(Decimal("0.01"))
        user.add_balance(amount)
        user.total_checkin_amount += amount
        user.last_checkin_date = date
        user.checkin_count += 1
        user.updated_at = timestamp
        self.storage.save_user(user)
        self.storage.append_transaction(user.user_id, user.session_id, "checkin", amount, user.balance, note="每日签到", created_at=timestamp)
        return True, user, amount

    def place_bet(self, event, match: LotteryMatch, selection_value: str, amount_value, timestamp: Optional[int] = None) -> BetOrder:
        timestamp = timestamp or now_ts()
        if not match.is_open_for_betting(timestamp):
            raise ValueError("该比赛已停售，不能投注")
        if not match.is_world_cup:
            raise ValueError("当前只开放世界杯赛事投注")

        context = self.storage.get_event_context(event)
        user = self.get_or_create_user(context, timestamp)
        stake = money(amount_value)
        validate_bet_amount(stake, self._money_config("min_bet_amount", 100), self._money_config("max_bet_amount", 100000))
        if not user.can_afford(stake):
            raise ValueError(f"余额不足，当前余额 {money_text(user.balance)}")

        selection = parse_selection(selection_value)
        odds = match.selection_odds(selection)
        potential_payout = Decimal(money_text(stake * odds))
        bet = BetOrder(
            bet_id=self.storage.next_bet_id(),
            user_id=user.user_id,
            username=user.username,
            session_id=user.session_id,
            match_id=match.match_id,
            match_num=match.match_num,
            league_name=match.league_name,
            home_team=match.home_team,
            away_team=match.away_team,
            match_time=match.match_time,
            pool_type=match.pool_type,
            goal_line=match.goal_line,
            selection=selection,
            selection_text=selection_text(selection),
            odds_locked=odds,
            stake=stake,
            potential_payout=potential_payout,
            created_at=timestamp,
            updated_at=timestamp,
        )
        user.deduct_balance(stake)
        user.total_staked += stake
        user.updated_at = timestamp
        self.storage.save_user(user)
        self.storage.save_bet(bet)
        self.storage.append_transaction(user.user_id, user.session_id, "stake", -stake, user.balance, bet.bet_id, "投注扣款", timestamp)
        return bet

    def cancel_bet(self, event, bet_id: str, match: Optional[LotteryMatch] = None, timestamp: Optional[int] = None) -> BetOrder:
        timestamp = timestamp or now_ts()
        context = self.storage.get_event_context(event)
        bet = self.storage.get_bet(bet_id)
        if not bet:
            raise ValueError("投注单不存在")
        if bet.user_id != context["user_id"]:
            raise ValueError("只能撤销自己的投注单")
        if bet.status != "pending":
            raise ValueError("该投注单已结算或已撤销")
        match = match or self.storage.find_match(bet.match_id)
        if match and not match.is_open_for_betting(timestamp):
            raise ValueError("该比赛已停售，不能撤单")
        user = self.storage.get_user(bet.user_id)
        if not user:
            raise ValueError("账户不存在")

        user.add_balance(bet.stake)
        user.cancelled += 1
        user.updated_at = timestamp
        bet.status = "cancelled"
        bet.payout = bet.stake
        bet.updated_at = timestamp
        bet.settled_at = timestamp
        self.storage.save_user(user)
        self.storage.save_bet(bet)
        self.storage.append_transaction(user.user_id, user.session_id, "refund", bet.stake, user.balance, bet.bet_id, "撤单退款", timestamp)
        return bet

    def account_summary(self, event) -> Dict[str, Any]:
        user = self.get_or_create_user_from_event(event)
        pending = [bet for bet in self.storage.get_user_bets(user.user_id, "pending")]
        pending_stake = sum((bet.stake for bet in pending), Decimal("0"))
        return {"user": user, "pending_count": len(pending), "pending_stake": pending_stake}

    def user_bets(self, event, status: Optional[str] = None) -> List[BetOrder]:
        user = self.get_or_create_user_from_event(event)
        return self.storage.get_user_bets(user.user_id, status)

    def group_ranking(self, event) -> List[Dict[str, Any]]:
        context = self.storage.get_event_context(event)
        users = [user for user in self.storage.get_all_users() if user.session_id == context["session_id"]]
        rows = []
        for user in users:
            pending_stake = sum((bet.stake for bet in self.storage.get_user_bets(user.user_id, "pending")), Decimal("0"))
            net_assets = user.balance + pending_stake
            profit = net_assets - user.total_checkin_amount
            rows.append({"user": user, "net_assets": net_assets, "profit": profit, "pending_stake": pending_stake})
        return sorted(rows, key=lambda row: (row["net_assets"], row["profit"]), reverse=True)

    def _money_config(self, key: str, default: int) -> Decimal:
        return Decimal(str(self.config.get(key, default))).quantize(Decimal("0.01"))
