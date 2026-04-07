"""Stage 1: Entity Extraction Engine.

Extracts named entities from raw brain dump text using LLM (primary)
with heuristic line-by-line parsing as fallback.
"""

import json
import re


def _llm_extract_entities(text):
    """Use the LLM to extract and classify entities from a brain dump.

    Returns a list of entity dicts with name, type, source, themes, traits,
    or empty list if LLM is unavailable or fails.
    """
    from .llm import chat, is_available

    if not is_available():
        return []

    system = (
        "You are a cultural reference analyzer. You receive a brain dump of references "
        "(characters, films, books, figures, etc.) and extract each one as structured data. "
        "You respond ONLY with a JSON array. No explanation, no markdown, no code fences."
    )

    user = f"""Analyze these references and extract EVERY SINGLE ONE as a separate entry. Do not stop until you have extracted all of them.

For each reference provide:
- name: the character or entity name
- type: one of character, person, work, concept, historical_figure
- source: what work/media it comes from (empty string if not applicable)
- themes: 3-5 thematic keywords (e.g. ambition, power, rebellion)
- traits: 2-4 personality trait adjectives

References:
{text.strip()}

IMPORTANT: You MUST extract ALL references listed above. Output ONLY a JSON array, no other text:
[{{"name": "...", "type": "...", "source": "...", "themes": [...], "traits": [...]}}]"""

    try:
        response = chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            model=None,
        )
    except Exception:
        return []

    if not response or len(response) < 10:
        return []

    # Extract JSON from the response (may be wrapped in code fences)
    json_str = response.strip()
    if "```" in json_str:
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", json_str, re.DOTALL)
        if match:
            json_str = match.group(1).strip()

    # Find the array bounds
    start = json_str.find("[")
    end = json_str.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []

    try:
        data = json.loads(json_str[start:end + 1])
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    entities = []
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "").strip()
        if not name or len(name) < 2:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        themes = item.get("themes", [])
        if isinstance(themes, str):
            themes = [t.strip() for t in themes.split(",")]
        traits = item.get("traits", [])
        if isinstance(traits, str):
            traits = [t.strip() for t in traits.split(",")]

        entities.append({
            "original": name,
            "canonical": name,
            "source": item.get("source", ""),
            "type": item.get("type", "concept"),
            "description": item.get("description", ""),
            "themes": [t.lower().strip() for t in themes if t.strip()],
            "traits": [t.lower().strip() for t in traits if t.strip()],
            "confidence": 0.95,
        })

    return entities


def _parse_line_entity(line):
    """Parse a single brain-dump line into a basic entity dict."""
    line = line.strip()
    if not line or len(line) < 2:
        return None

    # Strip leading markers (-, *, bullet, numbers)
    line = re.sub(r'^[\s*\-•]*(?:\d+[.\):]\s*)?', '', line).strip()
    if not line:
        return None

    name = line
    source = ""

    paren_match = re.match(r'^(.+?)\s*\(([^)]+)\)\s*$', line)
    dash_match = re.match(r'^(.+?)\s*[-\u2013\u2014]\s*(.+)$', line)
    comma_match = re.match(r'^(.+?)\s*,\s*(.+)$', line)
    from_match = re.match(r'^(.+?)\s+(?:from|via|in)\s+(.+)$', line, re.IGNORECASE)
    slash_match = re.match(r'^(.+?)\s*/\s*(.+)$', line)

    if paren_match:
        name, source = paren_match.group(1).strip(), paren_match.group(2).strip()
    elif from_match:
        name, source = from_match.group(1).strip(), from_match.group(2).strip()
    elif dash_match:
        name, source = dash_match.group(1).strip(), dash_match.group(2).strip()
    elif slash_match:
        name, source = slash_match.group(1).strip(), slash_match.group(2).strip()
    elif comma_match and len(comma_match.group(1).strip().split()) <= 4:
        name, source = comma_match.group(1).strip(), comma_match.group(2).strip()

    name = re.sub(r'^["\'](.+)["\']$', r'\1', name).strip()
    if not name or len(name) < 2:
        return None

    return {
        "original": line,
        "canonical": name,
        "source": source,
        "type": "character" if source else "concept",
        "description": "",
        "themes": [],
        "traits": [],
        "confidence": 0.7,
    }


def _heuristic_extract(text):
    """Fallback: line-by-line + capitalized phrase extraction."""
    entities = []
    seen = set()

    # Line-by-line first
    lines = re.split(r'[\n\r]+', text)
    for line in lines:
        entity = _parse_line_entity(line)
        if entity:
            key = entity["canonical"].lower()
            if key not in seen and len(key) > 2:
                seen.add(key)
                entities.append(entity)

    # If no line entities found, try capitalized phrases
    if not entities:
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        matches = re.findall(pattern, text)
        starters = {
            "The", "This", "That", "These", "Those", "It", "He", "She",
            "His", "Her", "They", "Their", "We", "Our", "My", "Your",
            "And", "But", "Or", "So", "If", "When", "While", "Not",
        }
        for m in matches:
            key = m.lower()
            if m not in starters and len(m) > 2 and key not in seen:
                seen.add(key)
                entities.append({
                    "original": m,
                    "canonical": m.strip(),
                    "source": "",
                    "type": "concept",
                    "description": "",
                    "themes": [],
                    "traits": [],
                    "confidence": 0.6,
                })

    return entities


def extract_entities(text):
    """Main extraction pipeline. Requires LLM.

    Raises RuntimeError if LLM is unavailable.
    """
    if not text or not text.strip():
        return []

    entities = _llm_extract_entities(text)

    if not entities:
        raise RuntimeError(
            "LLM entity extraction failed. Ensure Ollama is running with a model loaded. "
            "Run: ollama serve && ollama pull gemma4"
        )

    return entities
