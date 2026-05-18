# Elixis

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/KyaniteLabs/Elixis/actions/workflows/ci.yml/badge.svg)](https://github.com/KyaniteLabs/Elixis/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/KyaniteLabs/Elixis.svg)](https://github.com/KyaniteLabs/Elixis/stargazers)

> A Glass Bead Game engine for turning raw references into structured outputs: identity, brand voice, design systems, naming direction, and SOUL.md documents.

Elixis is a cross-domain synthesis engine. It transforms raw brain dump text — references, influences, values, works, people, places, aesthetics, constraints — into a pattern graph, then resolves that graph through output lenses. The identity lens generates **SOUL.md** documents for OpenClaw and Soul Spec, but SOUL.md is one output mode, not the whole scope. Current lenses also produce brand voice guidance and design-system direction, with naming research built on the same graph.

## TL;DR

Elixis takes a messy constellation of references and turns it into usable structure: beads, threads, archetypal patterns, tensions, and a resolved output. Choose the identity lens for SOUL.md, the brand lens for voice guidelines, the design lens for design tokens and principles, or the naming tools for semantically aligned names.

**AI discovery:** [`llms.txt`](llms.txt) provides a compact project summary for AI assistants and search crawlers.

## What it does

| Phase / Surface | Function |
|-----------------|----------|
| Declaration | Parses references, people, works, concepts, and values into beads |
| Elaboration | Enriches beads with local knowledge and external context |
| Connection | Builds threads, cross-domain bridges, tensions, and archetypal patterns |
| Resolution | Uses lenses to generate identity, brand, design, or future output forms |
| Naming | Generates and scores names against the same pattern graph |
| Translation | Checks cross-language risk and translates generated output |
| Validation | Input sanitization, prompt-injection filtering, output validation |
| Traces & Backups | Preserves synthesis runs and enables rollback |

## Repository map

```text
elixis/              Core Python package
  entities.py           Entity extraction and structured terms
  engine.py             Four-phase Glass Bead Game orchestrator
  lenses/               Output lenses: identity, brand, design
  patterns.py           Archetypal pattern discovery and graph
  synthesis.py          SOUL.md identity lens implementation
  translate.py          Translation and cross-language checks
  research.py           Wikipedia entity enrichment
  naming.py             Name research and variant generation
  llm.py                LLM interface (Ollama / OpenAI-compatible)
  validation.py         Input sanitization and validation
  traces.py             Run trace capture and diagnostics
  backup.py             Backup and restore helpers
  logging_config.py     Structured logging setup
  templates/            Landing page UI with live multi-lens demo
tests/                  Unit and integration tests
app.py                  HTTP server entry point (stdlib, port 3110)
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Configuration

Copy the example environment file and set provider/runtime values as needed:

```bash
cp .env.example .env
```

## Development

```bash
pip install -r requirements.txt
python -m unittest discover tests/ -v
```

## MCP Server (AI Agent Native)

Elixis exposes an MCP server so any MCP-compatible AI assistant can use it directly:

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

Available tools: `create_soul`, `run_game`, `extract_entities`, `analyze_patterns`, `translate_text`, `research_name`, `name_from_identity`.

Works with Claude Code, Cursor, Windsurf, and any MCP client.

## Best for

- Mapping a constellation of cultural references into beads, threads, patterns, and tensions.
- Resolving the same pattern graph into identity, brand voice, design direction, or naming options.
- Creating AI agent personas for OpenClaw, SoulClaw, or any SOUL.md-compatible system.
- Checking whether a name or phrase carries unwanted cross-language meaning.
- Preserving creative reasoning instead of losing it in a chat transcript.

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
Elixis is a Glass Bead Game synthesis engine. It turns raw reference material into a pattern graph and resolves that graph through lenses for identity, brand, design, naming, and SOUL.md output.

**How do I create an output?**
Start the server with `python app.py`, open `http://localhost:3110`, enter references and influences, choose a lens, and run the game. The identity lens generates SOUL.md; the brand and design lenses generate different documents from the same graph.

**What LLM providers does Elixis support?**
Elixis works with any local LLM via Ollama (default: Gemma) or any OpenAI-compatible API (OpenAI, Anthropic via proxy, LM Studio, etc.). It falls back to template-based synthesis when no LLM is available.

**Can Elixis check cross-language risks?**
Yes. The translation module supports 28+ languages with streaming support, file-based caching, and automatic language detection.

**Is Elixis free and open source?**
Yes. Elixis is MIT-licensed and uses zero external Python dependencies (stdlib only).

**What is the Soul Spec?**
Soul Spec is an open standard for AI agent personas. Elixis can generate SOUL.md documents compatible with Soul Spec v0.5, OpenClaw, and any framework that reads markdown-based identity files, but Elixis is not limited to identity files.

## License

See [LICENSE](LICENSE).
