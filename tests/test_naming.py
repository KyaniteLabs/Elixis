"""Tests for naming research module."""

import unittest
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elixis.knowledge import (
    taxonomy,
    taxonomy_by_name,
    taxonomy_by_kingdom,
    taxonomy_search,
    clear_cache,
)
from elixis.naming import (
    research_name,
    research_name_from_identity,
    format_research_report,
    _default_semantics,
    _score_identity_fit,
    generate_taxonomy_variants,
    _taxonomy_enrich_variants,
)


class TestDefaultSemantics(unittest.TestCase):
    """Test default semantics structure."""

    def test_structure(self):
        """Default semantics has required fields."""
        result = _default_semantics()
        self.assertIn("themes", result)
        self.assertIn("pronounceability", result)
        self.assertIn("memorability", result)
        self.assertIn("uniqueness", result)


class TestResearchName(unittest.TestCase):
    """Test naming research pipeline."""

    def test_returns_report_structure(self):
        """Research returns proper report structure."""
        report = research_name("TestName", context="tech", generate_variants=False)

        self.assertIn("input_name", report)
        self.assertIn("context", report)
        self.assertIn("semantics", report)
        self.assertIn("recommendations", report)
        self.assertEqual(report["input_name"], "TestName")

    def test_semantics_populated(self):
        """Report includes semantic analysis."""
        report = research_name("Kyanite", context="AI platform")

        semantics = report.get("semantics", {})
        # Should have some analysis fields
        self.assertIn("themes", semantics)


class TestFormatResearchReport(unittest.TestCase):
    """Test report formatting."""

    def test_includes_name(self):
        """Formatted report includes input name."""
        report = {
            "input_name": "TestCorp",
            "context": "startup",
            "semantics": {
                "themes": ["innovation", "speed"],
                "pronounceability": 0.9,
                "memorability": 0.8,
                "uniqueness": 0.7,
                "positive_connotations": ["modern", "fast"],
                "negative_connotations": [],
            },
            "variants": [],
            "recommendations": ["Good choice"],
        }

        formatted = format_research_report(report)
        self.assertIn("TestCorp", formatted)
        self.assertIn("innovation", formatted)
        self.assertIn("Good choice", formatted)


# ---------------------------------------------------------------------------
# Taxonomy data loader tests
# ---------------------------------------------------------------------------


class TestTaxonomyData(unittest.TestCase):
    """Taxonomy dataset loads and has expected structure."""

    @classmethod
    def setUpClass(cls):
        clear_cache()

    def test_taxonomy_loads(self):
        data = taxonomy()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 50)

    def test_entry_has_required_fields(self):
        data = taxonomy()
        required = {"name", "kingdom", "etymology", "themes", "product_fit"}
        for entry in data[:5]:
            for field in required:
                self.assertIn(field, entry, f"Missing {field} in {entry.get('name')}")

    def test_kingdoms_represented(self):
        data = taxonomy()
        kingdoms = {e.get("kingdom") for e in data}
        self.assertIn("plantae", kingdoms)
        self.assertIn("animalia", kingdoms)
        self.assertIn("mineralia", kingdoms)
        self.assertIn("fungi", kingdoms)


class TestTaxonomyByName(unittest.TestCase):
    """taxonomy_by_name lookup."""

    def test_finds_known_entry(self):
        result = taxonomy_by_name("Gasteria")
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Gasteria")

    def test_case_insensitive(self):
        result = taxonomy_by_name("gasteria")
        self.assertIsNotNone(result)

    def test_missing_returns_none(self):
        result = taxonomy_by_name("NonexistentThingXYZ")
        self.assertIsNone(result)


class TestTaxonomyByKingdom(unittest.TestCase):
    """taxonomy_by_kingdom filter."""

    def test_plantae(self):
        plants = taxonomy_by_kingdom("plantae")
        self.assertGreater(len(plants), 5)
        for p in plants:
            self.assertEqual(p["kingdom"], "plantae")

    def test_unknown_kingdom_empty(self):
        result = taxonomy_by_kingdom("extraterrestria")
        self.assertEqual(result, [])


