import tempfile
from pathlib import Path
from decimal import Decimal

from models import LotteryMatch
from utils.storage import DataStorage
from utils.time_utils import now_ts


class FakeEvent:
    def __init__(self, message_str="", sender_id="u1", session_id="g1", username="Alice", platform="test"):
        self.message_str = message_str
        self._sender_id = sender_id
        self._session_id = session_id
        self._username = username
        self._platform = platform
        self.unified_msg_origin = f"{platform}:{session_id}"
        self.results = []

    def get_platform_name(self):
        return self._platform

    def get_sender_id(self):
        return self._sender_id

    def get_session_id(self):
        return self._session_id

    def get_sender_name(self):
        return self._username

    def plain_result(self, text):
        self.results.append(text)
        return text


class TempStorageMixin:
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.storage = DataStorage(data_dir=Path(self._tmpdir.name))

    def tearDown(self):
        self._tmpdir.cleanup()


class FakeLLMResponse:
    def __init__(self, completion_text=""):
        self.completion_text = completion_text


class FakeContext:
    def __init__(self, completion_text="", provider_id="fake-provider", error=None):
        self.completion_text = completion_text
        self.provider_id = provider_id
        self.error = error
        self.prompts = []

    async def get_current_chat_provider_id(self, umo=""):
        if self.error:
            raise self.error
        return self.provider_id

    async def llm_generate(self, chat_provider_id=None, prompt="", contexts=None):
        if self.error:
            raise self.error
        self.prompts.append(prompt)
        return FakeLLMResponse(self.completion_text)


def sample_match(
    match_id="lottery_1",
    match_num="周五001",
    sale_close=None,
    result="",
    home_team="主队",
    away_team="客队",
    kickoff_offset=7200,
):
    ts = now_ts()
    return LotteryMatch(
        match_id=match_id,
        raw_match_id=match_id.replace("lottery_", ""),
        match_num=match_num,
        league_name="世界杯",
        home_team=home_team,
        away_team=away_team,
        match_date="2026-06-13",
        match_time="2026-06-13 20:00:00",
        kickoff_ts=ts + kickoff_offset,
        sale_close_ts=sale_close if sale_close is not None else ts + 3600,
        pool_type="had",
        odds_h=Decimal("2.00"),
        odds_d=Decimal("3.00"),
        odds_a=Decimal("4.00"),
        result=result,
        fetched_at=ts,
        is_world_cup=True,
    )
