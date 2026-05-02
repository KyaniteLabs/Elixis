"""Negation-aware sentiment and intensity detection for the Glass Bead Game."""

import re
from collections import Counter

POSITIVE_WORDS = frozenset({
    "love", "like", "admire", "respect", "adore", "fascinated", "inspired",
    "drawn", "connected", "resonate", "appreciate", "enjoy", "favorite",
    "brilliant", "amazing", "great", "beautiful", "powerful", "incredible",
    "excellent",
})

NEGATIVE_WORDS = frozenset({
    "hate", "despise", "fear", "dread", "dislike", "loathe", "repelled",
    "disgusted", "annoyed", "frustrated", "angry", "disturbed", "terrified",
    "appalled", "repulsed", "sickened",
})

NEGATION_WORDS = frozenset({
    "not", "don't", "doesn't", "didn't", "won't", "can't", "never",
    "barely", "hardly", "rarely", "seldom", "no", "neither", "nor",
})

INTENSIFIERS = frozenset({
    "really", "very", "extremely", "absolutely", "deeply", "profoundly",
    "incredibly", "utterly", "totally", "completely", "especially",
    "particularly",
})

PROFUNDITY_MARKERS = frozenset({
    "always", "never", "everything", "nothing", "completely", "absolutely",
    "fundamentally", "essentially",
})

_WORD_RE = re.compile(r"[a-zA-Z']+")


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def detect_sentiment(text: str) -> float:
    words = _tokenize(text)
    if not words:
        return 0.0

    values: list[float] = []
    for i, word in enumerate(words):
        polarity = 0.0
        if word in POSITIVE_WORDS:
            polarity = 1.0
        elif word in NEGATIVE_WORDS:
            polarity = -1.0
        else:
            continue

        negated = False
        intensified = False
        start = max(0, i - 3)
        for j in range(start, i):
            if words[j] in NEGATION_WORDS:
                negated = True
        int_start = max(0, i - 2)
        for j in range(int_start, i):
            if words[j] in INTENSIFIERS:
                intensified = True

        if negated:
            polarity = -polarity
        if intensified:
            polarity *= 1.5

        values.append(polarity)

    if not values:
        return 0.0

    result = sum(values) / len(values)
    return max(-1.0, min(1.0, result))


def detect_intensity(text: str) -> float:
    intensity = 0.3

    exclamations = text.count("!")
    intensity += min(exclamations, 3) * 0.1

    caps_words = re.findall(r"\b[A-Z]{3,}\b", text)
    intensity += min(len(caps_words), 4) * 0.05

    words = _tokenize(text)
    intensifier_count = sum(1 for w in words if w in INTENSIFIERS)
    intensity += min(intensifier_count, 3) * 0.1

    counts = Counter(words)
    repeated = sum(1 for c in counts.values() if c >= 2)
    if repeated:
        intensity += 0.1

    profundity_count = sum(1 for w in words if w in PROFUNDITY_MARKERS)
    intensity += min(profundity_count, 4) * 0.05

    return max(0.0, min(1.0, intensity))


def annotate_bead(text: str) -> dict:
    return {
        "sentiment": detect_sentiment(text),
        "intensity": detect_intensity(text),
    }
