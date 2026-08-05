import os
import tempfile
import unittest

from riskengine.data import PriceSeries, load_prices_csv, synthetic_equity_curve

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                      "sample_data", "sample_ohlcv.csv")


class TestPriceSeries(unittest.TestCase):
    def test_returns_are_period_over_period(self):
        ps = PriceSeries(name="x", dates=[], prices=[100.0, 110.0, 99.0])
        self.assertAlmostEqual(ps.returns()[0], 0.10)
        self.assertAlmostEqual(ps.returns()[1], 99.0 / 110.0 - 1.0)

    def test_n_obs_and_dates(self):
        ps = PriceSeries(name="x", dates=["2020-01-01", "2020-01-02"],
                         prices=[1.0, 2.0])
        self.assertEqual(ps.n_obs, 2)
        self.assertEqual(ps.from_date(), "2020-01-01")
        self.assertEqual(ps.to_date(), "2020-01-02")


class TestLoadPricesCsv(unittest.TestCase):
    def test_ohlcv_uses_close_column(self):
        ps = load_prices_csv(SAMPLE, name="SPX")
        self.assertEqual(ps.name, "SPX")
        self.assertGreaterEqual(ps.n_obs, 250)
        self.assertAlmostEqual(ps.prices[0], 100.6759, places=4)
        self.assertEqual(ps.dates[0], "2020-01-02")

    def test_returns_computed(self):
        ps = load_prices_csv(SAMPLE)
        self.assertEqual(len(ps.returns()), ps.n_obs - 1)

    def test_bare_numeric_csv(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("price\n100\n105\n101\n")
            path = f.name
        try:
            ps = load_prices_csv(path)
            self.assertEqual(ps.prices, [100.0, 105.0, 101.0])
            self.assertEqual(ps.dates, [])
        finally:
            os.unlink(path)

    def test_date_column_carried(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("date,close\n2020-01-02,10\n2020-01-03,10.5\n")
            path = f.name
        try:
            ps = load_prices_csv(path)
            self.assertEqual(ps.dates, ["2020-01-02", "2020-01-03"])
            self.assertEqual(ps.prices, [10.0, 10.5])
        finally:
            os.unlink(path)

    def test_skips_rows_without_close(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("date,open,high,low,close,volume\n")
            f.write("2020-01-02,1,2,0.5,1.5,100\n")
            f.write("2020-01-03,,,,\n")
            f.write("2020-01-06,2,3,1.5,2.5,100\n")
            path = f.name
        try:
            ps = load_prices_csv(path)
            self.assertEqual(ps.prices, [1.5, 2.5])
            self.assertEqual(ps.dates, ["2020-01-02", "2020-01-06"])
        finally:
            os.unlink(path)

    def test_empty_file_raises(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_prices_csv(path)
        finally:
            os.unlink(path)


class TestSynthetic(unittest.TestCase):
    def test_seeded_reproducible(self):
        a = synthetic_equity_curve(seed=3, years=1)
        b = synthetic_equity_curve(seed=3, years=1)
        self.assertEqual(a.prices, b.prices)
        self.assertEqual(a.dates, b.dates)

    def test_length_matches_years(self):
        ps = synthetic_equity_curve(seed=42, years=1)
        self.assertEqual(ps.n_obs, 253)  # start + 252 trading days

    def test_starts_at_given_value(self):
        ps = synthetic_equity_curve(seed=42, start=500.0)
        self.assertEqual(ps.prices[0], 500.0)

    def test_dates_are_weekdays(self):
        import datetime as dt
        ps = synthetic_equity_curve(seed=42, years=1)
        for d in ps.dates:
            self.assertLess(dt.date.fromisoformat(d).weekday(), 5)


if __name__ == "__main__":
    unittest.main()
