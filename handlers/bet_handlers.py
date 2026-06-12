try:
    from utils.formatters import Formatters
except ImportError:
    from ..utils.formatters import Formatters


class BetHandlers:
    def __init__(self, lottery_service, betting_engine):
        self.lottery_service = lottery_service
        self.betting_engine = betting_engine

    async def handle_place_bet(self, event):
        try:
            params = self._params(event)
            if len(params) < 3:
                yield event.plain_result("格式：/足球投注 <场次编号或match_id> <主胜|平|客胜> <金额>")
                return
            match = self.lottery_service.find_match(params[0])
            if not match:
                yield event.plain_result("未找到该场次，请先使用 /世界杯赛事 查看缓存赛事。")
                return
            bet = self.betting_engine.place_bet(event, match, params[1], params[2])
            yield event.plain_result(Formatters.bet_created(bet))
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

    def _params(self, event):
        return event.message_str.strip().split()[1:]
