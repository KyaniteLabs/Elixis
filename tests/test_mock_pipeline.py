"""Deterministic pipeline tests using LLM mocking.

Tests the full pipeline with mocked LLM responses to verify
entity extraction, pattern analysis, and synthesis work correctly
without requiring a running LLM backend.
"""

import json
import unittest
from unittest.mock import patch

from elixis.entities import extract_entities
from elixis.patterns import build_pattern_graph
from elixis.synthesis import synthesize_soulmd
from elixis.parsing import parse_llm_json_array


class TestParseLlmJsonArray(unittest.TestCase):
    """Tests for the shared LLM JSON parsing utility."""

    def test_plain_json_array(self):
        result = parse_llm_json_array('[{"name": "test"}]')
        self.assertEqual(result, [{"name": "test"}])

    def test_json_in_code_fences(self):
        response = '```json\n[{"name": "test"}]\n```'
        result = parse_llm_json_array(response)
        self.assertEqual(result, [{"name": "test"}])

    def test_json_in_plain_fences(self):
        response = '```\n[{"name": "test"}]\n```'
        result = parse_llm_json_array(response)
        self.assertEqual(result, [{"name": "test"}])

    def test_json_with_surrounding_text(self):
        response = 'Here are the results:\n[{"name": "test"}]\nDone.'
        result = parse_llm_json_array(response)
        self.assertEqual(result, [{"name": "test"}])

    def test_empty_string(self):
        self.assertIsNone(parse_llm_json_array(""))

    def test_none_input(self):
        self.assertIsNone(parse_llm_json_array(None))

    def test_no_array(self):
        self.assertIsNone(parse_llm_json_array('{"key": "value"}'))

    def test_invalid_json(self):
        self.assertIsNone(parse_llm_json_array('[{broken json}]'))

    def test_empty_array(self):
        result = parse_llm_json_array('[]')
        self.assertEqual(result, [])

    def test_mismatched_brackets(self):
        self.assertIsNone(parse_llm_json_array('[{'))


class TestEntityExtractionMocked(unittest.TestCase):
    """Test entity extraction with mocked LLM responses."""

    @patch('elixis.llm.chat')
    def test_extracts_entities_from_mock_response(self, mock_chat):
        mock_chat.return_value = {
            "content": json.dumps([
                {"original": "Tony Montana", "canonical": "Tony Montana", "type": "character",
                 "source": "Scarface", "themes": ["power"], "traits": ["ruthless"]},
                {"original": "Fight Club", "canonical": "Fight Club", "type": "movie",
                 "source": "", "themes": ["rebellion"], "traits": ["subversive"]},
            ]),
            "tokens_in": 100,
            "tokens_out": 50,
            "latency_ms": 500,
            "model": "test",
            "provider": "test",
        }
        entities = extract_entities("Tony Montana\nFight Club")
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0]["canonical"], "Tony Montana")
        self.assertIn(entities[0]["type"], ("character", "concept"))
        self.assertEqual(entities[1]["canonical"], "Fight Club")

    @patch('elixis.llm.chat')
    def test_handles_code_fence_response(self, mock_chat):
        mock_chat.return_value = {
            "content": '```json\n' + json.dumps([
                {"original": "Sherlock Holmes", "canonical": "Sherlock Holmes", "type": "character",
                 "source": "", "themes": ["intellect"], "traits": ["analytical"]},
            ]) + '\n```',
            "tokens_in": 100,
            "tokens_out": 50,
            "latency_ms": 500,
            "model": "test",
            "provider": "test",
        }
        entities = extract_entities("Sherlock Holmes")
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]["canonical"], "Sherlock Holmes")

    @patch('elixis.llm.chat')
    def test_returns_empty_on_llm_failure(self, mock_chat):
        mock_chat.return_value = {
            "content": "",
            "error": "Connection refused",
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 0,
            "model": "test",
            "provider": "test",
        }
        entities = extract_entities("some input")
        # LLM failure triggers heuristic fallback, which may extract items
        self.assertIsInstance(entities, list)

    @patch('elixis.llm.chat')
    def test_deduplicates_entities(self, mock_chat):
        mock_chat.return_value = {
            "content": json.dumps([
                {"original": "Batman", "canonical": "Batman", "type": "character",
                 "source": "", "themes": ["justice"], "traits": ["dark"]},
                {"original": "Batman", "canonical": "Batman", "type": "character",
                 "source": "", "themes": ["justice"], "traits": ["dark"]},
            ]),
            "tokens_in": 100,
            "tokens_out": 50,
            "latency_ms": 500,
            "model": "test",
            "provider": "test",
        }
        entities = extract_entities("Batman\nBatman")
        self.assertEqual(len(entities), 1)


