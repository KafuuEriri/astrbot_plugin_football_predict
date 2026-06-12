import importlib
import sys
import types
import unittest


class _Logger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass


class _Filter:
    def command(self, *args, **kwargs):
        return lambda func: func

    def permission_type(self, *args, **kwargs):
        return lambda func: func


class _Star:
    def __init__(self, context=None, config=None):
        pass


class _Context:
    pass


class _AstrMessageEvent:
    pass


class _PermissionType:
    ADMIN = "admin"


def _install_astrbot_stubs():
    if "astrbot.api" in sys.modules:
        return
    astrbot = types.ModuleType("astrbot")
    api = types.ModuleType("astrbot.api")
    api.logger = _Logger()
    event = types.ModuleType("astrbot.api.event")
    event.AstrMessageEvent = _AstrMessageEvent
    event.filter = _Filter()
    star = types.ModuleType("astrbot.api.star")
    star.Context = _Context
    star.Star = _Star
    core = types.ModuleType("astrbot.core")
    core_star = types.ModuleType("astrbot.core.star")
    core_filter = types.ModuleType("astrbot.core.star.filter")
    permission = types.ModuleType("astrbot.core.star.filter.permission")
    permission.PermissionType = _PermissionType
    sys.modules.update({
        "astrbot": astrbot,
        "astrbot.api": api,
        "astrbot.api.event": event,
        "astrbot.api.star": star,
        "astrbot.core": core,
        "astrbot.core.star": core_star,
        "astrbot.core.star.filter": core_filter,
        "astrbot.core.star.filter.permission": permission,
    })


class _LotteryService:
    def __init__(self, fail=False):
        self.fail = fail
        self.fetch_count = 0

    async def fetch_and_cache(self):
        self.fetch_count += 1
        if self.fail:
            raise RuntimeError("fetch failed")
        return []


class _SettlementService:
    def __init__(self):
        self.settle_count = 0

    def settle_pending(self):
        self.settle_count += 1
        return {"scanned": 1, "settled": 1}


class MainLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def test_safe_fetch_settles_after_successful_refresh(self):
        _install_astrbot_stubs()
        main = importlib.import_module("main")
        plugin = main.FootballPredictPlugin.__new__(main.FootballPredictPlugin)
        plugin.lottery_service = _LotteryService()
        plugin.settlement_service = _SettlementService()
        await plugin._safe_fetch_once()
        self.assertEqual(plugin.lottery_service.fetch_count, 1)
        self.assertEqual(plugin.settlement_service.settle_count, 1)

    async def test_safe_fetch_skips_settle_when_refresh_fails(self):
        _install_astrbot_stubs()
        main = importlib.import_module("main")
        plugin = main.FootballPredictPlugin.__new__(main.FootballPredictPlugin)
        plugin.lottery_service = _LotteryService(fail=True)
        plugin.settlement_service = _SettlementService()
        await plugin._safe_fetch_once()
        self.assertEqual(plugin.lottery_service.fetch_count, 1)
        self.assertEqual(plugin.settlement_service.settle_count, 0)


if __name__ == "__main__":
    unittest.main()
