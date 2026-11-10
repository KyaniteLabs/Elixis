"""State-machine tests for the GameEngine phase lifecycle (elixis.engine.Phase).

Covers: the transition table, every legal move, every illegal move refused,
legacy/unknown stored values read tolerantly, regressions for the bugs the
explicit machine fixed, and a seeded random-walk model test (stdlib only, the
project has no runtime or test dependency beyond pytest).
"""

import json
import random
from unittest.mock import patch

import pytest

from elixis.engine import (
    NAMEABLE_PHASES,
    TRANSITIONS,
    GameEngine,
    GameState,
    IllegalTransition,
    Move,
    Phase,
    can_transition,
    parse_phase,
    transition,
)
from tests.test_engine import _make_engine

# The expected table, written out independently of the implementation.
EXPECTED = {
    Move.DECLARE: ({Phase.INIT}, Phase.DECLARATION),
    Move.ELABORATE: ({Phase.INIT, Phase.DECLARATION}, Phase.ELABORATION),
    Move.CONNECT: ({Phase.DECLARATION, Phase.ELABORATION}, Phase.CONNECTION),
    Move.RESOLVE: ({Phase.ELABORATION, Phase.CONNECTION}, Phase.RESOLUTION),
}


ALL_PAIRS = [(phase, move) for phase in Phase for move in Move]


class TestTable:
    def test_every_move_is_in_the_table(self):
        assert set(TRANSITIONS) == set(Move)
        assert set(EXPECTED) == set(Move)

    def test_table_matches_expected(self):
        for move, (sources, target) in EXPECTED.items():
            assert set(TRANSITIONS[move][0]) == sources
            assert TRANSITIONS[move][1] == target

    def test_every_phase_is_reachable_or_initial(self):
        targets = {TRANSITIONS[m][1] for m in Move}
        assert targets | {Phase.INIT} == set(Phase)

    def test_every_non_terminal_phase_has_an_exit(self):
        sources = set().union(*(TRANSITIONS[m][0] for m in Move))
        assert set(Phase) - sources == {Phase.RESOLUTION}

    def test_stored_values_are_unchanged(self):
        # Persisted/serialized strings must never change.
        assert [p.value for p in Phase] == [
            "init", "declaration", "elaboration", "connection", "resolution",
        ]

    def test_nameable_phases(self):
        assert NAMEABLE_PHASES == {Phase.ELABORATION, Phase.CONNECTION, Phase.RESOLUTION}


@pytest.mark.parametrize("phase,move", ALL_PAIRS, ids=[f"{p.value}-{m.value}" for p, m in ALL_PAIRS])
def test_transition_exhaustive(phase, move):
    """Every (phase, move) pair either lands on the expected target or is refused."""
    state = GameState(phase=phase)
    sources, target = EXPECTED[move]
    if phase in sources:
        assert can_transition(phase, move)
        transition(state, move)
        assert state.phase is target
    else:
        assert not can_transition(phase, move)
        with pytest.raises(IllegalTransition):
            transition(state, move)
        assert state.phase is phase  # refused move leaves state untouched


def test_illegal_transition_is_a_runtime_error():
    # Callers that caught RuntimeError keep working.
    assert issubclass(IllegalTransition, RuntimeError)


def test_transition_without_state_is_refused():
    with pytest.raises(IllegalTransition):
        transition(None, Move.DECLARE)


class TestLegacyValues:
    @pytest.mark.parametrize("raw", [p.value for p in Phase])
    def test_known_strings_parse(self, raw):
        assert parse_phase(raw) is Phase(raw)

    def test_missing_is_init(self):
        assert parse_phase(None) is Phase.INIT
        assert GameState.from_dict({}).phase is Phase.INIT

    def test_unknown_value_kept_verbatim_and_frozen(self):
        state = GameState.from_dict({"phase": "legacy-unknown"})
        assert state.phase == "legacy-unknown"
        assert state.to_dict()["phase"] == "legacy-unknown"
        for move in Move:
            with pytest.raises(IllegalTransition):
                transition(state, move)

    @pytest.mark.parametrize("raw", [p.value for p in Phase])
    def test_round_trip_is_byte_compatible(self, raw):
        state = GameState.from_dict({"phase": raw})
        assert json.dumps(state.to_dict()["phase"]) == json.dumps(raw)
        assert state.phase == raw


class TestEngineMoves:
    def test_happy_path(self):
        engine = _make_engine()
        with patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "out"}):
            engine.run_full("input")
        assert engine.state.phase is Phase.RESOLUTION

    def test_resolution_is_terminal(self):
        engine = _make_engine()
        with patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "out"}):
            engine.run_full("input")
            with pytest.raises(IllegalTransition):
                engine.resolve()
        with pytest.raises(IllegalTransition):
            engine.elaborate()
        with pytest.raises(IllegalTransition):
            engine.connect_domains()

    def test_new_game_resets_from_any_phase(self):
        engine = _make_engine()
        with patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "out"}):
            engine.run_full("input")
        engine.new_game("again")
        assert engine.state.phase is Phase.INIT

    def test_refused_move_does_no_work(self):
        calls = []
        engine = _make_engine(
            enrich_entities=lambda entities, telemetry=None: calls.append(1) or entities,
        )
        engine.declare_themes("input")
        engine.elaborate()
        with pytest.raises(IllegalTransition):
            engine.elaborate()
        assert calls == [1]


