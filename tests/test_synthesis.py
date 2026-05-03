"""Tests for elixis.synthesis — SOUL.md template synthesis and helpers."""

from unittest.mock import patch

from elixis.synthesis import (
    _derive_identity_name,
    _derive_who_i_am,
    _derive_worldview,
    _derive_voice_and_tone,
    _derive_principles,
    _derive_response_patterns,
    _derive_response_patterns_for_pattern,
    _derive_boundaries,
    _derive_boundaries_for_pattern,
    _derive_pet_peeves,
    _derive_pet_peeves_for_entities,
    _template_synthesize,
    synthesize_soulmd,
    synthesize_soulmd_stream,
    _build_llm_messages,
    _VOICE_PROFILES,
    _PRINCIPLE_MAP,
    _FALLBACK_PRINCIPLES,
)


def _make_entity(**overrides):
    defaults = {
        "canonical": "Test Entity",
        "original": "Test Entity",
        "themes": ["power"],
        "traits": [],
        "confidence": 0.8,
    }
    defaults.update(overrides)
    return defaults


def _make_graph(**overrides):
    defaults = {
        "patterns": [
            {"id": "power", "name": "Power", "probability": 0.4, "supporting_entities": 3},
        ],
        "bridges": [],
        "consensus_score": 0.6,
        "emergent_topic": "Power",
        "emergent_theme": "the exercise of will",
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# _derive_identity_name
# ---------------------------------------------------------------------------

class TestDeriveIdentityName:
    def test_three_or_more_entities(self):
        entities = [_make_entity(), _make_entity(), _make_entity()]
        graph = _make_graph(emergent_topic="Power")
        assert _derive_identity_name(entities, graph) == "The Power Identity"

    def test_fewer_than_three_entities(self):
        entities = [_make_entity()]
        graph = _make_graph()
        assert _derive_identity_name(entities, graph) == "The Constructed Self"

    def test_empty_entities(self):
        graph = _make_graph()
        assert _derive_identity_name([], graph) == "The Constructed Self"


# ---------------------------------------------------------------------------
# _derive_who_i_am
# ---------------------------------------------------------------------------

class TestDeriveWhoIAm:
    def test_high_consensus(self):
        entities = [_make_entity(canonical="Mozart"), _make_entity(canonical="Beethoven")]
        graph = _make_graph(consensus_score=0.8, emergent_topic="Power", emergent_theme="will")
        result = _derive_who_i_am(entities, graph)
        assert "Mozart" in result
        assert "Beethoven" in result

    def test_low_consensus(self):
        entities = [_make_entity(canonical="Mozart"), _make_entity(canonical="Beethoven")]
        graph = _make_graph(consensus_score=0.3, emergent_topic="Power")
        result = _derive_who_i_am(entities, graph)
        assert "multifaceted" in result

    def test_single_entity(self):
        entities = [_make_entity(canonical="Mozart")]
        graph = _make_graph(consensus_score=0.7)
        result = _derive_who_i_am(entities, graph)
        assert "Mozart" in result

    def test_empty_entities(self):
        graph = _make_graph(consensus_score=0.6)
        result = _derive_who_i_am([], graph)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# _derive_worldview
# ---------------------------------------------------------------------------

class TestDeriveWorldview:
    def test_with_patterns(self):
        graph = _make_graph(patterns=[
            {"id": "power", "name": "Power", "probability": 0.4},
            {"id": "wisdom", "name": "Wisdom", "probability": 0.2},
        ])
        result = _derive_worldview(graph)
        assert "deeply" in result
        assert "often" in result

    def test_low_probability_filtered(self):
        graph = _make_graph(patterns=[
            {"id": "power", "name": "Power", "probability": 0.03},
        ])
        result = _derive_worldview(graph)
        assert "identity is something you do" in result

    def test_empty_patterns(self):
        graph = _make_graph(patterns=[])
        result = _derive_worldview(graph)
        assert "identity is something you do" in result

    def test_sometimes_intensity(self):
        graph = _make_graph(patterns=[
            {"id": "power", "name": "Power", "probability": 0.10},
        ])
        result = _derive_worldview(graph)
        assert "sometimes" in result


# ---------------------------------------------------------------------------
# _derive_voice_and_tone
# ---------------------------------------------------------------------------

class TestDeriveVoiceAndTone:
    def test_uses_top_pattern_voice(self):
        graph = _make_graph(patterns=[
            {"id": "shadow", "name": "Shadow", "probability": 0.5},
        ])
        result = _derive_voice_and_tone(graph)
        assert result == _VOICE_PROFILES["shadow"]

    def test_empty_patterns_uses_wisdom(self):
        graph = _make_graph(patterns=[])
        result = _derive_voice_and_tone(graph)
        assert result == _VOICE_PROFILES["wisdom"]

    def test_unknown_pattern_uses_wisdom(self):
        graph = _make_graph(patterns=[
            {"id": "nonexistent", "name": "X", "probability": 0.5},
        ])
        result = _derive_voice_and_tone(graph)
        assert result == _VOICE_PROFILES["wisdom"]


# ---------------------------------------------------------------------------
# _derive_principles
# ---------------------------------------------------------------------------

class TestDerivePrinciples:
    def test_with_known_patterns(self):
        graph = _make_graph(patterns=[
            {"id": "power", "name": "Power", "probability": 0.4},
            {"id": "wisdom", "name": "Wisdom", "probability": 0.3},
        ])
        result = _derive_principles(graph)
        assert _PRINCIPLE_MAP["power"] in result
        assert _PRINCIPLE_MAP["wisdom"] in result

    def test_low_probability_filtered(self):
        graph = _make_graph(patterns=[
            {"id": "power", "name": "Power", "probability": 0.03},
        ])
        result = _derive_principles(graph)
        assert _PRINCIPLE_MAP["power"] not in result

    def test_few_patterns_adds_fallback(self):
        graph = _make_graph(patterns=[
            {"id": "power", "name": "Power", "probability": 0.4},
        ])
        result = _derive_principles(graph)
        assert _FALLBACK_PRINCIPLES[0] in result

    def test_empty_patterns(self):
        graph = _make_graph(patterns=[])
        result = _derive_principles(graph)
        assert _FALLBACK_PRINCIPLES[0] in result
        assert _FALLBACK_PRINCIPLES[1] in result

    def test_max_five_principles(self):
        graph = _make_graph(patterns=[
            {"id": k, "name": k.title(), "probability": 0.3}
            for k in list(_PRINCIPLE_MAP.keys())[:6]
        ])
        result = _derive_principles(graph)
        lines = [line for line in result.split("\n") if line.strip()]
        assert len(lines) <= 5


# ---------------------------------------------------------------------------
# _derive_response_patterns
# ---------------------------------------------------------------------------

class TestDeriveResponsePatterns:
    def test_returns_string(self):
        result = _derive_response_patterns()
        assert isinstance(result, str)
        assert "challenged" in result


# ---------------------------------------------------------------------------
# _derive_response_patterns_for_pattern
# ---------------------------------------------------------------------------

class TestDeriveResponsePatternsForPattern:
    def test_known_pattern(self):
        result = _derive_response_patterns_for_pattern("power")
        assert "cornered" in result

    def test_unknown_pattern(self):
        result = _derive_response_patterns_for_pattern("nonexistent")
        assert result == ""


# ---------------------------------------------------------------------------
# _derive_boundaries
# ---------------------------------------------------------------------------

class TestDeriveBoundaries:
    def test_returns_string(self):
        result = _derive_boundaries()
        assert isinstance(result, str)
        assert "certainty" in result


# ---------------------------------------------------------------------------
# _derive_boundaries_for_pattern
# ---------------------------------------------------------------------------

class TestDeriveBoundariesForPattern:
    def test_known_pattern(self):
        result = _derive_boundaries_for_pattern("power")
        assert "influence" in result

    def test_unknown_pattern(self):
        result = _derive_boundaries_for_pattern("nonexistent")
        assert result == ""


# ---------------------------------------------------------------------------
# _derive_pet_peeves
# ---------------------------------------------------------------------------

class TestDerivePetPeeves:
    def test_returns_string(self):
        result = _derive_pet_peeves()
        assert isinstance(result, str)
        assert "Corporate" in result


# ---------------------------------------------------------------------------
# _derive_pet_peeves_for_entities
# ---------------------------------------------------------------------------

class TestDerivePetPeevesForEntities:
    def test_power_theme(self):
        entities = [_make_entity(themes=["power"])]
        result = _derive_pet_peeves_for_entities(entities)
        assert "humility" in result

    def test_wisdom_theme(self):
        entities = [_make_entity(themes=["wisdom"])]
        result = _derive_pet_peeves_for_entities(entities)
        assert "question that matters" in result

    def test_freedom_theme(self):
        entities = [_make_entity(themes=["freedom"])]
        result = _derive_pet_peeves_for_entities(entities)
        assert "permission" in result

    def test_no_matching_theme(self):
        entities = [_make_entity(themes=["creation"])]
        result = _derive_pet_peeves_for_entities(entities)
        assert result == ""

    def test_empty_entities(self):
        result = _derive_pet_peeves_for_entities([])
        assert result == ""


# ---------------------------------------------------------------------------
# _template_synthesize
# ---------------------------------------------------------------------------

class TestTemplateSynthesize:
    def test_produces_soul_md(self):
        entities = [_make_entity(), _make_entity(), _make_entity()]
        graph = _make_graph()
        result = _template_synthesize(entities, graph)
        assert "# The Power Identity" in result
        assert "## Who I Am" in result
        assert "## Worldview" in result
        assert "## Voice & Tone" in result
        assert "## Operating Principles" in result
        assert "## Response Patterns" in result
        assert "## Boundaries" in result
        assert "## Pet Peeves" in result

    def test_includes_footer(self):
        entities = [_make_entity()]
        graph = _make_graph()
        result = _template_synthesize(entities, graph)
        assert "Generated by Elixis" in result

    def test_includes_pattern_response_hint(self):
        entities = [_make_entity()]
        graph = _make_graph(patterns=[
            {"id": "power", "name": "Power", "probability": 0.5, "supporting_entities": 2},
        ])
        result = _template_synthesize(entities, graph)
        assert "reframe the terms" in result

    def test_includes_pattern_boundary(self):
        entities = [_make_entity()]
        graph = _make_graph(patterns=[
            {"id": "shadow", "name": "Shadow", "probability": 0.5, "supporting_entities": 2},
        ])
        result = _template_synthesize(entities, graph)
        assert "discomfort" in result

    def test_includes_entity_pet_peeve(self):
        entities = [_make_entity(themes=["power"])]
        graph = _make_graph()
        result = _template_synthesize(entities, graph)
        assert "humility" in result

    def test_no_pattern_hint(self):
        entities = [_make_entity()]
        graph = _make_graph(patterns=[])
        result = _template_synthesize(entities, graph)
        assert "## Response Patterns" in result


# ---------------------------------------------------------------------------
# _build_llm_messages
# ---------------------------------------------------------------------------

class TestBuildLlmMessages:
    def test_returns_two_messages(self):
        entities = [_make_entity(canonical="Mozart")]
        graph = _make_graph()
        messages = _build_llm_messages(entities, graph)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_includes_entity_names(self):
        entities = [_make_entity(canonical="Mozart"), _make_entity(canonical="Beethoven")]
        graph = _make_graph()
        messages = _build_llm_messages(entities, graph)
        assert "Mozart" in messages[1]["content"]
        assert "Beethoven" in messages[1]["content"]

    def test_includes_bridges(self):
        entities = [_make_entity()]
        graph = _make_graph(bridges=[
            {"entity": "X", "pattern_a": "Power", "score_a": 0.5,
             "pattern_b": "Wisdom", "score_b": 0.4},
        ])
        messages = _build_llm_messages(entities, graph)
        assert "Pattern bridges" in messages[1]["content"]

    def test_no_bridges(self):
        entities = [_make_entity()]
        graph = _make_graph(bridges=[])
        messages = _build_llm_messages(entities, graph)
        assert "Pattern bridges" not in messages[1]["content"]


# ---------------------------------------------------------------------------
# synthesize_soulmd (with mocked LLM)
# ---------------------------------------------------------------------------

class TestSynthesizeSoulmd:
    @patch("elixis.synthesis.llm_available", return_value=False)
    def test_uses_template_when_no_llm(self, mock_avail):
        entities = [_make_entity(), _make_entity(), _make_entity()]
        graph = _make_graph()
        result = synthesize_soulmd(entities, graph)
        assert "## Who I Am" in result

    @patch("elixis.synthesis.llm_available", return_value=True)
    @patch("elixis.synthesis._llm_synthesize")
    def test_uses_llm_when_available(self, mock_llm, mock_avail):
        mock_llm.return_value = "# LLM Output\n\nGenerated content here."
        entities = [_make_entity()]
        graph = _make_graph()
        result = synthesize_soulmd(entities, graph)
        assert result == "# LLM Output\n\nGenerated content here."


# ---------------------------------------------------------------------------
# synthesize_soulmd_stream (with mocked LLM)
# ---------------------------------------------------------------------------

class TestSynthesizeSoulmdStream:
    @patch("elixis.synthesis.llm_available", return_value=False)
    def test_template_stream_yields_events(self, mock_avail):
        entities = [_make_entity()]
        graph = _make_graph()
        events = list(synthesize_soulmd_stream(entities, graph))
        types = [e["type"] for e in events]
        assert "soulmd_token" in types
        assert "soulmd_done" in types
        assert events[-1]["data"]["source"] == "template"

    @patch("elixis.synthesis.llm_available", return_value=True)
    @patch("elixis.synthesis.chat_stream")
    def test_llm_stream_yields_events(self, mock_stream, mock_avail):
        mock_stream.return_value = [
            {"type": "token", "content": "Hello "},
            {"type": "token", "content": "World"},
            {"type": "done", "latency_ms": 100, "model": "test", "provider": "ollama",
             "tokens_in": 10, "tokens_out": 5, "tokens_per_sec": 50},
        ]
        entities = [_make_entity()]
        graph = _make_graph()
        events = list(synthesize_soulmd_stream(entities, graph))
        types = [e["type"] for e in events]
        assert "soulmd_token" in types
        assert "telemetry" in types
        assert "soulmd_done" in types
        assert events[-1]["data"]["source"] == "llm"

    @patch("elixis.synthesis.llm_available", return_value=True)
    @patch("elixis.synthesis.chat_stream")
    def test_llm_stream_with_thinking(self, mock_stream, mock_avail):
        mock_stream.return_value = [
            {"type": "thinking", "content": "hmm"},
            {"type": "token", "content": "output"},
            {"type": "done", "latency_ms": 50, "model": "test", "provider": "ollama",
             "tokens_in": 5, "tokens_out": 2, "tokens_per_sec": 40},
        ]
        events = list(synthesize_soulmd_stream([_make_entity()], _make_graph()))
        thinking_events = [e for e in events if e["type"] == "thinking"]
        assert len(thinking_events) == 1
        assert thinking_events[0]["content"] == "hmm"

    @patch("elixis.synthesis.llm_available", return_value=True)
    @patch("elixis.synthesis.chat_stream")
    def test_llm_stream_telemetry(self, mock_stream, mock_avail):
        mock_stream.return_value = [
            {"type": "token", "content": "text"},
            {"type": "done", "latency_ms": 200, "model": "test", "provider": "ollama",
             "tokens_in": 20, "tokens_out": 10, "tokens_per_sec": 50},
        ]
        events = list(synthesize_soulmd_stream(
            [_make_entity()], _make_graph(), stage_timings={"stage1_ms": 100},
        ))
        telemetry = [e for e in events if e["type"] == "telemetry"][0]
        assert telemetry["data"]["tokens_prompt"] == 20
        assert telemetry["data"]["tokens_completion"] == 10
        assert telemetry["data"]["tokens_total"] == 30
        assert telemetry["data"]["total_ms"] == 300
        assert telemetry["data"]["stage_timings_ms"]["stage1_ms"] == 100
