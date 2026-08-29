"""Elixis pattern synthesis engine."""

import os as _os

__version__ = "1.0.0"


def _load_dotenv():
    """Load .env from the repo root into os.environ (values already set win).

    Stdlib-only replacement for python-dotenv. Ignores comments and blank
    lines; does not expand values; never overrides existing environment
    variables so real deployments keep control.
    """
    path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), ".env")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in _os.environ:
                    _os.environ[key] = value
    except Exception:
        pass  # no/unreadable .env — fall back to process environment and defaults


_load_dotenv()