class TestTaxonomySearch(unittest.TestCase):
    """taxonomy_search by keyword/etymology."""

    def test_search_by_theme(self):
        results = taxonomy_search("transformation")
        self.assertGreater(len(results), 0)

    def test_search_by_name(self):
        results = taxonomy_search("morpho")
        names = [r["name"].lower() for r in results]
        self.assertIn("morpho", names)

    def test_search_limit(self):
        results = taxonomy_search("a", limit=3)
        self.assertLessEqual(len(results), 3)

    def test_search_no_match(self):
        results = taxonomy_search("zzzzzzzzzzz")
        self.assertEqual(len(results), 0)


# ---------------------------------------------------------------------------
# Taxonomy naming variant tests
# ---------------------------------------------------------------------------


class TestTaxonomyEnrichVariants(unittest.TestCase):
    """_taxonomy_enrich_variants cross-references taxonomy data."""

    def test_enriches_matching_name(self):
        variants = [{"name": "Morpho", "availability_score": 0.5}]
        result = _taxonomy_enrich_variants(variants)
        self.assertIn("taxonomy_match", result[0])
        self.assertEqual(result[0]["taxonomy_match"]["kingdom"], "animalia")

    def test_no_match_leaves_unchanged(self):
        variants = [{"name": "Xyzqwr", "availability_score": 0.5}]
        result = _taxonomy_enrich_variants(variants)
        self.assertNotIn("taxonomy_match", result[0])

    def test_boosts_availability_on_match(self):
        variants = [{"name": "Morpho", "availability_score": 0.5}]
        result = _taxonomy_enrich_variants(variants)
        self.assertGreater(result[0]["availability_score"], 0.5)


class TestGenerateTaxonomyVariants(unittest.TestCase):
    """generate_taxonomy_variants with mocked LLM."""

    @patch("elixis.llm.chat")
    def test_returns_variants(self, mock_chat):
        mock_chat.return_value = {
            "content": '[{"name": "Gastrella", "style": "latinized", "availability_score": 0.7, "etymology_guess": "from Gasteria", "reasoning": "short and memorable"}]'
        }
        result = generate_taxonomy_variants("Elixis", "AI tool")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Gastrella")
        self.assertEqual(result[0]["style"], "latinized")

    @patch("elixis.llm.chat")
    def test_empty_llm_response(self, mock_chat):
        mock_chat.return_value = {"content": ""}
        result = generate_taxonomy_variants("Test")
        self.assertEqual(result, [])

    @patch("elixis.llm.chat")
    def test_invalid_json_response(self, mock_chat):
        mock_chat.return_value = {"content": "not json at all"}
        result = generate_taxonomy_variants("Test")
        self.assertEqual(result, [])

    @patch("elixis.llm.chat")
    def test_deduplication(self, mock_chat):
        mock_chat.return_value = {
            "content": '[{"name": "Lithex", "style": "blend", "availability_score": 0.6, "etymology_guess": "from Lithops", "reasoning": "short"}, {"name": "lithex", "style": "blend", "availability_score": 0.5, "etymology_guess": "variant", "reasoning": "alt"}]'
        }
        result = generate_taxonomy_variants("Test")
        self.assertEqual(len(result), 1)

    @patch("elixis.llm.chat")
    def test_taxonomy_match_enrichment(self, mock_chat):
        mock_chat.return_value = {
            "content": '[{"name": "Morpho", "style": "latinized", "availability_score": 0.8, "etymology_guess": "Greek morphe", "reasoning": "real genus"}]'
        }
        result = generate_taxonomy_variants("Test")
        self.assertIn("taxonomy_match", result[0])
        self.assertEqual(result[0]["taxonomy_match"]["real_name"], "Morpho")


