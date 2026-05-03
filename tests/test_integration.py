"""Integration tests for full pipeline."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fugax.entities import extract_entities
from fugax.patterns import build_pattern_graph
from fugax.synthesis import synthesize_soulmd


class TestFullPipeline(unittest.TestCase):
    """Test the complete 3-stage pipeline."""

    def test_pipeline_end_to_end(self):
        """Run full pipeline on sample brain dump."""
        brain_dump = """
Kyan - AI systems architect, builder of tools
Miyamoto Musashi (Book of Five Rings) - strategist, philosopher
The concept of emergence from complexity
Flow states in creative work
"""
        # Stage 1: Extract entities
        entities = extract_entities(brain_dump)
        self.assertIsInstance(entities, list)

        # Stage 2: Build pattern graph
        graph = build_pattern_graph(entities, brain_dump)
        self.assertIn("patterns", graph)
        self.assertIn("emergent_topic", graph)

        # Stage 3: Synthesize SOUL.md
        soulmd = synthesize_soulmd(entities, graph)
        self.assertIn("#", soulmd)
        self.assertIn("Who I Am", soulmd)
        self.assertGreater(len(soulmd), 200)

    def test_short_input_pipeline(self):
        """Pipeline handles short inputs gracefully."""
        brain_dump = "Kyan builds AI"

        entities = extract_entities(brain_dump)
        graph = build_pattern_graph(entities, brain_dump)
        soulmd = synthesize_soulmd(entities, graph)

        self.assertIsInstance(soulmd, str)
        self.assertGreater(len(soulmd), 100)


class TestPipelineWithEmptyData(unittest.TestCase):
    """Test pipeline edge cases."""

    def test_empty_brain_dump(self):
        """Empty brain dump is handled."""
        entities = extract_entities("")
        self.assertEqual(entities, [])

        graph = build_pattern_graph(entities, "")
        soulmd = synthesize_soulmd(entities, graph)
        self.assertIsInstance(soulmd, str)


if __name__ == "__main__":
    unittest.main()
