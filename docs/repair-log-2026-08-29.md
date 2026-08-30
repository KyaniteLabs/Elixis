# Repair log: engine LLM core + naming discipline (2026-08-29)

PR #143 (squash `7ffce01`). One session, four outcomes: the engine's LLM
core runs live, the naming discipline is machine-encoded, the receipts feed
exists, and the whole lane is proven by golden runs with receipts in
`.elixis/runs/golden-*.md`.

## What was broken

1. **No seat.** No `.env` existed, nothing loaded one even if present, and
   the default model `gemma-4b` matched nothing on any reachable server.
   Every documented run rode the heuristic fallback ("0 LLM variants" in
   ELIXIS-TITLES section 1).
2. **The local ollama stack was a trap** (three KeepAlive services warring
   over 11434, a 5-minute restart metronome, a long-generation crash cliff
   at ~380 output tokens). Policy now: no ollama in any form; registry
   seats only.
3. **Latent engine bugs:** `chat()` dropped `think=False` on cloud paths
   (thinking models burn the whole budget on reasoning blocks and return
   zero text); `parse_llm_json_array` hard-failed on max_tokens-truncated
   arrays; the extraction prompt assumed persona brain-dumps and returned
   `[]` against ledger corpora.
4. **The discipline lived only in prompts and experiment docs.**

## The seat

The GLM coding-plan seat from the pushed dispatch registry
(`~/.sinter/config.json` roles/harness, `glmCodingPlanSeat: true`):
Anthropic wire @ `api.z.ai/api/anthropic`, model `glm-5.3`, key only in
gitignored `.env`. The coding-plan key is bound to that endpoint (the
OpenAI-compatible route rejects it). Requires: thinking disabled for
classification calls, thinking blocks merged out of text output.

## Machine-encoded discipline

`elixis/discipline.py` — kill lists (house + object profiles), prosody
rubric ST/EC/SO/SY scored 1-5 from string features, deniability gate,
plate unit. Calibration receipts: SY reproduces all five documented pair
cells of ELIXIS-INWORLD-GLASS round 2; ST/EC/SO land within one point of
every human-judged cell with field ordering intact. See
`docs/naming-discipline.md` for the spec.

## Learnings (durable)

- **Thinking-model seats need think-routing, not just prompts.** A seat
  that "works" on a smoke test can return zero text on real calls when
  thinking consumes the token budget. Forward the think flag through every
  provider adapter; test both paths.
- **Empty output is a prompt-schema failure mode, not an availability
  failure.** The model returned `[]` (2 tokens) because the schema
  demanded persona entities from a watch-ledger. Few-shot examples of the
  actual input shape fixed it; the telemetry `source` field is what tells
  you which path you rode ("llm" vs "heuristic" vs "empty_response").
- **Salvage truncated JSON.** max_tokens cuts arrays mid-element; closing
  at the last parseable `}` recovered every real extraction. Strict parse
  = silent fallback to heuristics.
- **A metronomic restart pattern in server logs means a watchdog/port
  war, not flaky hardware** — check `Listening on` timestamps before
  debugging the model. Local ollama on this Mac is retired; do not re-seat.
- **Remotes go stale after repo renames.** Both `origin` and
  `upstream-github` pointed at dead `Fugax` paths; "push to create is not
  enabled" was the tell. Fixed to `KyaniteLabs/Elixis` on both hosts.
- **Merge-then-PR, PR-then-race:** merge immediately after force-push
  fails with "merge commit cannot be cleanly created" even when the PR is
  clean — GitHub hasn't recomputed mergeability. Re-check state before
  concluding conflict.
- **Golden runs with receipts are the only proof that counts.** Unit
  tests proved the code; the 55-60s golden runs (extraction_source=llm,
  150 tok/s, validated plate) proved the system.

## Golden run shape (latest at time of merge)

55 months of ledger -> 4000-char seed -> 56 LLM-extracted beads ->
Wikipedia enrichment -> 24 patterns, 123 isomorphic threads, 1 tension ->
14 LLM naming variants adjudicated by the discipline -> plate (silk +
name + subtitle) validated -> 3357-char SOUL.md. ~60 seconds.
