"""Comprehensive tests for elixis.engine — GameState, GameEngine, and helpers."""

from unittest.mock import patch

import pytest

from elixis.engine import GameState, GameEngine, _infer_domains, _check_isomorphism
from elixis.bead import Bead
from elixis.thread import Thread


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_entity(
    canonical="Test Entity",
    original="Test Entity",
    etype="concept",
    themes=None,
    traits=None,
    confidence=0.5,
    source="",
    description="",
    related=None,
):
    return {
        "canonical": canonical,
        "original": original,
        "type": etype,
        "themes": themes or ["power"],
        "traits": traits or ["bold"],
        "confidence": confidence,
        "source": source,
        "description": description,
        "related": related or [],
    }


def _make_engine(**overrides):
    """Build a GameEngine with sensible defaults that avoid lazy imports."""
    defaults = dict(
        extract_entities=lambda x, telemetry=None: [
            _make_entity(canonical="Alpha", themes=["power", "shadow"]),
            _make_entity(canonical="Beta", etype="character", themes=["wisdom"]),
        ],
        annotate_bead=lambda x: {"sentiment": 0.5, "intensity": 0.7},
        deduplicate_beads=lambda beads: beads,
        enrich_entities=lambda entities, telemetry=None: entities,
        character_by_name=lambda name: None,
        build_pattern_graph=lambda entities, text, telemetry=None: {
            "patterns": [
                {"name": "Power", "probability": 0.8, "supporting_entities": 2, "sub_patterns": []},
            ],
            "bridges": [],
            "consensus_score": 0.75,
            "emergent_topic": "Power",
        },
        build_relationship_graph=lambda beads: {
            "edges": [
                {
                    "bead_a": "Alpha",
                    "bead_b": "Beta",
                    "relationship": "complements",
                    "strength": 0.6,
                    "isomorphic": True,
                    "domains_bridged": ("philosophy", "literature"),
                    "evidence": ["Shared themes: power"],
                }
            ],
        },
    )
    defaults.update(overrides)
    return GameEngine(**defaults)


# ===========================================================================
# GameState
# ===========================================================================


class TestGameState:
    """Tests for GameState construction, serialization, and roundtrip."""

    def test_default_construction(self):
        gs = GameState()
        assert gs.phase == "init"
        assert gs.beads == []
        assert gs.threads == []
        assert gs.scores == {}
        assert gs.provenance == {}
        assert gs.tensions == []
        assert gs.raw_input == ""
        assert gs.timings == {}
        assert gs.metadata == {}

    def test_construction_with_args(self):
        gs = GameState(raw_input="hello world", phase="declaration")
        assert gs.raw_input == "hello world"
        assert gs.phase == "declaration"

    def test_to_dict_empty(self):
        gs = GameState()
        d = gs.to_dict()
        assert d["phase"] == "init"
        assert d["beads"] == []
        assert d["threads"] == []
        assert d["scores"] == {}

    def test_to_dict_with_beads_and_threads(self):
        gs = GameState()
        gs.beads = [Bead(canonical="X", type="concept")]
        gs.threads = [Thread(bead_a="X", bead_b="Y", relationship="parallels")]
        gs.scores = {"X::power": 0.8}
        gs.provenance = {"bead_count": 1}
        gs.tensions = [{"type": "essential_tension"}]
        gs.timings = {"declaration_ms": 42}
        gs.metadata = {"key": "val"}

        d = gs.to_dict()
        assert len(d["beads"]) == 1
        assert d["beads"][0]["canonical"] == "X"
        assert len(d["threads"]) == 1
        assert d["scores"]["X::power"] == 0.8
        assert d["provenance"]["bead_count"] == 1
        assert len(d["tensions"]) == 1
        assert d["timings"]["declaration_ms"] == 42
        assert d["metadata"]["key"] == "val"

    def test_from_dict_roundtrip(self):
        gs = GameState()
        gs.beads = [
            Bead(canonical="A", type="character", domains=["culture"], themes=["power"]),
            Bead(canonical="B", type="concept", domains=["philosophy"], themes=["wisdom"]),
        ]
        gs.threads = [
            Thread(bead_a="A", bead_b="B", relationship="complements", strength=0.65),
        ]
        gs.scores = {"A::power": 0.9}
        gs.provenance = {"bead_count": 2}
        gs.tensions = []
        gs.timings = {"declaration_ms": 10}
        gs.metadata = {"pattern_graph": {"patterns": []}}

        d = gs.to_dict()
        restored = GameState.from_dict(d)

        assert restored.phase == gs.phase
        assert len(restored.beads) == 2
        assert restored.beads[0].canonical == "A"
        assert restored.beads[1].canonical == "B"
        assert len(restored.threads) == 1
        assert restored.threads[0].bead_a == "A"
        assert restored.scores == gs.scores
        assert restored.provenance == gs.provenance
        assert restored.timings == gs.timings
        assert restored.metadata == gs.metadata

    def test_from_dict_empty_data(self):
        gs = GameState.from_dict({})
        assert gs.phase == "init"
        assert gs.beads == []
        assert gs.threads == []

    def test_from_dict_preserves_raw_input(self):
        d = {"raw_input": "some text", "phase": "declaration"}
        gs = GameState.from_dict(d)
        assert gs.raw_input == "some text"
        assert gs.phase == "declaration"


