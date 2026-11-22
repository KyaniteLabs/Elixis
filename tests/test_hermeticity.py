"""Hermeticity guard: neither pytest nor `python -m unittest` can reach a
live LLM seat (#144).

The env pin lives in tests/__init__.py precisely because plain unittest
never loads conftest.py. ProbeOnly is executed through a real
`python -m unittest` subprocess with a poisoned LLM environment to prove
the pin holds for that entry point too.
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEAD_PIN = "http://127.0.0.1:9"


class TestHermeticUnderPytest(unittest.TestCase):
    def test_env_is_pinned_before_elixis_reads_it(self):
        from elixis import llm

        self.assertEqual(os.environ.get("ELIXIS_TEST"), "1")
        self.assertEqual(llm.cfg.base_url, DEAD_PIN)
        self.assertEqual(llm.cfg.provider, "ollama")

    def test_availability_probe_refuses_instantly(self):
        from elixis import llm

        llm._availability_cache["result"] = None
        llm._availability_cache["expires"] = 0
        self.assertFalse(llm.is_available())


class ProbeOnly(unittest.TestCase):
    """Runs only via `python -m unittest tests.test_hermeticity.ProbeOnly`."""

    def test_unittest_invocation_is_pinned_to_dead_endpoint(self):
        from elixis import llm

        self.assertEqual(os.environ.get("ELIXIS_TEST"), "1")
        self.assertEqual(llm.cfg.base_url, DEAD_PIN)
        self.assertFalse(llm.is_available())


class TestUnittestRunnerHermeticity(unittest.TestCase):
    def test_python_dash_m_unittest_pins_env_even_when_poisoned(self):
        """A unittest-invoked run cannot reach a live base URL even with a
        hostile LLM_* environment inherited from the caller (TEST-NET-1 is
        never contacted: the pin must override it before elixis reads env)."""
        env = {
            "PATH": os.environ.get("PATH", ""),
            "LLM_PROVIDER": "zai",
            "LLM_BASE_URL": "http://192.0.2.1:11434",
            "LLM_API_KEY": "dummy-hermeticity-key",
        }
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "tests.test_hermeticity.ProbeOnly", "-v"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(
            proc.returncode, 0, f"probe failed:\n{proc.stdout}\n{proc.stderr}"
        )
        self.assertIn(
            "test_unittest_invocation_is_pinned_to_dead_endpoint", proc.stderr
        )


if __name__ == "__main__":
    unittest.main()
