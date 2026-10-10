"""Real source registry and original private inventory gates."""
import copy
import json
import unittest

from scripts.verify_external_source_witnesses import DREAM, DAYUN, validate, verify

class ExternalSourceWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dream = json.loads(DREAM.read_text("utf-8"))
        cls.dayun = json.loads(DAYUN.read_text("utf-8"))

    def test_fixed_real_research_witnesses_and_private_snapshot(self):
        observed = verify()
        self.assertEqual(observed["dream_excerpt_witnesses"], 2)
        self.assertEqual(observed["dayun_excerpt_witnesses"], 3)
        self.assertEqual(observed["bibliography_leads"], 2)
        self.assertEqual(observed["production_promotions"], 0)

    def test_fake_public_promotion_and_method_approval_rejected(self):
        for section, field, value in (
            ("dream", "public_enabled", True),
            ("dream", "canonical_promotions", 1),
            ("dream", "independent_edition_confirmed", True),
            ("dayun", "classical_method_adjudicated", True),
            ("dayun", "start_age_release", True),
            ("dayun", "handover_datetime_release", True),
        ):
            dream, dayun = copy.deepcopy(self.dream), copy.deepcopy(self.dayun)
            (dream if section == "dream" else dayun)["gate"][field] = value
            with self.subTest(section=section, field=field):
                with self.assertRaisesRegex(ValueError, "integrity"):
                    validate(dream, dayun)

    def test_forged_source_excerpt_and_resolved_conflict_rejected(self):
        for side, mutate in (
            ("dream", lambda d: d["witnesses"][0].__setitem__(
                "transcribed_excerpt", "伪造的古籍断语")),
            ("dayun", lambda d: d["witnesses"][1].__setitem__(
                "exact_excerpt", "并非三日一岁")),
            ("dayun", lambda d: d["conflict_register"][0].__setitem__(
                "status", "resolved")),
        ):
            dream, dayun = copy.deepcopy(self.dream), copy.deepcopy(self.dayun)
            mutate(dream if side == "dream" else dayun)
            with self.subTest(side=side):
                with self.assertRaisesRegex(ValueError, "integrity"):
                    validate(dream, dayun)

if __name__ == "__main__":
    unittest.main()
