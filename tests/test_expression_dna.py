"""Tests for expression DNA analysis (elixis.expression_dna)."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elixis.expression_dna import (
    analyze_text,
    compare_styles,
    detect_caricature,
)


class TestAnalyzeTextDimensions(unittest.TestCase):
    """analyze_text returns correct dimension values for known inputs."""

    def test_formal_long_sentences(self):
        text = (
            "The fundamental principles underlying this particular subject are "
            "extraordinarily complex and require careful examination of multiple "
            "interconnected frameworks. Furthermore, the implications of these "
            "findings extend well beyond the immediate scope of the analysis."
        )
        result = analyze_text(text)
        # Long sentences produce high avg_sentence_length
        self.assertGreater(result["dimensions"]["avg_sentence_length"], 15)
        # Which drives the formal_colloquial spectra positive
        self.assertGreater(result["spectra"]["formal_colloquial"], 0)

    def test_questions_yield_positive_ratio(self):
        text = "What is the meaning of this? Why does it matter? How so?"
        result = analyze_text(text)
        self.assertGreater(result["dimensions"]["question_ratio"], 0)

    def test_analogies_yield_positive_density(self):
        text = "This is like a dream. It is as if the world changed. It is akin to magic."
        result = analyze_text(text)
        self.assertGreater(result["dimensions"]["analogy_density"], 0)

    def test_first_person_yields_positive_ratio(self):
        text = "I think my approach is better. I've seen it. I'll prove it."
        result = analyze_text(text)
        self.assertGreater(result["dimensions"]["first_person_ratio"], 0)

    def test_certainty_words_yield_positive(self):
        text = "This is certainly the right approach. It is obviously correct."
        result = analyze_text(text)
        self.assertGreater(result["dimensions"]["certainty_expression"], 0)

    def test_transitions_yield_positive_frequency(self):
        text = (
            "First point. However, there is more. Therefore we proceed. "
            "Furthermore, it matters."
        )
        result = analyze_text(text)
        self.assertGreater(result["dimensions"]["transition_frequency"], 0)

    def test_empty_string(self):
        result = analyze_text("")
        dims = result["dimensions"]
        self.assertEqual(dims["avg_sentence_length"], 0.0)
        self.assertEqual(dims["question_ratio"], 0.0)


class TestAnalyzeTextStructure(unittest.TestCase):
    """analyze_text returns the expected keys and clamped values."""

    def test_returns_all_six_dimensions(self):
        result = analyze_text("Hello world.")
        expected_dims = {
            "avg_sentence_length",
            "question_ratio",
            "analogy_density",
            "first_person_ratio",
            "certainty_expression",
            "transition_frequency",
        }
        self.assertEqual(set(result["dimensions"].keys()), expected_dims)

    def test_returns_all_seven_spectra(self):
        result = analyze_text("Hello world.")
        expected_spectra = {
            "formal_colloquial",
            "abstract_concrete",
            "cautious_assertive",
            "analytical_narrative",
            "serious_playful",
            "reserved_expressive",
            "concise_elaborate",
        }
        self.assertEqual(set(result["spectra"].keys()), expected_spectra)

    def test_spectra_values_clamped(self):
        text = (
            "Certainly definitely clearly obviously undeniably absolutely "
            "undoubtedly without question. " * 20
        )
        result = analyze_text(text)
        for name, value in result["spectra"].items():
            self.assertGreaterEqual(
                value, -1.0, f"Spectra {name} is below -1.0: {value}"
            )
            self.assertLessEqual(
                value, 1.0, f"Spectra {name} is above 1.0: {value}"
            )

    def test_spectra_values_clamped_negative_direction(self):
        text = "Hi! Wow! Cool! Amazing! Me! My! I'm thrilled! " * 20
        result = analyze_text(text)
        for name, value in result["spectra"].items():
            self.assertGreaterEqual(value, -1.0)
            self.assertLessEqual(value, 1.0)


class TestCompareStyles(unittest.TestCase):
    """compare_styles computes similarity between two DNA profiles."""

    def test_identical_dna_returns_near_one(self):
        dna = analyze_text("The formal analysis of this subject is thorough.")
        similarity = compare_styles(dna, dna)
        self.assertAlmostEqual(similarity, 1.0, places=5)

    def test_opposite_dna_returns_lower_value(self):
        dna_formal = analyze_text(
            "The fundamental principles underlying this subject are "
            "extraordinarily complex and require careful examination."
        )
        dna_casual = analyze_text(
            "Hey! I love this! Wow, it's so cool! Me too! My favorite!"
        )
        sim_same = compare_styles(dna_formal, dna_formal)
        sim_diff = compare_styles(dna_formal, dna_casual)
        self.assertLess(sim_diff, sim_same)

    def test_zero_magnitude_vectors_uses_fallback(self):
        # Craft spectra where all values are 0 to get zero magnitude
        dna_a = {"spectra": {k: 0.0 for k in [
            "formal_colloquial", "abstract_concrete", "cautious_assertive",
            "analytical_narrative", "serious_playful", "reserved_expressive",
            "concise_elaborate",
        ]}}
        dna_b = {"spectra": {k: 0.0 for k in dna_a["spectra"]}}
        result = compare_styles(dna_a, dna_b)
        self.assertAlmostEqual(result, 1.0)

    def test_one_zero_one_nonzero(self):
        dna_zero = {"spectra": {k: 0.0 for k in [
            "formal_colloquial", "abstract_concrete", "cautious_assertive",
            "analytical_narrative", "serious_playful", "reserved_expressive",
            "concise_elaborate",
        ]}}
        dna_nonzero = {"spectra": {k: 0.5 for k in dna_zero["spectra"]}}
        result = compare_styles(dna_zero, dna_nonzero)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)


class TestDetectCaricature(unittest.TestCase):
    """detect_caricature identifies extreme dimension values."""

    def test_extreme_value_is_caricature(self):
        dna = {"spectra": {
            "formal_colloquial": 0.95,
            "abstract_concrete": 0.0,
            "cautious_assertive": 0.0,
            "analytical_narrative": 0.0,
            "serious_playful": 0.0,
            "reserved_expressive": 0.0,
            "concise_elaborate": 0.0,
        }}
        result = detect_caricature(dna)
        self.assertTrue(result["is_caricature"])
        self.assertIn("formal_colloquial", result["extreme_dimensions"])

    def test_negative_extreme_is_caricature(self):
        dna = {"spectra": {
            "formal_colloquial": -0.95,
            "abstract_concrete": 0.0,
            "cautious_assertive": 0.0,
            "analytical_narrative": 0.0,
            "serious_playful": 0.0,
            "reserved_expressive": 0.0,
            "concise_elaborate": 0.0,
        }}
        result = detect_caricature(dna)
        self.assertTrue(result["is_caricature"])

    def test_moderate_values_not_caricature(self):
        dna = {"spectra": {
            "formal_colloquial": 0.3,
            "abstract_concrete": -0.2,
            "cautious_assertive": 0.5,
            "analytical_narrative": -0.4,
            "serious_playful": 0.1,
            "reserved_expressive": -0.3,
            "concise_elaborate": 0.2,
        }}
        result = detect_caricature(dna)
        self.assertFalse(result["is_caricature"])
        self.assertEqual(result["extreme_dimensions"], [])

    def test_suggestion_includes_dimension_name(self):
        dna = {"spectra": {
            "formal_colloquial": 0.93,
            "abstract_concrete": 0.0,
            "cautious_assertive": 0.0,
            "analytical_narrative": 0.0,
            "serious_playful": 0.0,
            "reserved_expressive": 0.0,
            "concise_elaborate": 0.0,
        }}
        result = detect_caricature(dna)
        self.assertIn("formal_colloquial", result["suggestion"])

    def test_no_caricature_empty_suggestion(self):
        dna = {"spectra": {
            "formal_colloquial": 0.3,
            "abstract_concrete": 0.2,
            "cautious_assertive": 0.1,
            "analytical_narrative": -0.1,
            "serious_playful": -0.2,
            "reserved_expressive": 0.0,
            "concise_elaborate": 0.4,
        }}
        result = detect_caricature(dna)
        self.assertEqual(result["suggestion"], "")


if __name__ == "__main__":
    unittest.main()