class TestBugRegressions:
    """Each test here fails on the pre-refactor engine."""

    def test_redeclare_without_input_is_refused(self):
        """Bug: declare_themes() with no raw_input was accepted from ANY phase.

        It rebuilt beads but kept the old threads, scores, pattern_graph and
        tensions, so running connect_domains() again appended a duplicate
        essential tension. Now re-declaring requires a new game.
        """
        engine = _make_engine(
            extract_entities=lambda x, telemetry=None: [
                {"canonical": n, "original": n, "type": "concept", "themes": ["t"],
                 "traits": [], "confidence": 0.5}
                for n in ("A", "B", "C")
            ],
            build_pattern_graph=lambda e, t, telemetry=None: {
                "patterns": [], "bridges": [], "consensus_score": 0.1,
            },
            build_relationship_graph=lambda beads: {"edges": []},
        )
        engine.declare_themes("input")
        engine.elaborate()
        engine.connect_domains()
        assert len(engine.state.tensions) == 1
        with pytest.raises(IllegalTransition):
            engine.declare_themes()
        assert engine.state.phase is Phase.CONNECTION
        assert len(engine.state.tensions) == 1

    def test_redeclare_with_input_starts_fresh(self):
        engine = _make_engine()
        engine.declare_themes("first")
        engine.elaborate()
        state = engine.declare_themes("second")
        assert state.phase is Phase.DECLARATION
        assert state.raw_input == "second"

    @patch("elixis.lenses.identity.generate_identity_stream")
    def test_identity_stream_reaches_resolution(self, mock_stream):
        """Bug: resolve_stream(lens="identity") never moved to RESOLUTION.

        resolve() and resolve_stream() were copies that disagreed: only the
        non-streaming path set the phase, output, lens and resolution_ms.
        After a full streamed run the game stayed in CONNECTION and could be
        resolved a second time.
        """
        mock_stream.return_value = iter([
            {"type": "soulmd_token", "content": "Hel"},
            {"type": "soulmd_token", "content": "lo"},
            {"type": "soulmd_done", "data": {"length": 5}},
        ])
        engine = _make_engine()
        list(engine.run_full_stream("input", lens="identity"))
        state = engine.state
        assert state.phase is Phase.RESOLUTION
        assert state.metadata["output"] == "Hello"
        assert state.metadata["lens"] == "identity"
        assert "resolution_ms" in state.timings
        with pytest.raises(IllegalTransition):
            list(engine.resolve_stream(lens="identity"))

    @patch("elixis.lenses.identity.generate_identity_stream")
    def test_abandoned_stream_stays_in_connection(self, mock_stream):
        mock_stream.return_value = iter([
            {"type": "soulmd_token", "content": "a"},
            {"type": "soulmd_token", "content": "b"},
        ])
        engine = _make_engine()
        engine.declare_themes("input")
        engine.elaborate()
        engine.connect_domains()
        stream = engine.resolve_stream(lens="identity")
        next(stream)
        stream.close()
        assert engine.state.phase is Phase.CONNECTION
        assert "output" not in engine.state.metadata


# ---------------------------------------------------------------------------
# Stateful model test: random walks over the public engine API
# ---------------------------------------------------------------------------

ACTIONS = ("new_game", "declare", "declare_input", "elaborate", "connect", "resolve", "name")


def _model_step(phase, action):
    """Reference model: returns the next phase, or None when the call must raise."""
    if action == "new_game":
        return Phase.INIT
    if action == "declare_input":
        return Phase.DECLARATION
    if phase is None:
        return None
    if action == "name":
        return phase if phase in NAMEABLE_PHASES else None
    move = {"declare": Move.DECLARE, "elaborate": Move.ELABORATE,
            "connect": Move.CONNECT, "resolve": Move.RESOLVE}[action]
    return EXPECTED[move][1] if phase in EXPECTED[move][0] else None


def _apply(engine, action):
    if action == "new_game":
        engine.new_game("walk")
    elif action == "declare":
        engine.declare_themes()
    elif action == "declare_input":
        engine.declare_themes("walk")
    elif action == "elaborate":
        engine.elaborate()
    elif action == "connect":
        engine.connect_domains()
    elif action == "resolve":
        engine.resolve("identity")
    elif action == "name":
        engine.name()


@pytest.mark.parametrize("seed", range(40))
def test_random_walk_matches_model(seed):
    rng = random.Random(seed)
    engine = _make_engine()
    model = None
    with patch("elixis.lenses.LENS_REGISTRY", {"identity": lambda e, g: "out"}), \
         patch("elixis.naming.research_name_from_identity", return_value={"variants": []}):
        for _ in range(60):
            action = rng.choice(ACTIONS)
            expected = _model_step(model, action)
            before = engine.state.phase if engine.state else None
            if expected is None:
                with pytest.raises(RuntimeError):
                    _apply(engine, action)
                after = engine.state.phase if engine.state else None
                assert after == before, f"refused {action} changed phase"
            else:
                _apply(engine, action)
                model = expected
            # Invariants after every step.
            current = engine.state.phase if engine.state else None
            assert current == model
            if current is not None:
                assert current in set(Phase)
                if current is Phase.CONNECTION:
                    assert "pattern_graph" in engine.state.metadata
                if current is Phase.RESOLUTION:
                    assert "output" in engine.state.metadata
                    assert "resolution_ms" in engine.state.timings
                if current is Phase.INIT:
                    assert engine.state.beads == []


def test_game_engine_import_unchanged():
    # Public name still importable from the same place.
    assert GameEngine is not None
