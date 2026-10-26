# Changelog

All notable user-visible changes to Elixis will be documented in this file.

This project follows the intent of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- README has a `bash readme-test` block (version and offline `extract`) that CI runs on every change through the shared profile's Layer 3 step.
- Started the project changelog so product, CLI, API, and synthesis-engine changes have a durable release history.

### Fixed

- Offline entity extraction now reads a comma-separated list of short names ("Athena, Batman, Miyamoto Musashi") as separate entities. The first name used to swallow the rest as its source, and one-word names such as "Batman" were dropped. A single comma still means "Name, Source".

### Changed

- **Internal: one service module behind every surface.** The new `elixis/service.py` (`prepare_text`, `synthesize` returning a `SynthesisRun`, `patterns`, `name_from_identity`) owns input validation, engine orchestration and result shaping. The CLI, MCP server and HTTP pipelines now call it instead of each re-wiring `GameEngine`. Output is unchanged across all three surfaces.

## [1.0.0] - 2026-09-25

_Tag `v1.0.0` points at `a7cdd4c` (2026-09-25), a text-only cleanup of one archived
note on top of `89d5eff` (2026-05-02). The tagged code is otherwise the 2026-05-02
tree. It shipped as 1.0.0 under an earlier working name, MIT-licensed. The
package was renamed to Elixis after the tag (`63ef5c2`, `186be29`, 2026-05-03) and
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
