# Elixis

A local-first pattern synthesis engine: turn a messy reference brief, repository or folder into a Source Corpus, beads, threads, patterns/tensions, then resolve that graph into identity, brand voice, design direction, naming or a Market Kit. SOUL.md is one output lens, not the whole product.

## Existing experience

- Browser reference-brief interface with identity/brand/design lenses; Python CLI, HTTP API and optional MCP adapter reach the same engine.
- Read-only source ingestion with ranked/accepted/rejected evidence, bounded file/signal sizes and persisted ingestion runs. GitHub ingestion can fetch remote metadata; it does not execute the target project's code.
- Four-phase synthesis, local entity/pattern knowledge, optional Wikipedia enrichment and model-backed generation; Market Kit orchestrates corpus, naming, brand/design outputs and rendered artifacts.
- Traces, output validation and backup/restore helpers. Bundled traits, entity types, domains, relationships, taxonomy and archetypes support synthesis; they are not independently validated identity/market research datasets.

## Evidence and boundaries

Actual CLI version/help and local ingestion of a synthetic README passed; Source Corpus contained the supplied project evidence. Chromium rendered the real root HTTP handler with all non-GET requests blocked. No synthesis/model, remote source ingestion, private folder, backup/restore or deployment ran. These checks do not establish output quality or user acceptance.

“Local-first” describes control/data paths, not guaranteed offline inference: configured providers/enrichment can transmit references and code-derived context. The production server binds all interfaces by default; keep deployment private/authenticated appropriately. Name suggestions are not trademark/domain clearance and generated identity/design output is not factual characterization. See [ARCHITECTURE.md](ARCHITECTURE.md) and [README.md](README.md).
