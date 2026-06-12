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


if __name__ == "__main__":
    unittest.main()
