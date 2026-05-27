# Elixis

Elixis turns raw reference material into a pattern graph, then resolves that graph through output lenses for identity, brand voice, design systems, naming, and marketing direction.

## Overview

Elixis ingests source targets (GitHub repositories or local folders) and produces structured **Market Kits** — bundled outputs combining naming, positioning, brand voice, messaging, and design direction.

## Features

- **Source Corpus Ingestion**: Select and score quality signals from GitHub repos or local folders
- **Pattern Graph Resolution**: Extract meaningful patterns from curated evidence
- **Market Kit Orchestration**: Generate naming, positioning, brand voice, and design system outputs
- **Multiple Operator Surfaces**: CLI, HTTP API, and MCP integration

## Installation

```bash
pip install elixis
```

## Quick Start

### CLI

```bash
# Ingest a GitHub repository
elixis ingest --source https://github.com/owner/repo

# Ingest a local folder
elixis ingest --source ./my-project

# Generate a Market Kit
elixis market-kit --run-id <run-id>
```

### HTTP API

```bash
# Start the server
python -m elixis serve

# Ingest via API
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"source": "https://github.com/owner/repo"}'
```

### MCP

Use the MCP tools `ingest_source` and `inspect_ingestion` for AI assistant integration.

## Configuration

- `ELIXIS_INFERENCE_PROVIDER`: Inference provider (glm, kimi, openai)
- `ZAI_API_KEY`: API key for Zhipu AI inference
- `GITHUB_TOKEN`: GitHub authentication token (optional, for private repos)

## Documentation

- [CONTEXT.md](CONTEXT.md) — Domain terminology and relationships
- [docs/DEPLOY_SETUP.md](docs/DEPLOY_SETUP.md) — CI/CD deployment configuration
- [agent-docs/](agent-docs/) — Agent and operator documentation

## License

MIT License — see [LICENSE](LICENSE)
