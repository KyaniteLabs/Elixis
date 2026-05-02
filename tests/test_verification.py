"""Tests for triple verification (soulcraft.verification)."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soulcraft.verification import verify_pattern, verify_bead, verify_graph
from soulcraft.bead import Bead


def _make_good_pattern():
    """Pattern that should pass all 3 gates."""
    return {
        "name": "cross-domain pattern with multiple themes",
        "supporting_entities": 3,
        "themes": ["power", "transformation"],
        "probability": 0.2,
    }


class TestVerifyPatternAllGates(unittest.TestCase):
    """Pattern verification with varying gate outcomes."""

    def test_all_three_gates_passes(self):
        pattern = _make_good_pattern()
        result = verify_pattern(pattern)
        self.assertEqual(result["level"], "model")
        self.assertAlmostEqual(result["confidence"], 0.9)
        self.assertTrue(all(result["gates"].values()))

    def test_two_gates_passes(self):
        # cross_domain=True, generative=True, exclusive=False (short name)
        pattern = {
            "name": "short",
            "supporting_entities": 3,
            "themes": ["a", "b"],
            "probability": 0.2,
        }
        result = verify_pattern(pattern)
        self.assertEqual(result["level"], "model")
        self.assertAlmostEqual(result["confidence"], 0.75)

    def test_one_gate_passes(self):
        # exclusive=True only (probability > 0.05, name > 5 chars)
        pattern = {
            "name": "sufficiently long name",
            "supporting_entities": 0,
            "themes": [],
            "probability": 0.06,
        }
        result = verify_pattern(pattern)
        self.assertEqual(result["level"], "heuristic")
        self.assertAlmostEqual(result["confidence"], 0.5)

    def test_zero_gates_discard(self):
        pattern = {
            "name": "",
            "supporting_entities": 0,
            "themes": [],
            "probability": 0.0,
        }
        result = verify_pattern(pattern)
        self.assertEqual(result["level"], "discard")
        self.assertAlmostEqual(result["confidence"], 0.1)

    def test_good_pattern_returns_gates_dict(self):
        pattern = _make_good_pattern()
        result = verify_pattern(pattern)
        self.assertIn("cross_domain", result["gates"])
        self.assertIn("generative", result["gates"])
        self.assertIn("exclusive", result["gates"])


class TestVerifyBeadDict(unittest.TestCase):
    """Bead verification with dict input."""

    def test_valid_dict(self):
        bead = {
            "canonical": "Marcus Aurelius",
            "type": "person",
            "themes": ["wisdom", "power"],
            "confidence": 0.8,
        }
        result = verify_bead(bead)
        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])

    def test_missing_canonical(self):
        bead = {
            "type": "concept",
            "themes": ["transformation"],
            "confidence": 0.7,
        }
        result = verify_bead(bead)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("canonical" in i for i in result["issues"])
        )

    def test_no_themes_warning(self):
        bead = {
            "canonical": "Test",
            "type": "concept",
            "themes": [],
            "confidence": 0.5,
        }
        result = verify_bead(bead)
        self.assertTrue(
            any("themes" in w.lower() for w in result["warnings"])
        )

    def test_invalid_confidence(self):
        bead = {
            "canonical": "Test",
            "type": "concept",
            "confidence": -1,
        }
        result = verify_bead(bead)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("confidence" in i.lower() for i in result["issues"])
        )

    def test_zero_confidence_invalid(self):
        bead = {
            "canonical": "Test",
            "type": "concept",
            "confidence": 0,
        }
        result = verify_bead(bead)
        self.assertFalse(result["valid"])

    def test_invalid_type(self):
        bead = {
            "canonical": "Test",
            "type": "nonexistent_type",
            "confidence": 0.5,
        }
        result = verify_bead(bead)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("type" in i.lower() for i in result["issues"])
        )


class TestVerifyBeadObject(unittest.TestCase):
    """Bead verification with Bead object input."""

    def test_valid_bead_object(self):
        bead = Bead(
            name="Stoicism",
            canonical="Stoicism",
            type="concept",
            themes=["wisdom"],
            confidence=0.7,
        )
        result = verify_bead(bead)
        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])

    def test_bead_from_dict(self):
        data = {
            "name": "Test",
            "canonical": "Test",
            "type": "concept",
            "themes": ["creation"],
            "confidence": 0.6,
        }
        bead = Bead.from_dict(data)
        result = verify_bead(bead)
        self.assertTrue(result["valid"])

    def test_bead_object_missing_canonical(self):
        bead = Bead(name="", canonical="", type="concept", confidence=0.5)
        result = verify_bead(bead)
        self.assertFalse(result["valid"])


class TestVerifyGraphValid(unittest.TestCase):
    """Graph verification with valid inputs."""

    def test_valid_graph(self):
        graph = {
            "patterns": [_make_good_pattern()],
            "emergent_topic": "Transformation",
            "consensus_score": 0.8,
            "entity_scores": {"entity1": 0.9},
        }
        result = verify_graph(graph)
        self.assertTrue(result["valid"])
        self.assertEqual(result["patterns_verified"], 1)
        self.assertEqual(result["models"], 1)
        self.assertEqual(result["issues"], [])

    def test_no_patterns_warning(self):
        graph = {
            "patterns": [],
            "emergent_topic": "Test Topic",
            "consensus_score": 0.7,
            "entity_scores": {},
        }
        result = verify_graph(graph)
        # No patterns is a warning, not an issue
        self.assertTrue(
            any("no patterns" in w.lower() for w in result["warnings"]),
            f"Expected 'no patterns' warning, got: {result['warnings']}",
        )


class TestVerifyGraphWarnings(unittest.TestCase):
    """Graph verification produces appropriate warnings."""

    def test_missing_emergent_topic_warning(self):
        graph = {
            "patterns": [_make_good_pattern()],
            "emergent_topic": "Unknown",
            "consensus_score": 0.5,
            "entity_scores": {"a": 0.5},
        }
        result = verify_graph(graph)
        self.assertTrue(
            any("emergent_topic" in w for w in result["warnings"]),
            f"Expected emergent_topic warning, got: {result['warnings']}",
        )

    def test_missing_emergent_topic_key_warning(self):
        graph = {
            "patterns": [_make_good_pattern()],
            "consensus_score": 0.5,
            "entity_scores": {"a": 0.5},
        }
        result = verify_graph(graph)
        self.assertTrue(
            any("emergent_topic" in w for w in result["warnings"]),
            f"Expected emergent_topic warning, got: {result['warnings']}",
        )


class TestVerifyGraphIssues(unittest.TestCase):
    """Graph verification produces appropriate issues."""

    def test_invalid_consensus_score(self):
        graph = {
            "patterns": [],
            "emergent_topic": "Test",
            "consensus_score": 1.5,
            "entity_scores": {},
        }
        result = verify_graph(graph)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("consensus_score" in i for i in result["issues"]),
            f"Expected consensus_score issue, got: {result['issues']}",
        )

    def test_negative_consensus_score(self):
        graph = {
            "patterns": [],
            "emergent_topic": "Test",
            "consensus_score": -0.5,
            "entity_scores": {},
        }
        result = verify_graph(graph)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("consensus_score" in i for i in result["issues"])
        )

    def test_no_entity_scores(self):
        graph = {
            "patterns": [_make_good_pattern()],
            "emergent_topic": "Test",
            "consensus_score": 0.5,
        }
        result = verify_graph(graph)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("entity_scores" in i for i in result["issues"]),
            f"Expected entity_scores issue, got: {result['issues']}",
        )


class TestVerifyGraphMixedQuality(unittest.TestCase):
    """Graph with patterns of varying quality levels."""

    def test_mixed_quality_patterns(self):
        good = _make_good_pattern()
        medium = {
            "name": "short",
            "supporting_entities": 3,
            "themes": ["a", "b"],
            "probability": 0.2,
        }
        weak = {
            "name": "",
            "supporting_entities": 0,
            "themes": [],
            "probability": 0.0,
        }
        graph = {
            "patterns": [good, medium, weak],
            "emergent_topic": "Mixed",
            "consensus_score": 0.6,
            "entity_scores": {"e1": 0.5},
        }
        result = verify_graph(graph)
        self.assertTrue(result["valid"])
        self.assertEqual(result["patterns_verified"], 3)
        self.assertGreaterEqual(result["models"], 2)
        self.assertGreaterEqual(result["discarded"], 1)


if __name__ == "__main__":
    unittest.main()
