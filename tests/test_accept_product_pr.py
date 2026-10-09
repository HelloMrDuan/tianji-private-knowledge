"""Pure guardrail regressions for private-only PR acceptance orchestration."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "accept_product_pr.py"
spec = importlib.util.spec_from_file_location("accept_product_pr", MODULE_PATH)
assert spec is not None and spec.loader is not None
accept = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accept)


class AcceptanceScriptTests(unittest.TestCase):
    def test_only_declared_real_suites_are_accepted(self):
        self.assertEqual(accept.modules_for("career"), [
            "test_career_interpretation", "test_scenario_engine"])
        self.assertEqual(accept.modules_for("romance"), [
            "test_romance_spouse_year_structure", "test_scenario_engine"])
        self.assertEqual(accept.modules_for("periods"), [
            "test_daily_period_branch_relations", "test_scenario_engine"])
        self.assertEqual(accept.modules_for("all")[-1], "test_scenario_engine")
        with self.assertRaisesRegex(ValueError, "Unknown"):
            accept.modules_for("unknown")

    def test_unpinned_and_data_bearing_public_checkouts_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "code"
            root.mkdir()
            (root / "data").mkdir()
            with self.assertRaisesRegex(ValueError, "private data"):
                accept._assert_public_checkout(root, "a" * 40)
            (root / "data").rmdir()
            with self.assertRaisesRegex(ValueError, "40-character"):
                accept._assert_public_checkout(root, "main")
            allowed_origin = "https://github.com/HelloMrDuan/tianji-knowledge-base.git"
            with patch.object(accept.subprocess, "check_output",
                              side_effect=[allowed_origin, "b" * 40]):
                with self.assertRaisesRegex(ValueError, "pinned SHA"):
                    accept._assert_public_checkout(root, "a" * 40)
            with patch.object(accept.subprocess, "check_output",
                              return_value="https://github.com/not-owner/other.git"):
                with self.assertRaisesRegex(ValueError, "owner's public repository"):
                    accept._assert_public_checkout(root, "a" * 40)
            with patch.object(accept.subprocess, "check_output",
                              side_effect=[allowed_origin, "a" * 40, "?? scripts/unsafe.py"]):
                with self.assertRaisesRegex(ValueError, "unreviewed local"):
                    accept._assert_public_checkout(root, "a" * 40)
            with patch.object(accept.subprocess, "check_output",
                              side_effect=[allowed_origin, "a" * 40, ""]):
                accept._assert_public_checkout(root, "a" * 40)

    def test_reject_non_private_ci_before_reading_data_or_installing_code(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(accept.os.environ, {
                "GITHUB_ACTIONS": "true",
                "GITHUB_REPOSITORY": "untrusted/public",
            }):
                with self.assertRaisesRegex(ValueError, "only in the private repository"):
                    accept.run_acceptance(Path(temp), Path(temp), "a" * 40, "career")

    def test_no_shell_execution_function(self):
        import inspect
        source = inspect.getsource(accept._run)
        self.assertNotIn("shell=True", source)
        self.assertIn("check=True", source)


if __name__ == "__main__":
    unittest.main()
