"""Stage 1: Entity Extraction Engine.

Extracts named entities from raw brain dump text.
Entity types: person, place, concept, work, event, emotion, skill
"""

import re
from collections import Counter

# Known cultural references for classification
_KNOWN_PEOPLE = {
    "gandhi", "einstein", "tesla", "socrates", "plato", "aristotle", "nietzsche",
    "camus", "sartre", "jung", "freud", "marcus aurelius", "sun tzu", "machiavelli",
    "buddha", "jesus", "muhammad", "moses", "david", "goliath", "odysseus",
    "hamlet", "macbeth", "romeo", "juliet", "holmes", "watson", "gollum",
    "frodo", "gandalf", "vader", "yoda", "morpheus", "neo", "trinity",
    "miyagi", "rocky", "terminator", "batman", "superman", "spiderman",
    "wolverine", "magneto", "professor x", "stark", "iron man", "thor",
    "loki", "hulk", "black panther", "wonder woman", "harley quinn",
    "joker", "pennywise", "freddy", "jason", "michael myers",
    "job", "abraham", "solomon", "david", "noah", "adam", "eve",
    "sappho", "medusa", "athena", "zeus", "poseidon", "hades", "apollo",
    "artemis", "aphrodite", "hermes", "ares", "dionysus", "hephaestus",
    "persephone", "demeter", "hera", "hestia",
}

_KNOWN_WORKS = {
    "the matrix", "star wars", "lord of the rings", "harry potter",
    "game of thrones", "breaking bad", "the wire", "stranger things",
    "dark knight", "inception", "interstellar", "blade runner",
    "ghost in the shell", "akira", "evangelion", "cowboy bebop",
    "attack on titan", "one piece", "naruto", "dragon ball",
    "fullmetal alchemist", "death note", "hunter x hunter",
    "jojo", "mob psycho", "one punch man",
    "the republic", "the prince", "meditations", "thus spoke zarathustra",
    "the stranger", "being and nothingness", "beyond good and evil",
    "critique of pure reason", "phenomenology of spirit",
    "the art of war", "the book of five rings", "hagakure",
    "tao te ching", "i ching", "bhagavad gita", "upanishads",
    "dune", "foundation", "neuromancer", "snow crash",
    "1984", "brave new world", "fahrenheit 451",
    "catcher in the rye", "the great gatsby", "moby dick",
    "crime and punishment", "the brothers karamazov", "war and peace",
}

_EMOTION_WORDS = {
    "love", "hate", "fear", "anger", "joy", "sadness", "grief", "hope",
    "despair", "rage", "fury", "bliss", "ecstasy", "agony", "torment",
    "passion", "desire", "longing", "nostalgia", "melancholy", "anguish",
    "terror", "horror", "dread", "anxiety", "serenity", "peace", "calm",
    "euphoria", "elation", "sorrow", "misery", "suffering", "pain",
    "pleasure", "excitement", "thrill", "awe", "wonder", "curiosity",
    "boredom", "apathy", "indifference", "contempt", "disgust",
    "shame", "guilt", "pride", "arrogance", "humility", "gratitude",
    "forgiveness", "resentment", "bitterness", "jealousy", "envy",
    "admiration", "respect", "loyalty", "betrayal", "trust",
    "determination", "resilience", "courage", "bravery", "cowardice",
}

_SKILL_PATTERNS = [
    r'\b(programming|coding|development|engineering)\b',
    r'\b(writing|poetry|storytelling|narrative)\b',
    r'\b(design|art|illustration|painting|drawing)\b',
    r'\b(music|guitar|piano|drums|singing|composition)\b',
    r'\b(cooking|baking|chef|recipe)\b',
    r'\b(martial arts|karate|jiu.?jitsu|boxing|mma)\b',
    r'\b(meditation|mindfulness|yoga|breathwork)\b',
    r'\b(mathematics|physics|chemistry|biology|science)\b',
    r'\b(philosophy|ethics|logic|reasoning)\b',
    r'\b(strategy|tactics|chess|go)\b',
    r'\b(teaching|mentoring|coaching)\b',
    r'\b(leadership|management|negotiation)\b',
    r'\b(analysis|research|investigation)\b',
    r'\b(healing|therapy|medicine|nursing)\b',
    r'\b(fighting|combat|warfare|survival)\b',
]


