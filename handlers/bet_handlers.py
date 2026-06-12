try:
    from utils.formatters import Formatters
    from utils.validators import parse_selection
except ImportError:
    from ..utils.formatters import Formatters
    from ..utils.validators import parse_selection


class BetHandlers:
    def __init__(self, lottery_service, betting_engine, intent_parser=None):
        self.lottery_service = lottery_service
        self.betting_engine = betting_engine
        self.intent_parser = intent_parser

    async def handle_place_bet(self, event):
        try:
            params = self._params(event)
            if len(params) >= 3 and self.lottery_service.find_match(params[0]):
                yield event.plain_result(self._place_exact_bet(event, params[0], params[1], params[2]))
                return
            text = " ".join(params).strip()
            if not text:
                yield event.plain_result(Formatters.natural_bet_usage())
                return
            yield event.plain_result(await self._place_natural_bet(event, text))
        except Exception as exc:
            yield event.plain_result(f"投注失败：{exc}")

    async def handle_simple_bet(self, event):
        try:
            text = " ".join(self._params(event)).strip()
            if not text:
                yield event.plain_result(Formatters.natural_bet_usage())
                return
            yield event.plain_result(await self._place_natural_bet(event, text))
        except Exception as exc:
            yield event.plain_result(f"投注失败：{exc}")

    async def handle_cancel_bet(self, event):
        try:
            params = self._params(event)
            if not params:
                yield event.plain_result("格式：/足球撤单 <投注单号>")
                return
            bet = self.betting_engine.cancel_bet(event, params[0])
            yield event.plain_result(Formatters.bet_cancelled(bet))
        except Exception as exc:
            yield event.plain_result(f"撤单失败：{exc}")

    async def handle_my_bets(self, event):
        try:
            params = self._params(event)
            status = None
            page = 1
            if params:
                if params[0] == "未结":
                    status = "pending"
                elif params[0] == "已结":
                    status = None
                else:
                    try:
                        page = max(1, int(params[0]))
                    except ValueError:
                        pass
            bets = self.betting_engine.user_bets(event, status)
            if params and params[0] == "已结":
                bets = [bet for bet in bets if bet.status != "pending"]
            yield event.plain_result(Formatters.bet_history(bets, page=page))
        except Exception as exc:
            yield event.plain_result(f"查询投注失败：{exc}")

    def _place_exact_bet(self, event, match_key: str, selection: str, amount: str) -> str:
        match = self.lottery_service.find_match(match_key)
        if not match:
            return "未找到该场次，请先使用 /世界杯赛事 查看缓存赛事。"
        bet = self.betting_engine.place_bet(event, match, selection, amount)
        return Formatters.bet_created(bet)

    async def _place_natural_bet(self, event, text: str) -> str:
        if not self.intent_parser:
            return Formatters.natural_bet_usage()
        intent = await self.intent_parser.parse(event, text)
        if not intent:
            return Formatters.natural_bet_usage()

        match = self.lottery_service.find_match(intent.match_key) if intent.match_key else None
        candidates = []
        if not match and intent.team_text:
            candidates = self.lottery_service.find_open_matches_by_team(intent.team_text)
            if len(candidates) == 1:
                match = candidates[0]
            elif len(candidates) > 1:
                return Formatters.natural_bet_candidates(intent.team_text, candidates)

        if not match:
            return Formatters.natural_bet_no_match(intent.team_text or intent.match_key)

        selection = self._selection_for_intent(intent, match)
        if not selection:
            return Formatters.natural_bet_usage()

        bet = self.betting_engine.place_bet(event, match, selection, intent.amount_text)
        return Formatters.bet_created(bet)

    def _selection_for_intent(self, intent, match) -> str:
        selection = str(intent.selection_text).strip()
        if selection in ("赢", "胜", "输", "负"):
            side = self.lottery_service.team_side(match, intent.team_text)
            if not side:
                return ""
            if selection in ("赢", "胜"):
                return "H" if side == "home" else "A"
            return "A" if side == "home" else "H"
        try:
            return parse_selection(selection)
        except ValueError:
            return ""

    def _params(self, event):
        return event.message_str.strip().split()[1:]
