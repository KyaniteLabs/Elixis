# BUG-SMELL-REGISTRY — Elixis

Per the standing CEO law (2026-08-18): every bug or smell is noted here
the moment it is noticed — one line + timestamp + surface. No triage at
note-time. Batch reaction runs at critical-path wait-points, >=3 smells,
or end of day.

| noted (UTC) | surface | smell / bug | status |
|---|---|---|---|
| 2026-08-29 | elixis/llm.py | `chat()` dropped `think=False` on cloud provider paths; thinking models returned zero text on real calls while smoke tests passed | FIXED (PR #143) |
| 2026-08-29 | elixis/parsing.py | strict JSON parse silently discarded max_tokens-truncated arrays -> heuristic fallback masqueraded as LLM output | FIXED (PR #143, salvage) |
| 2026-08-29 | elixis/entities.py | extraction prompt schema-fit: `[]` (2-token) responses on ledger corpora; telemetry source field disambiguated | FIXED (PR #143, few-shot) |
| 2026-08-29 | infra/ollama | three KeepAlive services war over 11434; 5-min restart metronome; long-generation crash cliff ~380 tokens | DISPATCHED (#141); ollama retired by policy |
| 2026-08-29 | git remotes | both remotes stale post-rename (`Fugax` -> `Elixis`); push-to-create error was the tell | FIXED (both remotes) |
| 2026-08-29 | review process | fallback wrapper was dead code (inner client swallowed the exceptions the wrapper waited for); no test exercised the path | FIXED (PR #143 review cycle; regression tests added) |
| 2026-08-29 | tests/conftest.py | hermeticity holds only under pytest; `python -m unittest` bypasses conftest and can hit a live seat | OPEN (task board) |
| 2026-08-29 | scripts/golden_run.py | personal absolute corpus path hardcoded in a committed script (username leak) | FIXED (ELIXIS_CORPUS env; .env) |
