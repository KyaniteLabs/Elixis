"""Tests for elixis.entities — entity extraction, parsing, and type inference."""

from unittest.mock import patch

from elixis.entities import (
    _infer_type,
    _parse_line_entity,
    _heuristic_extract,
    _salient_phrase_entities,
    extract_entities,
    _llm_extract_entities,
)


# ---------------------------------------------------------------------------
# _infer_type
# ---------------------------------------------------------------------------

class TestInferType:
    def test_mythological_without_source(self):
        assert _infer_type("Zeus", "") == "mythological"

    def test_mythological_with_source(self):
        assert _infer_type("Zeus", "Greek Mythology") == "character"

    def test_mythological_gandalf(self):
        assert _infer_type("Gandalf", "") == "mythological"

    def test_place_hints(self):
        assert _infer_type("Dark City", "") == "place"

    def test_place_with_source_not_place(self):
        # "Dark City" with source "Film" — not a place (has source), not a person
        # (it's a work name, but no explicit work detection for this pattern)
        result = _infer_type("Dark City", "Film")
        assert result in ("character", "person", "work")

    def test_archetype_exact(self):
        assert _infer_type("hero", "") == "archetype"

    def test_archetype_in_name(self):
        assert _infer_type("Dark Knight", "") == "archetype"

    def test_archetype_long_name_not_archetype(self):
        assert _infer_type("The Great Warrior King of the North", "") == "concept"

    def test_character_with_source(self):
        # Walter White with a source is detected as person (2 caps + source)
        assert _infer_type("Walter White", "Breaking Bad") == "person"

    def test_concept_no_source(self):
        assert _infer_type("Freedom", "") == "concept"

    def test_yoda_is_mythological(self):
        assert _infer_type("Yoda", "") == "mythological"


# ---------------------------------------------------------------------------
# _parse_line_entity
# ---------------------------------------------------------------------------

class TestParseLineEntity:
    def test_simple_name(self):
        result = _parse_line_entity("Mozart")
        assert result is not None
        assert result["canonical"] == "Mozart"

    def test_name_with_parens_source(self):
        result = _parse_line_entity("Walter White (Breaking Bad)")
        assert result is not None
        assert result["canonical"] == "Walter White"
        assert result["source"] == "Breaking Bad"

    def test_name_with_dash_source(self):
        result = _parse_line_entity("Mozart - Classical Composer")
        assert result is not None
        assert result["canonical"] == "Mozart"
        assert result["source"] == "Classical Composer"

    def test_name_with_comma_source(self):
        result = _parse_line_entity("Bach, Classical Music")
        assert result is not None
        assert result["canonical"] == "Bach"
        assert result["source"] == "Classical Music"

    def test_name_with_from_source(self):
        result = _parse_line_entity("Gandalf from Lord of the Rings")
        assert result is not None
        assert result["canonical"] == "Gandalf"
        assert result["source"] == "Lord of the Rings"

    def test_name_with_slash_source(self):
        result = _parse_line_entity("Mozart / Classical Era")
        assert result is not None
        assert result["canonical"] == "Mozart"
        assert result["source"] == "Classical Era"

    def test_bullet_point(self):
        result = _parse_line_entity("- Mozart")
        assert result is not None
        assert result["canonical"] == "Mozart"

    def test_numbered_item(self):
        result = _parse_line_entity("1. Mozart")
        assert result is not None
        assert result["canonical"] == "Mozart"

    def test_empty_line(self):
        assert _parse_line_entity("") is None

    def test_short_text(self):
        assert _parse_line_entity("A") is None

    def test_none_like_input(self):
        assert _parse_line_entity("  ") is None

    def test_quotes_stripped(self):
        result = _parse_line_entity('"Mozart"')
        assert result is not None
        assert result["canonical"] == "Mozart"

    def test_type_inferred(self):
        result = _parse_line_entity("Zeus")
        assert result is not None
        assert result["type"] == "mythological"

    def test_original_preserved(self):
        result = _parse_line_entity("- Walter White (Breaking Bad)")
        assert result is not None
        assert "Walter White" in result["original"]

    def test_em_dash(self):
        result = _parse_line_entity("Mozart — Composer")
        assert result is not None
        assert result["canonical"] == "Mozart"

    def test_comma_short_name_splits(self):
        result = _parse_line_entity("Mozart, the great composer")
        assert result is not None
        assert result["canonical"] == "Mozart"
        assert result["source"] == "the great composer"

    def test_comma_long_name_not_split(self):
        # comma_match only splits if left side has <= 4 words — 5+ words stays whole
        result = _parse_line_entity("The Great Composer Wolfgang Mozart, of the classical era")
        assert result is not None
        assert "source" not in result or result.get("source", "") != "of the classical era"


# ---------------------------------------------------------------------------
# _heuristic_extract
# ---------------------------------------------------------------------------

