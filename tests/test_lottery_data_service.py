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


class LotteryDataServiceTest(TempStorageMixin, unittest.IsolatedAsyncioTestCase):
    async def test_fetch_and_cache_writes_matches_and_history(self):
        service = LotteryDataService(self.storage, {"days_ahead": 7}, spider=FakeSpider())
        matches = await service.fetch_and_cache()
        self.assertEqual(len(matches), 1)
        cached = self.storage.get_matches()
        self.assertEqual(cached[0].match_num, "周五001")
        self.assertEqual(len(self.storage.read_csv("odds_history.csv")), 1)
        self.assertTrue(cached[0].is_world_cup)


if __name__ == "__main__":
    unittest.main()
