# Contributing to Elixis

Thanks for your interest! Elixis is a local-first AI pattern synthesis engine that turns brain dump text into structured outputs for identity, brand voice, design systems, naming research, and lens-specific documents.

## Quick Start

```bash
git clone https://github.com/KyaniteLabs/Elixis.git
cd Elixis
python -m pytest  # or: python -m unittest discover -s tests
python app.py     # starts on http://localhost:3110
```

Elixis uses **zero external Python dependencies** — everything runs on the stdlib. You'll need a running Ollama instance (or OpenAI-compatible API) for the LLM pipeline.

## Development Setup

1. Python 3.12+
2. An LLM backend (Ollama recommended for local dev)
3. Set environment variables in `.env` (see `.env.example`)

## Architecture

Four-phase synthesis pipeline: **Declaration** → **Elaboration** → **Connection** → **Resolution**

- `app.py` — HTTP server, routing, SSE streaming
- `elixis/engine.py` — four-phase GameEngine orchestration
- `elixis/entities.py` — declaration: LLM entity extraction
- `elixis/research.py` — elaboration: Wikipedia and knowledge-base enrichment
- `elixis/patterns.py` and `elixis/graph.py` — connection: archetypal graph, bridges, and threads
- `elixis/lenses/` — resolution: identity, brand, and design output lenses
- `elixis/synthesis.py` — SOUL.md identity lens implementation
- `elixis/llm.py` — LLM client (Ollama / OpenAI-compatible)
- `elixis/translate.py` — On-the-fly translation with streaming and caching
- `elixis/mcp_server.py` — MCP server for AI agent native access

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
