# Elixis product

## Purpose and core experience

Elixis turns a user's references, influences and product evidence into structured
creative direction. The core is a reusable cross-domain synthesis engine, not
just a SOUL.md generator. Operators supply text or select a GitHub repository or
local folder; Elixis builds a curated **Source Corpus**, connects references into
patterns and threads, and resolves them into useful output. Domain vocabulary
lives in [`CONTEXT.md`](CONTEXT.md); execution lives in
[`elixis/engine.py`](elixis/engine.py), [`ingest.py`](elixis/ingest.py) and
[`market.py`](elixis/market.py).

## Implemented experience

- **Synthesis:** declaration, elaboration, connection and resolution; identity,
  brand and design lenses produce identity documents, voice guidance and design
  direction ([`elixis/lenses/`](elixis/lenses/), [`synthesis.py`](elixis/synthesis.py)).
- **Evidence ingestion:** GitHub/local-folder selection, candidate filtering and
  scoring, provenance, included/rejected evidence, budgets and persisted results
  ([`ingest.py`](elixis/ingest.py)). This is selected evidence, not a promise to
  understand every file or permission to execute the selected project's code.
- **Market Kits:** orchestrated naming, positioning, brand voice, messaging and
  design-system direction; structured results and optional rendered artifacts
  ([`market.py`](elixis/market.py)). Naming research and discipline checks live in
  [`naming.py`](elixis/naming.py) and [`discipline.py`](elixis/discipline.py).
- **Operator surfaces:** CLI ([`__main__.py`](elixis/__main__.py)), HTTP/JSON and
  SSE ([`app.py`](app.py), [`openapi.yaml`](openapi.yaml)), stdio MCP
  ([`mcp_server.py`](elixis/mcp_server.py)), browser landing/live-demo template
  ([`landing.html`](elixis/templates/landing.html)), static public documentation
  ([`docs/index.html`](docs/index.html)) and the
  [public agent skill](skills/elixis/SKILL.md).
- **Supporting features:** translation, output validation, process traces,
  diagnostics and backups ([`translate.py`](elixis/translate.py),
  [`quality.py`](elixis/quality.py), [`traces.py`](elixis/traces.py),
  [`backup.py`](elixis/backup.py)).

## Bundled reference data

[`elixis/data/`](elixis/data/) contains `archetypes.json` (pattern definitions),
`characters.jsonl` (annotated fictional/historical/cultural references),
`domains.json` (domains and isomorphisms), `entity_types.json`,
`relationships.json`, `taxonomy.json` (naming-oriented taxonomic references), and
`traits.json`. [`knowledge.py`](elixis/knowledge.py) loads local knowledge.
These are shipped reference resources, not an independently validated benchmark
or evidence that generated personality/archetype scores are scientific findings.
The repository includes an Apache-2.0 [LICENSE](LICENSE); no new rights to
third-party works or user-provided corpora are asserted here.

## Limits and plans are not shipped guarantees

Local-first does not mean offline or confidential by default: configured model
providers and enrichment can receive content; run records may retain it. Input
filters and naming checks are not guarantees of secrecy, trademark clearance,
factual accuracy or creative quality. More output forms and domain ambitions in
`CONTEXT.md` are not automatically implemented contracts. Consult current source
and [`qa/foundation-gaps.md`](qa/foundation-gaps.md): browser/live-model quality,
production deployment and mirror adoption remain unverified in this change.
Product approval of this document is required before Security's merge review.