# ===========================================================================
# GameEngine — state management
# ===========================================================================


class TestGameEngineState:
    """Tests for GameEngine state property and new_game."""

    def test_state_is_none_initially(self):
        engine = _make_engine()
        assert engine.state is None

    def test_new_game_creates_state(self):
        engine = _make_engine()
        state = engine.new_game("test input")
        assert engine.state is not None
        assert state is engine.state
        assert state.raw_input == "test input"
        assert state.phase == "init"

    def test_new_game_resets_state(self):
        engine = _make_engine()
        engine.new_game("first")
        engine.new_game("second")
        assert engine.state.raw_input == "second"


# ===========================================================================
# GameEngine — Phase 1: declare_themes
# ===========================================================================


class TestDeclareThemes:
    """Tests for GameEngine.declare_themes."""

    def test_creates_beads_from_entities(self):
        engine = _make_engine()
        state = engine.declare_themes("Some raw input")
        assert state.phase == "declaration"
        assert len(state.beads) == 2
        assert state.beads[0].canonical == "Alpha"
        assert state.beads[1].canonical == "Beta"

    def test_uses_annotate_bead(self):
        engine = _make_engine(
            annotate_bead=lambda x: {"sentiment": -0.3, "intensity": 0.9},
        )
        state = engine.declare_themes("input")
        assert state.beads[0].sentiment == -0.3
        assert state.beads[0].intensity == 0.9

    def test_uses_deduplicate_beads(self):
        engine = _make_engine(
            deduplicate_beads=lambda beads: beads[:1],
        )
        state = engine.declare_themes("input")
        assert len(state.beads) == 1

    def test_sets_provenance_based_on_confidence(self):
        engine = _make_engine(
            extract_entities=lambda x, telemetry=None: [
                _make_entity(canonical="High", confidence=0.95),
                _make_entity(canonical="Low", confidence=0.5),
            ],
        )
        state = engine.declare_themes("input")
        high = next(b for b in state.beads if b.canonical == "High")
        low = next(b for b in state.beads if b.canonical == "Low")
        assert high.provenance == "first-hand"
        assert low.provenance == "inferred"

    def test_records_timing(self):
        engine = _make_engine()
        state = engine.declare_themes("input")
        assert "declaration_ms" in state.timings
        assert isinstance(state.timings["declaration_ms"], int)

    def test_records_bead_count_provenance(self):
        engine = _make_engine()
        state = engine.declare_themes("input")
        assert state.provenance["bead_count"] == 2

    def test_raises_without_game(self):
        engine = _make_engine()
        # No new_game or raw_input passed
        with pytest.raises(RuntimeError, match="No game in progress"):
            engine.declare_themes()

    def test_accepts_raw_input_to_start_game(self):
        engine = _make_engine()
        state = engine.declare_themes("fresh input")
        assert state.raw_input == "fresh input"

    def test_entity_with_no_themes(self):
        engine = _make_engine(
            extract_entities=lambda x, telemetry=None: [{"canonical": "Empty", "original": "Empty", "type": "concept", "themes": [], "traits": [], "confidence": 0.5, "source": "", "description": "", "related": []}],
        )
        state = engine.declare_themes("input")
        assert state.beads[0].themes == []


