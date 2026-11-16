# Elixis architecture

```text
brief -> engine declaration -> elaboration/enrichment -> connection/pattern graph -> lens
folder/GitHub -> ingest -> Source Corpus -> Market Kit orchestration -> artifacts
CLI / HTTP / MCP -------------------------^ shared Python package
```

[engine.py](elixis/engine.py) holds phase/state/bead/thread orchestration with injectable/lazy dependencies. Entity, research, graph, pattern, lens and naming modules perform its stages. Identity synthesis, brand and design share graph evidence but produce different artifacts. [market.py](elixis/market.py) explicitly ingests, runs the engine, invokes lenses/naming, renders outputs and persists the result; it is not just a folder formatter.

[ingest.py](elixis/ingest.py) walks a local source or fetches GitHub evidence, bounds text/file/signal volume, filters/ranks signals, records rejections and saves `.elixis/ingestion-runs`. Read-only refers to source extraction, not absence of run artifacts or remote requests. [app.py](app.py) implements a stdlib threaded HTTP/SSE service, body/concurrency limits, security headers, routes and shutdown draining; `__main__` and MCP expose the same package. There are no mandatory third-party Python requirements.

## Risk / failure boundaries

- Treat references/code as untrusted prompt input and private data. Filtering/validation is not a guarantee against injection; external enrichment and configured LLM calls can disclose context or cost money.
- Signal limits, rejected evidence, failed enrichment and fallback generation change confidence. A plausible artifact does not prove scientific psychological inference, truthful positioning, design quality or name availability.
- HTTP main binds `0.0.0.0`, while CORS/admin-key settings govern different routes; do not assume localhost-only/authenticated deployment from “local-first”. Saturated pipelines/SSE timeouts can produce incomplete outputs.
- Trace/backups preserve raw/derived reference information; restore/cleanup can overwrite/delete files. Production shutdown invokes auto-backup. Preserve provenance and review retention/backup operations before using real workspaces.

## Docs verification

Read purpose/rules, engine, ingest, Market Kit and HTTP entry/lifecycle. CLI version/help and synthetic local Source Corpus ingestion passed with artifacts in the session evidence directory. Real HTTP Handler root rendered in Chromium on a loopback-only harness (production main/shutdown backup not run); non-GET blocked. No model, synthesis, external research, private source, backup cleanup/restore or release. Independent user/output-quality acceptance remains open; runtime unchanged, revert docs for rollback.
