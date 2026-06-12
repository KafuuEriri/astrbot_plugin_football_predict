import unittest

from china_lottery_spider import ChinaLotterySpider


class SpiderParserTest(unittest.TestCase):
    def test_parse_prefers_had_and_exposes_normalized_odds(self):
        had_data = {
            "value": {"matchInfoList": [{"businessDate": "2026-06-12", "subMatchList": [{
                "matchId": "1001",
                "had": {"h": "1.80", "d": "3.20", "a": "4.00", "updateDate": "2026-06-12", "updateTime": "10:00:00"},
            }]}]}
        }
        hhad_data = {
            "value": {"matchInfoList": [{"businessDate": "2026-06-12", "subMatchList": [{
                "matchId": "1001",
                "homeTeamAllName": "主队",
                "awayTeamAllName": "客队",
                "leagueAbbName": "世界杯",
                "matchDate": "2026-06-13",
                "matchTime": "20:00:00",
                "matchNumStr": "周五001",
                "matchStatus": "Selling",
                "hhad": {"h": "2.10", "d": "3.30", "a": "2.90", "goalLine": "-1"},
            }]}]}
        }
        matches = ChinaLotterySpider().parse_match_data_with_odds_priority(had_data, hhad_data)
        self.assertEqual(len(matches), 1)
        odds = matches[0]["odds"]
        self.assertEqual(odds["pool_type"], "had")
        self.assertEqual(odds["odds_h"], "1.80")
        self.assertEqual(matches[0]["raw_match_id"], "1001")

    def test_extract_hhad_fallback(self):
        match_data = {"hhad": {"h": "2.10", "d": "3.30", "a": "2.90", "goalLine": "-1"}}
        odds = ChinaLotterySpider().extract_odds(match_data)
        self.assertEqual(odds["pool_type"], "hhad")
        self.assertEqual(odds["goal_line"], "-1")


if __name__ == "__main__":
    unittest.main()