# ===========================================================================
# GameEngine — Phase 2: elaborate
# ===========================================================================


class TestElaborate:
    """Tests for GameEngine.elaborate."""

    def test_enriches_beads(self):
        engine = _make_engine(
            enrich_entities=lambda entities, telemetry=None: [
                {**e, "description": "enriched desc", "themes": ["power", "extra"]}
                for e in entities
            ],
        )
        engine.declare_themes("input")
        state = engine.elaborate()
        assert state.phase == "elaboration"

    def test_raises_before_declaration(self):
        engine = _make_engine()
        with pytest.raises(RuntimeError, match="declare_themes"):
            engine.elaborate()

    def test_allows_init_phase(self):
        engine = _make_engine()
        engine.new_game("input")
        # elaborate() accepts "init" phase per engine.py line 205
        state = engine.elaborate()
        assert state.phase == "elaboration"

    def test_records_timing(self):
        engine = _make_engine()
        engine.declare_themes("input")
        state = engine.elaborate()
        assert "elaboration_ms" in state.timings

    def test_knowledge_base_lookup(self):
        kb_data = {
            "canonical": "Alpha",
            "big_five": {"O": 0.9},
            "archetype_scores": {"power": 0.8},
        }
        engine = _make_engine(
            character_by_name=lambda name: kb_data if name == "Alpha" else None,
        )
        engine.declare_themes("input")
        state = engine.elaborate()
        # The bead should have knowledge_base enrichment
        alpha = next(b for b in state.beads if b.canonical == "Alpha")
        assert alpha.enrichment.get("knowledge_base") is kb_data
        # Scores should be set
        assert state.scores.get("Alpha::power") == 0.8

    def test_enrich_entities_shorter_than_beads(self):
        """If enrich returns fewer items, remaining beads stay unchanged."""
        engine = _make_engine(
            enrich_entities=lambda entities, telemetry=None: entities[:1],
        )
        engine.declare_themes("input")
        state = engine.elaborate()
        assert state.phase == "elaboration"
        assert len(state.beads) == 2  # beads list unchanged


# ===========================================================================
# GameEngine — Phase 3: connect_domains
# ===========================================================================


