import unittest
from decimal import Decimal

from utils.validators import money, money_text, parse_selection, validate_bet_amount


class ValidatorsTest(unittest.TestCase):
    def test_parse_money_and_format(self):
        self.assertEqual(money("100.235"), Decimal("100.24"))
        self.assertEqual(money_text(Decimal("3")), "3.00")
        with self.assertRaises(ValueError):
            money("0")

    def test_parse_selection_aliases(self):
        self.assertEqual(parse_selection("主胜"), "H")
        self.assertEqual(parse_selection("平局"), "D")
        self.assertEqual(parse_selection("负"), "A")
        with self.assertRaises(ValueError):
            parse_selection("大球")

    def test_validate_bet_amount(self):
        validate_bet_amount(Decimal("100"), Decimal("100"), Decimal("1000"))
        with self.assertRaises(ValueError):
            validate_bet_amount(Decimal("99"), Decimal("100"), Decimal("1000"))
        with self.assertRaises(ValueError):
            validate_bet_amount(Decimal("1001"), Decimal("100"), Decimal("1000"))


if __name__ == "__main__":
    unittest.main()
