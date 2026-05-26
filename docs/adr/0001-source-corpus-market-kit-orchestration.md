# Source Corpus and Market Kit Orchestration

Elixis will treat a GitHub repository or local folder as a **Source Target** that produces a quality-scored **Source Corpus**, not as raw prompt text. The corpus is the shared input to CLI, HTTP API, and MCP **Operator Surfaces**, and **Market Kit Orchestration** coordinates naming, positioning, brand voice, messaging, design-system direction, evidence trace, and optional artifacts rather than adding a fourth giant markdown lens. This keeps source ingestion auditable, secret-safe, and output-quality driven while preserving structured JSON as the source of truth and using HTML/CSS only as explicit high-value review artifacts.

## Considered Options

- Feed every readable file directly into the existing pattern workflow: rejected because it creates noise, token waste, secret risk, and weak provenance.
- Add a single `market` lens: rejected because naming, brand, design, marketing copy, and visual artifacts need structured coordination and separate renderers.
- Make CLI the only first surface: rejected because CLI, HTTP API, and MCP are all required operator paths for the same ingestion contract.
