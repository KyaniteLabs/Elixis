# Elixis

**Elixis is a local-first AI pattern synthesis engine that ingests source corpus material, builds a pattern graph, and resolves that graph through output lenses for identity, brand voice, design systems, naming, and marketing direction.**

Built with Python 3.12+ using only the standard library — no external dependencies required.

## What is this?

Elixis transforms raw reference material from GitHub repositories or local folders into structured **Market Kits** — bundled outputs combining naming, positioning, brand voice, messaging, and design direction.

The engine operates in three phases:

1. **Ingest** — Select and score quality signals from source targets (GitHub repos or local folders)
2. **Synthesize** — Extract meaningful patterns from curated evidence into a resolution graph
3. **Resolve** — Apply output lenses to produce identity, brand voice, design system, and naming artifacts

Elixis exposes three operator surfaces: a CLI, an HTTP API (port 3110), and an MCP server for AI assistant integration.

## Features

- **Source Corpus Ingestion** — Clone and analyze GitHub repositories or scan local folders for quality signals
- **Pattern Graph Resolution** — Extract, score, and connect patterns from curated evidence using graph-based synthesis
- **Market Kit Orchestration** — Generate naming, positioning, brand voice, design system, and messaging outputs
- **Entity & Sentiment Analysis** — Identify entities, sentiment, and archetypes across source material
- **Expression DNA** — Distill brand personality into structured expression profiles
- **Process Tracing** — Track synthesis decisions and evidence provenance across pipeline stages
- **Multiple Operator Surfaces** — CLI (`elixis`), HTTP API (`python -m elixis serve`), and MCP integration
- **Agent Skill** — Public agent skill for compatible AI agent hosts ([`skills/elixis/SKILL.md`](skills/elixis/SKILL.md))
- **Zero Dependencies** — Built entirely on the Python standard library
- **Local-First** — All processing runs locally; no data leaves your machine unless you configure an external inference provider

## Installation

```bash
git clone https://github.com/KyaniteLabs/Elixis.git && cd Elixis && pip install -e .
```

Requires Python 3.12 or later. Verify your installation:

```bash
elixis --help
```

### Docker

```bash
docker compose up --build
```

This starts the HTTP API on port 3110 with a Traefik reverse proxy configuration included in [`traefik/`](traefik/).

## Quick Start

### CLI

```bash
# Ingest a GitHub repository
elixis ingest --github https://github.com/owner/repo

# Ingest a local folder
elixis ingest --path ./my-project

# Generate a Market Kit from an ingestion run
elixis ingest --github https://github.com/owner/repo --kit

# Inspect a saved ingestion run
elixis corpus inspect <run-id>
```

### HTTP API

```bash
# Start the server
python -m elixis serve

# Ingest a source target via API
curl -X POST http://localhost:3110/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"github": "https://github.com/owner/repo"}'
```

### MCP

Use the MCP tools `ingest_source` and `create_market_kit` for integration with AI assistants and agent workflows.

## Usage

### Configuration

Elixis uses environment variables for configuration:

| Variable | Description | Required |
|---|---|---|
| `ELIXIS_INFERENCE_PROVIDER` | Inference provider (`glm`, `kimi`, `openai`) | No — runs pattern extraction without LLM if unset |
| `ZAI_API_KEY` | API key for Zhipu AI inference | Only when using `glm` or `kimi` providers |
| `GITHUB_TOKEN` | GitHub authentication token | No — required only for private repositories |

### Core Pipeline

Elixis modules map to the pipeline stages:

| Module | Purpose |
|---|---|
| `elixis.ingest` | Source corpus ingestion and quality scoring |
| `elixis.parsing` | Raw content parsing and normalization |
| `elixis.patterns` | Pattern extraction and classification |
| `elixis.graph` | Pattern graph construction |
| `elixis.synthesis` | Multi-signal synthesis across patterns |
| `elixis.resolution` | Graph resolution through output lenses |
| `elixis.naming` | Naming research and generation |
| `elixis.market` | Market Kit orchestration |
| `elixis.traces` | Evidence provenance and process tracing |
| `elixis.entities` | Entity extraction and classification |
| `elixis.sentiment` | Sentiment analysis across source material |
| `elixis.expression_dna` | Brand personality distillation |
| `elixis.llm` | LLM provider abstraction |
| `elixis.mcp_server` | MCP tool server |

### OpenAPI

The HTTP API exposes an OpenAPI specification at [`openapi.yaml`](openapi.yaml).

## FAQ

**Does Elixis require an LLM or API key?**

No. Elixis can run entirely on its local pattern extraction and graph resolution pipeline without any external inference provider. LLM integration is optional and enhances synthesis quality when configured.

**What source formats does Elixis support?**

Elixis ingests GitHub repositories (public or authenticated via `GITHUB_TOKEN`) and local folders. It processes code, documentation, configuration files, and other text-based content.

**What is a Market Kit?**

A Market Kit is a structured bundle of outputs produced by Elixis — including naming candidates, positioning statements, brand voice guidelines, design direction, and messaging frameworks — all derived from pattern analysis of the source corpus.

**Can I use Elixis with AI agents?**

Yes. Elixis includes an MCP server for tool-based integration and a public agent skill at [`skills/elixis/SKILL.md`](skills/elixis/SKILL.md). Use `$elixis` in compatible agent hosts to invoke the right workflow.

**How do I deploy Elixis in production?**

Use the included `Dockerfile` and `docker-compose.yml`. A Traefik reverse proxy configuration is provided in [`traefik/`](traefik/). See [`docs/DEPLOY_SETUP.md`](docs/DEPLOY_SETUP.md) for CI/CD deployment details.

## Contributing

Contributions are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines on how to get started, submit issues, and open pull requests.

## Documentation

| Document | Description |
|---|---|
| [`CONTEXT.md`](CONTEXT.md) | Domain terminology and relationships |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution guidelines |
| [`CHANGELOG.md`](CHANGELOG.md) | Release history |
| [`AGENTS.md`](AGENTS.md) | Agent configuration and behavior |
| [`skills/elixis/SKILL.md`](skills/elixis/SKILL.md) | Public agent skill for Elixis workflows |
| [`docs/DEPLOY_SETUP.md`](docs/DEPLOY_SETUP.md) | CI/CD deployment configuration |
| [`agent-docs/`](agent-docs/) | Agent and operator documentation |
| [`openapi.yaml`](openapi.yaml) | HTTP API specification |
| [`llms.txt`](llms.txt) | Machine-readable project summary for AI systems |

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

## Part of KyaniteLabs

More from [KyaniteLabs](https://kyanitelabs.tech). Related projects:

- **[liminal](https://github.com/KyaniteLabs/liminal)** — AI creative-coding studio (p5.js, GLSL, Three.js)
- **[Innerscape](https://github.com/KyaniteLabs/Innerscape)** — personal-growth OS: journaling & reflection
- **[dev-learning-archaeologist](https://github.com/KyaniteLabs/dev-learning-archaeologist)** — forensic git-history learning diagnostic

→ More at **[kyanitelabs.tech](https://kyanitelabs.tech)**