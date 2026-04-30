# SoulCraft

> Research-backed naming, language, and story synthesis for meaningful brands, products, and creative systems.

SoulCraft helps turn raw ideas, cultural context, research notes, and language constraints into grounded names, positioning, and narrative patterns. It includes entity extraction, pattern discovery, LLM-assisted synthesis, translation checks, validation, trace logging, backup flows, and a lightweight Flask landing/app surface.

## Public Discovery

**SoulCraft** is a language-and-meaning workbench for founders, artists, product builders, and creative technologists who need names and narratives that carry context instead of generic AI slop. It is useful for brand naming, product naming, symbolic research, multilingual naming review, and story synthesis.

**AI discovery:** [`llms.txt`](llms.txt) provides a compact project summary for AI assistants and search crawlers.

**Best-fit searches:** AI naming tool, brand naming research, product naming assistant, symbolic language synthesis, multilingual naming validation, creative research assistant, narrative synthesis tool, meaning-centered brand strategy.

## What it does

- Extracts entities and candidate terms from research material.
- Detects naming and language patterns.
- Uses LLM-assisted synthesis for name/story options.
- Checks translation and cross-language risks.
- Validates outputs against project constraints.
- Keeps traces and backups for repeatable creative decisions.

## Repository map

```text
soulcraft/              Core Python package
  entities.py           Entity extraction and structured terms
  patterns.py           Pattern discovery
  synthesis.py          Naming/story synthesis
  translate.py          Translation and language checks
  validation.py         Output validation
  traces.py             Trace capture
  backup.py             Backup helpers
  templates/            Flask templates
tests/                  Unit and integration tests
scripts/                Deployment helpers
traefik/                Reverse-proxy deployment examples
app.py                  Flask entry point
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
pytest
```

## Best for

- Naming a product, project, artwork, or studio.
- Turning research notes into language directions.
- Checking whether a name carries unwanted cross-language meaning.
- Preserving creative reasoning instead of losing it in a chat transcript.

## License

See [LICENSE](LICENSE).
