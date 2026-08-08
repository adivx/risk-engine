import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from riskengine import __version__
from riskengine.cli import build_parser, main


class TestParser(unittest.TestCase):
    def test_defaults(self):
        args = build_parser().parse_args([])
        self.assertEqual(args.command, "report")
        self.assertIsNone(args.csv)
        self.assertEqual(args.alpha, 0.05)

    def test_csv_flag(self):
        args = build_parser().parse_args(["--csv", "x.csv"])
        self.assertEqual(args.csv, "x.csv")


class TestMain(unittest.TestCase):
    def test_synthetic_report_exits_zero(self):
        self.assertEqual(main(["--seed", "1", "--years", "1"]), 0)

    def test_csv_report_exits_zero(self):
        sample = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "sample_data", "sample_ohlcv.csv")
        self.assertEqual(main(["--csv", sample]), 0)

    def test_missing_csv_exits_nonzero(self):
        self.assertNotEqual(main(["--csv", "/nonexistent/nope.csv"]), 0)

    def test_chart_writes_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "dd.svg")
            self.assertEqual(main(["--seed", "1", "chart", "--out", out]), 0)
            self.assertTrue(os.path.exists(out))
            with open(out) as f:
                content = f.read()
            self.assertIn("<svg", content)
            self.assertIn("<polyline", content)

    def test_version_flag(self):
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, redirect_stdout(buf):
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(__version__, buf.getvalue())


class TestJsonReport(unittest.TestCase):
    def test_json_report_is_valid_and_complete(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(main(["--seed", "1", "--years", "1", "--json"]), 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["alpha"], 0.05)
        self.assertEqual(data["version"], __version__)
        self.assertIn("var", data)
        self.assertIn("drawdown", data)
        # Every VaR engine exposes both var and cvar.
        for engine in ("historical", "parametric", "monte_carlo"):
            self.assertIn("var", data["var"][engine])
            self.assertIn("cvar", data["var"][engine])

    def test_json_defaults_to_false(self):
        self.assertFalse(build_parser().parse_args([]).json)

    def test_alpha_flag_changes_the_computed_var(self):
        # Regression guard: --alpha must reach var_estimate, not just the
        # table title.
        def historical_var(alpha):
            buf = io.StringIO()
            with redirect_stdout(buf):
                main(["--seed", "1", "--years", "1", "--json",
                      "--alpha", str(alpha)])
            return json.loads(buf.getvalue())["var"]["historical"]["var"]

        self.assertNotAlmostEqual(historical_var(0.01), historical_var(0.05),
                                  places=6)


if __name__ == "__main__":
    unittest.main()
