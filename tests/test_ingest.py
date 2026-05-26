"""Tests for Source Corpus ingestion and Market Kit orchestration."""

import types

import pytest

from elixis.ingest import ingest_source
from elixis.market import create_market_kit


def test_local_ingestion_builds_quality_scored_source_corpus(tmp_path, monkeypatch):
    monkeypatch.setattr("elixis.ingest.RUNS_DIR", tmp_path / "runs")
    (tmp_path / "README.md").write_text("# Acme\n\nAI workflow tool for brand and design operators.")
    (tmp_path / "app.py").write_text('''"""Public API for Acme."""\n\ndef create_market_kit():\n    """Create a market kit for operators."""\n    return {}\n''')
    (tmp_path / ".env").write_text("API_KEY=supersecretvalue")

    result = ingest_source(path=str(tmp_path), include_code=True, max_signals=10)

    assert result["source_target"]["type"] == "local"
    assert result["source_corpus"]["signal_count"] >= 2
    assert any(signal["title"] == "README.md" for signal in result["source_corpus"]["signals"])
    assert any(signal["kind"] == "code_evidence" for signal in result["source_corpus"]["signals"])
    assert sum(result["signal_value_summary"]["included_by_kind"].values()) == result["source_corpus"]["signal_count"]
    assert result["rejected_signals"]["by_reason"]["hidden_file"] == 1
    assert "supersecretvalue" not in str(result)


def test_local_ingestion_rejects_sensitive_visible_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("elixis.ingest.RUNS_DIR", tmp_path / "runs")
    (tmp_path / "README.md").write_text("# Product\n\nMarketing and design direction.")
    (tmp_path / "production-token.txt").write_text("token=abc123abc123abc123abc123")

    result = ingest_source(path=str(tmp_path))

    assert result["rejected_signals"]["by_reason"]["sensitive_path"] == 1
    assert "abc123abc123" not in str(result)


def test_artifact_tiers_are_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr("elixis.ingest.RUNS_DIR", tmp_path / "runs")
    (tmp_path / "README.md").write_text("# Product\n\nAI brand design system.")

    result = ingest_source(path=str(tmp_path), artifacts=["html", "css"])

    assert result["artifact_tiers"] == ["html", "css"]
    assert "artifacts" not in result


def test_artifact_tiers_accept_single_string(tmp_path, monkeypatch):
    monkeypatch.setattr("elixis.ingest.RUNS_DIR", tmp_path / "runs")
    (tmp_path / "README.md").write_text("# Product\n\nAI brand design system.")

    result = ingest_source(path=str(tmp_path), artifacts="html")

    assert result["artifact_tiers"] == ["html"]


def test_ingestion_rejects_invalid_signal_budget(tmp_path, monkeypatch):
    monkeypatch.setattr("elixis.ingest.RUNS_DIR", tmp_path / "runs")
    (tmp_path / "README.md").write_text("# Product\n\nAI brand design system.")

    with pytest.raises(ValueError, match="max_signals"):
        ingest_source(path=str(tmp_path), max_signals=0)


def test_local_ingestion_skips_archived_stale_material_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr("elixis.ingest.RUNS_DIR", tmp_path / "runs")
    (tmp_path / "README.md").write_text("# Current Product\n\nModern market kit direction.")
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "old-brand.md").write_text("# Stale Brand\n\nOld identity-only positioning.")

    result = ingest_source(path=str(tmp_path), max_signals=10)

    titles = [signal["title"] for signal in result["source_corpus"]["signals"]]
    assert "README.md" in titles
    assert "archive/old-brand.md" not in titles


def test_market_kit_orchestration_returns_structured_contract(tmp_path, monkeypatch):
    monkeypatch.setattr("elixis.ingest.RUNS_DIR", tmp_path / "runs")
    (tmp_path / "README.md").write_text("# Acme\n\nAI workflow tool for brand and design operators.")

    class FakeBead:
        def to_dict(self):
            return {"canonical": "Acme", "themes": ["design", "workflow"], "traits": ["operator clarity"]}

    class FakeEngine:
        def __init__(self):
            self.state = types.SimpleNamespace(
                beads=[FakeBead()],
                threads=[],
                tensions=[],
                timings={},
                metadata={
                    "pattern_graph": {
                        "patterns": [
                            {"id": "wisdom", "name": "Wisdom & Knowledge", "probability": 0.8},
                            {"id": "creation", "name": "Creation & Artistry", "probability": 0.6},
                        ],
                        "emergent_topic": "operator clarity",
                        "emergent_theme": "AI workflow clarity",
                        "bridges": [],
                        "threads": [],
                        "thread_count": 0,
                        "cross_domain_thread_count": 0,
                    },
                    "pattern_telemetry": {"llm_available": False, "llm_classification": {"source": "rules"}},
                },
            )

        def declare_themes(self, text):
            self.text = text

        def elaborate(self):
            return None

        def connect_domains(self):
            return None

    monkeypatch.setattr("elixis.engine.GameEngine", FakeEngine)
    monkeypatch.setattr(
        "elixis.naming.research_name_from_identity",
        lambda entities, graph: {
            "variants": [{"name": "Acme", "identity_fit": 0.9, "style": "direct"}],
            "recommendations": ["Best identity fit: Acme"],
        },
    )

    result = create_market_kit(path=str(tmp_path), artifacts=["markdown", "html"])

    assert result["source_corpus"]["signal_count"] >= 1
    assert result["market_kit"]["positioning"]["market_premise"] == "AI workflow clarity"
    assert result["market_kit"]["design_system"]["color_palette"]
    assert result["artifacts"]["market-kit.md"].startswith("#")
    assert "market-kit.html" in result["artifacts"]
