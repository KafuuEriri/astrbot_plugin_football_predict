import unittest

from services.lottery_data_service import LotteryDataService
from services.natural_bet_intent import NaturalBetIntentParser
from tests.helpers import FakeContext, FakeEvent, TempStorageMixin, sample_match


class NaturalBetIntentParserTest(TempStorageMixin, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.storage.write_matches([sample_match(home_team="阿根廷", away_team="法国")])
        self.lottery_service = LotteryDataService(self.storage, {}, spider=object())
        self.event = FakeEvent()

    async def test_regex_parses_team_selection_and_amount(self):
        parser = NaturalBetIntentParser(None, self.lottery_service, {})
        intent = await parser.parse(self.event, "买阿根廷赢1000")
        self.assertEqual(intent.team_text, "阿根廷")
        self.assertEqual(intent.selection_text, "赢")
        self.assertEqual(intent.amount_text, "1000")
        self.assertEqual(intent.source, "regex")

    async def test_regex_parses_draw_with_space(self):
        parser = NaturalBetIntentParser(None, self.lottery_service, {})
        intent = await parser.parse(self.event, "押法国平 500")
        self.assertEqual(intent.team_text, "法国")
        self.assertEqual(intent.selection_text, "平")
        self.assertEqual(intent.amount_text, "500")

    async def test_llm_json_success(self):
        context = FakeContext('{"intent":"bet","team":"法国","selection":"赢","amount":"800","match_key":"","confidence":0.95}')
        parser = NaturalBetIntentParser(context, self.lottery_service, {"enable_natural_bet_regex": False})
        intent = await parser.parse(self.event, "帮我买法国")
        self.assertEqual(intent.team_text, "法国")
        self.assertEqual(intent.selection_text, "赢")
        self.assertEqual(intent.amount_text, "800")
        self.assertEqual(intent.source, "llm")
        self.assertTrue(context.prompts)

    async def test_llm_invalid_json_returns_none(self):
        context = FakeContext("不是JSON")
        parser = NaturalBetIntentParser(context, self.lottery_service, {"enable_natural_bet_regex": False})
        self.assertIsNone(await parser.parse(self.event, "帮我买法国"))

    async def test_llm_low_confidence_returns_none(self):
        context = FakeContext('{"intent":"bet","team":"法国","selection":"赢","amount":"800","match_key":"","confidence":0.2}')
        parser = NaturalBetIntentParser(context, self.lottery_service, {"enable_natural_bet_regex": False})
        self.assertIsNone(await parser.parse(self.event, "帮我买法国"))

    async def test_llm_unavailable_returns_none(self):
        context = FakeContext(error=RuntimeError("no provider"))
        parser = NaturalBetIntentParser(context, self.lottery_service, {"enable_natural_bet_regex": False})
        self.assertIsNone(await parser.parse(self.event, "帮我买法国"))


if __name__ == "__main__":
    unittest.main()