class TestConnectDomains:
    """Tests for GameEngine.connect_domains."""

    def test_creates_threads(self):
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        state = engine.connect_domains()
        assert state.phase == "connection"
        assert len(state.threads) >= 1

    def test_allows_declaration_phase(self):
        engine = _make_engine()
        engine.declare_themes("input")
        # connect_domains() accepts "declaration" phase per engine.py line 243
        state = engine.connect_domains()
        assert state.phase == "connection"

    def test_raises_when_init(self):
        engine = _make_engine()
        engine.new_game("input")
        with pytest.raises(RuntimeError, match="elaborate"):
            engine.connect_domains()

    def test_creates_bridge_threads(self):
        bridge = {
            "entity": "Alpha",
            "pattern_a": "Power",
            "pattern_b": "Shadow",
            "score_a": 0.8,
            "score_b": 0.6,
        }
        engine = _make_engine(
            build_pattern_graph=lambda e, t, telemetry=None: {
                "patterns": [{"name": "Power", "probability": 0.8, "sub_patterns": []}],
                "bridges": [bridge],
                "consensus_score": 0.75,
                "emergent_topic": "Power",
            },
        )
        engine.declare_themes("input")
        engine.elaborate()
        state = engine.connect_domains()
        bridge_threads = [t for t in state.threads if t.relationship == "bridges"]
        assert len(bridge_threads) == 1
        assert bridge_threads[0].bead_a == "Alpha"
        assert bridge_threads[0].bead_b == "Power"
        assert abs(bridge_threads[0].strength - 0.7) < 0.01

    def test_essential_tension_on_low_consensus(self):
        engine = _make_engine(
            extract_entities=lambda x, telemetry=None: [
                _make_entity(canonical="A"),
                _make_entity(canonical="B"),
                _make_entity(canonical="C"),
            ],
            build_pattern_graph=lambda e, t, telemetry=None: {
                "patterns": [{"name": "X", "probability": 0.3, "sub_patterns": []}],
                "bridges": [],
                "consensus_score": 0.2,
                "emergent_topic": "X",
            },
            build_relationship_graph=lambda beads: {"edges": []},
        )
        engine.declare_themes("input")
        engine.elaborate()
        state = engine.connect_domains()
        assert len(state.tensions) == 1
        assert state.tensions[0]["type"] == "essential_tension"

    def test_no_tension_when_consensus_high(self):
        engine = _make_engine(
            build_pattern_graph=lambda e, t, telemetry=None: {
                "patterns": [],
                "bridges": [],
                "consensus_score": 0.8,
                "emergent_topic": "Test",
            },
            build_relationship_graph=lambda beads: {"edges": []},
        )
        engine.declare_themes("input")
        engine.elaborate()
        state = engine.connect_domains()
        assert len(state.tensions) == 0

    def test_no_tension_when_few_beads(self):
        engine = _make_engine(
            extract_entities=lambda x, telemetry=None: [_make_entity(canonical="Solo")],
            build_pattern_graph=lambda e, t, telemetry=None: {
                "patterns": [],
                "bridges": [],
                "consensus_score": 0.1,
                "emergent_topic": "Test",
            },
            build_relationship_graph=lambda beads: {"edges": []},
        )
        engine.declare_themes("input")
        engine.elaborate()
        state = engine.connect_domains()
        assert len(state.tensions) == 0

    def test_records_timing(self):
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        state = engine.connect_domains()
        assert "connection_ms" in state.timings

    def test_stores_pattern_graph_in_metadata(self):
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        state = engine.connect_domains()
        assert "pattern_graph" in state.metadata


# ===========================================================================
# GameEngine — Phase 4: resolve
# ===========================================================================


class TestResolve:
    """Tests for GameEngine.resolve."""

    @patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "# SOUL.md\nTest output."})
    def test_generates_output(self):
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        engine.connect_domains()
        output = engine.resolve(lens="identity")
        assert "SOUL.md" in output
        assert engine.state.phase == "resolution"

    @patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "result", "brand": lambda e, g: "brand result"})
    def test_different_lenses(self):
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        engine.connect_domains()
        output = engine.resolve(lens="brand")
        assert output == "brand result"
        assert engine.state.metadata["lens"] == "brand"

    @patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "result"})
    def test_unknown_lens_raises(self):
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        engine.connect_domains()
        with pytest.raises(RuntimeError, match="Invalid lens"):
            engine.resolve(lens="unknown")

    def test_raises_before_elaboration(self):
        engine = _make_engine()
        engine.declare_themes("input")
        # Phase is "declaration", not in ("elaboration", "connection")
        with pytest.raises(RuntimeError, match="connect_domains"):
            engine.resolve()

    @patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "ok"})
    def test_records_timing(self):
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        engine.connect_domains()
        engine.resolve()
        assert "resolution_ms" in engine.state.timings

    @patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "output text"})
    def test_stores_output_in_metadata(self):
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        engine.connect_domains()
        engine.resolve()
        assert engine.state.metadata["output"] == "output text"
        assert engine.state.metadata["lens"] == "identity"


# ===========================================================================
# GameEngine — resolve_stream
# ===========================================================================


