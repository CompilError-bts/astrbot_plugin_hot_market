from __future__ import annotations

import unittest

from astrbot_plugin_hot_market.renderer import (
    change_percent,
    money,
    sparkline_points,
)


class RendererTest(unittest.TestCase):
    def test_money(self) -> None:
        self.assertEqual(money(123_456), "1,234.56")

    def test_change_percent(self) -> None:
        self.assertAlmostEqual(change_percent(125, 100), 25.0)
        self.assertEqual(change_percent(100, 0), 0.0)

    def test_sparkline_handles_flat_and_rising_data(self) -> None:
        flat = sparkline_points([100, 100, 100])
        rising = sparkline_points([100, 110, 130])
        self.assertEqual(len(flat.split()), 3)
        self.assertEqual(len(rising.split()), 3)
        self.assertNotEqual(flat, rising)


if __name__ == "__main__":
    unittest.main()
