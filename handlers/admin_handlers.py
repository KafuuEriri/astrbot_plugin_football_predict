try:
    from utils.formatters import Formatters
except ImportError:
    from ..utils.formatters import Formatters


class AdminHandlers:
    def __init__(self, storage, lottery_service, settlement_service):
        self.storage = storage
        self.lottery_service = lottery_service
        self.settlement_service = settlement_service

    async def handle_refresh(self, event):
        try:
            matches = await self.lottery_service.fetch_and_cache()
            world_cup_count = sum(1 for match in matches if match.is_world_cup)
            yield event.plain_result(f"刷新完成：缓存 {len(matches)} 场，其中世界杯 {world_cup_count} 场。")
        except Exception as exc:
            yield event.plain_result(f"刷新失败：{exc}")

    async def handle_settle(self, event):
        try:
            summary = self.settlement_service.settle_pending()
            yield event.plain_result(Formatters.settlement_summary(summary))
        except Exception as exc:
            yield event.plain_result(f"结算失败：{exc}")

    async def handle_status(self, event):
        try:
            fetch_state = self.storage.get_fetch_state()
            cached_count = len(self.storage.get_matches())
            pending_count = len(self.storage.get_pending_bets())
            yield event.plain_result(Formatters.status(fetch_state, cached_count, pending_count))
        except Exception as exc:
            yield event.plain_result(f"查询状态失败：{exc}")

    async def handle_record_result(self, event):
        try:
            params = event.message_str.strip().split()[1:]
            if len(params) < 2:
                yield event.plain_result("格式：/足球录赛果 <场次编号或match_id> <主胜|平|客胜|无效> [比分]")
                return
            entered_by = event.get_sender_id() if hasattr(event, "get_sender_id") else ""
            row = self.settlement_service.record_manual_result(params[0], params[1], entered_by=entered_by, score=params[2] if len(params) > 2 else "")
            yield event.plain_result(f"赛果已记录：{row['match_num']} -> {row['result']}。可执行 /足球结算 结算投注。")
        except Exception as exc:
            yield event.plain_result(f"记录赛果失败：{exc}")
