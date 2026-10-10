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
        self.assertEqual(result["candidate_count"], 7)
        self.assertEqual(result["evidence_level"], "D")
        self.assertFalse(result["released"])
        self.assertFalse(result["independent_source_verified"])
        self.assertEqual(verify(BASE), before)

    def test_four_related_modern_topics_are_not_historical_scene_equivalents(self):
        expected = {
            "pregnancy": "携手上桥妻有孕",
            "marriage": "夫妇宴会主相别",
            "work": "受职上官财物来",
            "exam": "读书文写字大吉",
        }
        records = {item["id"]: item for item in self.appendix["candidates"]}
        self.assertEqual(len(records), 7)
        for name, quote in expected.items():
            with self.subTest(name=name):
                row = records[name]
                self.assertEqual(row["exact_anchor"], quote)
                self.assertEqual(row["match_scope"], "related_only")
                self.assertEqual(row["review_status"], "pending")
                self.assertEqual(row["evidence_level"], "D")
                self.assertFalse(row["production_allowed"])
                self.assertEqual(self.raw.decode("utf-8").count(quote), 1)
                offset = row["raw_unicode_offset"]
                self.assertEqual(self.raw.decode("utf-8")[offset:offset+len(quote)], quote)
        outcome = verify_pending_review(self.raw, self.metadata, self.appendix)
        self.assertEqual(outcome["candidate_count"], 7)
        self.assertFalse(outcome["released"])
        self.assertFalse(outcome["independent_source_verified"])

    def test_extended_related_topics_cannot_be_promoted_or_repositioned(self):
        for name in ("pregnancy", "marriage", "work", "exam"):
            index = next(i for i, row in enumerate(self.appendix["candidates"])
                         if row["id"] == name)
            for field, value in (
                ("review_status", "approved_cultural_excerpt"),
                ("match_scope", "direct_scene"),
                ("evidence_level", "C"),
                ("production_allowed", True),
                ("raw_unicode_offset", 0),
                ("exact_anchor", "臆造新古籍条目"),
            ):
                altered = copy.deepcopy(self.appendix)
                altered["candidates"][index][field] = value
                with self.subTest(name=name, field=field), self.assertRaisesRegex(
                        ValueError, "integrity"):
                    verify_pending_review(self.raw, self.metadata, altered)

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