def _extract_capitalized_phrases(text):
    """Extract capitalized phrases that are likely proper nouns."""
    # Match sequences of capitalized words
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    matches = re.findall(pattern, text)
    # Filter out common sentence starters
    starters = {
        "The", "This", "That", "These", "Those", "It", "Its", "He", "She",
        "His", "Her", "They", "Their", "We", "Our", "My", "Your", "I", "Me",
        "And", "But", "Or", "So", "If", "When", "While", "After", "Before",
        "In", "On", "At", "To", "For", "With", "From", "By", "About",
        "Not", "No", "Yes", "All", "Some", "Most", "Many", "Few",
        "Just", "Only", "Even", "Still", "Also", "Very", "Really",
        "There", "Here", "Where", "What", "How", "Why", "Who", "Which",
        "Every", "Each", "Both", "Either", "Neither", "None",
        "First", "Second", "Third", "Last", "Next", "Then", "Now",
    }
    return [m for m in matches if m not in starters and len(m) > 2]


def _extract_quoted_entities(text):
    """Extract entities from quotes, italics, or emphasis."""
    patterns = [
        r'"([^"]+)"',
        r"'([^']+)'",
        r'\*\*([^*]+)\*\*',
        r'\*([^*]+)\*',
        r'_([^_]+)_',
    ]
    results = []
    for p in patterns:
        results.extend(re.findall(p, text))
    return [r for r in results if len(r) > 2 and len(r) < 80]


def _extract_skill_entities(text):
    """Extract skill-related entities."""
    found = []
    text_lower = text.lower()
    for pattern in _SKILL_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            found.append(match.group(1))
    return found


def _extract_emotion_entities(text):
    """Extract emotion-related entities."""
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    found = [w for w in words if w in _EMOTION_WORDS]
    return list(dict.fromkeys(found))[:15]


def _classify_entity(name, context=""):
    """Classify an entity into a type."""
    name_lower = name.lower()
    context_lower = context.lower()

    if name_lower in _KNOWN_PEOPLE:
        return "person"
    if name_lower in _KNOWN_WORKS:
        return "work"

    # Check context clues
    person_clues = ["he ", "she ", "his ", "her ", "him ", "told", "said", "met", "friend", "mentor", "teacher", "father", "mother", "brother", "sister", "uncle", "aunt"]
    work_clues = ["read", "watched", "played", "listened", "book", "movie", "film", "show", "series", "album", "song", "game", "novel", "story", "anime", "manga"]
    place_clues = ["visited", "lived in", "from", "city", "country", "mountain", "river", "ocean", "forest", "island", "country"]

    for clue in person_clues:
        if clue in context_lower and name_lower in context_lower:
            return "person"
    for clue in work_clues:
        if clue in context_lower and name_lower in context_lower:
            return "work"
    for clue in place_clues:
        if clue in context_lower and name_lower in context_lower:
            return "place"

    # Heuristic: short capitalized words are likely people
    if len(name.split()) == 1 and name[0].isupper():
        return "person"
    # Longer phrases tend to be works or concepts
    if len(name.split()) >= 3:
        return "work"

    return "concept"


def extract_entities(text):
    """Main extraction pipeline. Returns list of entity dicts."""
    if not text or not text.strip():
        return []

    entities = []
    seen = set()

    # 1. Quoted entities (high confidence)
    for name in _extract_quoted_entities(text):
        key = name.lower()
        if key not in seen and len(key) > 2:
            seen.add(key)
            etype = _classify_entity(name, text)
            entities.append({
                "original": name,
                "canonical": name.strip(),
                "type": etype,
                "confidence": 0.9,
            })

    # 2. Capitalized phrases
    for name in _extract_capitalized_phrases(text):
        key = name.lower()
        if key not in seen and len(key) > 2:
            seen.add(key)
            etype = _classify_entity(name, text)
            entities.append({
                "original": name,
                "canonical": name.strip(),
                "type": etype,
                "confidence": 0.7,
            })

    # 3. Known works/characters mentioned in lowercase
    text_lower = text.lower()
    for work in _KNOWN_WORKS:
        if work in text_lower and work not in seen:
            seen.add(work)
            entities.append({
                "original": work.title(),
                "canonical": work.title(),
                "type": "work",
                "confidence": 0.85,
            })
    for person in _KNOWN_PEOPLE:
        if person in text_lower and person not in seen:
            seen.add(person)
            entities.append({
                "original": person.title(),
                "canonical": person.title(),
                "type": "person",
                "confidence": 0.85,
            })

    # 4. Emotions
    for emo in _extract_emotion_entities(text):
        key = f"emotion:{emo}"
        if key not in seen:
            seen.add(key)
            entities.append({
                "original": emo,
                "canonical": emo.capitalize(),
                "type": "emotion",
                "confidence": 0.8,
            })

    # 5. Skills
    for skill in _extract_skill_entities(text):
        key = f"skill:{skill}"
        if key not in seen:
            seen.add(key)
            entities.append({
                "original": skill,
                "canonical": skill.capitalize(),
                "type": "skill",
                "confidence": 0.75,
            })

    return entities
