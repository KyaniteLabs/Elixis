"""Tests for public process trace observability."""

from types import SimpleNamespace

from elixis.process_trace import process_trace_from_state


class _TraceBead:
    def to_dict(self):
        return {
            "canonical": "Adaptive Philosophy",
            "type": "concept",
            "themes": ["resilience", "transformation"],
            "traits": ["adaptive"],
            "domains": ["philosophy", "psychology"],
            "confidence": 0.9,
        }


def test_process_trace_exposes_thread_counts_and_evidence():
    state = SimpleNamespace(
        beads=[_TraceBead()],
        threads=[],
        metadata={
            "pattern_graph": {
                "patterns": [{"id": "resilience", "name": "Resilience", "probability": 0.8}],
                "bridges": [],
                "threads": [
                    {
                        "bead_a": "Adaptive Philosophy",
                        "bead_b": "Resilient Visual Work",
                        "relationship": "complements",
                        "strength": 1.0,
                        "isomorphic": True,
                        "domains_bridged": ["philosophy", "literature"],
                        "evidence": [
                            "Shared themes: resilience, transformation",
                            "Cross-domain: ['philosophy'] <-> ['literature']",
                        ],
                    }
                ],
                "thread_count": 1,
                "cross_domain_thread_count": 1,
            },
            "pattern_telemetry": {"llm_available": True, "llm_classification": {"source": "llm"}},
        },
        timings={"connection_ms": 12},
    )

    trace = process_trace_from_state(state, lens="brand")

    connection_phase = trace["phases"][2]
    assert connection_phase["thread_count"] == 1
    assert connection_phase["cross_domain_thread_count"] == 1
    assert trace["pattern_matching"]["thread_count"] == 1
    assert trace["pattern_matching"]["cross_domain_thread_count"] == 1
    assert trace["pattern_matching"]["threads"][0]["relationship"] == "complements"
    assert "Shared themes" in trace["pattern_matching"]["threads"][0]["evidence"][0]