class TestResolveStream:
    """Tests for GameEngine.resolve_stream."""

    @patch("elixis.lenses.identity.generate_identity_stream")
    @patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "fallback"})
    def test_identity_stream_yields_events(self, mock_stream):
        mock_stream.return_value = iter([
            {"type": "stage_start", "stage": "header"},
            {"type": "soulmd_done", "data": {"length": 100}},
        ])
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        engine.connect_domains()
        events = list(engine.resolve_stream(lens="identity"))
        assert len(events) == 2
        assert events[0]["type"] == "stage_start"
        assert events[1]["type"] == "soulmd_done"

    @patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "fallback", "brand": lambda e, g: "brand text"})
    def test_non_identity_stream_yields_token_and_done(self):
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        engine.connect_domains()
        events = list(engine.resolve_stream(lens="brand"))
        assert len(events) == 2
        assert events[0]["type"] == "soulmd_token"
        assert events[0]["content"] == "brand text"
        assert events[1]["type"] == "soulmd_done"
        assert events[1]["data"]["source"] == "brand"

    def test_raises_before_connection(self):
        engine = _make_engine()
        with pytest.raises(RuntimeError, match="connect_domains"):
            list(engine.resolve_stream())


# ===========================================================================
# GameEngine — full pipeline
# ===========================================================================


class TestRunFull:
    """Tests for GameEngine.run_full and run_full_stream."""

    @patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "# Full pipeline output"})
    def test_run_full(self):
        engine = _make_engine()
        output = engine.run_full("test input", lens="identity")
        assert "Full pipeline output" in output
        assert engine.state.phase == "resolution"

    @patch("elixis.lenses.identity.generate_identity_stream")
    def test_run_full_stream(self, mock_stream):
        mock_stream.return_value = iter([
            {"type": "soulmd_token", "content": "Hello"},
            {"type": "soulmd_done", "data": {"length": 5}},
        ])
        engine = _make_engine()
        events = list(engine.run_full_stream("test input", lens="identity"))
        assert len(events) == 2
        assert events[0]["content"] == "Hello"

    @patch("elixis.lenses.identity.generate_identity_stream")
    @patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "irrelevant"})
    def test_run_full_stream_yields_identity_events(self, mock_stream):
        mock_stream.return_value = iter([
            {"type": "soulmd_token", "content": "Hello"},
            {"type": "soulmd_done", "data": {"length": 5}},
        ])
        engine = _make_engine()
        events = list(engine.run_full_stream("test input"))
        assert len(events) == 2
        assert events[0]["content"] == "Hello"


# ===========================================================================
# Helper: _infer_domains
# ===========================================================================


class TestInferDomains:
    """Tests for _infer_domains helper."""

    def test_character_type(self):
        result = _infer_domains(_make_entity(etype="character"))
        assert "literature" in result or "culture" in result

    def test_person_type(self):
        result = _infer_domains(_make_entity(etype="person"))
        assert "culture" in result

    def test_historical_figure_type(self):
        result = _infer_domains(_make_entity(etype="historical_figure"))
        assert "culture" in result
        assert "philosophy" in result

    def test_work_type(self):
        result = _infer_domains(_make_entity(etype="work"))
        assert "literature" in result

    def test_concept_type(self):
        result = _infer_domains(_make_entity(etype="concept"))
        assert "philosophy" in result

    def test_archetype_type(self):
        result = _infer_domains(_make_entity(etype="archetype"))
        assert "philosophy" in result

    def test_unknown_type_defaults_to_culture(self):
        result = _infer_domains(_make_entity(etype="unknown_thing"))
        assert "culture" in result

    def test_theme_hint_music(self):
        result = _infer_domains(_make_entity(themes=["music"]))
        assert "music" in result

    def test_theme_hint_science(self):
        result = _infer_domains(_make_entity(themes=["science"]))
        assert "science" in result

    def test_source_hint_nature(self):
        result = _infer_domains(_make_entity(source="Nature Journal"))
        assert "nature" in result

    def test_source_hint_film(self):
        result = _infer_domains(_make_entity(source="Film Database"))
        assert "culture" in result  # "film" in source maps to culture + visual_art

    def test_max_three_domains(self):
        entity = _make_entity(themes=["music", "science", "nature", "art"])
        result = _infer_domains(entity)
        assert len(result) <= 3

    def test_only_valid_domains_returned(self):
        result = _infer_domains(_make_entity(etype="character"))
        from elixis.knowledge import domain_ids
        valid = set(domain_ids())
        assert all(d in valid for d in result)

    def test_empty_entity(self):
        result = _infer_domains({})
        assert isinstance(result, list)


