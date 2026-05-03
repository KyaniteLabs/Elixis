"""Tests for fugax.resolution — name normalization, similarity, dedup, entity resolution."""


from fugax.bead import Bead
from fugax.resolution import (
    normalize_name,
    name_similarity,
    _levenshtein,
    deduplicate_beads,
    resolve_entities,
)


# ---------------------------------------------------------------------------
# normalize_name
# ---------------------------------------------------------------------------

class TestNormalizeName:
    def test_strips_leading_double_quotes(self):
        assert normalize_name('"Mozart"') == "Mozart"

    def test_strips_leading_single_quotes(self):
        assert normalize_name("'Beethoven'") == "Beethoven"

    def test_strips_leading_dashes(self):
        assert normalize_name("-Bach") == "Bach"

    def test_strips_trailing_dashes(self):
        assert normalize_name("Bach-") == "Bach"

    def test_strips_mixed_quotes_and_dashes(self):
        assert normalize_name('"\'-Mozart-\'"') == "Mozart"

    def test_normalizes_internal_whitespace(self):
        assert normalize_name("Ludwig   van    Beethoven") == "Ludwig van Beethoven"

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_name("  Mozart  ") == "Mozart"

    def test_empty_string(self):
        assert normalize_name("") == ""

    def test_only_whitespace(self):
        assert normalize_name("   ") == ""

    def test_only_quotes(self):
        assert normalize_name('""') == ""

    def test_name_without_changing(self):
        assert normalize_name("Mozart") == "Mozart"


# ---------------------------------------------------------------------------
# _levenshtein
# ---------------------------------------------------------------------------

class TestLevenshtein:
    def test_identical_strings(self):
        assert _levenshtein("abc", "abc") == 0

    def test_completely_different(self):
        assert _levenshtein("abc", "xyz") == 3

    def test_empty_strings(self):
        assert _levenshtein("", "") == 0

    def test_one_empty(self):
        assert _levenshtein("abc", "") == 3
        assert _levenshtein("", "abc") == 3

    def test_single_edit(self):
        assert _levenshtein("cat", "bat") == 1

    def test_insertion(self):
        assert _levenshtein("abc", "abcd") == 1

    def test_deletion(self):
        assert _levenshtein("abcd", "abc") == 1

    def test_swapped_order(self):
        assert _levenshtein("abc", "xyz") == _levenshtein("xyz", "abc")


# ---------------------------------------------------------------------------
# name_similarity
# ---------------------------------------------------------------------------

class TestNameSimilarity:
    def test_identical_names(self):
        assert name_similarity("Mozart", "Mozart") == 1.0

    def test_case_insensitive_identical(self):
        assert name_similarity("mozart", "MOZART") == 1.0

    def test_empty_strings(self):
        assert name_similarity("", "") == 1.0

    def test_one_empty(self):
        assert name_similarity("Mozart", "") == 0.0
        assert name_similarity("", "Mozart") == 0.0

    def test_substring_match(self):
        score = name_similarity("Mozart", "Wolfgang Mozart")
        assert score == 0.85

    def test_reverse_substring(self):
        score = name_similarity("Wolfgang Mozart", "Mozart")
        assert score == 0.85

    def test_typo_level_similarity(self):
        score = name_similarity("Beethoven", "Beethovan")
        assert score >= 0.8

    def test_completely_different(self):
        score = name_similarity("abc", "xyz")
        assert score < 0.5

    def test_prefix_match(self):
        score = name_similarity("Beethoven", "Beethov")
        assert score >= 0.7

    def test_normalizes_before_compare(self):
        score = name_similarity('"Mozart"', "'Mozart'")
        assert score == 1.0

    def test_result_in_range(self):
        score = name_similarity("something", "other")
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# deduplicate_beads
# ---------------------------------------------------------------------------

