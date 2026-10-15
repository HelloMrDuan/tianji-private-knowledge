"""Verify actual pinned original texts and approved Bazi excerpts."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def validate(audit, phase1, foundations):
    texts = {}
    for source_id, source in audit["sources"].items():
        raw = (ROOT / source["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("original SHA mismatch: " + source_id)
        texts[source_id] = raw.decode("utf-8")
    sections = {row["id"]: row for row in phase1["sections"]}
    if len(audit["witnesses"]) != 12:
        raise ValueError("expected twelve witnesses")
    for witness in audit["witnesses"]:
        sec = sections[witness["section_id"]]
        if sec["review"]["status"] != "approved":
            raise ValueError("unapproved excerpt")
        if sec["source_id"] != witness["source_id"]:
            raise ValueError("source ID mismatch")
        text = texts[witness["source_id"]]
        start = witness["raw_char_offset"]
        if text[start:start + len(sec["text"])] != sec["text"]:
            raise ValueError("raw text or offset mismatch: " + sec["id"])
    if foundations["provenance"]["repo"] != audit["secondary_table"]["original_repo"]:
        raise ValueError("secondary source identity changed")
    return sections


class WitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load("data/audit/tj0101_source_witnesses.json")
        cls.phase1 = load("data/canonical/bazi/phase1_knowledge.json")
        cls.foundations = load("data/canonical/bazi/foundations_v1.json")

    def test_twelve_pinned_raw_offsets_and_sha256(self):
        sections = validate(self.audit, self.phase1, self.foundations)
        self.assertEqual(len(sections["bazi.section.s004"]["text"]) > 80, True)

    def test_mutated_offset_rejected(self):
        import copy
        altered = copy.deepcopy(self.audit)
        altered["witnesses"][0]["raw_char_offset"] += 1
        with self.assertRaisesRegex(ValueError, "offset mismatch"):
            validate(altered, self.phase1, self.foundations)

    def test_mutated_sha256_rejected(self):
        import copy
        altered = copy.deepcopy(self.audit)
        altered["sources"]["bazi.source.yuanhai"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            validate(altered, self.phase1, self.foundations)
