"""Behaviour tests for elixis.expression_dna.

Every expected value below is derived by hand from the formulas in
elixis/expression_dna.py, not copied from current output:

- sentences split on runs of [.!?]; ratios divide by max(sentence_count, 1);
- phrase counting is per-phrase-present, not per-occurrence;
- each spectrum is a fixed linear combination clamped to [-1, 1];
- compare_styles is cosine similarity clamped to [0, 1], with a Manhattan
  fallback (1 - manhattan / (2 * len)) when either vector is all-zero;
- detect_caricature flags |value| strictly greater than 0.9.
"""

import pytest

from elixis.expression_dna import analyze_text, compare_styles, detect_caricature


SPECTRA_KEYS = [
    "formal_colloquial",
    "abstract_concrete",
    "cautious_assertive",
    "analytical_narrative",
    "serious_playful",
    "reserved_expressive",
    "concise_elaborate",
]


def dna(values):
    """Build a minimal DNA dict from 7 spectrum values in canonical order."""
    return {"spectra": dict(zip(SPECTRA_KEYS, values))}


# ---------------------------------------------------------------------------
# analyze_text — exact dimensions
# ---------------------------------------------------------------------------

class TestDimensionsExact:
    def test_single_word_sentence(self):
        result = analyze_text("Okay.")
        assert result["dimensions"] == {
            "avg_sentence_length": 1.0,
            "question_ratio": 0.0,
            "analogy_density": 0.0,
            "first_person_ratio": 0.0,
            "certainty_expression": 0.0,
            "transition_frequency": 0.0,
        }

    def test_question_ratio_is_questions_over_sentences(self):
        # "Why? Why not." -> 2 sentences, 1 '?' -> 0.5; avg (1+2)/2 = 1.5.
        result = analyze_text("Why? Why not.")
        assert result["dimensions"]["question_ratio"] == pytest.approx(0.5)
        assert result["dimensions"]["avg_sentence_length"] == pytest.approx(1.5)

    def test_first_person_ratio_exact(self):
        # "I think I am." -> 4 tokens, 2 first-person ("i", "i") -> 0.5.
        result = analyze_text("I think I am.")
        assert result["dimensions"]["first_person_ratio"] == pytest.approx(0.5)

    def test_single_first_person_word_is_ratio_one(self):
        # One token, one first-person hit -> 1/1 = 1.0.
        result = analyze_text("I.")
        assert result["dimensions"]["first_person_ratio"] == 1.0

    def test_certainty_expression_exact(self):
        # One certainty word, one sentence -> 1.0.
        result = analyze_text("certainly.")
        assert result["dimensions"]["certainty_expression"] == pytest.approx(1.0)

    def test_without_question_phrase_counts_once_extra(self):
        # "without question" is a phrase bonus on top of word hits: 1/1 = 1.0.
        result = analyze_text("without question.")
        assert result["dimensions"]["certainty_expression"] == pytest.approx(1.0)

    def test_transition_frequency_counts_each_phrase_once(self):
        # "however" and "therefore" both present, 2 sentences -> 2/2 = 1.0.
        result = analyze_text("however. therefore.")
        assert result["dimensions"]["transition_frequency"] == pytest.approx(1.0)

    def test_analogy_density_counts_each_phrase_once(self):
        # "like" appears twice but is one phrase: 1 phrase / 1 sentence = 1.0.
        result = analyze_text("like this and like that.")
        assert result["dimensions"]["analogy_density"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# analyze_text — exact spectra
# ---------------------------------------------------------------------------

class TestSpectraExact:
    def test_minimal_sentence_full_profile(self):
        # avg = 1.0 word/sentence; nothing else present.
        # formal: 1/15 -> 2/15 - 1; abstract: 0 -> -1; cautious/analytical: 0;
        # serious: 0.5; reserved_expressive: clamp(1 - 0 - 0 + 0.5) = clamp(1.5) = 1.0;
        # concise_elaborate: (0 + 1/30) - 1/(1 + 1/10).
        result = analyze_text("Okay.")
        s = result["spectra"]
        assert s["formal_colloquial"] == pytest.approx(2.0 * (1.0 / 15.0) - 1.0)
        assert s["abstract_concrete"] == -1.0
        assert s["cautious_assertive"] == 0.0
        assert s["analytical_narrative"] == 0.0
        assert s["serious_playful"] == 0.5
        assert s["reserved_expressive"] == 1.0
        assert s["concise_elaborate"] == pytest.approx(1.0 / 30.0 - 1.0 / 1.1)

    def test_formal_long_question_scores_zero(self):
        # One 16-word sentence ending in '?': avg 16.0 > 15 -> formal branch
        # 1.0; question_ratio 1.0 -> formal = 1.0 - 0.5 = 0.5 -> spectrum 0.0.
        words = " ".join(f"w{n}" for n in range(1, 17)) + "?"
        result = analyze_text(words)
        assert result["dimensions"]["avg_sentence_length"] == 16.0
        assert result["dimensions"]["question_ratio"] == 1.0
        assert result["spectra"]["formal_colloquial"] == pytest.approx(0.0)

    def test_formal_threshold_at_fifteen_words(self):
        # A single 15-word sentence, no other features: avg = 15.0 exactly,
        # so formal_score = 1.0 on both branches -> formal_colloquial = 1.0.
        words = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen."
        result = analyze_text(words)
        assert result["dimensions"]["avg_sentence_length"] == 15.0
        assert result["spectra"]["formal_colloquial"] == 1.0

    def test_question_penalty_is_half_the_ratio(self):
        # 2 sentences ("Why", 11 neutral words): avg = 6.0, question_ratio 0.5.
        # formal = 6/15 - 0.25 = 0.15 -> formal_colloquial = -0.7.
        text = "Why? aa bb cc dd ee ff gg hh ii jj kk."
        result = analyze_text(text)
        assert result["spectra"]["formal_colloquial"] == pytest.approx(
            2.0 * (6.0 / 15.0 - 0.5 * 0.5) - 1.0
        )

    def test_abstract_from_two_analogy_phrases(self):
        # "like" and "akin to" present, 2 sentences -> density 1.0;
        # abstract = 1.0 * 0.5 + 0 -> 0.5 -> spectrum 0.0.
        result = analyze_text("It is like a bridge. Also akin to a spring.")
        assert result["spectra"]["abstract_concrete"] == pytest.approx(0.0)

    def test_abstract_from_philosophical_word(self):
        # 1 philosophical word / 1 sentence: abstract = 0 + 1.0 -> 1.0;
        # analytical = 0 + 1.0, narrative 0 -> analytical_narrative 1.0.
        result = analyze_text("ontology.")
        assert result["spectra"]["abstract_concrete"] == 1.0
        assert result["spectra"]["analytical_narrative"] == 1.0

    def test_philosophical_word_dilutes_over_three_sentences(self):
        # 1 philosophical word over 3 sentences: abstract = 1/3 ->
        # spectrum = clamp(2/3 - 1) = -1/3.
        result = analyze_text("ontology. plain. words.")
        assert result["spectra"]["abstract_concrete"] == pytest.approx(-1.0 / 3.0)

    def test_multi_word_philosophical_phrase_counts(self):
        # "a priori" only matches as a substring phrase: 1/1 -> abstract 1.0.
        result = analyze_text("This is a priori reasoning.")
        assert result["spectra"]["abstract_concrete"] == 1.0

    def test_multi_word_phrase_dilutes_over_three_sentences(self):
        # Same 1/3 dilution via the phrase hit alone.
        result = analyze_text("This is a priori reasoning. plain. words.")
        assert result["spectra"]["abstract_concrete"] == pytest.approx(-1.0 / 3.0)

    def test_cautious_assertive_zero_when_balanced(self):
        # "perhaps" hedges, "clearly" asserts; 1 each over 2 sentences -> 0.0.
        result = analyze_text("perhaps. clearly.")
        assert result["spectra"]["cautious_assertive"] == pytest.approx(0.0)

    def test_single_hedge_saturates_minus_one(self):
        # "perhaps." -> 1 sentence, 1 hedge: caution 1.0, assert 0 -> -1.0.
        result = analyze_text("perhaps.")
        assert result["spectra"]["cautious_assertive"] == -1.0

    def test_without_question_pushes_assertive_to_one(self):
        result = analyze_text("without question.")
        assert result["spectra"]["cautious_assertive"] == 1.0

    def test_analytical_minus_narrative_exact(self):
        # "however. then." -> 2 sentences: transition freq 0.5, temporal 0.5,
        # philosophical 0. analytical = 0.25, narrative = 0.5 -> -0.25.
        result = analyze_text("however. then.")
        assert result["spectra"]["analytical_narrative"] == pytest.approx(-0.25)

    def test_philosophical_word_drives_analytical_third(self):
        # "ontology. plain. words." -> 3 sentences, philosophical 1, no
        # transitions/temporals: analytical = 1/3, narrative 0 -> 1/3.
        result = analyze_text("ontology. plain. words.")
        assert result["spectra"]["analytical_narrative"] == pytest.approx(1.0 / 3.0)

    def test_pure_narrative_saturates_minus_one(self):
        # "then." -> 1 sentence, 1 temporal marker: narrative 1.0,
        # analytical 0 -> clamp(-1.0) = -1.0.
        result = analyze_text("then.")
        assert result["spectra"]["analytical_narrative"] == -1.0

    def test_serious_playful_exact(self):
        # "ironically! wow!" -> 2 sentences, 1 playful word, 2 '!':
        # playful = 1/2 + (2/2) * 0.3 = 0.8 -> 0.5 - 0.8 = -0.3.
        result = analyze_text("ironically! wow!")
        assert result["spectra"]["serious_playful"] == pytest.approx(-0.3)

    def test_single_playful_word_saturates_minus_half(self):
        # "ironically." -> 1 sentence, 1 playful word, no '!':
        # playful = 1.0 -> 0.5 - 1.0 = -0.5.
        result = analyze_text("ironically.")
        assert result["spectra"]["serious_playful"] == pytest.approx(-0.5)

    def test_single_exclamation_without_playful_words(self):
        # "wow!" -> 1 sentence, no playful word, 1 '!':
        # playful = 0 + (1/1) * 0.3 = 0.3 -> 0.5 - 0.3 = 0.2.
        result = analyze_text("wow!")
        assert result["spectra"]["serious_playful"] == pytest.approx(0.2)

    def test_reserved_expressive_exact(self):
        # "I see the mountain here." -> fpr = 1/5 = 0.2, no emotional words.
        # reserved = 1 - 0.2*5 = 0.0; expressive = 0.2*3 = 0.6;
        # spectrum = clamp(0.0 - 0.6 + 0.5) = -0.1.
        result = analyze_text("I see the mountain here.")
        assert result["spectra"]["reserved_expressive"] == pytest.approx(-0.1)

    def test_emotional_weight_is_ten_over_words(self):
        # 13 tokens, no first person, 1 emotional word ("joyful"):
        # expressive = 10/13; reserved = 1.0;
        # spectrum = clamp(1.0 - 10/13 + 0.5) = 1.5 - 10/13.
        text = "joyful and calm and bright and quiet and soft and clear skies today."
        result = analyze_text(text)
        assert result["spectra"]["reserved_expressive"] == pytest.approx(1.5 - 10.0 / 13.0)

    def test_concise_elaborate_exact(self):
        # "however." -> avg 1.0, transition freq 1.0:
        # concise = 1/1.1; elaborate = 0.5 + 1/30;
        # spectrum = 0.5 + 1/30 - 1/1.1.
        result = analyze_text("however.")
        assert result["spectra"]["concise_elaborate"] == pytest.approx(0.5 + 1.0 / 30.0 - 1.0 / 1.1)

    def test_spectra_key_order_is_canonical(self):
        # The spectra dict is built from a fixed key list; order is part of
        # the contract because compare_styles consumes values() positionally.
        result = analyze_text("Okay.")
        assert list(result["spectra"].keys()) == SPECTRA_KEYS


# ---------------------------------------------------------------------------
# compare_styles — exact cosine and fallback
# ---------------------------------------------------------------------------

class TestCompareStylesExact:
    def test_identical_vectors_score_one(self):
        v = dna([0.5, -0.25, 0.75, -0.5, 0.1, -0.1, 0.0])
        assert compare_styles(v, dna([0.5, -0.25, 0.75, -0.5, 0.1, -0.1, 0.0])) == pytest.approx(1.0)

    def test_identical_vectors_clamp_fp_overshoot_exactly(self):
        # dot/(|a||a|) can round a hair above 1.0 for this vector
        # (fl(sqrt(S))**2 < S), so the upper clamp must pull it back to
        # exactly 1.0 — assert with plain equality, not approx.
        v = dna([1.0, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0])
        assert compare_styles(v, dna([1.0, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0])) == 1.0

    def test_known_cosine(self):
        # a = [1,0,1,...], b = [1,1,0,...]: dot 1, |a||b| = sqrt(2)*sqrt(2) = 2
        # -> cosine 0.5.
        a = dna([1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0])
        b = dna([1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert compare_styles(a, b) == pytest.approx(0.5)

    def test_orthogonal_vectors_score_zero(self):
        a = dna([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        b = dna([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert compare_styles(a, b) == pytest.approx(0.0)

    def test_opposite_vectors_clamp_to_zero(self):
        # Raw cosine is -1.0; the clamp keeps similarity in [0, 1].
        a = dna([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        b = dna([-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert compare_styles(a, b) == pytest.approx(0.0)

    def test_zero_vector_falls_back_to_manhattan(self):
        # |a| = 0 -> fallback: manhattan = 7, max_dist = 2*7 = 14 -> 0.5.
        zero = dna([0.0] * 7)
        ones = dna([1.0] * 7)
        assert compare_styles(zero, ones) == pytest.approx(0.5)

    def test_zero_second_vector_also_falls_back(self):
        # Mirrored argument order: |b| = 0 must not reach the cosine divide.
        assert compare_styles(dna([1.0] * 7), dna([0.0] * 7)) == pytest.approx(0.5)

    def test_two_zero_vectors_score_one(self):
        zero = dna([0.0] * 7)
        assert compare_styles(zero, dna([0.0] * 7)) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# detect_caricature — strict threshold and suggestion format
# ---------------------------------------------------------------------------

class TestDetectCaricatureExact:
    def test_moderate_values_are_not_caricature(self):
        result = detect_caricature(dna([0.5] * 7))
        assert result == {
            "is_caricature": False,
            "extreme_dimensions": [],
            "suggestion": "",
        }

    def test_zero_point_nine_exactly_is_not_extreme(self):
        # Threshold is strictly greater than 0.9.
        result = detect_caricature(dna([0.9] + [0.0] * 6))
        assert result["is_caricature"] is False

    def test_extreme_dimension_reported_with_suggestion(self):
        result = detect_caricature(dna([0.99] + [0.0] * 6))
        assert result["is_caricature"] is True
        assert result["extreme_dimensions"] == ["formal_colloquial"]
        # "{:.1f}".format(0.99) == "1.0"
        assert result["suggestion"] == "Soften formal_colloquial from 1.0 toward center"

    def test_negative_extreme_counts(self):
        result = detect_caricature(dna([0.0, -0.99] + [0.0] * 5))
        assert result["is_caricature"] is True
        assert result["extreme_dimensions"] == ["abstract_concrete"]
