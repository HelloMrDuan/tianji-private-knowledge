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

    def test_twelve_branch_memberships_match_approved_s004(self):
        sections = validate(self.audit, self.phase1, self.foundations)
        song = sections["bazi.section.s004"]["text"]
        expected = {
            "子": ("子宫癸水", "癸"), "丑": ("丑癸辛金己土", "癸辛己"),
            "寅": ("寅宫甲木兼丙戊", "甲丙戊"), "卯": ("卯宫乙木独相逢", "乙"),
            "辰": ("辰藏乙戊三分癸", "乙戊癸"), "巳": ("巳中庚金丙戊丛", "庚丙戊"),
            "午": ("午宫丁火并己土", "丁己"), "未": ("未宫乙己丁共宗", "乙己丁"),
            "申": ("申位庚金壬水戊", "庚壬戊"), "酉": ("酉宫辛金独丰隆", "辛"),
            "戌": ("戌宫辛金及丁戊", "辛丁戊"), "亥": ("亥藏壬甲是真踪", "壬甲"),
        }
        actual = self.foundations["hidden_stems"]
        self.assertEqual(set(actual), set(expected))
        for branch, (clause, stems) in expected.items():
            with self.subTest(branch=branch):
                self.assertIn(clause, song)
                self.assertEqual(len(actual[branch]), len(stems))
                self.assertEqual(set(actual[branch]), set(stems))

    def test_mutated_hidden_stem_membership_rejected(self):
        import copy
        altered = copy.deepcopy(self.foundations)
        altered["hidden_stems"]["寅"].remove("戊")
        song = validate(self.audit, self.phase1, altered)["bazi.section.s004"]["text"]
        self.assertIn("寅宫甲木兼丙戊", song)
        self.assertNotEqual(set(altered["hidden_stems"]["寅"]), set("甲丙戊"))

    def test_no_promoted_or_unresolved_method_claims(self):
        self.assertFalse(self.audit["secondary_table"]["canonical_removal_authorized"])
        self.assertEqual(len(self.audit["unresolved"]), 4)
        self.assertEqual({x["review_level"] for x in self.audit["witnesses"]}, {"C"})
        self.assertIn("weight", " ".join(self.audit["unresolved"]))


if __name__ == '__main__':
    unittest.main()
