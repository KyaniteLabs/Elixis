"""Tests for soulcraft.sentiment — sentiment/intensity detection and annotation."""

import pytest

from soulcraft.sentiment import (
    POSITIVE_WORDS,
    NEGATIVE_WORDS,
    NEGATION_WORDS,
    INTENSIFIERS,
    PROFUNDITY_MARKERS,
    detect_sentiment,
    detect_intensity,
    annotate_bead,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_positive_words_nonempty(self):
        assert len(POSITIVE_WORDS) > 0
        assert "love" in POSITIVE_WORDS
        assert "great" in POSITIVE_WORDS

    def test_negative_words_nonempty(self):
        assert len(NEGATIVE_WORDS) > 0
        assert "hate" in NEGATIVE_WORDS
        assert "fear" in NEGATIVE_WORDS

    def test_negation_words_nonempty(self):
        assert len(NEGATION_WORDS) > 0
        assert "not" in NEGATION_WORDS
        assert "never" in NEGATION_WORDS

    def test_intensifiers_nonempty(self):
        assert len(INTENSIFIERS) > 0
        assert "very" in INTENSIFIERS
        assert "extremely" in INTENSIFIERS

    def test_profundity_markers_nonempty(self):
        assert len(PROFUNDITY_MARKERS) > 0
        assert "always" in PROFUNDITY_MARKERS


# ---------------------------------------------------------------------------
# detect_sentiment
# ---------------------------------------------------------------------------

class TestDetectSentiment:
    def test_positive_text(self):
        score = detect_sentiment("I love this beautiful music")
        assert score > 0.0

    def test_negative_text(self):
        score = detect_sentiment("I hate this disgusting thing")
        assert score < 0.0

    def test_neutral_text(self):
        score = detect_sentiment("the cat sat on the mat")
        assert score == 0.0

    def test_empty_string(self):
        assert detect_sentiment("") == 0.0

    def test_negation_flips_positive_to_negative(self):
        normal = detect_sentiment("I love this")
        negated = detect_sentiment("I don't love this")
        assert normal > 0.0
        assert negated < 0.0

    def test_negation_flips_negative_to_positive(self):
        normal = detect_sentiment("I hate this")
        negated = detect_sentiment("I don't hate this")
        assert normal < 0.0
        assert negated > 0.0

    def test_intensifier_boosts_score(self):
        # "love" alone = 1.0 (clamped). With mixed sentiment the baseline
        # is lower, and intensifier on the positive word raises the average.
        normal = detect_sentiment("I love this but I fear that")
        intensified = detect_sentiment("I really love this but I fear that")
        assert intensified > normal

    def test_multiple_positive_words(self):
        score = detect_sentiment("I love this amazing brilliant work")
        assert score > 0.0

    def test_mixed_sentiment(self):
        score = detect_sentiment("I love it but I hate the ending")
        assert -1.0 <= score <= 1.0

    def test_result_clamped_to_range(self):
        # Even with many intensifiers and words, stays in [-1, 1]
        score = detect_sentiment(
            "I really extremely absolutely love this incredibly amazing beautiful brilliant work"
        )
        assert -1.0 <= score <= 1.0

    def test_never_negation(self):
        score = detect_sentiment("I never like this")
        assert score < 0.0

    def test_barely_negation(self):
        score = detect_sentiment("I barely like this")
        assert score < 0.0

    def test_multiple_negations_in_window(self):
        score = detect_sentiment("I do not never hate this")
        # Double negation should still flip
        assert -1.0 <= score <= 1.0

    def test_result_is_float(self):
        score = detect_sentiment("test")
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# detect_intensity
# ---------------------------------------------------------------------------

class TestDetectIntensity:
    def test_base_intensity_for_plain_text(self):
        intensity = detect_intensity("a quick brown fox jumps over lazy dog")
        assert intensity == pytest.approx(0.3)

    def test_exclamation_marks_increase_intensity(self):
        base = detect_intensity("I like this")
        excited = detect_intensity("I like this!!!")
        assert excited > base

    def test_caps_words_increase_intensity(self):
        base = detect_intensity("I like this")
        caps = detect_intensity("I REALLY like this")
        assert caps > base

    def test_intensifier_words_increase_intensity(self):
        base = detect_intensity("I like this")
        intensified = detect_intensity("I really like this")
        assert intensified > base

    def test_repeated_words_increase_intensity(self):
        base = detect_intensity("I like cats")
        repeated = detect_intensity("I like cats cats")
        assert repeated > base

    def test_profundity_markers_increase_intensity(self):
        base = detect_intensity("I like this thing")
        profound = detect_intensity("I like this thing always fundamentally")
        assert profound > base

    def test_intensity_clamped_to_0_1(self):
        # Even with maximum signals
        intensity = detect_intensity("I REALLY VERY EXTREMELY ABSOLUTELY love this!!!!")
        assert 0.0 <= intensity <= 1.0

    def test_empty_string(self):
        intensity = detect_intensity("")
        assert 0.0 <= intensity <= 1.0
        assert intensity == pytest.approx(0.3)

    def test_many_exclamation_marks_capped(self):
        intensity = detect_intensity("wow!!!!!!")
        assert intensity <= 1.0

    def test_result_is_float(self):
        intensity = detect_intensity("test")
        assert isinstance(intensity, float)


# ---------------------------------------------------------------------------
# annotate_bead
# ---------------------------------------------------------------------------

class TestAnnotateBead:
    def test_returns_dict_with_both_keys(self):
        result = annotate_bead("I love music")
        assert "sentiment" in result
        assert "intensity" in result

    def test_sentiment_is_float(self):
        result = annotate_bead("I love music")
        assert isinstance(result["sentiment"], float)

    def test_intensity_is_float(self):
        result = annotate_bead("I love music")
        assert isinstance(result["intensity"], float)

    def test_sentiment_in_range(self):
        result = annotate_bead("I love music")
        assert -1.0 <= result["sentiment"] <= 1.0

    def test_intensity_in_range(self):
        result = annotate_bead("I love music")
        assert 0.0 <= result["intensity"] <= 1.0

    def test_empty_string(self):
        result = annotate_bead("")
        assert result["sentiment"] == 0.0
        assert result["intensity"] == pytest.approx(0.3)

    def test_positive_text(self):
        result = annotate_bead("I really love this amazing work!")
        assert result["sentiment"] > 0.0
        assert result["intensity"] > 0.3

    def test_negative_text(self):
        result = annotate_bead("I hate this disgusting mess")
        assert result["sentiment"] < 0.0
