"""The service module is the one seam every adapter crosses; test it there."""

import pytest

from elixis import service

TEXT = "Athena, Batman, Miyamoto Musashi. A quiet glassblower restores old lighthouse lenses."


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    # No model: exercise the deterministic offline path the adapters fall back to.
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_FALLBACK_URL", raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9")


def test_prepare_text_rejects_empty_input():
    with pytest.raises(service.InvalidInput):
        service.prepare_text("   ")


def test_prepare_text_returns_the_sanitized_text():
    assert service.prepare_text(TEXT).strip() == TEXT


def test_synthesize_rejects_an_unknown_lens_before_running():
    with pytest.raises(service.InvalidInput, match="identity, brand, design"):
        service.synthesize(TEXT, lens="poster")


def test_synthesize_summary_is_consistent_with_the_run():
    run = service.synthesize(service.prepare_text(TEXT), lens="brand")
    summary = run.summary()
    assert list(summary) == [
        "lens", "entity_count", "thread_count", "cross_domain_thread_count", "threads",
        "tension_count", "top_patterns", "emergent_topic", "emergent_theme",
        "consensus_score", "process_trace", "output",
    ]
    assert summary["lens"] == "brand"
    assert summary["entity_count"] == len(run.entities)
    assert summary["thread_count"] == run.thread_count
    assert summary["threads"] == run.threads[:8]
    assert summary["output"] == run.output and run.output


def test_patterns_builds_a_graph_from_prepared_text():
    graph = service.patterns(service.prepare_text(TEXT))
    assert isinstance(graph.get("patterns"), list)


def test_name_from_identity_returns_a_naming_report():
    report = service.name_from_identity(service.prepare_text(TEXT))
    assert "variants" in report
