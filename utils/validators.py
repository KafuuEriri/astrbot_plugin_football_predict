from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict

SELECTION_ALIASES: Dict[str, str] = {
    "主胜": "H",
    "胜": "H",
    "h": "H",
    "H": "H",
    "平": "D",
    "平局": "D",
    "d": "D",
    "D": "D",
    "客胜": "A",
    "负": "A",
    "客负": "A",
    "a": "A",
    "A": "A",
}

SELECTION_TEXT = {"H": "主胜", "D": "平", "A": "客胜"}


def money(value) -> Decimal:
    if isinstance(value, Decimal):
        result = value
    else:
        try:
            result = Decimal(str(value).strip())
        except (InvalidOperation, AttributeError):
            raise ValueError("金额格式错误")
    if result <= 0:
        raise ValueError("金额必须大于0")
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_text(value) -> str:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP).to_eng_string()


def parse_selection(value: str) -> str:
    selection = SELECTION_ALIASES.get(str(value).strip())
    if not selection:
        raise ValueError("投注选项必须是主胜、平或客胜")
    return selection


def selection_text(selection: str) -> str:
    return SELECTION_TEXT.get(selection, selection)


def validate_bet_amount(amount: Decimal, min_amount: Decimal, max_amount: Decimal) -> None:
    if amount < min_amount:
        raise ValueError(f"投注金额不能低于 {money_text(min_amount)}")
    if amount > max_amount:
        raise ValueError(f"投注金额不能高于 {money_text(max_amount)}")
