import unittest

from ..parsing import parse_money_to_cents


class MoneyParsingTests(unittest.TestCase):
    def test_string_amount_is_converted_to_cents(self):
        self.assertEqual(parse_money_to_cents("500"), 50_000)
        self.assertEqual(parse_money_to_cents(" 12.34 "), 1_234)

    def test_fractional_cent_rounds_half_up(self):
        self.assertEqual(parse_money_to_cents("12.345"), 1_235)

    def test_invalid_amounts_are_rejected(self):
        for amount in ("", "abc", "NaN", "Infinity", "0", "-1", "0.001"):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    parse_money_to_cents(amount)


if __name__ == "__main__":
    unittest.main()
