"""Test hermeticity: never touch a real LLM seat.

A developer's .env may point the engine at a live local model (and the
.env loader in elixis/__init__.py reads it). Tests pin a dead endpoint so
every fallback path is exercised deterministically and no test billows to
minutes on a 3 tok/s seat.
"""

import os

os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:9"  # closed port: instant refusal
os.environ.setdefault("LLM_MODEL", "stub-model")