class TestHeuristicExtract:
    def test_single_line_entity(self):
        result = _heuristic_extract("Mozart")
        assert len(result) >= 1
        assert result[0]["canonical"] == "Mozart"

    def test_multiline(self):
        text = "Mozart\nBeethoven\nBach"
        result = _heuristic_extract(text)
        assert len(result) == 3
        names = {e["canonical"] for e in result}
        assert "Mozart" in names
        assert "Beethoven" in names

    def test_deduplication(self):
        result = _heuristic_extract("Mozart\nMozart\nMozart")
        assert len(result) == 1

    def test_empty_text(self):
        assert _heuristic_extract("") == []

    def test_whitespace_only(self):
        assert _heuristic_extract("   \n  \n  ") == []

    def test_capitalized_fallback(self):
        # No line breaks → line parser finds nothing → capitalized phrase extraction
        result = _heuristic_extract("I love Sherlock Holmes and his methods")
        assert len(result) >= 1
        names = {e["canonical"] for e in result}
        # Holmes is a mythological hint so type should be mythological
        assert any("Holmes" in n for n in names)

    def test_capitalized_filters_starters(self):
        result = _heuristic_extract("The cat sat on the mat")
        names = [e["canonical"] for e in result]
        assert "The" not in names


class TestSalientPhraseEntities:
    def test_extracts_aesthetic_and_value_phrases(self):
        result = _salient_phrase_entities(
            "Athena, Batman, kyanite blue, operator clarity, ritual tools, calm exact systems",
            existing={"athena", "batman"},
        )
        names = {e["canonical"] for e in result}
        assert "kyanite blue" in names
        assert "operator clarity" in names
        assert "ritual tools" in names
        assert "calm exact systems" in names

    def test_skips_existing_phrases(self):
        result = _salient_phrase_entities("operator clarity, ritual tools", existing={"operator clarity"})
        names = {e["canonical"] for e in result}
        assert "operator clarity" not in names
        assert "ritual tools" in names


# ---------------------------------------------------------------------------
# _llm_extract_entities (mocked LLM)
# ---------------------------------------------------------------------------

class TestLlmExtractEntities:
    @patch("elixis.llm.is_available", return_value=False)
    def test_returns_empty_when_unavailable(self, mock_avail):
        result = _llm_extract_entities("Mozart, Beethoven")
        assert result == []

    @patch("elixis.parsing.parse_llm_json_array", return_value=None)
    @patch("elixis.llm.chat")
    @patch("elixis.llm.is_available", return_value=True)
    def test_returns_empty_on_parse_failure(self, mock_avail, mock_chat, mock_parse):
        mock_chat.return_value = {"content": "this is not valid json output"}
        result = _llm_extract_entities("test input")
        assert result == []

    @patch("elixis.parsing.parse_llm_json_array")
    @patch("elixis.llm.chat")
    @patch("elixis.llm.is_available", return_value=True)
    def test_extracts_dict_entities(self, mock_avail, mock_chat, mock_parse):
        mock_chat.return_value = {"content": "a valid json response array"}
        mock_parse.return_value = [
            {"name": "Mozart", "type": "historical_figure", "source": "",
             "themes": ["creation"], "traits": ["genius"], "related": ["Beethoven"]},
        ]
        result = _llm_extract_entities("I like Mozart")
        assert len(result) == 1
        assert result[0]["canonical"] == "Mozart"
        assert result[0]["confidence"] == 0.95

    @patch("elixis.parsing.parse_llm_json_array")
    @patch("elixis.llm.chat")
    @patch("elixis.llm.is_available", return_value=True)
    def test_extracts_string_entities(self, mock_avail, mock_chat, mock_parse):
        mock_chat.return_value = {"content": "a valid json response array"}
        mock_parse.return_value = ["Mozart"]
        result = _llm_extract_entities("I like Mozart")
        assert len(result) == 1
        assert result[0]["canonical"] == "Mozart"

    @patch("elixis.parsing.parse_llm_json_array")
    @patch("elixis.llm.chat")
    @patch("elixis.llm.is_available", return_value=True)
    def test_deduplicates(self, mock_avail, mock_chat, mock_parse):
        mock_chat.return_value = {"content": "a valid json response array"}
        mock_parse.return_value = [
            {"name": "Mozart", "type": "historical_figure"},
            {"name": "Mozart", "type": "historical_figure"},
        ]
        result = _llm_extract_entities("Mozart Mozart")
        assert len(result) == 1

    @patch("elixis.parsing.parse_llm_json_array")
    @patch("elixis.llm.chat")
    @patch("elixis.llm.is_available", return_value=True)
    def test_filters_short_names(self, mock_avail, mock_chat, mock_parse):
        mock_chat.return_value = {"content": "a valid json response array"}
        mock_parse.return_value = [
            {"name": "A", "type": "concept"},
            {"name": "Mozart", "type": "historical_figure"},
        ]
        result = _llm_extract_entities("test")
        assert len(result) == 1
        assert result[0]["canonical"] == "Mozart"

    @patch("elixis.parsing.parse_llm_json_array")
    @patch("elixis.llm.chat")
    @patch("elixis.llm.is_available", return_value=True)
    def test_handles_comma_separated_themes(self, mock_avail, mock_chat, mock_parse):
        mock_chat.return_value = {"content": "a valid json response array"}
        mock_parse.return_value = [
            {"name": "Mozart", "themes": "creation, wisdom", "traits": "genius"},
        ]
        result = _llm_extract_entities("test")
        assert result[0]["themes"] == ["creation", "wisdom"]
        assert result[0]["traits"] == ["genius"]

    @patch("elixis.llm.chat", side_effect=Exception("LLM down"))
    @patch("elixis.llm.is_available", return_value=True)
    def test_handles_chat_exception(self, mock_avail, mock_chat):
        result = _llm_extract_entities("test input")
        assert result == []

    @patch("elixis.parsing.parse_llm_json_array")
    @patch("elixis.llm.chat")
    @patch("elixis.llm.is_available", return_value=True)
    def test_truncates_long_input(self, mock_avail, mock_chat, mock_parse):
        mock_chat.return_value = {"content": "[]"}
        mock_parse.return_value = []
        long_text = "x" * 5000
        _llm_extract_entities(long_text)
        call_args = mock_chat.call_args[0][0][1]["content"]
        assert "truncated" in call_args

    @patch("elixis.parsing.parse_llm_json_array")
    @patch("elixis.llm.chat")
    @patch("elixis.llm.is_available", return_value=True)
    def test_skips_non_string_non_dict_items(self, mock_avail, mock_chat, mock_parse):
        mock_chat.return_value = {"content": "a valid json response array"}
        mock_parse.return_value = [123, None, True]
        result = _llm_extract_entities("test")
        assert result == []

    @patch("elixis.llm.chat")
    @patch("elixis.llm.is_available", return_value=True)
    def test_short_response_rejected(self, mock_avail, mock_chat):
        mock_chat.return_value = {"content": "ab"}
        result = _llm_extract_entities("test")
        assert result == []


