"""Elixis test suite.

Hermeticity pin (#144): this lives in the package __init__ — not only in
conftest.py — so BOTH runners apply it (plain `python -m unittest` never
imports conftest.py). The pin overwrites any inherited LLM_* environment
before `elixis` is imported, and the elixis .env loader never overrides
values that are already set, so no test run can follow a developer's live
.env LLM seat. Tests pin a dead endpoint so every fallback path is
exercised deterministically and no test billows to minutes on a 3 tok/s
seat.
"""

import os

os.environ["ELIXIS_TEST"] = "1"
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:9"  # closed port: instant refusal
os.environ.setdefault("LLM_MODEL", "stub-model")
