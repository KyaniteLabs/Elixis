"""Behaviour tests for elixis.sentiment.

Every expected value below is derived by hand from the rules in
elixis/sentiment.py, not copied from current output:

- polarity words score +1 / -1;
- a negation in the 3 tokens before the polarity word flips it (odd count only);
- an intensifier in the 2 tokens before the polarity word multiplies it by 1.5;
- the result is the mean of all polarity values, clamped to [-1, 1].

detect_intensity starts at 0.3 and adds: min(exclamations, 3) * 0.1,
min(caps words, 4) * 0.05, min(intensifiers, 3) * 0.1, a flat 0.1 when any
word repeats, and min(profundity markers, 4) * 0.05 — clamped to [0, 1].
"""

import pytest

from elixis.sentiment import detect_sentiment, detect_intensity, annotate_bead


# ---------------------------------------------------------------------------
# detect_sentiment — exact polarity arithmetic
# ---------------------------------------------------------------------------

class TestSentimentExactValues:
    def test_single_positive_word_scores_one(self):
        # "love" at +1.0, no negation or intensifier in range; mean 1.0.
        assert detect_sentiment("I love this") == 1.0

    def test_single_negative_word_scores_minus_one(self):
        assert detect_sentiment("I hate this") == -1.0

    def test_neutral_text_scores_zero(self):
        # No polarity words at all -> values empty -> 0.0.
        assert detect_sentiment("the cat sat on the mat") == 0.0

    def test_empty_string_scores_zero(self):
        assert detect_sentiment("") == 0.0

    def test_negation_flips_positive_exactly(self):
        # "don't" is 1 token before "love": odd count -> -1.0.
        assert detect_sentiment("I don't love this") == -1.0

    def test_negation_flips_negative_exactly(self):
        # "don't" directly before "hate": -(-1.0) -> +1.0.
        assert detect_sentiment("don't hate") == 1.0

    def test_double_negation_keeps_polarity(self):
        # "no" and "not" both inside the 3-token window: even count -> +1.0.
        assert detect_sentiment("no not love") == 1.0

    def test_triple_negation_flips(self):
        # All 3 window tokens negate: odd count -> flip -> -1.0.
        assert detect_sentiment("not no never love") == -1.0

    def test_mixed_polarity_mean_is_exact(self):
        # (+1.0 + -1.0) / 2 = 0.0
        assert detect_sentiment("love hate") == 0.0

    def test_three_word_mean_is_exact(self):
        # (+1.0 + 1.0 + -1.0) / 3 = 1/3
        assert detect_sentiment("love love hate") == pytest.approx(1.0 / 3.0)


class TestSentimentWindows:
    def test_negation_window_reaches_three_tokens_back(self):
        # "not" is exactly 3 tokens before "love" -> inside the window -> flip.
        assert detect_sentiment("not aa bb love") == -1.0

    def test_negation_window_excludes_fourth_token_back(self):
        # "not" is 4 tokens back -> outside the window -> polarity unchanged.
        assert detect_sentiment("not aa bb cc love") == 1.0

    def test_intensifier_window_reaches_two_tokens_back(self):
        # "very" is exactly 2 tokens before "love": 1.5, then mean with -1.0
        # from "hate" -> (1.5 - 1.0) / 2 = 0.25.
        assert detect_sentiment("aa very bb love but hate") == pytest.approx(0.25)

    def test_intensifier_window_excludes_third_token_back(self):
        # "very" is 3 tokens back -> no boost: (1.0 - 1.0) / 2 = 0.0.
        assert detect_sentiment("very aa bb love but hate") == pytest.approx(0.0)

    def test_intensifier_multiplies_by_three_halves(self):
        # "really" directly before "love": 1.5 vs -1.0 from "hate" -> 0.25.
        assert detect_sentiment("really love but hate") == pytest.approx(0.25)


class TestSentimentClamp:
    def test_intensified_positive_clamps_at_one(self):
        # 1.5 clamped to 1.0.
        assert detect_sentiment("really love") == 1.0

    def test_intensified_negative_clamps_at_minus_one(self):
        # -1.5 clamped to -1.0.
        assert detect_sentiment("really hate") == -1.0


# ---------------------------------------------------------------------------
# detect_intensity — exact additive arithmetic
# ---------------------------------------------------------------------------

class TestIntensityExactValues:
    def test_plain_text_is_base_only(self):
        # No !, no 3+-letter caps runs, no intensifiers, repeats or markers.
        assert detect_intensity("the cat sat quietly") == pytest.approx(0.3)

    def test_one_exclamation_adds_one_tenth(self):
        assert detect_intensity("wow!") == pytest.approx(0.4)

    def test_three_exclamations_add_three_tenths(self):
        assert detect_intensity("wow!!!") == pytest.approx(0.6)

    def test_exclamations_cap_at_three(self):
        # 4 marks still count 3 -> same 0.6, not 0.7.
        assert detect_intensity("wow!!!!") == pytest.approx(0.6)

    def test_three_caps_words_add_fifteen_hundredths(self):
        # MOM, LOOK, NOW each +0.05.
        assert detect_intensity("MOM LOOK NOW") == pytest.approx(0.45)

    def test_caps_words_cap_at_four(self):
        # Five 3+-letter caps runs still count 4 -> 0.3 + 0.20 = 0.50.
        assert detect_intensity("AAA BBB CCC DDD EEE") == pytest.approx(0.5)

    def test_one_intensifier_adds_one_tenth(self):
        assert detect_intensity("really special") == pytest.approx(0.4)

    def test_three_intensifiers_add_three_tenths(self):
        assert detect_intensity("really very extremely special") == pytest.approx(0.6)

    def test_intensifiers_cap_at_three(self):
        # Fourth intensifier ("deeply", not also a profundity marker) adds nothing.
        assert detect_intensity("really very extremely deeply special") == pytest.approx(0.6)

    def test_any_repeated_word_adds_flat_one_tenth(self):
        assert detect_intensity("duck duck goose") == pytest.approx(0.4)

    def test_repetition_bonus_is_flat_not_scaled(self):
        # Two distinct words repeat; still exactly one flat +0.1.
        assert detect_intensity("duck duck goose goose") == pytest.approx(0.4)

    def test_one_profundity_marker_adds_five_hundredths(self):
        assert detect_intensity("always") == pytest.approx(0.35)

    def test_profundity_markers_cap_at_four(self):
        # Four markers = +0.20; a fifth ("fundamentally") adds nothing.
        assert detect_intensity("always never everything nothing") == pytest.approx(0.5)
        assert detect_intensity("always never everything nothing fundamentally") == pytest.approx(0.5)

    def test_combined_signals_clamp_at_one(self):
        # 0.3 base + 0.3 excl (4 capped at 3) + 0.15 caps (REALLY/VERY/WOW)
        # + 0.2 intensifiers (really, very) + 0.2 profundity (4 markers)
        # = 1.15 raw, clamped to 1.0.
        assert detect_intensity("REALLY VERY WOW!!!! always never everything nothing") == pytest.approx(1.0)

    def test_empty_string_is_base_only(self):
        assert detect_intensity("") == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# annotate_bead — both annotations wired to the right key
# ---------------------------------------------------------------------------

class TestAnnotateBeadExact:
    def test_exact_pair(self):
        # sentiment: "love" at +1.0 -> 1.0.
        # intensity: 0.3 base + 0.1 for one "!" -> 0.4.
        assert annotate_bead("I love this!") == {
            "sentiment": 1.0,
            "intensity": pytest.approx(0.4),
        }
