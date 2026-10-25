# Changelog

All notable user-visible changes to Elixis will be documented in this file.

This project follows the intent of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Started the project changelog so product, CLI, API, and synthesis-engine changes have a durable release history.

## [1.0.0] - 2026-09-25

_Tag `v1.0.0` points at `a7cdd4c` (2026-09-25), a text-only cleanup of one archived
note on top of `89d5eff` (2026-05-02). The tagged code is otherwise the 2026-05-02
tree. It shipped under the earlier package name `soulcraft` 1.0.0, MIT-licensed.
The package was renamed after the tag (`63ef5c2`, `186be29`, 2026-05-03) and
relicensed to Apache-2.0 (`79d17b4`, `ac753cc`)._

### Added

- Three-stage pipeline: LLM-powered entity extraction with Wikipedia enrichment,
  archetypal pattern analysis, and LLM synthesis of SOUL.md documents via Ollama
  (`82ba3ae`, `9bf9bda`, `26a5445`).
- Streaming SSE output, tracing, diagnostics and run history (`9d9e98d`, `8778e86`).
- On-the-fly translation with streaming and caching (`5f127b8`).
- Docker deployment, CI, and tests (`7000d3b`).
- MCP server, `llms-full.txt`, `pyproject.toml` and an OpenAPI spec (`fe5cec9`,
  `568e612`).

### Changed

- Repositioned as an OpenClaw companion tool (`b83f6c5`); performance and
  reliability improvements (`a0c47aa`).
- An LLM is required; the heuristic entity-extraction fallback was removed (`70c9308`).

### Security

- Security fixes, stronger prompt-injection detection, and a higher entity
  classification limit (`b83f6c5`, `89d5eff`).
