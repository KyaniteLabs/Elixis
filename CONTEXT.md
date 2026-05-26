# Elixis

Elixis turns raw reference material into a pattern graph, then resolves that graph through output lenses for identity, brand voice, design systems, naming, and marketing direction.

## Language

**Source Target**:
A GitHub repository URL or local folder path that an operator points Elixis at for ingestion.
_Avoid_: Repo import, folder import, crawl target

**Source Corpus**:
A curated, auditable evidence bundle intentionally selected from a **Source Target** because it improves Elixis output quality.
_Avoid_: Whole repo, all files, dump

**Ingestion Run**:
The act of crawling, filtering, ranking, and distilling a **Source Target** into a quality-focused **Source Corpus**.
_Avoid_: Scrape, import, sync

**Corpus Signal**:
One usable unit of evidence inside a **Source Corpus** that can materially improve naming, brand, design, identity, or marketing outputs.
_Avoid_: File chunk, raw text blob

**Signal Value Score**:
A quality score that decides whether a candidate **Corpus Signal** belongs in a **Source Corpus**.
_Avoid_: Relevance score, file rank, importance

**Market Kit**:
A bundled market-facing output generated from one **Source Corpus** and pattern graph, combining naming, positioning, brand voice, messaging, marketing copy, and design direction.
_Avoid_: Brand pack, marketing bundle, repo report

**Market Kit Orchestration**:
The coordination layer that assembles a **Market Kit** from naming, brand, design, marketing, positioning, visual, and evidence-generation surfaces.
_Avoid_: Market lens, fourth lens, giant markdown generator

**Operator Surface**:
An entry point an operator uses to run Elixis workflows, including CLI, HTTP API, and MCP.
_Avoid_: UI wrapper, adapter-only, secondary interface

**Ingestion Result**:
The shared structured contract returned by every **Operator Surface** after an **Ingestion Run**.
_Avoid_: CLI output, API response shape, MCP payload

**Artifact**:
A rendered output derived from an **Ingestion Result**, such as markdown, JSON, HTML, or CSS.
_Avoid_: Source of truth, primary result

**Artifact Tier**:
An explicit generation choice that controls which rendered **Artifacts** are produced from an **Ingestion Result**.
_Avoid_: Always-on render, implicit export

**Code Evidence**:
Supporting product evidence extracted from source code structure, public interfaces, routes, commands, tests, comments, or docstrings.
_Avoid_: Full source dump, implementation truth

**Ingestion Budget**:
The cap that limits **Source Corpus** size by **Signal Value Score**, evidence class, and output utility.
_Avoid_: File limit, token limit

**Sensitive Candidate**:
A candidate signal that may contain secrets, credentials, private keys, tokens, environment values, or unsafe local/private material.
_Avoid_: Useful secret, private signal

**Review Artifact**:
An HTML/CSS or similarly visual **Artifact** intended for high-quality human stakeholder review.
_Avoid_: Default export, always-on page

## Relationships

