import unittest

from handlers.bet_handlers import BetHandlers
from handlers.match_handlers import MatchHandlers
from services.betting_engine import BettingEngine
from services.lottery_data_service import LotteryDataService
from services.natural_bet_intent import NaturalBetIntentParser
from tests.helpers import FakeContext, FakeEvent, TempStorageMixin, sample_match


class HandlerTest(TempStorageMixin, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.engine = BettingEngine(self.storage, {"daily_checkin_amount": 20000})
        self.lottery_service = LotteryDataService(self.storage, {}, spider=object())

    async def test_match_list_reads_cache(self):
        self.storage.write_matches([sample_match()])
        handler = MatchHandlers(self.lottery_service)
        event = FakeEvent(message_str="/世界杯赛事 1")
        results = []
        async for result in handler.handle_matches(event):
            results.append(result)
        self.assertEqual(len(results), 1)
        self.assertIn("周五001", results[0])

    async def test_match_list_defaults_to_two_days_and_all_shows_full_cache(self):
        near = sample_match(match_id="lottery_10", match_num="周五010", kickoff_offset=3600)
        far = sample_match(match_id="lottery_11", match_num="周一011", kickoff_offset=3 * 86400)
        self.storage.write_matches([near, far])
        handler = MatchHandlers(self.lottery_service)
        default_results = []
        async for result in handler.handle_matches(FakeEvent(message_str="/世界杯赛事")):
            default_results.append(result)
        all_results = []
        async for result in handler.handle_matches(FakeEvent(message_str="/世界杯赛事 全部")):
            all_results.append(result)
        self.assertIn("周五010", default_results[0])
        self.assertNotIn("周一011", default_results[0])
        self.assertIn("周一011", all_results[0])

    async def test_exact_bet_command_still_works(self):
        self.storage.write_matches([sample_match(home_team="阿根廷", away_team="法国")])
        event = self._funded_event("/足球投注 周五001 主胜 1000")
        handler = self._bet_handler()
        results = []
        async for result in handler.handle_place_bet(event):
            results.append(result)
        self.assertIn("投注成功", results[0])
        self.assertEqual(len(self.storage.get_all_bets()), 1)

    async def test_natural_bet_under_football_bet_command(self):
        self.storage.write_matches([sample_match(home_team="阿根廷", away_team="法国")])
        event = self._funded_event("/足球投注 买阿根廷赢1000")
        handler = self._bet_handler()
        results = []
        async for result in handler.handle_place_bet(event):
            results.append(result)
        bet = self.storage.get_all_bets()[0]
        self.assertIn("投注成功", results[0])
        self.assertEqual(bet.selection, "H")

    async def test_simple_buy_command_places_natural_bet(self):
        self.storage.write_matches([sample_match(home_team="阿根廷", away_team="法国")])
        event = self._funded_event("/买球 法国赢1000")
        handler = self._bet_handler()
        results = []
        async for result in handler.handle_simple_bet(event):
            results.append(result)
        bet = self.storage.get_all_bets()[0]
        self.assertIn("投注成功", results[0])
        self.assertEqual(bet.selection, "A")

    async def test_ambiguous_team_does_not_place_bet(self):
        self.storage.write_matches([
            sample_match(match_id="lottery_1", match_num="周五001", home_team="阿根廷", away_team="法国"),
            sample_match(match_id="lottery_2", match_num="周六002", home_team="阿根廷U21", away_team="巴西"),
        ])
        event = self._funded_event("/买球 阿根廷赢1000")
        handler = self._bet_handler()
        results = []
        async for result in handler.handle_simple_bet(event):
            results.append(result)
        self.assertIn("多场", results[0])
        self.assertEqual(len(self.storage.get_all_bets()), 0)

    async def test_llm_fallback_places_bet(self):
        self.storage.write_matches([sample_match(home_team="阿根廷", away_team="法国")])
        context = FakeContext('{"intent":"bet","team":"法国","selection":"赢","amount":"1000","match_key":"","confidence":0.95}')
        parser = NaturalBetIntentParser(context, self.lottery_service, {"enable_natural_bet_regex": False})
        handler = BetHandlers(self.lottery_service, self.engine, parser)
        event = self._funded_event("/足球投注 帮我买法国")
        results = []
        async for result in handler.handle_place_bet(event):
            results.append(result)
        bet = self.storage.get_all_bets()[0]
        self.assertIn("投注成功", results[0])
        self.assertEqual(bet.selection, "A")

    def _bet_handler(self):
        parser = NaturalBetIntentParser(FakeContext(), self.lottery_service, {})
        return BetHandlers(self.lottery_service, self.engine, parser)

    def _funded_event(self, message):
        event = FakeEvent(message_str=message)
        self.engine.checkin(event, date="2026-06-12", timestamp=1)
        return event


if __name__ == "__main__":
    unittest.main()
