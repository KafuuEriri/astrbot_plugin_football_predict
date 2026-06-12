import unittest

from services.lottery_data_service import LotteryDataService
from tests.helpers import TempStorageMixin


class FakeSpider:
    def get_formatted_matches(self, days_ahead=7):
        return [{
            "match_id": "lottery_1",
            "raw_match_id": "1",
            "match_num": "周五001",
            "business_date": "2026-06-12",
            "league_name": "世界杯",
            "home_team": "主队",
            "away_team": "客队",
            "match_date": "2026-06-13",
            "match_time": "2026-06-13 20:00:00",
            "status": "Selling",
            "source": "china_lottery",
            "odds": {"pool_type": "had", "odds_h": "2.00", "odds_d": "3.00", "odds_a": "4.00", "update_time": "2026-06-12 10:00:00"},
        }]


class TrackingSpider:
    def __init__(self):
        self.called_with = None

    def get_formatted_matches(self, days_ahead=7, result_lookback_days=0):
        self.called_with = (days_ahead, result_lookback_days)
        return [{
            "match_id": "lottery_2",
            "raw_match_id": "2",
            "match_num": "周六002",
            "business_date": "2026-06-12",
            "league_name": "世界杯",
            "home_team": "主队",
            "away_team": "客队",
            "match_date": "2026-06-12",
            "match_time": "2026-06-12 20:00:00",
            "status": "Finished",
            "home_score": "2",
            "away_score": "1",
            "result": "H",
            "source": "china_lottery",
            "odds": {"pool_type": "had", "odds_h": "2.00", "odds_d": "3.00", "odds_a": "4.00"},
        }]


class LotteryDataServiceTest(TempStorageMixin, unittest.IsolatedAsyncioTestCase):
    async def test_fetch_and_cache_writes_matches_and_history(self):
        service = LotteryDataService(self.storage, {"days_ahead": 7}, spider=FakeSpider())
        matches = await service.fetch_and_cache()
        self.assertEqual(len(matches), 1)
        cached = self.storage.get_matches()
        self.assertEqual(cached[0].match_num, "周五001")
        self.assertEqual(len(self.storage.read_csv("odds_history.csv")), 1)
        self.assertTrue(cached[0].is_world_cup)

    async def test_fetch_passes_result_lookback_and_caches_scores(self):
        spider = TrackingSpider()
        service = LotteryDataService(self.storage, {"days_ahead": 5, "result_lookback_days": 2}, spider=spider)
        await service.fetch_and_cache()
        cached = self.storage.find_match("周六002")
        self.assertEqual(spider.called_with, (5, 2))
        self.assertEqual(cached.home_score, "2")
        self.assertEqual(cached.away_score, "1")
        self.assertEqual(cached.result, "H")

    async def test_get_cached_matches_filters_max_days_ahead(self):
        from tests.helpers import sample_match

        near = sample_match(match_id="lottery_3", match_num="周五003", kickoff_offset=3600)
        far = sample_match(match_id="lottery_4", match_num="周一004", kickoff_offset=3 * 86400)
        self.storage.write_matches([near, far])
        service = LotteryDataService(self.storage, {}, spider=object())
        matches = service.get_cached_matches(world_cup_only=True, open_only=True, max_days_ahead=2)
        self.assertEqual([match.match_num for match in matches], ["周五003"])

    async def test_find_open_matches_by_team_matches_home_and_away(self):
        from tests.helpers import sample_match

        match = sample_match(match_id="lottery_5", match_num="周五005", home_team="阿根廷", away_team="法国")
        self.storage.write_matches([match])
        service = LotteryDataService(self.storage, {}, spider=object())
        self.assertEqual(service.find_open_matches_by_team("阿根廷")[0].match_num, "周五005")
        self.assertEqual(service.find_open_matches_by_team("法国")[0].match_num, "周五005")


if __name__ == "__main__":
    unittest.main()