class TestDeduplicateBeads:
    def test_empty_list(self):
        assert deduplicate_beads([]) == []

    def test_single_bead_unchanged(self):
        b = Bead(name="Mozart", canonical="Mozart", confidence=0.9)
        result = deduplicate_beads([b])
        assert len(result) == 1
        assert result[0].canonical == "Mozart"

    def test_keeps_higher_confidence_bead(self):
        a = Bead(name="Mozart", canonical="Mozart", confidence=0.7)
        b = Bead(name="Mozart", canonical="Mozart", confidence=0.9)
        result = deduplicate_beads([a, b])
        assert len(result) == 1
        assert result[0].confidence == 0.9

    def test_merges_themes(self):
        a = Bead(name="Mozart", canonical="Mozart", confidence=0.9, themes=["power"])
        b = Bead(name="Mozart", canonical="Mozart", confidence=0.5, themes=["wisdom"])
        result = deduplicate_beads([a, b])
        assert "power" in result[0].themes
        assert "wisdom" in result[0].themes

    def test_merges_traits(self):
        a = Bead(name="Mozart", canonical="Mozart", confidence=0.9, traits=["genius"])
        b = Bead(name="Mozart", canonical="Mozart", confidence=0.5, traits=["prolific"])
        result = deduplicate_beads([a, b])
        assert "genius" in result[0].traits
        assert "prolific" in result[0].traits

    def test_merges_related(self):
        a = Bead(name="Mozart", canonical="Mozart", confidence=0.9, related=["Haydn"])
        b = Bead(name="Mozart", canonical="Mozart", confidence=0.5, related=["Beethoven"])
        result = deduplicate_beads([a, b])
        assert "Haydn" in result[0].related
        assert "Beethoven" in result[0].related

    def test_merges_enrichment(self):
        a = Bead(name="Mozart", canonical="Mozart", confidence=0.9,
                 enrichment={"wikipedia": "composer"})
        b = Bead(name="Mozart", canonical="Mozart", confidence=0.5,
                 enrichment={"source": "encyclopedia"})
        result = deduplicate_beads([a, b])
        assert result[0].enrichment["wikipedia"] == "composer"
        assert result[0].enrichment["source"] == "encyclopedia"

    def test_winner_enrichment_overwrites_loser(self):
        a = Bead(name="Mozart", canonical="Mozart", confidence=0.9,
                 enrichment={"key": "winner_val"})
        b = Bead(name="Mozart", canonical="Mozart", confidence=0.5,
                 enrichment={"key": "loser_val"})
        result = deduplicate_beads([a, b])
        assert result[0].enrichment["key"] == "winner_val"

    def test_keeps_max_sentiment(self):
        a = Bead(name="X", canonical="X", confidence=0.9, sentiment=0.3)
        b = Bead(name="X", canonical="X", confidence=0.5, sentiment=0.8)
        result = deduplicate_beads([a, b])
        assert result[0].sentiment == 0.8

    def test_keeps_max_intensity(self):
        a = Bead(name="X", canonical="X", confidence=0.9, intensity=0.4)
        b = Bead(name="X", canonical="X", confidence=0.5, intensity=0.9)
        result = deduplicate_beads([a, b])
        assert result[0].intensity == 0.9

    def test_different_beads_not_merged(self):
        a = Bead(name="Mozart", canonical="Mozart", confidence=0.9)
        b = Bead(name="Beethoven", canonical="Beethoven", confidence=0.9)
        result = deduplicate_beads([a, b])
        assert len(result) == 2

    def test_similar_names_merged(self):
        a = Bead(name="Beethoven", canonical="Beethoven", confidence=0.9)
        b = Bead(name="Beethovan", canonical="Beethovan", confidence=0.5)
        result = deduplicate_beads([a, b])
        assert len(result) == 1

    def test_three_beads_two_similar(self):
        a = Bead(name="Mozart", canonical="Mozart", confidence=0.9)
        b = Bead(name="Mozart", canonical="Mozart", confidence=0.5)
        c = Bead(name="Bach", canonical="Bach", confidence=0.9)
        result = deduplicate_beads([a, b, c])
        assert len(result) == 2

    def test_preserves_unrelated_beads_order(self):
        a = Bead(name="A", canonical="Alpha", confidence=0.5)
        b = Bead(name="B", canonical="Beta", confidence=0.5)
        c = Bead(name="C", canonical="Gamma", confidence=0.5)
        result = deduplicate_beads([a, b, c])
        assert len(result) == 3
        names = [r.canonical for r in result]
        assert "Alpha" in names
        assert "Beta" in names
        assert "Gamma" in names


# ---------------------------------------------------------------------------
# resolve_entities
# ---------------------------------------------------------------------------

class TestResolveEntities:
    def test_empty_list(self):
        assert resolve_entities([]) == []

    def test_single_name(self):
        result = resolve_entities(["Mozart"])
        assert len(result) == 1
        assert result[0]["canonical"] == "Mozart"
        assert result[0]["original"] == "Mozart"
        assert result[0]["aliases"] == []

    def test_groups_similar_names(self):
        result = resolve_entities(["Mozart", "mozart"])
        assert len(result) == 1
        assert result[0]["canonical"] in ("Mozart", "mozart")

    def test_keeps_longest_as_canonical(self):
        result = resolve_entities(["Mozart", "Wolfgang Mozart"])
        assert len(result) == 1
        assert result[0]["canonical"] == "Wolfgang Mozart"

    def test_different_names_separate(self):
        result = resolve_entities(["Mozart", "Beethoven"])
        assert len(result) == 2

    def test_aliases_excludes_canonical(self):
        result = resolve_entities(["Mozart", "mozart", "W.A. Mozart"])
        for entry in result:
            assert entry["canonical"] not in entry["aliases"]

    def test_original_is_first_occurrence(self):
        result = resolve_entities(["mozart", "Mozart"])
        assert result[0]["original"] == "mozart"

    def test_typo_grouping(self):
        result = resolve_entities(["Beethoven", "Beethovan"])
        assert len(result) == 1

    def test_three_similar_names(self):
        result = resolve_entities(["Mozart", "mozart", "MOZART"])
        assert len(result) == 1

    def test_result_structure(self):
        result = resolve_entities(["Mozart"])
        entry = result[0]
        assert "original" in entry
        assert "canonical" in entry
        assert "aliases" in entry
        assert isinstance(entry["aliases"], list)

    def test_dissimilar_names_stay_separate(self):
        result = resolve_entities(["abc", "xyz"])
        assert len(result) == 2

    def test_mixed_similar_and_dissimilar(self):
        result = resolve_entities(["Mozart", "mozart", "Beethoven"])
        assert len(result) == 2
