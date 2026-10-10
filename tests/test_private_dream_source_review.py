"""Original-RAW negative tests for an unpromoted D-level dream review."""
import copy
import json
import os
import unittest
from pathlib import Path

from scripts.import_public_snapshot import verify
from scripts.verify_pending_dream_source import (
    APPENDIX, BASE, SNAPSHOT, verify_pending_review,
)

RAW_FILE = os.environ.get("TIANJI_REVIEW_DREAM_RAW")


@unittest.skipUnless(RAW_FILE, "Original raw is supplied by the dedicated pinned CI")
class PendingDreamSourceReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = Path(RAW_FILE).read_bytes()
        cls.metadata = json.loads(SNAPSHOT.read_text("utf-8"))
        cls.appendix = json.loads(APPENDIX.read_text("utf-8"))

    def test_complete_original_and_untouched_private_snapshot(self):
        before = verify(BASE)
        result = verify_pending_review(self.raw, self.metadata, self.appendix)
        self.assertEqual(before["file_count"], 235)
        self.assertEqual(result["candidate_count"], 3)
        self.assertEqual(result["evidence_level"], "D")
        self.assertFalse(result["released"])
        self.assertFalse(result["independent_source_verified"])
        self.assertEqual(verify(BASE), before)

    def test_tampered_raw_and_promoted_candidate_are_rejected(self):
        for value in (self.raw + b" ", b"X" + self.raw[1:]):
            with self.assertRaisesRegex(ValueError, "integrity"):
                verify_pending_review(value, self.metadata, self.appendix)
        for name, modify in (
            ("moved_offset", lambda a: a["candidates"][0].__setitem__("raw_unicode_offset", 1)),
            ("fabricated_quote", lambda a: a["candidates"][0].__setitem__("exact_anchor", "假造梦书原文")),
            ("level_upgrade", lambda a: a["candidates"][0].__setitem__("evidence_level", "C")),
            ("scope_upgrade", lambda a: a["candidates"][1].__setitem__("match_scope", "direct_scene")),
            ("unauthorized_api", lambda a: a["promotion"].__setitem__("public_enabled", True)),
            ("unauthorized_AI", lambda a: a["promotion"].__setitem__("ai_enabled", True)),
            ("claimed_independent_edition", lambda a: a["promotion"].__setitem__("independent_source_verified", True)),
        ):
            amended = copy.deepcopy(self.appendix)
            modify(amended)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "integrity"):
                verify_pending_review(self.raw, self.metadata, amended)


if __name__ == "__main__":
    unittest.main()
