import csv
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from astrbot.api.star import StarTools
except Exception:
    StarTools = None

try:
    from models import BetOrder, LotteryMatch, UserAccount
    from utils.validators import money_text
except ImportError:
    from ..models import BetOrder, LotteryMatch, UserAccount
    from .validators import money_text

MATCH_FIELDS = [
    "match_id",
    "raw_match_id",
    "match_num",
    "business_date",
    "league_name",
    "home_team",
    "away_team",
    "match_date",
    "match_time",
    "kickoff_ts",
    "sale_close_ts",
    "status",
    "pool_type",
    "goal_line",
    "odds_h",
    "odds_d",
    "odds_a",
    "odds_update_time",
    "home_score",
    "away_score",
    "result",
    "source",
    "fetched_at",
    "is_world_cup",
]

ODDS_HISTORY_FIELDS = ["snapshot_id"] + MATCH_FIELDS
TRANSACTION_FIELDS = ["tx_id", "user_id", "session_id", "type", "amount", "balance_after", "related_id", "created_at", "note"]
MANUAL_RESULT_FIELDS = ["match_id", "match_num", "result", "home_score", "away_score", "entered_by", "entered_at", "note"]


class DataStorage:
    def __init__(self, plugin_name: str = "astrbot_plugin_football_predict", data_dir: Optional[Path] = None):
        self.plugin_name = plugin_name
        if data_dir is not None:
            self.data_dir = Path(data_dir)
        elif StarTools is not None:
            self.data_dir = Path(StarTools.get_data_dir(plugin_name))
        else:
            self.data_dir = Path.cwd() / "data" / plugin_name
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._ensure_files()

    def get_isolated_user_id(self, event) -> str:
        platform_name = self._call_event(event, "get_platform_name", "unknown")
        sender_id = self._call_event(event, "get_sender_id", "unknown")
        session_id = self._call_event(event, "get_session_id", "private")
        if sender_id and isinstance(session_id, str) and session_id.startswith(f"{sender_id}_"):
            session_id = session_id[len(sender_id) + 1:]
        return f"{platform_name}:{sender_id}:{session_id}"

    def get_event_context(self, event) -> Dict[str, str]:
        return {
            "user_id": self.get_isolated_user_id(event),
            "username": self._call_event(event, "get_sender_name", ""),
            "platform_name": self._call_event(event, "get_platform_name", "unknown"),
            "sender_id": self._call_event(event, "get_sender_id", "unknown"),
            "session_id": self._call_event(event, "get_session_id", "private"),
        }

    def get_user(self, user_id: str) -> Optional[UserAccount]:
        data = self._load_json("users.json")
        if user_id not in data:
            return None
        return UserAccount.from_dict(data[user_id])

    def save_user(self, user: UserAccount) -> None:
        with self._lock:
            data = self._load_json("users.json")
            data[user.user_id] = user.to_dict()
            self._save_json("users.json", data)

    def get_all_users(self) -> List[UserAccount]:
        return [UserAccount.from_dict(item) for item in self._load_json("users.json").values()]

    def get_bet(self, bet_id: str) -> Optional[BetOrder]:
        data = self._load_json("bets.json")
        if bet_id not in data:
            return None
        return BetOrder.from_dict(data[bet_id])

    def save_bet(self, bet: BetOrder) -> None:
        with self._lock:
            data = self._load_json("bets.json")
            data[bet.bet_id] = bet.to_dict()
            self._save_json("bets.json", data)

    def get_all_bets(self) -> List[BetOrder]:
        return [BetOrder.from_dict(item) for item in self._load_json("bets.json").values()]

    def get_user_bets(self, user_id: str, status: Optional[str] = None) -> List[BetOrder]:
        bets = [bet for bet in self.get_all_bets() if bet.user_id == user_id]
        if status:
            bets = [bet for bet in bets if bet.status == status]
        return sorted(bets, key=lambda bet: bet.created_at, reverse=True)

    def get_pending_bets(self) -> List[BetOrder]:
        return [bet for bet in self.get_all_bets() if bet.status == "pending"]

    def next_bet_id(self) -> str:
        return f"B{self._next_counter('bet_number'):06d}"

    def next_tx_id(self) -> str:
        return f"T{self._next_counter('tx_number'):06d}"

    def write_matches(self, matches: Iterable[LotteryMatch]) -> None:
        with self._lock:
            rows = {self._match_key(row): row for row in self.read_csv("matches.csv")}
            for match in matches:
                rows[(match.match_id, match.pool_type)] = match.to_dict()
            self._write_csv("matches.csv", MATCH_FIELDS, rows.values())

    def get_matches(self) -> List[LotteryMatch]:
        return [LotteryMatch.from_dict(row) for row in self.read_csv("matches.csv") if row.get("match_id")]

    def find_match(self, key: str) -> Optional[LotteryMatch]:
        normalized = str(key).strip()
        for match in self.get_matches():
            if match.match_id == normalized or match.match_num == normalized or match.raw_match_id == normalized:
                return match
        return None

    def append_odds_history(self, matches: Iterable[LotteryMatch]) -> None:
        rows = []
        for match in matches:
            row = match.to_dict()
            row["snapshot_id"] = f"S{self._next_counter('snapshot_number'):08d}"
            rows.append(row)
        self.append_csv("odds_history.csv", ODDS_HISTORY_FIELDS, rows)

    def append_transaction(
        self,
        user_id: str,
        session_id: str,
        tx_type: str,
        amount,
        balance_after,
        related_id: str = "",
        note: str = "",
        created_at: int = 0,
    ) -> None:
        row = {
            "tx_id": self.next_tx_id(),
            "user_id": user_id,
            "session_id": session_id,
            "type": tx_type,
            "amount": money_text(amount),
            "balance_after": money_text(balance_after),
            "related_id": related_id,
            "created_at": str(created_at),
            "note": note,
        }
        self.append_csv("transactions.csv", TRANSACTION_FIELDS, [row])

    def save_fetch_state(self, state: Dict[str, Any]) -> None:
        self._save_json("fetch_state.json", state)

    def get_fetch_state(self) -> Dict[str, Any]:
        return self._load_json("fetch_state.json")

    def save_manual_result(self, row: Dict[str, Any]) -> None:
        self.append_csv("manual_results.csv", MANUAL_RESULT_FIELDS, [row])

    def get_manual_results(self) -> List[Dict[str, str]]:
        return self.read_csv("manual_results.csv")

    def read_csv(self, filename: str) -> List[Dict[str, str]]:
        path = self._path(filename)
        if not path.exists():
            return []
        with self._lock:
            with path.open("r", encoding="utf-8", newline="") as handle:
                return list(csv.DictReader(handle))

    def append_csv(self, filename: str, fieldnames: List[str], rows: Iterable[Dict[str, Any]]) -> None:
        with self._lock:
            path = self._path(filename)
            exists = path.exists() and path.stat().st_size > 0
            with path.open("a", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                if not exists:
                    writer.writeheader()
                for row in rows:
                    writer.writerow({field: row.get(field, "") for field in fieldnames})

    def _ensure_files(self) -> None:
        defaults = {
            "users.json": {},
            "bets.json": {},
            "counters.json": {"bet_number": 0, "tx_number": 0, "snapshot_number": 0},
            "fetch_state.json": {},
        }
        for filename, default in defaults.items():
            path = self._path(filename)
            if not path.exists():
                self._save_json(filename, default)

        csv_defaults = {
            "matches.csv": MATCH_FIELDS,
            "odds_history.csv": ODDS_HISTORY_FIELDS,
            "transactions.csv": TRANSACTION_FIELDS,
            "manual_results.csv": MANUAL_RESULT_FIELDS,
        }
        for filename, fields in csv_defaults.items():
            path = self._path(filename)
            if not path.exists():
                self._write_csv(filename, fields, [])

    def _next_counter(self, name: str) -> int:
        with self._lock:
            counters = self._load_json("counters.json")
            counters[name] = int(counters.get(name, 0)) + 1
            self._save_json("counters.json", counters)
            return counters[name]

    def _load_json(self, filename: str) -> Dict[str, Any]:
        path = self._path(filename)
        if not path.exists():
            return {}
        with self._lock:
            with path.open("r", encoding="utf-8") as handle:
                try:
                    return json.load(handle)
                except json.JSONDecodeError:
                    return {}

    def _save_json(self, filename: str, data: Dict[str, Any]) -> None:
        text = json.dumps(data, ensure_ascii=False, indent=2)
        self._write_text_atomic(filename, text)

    def _write_csv(self, filename: str, fieldnames: List[str], rows: Iterable[Dict[str, Any]]) -> None:
        temp_path = self._path(filename).with_suffix(self._path(filename).suffix + ".tmp")
        with self._lock:
            with temp_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for row in rows:
                    writer.writerow({field: row.get(field, "") for field in fieldnames})
            os.replace(temp_path, self._path(filename))

    def _write_text_atomic(self, filename: str, text: str) -> None:
        path = self._path(filename)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with self._lock:
            temp_path.write_text(text, encoding="utf-8")
            os.replace(temp_path, path)

    def _path(self, filename: str) -> Path:
        return self.data_dir / filename

    def _match_key(self, row: Dict[str, Any]) -> Tuple[str, str]:
        return str(row.get("match_id", "")), str(row.get("pool_type", ""))

    def _call_event(self, event, method: str, default: str) -> str:
        func = getattr(event, method, None)
        if callable(func):
            value = func()
            return str(value) if value is not None else default
        return default
