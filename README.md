# SoulCraft

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/KyaniteLabs/SoulCraft/actions/workflows/ci.yml/badge.svg)](https://github.com/KyaniteLabs/SoulCraft/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/KyaniteLabs/SoulCraft.svg)](https://github.com/KyaniteLabs/SoulCraft/stargazers)

> AI-powered identity synthesis for OpenClaw-compatible SOUL.md documents. Transform brain dump text into structured AI agent personas.

SoulCraft is a companion tool for the [OpenClaw](https://github.com/openclaw/openclaw) and [Soul Spec](https://github.com/clawsouls/soulspec) ecosystem. It transforms raw brain dump text — references, influences, values, context — into structured **SOUL.md** identity documents through a 3-stage pipeline: entity extraction, archetypal pattern analysis, and LLM-assisted synthesis. Works with any local or remote LLM via Ollama or OpenAI-compatible APIs.

## TL;DR

SoulCraft takes what you love, admire, or identify with — people, works, concepts, values — and synthesizes it into a complete AI persona document. The output is a SOUL.md file compatible with OpenClaw, SoulClaw, Claude Code, Cursor, and any system that reads markdown-based agent identities. No prompt engineering required. Drop in your influences, get back a soul.

**AI discovery:** [`llms.txt`](llms.txt) provides a compact project summary for AI assistants and search crawlers.

## What it does

| Stage | Function |
|-------|----------|
| Entity Extraction | Parses references, people, works, concepts from raw text |
| Pattern Analysis | Maps entities to 12 archetypal patterns (transformation, power, outsider, shadow, trickster, etc.) |
| SOUL.md Synthesis | Generates a complete identity document with voice, worldview, principles, boundaries |
| Translation | Checks cross-language risks and translates SOUL.md output |
| Validation | Input sanitization, prompt injection detection, output validation |
| Traces & Backups | Preserves creative reasoning and enables rollback |

## Repository map

```text
soulcraft/              Core Python package
  entities.py           Entity extraction and structured terms
  patterns.py           Archetypal pattern discovery and graph
  synthesis.py          SOUL.md synthesis (LLM + template fallback)
  translate.py          Translation and cross-language checks
  research.py           Wikipedia entity enrichment
  naming.py             Name research and variant generation
  llm.py                LLM interface (Ollama / OpenAI-compatible)
  validation.py         Input sanitization and validation
  traces.py             Run trace capture and diagnostics
  backup.py             Backup and restore helpers
  logging_config.py     Structured logging setup
  templates/            Landing page UI with live demo
tests/                  Unit and integration tests (80 tests)
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

SoulCraft exposes an MCP server so any MCP-compatible AI assistant can use it directly:

```json
{
  "mcpServers": {
    "soulcraft": {
      "command": "python",
      "args": ["-m", "soulcraft.mcp_server"]
    }
  }
}
```

Available tools: `create_soul`, `extract_entities`, `analyze_patterns`, `translate_text`, `research_name`.

Works with Claude Code, Cursor, Windsurf, and any MCP client.

## Best for

- Creating AI agent personas for OpenClaw, SoulClaw, or any SOUL.md-compatible system.
- Synthesizing identity from cultural influences, heroes, values, and references.
- Checking whether a name or phrase carries unwanted cross-language meaning.
- Preserving creative reasoning instead of losing it in a chat transcript.
- Generating portable persona files that work across Claude Code, Cursor, ChatGPT, and Gemini.

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

**What is SoulCraft?**
SoulCraft is a companion tool for the OpenClaw ecosystem that transforms brain dump text into structured SOUL.md identity documents for AI agents.

**How do I create a SOUL.md file?**
Start the server with `python app.py`, open `http://localhost:3110`, enter your references and influences in the text area, and click Extract. The 3-stage pipeline generates a complete SOUL.md document.

**What LLM providers does SoulCraft support?**
SoulCraft works with any local LLM via Ollama (default: Gemma) or any OpenAI-compatible API (OpenAI, Anthropic via proxy, LM Studio, etc.). It falls back to template-based synthesis when no LLM is available.

**Can SoulCraft check cross-language risks?**
Yes. The translation module supports 28+ languages with streaming support, file-based caching, and automatic language detection.

**Is SoulCraft free and open source?**
Yes. SoulCraft is MIT-licensed and uses zero external Python dependencies (stdlib only).

**What is the Soul Spec?**
Soul Spec is an open standard for AI agent personas. SoulCraft generates SOUL.md documents compatible with Soul Spec v0.5, OpenClaw, and any framework that reads markdown-based identity files.

## License

See [LICENSE](LICENSE).
