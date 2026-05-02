"""Quantified style analysis for the Glass Bead Game."""

import math
import re

ANALOGY_PHRASES = (
    "like", "as if", "similar to", "akin to", "reminiscent",
    "comparable", "analogous", "parallel",
)

CERTAINTY_WORDS = frozenset({
    "certainly", "definitely", "clearly", "obviously", "undeniably",
    "absolutely", "undoubtedly", "without question",
})

TRANSITION_PHRASES = (
    "however", "therefore", "moreover", "furthermore", "consequently",
    "nevertheless", "meanwhile", "conversely", "similarly",
    "in contrast", "as a result",
)

FIRST_PERSON_TOKENS = frozenset({
    "i", "i'm", "i've", "i'd", "i'll", "my", "me", "mine",
})

HEDGE_WORDS = frozenset({
    "perhaps", "maybe", "might", "could", "seems",
})

PLAYFUL_WORDS = frozenset({
    "ironically", "amusingly", "curiously", "playfully", "whimsically",
    "wryly", "tongue-in-cheek",
})

EMOTIONAL_WORDS = frozenset({
    "love", "hate", "passionate", "furious", "delighted", "heartbroken",
    "thrilled", "devastated", "ecstatic", "anguished", "joyful", "sorrowful",
})

PHILOSOPHICAL_TERMS = frozenset({
    "ontology", "epistemology", "phenomenology", "hermeneutic", "dialectic",
    "teleological", "existential", "metaphysical", "transcendent", "immanent",
    "a priori", "a posteriori", "noumenal", "heuristic", "paradigm",
})

TEMPORAL_MARKERS = frozenset({
    "then", "after", "before", "when", "while", "during", "once", "later",
    "earlier", "afterwards", "beforehand", "suddenly", "moment",
})

_WORD_RE = re.compile(r"[a-zA-Z']+")


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r'[.!?]+', text)
    return [s.strip() for s in parts if s.strip()]


def _count_phrases(text_lower: str, phrases: tuple) -> int:
    return sum(1 for p in phrases if p in text_lower)


def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def analyze_text(text: str) -> dict:
    sentences = _split_sentences(text)
    sentence_count = max(len(sentences), 1)
    full_lower = text.lower()
    words = _tokenize(text)
    word_count = max(len(words), 1)

    words_per_sentence = [len(_tokenize(s)) for s in sentences]
    avg_sentence_length = sum(words_per_sentence) / len(words_per_sentence) if words_per_sentence else 0.0

    question_count = sum(1 for c in text if c == '?')
    question_ratio = question_count / sentence_count

    analogy_density = _count_phrases(full_lower, ANALOGY_PHRASES) / sentence_count

    first_person_hits = sum(1 for w in words if w in FIRST_PERSON_TOKENS)
    first_person_ratio = first_person_hits / word_count

    certainty_hits = sum(1 for w in words if w in CERTAINTY_WORDS)
    certainty_hits += 1 if "without question" in full_lower else 0
    certainty_expression = certainty_hits / sentence_count

    transition_hits = _count_phrases(full_lower, TRANSITION_PHRASES)
    transition_frequency = transition_hits / sentence_count

    hedge_count = sum(1 for w in words if w in HEDGE_WORDS)
    playful_count = sum(1 for w in words if w in PLAYFUL_WORDS)
    exclamation_count = text.count('!')
    emotional_count = sum(1 for w in words if w in EMOTIONAL_WORDS)
    philosophical_count = sum(1 for w in words if w in PHILOSOPHICAL_TERMS)
    philosophical_count += sum(1 for p in PHILOSOPHICAL_TERMS if ' ' in p and p in full_lower)
    temporal_count = sum(1 for w in words if w in TEMPORAL_MARKERS)

    formal_score = (1.0 if avg_sentence_length > 15 else avg_sentence_length / 15.0) - question_ratio * 0.5
    formal_colloquial = _clamp(formal_score * 2.0 - 1.0)

    abstract_score = analogy_density * 0.5 + philosophical_count / max(sentence_count, 1)
    abstract_concrete = _clamp(abstract_score * 2.0 - 1.0)

    caution_score = hedge_count / max(sentence_count, 1)
    assert_score = certainty_expression
    cautious_assertive = _clamp(assert_score - caution_score)

    analytical_score = transition_frequency * 0.5 + philosophical_count / max(sentence_count, 1)
    narrative_score = temporal_count / max(sentence_count, 1)
    analytical_narrative = _clamp(analytical_score - narrative_score)

    serious_score = 0.5
    playful_score = playful_count / max(sentence_count, 1) + exclamation_count / max(sentence_count, 1) * 0.3
    serious_playful = _clamp(serious_score - playful_score)

    reserved_score = 1.0 - first_person_ratio * 5.0
    expressive_score = first_person_ratio * 3.0 + emotional_count / max(word_count, 1) * 10.0
    reserved_expressive = _clamp(reserved_score - expressive_score + 0.5)

    concise_score = 1.0 / (1.0 + avg_sentence_length / 10.0)
    elaborate_score = transition_frequency * 0.5 + avg_sentence_length / 30.0
    concise_elaborate = _clamp(elaborate_score - concise_score)

    spectra_keys = [
        "formal_colloquial", "abstract_concrete", "cautious_assertive",
        "analytical_narrative", "serious_playful", "reserved_expressive",
        "concise_elaborate",
    ]
    spectra_values = [
        formal_colloquial, abstract_concrete, cautious_assertive,
        analytical_narrative, serious_playful, reserved_expressive,
        concise_elaborate,
    ]
    spectra = dict(zip(spectra_keys, spectra_values))

    return {
        "dimensions": {
            "avg_sentence_length": avg_sentence_length,
            "question_ratio": question_ratio,
            "analogy_density": analogy_density,
            "first_person_ratio": first_person_ratio,
            "certainty_expression": certainty_expression,
            "transition_frequency": transition_frequency,
        },
        "spectra": spectra,
    }


def compare_styles(dna_a: dict, dna_b: dict) -> float:
    a = list(dna_a["spectra"].values())
    b = list(dna_b["spectra"].values())

    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))

    if mag_a > 0.0 and mag_b > 0.0:
        return _clamp(dot / (mag_a * mag_b), 0.0, 1.0)

    manhattan = sum(abs(x - y) for x, y in zip(a, b))
    max_dist = 2.0 * len(a)
    return _clamp(1.0 - manhattan / max_dist, 0.0, 1.0)


def detect_caricature(dna: dict) -> dict:
    extreme = []
    for name, value in dna["spectra"].items():
        if abs(value) > 0.9:
            extreme.append(name)

    if extreme:
        dim = extreme[0]
        val = dna["spectra"][dim]
        suggestion = f"Soften {dim} from {val:.1f} toward center"
    else:
        suggestion = ""

    return {
        "is_caricature": len(extreme) > 0,
        "extreme_dimensions": extreme,
        "suggestion": suggestion,
    }