- A **Source Target** produces zero or one **Source Corpus** per **Ingestion Run**.
- A **Source Corpus** contains many **Corpus Signals**.
- A **Source Corpus** feeds the existing Elixis declaration, elaboration, connection, and resolution phases.
- A **Corpus Signal** must preserve provenance back to its **Source Target**.
- A candidate **Corpus Signal** belongs in a **Source Corpus** only when it has a defensible output-quality reason for inclusion.
- A **Signal Value Score** evaluates candidate signals by relevance, distinctiveness, authority, lens utility, provenance, freshness, and noise risk.
- An **Ingestion Run** records included and rejected signal counts with reasons so operators can audit the **Source Corpus**.
- A **Market Kit** includes naming directions, candidate names, positioning, audience/category notes, brand voice, messaging pillars, tagline options, landing-page copy angles, color palettes, typography, spacing, borders, shadows, visual motifs, and design-system direction.
- A **Market Kit** should preserve evidence links from its recommendations back to the **Corpus Signals** that shaped them.
- **Market Kit Orchestration** coordinates existing and future output lenses instead of replacing them with a single fourth lens.
- CLI, HTTP API, and MCP are all first-class **Operator Surfaces** for **Ingestion Runs**, **Source Corpus** inspection, and **Market Kit Orchestration**.
- MCP is an **Operator Surface** and integration adapter; it is not the product scope by itself.
- Every **Operator Surface** returns the same **Ingestion Result** contract.
- An **Ingestion Result** includes the **Source Target**, **Source Corpus**, included and rejected signal evidence, **Signal Value Score** summary, pattern graph, **Market Kit**, process trace, and optional **Artifacts**.
- **Artifacts** are renderings of the **Ingestion Result**; they are not the source of truth.
- HTML and CSS are valid **Artifact** options only when high-quality human-readable design presentation justifies the additional token and generation cost.
- **Artifact Tiers** are explicit operator choices across CLI, HTTP API, and MCP.
- HTML and CSS **Artifacts** are generated only when requested, when a design-heavy workflow requires them, when stakeholder review needs a visual presentation, or when the UI needs a visual preview.
- An **Ingestion Run** must not silently spend extra model tokens generating HTML or CSS for every **Ingestion Result**.
- **Code Evidence** is supporting evidence, not primary evidence; it belongs in a **Source Corpus** only when it improves naming, positioning, brand, design, marketing, identity, or operator-journey understanding.
- Useful **Code Evidence** includes file tree shape, module and package names, public API names, exported symbols, routes, CLI commands, MCP tool names, tests that reveal user stories, and comments or docstrings that explain product behavior.
- Implementation internals, generated code, lockfiles, vendored dependencies, minified bundles, logs, snapshots, large data files, and dependency churn are excluded unless their **Signal Value Score** justifies inclusion.
- Public GitHub **Source Targets** can be ingested without authentication; private GitHub **Source Targets** use GitHub CLI credentials, environment tokens, API bearer tokens, or MCP host credentials.
- Local folder **Source Targets** are read-only: an **Ingestion Run** does not execute project code, install dependencies, run scripts, or evaluate generated commands.
- **Sensitive Candidates** are rejected before scoring; traces report rejected categories and paths without exposing secret values.
- Images and binary media contribute metadata, filenames, dimensions, alt text, and provenance by default; visual analysis and OCR are opt-in for **Market Kit** design quality.
- GitHub **Source Corpus** defaults include repository metadata, description, homepage, topics, languages, license, releases, tags, README, docs, package metadata, repo tree, examples, screenshots, and public assets.
- Issues, pull requests, discussions, and commit history are opt-in evidence classes because they can improve output quality but carry higher noise and privacy risk.
- Dependency metadata is included only when it clarifies product category, capability, audience, framework, or design/marketing positioning.
- An **Ingestion Budget** keeps top-ranked **Corpus Signals** per evidence class and records rejected counts and reasons.
- Every included **Corpus Signal** carries source type, path or URL, line or range when available, score, and inclusion reason.
- **Ingestion Result** traces show included and rejected counts, scoring rationale, top evidence by lens, model metadata, token estimates, fallbacks, and failures.
- A **Review Artifact** is generated as a static market-kit presentation only when the selected **Artifact Tier** calls for human-readable visual review.
- **Ingestion Results**, traces, and optional **Artifacts** are persisted as local run records so operator surfaces can inspect or re-render them by run ID.
- Streaming **Operator Surfaces** report ingestion progress through discover, classify, score, corpus-ready, graph-ready, kit-section, artifact-ready, and done events.

## Example Dialogue

> **Dev:** "Should Elixis send every file from this repository into the pattern engine?"
> **Domain expert:** "No. The **Ingestion Run** should build a **Source Corpus** first, then pass curated **Corpus Signals** into the existing pattern workflow."

> **Dev:** "This local folder has source code, screenshots, package metadata, and open issues. Do we ingest all of it?"
> **Domain expert:** "No. Score each candidate by output quality. Include **Code Evidence** and metadata when they improve the **Market Kit**; reject **Sensitive Candidates** and low-value noise with traceable reasons."

## Flagged Ambiguities

- "Point Elixis at a repo" means selecting a **Source Target**, not importing an entire repository as raw prompt text.
- "Everything useful" means everything that improves output quality, not everything that is technically readable.
- "Read the code" means extracting quality-improving **Code Evidence**, not treating all implementation details as primary brand evidence.
