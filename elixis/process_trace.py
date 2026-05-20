"""Public process-trace helpers shared by HTTP, CLI, and MCP surfaces."""

from __future__ import annotations

from urllib.parse import urlparse

from .thread import is_cross_domain_thread_data, serialize_threads


def llm_public_config():
    """Return model configuration safe to expose in per-run process traces."""
    from .llm import cfg

    parsed = urlparse(cfg.base_url or "")
    host = parsed.netloc or parsed.path or ""
    return {
        "provider": cfg.provider,
        "model": cfg.default_model,
        "base_host": host,
        "classify_model": cfg.classify_model or cfg.default_model,
    }


def _safe_len(value):
    try:
        return len(value or [])
    except TypeError:
        return 0


def _thread_dicts_from_state(state, graph):
    graph_threads = graph.get("threads")
    if isinstance(graph_threads, list):
        return graph_threads

    return serialize_threads(getattr(state, "threads", []))


def _thread_preview(thread):
    return {
        "bead_a": thread.get("bead_a"),
        "bead_b": thread.get("bead_b"),
        "relationship": thread.get("relationship"),
        "strength": thread.get("strength"),
        "isomorphic": thread.get("isomorphic"),
        "domains_bridged": thread.get("domains_bridged", []),
        "evidence": thread.get("evidence", [])[:3],
    }


def process_trace_from_state(state, lens="identity"):
    """Build an auditable public trace for a pipeline run."""
    graph = state.metadata.get("pattern_graph", {})
    extraction = state.metadata.get("extraction_telemetry", {})
    enrichment = state.metadata.get("enrichment_telemetry", {})
    pattern_telemetry = state.metadata.get("pattern_telemetry", {})
    classification = pattern_telemetry.get("llm_classification", {})
    timings = state.timings or {}
    threads = _thread_dicts_from_state(state, graph)
    thread_count = graph.get("thread_count", _safe_len(threads) or _safe_len(getattr(state, "threads", [])))
    cross_domain_thread_count = graph.get(
        "cross_domain_thread_count",
        sum(1 for thread in threads if is_cross_domain_thread_data(thread)),
    )

    entities = []
    for bead in state.beads:
        data = bead.to_dict()
        entities.append({
            "name": data.get("canonical") or data.get("name"),
            "type": data.get("type"),
            "themes": data.get("themes", [])[:8],
            "traits": data.get("traits", [])[:6],
            "domains": data.get("domains", [])[:5],
            "confidence": data.get("confidence"),
            "provenance": data.get("provenance"),
        })

    return {
        "visibility": (
            "Auditable process trace. Internal token-level reasoning is not exposed; "
            "this shows the observable extraction, scoring, evidence, timings, and model metadata."
        ),
        "lens": lens,
        "model": llm_public_config(),
        "phases": [
            {
                "name": "declaration",
                "method": "LLM entity extraction with heuristic fallback",
                "duration_ms": timings.get("declaration_ms"),
                "source": extraction.get("source"),
                "entity_count": extraction.get("entity_count", len(entities)),
                "model": extraction.get("model"),
                "provider": extraction.get("provider"),
                "tokens_in": extraction.get("tokens_in"),
                "tokens_out": extraction.get("tokens_out"),
            },
            {
                "name": "elaboration",
                "method": "External/curated enrichment plus knowledge-base cross-reference",
                "duration_ms": timings.get("elaboration_ms"),
                "source": enrichment.get("source") or "research+knowledge_base",
            },
            {
                "name": "connection",
                "method": "Pattern graph: LLM classification blended with keyword/type/knowledge scoring",
                "duration_ms": timings.get("connection_ms"),
                "source": "llm+rules" if pattern_telemetry.get("llm_available") else "rules",
                "pattern_count": pattern_telemetry.get("pattern_count", len(graph.get("patterns", []))),
                "bridge_count": pattern_telemetry.get("bridge_count", len(graph.get("bridges", []))),
                "thread_count": thread_count,
                "cross_domain_thread_count": cross_domain_thread_count,
                "model": classification.get("model"),
                "provider": classification.get("provider"),
                "tokens_in": classification.get("tokens_in"),
                "tokens_out": classification.get("tokens_out"),
                "max_tokens": classification.get("max_tokens"),
            },
            {
                "name": "resolution",
                "method": f"{lens} lens document generation",
                "duration_ms": timings.get("resolution_ms") or timings.get("stage3_synthesis_ms"),
            },
        ],
        "pattern_matching": {
            "method": "0.7 LLM classification + 0.3 keyword/theme/type/knowledge scoring",
            "llm_available": pattern_telemetry.get("llm_available"),
            "classification_source": classification.get("source"),
            "classification_error": classification.get("error"),
            "classification_max_tokens": classification.get("max_tokens"),
            "top_patterns": [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "probability": p.get("probability"),
                    "supporting_entities": p.get("supporting_entities"),
                    "sub_patterns": p.get("sub_patterns", [])[:3],
                }
                for p in graph.get("patterns", [])[:8]
            ],
            "bridges": graph.get("bridges", [])[:5],
            "thread_count": thread_count,
            "cross_domain_thread_count": cross_domain_thread_count,
            "threads": [_thread_preview(thread) for thread in threads[:8]],
            "entity_scores": graph.get("entity_scores", [])[:8],
            "analysis_notes": graph.get("analysis_notes", [])[:6],
            "emergent_topic": graph.get("emergent_topic"),
            "emergent_theme": graph.get("emergent_theme"),
            "consensus_score": graph.get("consensus_score"),
        },
        "entities": entities,
        "timings_ms": timings,
    }
