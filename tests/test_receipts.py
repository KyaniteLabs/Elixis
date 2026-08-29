"""Tests for the receipts feed (elixis/receipts.py)."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elixis.receipts import corpus_to_seed, ingest_corpus

SAMPLE = """# ELIXIS Corpus Feed — attention x activity by month (lab 08)

## 2026-02 — watched 370 AI videos; built: claude-code(388)
- Deep Dive: The M2 MacBook Air
- Claude Skills Are Great

## 2026-03 — watched 398 AI videos; built: claude-code(3778), hermes-agent(4)
- Claude Skills Are Great
- Why Local Models Win

## 2026-04 — watched 594 AI videos; built: —
- Why Local Models Win
"""


class TestIngestCorpus(unittest.TestCase):
    def setUp(self):
        self.data = ingest_corpus(SAMPLE)

    def test_months_parsed(self):
        self.assertEqual(self.data["months_count"], 3)
        self.assertEqual(self.data["months"][0]["month"], "2026-02")

    def test_watched_counts(self):
        self.assertEqual(self.data["watched_total"], 370 + 398 + 594)

    def test_build_ledgers(self):
        self.assertEqual(self.data["built_projects"]["claude-code"], 388 + 3778)
        self.assertEqual(self.data["built_projects"]["hermes-agent"], 4)
        self.assertEqual(self.data["months"][2]["built"], {})  # built: —
        self.assertEqual(self.data["built_total"], 388 + 3778 + 4)

    def test_titles_and_dedup(self):
        self.assertEqual(self.data["unique_titles"], 3)
        self.assertEqual(self.data["title_counts"]["Claude Skills Are Great"], 2)
        self.assertEqual(self.data["title_counts"]["Why Local Models Win"], 2)

    def test_empty_corpus(self):
        data = ingest_corpus("")
        self.assertEqual(data["months_count"], 0)
        self.assertEqual(data["unique_titles"], 0)


class TestCorpusToSeed(unittest.TestCase):
    def test_built_ledgers_lead_the_seed(self):
        seed = corpus_to_seed(SAMPLE)
        first_line = seed.splitlines()[0]
        self.assertTrue(first_line.startswith("2026-02 built:"))
        self.assertIn("claude-code(388)", first_line)
        self.assertIn("2026-03 built:", seed)
        self.assertIn("claude-code(3778)", seed)

    def test_titles_deduped_and_normalized(self):
        seed = corpus_to_seed(SAMPLE)
        self.assertEqual(seed.count("Claude Skills Are Great"), 1)
        self.assertNotIn("—", seed)  # em dashes neutralized

    def test_seed_respects_cap(self):
        seed = corpus_to_seed(SAMPLE, max_chars=50)
        self.assertLessEqual(len(seed), 50)

    def test_seed_feeds_the_engine(self):
        from elixis.engine import GameEngine

        seed = corpus_to_seed(SAMPLE)
        engine = GameEngine(
            enrich_entities=lambda entities, telemetry=None: entities,
        )
        engine.declare_themes(seed)
        engine.elaborate()
        engine.connect_domains()
        self.assertGreaterEqual(len(engine.state.beads), 1)


if __name__ == "__main__":
    unittest.main()
