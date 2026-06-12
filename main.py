import asyncio
from contextlib import suppress

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.star.filter.permission import PermissionType

try:
    from .handlers.admin_handlers import AdminHandlers
    from .handlers.bet_handlers import BetHandlers
    from .handlers.match_handlers import MatchHandlers
    from .handlers.user_handlers import UserHandlers
    from .services.betting_engine import BettingEngine
    from .services.lottery_data_service import LotteryDataService
    from .services.settlement_service import SettlementService
    from .utils.storage import DataStorage
except ImportError:
    from handlers.admin_handlers import AdminHandlers
    from handlers.bet_handlers import BetHandlers
    from handlers.match_handlers import MatchHandlers
    from handlers.user_handlers import UserHandlers
    from services.betting_engine import BettingEngine
    from services.lottery_data_service import LotteryDataService
    from services.settlement_service import SettlementService
    from utils.storage import DataStorage


class FootballPredictPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context, config)
        self.plugin_config = config or {}
        self._tasks = []
        self._initialize_services()
        self._initialize_handlers()

    def _initialize_services(self):
        self.storage = DataStorage("astrbot_plugin_football_predict")
        self.lottery_service = LotteryDataService(self.storage, self.plugin_config, logger=logger)
        self.betting_engine = BettingEngine(self.storage, self.plugin_config)
        self.settlement_service = SettlementService(self.storage, self.plugin_config)

    def _initialize_handlers(self):
        self.user_handlers = UserHandlers(self.betting_engine)
        self.match_handlers = MatchHandlers(self.lottery_service)
        self.bet_handlers = BetHandlers(self.lottery_service, self.betting_engine)
        self.admin_handlers = AdminHandlers(self.storage, self.lottery_service, self.settlement_service)

    async def initialize(self):
        if self._config_bool("auto_fetch_on_start", True):
            self._tasks.append(asyncio.create_task(self._safe_fetch_once()))
        fetch_interval = self._config_int("fetch_interval_minutes", 180)
        settlement_interval = self._config_int("settlement_interval_minutes", 10)
        if fetch_interval > 0:
            self._tasks.append(asyncio.create_task(self._fetch_loop(fetch_interval)))
        if settlement_interval > 0:
            self._tasks.append(asyncio.create_task(self._settlement_loop(settlement_interval)))
        logger.info("体彩世界杯模拟投注插件启动完成")

    async def terminate(self):
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        logger.info("体彩世界杯模拟投注插件已停止")

    async def _safe_fetch_once(self):
        try:
            await self.lottery_service.fetch_and_cache()
        except Exception as exc:
            logger.warning(f"体彩缓存刷新失败: {exc}")

    async def _fetch_loop(self, interval_minutes: int):
        while True:
            await asyncio.sleep(max(60, interval_minutes * 60))
            await self._safe_fetch_once()

    async def _settlement_loop(self, interval_minutes: int):
        while True:
            await asyncio.sleep(max(60, interval_minutes * 60))
            try:
                self.settlement_service.settle_pending()
            except Exception as exc:
                logger.warning(f"足球投注结算失败: {exc}")

    def _config_int(self, key: str, default: int) -> int:
        try:
            return int(self.plugin_config.get(key, default))
        except (TypeError, ValueError):
            return default

    def _config_bool(self, key: str, default: bool) -> bool:
        value = self.plugin_config.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")

    @filter.command("足球帮助")
    async def football_help(self, event: AstrMessageEvent):
        async for result in self.match_handlers.handle_help(event):
            yield result

    @filter.command("足球签到")
    async def football_checkin(self, event: AstrMessageEvent):
        async for result in self.user_handlers.handle_checkin(event):
            yield result

    @filter.command("足球账户")
    async def football_account(self, event: AstrMessageEvent):
        async for result in self.user_handlers.handle_account(event):
            yield result

    @filter.command("世界杯赛事")
    async def football_matches(self, event: AstrMessageEvent):
        async for result in self.match_handlers.handle_matches(event):
            yield result

    @filter.command("足球赔率")
    async def football_odds(self, event: AstrMessageEvent):
        async for result in self.match_handlers.handle_odds(event):
            yield result

    @filter.command("足球投注")
    async def football_bet(self, event: AstrMessageEvent):
        async for result in self.bet_handlers.handle_place_bet(event):
            yield result

    @filter.command("足球撤单")
    async def football_cancel(self, event: AstrMessageEvent):
        async for result in self.bet_handlers.handle_cancel_bet(event):
            yield result

    @filter.command("我的投注")
    async def football_my_bets(self, event: AstrMessageEvent):
        async for result in self.bet_handlers.handle_my_bets(event):
            yield result

    @filter.command("足球排行")
    async def football_ranking(self, event: AstrMessageEvent):
        async for result in self.user_handlers.handle_ranking(event):
            yield result

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("足球刷新")
    async def football_refresh(self, event: AstrMessageEvent):
        async for result in self.admin_handlers.handle_refresh(event):
            yield result

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("足球结算")
    async def football_settle(self, event: AstrMessageEvent):
        async for result in self.admin_handlers.handle_settle(event):
            yield result

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("足球状态")
    async def football_status(self, event: AstrMessageEvent):
        async for result in self.admin_handlers.handle_status(event):
            yield result

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("足球录赛果")
    async def football_record_result(self, event: AstrMessageEvent):
        async for result in self.admin_handlers.handle_record_result(event):
            yield result
