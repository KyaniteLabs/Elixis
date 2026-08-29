"""Golden end-to-end game run with a stubbed LLM seat.

Proves the full loop deterministically (no network): declare -> elaborate ->
connect -> resolve -> name, with the LLM core firing through the same call
path production uses, discipline adjudication applied to live variant output,
and the plate emitted as one unit. The real-seat golden run lives in
scripts/golden_run.py and is executed manually against a live .env.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elixis import llm
from elixis.engine import GameEngine

EXTRACTION = """[
 {"name": "Fujifilm X100V", "type": "work", "source": "Fujifilm", "themes": ["creation", "explorer"], "traits": ["compact craftsmanship"], "related": ["X-E4"]},
 {"name": "Midjourney", "type": "concept", "source": "", "themes": ["creation", "transformation"], "traits": ["generative imagination"], "related": ["Stable Diffusion"]},
 {"name": "Marcus Aurelius", "type": "historical_figure", "source": "Meditations", "themes": ["wisdom", "struggle"], "traits": ["stoic discipline"], "related": ["Seneca"]},
 {"name": "Miyamoto Musashi", "type": "person", "source": "Book of Five Rings", "themes": ["struggle", "wisdom"], "traits": ["patient mastery"], "related": ["Marcus Aurelius"]}
]"""

CLASSIFY = """[
 {"entity": "Fujifilm X100V", "scores": {"sage": 0.8, "creator": 0.6}},
 {"entity": "Midjourney", "scores": {"creator": 0.9, "magician": 0.7}},
 {"entity": "Marcus Aurelius", "scores": {"sage": 0.9, "ruler": 0.5}},
 {"entity": "Miyamoto Musashi", "scores": {"warrior": 0.8, "sage": 0.6}}
]"""

VARIANTS = """[
 {"name": "Luminara", "style": "latinized", "availability_score": 0.8, "etymology_guess": "lumen light", "reasoning": "translucent light"},
 {"name": "Glasswick", "style": "compound", "availability_score": 0.7, "etymology_guess": "glass wick", "reasoning": "glass family reject"},
 {"name": "tokpipe", "style": "compound", "availability_score": 0.9, "etymology_guess": "tok pipe", "reasoning": "undeniable wink reject"},
 {"name": "Vitrine", "style": "french", "availability_score": 0.6, "etymology_guess": "glass case", "reasoning": "glass case reject"},
 {"name": "QX", "style": "abstract", "availability_score": 0.9, "etymology_guess": "", "reasoning": "single part reject"}
]"""

SEMANTICS = """{
 "themes": ["translucency", "attention"],
 "positive_connotations": ["clear", "warm"],
 "negative_connotations": [],
 "pronounceability": 0.8,
 "memorability": 0.7,
 "uniqueness": 0.6,
 "global_considerations": ""
}"""


def _stub_chat(messages, model=None, max_tokens=None, think=True):
    """Route by prompt shape, exactly as the engine issues them."""
    system = messages[0].get("content", "") if messages else ""
    user = messages[-1].get("content", "") if messages else ""
    blob = system + "\n" + user
    if "named reference" in blob:
        content = EXTRACTION
    elif "archetypal patterns" in system:
        content = CLASSIFY
    elif "product names" in blob or "name variants" in blob:
        content = VARIANTS
    elif "Analyze the name" in blob:
        content = SEMANTICS
    else:
        content = '{"ok": true}'
    return {
        "content": content,
        "tokens_in": 100,
        "tokens_out": len(content.split()),
        "latency_ms": 1,
        "tokens_per_sec": 1000.0,
        "model": model or "stub",
        "provider": "stub",
    }


class TestGoldenRun(unittest.TestCase):
    """One full game, LLM core firing (stubbed), discipline applied."""

    def setUp(self):
        self._real_chat = llm.chat
        self._real_avail = llm.is_available
        llm.chat = _stub_chat
        llm.is_available = lambda: True

    def tearDown(self):
        llm.chat = self._real_chat
        llm.is_available = self._real_avail

    def test_full_game_with_llm_core_and_discipline(self):
        brain_dump = (
            "Photography with the Fujifilm X100V, generative art in Midjourney, "
            "reading Marcus Aurelius and Miyamoto Musashi."
        )
        engine = GameEngine(
            enrich_entities=lambda entities, telemetry=None: entities,
        )

        engine.declare_themes(brain_dump)
        state = engine.state
        self.assertEqual(
            state.metadata["extraction_telemetry"]["source"], "llm",
            "LLM extraction core must fire, not the heuristic fallback",
        )
        self.assertEqual(len(state.beads), 4)

        engine.elaborate()
        engine.connect_domains()
        self.assertTrue(state.threads or state.metadata["pattern_graph"]["patterns"])

        output = engine.resolve("identity")
        self.assertGreater(len(output), 200)

        report = engine.name(source="taxonomy", object_profile="glass-titles")
        self.assertEqual(
            report["discipline"]["applied"], True,
            "machine-encoded discipline must adjudicate variants",
        )
        kept_names = [v["name"] for v in report["variants"]]
        rejected_names = [v["name"] for v in report["rejected_variants"]]
        self.assertIn("Luminara", kept_names)
        self.assertIn("Glasswick", rejected_names)
        self.assertIn("tokpipe", rejected_names)
        self.assertIn("QX", rejected_names)
        self.assertIn("Vitrine", rejected_names)

        plate = report.get("plate")
        self.assertIsNotNone(plate, "a discipline-passing variant must yield a plate")
        self.assertEqual(plate["name"], "Luminara")
        self.assertTrue(plate["validation"]["valid"], plate["validation"])
        self.assertTrue(2 <= len(plate["silk"].split(" · ")) <= 5)
        self.assertEqual(state.metadata["plate"], plate)

        # Every kept variant carries the rubric
        for v in report["variants"]:
            for axis in ("ST", "EC", "SO"):
                self.assertIn(axis, v["prosody"])
            self.assertIn("deniability", v)


if __name__ == "__main__":
    unittest.main()
