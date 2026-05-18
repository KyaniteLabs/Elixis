"""Declaration support: entity extraction engine.

Extracts named entities from raw brain dump text using LLM (primary)
with heuristic line-by-line parsing as fallback.
"""

import logging
import re
import time

logger = logging.getLogger("elixis.entities")


def _llm_extract_entities(text, telemetry=None):
    """Use the LLM to extract and classify entities from a brain dump.

    Args:
        text: raw brain dump text
        telemetry: optional dict to populate with extraction metrics

    Returns a list of entity dicts with name, type, source, themes, traits,
    or empty list if LLM is unavailable or fails.
    """
    from .llm import chat, is_available

    if not is_available():
        if telemetry is not None:
            telemetry["source"] = "unavailable"
            telemetry["error"] = "LLM not available"
        return []

    t0 = time.time()
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

    from .bead import VALID_THEMES
    themes_list = ", ".join(sorted(VALID_THEMES))

    user = f"""Extract all named references from this text. Fix any typos in names.

For each entity, return:
- name: canonical name (corrected if misspelled)
- type: one of: {types_list}
- source: origin work/media (or "")
- themes: 3-5 keywords from: {themes_list}
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
    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        logger.warning("LLM entity extraction failed (%dms): %s", duration_ms, exc)
        if telemetry is not None:
            telemetry["source"] = "error"
            telemetry["error"] = str(exc)
            telemetry["duration_ms"] = duration_ms
        return []

    duration_ms = int((time.time() - t0) * 1000)

    # Capture LLM metrics from the result dict
    llm_meta = {}
    if isinstance(result, dict):
        llm_meta = {
            "model": result.get("model", ""),
            "provider": result.get("provider", ""),
            "tokens_in": result.get("tokens_in", 0),
            "tokens_out": result.get("tokens_out", 0),
            "latency_ms": result.get("latency_ms", 0),
            "tokens_per_sec": result.get("tokens_per_sec", 0),
        }
        if result.get("error"):
            llm_meta["llm_error"] = result["error"]

    response = result["content"] if isinstance(result, dict) else result
    if not response or len(response) < 10:
        logger.warning("LLM response too short (%d chars) after %dms", len(response or ""), duration_ms)
        if telemetry is not None:
            telemetry.update({"source": "empty_response", "duration_ms": duration_ms, **llm_meta})
        return []

    from .parsing import parse_llm_json_array
    data = parse_llm_json_array(response)
    if data is None:
        logger.warning("LLM response failed JSON parse after %dms (response length: %d)", duration_ms, len(response))
        if telemetry is not None:
            telemetry.update({
                "source": "parse_failure", "duration_ms": duration_ms,
                "response_length": len(response), **llm_meta,
            })
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

    if telemetry is not None:
        telemetry.update({
            "source": "llm",
            "duration_ms": duration_ms,
            "parse_success": True,
            "entity_count": len(entities),
            "input_length": len(text),
            "input_truncated": len(raw) > _MAX_EXTRACT_CHARS,
            "items_in_raw_response": len(data),
            **llm_meta,
        })
    logger.info("LLM extracted %d entities in %dms (tokens: %d→%d)",
                len(entities), duration_ms,
                llm_meta.get("tokens_in", 0), llm_meta.get("tokens_out", 0))

    return entities


def _infer_type(name, source):
    """Infer entity type from name patterns and source.

    Detection order: mythological → historical → work → place → archetype → person → fallback
    """
    name_lower = name.lower()
    words = name.split()
    word_count = len(words)

    # --- Mythological / legendary fictional characters ---
    _MYTHO = {
        # Greek/Roman
        "zeus", "hera", "poseidon", "hades", "athena", "aphrodite", "apollo",
        "artemis", "ares", "hephaestus", "hermes", "dionysus", "hestia",
        "demeter", "persephone", "hercules", "achilles", "odysseus", "hector",
        "paris", "helena", "medusa", "minotaur", "cerberus", "prometheus",
        "icarus", "orpheus", "theseus", "perseus", "jason", "medea",
        "oedipus", "antigone", "electra", "cassandra", "penelope",
        # Norse
        "odin", "thor", "loki", "freya", "freyr", "baldr", "tyr", "heimdall",
        "frigg", "njord", "hel", "fenrir", "jormungandr", "sleipnir",
        "valkyrie", "ragnar", "bjorn", "lagerta", "ivar",
        # Egyptian
        "ra", "isis", "osiris", "horus", "anubis", "seth", "bastet", "thoth",
        "ptah", "sobek", "sekhmet", "hathor", "nephthys",
        # Hindu/Vedic
        "rama", "sita", "hanuman", "krishna", "arjuna", "shiva", "ganesh",
        "kali", "durga", "lakshmi", "saraswati", "brahma", "vishnu",
        # Japanese
        "amaterasu", "susano", "tsukuyomi", "izanagi", "izanami",
        # Celtic
        "morrigan", "dagda", "lugh", "brigid", "cernunnos",
        # Mesopotamian
        "gilgamesh", "enkidu", "ishtar", "marduk", "tiamat",
        # Famous fictional / literary
        "gandalf", "sauron", "voldemort", "yoda", "moriarty", "holmes",
        "dumbledore", "gollum", "aragorn", "legolas", "gimli", "frodo",
        "samwise", "saruman", "galadriel", "elrond", "bilbo",
        "darth vader", "luke skywalker", "han solo", "princess leia",
        "obi-wan", "emperor palpatine",
        "spock", "kirk", "captain picard",
        "batman", "superman", "wonder woman", "joker", "riddler",
        "dracula", "frankenstein",
    }

    for hint in _MYTHO:
        if hint in name_lower or name_lower == hint:
            return "mythological" if not source else "character"

    # --- Historical figure patterns ---
    _HISTORICAL_NAMES = {
        "mozart", "beethoven", "bach", "chopin", "handel", "haydn", "schubert",
        "brahms", "verdi", "wagner", "vivaldi", "tchaikovsky", "rachmaninoff",
        "napoleon", "cleopatra", "alexander", "caesar", "augustus", "nero",
        "confucius", "laozi", "buddha", "socrates", "plato", "aristotle",
        "leonardo", "michelangelo", "raphael", "donatello", "botticelli",
        "galileo", "newton", "einstein", "tesla", "darwin", "curie",
        "shakespeare", "dante", "cervantes", "goethe", "tolstoy", "dostoevsky",
        "marco polo", "magellan", "columbus", "ghengis", "genghis",
        "sun tzu", "miyamoto musashi",
        "freud", "jung", "nietzsche", "kant", "descartes", "hume",
        "edison", "faraday", "maxwell",
        "lincoln", "washington", "jefferson", "roosevelt", "churchill",
        "gandhi", "mandela", "mlk", "martin luther king",
    }
    for hint in _HISTORICAL_NAMES:
        if hint in name_lower:
            return "historical_figure"

    # --- Work detection ---
    _WORK_SUFFIXES = {
        "trilogy", "saga", "chronicle", "series", "cycle", "quartet",
        "symphony", "concerto", "sonata", "opera", "requiem", "mass",
        "novel", "poem", "play", "musical", "anthem", "ballad",
        "painting", "sculpture", "fresco", "mural",
        "theorem", "equation", "principle", "paradox",
        "meditation", "book", "code",
    }
    for suffix in _WORK_SUFFIXES:
        if name_lower.endswith(suffix) and word_count > 1:
            return "work"

    if name_lower.startswith("the ") and 2 <= word_count <= 5:
        # "The Matrix" (2), "The Godfather" (2), "The Divine Comedy" (3)
        # but NOT "The Great Warrior King of the North" (8)
        return "work"

    _KNOWN_WORKS = {
        "odyssey", "iliad", "aeneid", "divine comedy", "hamlet", "macbeth",
        "othello", "king lear", "tempest", "romeo and juliet",
        "don quixote", "moby dick", "war and peace", "crime and punishment",
        "1984", "brave new world", "catcher in the rye",
        "lord of the rings", "hobbit", "silmarillion", "narnia",
        "star wars", "star trek", "matrix", "inception", "interstellar",
        "citizen kane", "godfather", "pulp fiction", "fight club",
        "elements", "art of war", "book of five rings",
        "bhagavad gita", "tao te ching", "i ching",
    }
    for work in _KNOWN_WORKS:
        if name_lower == work or work in name_lower:
            return "work"

    # --- Place detection ---
    _PLACE_SUFFIXES = {
        "city", "country", "kingdom", "realm", "island", "mount", "mountain",
        "river", "forest", "valley", "planet", "world", "land", "region",
        "continent", "desert", "ocean", "sea", "lake", "bay", "gulf",
        "peninsula", "plateau", "canyon", "gorge", "coast", "shore",
        "empire", "republic", "province", "territory", "colony",
        "castle", "fortress", "palace", "temple", "cathedral", "tower",
        "dungeon", "labyrinth", "maze",
        "station", "port", "harbor", "haven",
    }
    for suffix in _PLACE_SUFFIXES:
        if name_lower.endswith(suffix) and not source:
            return "place"

    # --- Archetype detection ---
    _ARCHETYPES = {
        "hero", "villain", "mentor", "trickster", "sage", "warrior",
        "king", "queen", "wizard", "knight", "healer", "explorer",
        "outlaw", "lover", "caregiver", "creator", "jester", "magician",
        "orphan", "innocent", "ruler", "seeker",
        "shadow", "anima", "animus", "self", "persona",
        "herald", "guardian", "shapeshifter",
    }
    for arch in _ARCHETYPES:
        if name_lower == arch or (arch in name_lower and word_count <= 2):
            return "archetype"

    # --- Person detection: "First Last" pattern (2 capitalized words) ---
    # Only if source is present — a name mentioned in context of a work
    if (word_count == 2 and source
            and words[0][0].isupper() and words[1][0].isupper()):
        return "person"

    # --- Fallback ---
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

    description = ""
    if paren_match:
        name, source = paren_match.group(1).strip(), paren_match.group(2).strip()
    elif from_match:
        name, source = from_match.group(1).strip(), from_match.group(2).strip()
    elif dash_match:
        left = dash_match.group(1).strip()
        right = dash_match.group(2).strip()
        # Extract "by Author" from left side before checking description
        by_match = re.match(r'^(.+?)\s+by\s+(.+)$', left, re.IGNORECASE)
        if by_match:
            left = by_match.group(1).strip()
            source = by_match.group(2).strip()
        # Em/en-dash followed by a lowercase description, not a source
        if right and right[0].islower() and len(right) > 10:
            name = left
            description = right
            # source already set from by_match, or stays empty
        else:
            if not source:
                name, source = left, right
            else:
                name = left
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
        "description": description,
        "themes": [],
        "traits": [],
        "confidence": 0.7,
    }


def _heuristic_extract(text):
    """Fallback: line-by-line + period-split + capitalized phrase extraction."""
    entities = []
    seen = set()

    # Line-by-line first (also handles period-separated on single lines)
    lines = re.split(r'[\n\r]+', text)
    expanded = []
    for line in lines:
        # Always split on ". " period-space-capital
        parts = re.split(r'(?<=\.)\s+(?=[A-Z])', line)
        if len(parts) > 1:
            expanded.extend(parts)
        else:
            expanded.append(line)
    lines = expanded

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


def extract_entities(text, telemetry=None):
    """Main extraction pipeline. Uses LLM with heuristic fallback.

    Falls back to heuristic parsing if LLM returns empty.

    Args:
        text: raw brain dump text
        telemetry: optional dict to populate with extraction metrics
    """
    if not text or not text.strip():
        if telemetry is not None:
            telemetry["source"] = "empty_input"
        return []

    t0 = time.time()
    llm_tele = {}
    entities = _llm_extract_entities(text, telemetry=llm_tele)

    # Heuristic fallback: if LLM returns nothing, or returns a single bloated
    # entity that clearly swallowed the whole input (long name with many periods).
    needs_heuristic = not entities
    if len(entities) == 1 and len(entities[0].get("canonical", "")) > 60:
        needs_heuristic = True
        llm_tele["fallback_reason"] = "single_bloated_entity"

    if needs_heuristic:
        entities = _heuristic_extract(text)
        duration_ms = int((time.time() - t0) * 1000)
        if telemetry is not None:
            telemetry.update({
                "source": "heuristic",
                "duration_ms": duration_ms,
                "entity_count": len(entities),
                "input_length": len(text),
                "llm_attempted": True,
                "llm_source": llm_tele.get("source", "unknown"),
                "llm_duration_ms": llm_tele.get("duration_ms", 0),
            })
        logger.info("Fell back to heuristic extraction: %d entities in %dms (LLM source: %s)",
                    len(entities), duration_ms, llm_tele.get("source", "unknown"))
    else:
        duration_ms = int((time.time() - t0) * 1000)
        if telemetry is not None:
            telemetry.update(llm_tele)
            telemetry["total_duration_ms"] = duration_ms

    return entities