class TestPatternGraphMocked(unittest.TestCase):
    """Test pattern graph building with mocked LLM classification."""

    @patch('elixis.patterns.llm_classify_patterns')
    def test_builds_pattern_graph(self, mock_classify):
        mock_classify.return_value = {
            "Tony Montana": {"power": 0.8, "transformation": 0.3},
            "Fight Club": {"freedom": 0.7, "shadow": 0.4},
        }
        entities = [
            {"canonical": "Tony Montana", "type": "character", "themes": ["power"], "traits": []},
            {"canonical": "Fight Club", "type": "movie", "themes": ["rebellion"], "traits": []},
        ]
        graph = build_pattern_graph(entities, "Tony Montana\nFight Club")

        self.assertGreater(len(graph["patterns"]), 0)
        self.assertIsNotNone(graph["emergent_topic"])
        self.assertGreaterEqual(graph["consensus_score"], 0)
        self.assertLessEqual(graph["consensus_score"], 1)
        self.assertIn("analysis_notes", graph)

    def test_empty_entities_returns_defaults(self):
        graph = build_pattern_graph([], "")
        self.assertEqual(graph["patterns"], [])
        self.assertEqual(graph["consensus_score"], 0.0)
        self.assertEqual(graph["emergent_topic"], "Unknown")

    @patch('elixis.patterns.llm_classify_patterns')
    def test_dominant_pattern_has_highest_probability(self, mock_classify):
        mock_classify.return_value = {
            "Test": {"power": 0.9, "wisdom": 0.1},
        }
        entities = [
            {"canonical": "Test", "type": "concept", "themes": [], "traits": []},
        ]
        graph = build_pattern_graph(entities, "test")
        patterns = graph["patterns"]
        if len(patterns) > 1:
            self.assertGreaterEqual(patterns[0]["probability"], patterns[1]["probability"])

    @patch('elixis.patterns.llm_classify_patterns')
    def test_retries_transient_llm_classification_failure(self, mock_classify):
        mock_classify.side_effect = [
            RuntimeError("invalid JSON"),
            {"Athena": {"wisdom": 0.9}},
        ]
        entities = [
            {"canonical": "Athena", "type": "mythological", "themes": [], "traits": []},
        ]

        graph = build_pattern_graph(entities, "Athena")

        self.assertEqual(mock_classify.call_count, 2)
        self.assertTrue(any("LLM-assisted" in note for note in graph["analysis_notes"]))

    @patch('elixis.patterns.llm_classify_patterns')
    def test_records_llm_classification_failure_reason(self, mock_classify):
        mock_classify.side_effect = [
            RuntimeError("invalid JSON"),
            RuntimeError("empty response"),
        ]
        entities = [
            {"canonical": "Athena", "type": "mythological", "themes": [], "traits": []},
        ]
        telemetry = {}

        graph = build_pattern_graph(entities, "Athena", telemetry=telemetry)

        self.assertEqual(mock_classify.call_count, 2)
        self.assertFalse(telemetry["llm_available"])
        self.assertEqual(telemetry["llm_classification"]["error"], "empty response")
        self.assertTrue(any("empty response" in note for note in graph["analysis_notes"]))


class TestSynthesisMocked(unittest.TestCase):
    """Test SOUL.md synthesis with mocked LLM."""

    @patch('elixis.synthesis.chat')
    def test_produces_soulmd(self, mock_chat):
        mock_chat.return_value = {
            "content": "# The Constructed Self\n\n## Worldview\nTest worldview.\n\n## Voice\nTest voice.",
            "tokens_in": 100,
            "tokens_out": 200,
            "latency_ms": 1000,
            "model": "test",
            "provider": "test",
        }
        entities = [
            {"canonical": "Tony Montana", "type": "character", "themes": ["power"],
             "traits": ["ruthless"], "source": "Scarface"},
        ]
        graph = {
            "patterns": [{"id": "power", "name": "Power & Ambition", "probability": 0.8, "color": "#a855f7",
                          "supporting_entities": 1, "sub_patterns": []}],
            "emergent_topic": "Power & Ambition",
            "emergent_theme": "Power archetype",
            "emergent_color": "#a855f7",
            "consensus_score": 0.7,
            "entity_scores": [],
            "bridges": [],
            "sub_patterns": [],
            "analysis_notes": [],
        }
        result = synthesize_soulmd(entities, graph)
        self.assertIn("Worldview", result)
        self.assertGreater(len(result), 50)

    @patch('elixis.synthesis.chat')
    def test_falls_back_on_llm_failure(self, mock_chat):
        mock_chat.return_value = {
            "content": "",
            "error": "unavailable",
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 0,
            "model": "test",
            "provider": "test",
        }
        entities = [
            {"canonical": "Test Entity", "type": "concept", "themes": [], "traits": [],
             "source": ""},
        ]
        graph = {
            "patterns": [{"id": "wisdom", "name": "Wisdom", "probability": 0.5, "color": "#38bdf8",
                          "supporting_entities": 1, "sub_patterns": []}],
            "emergent_topic": "Wisdom",
            "emergent_theme": "Wisdom archetype",
            "emergent_color": "#38bdf8",
            "consensus_score": 0.5,
            "entity_scores": [],
            "bridges": [],
            "sub_patterns": [],
            "analysis_notes": [],
        }
        result = synthesize_soulmd(entities, graph)
        # Should produce a template fallback, not empty
        self.assertGreater(len(result), 0)


class TestLlmErrorReporting(unittest.TestCase):
    """Test that LLM errors are properly reported."""

    @patch('elixis.llm.urllib.request.urlopen')
    def test_ollama_failure_includes_error_field(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        from elixis.llm import _call_ollama
        result = _call_ollama([{"role": "user", "content": "test"}])

        self.assertEqual(result["content"], "")
        self.assertIn("error", result)
        self.assertIn("Connection refused", result["error"])


if __name__ == "__main__":
    unittest.main()
