import unittest
from decimal import Decimal

from models import LotteryMatch
from utils.time_utils import now_ts


class ModelsTest(unittest.TestCase):
    def test_had_result(self):
        match = LotteryMatch(match_id="m1", home_score="2", away_score="1", pool_type="had")
        self.assertEqual(match.compute_result(), "H")
        match.home_score = "1"
        match.away_score = "1"
        self.assertEqual(match.compute_result(), "D")

    def test_hhad_result_with_goal_line(self):
        match = LotteryMatch(match_id="m1", home_score="2", away_score="1", pool_type="hhad", goal_line="-1")
        self.assertEqual(match.compute_result(), "D")
        match.goal_line = "1"
        self.assertEqual(match.compute_result(), "H")

    def test_selection_odds_and_open_status(self):
        match = LotteryMatch(
            match_id="m1",
            sale_close_ts=now_ts() + 60,
            odds_h=Decimal("2.10"),
            odds_d=Decimal("3.10"),
            odds_a=Decimal("4.10"),
        )
        self.assertTrue(match.is_open_for_betting())
        self.assertEqual(match.selection_odds("A"), Decimal("4.10"))
        with self.assertRaises(ValueError):
            match.selection_odds("X")


if __name__ == "__main__":
    unittest.main()
