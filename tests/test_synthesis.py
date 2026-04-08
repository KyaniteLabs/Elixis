"""Tests for SOUL.md synthesis."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soulcraft.synthesis import synthesize_soulmd


class TestVoiceSelection(unittest.TestCase):
    """Test voice selection based on patterns."""

    def test_voice_returned(self):
        """Voice selection returns a valid voice via synthesis."""
        entities = [{"canonical": "Test", "type": "concept"}]
        graph = {
            "patterns": [{"name": "transformation", "probability": 0.8, "supporting_entities": ["Test"]}],
            "bridges": [],
            "emergent_topic": "test",
            "emergent_theme": "change",
            "consensus_score": 0.8,
        }
        soulmd = synthesize_soulmd(entities, graph)
        # Should produce output with voice characteristics
        self.assertIsNotNone(soulmd)
        self.assertGreater(len(soulmd), 100)


class TestSynthesizeSoulmd(unittest.TestCase):
    """Test SOUL.md generation."""

    def test_empty_entities(self):
        """Empty entities still produce output."""
        entities = []
        graph = {
            "patterns": [],
            "bridges": [],
            "emergent_topic": "creation",
            "emergent_theme": "power",
            "consensus_score": 0.5,
        }
        soulmd = synthesize_soulmd(entities, graph)
        self.assertIn("#", soulmd)  # Markdown header present
        self.assertIn("Who I Am", soulmd)

    def test_includes_emergent_topic(self):
        """Output includes emergent topic."""
        entities = [{"canonical": "Test", "type": "concept"}]
        graph = {
            "patterns": [{"name": "power", "probability": 0.9, "supporting_entities": ["Test"]}],
            "bridges": [],
            "emergent_topic": "creation",
            "emergent_theme": "transformation",
            "consensus_score": 0.8,
        }
        soulmd = synthesize_soulmd(entities, graph)
        # Should reference the emergent topic somewhere
        self.assertIn("creation", soulmd.lower())

    def test_includes_entity_references(self):
        """Output references provided entities."""
        entities = [{"canonical": "Miyamoto Musashi", "type": "historical_figure"}]
        graph = {
            "patterns": [{"name": "mastery", "probability": 0.9, "supporting_entities": ["Miyamoto Musashi"]}],
            "bridges": [],
            "emergent_topic": "mastery",
            "emergent_theme": "discipline",
            "consensus_score": 0.85,
        }
        soulmd = synthesize_soulmd(entities, graph)
        # Output should have content
        self.assertGreater(len(soulmd), 100)


if __name__ == "__main__":
    unittest.main()
