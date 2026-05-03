"""Tests for elixis.bead — Bead class, _clamp helper, and constants."""


from elixis.bead import (
    VALID_TYPES,
    VALID_DOMAINS,
    VALID_THEMES,
    VALID_PROVENANCE,
    _clamp,
    Bead,
)


# ---------------------------------------------------------------------------
# _clamp helper
# ---------------------------------------------------------------------------

class TestClamp:
    def test_value_within_range_unchanged(self):
        assert _clamp(0.5, 0.0, 1.0) == 0.5

    def test_clamp_low(self):
        assert _clamp(-3.0, -1.0, 1.0) == -1.0

    def test_clamp_high(self):
        assert _clamp(5.0, 0.0, 1.0) == 1.0

    def test_clamp_at_boundaries(self):
        assert _clamp(0.0, 0.0, 1.0) == 0.0
        assert _clamp(1.0, 0.0, 1.0) == 1.0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_valid_types_contains_expected(self):
        expected = {"character", "person", "historical_figure", "work", "concept",
                     "archetype", "mythological", "place"}
        assert VALID_TYPES == expected

    def test_valid_domains_nonempty(self):
        assert len(VALID_DOMAINS) > 0
        assert "music" in VALID_DOMAINS
        assert "philosophy" in VALID_DOMAINS

    def test_valid_themes_nonempty(self):
        assert len(VALID_THEMES) > 0
        assert "transformation" in VALID_THEMES

    def test_valid_provenance_includes_empty(self):
        assert "" in VALID_PROVENANCE
        assert "first-hand" in VALID_PROVENANCE


# ---------------------------------------------------------------------------
# Bead construction
# ---------------------------------------------------------------------------

class TestBeadConstruction:
    def test_default_construction(self):
        b = Bead()
        assert b.name == ""
        assert b.canonical == ""
        assert b.type == "concept"
        assert b.domains == []
        assert b.themes == []
        assert b.traits == []
        assert b.sentiment == 0.0
        assert b.intensity == 0.5
        assert b.confidence == 0.5
        assert b.provenance == ""
        assert b.enrichment == {}
        assert b.related == []

    def test_full_construction(self):
        b = Bead(
            name="Mozart",
            canonical="Wolfgang Amadeus Mozart",
            type="historical_figure",
            domains=["music"],
            themes=["creation", "wisdom"],
            traits=["genius"],
            sentiment=0.8,
            intensity=0.9,
            confidence=0.7,
            provenance="first-hand",
            enrichment={"wikipedia": "Austrian composer"},
            related=["Beethoven"],
        )
        assert b.name == "Mozart"
        assert b.canonical == "Wolfgang Amadeus Mozart"
        assert b.type == "historical_figure"
        assert b.domains == ["music"]
        assert b.themes == ["creation", "wisdom"]
        assert b.traits == ["genius"]
        assert b.sentiment == 0.8
        assert b.intensity == 0.9
        assert b.confidence == 0.7
        assert b.provenance == "first-hand"
        assert b.enrichment == {"wikipedia": "Austrian composer"}
        assert b.related == ["Beethoven"]

    def test_canonical_defaults_to_name(self):
        b = Bead(name="Bach")
        assert b.canonical == "Bach"

    def test_canonical_explicit_overrides_name(self):
        b = Bead(name="JSB", canonical="Johann Sebastian Bach")
        assert b.canonical == "Johann Sebastian Bach"

    def test_invalid_type_falls_back_to_concept(self):
        b = Bead(name="X", type="invalid_type")
        assert b.type == "concept"

    def test_invalid_provenance_falls_back_to_empty(self):
        b = Bead(name="X", provenance="imagined")
        assert b.provenance == ""

    def test_lists_are_copied(self):
        domains = ["music"]
        b = Bead(name="X", domains=domains)
        domains.append("science")
        assert b.domains == ["music"]

    def test_enrichment_is_copied(self):
        enrich = {"k": "v"}
        b = Bead(name="X", enrichment=enrich)
        enrich["k2"] = "v2"
        assert b.enrichment == {"k": "v"}


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------

