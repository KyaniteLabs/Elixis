---
name: elixis
description: Use Elixis for local-first pattern synthesis from source material into identity, brand voice, design-system direction, naming research, Source Corpus ingestion, and Market Kit outputs through CLI, HTTP API, or MCP tools.
---

# Elixis

Use Elixis when an agent needs to turn scattered reference material, a GitHub repository, or a local folder into structured identity, brand, design, naming, or Market Kit outputs. Elixis builds a curated Source Corpus, resolves a pattern graph, and emits lens-specific results.

## Start Here

- Read `../../README.md` for installation, CLI, HTTP API, and MCP examples.
- Read `../../CONTEXT.md` for domain language such as Source Target, Source Corpus, Corpus Signal, Market Kit, and Artifact Tier.
- Read `../../llms.txt` for a compact public summary.
- Use `../../elixis/mcp_server.py` when you need exact MCP tool names and schemas.
- Use `../../elixis/__main__.py` when you need exact CLI command names and flags.

## Choose A Surface

- CLI: best for local operator work such as `ingest`, `run`, `extract`, `patterns`, `name`, `corpus inspect`, and `serve`.
- MCP: best for agent hosts that need `ingest_source`, `create_market_kit`, `run_game`, `create_soul`, `extract_entities`, `analyze_patterns`, `research_name`, or `name_from_identity`.
- HTTP API: best for local app/server workflows after `python -m elixis serve`.

## Workflow

1. Identify the input:
   - raw reference text,
   - a local folder path,
   - a public or private GitHub repository URL,
   - an existing ingestion run ID.
2. Choose the output lens:
   - `identity` for persona, SOUL-style, or self-model documents,
   - `brand` for positioning, voice, and messaging,
   - `design` for visual system direction,
   - Market Kit for bundled naming, positioning, brand, messaging, design, and evidence.
3. For repository or folder work, run ingestion first and keep the distinction between Source Target, Source Corpus, Corpus Signal, and Artifact.
4. Request Artifact Tiers only when needed. Use `markdown`, `html`, `css`, or `market-page` intentionally instead of assuming all artifacts should be rendered.
5. Preserve provenance and review sensitive-candidate behavior before using outputs in public strategy or launch material.

## CLI Examples

```bash
elixis ingest --github https://github.com/owner/repo
elixis ingest --path ./my-project --kit --artifact markdown --artifact market-page
elixis corpus inspect <run-id>
elixis run --file notes.md --lens brand --json
elixis patterns --file notes.md
elixis name --name "Elixis" --context "AI pattern synthesis engine"
elixis mcp
```

## MCP Setup

```json
{
  "mcpServers": {
    "elixis": {
      "command": "python",
      "args": ["-m", "elixis.mcp_server"]
    }
  }
}
```

## Guardrails

- Do not treat an entire repository as raw prompt text. Build a Source Corpus first.
- Do not include hidden files, large files, issues, PRs, commits, visual analysis, or code evidence unless they improve the requested output and the user allowed that evidence class.
- Do not silently render HTML/CSS artifacts for every run; artifact generation is an explicit operator choice.
- Treat Elixis outputs as synthesized recommendations grounded in evidence, not as final trademark, legal, or market validation.
