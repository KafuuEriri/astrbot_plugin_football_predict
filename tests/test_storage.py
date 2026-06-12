import unittest
from decimal import Decimal

from models import BetOrder, UserAccount
from tests.helpers import TempStorageMixin, sample_match


class StorageTest(TempStorageMixin, unittest.TestCase):
    def test_write_and_find_matches(self):
        match = sample_match()
        self.storage.write_matches([match])
        found = self.storage.find_match("周五001")
        self.assertIsNotNone(found)
        self.assertEqual(found.match_id, match.match_id)

    def test_preserves_existing_matches_when_writing_new(self):
        first = sample_match(match_id="lottery_1", match_num="周五001")
        second = sample_match(match_id="lottery_2", match_num="周五002")
        self.storage.write_matches([first])
        self.storage.write_matches([second])
        self.assertEqual(len(self.storage.get_matches()), 2)

    def test_preserves_existing_result_when_refresh_has_blank_result(self):
        finished = sample_match(match_id="lottery_1", match_num="周五001")
        finished.home_score = "2"
        finished.away_score = "1"
        finished.result = "H"
        finished.status = "Finished"
        refreshed = sample_match(match_id="lottery_1", match_num="周五001")
        self.storage.write_matches([finished])
        self.storage.write_matches([refreshed])
        found = self.storage.find_match("周五001")
        self.assertEqual(found.home_score, "2")
        self.assertEqual(found.away_score, "1")
        self.assertEqual(found.result, "H")
        self.assertEqual(found.status, "Finished")

    def test_updates_existing_result_when_refresh_has_new_result(self):
        old = sample_match(match_id="lottery_1", match_num="周五001")
        old.home_score = "2"
        old.away_score = "1"
        old.result = "H"
        new = sample_match(match_id="lottery_1", match_num="周五001")
        new.home_score = "1"
        new.away_score = "1"
        new.result = "D"
        self.storage.write_matches([old])
        self.storage.write_matches([new])
        found = self.storage.find_match("周五001")
        self.assertEqual(found.home_score, "1")
        self.assertEqual(found.away_score, "1")
        self.assertEqual(found.result, "D")

    def test_user_bet_and_history_storage(self):
        user = UserAccount(user_id="test:u1:g1", session_id="g1", balance=Decimal("1000"))
        self.storage.save_user(user)
        bet = BetOrder(
            bet_id="B000001",
            user_id=user.user_id,
            username="Alice",
            session_id="g1",
            match_id="lottery_1",
            match_num="周五001",
            league_name="世界杯",
            home_team="主队",
            away_team="客队",
            match_time="2026-06-13 20:00:00",
            pool_type="had",
            selection="H",
            selection_text="主胜",
            odds_locked=Decimal("2.00"),
            stake=Decimal("100"),
            potential_payout=Decimal("200"),
            created_at=1,
            updated_at=1,
        )
        self.storage.save_bet(bet)
        self.assertEqual(self.storage.get_user(user.user_id).balance, Decimal("1000.00"))
        self.assertEqual(len(self.storage.get_user_bets(user.user_id)), 1)


if __name__ == "__main__":
    unittest.main()
