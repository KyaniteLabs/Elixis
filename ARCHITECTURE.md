# Elixis architecture

Elixis is a Python-stdlib pattern-synthesis application: Source Corpus input becomes
identity, brand voice, design direction, naming research, or Market Kit output.
It is local-first, **not necessarily offline**. Engineering owns implementation,
security-sensitive configuration, tests and automation; Product owns public copy,
domain descriptions, branding and the public skill. The machine-readable owner
map is [`qa/architecture-paths.json`](qa/architecture-paths.json).

## Components and one request's journey

- [`app.py`](app.py) serves HTTP, the landing template, JSON routes and SSE.
  [`elixis/__main__.py`](elixis/__main__.py) supplies the CLI;
  [`elixis/mcp_server.py`](elixis/mcp_server.py) supplies stdio MCP tools.
- A synthesis POST passes body/input/lens validation in `app.py` and
  [`elixis/validation.py`](elixis/validation.py), then invokes
  [`GameEngine.run_full`](elixis/engine.py): **declare → elaborate → connect → resolve**.
  [`entities.py`](elixis/entities.py) extracts references; [`research.py`](elixis/research.py)
  enriches them; [`patterns.py`](elixis/patterns.py), [`graph.py`](elixis/graph.py)
  and [`thread.py`](elixis/thread.py) build patterns and cross-domain links;
  [`lenses/`](elixis/lenses/) selects identity, brand or design generation.
- [`llm.py`](elixis/llm.py) crosses the configured Ollama, OpenAI-compatible or
  Anthropic HTTP boundary. Responses feed resolution; `app.py` saves the run
  through [`traces.py`](elixis/traces.py) and returns output, timings and process
  trace. [`market.py`](elixis/market.py) orchestrates Market Kits;
  [`ingest.py`](elixis/ingest.py) handles corpus ingestion;
  [`naming.py`](elixis/naming.py) and [`discipline.py`](elixis/discipline.py)
  handle naming and machine-checked constraints.

## Trust and persistence

Inputs, imported material, retrieved enrichment and model text are untrusted.
Configured external inference can receive user content; “local-first” is not a
privacy guarantee. [`elixis/data/`](elixis/data/) is the bundled knowledge corpus.
`traces.py` writes `.elixis/traces/`, `.elixis/runs/` and `requests.log` next to
`app.py`; run records and prompt/response previews can contain private text.
[`backup.py`](elixis/backup.py) manages archive/restore paths, including
`ELIXIS_DATA_DIR` and `ELIXIS_BACKUP_DIR` overrides. Treat backups as equally
sensitive. Admin routes in `app.py` require `ADMIN_API_KEY` (503 if unconfigured,
401 if unauthorized); this is not blanket authentication of synthesis routes.
CORS/CSP and concurrency/body limits are additional boundaries, not identity.

## Risky changes, failures and verification

Review HTTP validation/admin authorization, provider configuration, trace storage,
backup restore, prompt/graph/lens semantics and deployment together with their
callers. Observable failures include input rejection, exhausted pipeline capacity,
provider errors, fallback/keyword-only output, and filesystem failures; inspect
structured logs, timings and process traces, not output presence alone.
[`Dockerfile`](Dockerfile), [`docker-compose.yml`](docker-compose.yml),
[`traefik/`](traefik/) and [`scripts/deploy.sh`](scripts/deploy.sh) define deployment.

Run `LLM_PROVIDER=ollama LLM_BASE_URL=http://127.0.0.1:9 python3 -m unittest discover -s tests`
(or the pytest CI runner). [`tests/`](tests/) covers engine, mocked providers,
HTTP/admin boundaries, backups, CLI/MCP and golden-run tooling.
[`tests/test_http_e2e.py`](tests/test_http_e2e.py) adds real-loopback HTTP checks;
these are not browser or live-model quality evidence.
[`qa/foundation-gaps.md`](qa/foundation-gaps.md) records measured results, CI and
mirror limitations. No all-estate adoption is implied by this repository's PR.