class TestBeadValidate:
    def test_clamp_sentiment(self):
        b = Bead(name="X", sentiment=2.0)
        b.validate()
        assert b.sentiment == 1.0

    def test_clamp_sentiment_negative(self):
        b = Bead(name="X", sentiment=-3.0)
        b.validate()
        assert b.sentiment == -1.0

    def test_clamp_intensity_high(self):
        b = Bead(name="X", intensity=5.0)
        b.validate()
        assert b.intensity == 1.0

    def test_clamp_intensity_negative(self):
        b = Bead(name="X", intensity=-1.0)
        b.validate()
        assert b.intensity == 0.0

    def test_clamp_confidence_high(self):
        b = Bead(name="X", confidence=10.0)
        b.validate()
        assert b.confidence == 1.0

    def test_clamp_confidence_negative(self):
        b = Bead(name="X", confidence=-0.5)
        b.validate()
        assert b.confidence == 0.0

    def test_validate_fixes_invalid_type(self):
        b = Bead(name="X")
        b.type = "nonsense"
        b.validate()
        assert b.type == "concept"

    def test_validate_fixes_invalid_provenance(self):
        b = Bead(name="X")
        b.provenance = "dreamed"
        b.validate()
        assert b.provenance == ""

    def test_validate_returns_self(self):
        b = Bead(name="X")
        result = b.validate()
        assert result is b

    def test_valid_values_unchanged(self):
        b = Bead(name="X", sentiment=0.3, intensity=0.6, confidence=0.8)
        b.validate()
        assert b.sentiment == 0.3
        assert b.intensity == 0.6
        assert b.confidence == 0.8


# ---------------------------------------------------------------------------
# to_dict / from_dict roundtrip
# ---------------------------------------------------------------------------

class TestBeadSerialization:
    def test_to_dict_keys(self):
        b = Bead(name="Test")
        d = b.to_dict()
        expected_keys = {
            "name", "canonical", "type", "domains", "themes", "traits",
            "sentiment", "intensity", "confidence", "provenance",
            "enrichment", "related",
        }
        assert set(d.keys()) == expected_keys

    def test_roundtrip(self):
        original = Bead(
            name="Beethoven",
            canonical="Ludwig van Beethoven",
            type="historical_figure",
            domains=["music"],
            themes=["struggle", "creation"],
            traits=["deaf", "brilliant"],
            sentiment=-0.2,
            intensity=0.9,
            confidence=0.85,
            provenance="first-hand",
            enrichment={"wikipedia": "German composer"},
            related=["Mozart"],
        )
        d = original.to_dict()
        restored = Bead.from_dict(d)
        assert restored.name == original.name
        assert restored.canonical == original.canonical
        assert restored.type == original.type
        assert restored.domains == original.domains
        assert restored.themes == original.themes
        assert restored.traits == original.traits
        assert restored.sentiment == original.sentiment
        assert restored.intensity == original.intensity
        assert restored.confidence == original.confidence
        assert restored.provenance == original.provenance
        assert restored.enrichment == original.enrichment
        assert restored.related == original.related

    def test_from_dict_missing_keys_uses_defaults(self):
        d = {}
        b = Bead.from_dict(d)
        assert b.name == ""
        assert b.canonical == ""
        assert b.type == "concept"
        assert b.domains is None or b.domains == []
        assert b.sentiment == 0.0
        assert b.intensity == 0.5
        assert b.confidence == 0.5
        assert b.provenance == ""

    def test_from_dict_partial(self):
        d = {"name": "X", "type": "character"}
        b = Bead.from_dict(d)
        assert b.name == "X"
        assert b.type == "character"
        assert b.canonical == "X"  # canonical falls back to name

    def test_from_dict_with_none_collections(self):
        d = {"name": "X", "domains": None, "themes": None, "enrichment": None}
        b = Bead.from_dict(d)
        assert b.domains == []
        assert b.themes == []
        assert b.enrichment == {}


# ---------------------------------------------------------------------------
# update_from_dict
# ---------------------------------------------------------------------------

