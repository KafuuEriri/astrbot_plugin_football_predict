from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict

try:
    from utils.validators import money_text
except ImportError:
    from ..utils.validators import money_text


@dataclass
class UserAccount:
    user_id: str
    username: str = ""
    platform_name: str = ""
    sender_id: str = ""
    session_id: str = ""
    balance: Decimal = Decimal("0")
    total_checkin_amount: Decimal = Decimal("0")
    last_checkin_date: str = ""
    checkin_count: int = 0
    total_staked: Decimal = Decimal("0")
    total_payout: Decimal = Decimal("0")
    wins: int = 0
    losses: int = 0
    voids: int = 0
    cancelled: int = 0
    created_at: int = 0
    updated_at: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserAccount":
        return cls(
            user_id=str(data.get("user_id", "")),
            username=str(data.get("username", "")),
            platform_name=str(data.get("platform_name", "")),
            sender_id=str(data.get("sender_id", "")),
            session_id=str(data.get("session_id", "")),
            balance=Decimal(str(data.get("balance") or "0")),
            total_checkin_amount=Decimal(str(data.get("total_checkin_amount") or "0")),
            last_checkin_date=str(data.get("last_checkin_date", "")),
            checkin_count=int(data.get("checkin_count") or 0),
            total_staked=Decimal(str(data.get("total_staked") or "0")),
            total_payout=Decimal(str(data.get("total_payout") or "0")),
            wins=int(data.get("wins") or 0),
            losses=int(data.get("losses") or 0),
            voids=int(data.get("voids") or 0),
            cancelled=int(data.get("cancelled") or 0),
            created_at=int(data.get("created_at") or 0),
            updated_at=int(data.get("updated_at") or 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "platform_name": self.platform_name,
            "sender_id": self.sender_id,
            "session_id": self.session_id,
            "balance": money_text(self.balance),
            "total_checkin_amount": money_text(self.total_checkin_amount),
            "last_checkin_date": self.last_checkin_date,
            "checkin_count": self.checkin_count,
            "total_staked": money_text(self.total_staked),
            "total_payout": money_text(self.total_payout),
            "wins": self.wins,
            "losses": self.losses,
            "voids": self.voids,
            "cancelled": self.cancelled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def can_afford(self, amount: Decimal) -> bool:
        return self.balance >= amount

    def add_balance(self, amount: Decimal) -> None:
        self.balance += amount

    def deduct_balance(self, amount: Decimal) -> None:
        if amount > self.balance:
            raise ValueError("余额不足")
        self.balance -= amount
