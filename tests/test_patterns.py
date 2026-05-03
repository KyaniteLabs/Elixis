"""Tests for pattern graph building."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elixis.patterns import build_pattern_graph


class TestPatternGraph(unittest.TestCase):
    """Test pattern graph construction."""

    def test_empty_entities(self):
        """Empty entity list returns graph with required fields."""
        graph = build_pattern_graph([], "")
        self.assertIn("patterns", graph)
        self.assertIn("bridges", graph)
        self.assertIn("emergent_topic", graph)
        self.assertIn("emergent_theme", graph)
        self.assertIn("consensus_score", graph)

    def test_single_entity(self):
        """Single entity creates simple graph."""
        entities = [{
            "canonical": "Test",
            "type": "concept",
            "themes": ["power"],
            "traits": ["strong"],
        }]
        graph = build_pattern_graph(entities, "test brain dump")
        self.assertIsInstance(graph["patterns"], list)
        self.assertIsInstance(graph.get("emergent_topic"), str)

    def test_entity_themes_extracted(self):
        """Entity themes are properly used in graph building."""
        entities = [
            {"canonical": "A", "themes": ["transformation", "power"], "traits": []},
            {"canonical": "B", "themes": ["transformation", "wisdom"], "traits": []},
        ]
        graph = build_pattern_graph(entities, "test")
        # Should detect transformation-related pattern
        pattern_names = [p["name"].lower() for p in graph["patterns"]]
        self.assertTrue(any("transformation" in name for name in pattern_names))

    def test_patterns_have_required_fields(self):
        """Each pattern has required fields."""
        entities = [
            {"canonical": "A", "themes": ["power"], "traits": []},
        ]
        graph = build_pattern_graph(entities, "test")

        for pattern in graph.get("patterns", []):
            self.assertIn("name", pattern)
            self.assertIn("probability", pattern)
            self.assertIn("supporting_entities", pattern)


if __name__ == "__main__":
    unittest.main()