class TestBeadUpdateFromDict:
    def test_adds_wikipedia_description(self):
        b = Bead(name="Mozart")
        b.update_from_dict({"description": "Austrian composer"})
        assert b.enrichment["wikipedia"] == "Austrian composer"

    def test_overwrites_existing_wikipedia_desc(self):
        b = Bead(name="Mozart", enrichment={"wikipedia": "old"})
        b.update_from_dict({"description": "new desc"})
        assert b.enrichment["wikipedia"] == "new desc"

    def test_merges_themes(self):
        b = Bead(name="X", themes=["power", "wisdom"])
        b.update_from_dict({"themes": ["creation", "power"]})
        assert set(b.themes) == {"power", "wisdom", "creation"}

    def test_adds_enrichment_keys(self):
        b = Bead(name="X")
        b.update_from_dict({
            "source": "wiki",
            "knowledge_base": "music",
            "big_five": {"O": 0.9},
        })
        assert b.enrichment["source"] == "wiki"
        assert b.enrichment["knowledge_base"] == "music"
        assert b.enrichment["big_five"] == {"O": 0.9}

    def test_does_not_overwrite_existing_enrichment_keys(self):
        b = Bead(name="X", enrichment={"source": "original"})
        b.update_from_dict({"source": "new"})
        assert b.enrichment["source"] == "original"

    def test_empty_data_no_crash(self):
        b = Bead(name="X", themes=["a"])
        b.update_from_dict({})
        assert b.themes == ["a"]
        assert b.enrichment == {}

    def test_returns_self(self):
        b = Bead(name="X")
        result = b.update_from_dict({"description": "test"})
        assert result is b

    def test_empty_description_not_stored(self):
        b = Bead(name="X")
        b.update_from_dict({"description": ""})
        assert "wikipedia" not in b.enrichment

    def test_empty_themes_list_not_merged(self):
        b = Bead(name="X", themes=["power"])
        b.update_from_dict({"themes": []})
        assert b.themes == ["power"]


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------

class TestBeadRepr:
    def test_repr_format(self):
        b = Bead(name="Mozart", canonical="Mozart", type="historical_figure")
        assert repr(b) == "Bead('Mozart', type='historical_figure')"


# ---------------------------------------------------------------------------
# __eq__
# ---------------------------------------------------------------------------

class TestBeadEq:
    def test_equal_same_canonical(self):
        a = Bead(name="x", canonical="Mozart")
        b = Bead(name="y", canonical="Mozart")
        assert a == b

    def test_equal_case_insensitive(self):
        a = Bead(name="x", canonical="Mozart")
        b = Bead(name="y", canonical="mozart")
        assert a == b

    def test_not_equal_different_canonical(self):
        a = Bead(name="x", canonical="Mozart")
        b = Bead(name="y", canonical="Beethoven")
        assert a != b

    def test_eq_with_non_bead_returns_not_implemented(self):
        b = Bead(name="X", canonical="X")
        result = b.__eq__("not a bead")
        assert result is NotImplemented

    def test_eq_with_none(self):
        b = Bead(name="X")
        assert b != None  # noqa: E711


# ---------------------------------------------------------------------------
# __hash__
# ---------------------------------------------------------------------------

class TestBeadHash:
    def test_equal_beads_same_hash(self):
        a = Bead(name="x", canonical="Mozart")
        b = Bead(name="y", canonical="Mozart")
        assert hash(a) == hash(b)

    def test_case_insensitive_hash(self):
        a = Bead(name="x", canonical="Mozart")
        b = Bead(name="y", canonical="mozart")
        assert hash(a) == hash(b)

    def test_different_beads_different_hash(self):
        a = Bead(name="x", canonical="Mozart")
        b = Bead(name="y", canonical="Beethoven")
        assert hash(a) != hash(b)

    def test_usable_in_set(self):
        a = Bead(name="x", canonical="Mozart")
        b = Bead(name="y", canonical="Mozart")
        s = {a, b}
        assert len(s) == 1

    def test_usable_as_dict_key(self):
        a = Bead(name="x", canonical="Mozart")
        d = {a: "value"}
        b = Bead(name="y", canonical="Mozart")
        assert d[b] == "value"