class TestResearchNameWithTaxonomy(unittest.TestCase):
    """research_name with source='taxonomy'."""

    @patch("elixis.naming.generate_taxonomy_variants", return_value=[
        {"name": "TestName", "style": "latinized", "availability_score": 0.7}
    ])
    @patch("elixis.naming.analyze_name_semantics", return_value=_default_semantics())
    def test_taxonomy_source_uses_taxonomy_generator(self, mock_sem, mock_tax):
        report = research_name("Elixis", source="taxonomy")
        mock_tax.assert_called_once()
        self.assertEqual(report["source"], "taxonomy")

    @patch("elixis.naming.generate_name_variants", return_value=[])
    @patch("elixis.naming.analyze_name_semantics", return_value=_default_semantics())
    def test_general_source_uses_general_generator(self, mock_sem, mock_gen):
        report = research_name("Elixis", source="general")
        mock_gen.assert_called_once()
        self.assertEqual(report["source"], "general")

    @patch("elixis.naming.analyze_name_semantics", return_value=_default_semantics())
    @patch("elixis.naming.generate_name_variants", return_value=[])
    def test_default_source_is_general(self, mock_gen, mock_sem):
        report = research_name("Elixis")
        mock_gen.assert_called_once()
        self.assertEqual(report["source"], "general")


# ---------------------------------------------------------------------------
# Identity-based naming tests
# ---------------------------------------------------------------------------


def _sample_entities():
    return [
        {
            "canonical": "Morpho",
            "type": "concept",
            "themes": ["transformation", "beauty"],
            "traits": ["iridescent wings"],
            "enrichment": {"description": "Blue morpho butterfly"},
        },
        {
            "canonical": "Monstera",
            "type": "concept",
            "themes": ["growth", "resilience"],
            "traits": ["split leaves"],
            "enrichment": {"description": "Tropical plant"},
        },
    ]


def _sample_graph():
    return {
        "emergent_topic": "transformation",
        "emergent_theme": "Growth through transformation and hidden beauty",
        "patterns": [
            {"id": "transformation", "name": "Transformation & Rebirth", "probability": 0.45, "sub_patterns": ["Metamorphosis"]},
            {"id": "beauty", "name": "Hidden Beauty", "probability": 0.30, "sub_patterns": []},
        ],
        "bridges": [{"entity": "Morpho", "pattern_a": "transformation", "pattern_b": "beauty", "score_a": 0.8, "score_b": 0.7}],
        "entity_scores": [],
        "consensus_score": 0.6,
    }


class TestScoreIdentityFit(unittest.TestCase):
    """_score_identity_fit variant scoring."""

    def test_base_score_no_overlap(self):
        variant = {"availability_score": 0.5}
        score = _score_identity_fit(variant, [], [])
        self.assertEqual(score, 0.5)

    def test_etymology_overlap_with_themes(self):
        variant = {"availability_score": 0.5, "etymology_guess": "transformation Greek morphe"}
        patterns = [{"id": "transformation", "name": "Transformation", "sub_patterns": []}]
        score = _score_identity_fit(variant, patterns, ["transformation"])
        self.assertGreater(score, 0.5)

    def test_taxonomy_match_overlap(self):
        variant = {
            "availability_score": 0.5,
            "taxonomy_match": {
                "themes": ["transformation", "beauty"],
                "etymology": "Greek morphe",
            },
        }
        score = _score_identity_fit(variant, [{"id": "transformation", "name": "T", "sub_patterns": []}], ["transformation"])
        self.assertGreater(score, 0.7)

    def test_score_capped_at_1(self):
        variant = {
            "availability_score": 0.95,
            "etymology_guess": "transformation beauty",
            "taxonomy_match": {"themes": ["transformation"], "etymology": "root"},
        }
        score = _score_identity_fit(
            variant,
            [{"id": "transformation", "name": "T", "sub_patterns": []}],
            ["transformation", "beauty"],
        )
        self.assertLessEqual(score, 1.0)


