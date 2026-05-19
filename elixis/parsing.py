"""Shared LLM response parsing utilities."""

import json
import re

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def _strip_code_fence(response: str) -> str:
    json_str = response.strip()
    if "```" in json_str:
        match = _CODE_FENCE_RE.search(json_str)
        if match:
            json_str = match.group(1).strip()
    return json_str


def _loads_lenient(json_str: str):
    """Parse JSON, allowing the most common model-only trailing comma drift."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        cleaned = _TRAILING_COMMA_RE.sub(r"\1", json_str)
        if cleaned == json_str:
            raise
        return json.loads(cleaned)


def _first_list_value(value):
    """Return the first useful list from a wrapper object, if present."""
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        return None

    preferred_keys = (
        "results",
        "entities",
        "items",
        "data",
        "classifications",
        "patterns",
        "scores",
    )
    for key in preferred_keys:
        if isinstance(value.get(key), list):
            return value[key]

    for child in value.values():
        if isinstance(child, list):
            return child
    return None


def parse_llm_json_array(response: str):
    """Extract and parse a JSON array from an LLM response string.

    Strips markdown code fences, locates the outermost [ ], and parses.

    Returns:
        Parsed list on success, or None on failure.
    """
    if not response:
        return None

    json_str = _strip_code_fence(response)

    # Find array bounds
    start = json_str.find("[")
    end = json_str.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            data = _loads_lenient(json_str[start:end + 1])
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            return data

    # Some models wrap the requested array in a top-level object despite the
    # prompt. Accept that shape so classification does not drop to fallback.
    obj_start = json_str.find("{")
    obj_end = json_str.rfind("}")
    if obj_start == -1 or obj_end == -1 or obj_end <= obj_start:
        return None

    try:
        wrapped = _loads_lenient(json_str[obj_start:obj_end + 1])
    except json.JSONDecodeError:
        return None
    return _first_list_value(wrapped)


def parse_llm_json_object(response: str):
    """Extract and parse a JSON object from an LLM response string.

    Strips markdown code fences, locates the outermost { }, and parses.

    Returns:
        Parsed dict on success, or None on failure.
    """
    if not response:
        return None

    json_str = _strip_code_fence(response)

    # Find object bounds
    start = json_str.find("{")
    end = json_str.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        data = _loads_lenient(json_str[start:end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    return data
