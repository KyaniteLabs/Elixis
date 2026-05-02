# Contributing to SoulCraft

Thanks for your interest! SoulCraft is a companion tool for OpenClaw that transforms brain dump text into structured SOUL.md identity documents.

## Quick Start

```bash
git clone https://github.com/KyaniteLabs/SoulCraft.git
cd SoulCraft
python -m pytest  # or: python -m unittest discover -s tests
python app.py     # starts on http://localhost:3110
```

SoulCraft uses **zero external Python dependencies** — everything runs on the stdlib. You'll need a running Ollama instance (or OpenAI-compatible API) for the LLM pipeline.

## Development Setup

1. Python 3.12+
2. An LLM backend (Ollama recommended for local dev)
3. Set environment variables in `.env` (see `.env.example`)

## Architecture

3-stage pipeline: **Entity Extraction** → **Pattern Graph Engine** → **SOUL.md Synthesis**

- `app.py` — HTTP server, routing, SSE streaming
- `soulcraft/entities.py` — Stage 1: LLM entity extraction
- `soulcraft/patterns.py` — Stage 2: Archetypal pattern probability graph
- `soulcraft/synthesis.py` — Stage 3: SOUL.md document generation
- `soulcraft/llm.py` — LLM client (Ollama / OpenAI-compatible)
- `soulcraft/research.py` — Wikipedia enrichment with ThreadPoolExecutor
- `soulcraft/translate.py` — On-the-fly translation with streaming and caching
- `soulcraft/mcp_server.py` — MCP server for AI agent native access

## Code Style

- **Python stdlib only** — no external dependencies
- `unittest` for tests (no pytest plugins)
- Keep functions focused and small
- No inline data — extract to separate files if >2KB
- Type hints on public functions
- Docstrings: one-line summary, skip obvious ones

## Pull Requests

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes
4. Run tests: `python -m unittest discover -s tests`
5. Submit a PR with a clear description

### PR Conventions

- One logical change per PR
- Include tests for new functionality
- Update `openapi.yaml` if you add/modify API endpoints
- Update `llms.txt` if you add new modules or change architecture

## Reporting Issues

Open a GitHub issue with:
- What you expected
- What happened
- Steps to reproduce
- Your setup (Python version, LLM backend, OS)

## License

By contributing, you agree your work is licensed under the [MIT License](LICENSE).
