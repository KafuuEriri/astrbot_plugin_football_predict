try:
    from utils.formatters import Formatters
except ImportError:
    from ..utils.formatters import Formatters


class UserHandlers:
    def __init__(self, betting_engine):
        self.betting_engine = betting_engine

    async def handle_checkin(self, event):
        try:
            created, user, amount = self.betting_engine.checkin(event)
            yield event.plain_result(Formatters.checkin(created, user, amount))
        except Exception as exc:
            yield event.plain_result(f"签到失败：{exc}")

    async def handle_account(self, event):
        try:
            yield event.plain_result(Formatters.account(self.betting_engine.account_summary(event)))
        except Exception as exc:
            yield event.plain_result(f"查询账户失败：{exc}")

    async def handle_ranking(self, event):
        try:
            yield event.plain_result(Formatters.ranking(self.betting_engine.group_ranking(event)))
        except Exception as exc:
            yield event.plain_result(f"查询排行失败：{exc}")