class TestResearchNameFromIdentity(unittest.TestCase):
    """research_name_from_identity pipeline integration."""

    @patch("elixis.naming.generate_taxonomy_variants", return_value=[
        {"name": "Morphea", "style": "latinized", "availability_score": 0.8, "etymology_guess": "from Morpho transformation", "reasoning": "short"},
    ])
    @patch("elixis.naming.analyze_name_semantics", return_value=_default_semantics())
    def test_returns_report_structure(self, mock_sem, mock_tax):
        report = research_name_from_identity(_sample_entities(), _sample_graph())
        self.assertIn("input_name", report)
        self.assertIn("variants", report)
        self.assertIn("semantics", report)
        self.assertIn("recommendations", report)
        self.assertIn("identity_context", report)

    @patch("elixis.naming.generate_taxonomy_variants", return_value=[])
    @patch("elixis.naming.analyze_name_semantics", return_value=_default_semantics())
    def test_identity_context_populated(self, mock_sem, mock_tax):
        report = research_name_from_identity(_sample_entities(), _sample_graph())
        ctx = report["identity_context"]
        self.assertEqual(ctx["emergent_topic"], "transformation")
        self.assertIn("Morpho", ctx["bridge_entities"])
        self.assertIn("transformation", ctx["entity_themes"])
        self.assertEqual(ctx["entity_count"], 2)

    @patch("elixis.naming.generate_taxonomy_variants", return_value=[
        {"name": "Morphea", "style": "latinized", "availability_score": 0.8, "etymology_guess": "transformation", "reasoning": "test"},
    ])
    @patch("elixis.naming.analyze_name_semantics", return_value=_default_semantics())
    def test_variants_have_identity_fit(self, mock_sem, mock_tax):
        report = research_name_from_identity(_sample_entities(), _sample_graph())
        self.assertIn("identity_fit", report["variants"][0])

    @patch("elixis.naming.analyze_name_semantics", return_value=_default_semantics())
    def test_uses_emergent_topic_as_base(self, mock_sem):
        report = research_name_from_identity(_sample_entities(), _sample_graph(), generate_variants=False)
        self.assertEqual(report["input_name"], "transformation")

    @patch("elixis.naming.generate_name_variants", return_value=[])
    @patch("elixis.naming.analyze_name_semantics", return_value=_default_semantics())
    def test_general_source(self, mock_sem, mock_gen):
        report = research_name_from_identity(_sample_entities(), _sample_graph(), source="general")
        mock_gen.assert_called_once()

    @patch("elixis.naming.analyze_name_semantics", return_value=_default_semantics())
    def test_empty_entities_graceful(self, mock_sem):
        report = research_name_from_identity([], {}, generate_variants=False)
        self.assertIn("input_name", report)
        self.assertEqual(report["identity_context"]["entity_count"], 0)

    @patch("elixis.naming.analyze_name_semantics", return_value=_default_semantics())
    def test_empty_graph_graceful(self, mock_sem):
        report = research_name_from_identity(_sample_entities(), {}, generate_variants=False)
        self.assertIn("input_name", report)


class TestFormatReportWithIdentity(unittest.TestCase):
    """format_research_report handles identity_context."""

    def test_includes_identity_section(self):
        report = {
            "input_name": "transformation",
            "context": "test",
            "identity_context": {
                "emergent_theme": "Growth through transformation",
                "dominant_patterns": [{"id": "transformation", "name": "Transformation"}],
                "bridge_entities": ["Morpho"],
                "entity_themes": ["transformation", "beauty"],
            },
            "semantics": _default_semantics(),
            "variants": [],
            "recommendations": [],
        }
        formatted = format_research_report(report)
        self.assertIn("Identity Profile", formatted)
        self.assertIn("Growth through transformation", formatted)
        self.assertIn("Morpho", formatted)

    def test_variant_table_with_fit(self):
        report = {
            "input_name": "test",
            "context": "",
            "semantics": _default_semantics(),
            "variants": [
                {"name": "Elixis", "style": "blend", "availability_score": 0.8, "identity_fit": 0.9, "reasoning": "good"},
            ],
            "recommendations": [],
        }
        formatted = format_research_report(report)
        self.assertIn("Fit", formatted)
        self.assertIn("90%", formatted)


if __name__ == "__main__":
    unittest.main()
