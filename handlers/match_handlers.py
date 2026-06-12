try:
    from utils.formatters import Formatters
except ImportError:
    from ..utils.formatters import Formatters


class MatchHandlers:
    def __init__(self, lottery_service):
        self.lottery_service = lottery_service

    async def handle_help(self, event):
        yield event.plain_result(Formatters.help())

    async def handle_matches(self, event):
        try:
            params = self._params(event)
            show_all = bool(params and params[0] == "全部")
            page_index = 1 if show_all else 0
            page = self._page(params[page_index]) if len(params) > page_index else 1
            max_days = None if show_all else self.lottery_service._config_int("public_match_days", 2)
            matches = self.lottery_service.get_cached_matches(world_cup_only=True, open_only=True, max_days_ahead=max_days)
            yield event.plain_result(Formatters.match_list(matches, page=page))
        except Exception as exc:
            yield event.plain_result(f"查询赛事失败：{exc}")

    async def handle_odds(self, event):
        try:
            params = self._params(event)
            if not params:
                yield event.plain_result("格式：/足球赔率 <场次编号或match_id>")
                return
            match = self.lottery_service.find_match(params[0])
            if not match:
                yield event.plain_result("未找到该场次，请先使用 /世界杯赛事 查看缓存赛事。")
                return
            yield event.plain_result(Formatters.match_detail(match))
        except Exception as exc:
            yield event.plain_result(f"查询赔率失败：{exc}")

    def _params(self, event):
        return event.message_str.strip().split()[1:]

    def _page(self, value: str) -> int:
        try:
            return max(1, int(value))
        except ValueError:
            return 1
