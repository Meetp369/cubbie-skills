import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "grade.py"
spec = importlib.util.spec_from_file_location("grade", SCRIPT)
grade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grade)


class GradeMathTests(unittest.TestCase):
    def test_weighted_exact_math(self):
        data = {
            "scheme": "weighted", "cutoffs": {"A": 90}, "cutoffs_verified": True,
            "rules_verified": True, "inventory_complete": True,
            "categories": [
                {"name": "HW", "weight": 50, "scores": [[80, 100]], "remaining": [{"name":"HW2","possible":100}]},
                {"name": "Final", "weight": 50, "scores": [], "remaining": [{"name":"Final","possible":100}]},
            ]
        }
        notes, warnings = [], []
        grade.validate(data)
        current, A, B, W, items = grade.analyze(data, notes, warnings)
        self.assertAlmostEqual(current, 80)
        self.assertAlmostEqual(A, 20)
        self.assertAlmostEqual(B, 75)
        self.assertAlmostEqual(W, 100)
        self.assertFalse(warnings)
        self.assertEqual(len(items), 2)

    def test_drop_lowest(self):
        cat = {"name":"Quiz", "drop_lowest":1, "scores":[[2,10],[8,10],[10,10]]}
        scores, dropped = grade.read_scores(cat)
        self.assertEqual(dropped, [(2.0,10.0)])
        self.assertEqual(scores, [(8.0,10.0),(10.0,10.0)])

    def test_unknown_points_in_points_course_fails(self):
        data = {"scheme":"points", "categories":[{"name":"Final","scores":[],"remaining":[{"name":"Final","possible":None}]}]}
        grade.validate(data)
        with self.assertRaisesRegex(ValueError, "unknown points"):
            grade.analyze(data, [], [])

    def test_partial_weighted_unknown_future_fails_instead_of_guessing(self):
        data = {"scheme":"weighted", "categories":[{"name":"Project","weight":100,"scores":[[20,20]],"remaining":[{"name":"Phase 2","possible":None}]}]}
        grade.validate(data)
        with self.assertRaisesRegex(ValueError, "both completed work and remaining work with unknown points"):
            grade.analyze(data, [], [])

    def test_extra_credit_rejected_unless_enabled(self):
        data = {"scheme":"points", "categories":[{"name":"EC","scores":[[11,10]],"remaining":0}]}
        with self.assertRaisesRegex(ValueError, "allow_extra_credit"):
            grade.validate(data)
        data["allow_extra_credit"] = True
        grade.validate(data)


class CliTests(unittest.TestCase):
    def run_cli(self, payload, *args):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(payload, f); path = f.name
        return subprocess.run([sys.executable, str(SCRIPT), path, *args], text=True, capture_output=True)

    def test_exact_status_and_target_label(self):
        payload = {"course":"T", "scheme":"weighted", "cutoffs":{"A":90}, "cutoffs_verified":True,
                   "rules_verified":True, "inventory_complete":True,
                   "categories":[{"name":"Work","weight":100,"scores":[[80,100]],"remaining":[{"name":"Final","possible":100}]}]}
        r = self.run_cli(payload, "--target", "A")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Status: EXACT", r.stdout)
        self.assertIn("NOT separate minimums", r.stdout)
        self.assertIn("100/100", r.stdout)

    def test_missing_cutoff_is_provisional(self):
        payload = {"scheme":"points", "inventory_complete":True,
                   "categories":[{"name":"Work","scores":[[90,100]],"remaining":100}]}
        r = self.run_cli(payload, "--target", "A")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Status: PROVISIONAL", r.stdout)
        self.assertIn("fallback plus/minus scale", r.stdout)

    def test_invalid_target_errors_instead_of_silently_changing(self):
        payload = {"scheme":"points", "cutoffs":{"A":90}, "inventory_complete":True,
                   "categories":[{"name":"Work","scores":[[90,100]],"remaining":100}]}
        r = self.run_cli(payload, "--target", "A++")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not on the course grade scale", r.stdout)

    def test_what_if_range_validation(self):
        payload = {"scheme":"points", "categories":[{"name":"Work","scores":[[90,100]],"remaining":100}]}
        r = self.run_cli(payload, "--what-if", "120")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