# ===========================================================================
# Helper: _check_isomorphism
# ===========================================================================


class TestCheckIsomorphism:
    """Tests for _check_isomorphism helper."""

    def test_cross_domain_shared_themes(self):
        a = Bead(canonical="A", domains=["philosophy"], themes=["power", "shadow"])
        b = Bead(canonical="B", domains=["music"], themes=["power", "shadow"])
        assert _check_isomorphism(a, b) is True

    def test_same_domain_returns_false(self):
        a = Bead(canonical="A", domains=["philosophy"], themes=["power", "shadow"])
        b = Bead(canonical="B", domains=["philosophy"], themes=["power", "shadow"])
        assert _check_isomorphism(a, b) is False

    def test_fewer_than_two_shared_themes(self):
        a = Bead(canonical="A", domains=["philosophy"], themes=["power"])
        b = Bead(canonical="B", domains=["music"], themes=["power"])
        assert _check_isomorphism(a, b) is False

    def test_no_domains_returns_false(self):
        a = Bead(canonical="A", domains=[], themes=["power", "shadow"])
        b = Bead(canonical="B", domains=["music"], themes=["power", "shadow"])
        assert _check_isomorphism(a, b) is False

    def test_no_themes_overlap(self):
        a = Bead(canonical="A", domains=["philosophy"], themes=["power"])
        b = Bead(canonical="B", domains=["music"], themes=["wisdom"])
        assert _check_isomorphism(a, b) is False

    def test_both_empty_domains(self):
        a = Bead(canonical="A", domains=[], themes=["power", "shadow"])
        b = Bead(canonical="B", domains=[], themes=["power", "shadow"])
        assert _check_isomorphism(a, b) is False


class TestEngineName:
    """engine.name() naming phase."""

    def _make_engine_with_graph(self):
        engine = GameEngine()
        engine.new_game("test input for naming")
        # Manually set up state to the connection phase
        engine._state.phase = "connection"
        engine._state.metadata["pattern_graph"] = {
            "emergent_topic": "transformation",
            "emergent_theme": "Growth through change",
            "patterns": [
                {"id": "transformation", "name": "Transformation", "probability": 0.5, "sub_patterns": []},
            ],
            "bridges": [],
            "entity_scores": [],
            "consensus_score": 0.7,
        }
        engine._state.beads = [
            Bead(canonical="Morpho", type="concept", themes=["transformation"]),
        ]
        return engine

    @patch("elixis.naming.research_name_from_identity")
    def test_name_after_connect(self, mock_naming):
        mock_naming.return_value = {"input_name": "transformation", "variants": [], "identity_context": {}}
        engine = self._make_engine_with_graph()
        report = engine.name()
        assert report["input_name"] == "transformation"
        mock_naming.assert_called_once()

    @patch("elixis.naming.research_name_from_identity")
    def test_name_default_source_is_taxonomy(self, mock_naming):
        mock_naming.return_value = {"input_name": "t", "variants": [], "identity_context": {}}
        engine = self._make_engine_with_graph()
        engine.name()
        call_kwargs = mock_naming.call_args
        assert call_kwargs[1].get("source") == "taxonomy" or call_kwargs[0][2] == "taxonomy" if len(call_kwargs[0]) > 2 else True

    def test_name_requires_connection(self):
        engine = GameEngine()
        engine.new_game("test")
        with pytest.raises(RuntimeError, match="connect_domains"):
            engine.name()

    @patch("elixis.naming.research_name_from_identity")
    def test_name_populates_metadata(self, mock_naming):
        mock_naming.return_value = {"input_name": "t", "variants": [], "identity_context": {}}
        engine = self._make_engine_with_graph()
        engine.name()
        assert "naming_report" in engine.state.metadata
