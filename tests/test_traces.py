"""Tests for persisted diagnostic run summaries."""

import json
from pathlib import Path

import elixis.traces as traces


def test_save_run_persists_thread_observability(monkeypatch, tmp_path):
    runs_dir = tmp_path / "runs"
    traces_dir = tmp_path / "llm"
    request_log = tmp_path / "requests.log"
    monkeypatch.setattr(traces, "_RUNS_DIR", str(runs_dir))
    monkeypatch.setattr(traces, "_TRACES_DIR", str(traces_dir))
    monkeypatch.setattr(traces, "_REQUESTS_LOG", str(request_log))

    graph = {
        "patterns": [{"name": "Resilience", "probability": 0.8}],
        "bridges": [],
        "threads": [
            {
                "bead_a": "Adaptive Philosophy",
                "bead_b": "Resilient Visual Work",
                "relationship": "complements",
                "strength": 1.0,
                "isomorphic": True,
                "domains_bridged": ["philosophy", "literature"],
                "evidence": ["Shared themes: resilience"],
            }
        ],
        "thread_count": 1,
        "cross_domain_thread_count": 1,
    }

    traces.save_run(
        "adaptive philosophy and resilient visual work",
        [{"canonical": "Adaptive Philosophy", "type": "concept"}],
        graph,
        "# Output",
        lens="brand",
    )

    saved_files = list(Path(runs_dir).glob("*.json"))
    assert len(saved_files) == 1
    payload = json.loads(saved_files[0].read_text())
    assert payload["thread_count"] == 1
    assert payload["cross_domain_thread_count"] == 1
    assert payload["thread_preview"][0]["relationship"] == "complements"
