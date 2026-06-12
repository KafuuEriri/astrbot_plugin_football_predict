import unittest
from decimal import Decimal

from services.betting_engine import BettingEngine
from tests.helpers import FakeEvent, TempStorageMixin, sample_match


class BettingEngineTest(TempStorageMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.engine = BettingEngine(self.storage, {"daily_checkin_amount": 20000, "min_bet_amount": 100, "max_bet_amount": 100000})
        self.event = FakeEvent(message_str="/足球签到")
        self.storage.write_matches([sample_match()])

    def test_daily_checkin_once_per_day(self):
        created, user, amount = self.engine.checkin(self.event, date="2026-06-12", timestamp=1)
        self.assertTrue(created)
        self.assertEqual(amount, Decimal("20000.00"))
        created, user, amount = self.engine.checkin(self.event, date="2026-06-12", timestamp=2)
        self.assertFalse(created)
        self.assertEqual(amount, Decimal("0"))
        self.assertEqual(user.balance, Decimal("20000.00"))

    def test_group_isolation(self):
        self.engine.checkin(FakeEvent(sender_id="u1", session_id="g1"), date="2026-06-12")
        self.engine.checkin(FakeEvent(sender_id="u1", session_id="g2"), date="2026-06-12")
        self.assertEqual(len(self.storage.get_all_users()), 2)

    def test_place_and_cancel_bet(self):
        self.engine.checkin(self.event, date="2026-06-12", timestamp=1)
        match = self.storage.find_match("周五001")
        bet = self.engine.place_bet(FakeEvent(message_str="/足球投注 周五001 主胜 1000"), match, "主胜", "1000", timestamp=2)
        user = self.storage.get_user(bet.user_id)
        self.assertEqual(user.balance, Decimal("19000.00"))
        self.assertEqual(bet.potential_payout, Decimal("2000.00"))
        cancelled = self.engine.cancel_bet(FakeEvent(message_str="/足球撤单 B000001"), bet.bet_id, match=match, timestamp=3)
        user = self.storage.get_user(bet.user_id)
        self.assertEqual(cancelled.status, "cancelled")
        self.assertEqual(user.balance, Decimal("20000.00"))

    def test_rejects_insufficient_balance(self):
        match = self.storage.find_match("周五001")
        with self.assertRaises(ValueError):
            self.engine.place_bet(self.event, match, "主胜", "1000")


if __name__ == "__main__":
    unittest.main()
