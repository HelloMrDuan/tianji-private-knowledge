"""Private-only SHA-locked Dayun terminology appendix; original snapshot is immutable."""
import copy
import json
import unittest
from pathlib import Path

from scripts.import_public_snapshot import verify
from tianji_kb.bazi_dayun_source_audit import (
    validate_role_terminology_appendix, AUDIT_PATH, RAW_PATH,
    CANONICAL_PATH,
)

ROOT = Path(__file__).resolve().parents[1]
APPENDIX = ROOT / "private-reviews/dayun_role_terminology_v1.json"


class DayunRoleAppendixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))
        cls.appendix = json.loads(APPENDIX.read_text(encoding="utf-8"))
        cls.raw = (ROOT / RAW_PATH).read_bytes()
        cls.canonical = (ROOT / CANONICAL_PATH).read_bytes()

    def test_original_snapshot_manifest_remains_unchanged(self):
        record = verify(ROOT)
        self.assertEqual(record["file_count"], 235)
        self.assertEqual(record["total_bytes"], 13518179)
        self.assertEqual(len(self.audit["claims"]), 4)
        self.assertFalse((ROOT / "data/private-reviews").exists())

    def test_fixed_quote_is_real_but_direction_adjudication_remains_closed(self):
        result = validate_role_terminology_appendix(
            self.appendix, self.raw, self.canonical, self.audit)
        self.assertTrue(result["fixed_original_fragment_verified"])
        self.assertTrue(result["research_only"])
        self.assertFalse(result["canonical_method_adjudicated"])
        self.assertFalse(result["independent_edition_verified"])
        self.assertFalse(result["public_enabled"])
        self.assertFalse(result["ai_enabled"])

    def test_reject_forged_quote_and_unauthorized_release(self):
        for field, value in (
            ("exact_excerpt", "臆造顺逆命理古文"),
            ("raw_char_offset", 0),
            ("scope", "此处足以公开所有大运自动推断与吉凶断言"),
        ):
            altered = copy.deepcopy(self.appendix)
            altered["claim"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_role_terminology_appendix(
                    altered, self.raw, self.canonical, self.audit)
        altered = copy.deepcopy(self.appendix)
        altered["changes_to_release"]["public_enabled"] = True
        with self.assertRaisesRegex(ValueError, "cannot authorize release"):
            validate_role_terminology_appendix(
                altered, self.raw, self.canonical, self.audit)


if __name__ == "__main__":
    unittest.main()
