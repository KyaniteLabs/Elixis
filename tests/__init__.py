"""Elixis test suite.

`python -m unittest` imports this package and never loads conftest.py.
Keep this pin identical to tests/conftest.py so neither runner can dial
a live LLM seat. Values already in the environment lose: the .env loader
does not override them.
"""

import os

os.environ["ELIXIS_TEST"] = "1"
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:9"  # closed port: instant refusal
os.environ.setdefault("LLM_MODEL", "stub-model")
