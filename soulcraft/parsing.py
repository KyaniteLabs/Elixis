"""Shared LLM response parsing utilities."""

import json
import re

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)


def parse_llm_json_array(response: str):
    """Extract and parse a JSON array from an LLM response string.

    Strips markdown code fences, locates the outermost [ ], and parses.

    Returns:
        Parsed list on success, or None on failure.
    """
    if not response:
        return None

    json_str = response.strip()

    # Strip code fences
    if "```" in json_str:
        match = _CODE_FENCE_RE.search(json_str)
        if match:
            json_str = match.group(1).strip()

    # Find array bounds
    start = json_str.find("[")
    end = json_str.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        data = json.loads(json_str[start:end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(data, list):
        return None

    return data
