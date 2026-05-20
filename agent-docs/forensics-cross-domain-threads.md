# Cross-Domain Thread Visibility Forensic

Date: 2026-05-19

## Incident

The operator-facing Thread View could remain empty even after the engine created
cross-domain relationship threads. This made the connection phase look inert and
made it impossible to verify from the live UI whether pattern synthesis actually
bridged domains.

## Root Cause

`GameEngine.connect_domains()` built canonical runtime threads on
`GameState.threads`, but the streaming UI rendered only the SSE `graph` event.
That event was sourced from `state.metadata["pattern_graph"]`, and the pattern
graph was stored before relationship threads were attached.

The broken data path was:

1. Engine created `state.threads`.
2. HTTP/SSE emitted `state.metadata["pattern_graph"]`.
3. Browser called `renderThreads(state.graph.threads || [])`.
4. `graph.threads` was absent, so the UI showed the empty placeholder.

## Meta Pattern

Connection-phase state was split across two containers:

- `GameState.threads`: runtime truth inside the engine.
- `metadata["pattern_graph"]`: public graph payload consumed by API, SSE,
  traces, diagnostics, CLI, and MCP surfaces.

Any surface that treated `pattern_graph` as pattern-only could silently drop
thread evidence, counts, or cross-domain proof.

## Related Failures Found

- Public process traces showed patterns and bridges but did not expose thread
  counts or thread evidence.
- Saved run diagnostics persisted pattern and bridge counts but omitted thread
  counts and cross-domain thread counts.
- CLI and MCP summaries exposed only coarse thread counts, with no thread
  preview or cross-domain count.
- MCP `create_soul` bypassed `GameEngine` and therefore skipped the connection
  thread pipeline entirely.
- The landing page treated any non-empty `domains_bridged` array as
  cross-domain, so bridge placeholders like `["", ""]` could be mislabeled.

## Guardrails

- `connect_domains()` must keep `GameState.threads` and
  `pattern_graph.threads` synchronized.
- Public process traces must include `thread_count`,
  `cross_domain_thread_count`, and thread evidence preview.
- Persisted run diagnostics must include thread observability fields.
- CLI and MCP run surfaces must expose thread previews from the canonical graph.
- Cross-domain classification must use the shared thread-domain predicate, not
  duplicate ad hoc checks.

## Regression Tests

- `tests/test_engine.py::TestConnectDomains::test_exposes_threads_on_pattern_graph_for_streaming_ui`
- `tests/test_engine.py::TestConnectDomains::test_bridge_threads_do_not_count_as_cross_domain_without_domains`
- `tests/test_process_trace.py::test_process_trace_exposes_thread_counts_and_evidence`
- `tests/test_traces.py::test_save_run_persists_thread_observability`
- `tests/test_mcp_server.py::TestMcpServer::test_create_soul_uses_full_engine_connection_output`
