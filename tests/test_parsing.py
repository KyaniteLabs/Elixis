"""Tests for fugax.parsing — LLM JSON response parsing."""

from fugax.parsing import parse_llm_json_array, parse_llm_json_object


class TestParseLlmJsonArray:
    def test_valid_json_array(self):
        result = parse_llm_json_array('[{"name": "Test"}]')
        assert result == [{"name": "Test"}]

    def test_json_array_in_code_fence(self):
        result = parse_llm_json_array('```json\n[{"name": "Test"}]\n```')
        assert result == [{"name": "Test"}]

    def test_plain_array(self):
        result = parse_llm_json_array('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_empty_array(self):
        result = parse_llm_json_array('[]')
        assert result == []

    def test_none_input(self):
        assert parse_llm_json_array(None) is None

    def test_empty_string(self):
        assert parse_llm_json_array('') is None

    def test_no_array_brackets(self):
        assert parse_llm_json_array('{"key": "value"}') is None

    def test_invalid_json(self):
        assert parse_llm_json_array('[{invalid}]') is None

    def test_returns_non_list(self):
        assert parse_llm_json_array('"hello"') is None

    def test_json_with_surrounding_text(self):
        result = parse_llm_json_array('Here are the results:\n[{"a": 1}]\nDone.')
        assert result == [{"a": 1}]

    def test_code_fence_without_language(self):
        result = parse_llm_json_array('```\n[{"x": 1}]\n```')
        assert result == [{"x": 1}]


class TestParseLlmJsonObject:
    def test_valid_json_object(self):
        result = parse_llm_json_object('{"name": "Test", "value": 42}')
        assert result == {"name": "Test", "value": 42}

    def test_json_object_in_code_fence(self):
        result = parse_llm_json_object('```json\n{"name": "Test"}\n```')
        assert result == {"name": "Test"}

    def test_nested_object(self):
        result = parse_llm_json_object('{"outer": {"inner": 1}}')
        assert result == {"outer": {"inner": 1}}

    def test_none_input(self):
        assert parse_llm_json_object(None) is None

    def test_empty_string(self):
        assert parse_llm_json_object('') is None

    def test_no_object_braces(self):
        assert parse_llm_json_object('[1, 2, 3]') is None

    def test_invalid_json(self):
        assert parse_llm_json_object('{invalid}') is None

    def test_returns_non_dict(self):
        assert parse_llm_json_object('"hello"') is None

    def test_json_with_surrounding_text(self):
        result = parse_llm_json_object('Result: {"a": 1} End.')
        assert result == {"a": 1}

    def test_empty_object(self):
        result = parse_llm_json_object('{}')
        assert result == {}
