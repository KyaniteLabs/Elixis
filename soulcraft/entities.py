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

    _MAX_EXTRACT_CHARS = 4000
    raw = text.strip()
    truncated = raw[:_MAX_EXTRACT_CHARS]
    suffix = "\n... [text truncated for analysis]" if len(raw) > _MAX_EXTRACT_CHARS else ""

    system = (
        "You are a cultural reference analyzer. Extract entities from text. "
        "Respond with ONLY a JSON array. No markdown, no explanation."
    )

    from .bead import VALID_TYPES
    types_list = ", ".join(sorted(VALID_TYPES))

    user = f"""Extract all named references from this text. Fix any typos in names.

For each entity, return:
- name: canonical name (corrected if misspelled)
- type: one of: {types_list}
- source: origin work/media (or "")
- themes: 3-5 keywords from: transformation, power, outsider, creation, shadow, wisdom, connection, struggle, freedom, spiritual, trickster, explorer
- traits: 2-4 specific personality phrases (e.g. "paranoid ambition", "cold calculation")
- related: 2-3 similar characters/figures

Text: {truncated}{suffix}

Output JSON array only:
[{{"name": "...", "type": "...", "source": "...", "themes": [...], "traits": [...], "related": [...]}}]"""

    try:
        result = chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            model=None,
        )
    except Exception:
        return []

    response = result["content"] if isinstance(result, dict) else result
    if not response or len(response) < 10:
        return []

    from .parsing import parse_llm_json_array
    data = parse_llm_json_array(response)
    if data is None:
        return []

    entities = []
    seen = set()
    for item in data:
        # Handle both string items and dict items
        if isinstance(item, str):
            name = item.strip()
            item = {}
        elif isinstance(item, dict):
            name = item.get("name", "").strip()
        else:
            continue
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
            "related": [r.strip() for r in item.get("related", []) if isinstance(r, str) and r.strip()],
            "confidence": 0.95,
        })

    return entities


def _infer_type(name, source):
    """Infer entity type from name patterns and source."""
    name_lower = name.lower()
    mythological_hints = ["zeus", "odin", "thor", "aphrodite", "apollo", "athena",
                          "hercules", "achilles", "beowulf", "gandalf", "sauron",
                          "voldemort", "yoda", "moriarty", "holmes"]
    place_hints = ["city", "country", "kingdom", "realm", "island", "mount",
                   "river", "forest", "valley", "planet", "world", "land"]
    archetype_hints = ["hero", "villain", "mentor", "trickster", "sage",
                       "warrior", "king", "queen", "wizard", "knight"]

    for hint in mythological_hints:
        if hint in name_lower:
            return "mythological" if not source else "character"
    for hint in place_hints:
        if hint in name_lower and not source:
            return "place"
    for hint in archetype_hints:
        if name_lower == hint or (hint in name_lower and len(name.split()) <= 2):
            return "archetype"
    return "character" if source else "concept"


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
        "type": _infer_type(name, source),
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
            "There", "Here", "What", "Which", "Who", "How", "Why",
            "Where", "Each", "Every", "Some", "Any", "No", "All",
            "Both", "Either", "Neither", "Such", "Than", "Too",
            "Very", "Just", "Only", "Also", "Even", "Still",
            "Already", "Yet", "Now", "Then", "Today", "Tomorrow",
            "Yesterday", "Always", "Never", "Often", "Sometimes",
            "Before", "After", "Since", "Until", "During",
            "Between", "Among", "Through", "About", "Above",
            "Below", "Under", "Over", "Into", "From", "With",
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
    """Main extraction pipeline. Uses LLM with heuristic fallback.

    Falls back to heuristic parsing if LLM returns empty.
    """
    if not text or not text.strip():
        return []

    entities = _llm_extract_entities(text)

    # Fallback to heuristic if LLM returns empty
    if not entities:
        entities = _heuristic_extract(text)

    return entities
