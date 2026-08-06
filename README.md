# Elixis

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/KyaniteLabs/Elixis/actions/workflows/ci.yml/badge.svg)](https://github.com/KyaniteLabs/Elixis/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/KyaniteLabs/Elixis.svg)](https://github.com/KyaniteLabs/Elixis/stargazers)

> A local-first AI pattern synthesis engine for turning raw references, repositories, and folders into Source Corpora, Market Kits, identity, brand voice, design systems, and naming direction.

Elixis is a cross-domain synthesis engine. It transforms raw brain dump text, GitHub repositories, and local folders — references, influences, values, works, people, places, aesthetics, constraints, documentation, metadata, and public interfaces — into a curated Source Corpus and pattern graph, then resolves that graph into usable market, brand, design, naming, and identity outputs. The identity lens generates **SOUL.md** documents for OpenClaw and Soul Spec, but SOUL.md is one output mode, not the whole scope.

## TL;DR

Elixis takes a messy constellation of references or a real product repository and turns it into usable structure: Corpus Signals, beads, threads, archetypal patterns, tensions, and resolved outputs. Use Source Corpus ingestion to gather quality-ranked evidence, Market Kit orchestration for naming/positioning/messaging/design direction, the brand lens for voice guidelines, the design lens for design tokens and principles, the naming tools for semantically aligned names, or the identity lens for SOUL.md. It is bigger than identity-file generation: SOUL.md is a compatibility surface, while the core product is a reusable synthesis engine.

**AI discovery:** [`llms.txt`](llms.txt) provides a compact project summary for AI assistants and search crawlers.

**Public landing page:** https://kyanitelabs.github.io/Elixis/

## Canonical Names

Elixis has one active product and package name:

| Surface | Name |
|---------|------|
| Product and repository | Elixis |
| Python distribution, import package, CLI, Docker service | `elixis` |
| Compatibility targets, not package names | OpenClaw, SoulClaw, Soul Spec, SOUL.md |

Historical planning notes are preserved under `archive/` for continuity only. They do not define the current package, product, or public positioning.

## What it does

| Phase / Surface | Function |
|-----------------|----------|
| Declaration | Parses references, people, works, concepts, and values into beads |
| Elaboration | Enriches beads with local knowledge and external context |
| Connection | Builds threads, cross-domain bridges, tensions, and archetypal patterns |
| Resolution | Uses lenses to generate identity, brand, design, or future output forms |
| Naming | Generates and scores names against the same pattern graph |
| Source Corpus | Ingests GitHub repositories or local folders into quality-scored evidence |
| Market Kit | Orchestrates naming, positioning, brand, marketing, and design direction |
| Validation | Input sanitization, prompt-injection filtering, output validation |
| Traces & Backups | Preserves synthesis runs and enables rollback |

## Repository map

```text
elixis/              Core Python package
  __main__.py           Operator CLI: serve, run, extract, patterns, name, ingest, corpus, mcp
  entities.py           Entity extraction and structured terms
  engine.py             Four-phase pattern synthesis orchestrator
  lenses/               Output lenses: identity, brand, design
  patterns.py           Archetypal pattern discovery and graph
  synthesis.py          SOUL.md identity lens implementation
  translate.py          Text localization helpers and language detection
  research.py           Wikipedia entity enrichment
  naming.py             Name research and variant generation
  llm.py                LLM interface (Ollama / OpenAI-compatible / Anthropic)
  validation.py         Input sanitization and validation
  ingest.py             Source Corpus ingestion for GitHub repositories and local folders
  market.py             Market Kit orchestration from Source Corpus evidence
  traces.py             Run trace capture and diagnostics
  backup.py             Backup and restore helpers
  logging_config.py     Structured logging setup
  mcp_server.py         Optional stdio adapter for MCP-compatible assistants
  templates/            Landing page UI with live multi-lens demo
tests/                  Unit and integration tests
app.py                  HTTP server entry point (stdlib, port 3110)
openapi.yaml            HTTP API contract
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Operator surfaces

MCP is an integration adapter, not the product scope. The supported operator contract is the same engine behind three local-first surfaces:

| Surface | Command / contract | Use |
|---------|--------------------|-----|
| CLI | `python -m elixis run --text "Athena, Batman, Musashi" --lens brand` | Local scripting and one-shot synthesis |
| HTTP API | `python -m elixis serve --port 3110`; see `openapi.yaml` | Browser UI, services, and external clients |
| MCP stdio | `python -m elixis mcp` | AI assistants that need tool access to the same engine |

Useful CLI commands:

```bash
python -m elixis --version
python -m elixis serve --port 3110
python -m elixis run --file references.txt --lens design --json
python -m elixis extract --text "Athena, Batman, Miyamoto Musashi"
python -m elixis patterns --stdin < references.txt
python -m elixis name --name Elixis --context "local AI synthesis tool"
python -m elixis ingest --path . --kit --artifact markdown
python -m elixis ingest --github https://github.com/KyaniteLabs/Elixis --kit --artifact html
python -m elixis corpus inspect <run_id>
python -m elixis mcp
```

## Source Corpus and Market Kits

Elixis can point at a GitHub repository or local folder and build a **Source Corpus**: a curated, auditable evidence bundle selected because it improves output quality. The corpus is not a raw dump of every readable file. Each Corpus Signal is scored for relevance, distinctiveness, authority, lens utility, provenance, freshness, and noise risk.

The resulting **Ingestion Result** is the shared structured contract across CLI, HTTP API, and MCP. It contains the Source Target, included and rejected signals, scoring summary, process trace, and, when requested, a **Market Kit** with naming directions, positioning, audience/category notes, brand voice, messaging pillars, landing-page copy angles, color palettes, typography, spacing, borders, shadows, visual motifs, and design-system direction.

HTML/CSS are optional artifact tiers for high-quality human review. They are generated only when explicitly requested or when visual presentation is critical; structured JSON remains the source of truth.

## Configuration

Copy the example environment file and set provider/runtime values as needed:

```bash
cp .env.example .env
```

For GLM 5.1 cloud inference, use the OpenAI-compatible provider shape:

```bash
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.z.ai/api/paas/v4
LLM_MODEL=glm-5.1
ZAI_API_KEY=...
```

## Development

```bash
pip install -r requirements.txt
python -m unittest discover tests/ -v
```

## Best for

- Mapping a constellation of cultural references into beads, threads, patterns, and tensions.
- Turning a GitHub repository or local folder into a quality-scored Source Corpus.
- Generating a Market Kit with naming, positioning, messaging, brand, and visual design direction.
- Resolving the same pattern graph into identity, brand voice, design direction, or naming options.
- Creating AI agent personas for OpenClaw, SoulClaw, or any SOUL.md-compatible system.
- Inspecting process evidence: model, phases, pattern scores, entity support, bridges, timings, and fallbacks.

## Works With

| System | How |
|--------|-----|
| [OpenClaw](https://github.com/openclaw/openclaw) | Drop SOUL.md into `~/.openclaw/workspace/` |
| [SoulClaw](https://github.com/clawsouls/soulclaw) | Native Soul Spec v0.5 support |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Paste into `~/.claude/CLAUDE.md` |
| [Cursor](https://cursor.sh/) | Paste into `.cursorrules` |
| [Windsurf](https://codeium.com/windsurf) | Paste into `.windsurfrules` |
| Any LLM | Prepend SOUL.md to system prompt |

## FAQ

**What is Elixis?**
Elixis is a local-first AI pattern synthesis engine. It turns raw reference material into a pattern graph and resolves that graph through lenses for identity, brand voice, design systems, naming research, and lens-specific outputs.

**How do I create an output?**
Start the server with `python app.py`, open `http://localhost:3110`, enter references and influences, choose a lens, and run the synthesis. The identity lens generates SOUL.md; the brand and design lenses generate different documents from the same graph.

**What LLM providers does Elixis support?**
Elixis works with local LLMs via Ollama, OpenAI-compatible APIs, and Anthropic's Messages API. It falls back to template-based synthesis when no LLM is available.

**Is Elixis free and open source?**
Yes. Elixis is MIT-licensed and uses zero external Python dependencies (stdlib only).

**What is the Soul Spec?**
Soul Spec is an open standard for AI agent personas. Elixis can generate SOUL.md documents compatible with Soul Spec v0.5, OpenClaw, and any framework that reads markdown-based identity files, but Elixis is not limited to identity files.

## License

See [LICENSE](LICENSE).
