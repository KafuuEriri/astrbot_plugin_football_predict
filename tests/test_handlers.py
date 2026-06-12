import unittest

from handlers.match_handlers import MatchHandlers
from services.lottery_data_service import LotteryDataService
from tests.helpers import FakeEvent, TempStorageMixin, sample_match


class HandlerTest(TempStorageMixin, unittest.IsolatedAsyncioTestCase):
    async def test_match_list_reads_cache(self):
        self.storage.write_matches([sample_match()])
        handler = MatchHandlers(LotteryDataService(self.storage, {}, spider=object()))
        event = FakeEvent(message_str="/世界杯赛事 1")
        results = []
        async for result in handler.handle_matches(event):
            results.append(result)
        self.assertEqual(len(results), 1)
        self.assertIn("周五001", results[0])


if __name__ == "__main__":
    unittest.main()
