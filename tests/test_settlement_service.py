import unittest
from decimal import Decimal

from services.betting_engine import BettingEngine
from services.settlement_service import SettlementService
from tests.helpers import FakeEvent, TempStorageMixin, sample_match


class SettlementServiceTest(TempStorageMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.engine = BettingEngine(self.storage, {"daily_checkin_amount": 20000})
        self.settlement = SettlementService(self.storage)
        self.event = FakeEvent(sender_id="u1", session_id="g1")
        self.engine.checkin(self.event, date="2026-06-12", timestamp=1)
        self.storage.write_matches([sample_match()])

    def test_manual_result_settles_wins_losses_and_is_idempotent(self):
        match = self.storage.find_match("周五001")
        win_bet = self.engine.place_bet(self.event, match, "主胜", "1000", timestamp=2)
        lose_bet = self.engine.place_bet(self.event, match, "客胜", "1000", timestamp=3)
        self.settlement.record_manual_result("周五001", "主胜", score="2-1", timestamp=4)
        summary = self.settlement.settle_pending(timestamp=5)
        self.assertEqual(summary["won"], 1)
        self.assertEqual(summary["lost"], 1)
        self.assertEqual(self.storage.get_bet(win_bet.bet_id).status, "won")
        self.assertEqual(self.storage.get_bet(lose_bet.bet_id).status, "lost")
        self.assertEqual(self.storage.get_user(win_bet.user_id).balance, Decimal("20000.00"))
        second_summary = self.settlement.settle_pending(timestamp=6)
        self.assertEqual(second_summary["settled"], 0)
        self.assertEqual(self.storage.get_user(win_bet.user_id).balance, Decimal("20000.00"))

    def test_void_result_refunds_stake(self):
        match = self.storage.find_match("周五001")
        bet = self.engine.place_bet(self.event, match, "主胜", "1000", timestamp=2)
        self.settlement.record_manual_result("周五001", "无效", timestamp=3)
        summary = self.settlement.settle_pending(timestamp=4)
        self.assertEqual(summary["void"], 1)
        self.assertEqual(self.storage.get_bet(bet.bet_id).status, "void")
        self.assertEqual(self.storage.get_user(bet.user_id).balance, Decimal("20000.00"))

    def test_cached_score_auto_settles_pending_bet(self):
        match = self.storage.find_match("周五001")
        bet = self.engine.place_bet(self.event, match, "主胜", "1000", timestamp=2)
        match.home_score = "2"
        match.away_score = "1"
        match.status = "Finished"
        self.storage.write_matches([match])
        summary = self.settlement.settle_pending(timestamp=3)
        settled_bet = self.storage.get_bet(bet.bet_id)
        self.assertEqual(summary["won"], 1)
        self.assertEqual(settled_bet.status, "won")
        self.assertEqual(settled_bet.result, "H")
        self.assertEqual(self.storage.get_user(bet.user_id).balance, Decimal("21000.00"))

    def test_hhad_settlement_uses_bet_goal_line_with_fallback_score(self):
        hhad_match = sample_match(match_id="lottery_3", match_num="周五003")
        hhad_match.pool_type = "hhad"
        hhad_match.goal_line = "-1"
        self.storage.write_matches([hhad_match])
        bet = self.engine.place_bet(self.event, hhad_match, "平", "1000", timestamp=2)
        had_score = sample_match(match_id="lottery_3", match_num="周五003")
        had_score.home_score = "2"
        had_score.away_score = "1"
        had_score.result = "H"
        had_score.status = "Finished"
        self.storage.write_matches([had_score])
        summary = self.settlement.settle_pending(timestamp=3)
        settled_bet = self.storage.get_bet(bet.bet_id)
        self.assertEqual(summary["won"], 1)
        self.assertEqual(settled_bet.status, "won")
        self.assertEqual(settled_bet.result, "D")
        self.assertEqual(self.storage.get_user(bet.user_id).balance, Decimal("22000.00"))


if __name__ == "__main__":
    unittest.main()
