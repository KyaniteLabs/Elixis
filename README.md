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
git clone https://github.com/KyaniteLabs/Elixis.git && cd Elixis && pip install -e .
```

## Quick Start

### CLI

```bash
# Ingest a GitHub repository
elixis ingest --github https://github.com/owner/repo

# Ingest a local folder
elixis ingest --path ./my-project

# Generate a Market Kit
elixis ingest --github https://github.com/owner/repo --kit

# Inspect a saved ingestion run
elixis corpus inspect <run-id>
```

### HTTP API

```bash
# Start the server
python -m elixis serve

# Ingest via API
curl -X POST http://localhost:3110/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"github": "https://github.com/owner/repo"}'
```

### MCP

Use the MCP tools `ingest_source` and `create_market_kit` for AI assistant integration.

## Agent Skill

Elixis includes a public agent skill at [`skills/elixis/SKILL.md`](skills/elixis/SKILL.md). Use `$elixis` in compatible agent hosts when you want an agent to choose the right CLI, HTTP API, or MCP workflow for Source Corpus ingestion, pattern synthesis, identity, brand voice, design direction, naming research, and Market Kit outputs.

## Configuration

- `ELIXIS_INFERENCE_PROVIDER`: Inference provider (glm, kimi, openai)
- `ZAI_API_KEY`: API key for Zhipu AI inference
- `GITHUB_TOKEN`: GitHub authentication token (optional, for private repos)

## Documentation

- [skills/elixis/SKILL.md](skills/elixis/SKILL.md) — Public agent skill for Elixis workflows
- [CONTEXT.md](CONTEXT.md) — Domain terminology and relationships
- [docs/DEPLOY_SETUP.md](docs/DEPLOY_SETUP.md) — CI/CD deployment configuration
- [agent-docs/](agent-docs/) — Agent and operator documentation

## License

MIT License — see [LICENSE](LICENSE)

---

## Part of KyaniteLabs

More from [KyaniteLabs](https://kyanitelabs.tech). Related projects:

- **[liminal](https://github.com/KyaniteLabs/liminal)** — AI creative-coding studio (p5.js, GLSL, Three.js)
- **[Innerscape](https://github.com/KyaniteLabs/Innerscape)** — personal-growth OS: journaling & reflection
- **[dev-learning-archaeologist](https://github.com/KyaniteLabs/dev-learning-archaeologist)** — forensic git-history learning diagnostic

→ More at **[kyanitelabs.tech](https://kyanitelabs.tech)**