# ---------------------------------------------------------------------------
# extract_entities (integration: LLM with heuristic fallback)
# ---------------------------------------------------------------------------

class TestExtractEntities:
    def test_empty_input(self):
        assert extract_entities("") == []

    def test_whitespace_input(self):
        assert extract_entities("   ") == []

    def test_empty_input_telemetry(self):
        tele = {}
        extract_entities("", telemetry=tele)
        assert tele["source"] == "empty_input"

    @patch("elixis.entities._llm_extract_entities", return_value=[])
    def test_falls_back_to_heuristic(self, mock_llm):
        result = extract_entities("Mozart\nBeethoven")
        assert len(result) >= 1
        names = {e["canonical"] for e in result}
        assert "Mozart" in names

    @patch("elixis.entities._llm_extract_entities", return_value=[])
    def test_heuristic_telemetry(self, mock_llm):
        tele = {}
        extract_entities("Mozart\nBeethoven", telemetry=tele)
        assert tele["source"] == "heuristic"
        assert "duration_ms" in tele
        assert tele["entity_count"] >= 1
        assert tele["llm_attempted"] is True

    @patch("elixis.entities._llm_extract_entities")
    def test_uses_llm_result_when_available(self, mock_llm):
        mock_llm.return_value = [
            {"canonical": "Mozart", "original": "Mozart", "type": "historical_figure",
             "source": "", "themes": [], "traits": [], "confidence": 0.95,
             "description": "", "related": []},
        ]
        result = extract_entities("I like Mozart")
        assert len(result) == 1
        assert result[0]["canonical"] == "Mozart"

    @patch("elixis.entities._llm_extract_entities")
    def test_augments_llm_with_salient_concepts(self, mock_llm):
        mock_llm.return_value = [
            {"canonical": "Athena", "original": "Athena", "type": "mythological",
             "source": "", "themes": ["wisdom"], "traits": [], "confidence": 0.95,
             "description": "", "related": []},
        ]
        result = extract_entities("Athena, kyanite blue, operator clarity, ritual tools")
        names = {e["canonical"] for e in result}
        assert "Athena" in names
        assert "kyanite blue" in names
        assert "operator clarity" in names
        assert "ritual tools" in names

    @patch("elixis.entities._llm_extract_entities")
    def test_llm_telemetry_propagated(self, mock_llm):
        def fake_llm(text, telemetry=None):
            if telemetry is not None:
                telemetry["source"] = "llm"
                telemetry["duration_ms"] = 50
                telemetry["entity_count"] = 1
            return [
                {"canonical": "Mozart", "original": "Mozart", "type": "historical_figure",
                 "source": "", "themes": [], "traits": [], "confidence": 0.95,
                 "description": "", "related": []},
            ]
        mock_llm.side_effect = fake_llm
        tele = {}
        extract_entities("I like Mozart", telemetry=tele)
        assert tele["source"] == "llm"
        assert tele["duration_ms"] == 50
