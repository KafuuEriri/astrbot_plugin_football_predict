#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""足球胜平负爬虫。"""

import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class ChinaLotterySpider:
    """足球胜平负数据获取器。"""

    def __init__(
        self,
        timeout: int = 15,
        max_retries: int = 3,
        logger_instance: Optional[logging.Logger] = None,
    ):
        self.base_url = "https://webapi.sporttery.cn"
        self.api_endpoint = "/gateway/uniform/football/getMatchCalculatorV1.qry"
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logger_instance or logger
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.lottery.gov.cn/",
            "Origin": "https://www.lottery.gov.cn",
        }
        self.session = requests.Session() if requests is not None else None
        if self.session is not None:
            self.session.headers.update(self.headers)

    def fetch_lottery_data(self, pool_code: str = "hhad", channel: str = "c") -> Optional[Dict[str, Any]]:
        if requests is None or self.session is None:
            raise Exception("缺少 requests 依赖，请先安装 requirements.txt")
        url = f"{self.base_url}{self.api_endpoint}"
        params = {"poolCode": pool_code, "channel": channel}

        for attempt in range(self.max_retries):
            try:
                self.logger.info("正在获取体彩数据 (%s/%s): %s", attempt + 1, self.max_retries, url)
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                if data.get("success"):
                    self.logger.info("成功获取体彩API数据: %s", data.get("errorMessage", "处理成功"))
                    return data

                error_msg = data.get("errorMessage", "未知错误")
                self.logger.warning("体彩API返回错误: %s", error_msg)
                if attempt == self.max_retries - 1:
                    raise Exception(f"API调用失败: {error_msg}")

            except requests.exceptions.RequestException as exc:
                self.logger.warning("网络请求失败 (%s/%s): %s", attempt + 1, self.max_retries, exc)
                if attempt < self.max_retries - 1:
                    time.sleep(random.uniform(1, 3))
                else:
                    raise Exception(f"网络请求失败: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise Exception(f"响应数据格式错误: {exc}") from exc

        return None

    def parse_match_data(self, api_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        matches = []
        value = api_data.get("value", {})
        match_info_list = value.get("matchInfoList", [])

        if not match_info_list:
            self.logger.warning("API返回的数据中没有比赛信息")
            return matches

        for date_info in match_info_list:
            business_date = date_info.get("businessDate", "")
            for match_data in date_info.get("subMatchList", []):
                match_info = self._build_match_info(match_data, business_date)
                odds_info = self.extract_odds(match_data)
                if not odds_info:
                    continue
                match_info["odds"] = odds_info
                if self.validate_match(match_info):
                    matches.append(match_info)

        self.logger.info("成功解析 %s 场有效比赛", len(matches))
        return matches

    def extract_odds(self, match_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        had_data = match_data.get("had")
        if had_data:
            odds = self._build_odds("had", had_data)
            if odds:
                return odds

        for odds_item in match_data.get("oddsList") or []:
            if str(odds_item.get("poolCode", "")).upper() == "HAD":
                odds = self._build_odds("had", odds_item)
                if odds:
                    return odds

        hhad_data = match_data.get("hhad")
        if hhad_data:
            odds = self._build_odds("hhad", hhad_data)
            if odds:
                return odds

        for odds_item in match_data.get("oddsList") or []:
            if str(odds_item.get("poolCode", "")).upper() == "HHAD":
                odds = self._build_odds("hhad", odds_item)
                if odds:
                    return odds

        return None

    def clean_team_name(self, team_name: str) -> str:
        if not team_name:
            return ""
        import re

        cleaned = team_name.strip()
        cleaned = re.sub(r"\[.*?\]", "", cleaned)
        cleaned = re.sub(r"\(.*?\)", "", cleaned)
        return cleaned.strip()

    def validate_match(self, match: Dict[str, Any]) -> bool:
        for field in ["match_id", "home_team", "away_team", "league_name", "odds"]:
            if not match.get(field):
                return False

        odds = match.get("odds", {})
        odds_values = [odds.get("odds_h"), odds.get("odds_d"), odds.get("odds_a")]
        if not all(odds_values):
            hhad = odds.get("hhad", {})
            odds_values = [hhad.get("h"), hhad.get("d"), hhad.get("a")]

        if not all(odds_values):
            return False

        try:
            for odds_value in odds_values:
                float_val = float(odds_value)
                if float_val < 1.01 or float_val > 99.99:
                    return False
        except (ValueError, TypeError):
            return False

        return True

    def filter_matches_by_date(
        self,
        matches: List[Dict[str, Any]],
        days_ahead: int = 3,
        lookback_days: int = 0,
    ) -> List[Dict[str, Any]]:
        if not matches:
            return []

        current_date = datetime.now().date()
        start_date = current_date - timedelta(days=max(0, lookback_days))
        end_date = current_date + timedelta(days=days_ahead)
        filtered_matches = []

        for match in matches:
            match_date_str = match.get("match_date", "")
            if not match_date_str:
                continue
            try:
                match_date = datetime.strptime(match_date_str, "%Y-%m-%d").date()
            except ValueError:
                self.logger.warning("日期格式错误: %s", match_date_str)
                continue
            if start_date <= match_date <= end_date:
                filtered_matches.append(match)

        self.logger.info("日期过滤: %s -> %s 场比赛", len(matches), len(filtered_matches))
        return filtered_matches

    def get_formatted_matches(self, days_ahead: int = 3, result_lookback_days: int = 0) -> List[Dict[str, Any]]:
        had_data = None
        hhad_data = None

        try:
            had_data = self.fetch_lottery_data(pool_code="had")
        except Exception as exc:
            self.logger.warning("获取HAD数据失败: %s", exc)

        try:
            hhad_data = self.fetch_lottery_data(pool_code="hhad")
        except Exception as exc:
            self.logger.warning("获取HHAD数据失败: %s", exc)

        if not had_data and not hhad_data:
            raise Exception("无法获取任何API数据")

        if hhad_data:
            matches = self.parse_match_data_with_odds_priority(had_data, hhad_data)
        else:
            matches = self.parse_match_data(had_data or {})

        filtered_matches = self.filter_matches_by_date(matches, days_ahead, result_lookback_days)
        if not filtered_matches:
            raise Exception(f"近{result_lookback_days}天到未来{days_ahead}天内没有可用的比赛")

        had_count = sum(1 for match in filtered_matches if match.get("odds", {}).get("pool_type") == "had")
        hhad_count = sum(1 for match in filtered_matches if match.get("odds", {}).get("pool_type") == "hhad")
        self.logger.info("赔率统计: 不让球%s场, 让球%s场", had_count, hhad_count)
        return filtered_matches

    def parse_match_data_with_odds_priority(
        self,
        had_data: Optional[Dict[str, Any]],
        hhad_data: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        matches = []
        had_odds_map = self._build_had_odds_map(had_data)
        source_data = hhad_data or had_data or {}
        match_info_list = source_data.get("value", {}).get("matchInfoList", [])

        for date_info in match_info_list:
            business_date = date_info.get("businessDate", "")
            for match_data in date_info.get("subMatchList", []):
                match_id = str(match_data.get("matchId", ""))
                match_info = self._build_match_info(match_data, business_date)
                odds_info = had_odds_map.get(match_id) or self.extract_odds(match_data)
                if not odds_info:
                    continue
                match_info["odds"] = odds_info
                if self.validate_match(match_info):
                    matches.append(match_info)

        self.logger.info("成功解析 %s 场有效比赛", len(matches))
        return matches

    def _build_had_odds_map(self, had_data: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        odds_map = {}
        if not had_data:
            return odds_map

        for date_info in had_data.get("value", {}).get("matchInfoList", []):
            for match_data in date_info.get("subMatchList", []):
                match_id = str(match_data.get("matchId", ""))
                odds = self._build_odds("had", match_data.get("had") or {})
                if match_id and odds:
                    odds_map[match_id] = odds
        return odds_map

    def _build_match_info(self, match_data: Dict[str, Any], business_date: str = "") -> Dict[str, Any]:
        raw_match_id = str(match_data.get("matchId", ""))
        match_date = match_data.get("matchDate", "")
        match_time = match_data.get("matchTime", "")
        return {
            "match_id": f"lottery_{raw_match_id}",
            "raw_match_id": raw_match_id,
            "business_date": business_date,
            "home_team": self.clean_team_name(match_data.get("homeTeamAllName", match_data.get("homeTeamAbbName", ""))),
            "away_team": self.clean_team_name(match_data.get("awayTeamAllName", match_data.get("awayTeamAbbName", ""))),
            "league_name": match_data.get("leagueAbbName", match_data.get("leagueAllName", "")),
            "match_time": f"{match_date} {match_time}".strip(),
            "match_date": match_date,
            "match_num": match_data.get("matchNumStr", ""),
            "status": match_data.get("matchStatus", "Unknown"),
            "home_score": self._first_value(match_data, ["homeScore", "homeTeamScore", "hScore"]),
            "away_score": self._first_value(match_data, ["awayScore", "awayTeamScore", "aScore"]),
            "result": self._first_value(match_data, ["result", "matchResult", "winningResult"]),
            "source": "china_lottery",
        }

    def _build_odds(self, pool_type: str, odds_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not odds_data or not all(key in odds_data for key in ["h", "d", "a"]):
            return None

        odds_h = str(odds_data.get("h", "")).strip()
        odds_d = str(odds_data.get("d", "")).strip()
        odds_a = str(odds_data.get("a", "")).strip()
        if not odds_h or not odds_d or not odds_a:
            return None

        return {
            "pool_type": pool_type,
            "type": pool_type,
            "odds_h": odds_h,
            "odds_d": odds_d,
            "odds_a": odds_a,
            "hhad": {"h": odds_h, "d": odds_d, "a": odds_a},
            "goal_line": str(odds_data.get("goalLine", "") or ""),
            "update_time": f"{odds_data.get('updateDate', '')} {odds_data.get('updateTime', '')}".strip(),
        }

    def _first_value(self, data: Dict[str, Any], keys: List[str]) -> str:
        for key in keys:
            value = data.get(key)
            if value not in (None, ""):
                return str(value)
        return ""


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    spider = ChinaLotterySpider()

    try:
        print("测试爬虫...")
        matches = spider.get_formatted_matches(days_ahead=7)
        print(f"\n成功获取 {len(matches)} 场比赛")

        for index, match in enumerate(matches[:3]):
            odds = match["odds"]
            type_label = "不让球" if odds.get("pool_type") == "had" else "让球"
            print(f"\n比赛 {index + 1}:")
            print(f"  {match['match_num']}: {match['home_team']} vs {match['away_team']}")
            print(f"  联赛: {match['league_name']}")
            print(f"  时间: {match['match_time']}")
            print(f"  赔率({type_label}): 主胜{odds['odds_h']} 平局{odds['odds_d']} 客胜{odds['odds_a']}")
    except Exception as exc:
        print(f"测试失败: {exc}")


if __name__ == "__main__":
    main()
