"""Tests for pattern graph building."""

import unittest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elixis.patterns import build_pattern_graph, llm_classify_patterns


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


class TestLlmPatternClassificationParsing(unittest.TestCase):
    """Regression tests for model JSON shapes seen in cloud classification."""

    @patch("elixis.llm.chat")
    def test_accepts_entity_keyed_object_response(self, mock_chat):
        mock_chat.return_value = {
            "content": '{"Athena": {"Wisdom & Knowledge": 0.91, "Power & Ambition": 0.22}}',
            "model": "glm-5.1",
            "provider": "zai",
            "tokens_in": 20,
            "tokens_out": 10,
        }

        result = llm_classify_patterns([
            {"canonical": "Athena", "type": "mythological", "themes": [], "traits": []},
        ])

        self.assertEqual(result["Athena"]["wisdom"], 0.91)
        self.assertEqual(result["Athena"]["power"], 0.22)

    @patch("elixis.llm.chat")
    def test_accepts_wrapped_mapping_with_pattern_list_scores(self, mock_chat):
        mock_chat.return_value = {
            "content": (
                '{"classifications": {"Batman": ['
                '{"pattern": "The Guardian", "score": 0.82},'
                '{"pattern_id": "shadow", "probability": 0.41}'
                ']}}'
            ),
            "model": "glm-5.1",
            "provider": "zai",
            "tokens_in": 20,
            "tokens_out": 10,
        }

        result = llm_classify_patterns([
            {"canonical": "Batman", "type": "character", "themes": [], "traits": []},
        ])

        self.assertEqual(result["Batman"]["guardian"], 0.82)
        self.assertEqual(result["Batman"]["shadow"], 0.41)

    @patch("elixis.llm.chat")
    def test_expands_classification_token_budget_for_many_entities(self, mock_chat):
        mock_chat.return_value = {
            "content": '{"Entity 0": {"wisdom": 0.7}}',
            "model": "glm-5.1",
            "provider": "zai",
            "tokens_in": 40,
            "tokens_out": 12,
        }
        entities = [
            {"canonical": f"Entity {i}", "type": "concept", "themes": [], "traits": []}
            for i in range(11)
        ]

        llm_classify_patterns(entities)

        self.assertGreaterEqual(mock_chat.call_args.kwargs["max_tokens"], 2900)
        self.assertIn("compact minified JSON", mock_chat.call_args.args[0][0]["content"])


if __name__ == "__main__":
    unittest.main()
