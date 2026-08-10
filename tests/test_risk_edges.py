"""Edge cases for drawdown analytics."""

import unittest

from riskengine.risk import (
    current_drawdown,
    drawdown_series,
    longest_drawdown_stretch,
    max_drawdown,
)


class TestEmptySeries(unittest.TestCase):
    def test_empty_prices_raise_value_error(self):
        for fn in (drawdown_series, max_drawdown, current_drawdown,
                   longest_drawdown_stretch):
            with self.assertRaises(ValueError):
                fn([])


class TestDrawdownEdges(unittest.TestCase):
    def test_single_point_series(self):
        prices = [100.0]
        self.assertEqual(max_drawdown(prices), (0.0, 0, 0))
        self.assertEqual(current_drawdown(prices), 0.0)

    def test_flat_series_has_no_drawdown(self):
        prices = [100.0, 100.0, 100.0]
        dd, peak_i, trough_i = max_drawdown(prices)
        self.assertEqual(dd, 0.0)
        self.assertEqual((peak_i, trough_i), (0, 0))

    def test_recovery_same_day_resets_stretch(self):
        # 100 -> 90 (underwater) -> 105 (new peak, recovered same day) -> 104.
        prices = [100.0, 90.0, 105.0, 104.0]
        length, start, end = longest_drawdown_stretch(prices)
        self.assertEqual((length, start, end), (1, 1, 1))

    def test_prolonged_underwater_stretch(self):
        # 100 -> 80 -> 75 -> 95 -> 120: underwater from obs 1 to obs 3.
        prices = [100.0, 80.0, 75.0, 95.0, 120.0]
        length, start, end = longest_drawdown_stretch(prices)
        self.assertEqual((length, start, end), (3, 1, 3))


if __name__ == "__main__":
    unittest.main()
