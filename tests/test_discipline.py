"""Tests for the machine-encoded naming discipline (elixis/discipline.py).

Reference anchors come from halo-collab/experiments/ELIXIS-INWORLD-GLASS.md
round 2 prosody tables and ELIXIS-TITLES.md kill lists. The rubric is
signal-grade: orderings and anchors are asserted, not every human cell.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elixis.discipline import (
    apply_discipline,
    count_syllables,
    dangerous_words_found,
    deniability_check,
    kill_list_violations,
    make_plate,
    name_syllables,
    prosody_scores,
    score_sy,
    validate_plate,
)


class TestSyllables(unittest.TestCase):
    def test_reference_counts(self):
        self.assertEqual(count_syllables("tokjet"), 2)
        self.assertEqual(count_syllables("tokspar"), 2)
        self.assertEqual(count_syllables("meerschaum"), 2)
        self.assertEqual(count_syllables("cairngorm"), 2)
        self.assertEqual(count_syllables("tokmullite"), 3)
        self.assertEqual(count_syllables("tokiolite"), 4)  # the io dip splits

    def test_floors_and_edges(self):
        self.assertEqual(count_syllables("x"), 1)
        self.assertEqual(count_syllables(""), 0)
        self.assertEqual(count_syllables("stone"), 1)  # silent e


class TestProsodyRubric(unittest.TestCase):
    """ST/EC/SO anchors from the round-2 reference table."""

    def test_tokjet_is_the_reference_cadence(self):
        self.assertEqual(prosody_scores("tokjet")["ST"], 5)
        self.assertEqual(prosody_scores("tokjet")["EC"], 5)
        self.assertEqual(prosody_scores("tokjet")["SO"], 5)

    def test_tokmullite_matches_doc_cells(self):
        self.assertEqual(prosody_scores("tokmullite")["ST"], 4)
        self.assertEqual(prosody_scores("tokmullite")["EC"], 4)
        self.assertEqual(prosody_scores("tokmullite")["SO"], 4)

    def test_field_ordering(self):
        """jet sits above the field; iolite/hyalite at the bottom."""
        def avg3(n):
            s = prosody_scores(n)
            return (s["ST"] + s["EC"] + s["SO"]) / 3

        self.assertGreater(avg3("tokjet"), avg3("tokmullite"))
        self.assertGreater(avg3("tokmullite"), avg3("tokiolite"))
        self.assertGreaterEqual(avg3("tokhyalite"), 1.0)
        self.assertLessEqual(avg3("tokhyalite"), avg3("tokmullite"))

    def test_say_it_once_penalizes_ambiguous_units(self):
        self.assertLess(prosody_scores("tokhyalite")["SO"], prosody_scores("tokmullite")["SO"])

    def test_pair_symmetry_doc_anchors(self):
        self.assertEqual(score_sy("tokmullite", "tokopal"), 4)
        self.assertEqual(score_sy("tokspar", "toksmith"), 5)
        self.assertEqual(score_sy("tokiolite", "tokmullite"), 2)
        self.assertEqual(score_sy("tokcalcine", "tokmullite"), 4)

    def test_scores_bounded(self):
        for name in ("a", "aaaa", "tokhyalite", "x" * 20, "THE QUICK BROWN FOX"):
            s = prosody_scores(name)
            for axis in ("ST", "EC", "SO"):
                self.assertTrue(1 <= s[axis] <= 5, f"{axis} out of range for {name}: {s[axis]}")


class TestKillLists(unittest.TestCase):
    def test_em_dash_is_a_house_kill(self):
        self.assertTrue(any("em dash" in v for v in kill_list_violations("tokens — pages")))
        self.assertTrue(any("em dash" in v for v in kill_list_violations("en–dash dies too")))

    def test_house_tokens(self):
        for text in ("the journey begins", "unlock your potential", "unleash the machine"):
            self.assertTrue(kill_list_violations(text), text)

    def test_ai_slop_tokens(self):
        self.assertTrue(any("AI-slop" in v for v in kill_list_violations("a tapestry of insight")))
        self.assertTrue(any("AI-slop" in v for v in kill_list_violations("delve into data")))

    def test_single_part_abbreviation(self):
        self.assertTrue(any("single-part" in v for v in kill_list_violations("QK")))
        self.assertTrue(any("single-part" in v for v in kill_list_violations("CTX")))
        self.assertFalse(kill_list_violations("Tokpal"))

    def test_glass_profile_family_words(self):
        hits = kill_list_violations("Glassback viewer", profile="glass-titles")
        self.assertTrue(any("family word: glass" in h for h in hits))

    def test_glass_profile_killed_words(self):
        hits = kill_list_violations("my console app", profile="glass-titles")
        self.assertTrue(any("kill-list word: console" in h for h in hits))
        hits = kill_list_violations("aurelia", profile="glass-titles")
        self.assertTrue(any("kill-list word: aurelia" in h for h in hits))

    def test_inworld_profile(self):
        hits = kill_list_violations("tokkiln", profile="inworld-glass")
        self.assertTrue(any("kill-list word: kiln" in h for h in hits))

    def test_clean_names_pass(self):
        for name in ("tokmullite", "tokopal", "jellypath", "Pagethru"):
            self.assertEqual(kill_list_violations(name), [])

    def test_dangerous_words_warn_not_kill(self):
        self.assertEqual(kill_list_violations("Jelly Brick", profile="glass-titles"), [])
        self.assertIn("brick", dangerous_words_found("Jelly Brick", profile="glass-titles"))


class TestHyphenCompoundSmuggling(unittest.TestCase):
    """Banned tokens must not survive inside hyphenated compounds.

    The tokenizer kept hyphens inside tokens, so unlock-journey slipped past
    the house kill list that kills "unlock journey".
    """

    def test_hyphenated_house_tokens_killed_like_spaced(self):
        self.assertEqual(
            kill_list_violations("unlock-journey"),
            ["house token: journey", "house token: unlock"],
        )
        self.assertEqual(
            kill_list_violations("unlock journey"),
            ["house token: journey", "house token: unlock"],
        )
        self.assertTrue(
            any("house token: unleash" in v for v in kill_list_violations("unleash-journey"))
        )

    def test_hyphenated_smuggling_killed_for_each_profile(self):
        for profile in (None, "glass-titles", "inworld-glass"):
            hits = kill_list_violations("unlock-journey", profile=profile)
            self.assertIn("house token: journey", hits, profile)
            self.assertIn("house token: unlock", hits, profile)

    def test_hyphenated_house_token_still_matches_exactly(self):
        # "level-up" is itself a banned token; splitting must not lose it.
        self.assertEqual(kill_list_violations("level-up"), ["house token: level-up"])
        self.assertEqual(kill_list_violations("levelup"), ["house token: levelup"])

    def test_clean_hyphenated_names_pass_untouched(self):
        for name in ("tok-smith", "slate-harbor", "quartz-fall"):
            self.assertEqual(kill_list_violations(name), [], name)
            self.assertEqual(kill_list_violations(name, profile="glass-titles"), [], name)
            self.assertEqual(kill_list_violations(name, profile="inworld-glass"), [], name)
            self.assertEqual(dangerous_words_found(name, profile="glass-titles"), [], name)

    def test_hyphenated_dangerous_words_still_warn(self):
        self.assertEqual(dangerous_words_found("watch-path"), ["watch", "path"])
        self.assertEqual(dangerous_words_found("watch path"), ["watch", "path"])
        self.assertEqual(dangerous_words_found("tok-smith"), [])

    def test_prosody_and_syllables_unchanged_on_clean_hyphenated_names(self):
        # name_syllables already treated hyphens as separators; the kill-list
        # fix must not move prosody on clean compounds.
        self.assertEqual(name_syllables("tok-smith"), 2)
        self.assertEqual(prosody_scores("tok-smith"), {"ST": 5, "EC": 5, "SO": 5, "SY": 0})
        self.assertEqual(name_syllables("slate-harbor"), 3)
        self.assertEqual(prosody_scores("slate-harbor"), {"ST": 4, "EC": 4, "SO": 3, "SY": 0})
        self.assertEqual(name_syllables("quartz-fall"), 3)
        self.assertEqual(prosody_scores("quartz-fall"), {"ST": 5, "EC": 3, "SO": 4, "SY": 0})


class TestDeniability(unittest.TestCase):
    def test_bare_wink_fails_straight_face(self):
        for name in ("tokpipe", "tokbowl", "tokgreen", "smokehouse"):
            self.assertEqual(deniability_check(name)["verdict"], "fail", name)

    def test_etymological_wink_passes(self):
        for name in ("tokcairngorm", "tokmeerschaum", "tokamethyst"):
            self.assertEqual(deniability_check(name)["verdict"], "pass", name)

    def test_homophone_compound_passes(self):
        self.assertEqual(deniability_check("tokmullite")["verdict"], "pass")

    def test_no_wink_is_a_warning_not_a_kill(self):
        self.assertEqual(deniability_check("jellypath")["verdict"], "no-wink")


class TestApplyDiscipline(unittest.TestCase):
    def _variants(self):
        return [
            {"name": "tokmullite", "identity_fit": 0.9},
            {"name": "tokpipe", "identity_fit": 0.85},
            {"name": "Glasswick", "identity_fit": 0.8},
            {"name": "QX", "identity_fit": 0.7},
        ]

    def test_kill_list_rejections_go_to_audit_trail(self):
        result = apply_discipline(self._variants(), profile="glass-titles")
        names_kept = [v["name"] for v in result["kept"]]
        names_rejected = [v["name"] for v in result["rejected"]]
        self.assertIn("tokmullite", names_kept)
        self.assertIn("tokpipe", names_rejected)
        self.assertIn("Glasswick", names_rejected)  # glass family
        self.assertIn("QX", names_rejected)  # single-part

    def test_kept_variants_carry_rubric(self):
        result = apply_discipline(self._variants(), profile="glass-titles")
        kept = result["kept"][0]
        for axis in ("ST", "EC", "SO"):
            self.assertIn(axis, kept["prosody"])
        self.assertIn("deniability", kept)

    def test_prosody_failure_blocks_pass(self):
        result = apply_discipline(
            [{"name": "tokhyaliteioeighough", "identity_fit": 0.9}], profile=None
        )
        # catastrophic spellability keeps it out of plates even without kills
        self.assertFalse(result["kept"][0]["discipline_pass"])


class TestPlate(unittest.TestCase):
    def _plate(self):
        return make_plate(
            silk="TOKENS THRU JELLY · PAGES OUT",
            name="Jellypath",
            subtitle="A see-thru token machine that answers on a pager.",
            partner="Pagethru",
        )

    def test_valid_plate_passes(self):
        result = validate_plate(self._plate())
        self.assertEqual(result["violations"], [])
        self.assertTrue(result["valid"])

    def test_em_dash_in_silk_fails(self):
        plate = self._plate()
        plate["silk"] = "TOKENS — PAGES"
        self.assertFalse(validate_plate(plate)["valid"])

    def test_silk_word_count_bounds(self):
        plate = self._plate()
        plate["silk"] = "ONE"
        self.assertFalse(validate_plate(plate)["valid"])
        plate["silk"] = "A · B · C · D · E · F"
        self.assertFalse(validate_plate(plate)["valid"])

    def test_name_word_count_bounds(self):
        plate = self._plate()
        plate["name"] = "a b c d"
        self.assertFalse(validate_plate(plate)["valid"])

    def test_marketing_subtitle_fails(self):
        plate = self._plate()
        plate["subtitle"] = "A revolutionary game-changing machine."
        violations = validate_plate(plate)["violations"]
        self.assertTrue(any("marketing" in v for v in violations))

    def test_multiline_subtitle_fails(self):
        plate = self._plate()
        plate["subtitle"] = "line one\nline two."
        self.assertFalse(validate_plate(plate)["valid"])

    def test_undeniable_name_fails_plate(self):
        plate = self._plate()
        plate["name"] = "tokpipe"
        self.assertFalse(validate_plate(plate)["valid"])

    def test_dangerous_word_is_warning(self):
        result = validate_plate(self._plate(), profile="glass-titles")
        self.assertTrue(any("dangerous" in w for w in result["warnings"]))
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
