import json
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class NaturalBetIntent:
    team_text: str = ""
    match_key: str = ""
    selection_text: str = ""
    amount_text: str = ""
    source: str = ""
    confidence: float = 0.0


class NaturalBetIntentParser:
    def __init__(self, context, lottery_service, config=None, logger=None):
        self.context = context
        self.lottery_service = lottery_service
        self.config = config or {}
        self.logger = logger

    async def parse(self, event, text: str) -> Optional[NaturalBetIntent]:
        normalized = str(text or "").strip()
        if not normalized:
            return None
        if self._config_bool("enable_natural_bet_regex", True):
            intent = self._parse_with_regex(normalized)
            if intent:
                return intent
        if self._config_bool("enable_ai_bet_parser", True):
            return await self._parse_with_llm(event, normalized)
        return None

    def _parse_with_regex(self, text: str) -> Optional[NaturalBetIntent]:
        match = re.match(
            r"^(?:买|押|投|下注)?\s*(?P<team>.+?)\s*"
            r"(?P<selection>主胜|客胜|平局|客负|赢|胜|输|负|平)\s*"
            r"(?P<amount>\d+(?:\.\d+)?)\s*(?:元|块|金币|虚拟币)?$",
            text,
        )
        if not match:
            return None
        return NaturalBetIntent(
            team_text=match.group("team").strip(),
            selection_text=match.group("selection").strip(),
            amount_text=match.group("amount").strip(),
            source="regex",
            confidence=1.0,
        )

    async def _parse_with_llm(self, event, text: str) -> Optional[NaturalBetIntent]:
        if not self.context:
            return None
        try:
            provider_id = await self.context.get_current_chat_provider_id(umo=getattr(event, "unified_msg_origin", ""))
            if not provider_id:
                return None
            response = await self.context.llm_generate(chat_provider_id=provider_id, prompt=self._build_prompt(text))
            data = self._load_json(getattr(response, "completion_text", ""))
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"自然语言投注模型解析失败: {exc}")
            return None

        if not data or str(data.get("intent", "")).lower() not in ("bet", "投注"):
            return None
        confidence = self._float_value(data.get("confidence"), 0.0)
        if confidence < self._config_float("natural_bet_min_confidence", 0.7):
            return None
        selection = str(data.get("selection", "")).strip()
        amount = str(data.get("amount", "")).strip()
        team = str(data.get("team", "")).strip()
        match_key = str(data.get("match_key", "")).strip()
        if not selection or not amount or not (team or match_key):
            return None
        return NaturalBetIntent(
            team_text=team,
            match_key=match_key,
            selection_text=selection,
            amount_text=amount,
            source="llm",
            confidence=confidence,
        )

    def _build_prompt(self, text: str) -> str:
        max_matches = self._config_int("natural_bet_llm_max_matches", 10)
        candidates = self.lottery_service.get_natural_bet_candidates(max_count=max_matches)
        lines = []
        for match in candidates:
            lines.append(
                f"- match_key: {match.match_num or match.match_id}; match_id: {match.match_id}; "
                f"home: {match.home_team}; away: {match.away_team}; time: {match.match_time}; "
                f"pool: {match.pool_type}; goal_line: {match.goal_line}"
            )
        candidate_text = "\n".join(lines) if lines else "无可用候选赛事"
        return (
            "你是足球模拟投注意图解析器。只输出JSON，不要输出解释。\n"
            "用户文本可能是在表达投注。只能基于候选赛事解析，不能编造比赛、球队、金额或赔率。\n"
            "selection 可输出：主胜、客胜、平、赢、胜、输、负、H、D、A。\n"
            "如果不是投注意图，输出 {\"intent\":\"none\",\"confidence\":0}。\n"
            "投注意图JSON格式："
            "{\"intent\":\"bet\",\"team\":\"球队名\",\"selection\":\"赢/平/负/主胜/客胜\","
            "\"amount\":\"数字金额\",\"match_key\":\"候选中的match_key或空\",\"confidence\":0.0到1.0}\n"
            f"候选赛事：\n{candidate_text}\n"
            f"用户文本：{text}"
        )

    def _load_json(self, text: str):
        content = str(text or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end < start:
            return None
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            return None

    def _config_bool(self, key: str, default: bool) -> bool:
        value = self.config.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")

    def _config_int(self, key: str, default: int) -> int:
        try:
            return int(self.config.get(key, default))
        except (TypeError, ValueError):
            return default

    def _config_float(self, key: str, default: float) -> float:
        try:
            return float(self.config.get(key, default))
        except (TypeError, ValueError):
            return default

    def _float_value(self, value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
