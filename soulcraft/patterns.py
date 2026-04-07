"""Stage 2: Pattern Graph Engine.

Builds a full probability graph of archetypal patterns.
Every pattern gets a probability score, not just top-1.
Finds bridge concepts, consensus, and emergent patterns.
"""

import math
from collections import defaultdict

# Archetypal pattern definitions with keyword associations
PATTERNS = [
    {
        "id": "transformation",
        "name": "Transformation & Rebirth",
        "keywords": ["transform", "change", "rebirth", "evolve", "grow", "become",
                      "shed", "metamorphosis", "phoenix", "death", "resurrection",
                      "rebuild", "reinvent", "convert", "transition", "transcend",
                      "awakening", "enlightenment", "ascend", "rise"],
        "color": "#ff6b00",
    },
    {
        "id": "power",
        "name": "Power & Ambition",
        "keywords": ["power", "control", "dominate", "rule", "conquer", "master",
                      "strength", "force", "will", "command", "authority", "king",
                      "queen", "throne", "empire", "legacy", "victory", "triumph",
                      "war", "battle", "fight", "win", "champion", "hero"],
        "color": "#a855f7",
    },
    {
        "id": "outsider",
        "name": "The Outsider",
        "keywords": ["outsider", "outcast", "exile", "alien", "stranger", "different",
                      "misfit", "rebel", "renegade", "rogue", "wanderer", "loner",
                      "solitary", "isolated", "marginal", "fringe", "edge",
                      "refuse", "reject", "abandon", "forsaken"],
        "color": "#ffc200",
    },
    {
        "id": "creation",
        "name": "Creation & Artistry",
        "keywords": ["create", "build", "make", "craft", "design", "art", "music",
                      "write", "paint", "draw", "compose", "sculpt", "forge",
                      "invent", "imagine", "dream", "vision", "inspire", "beauty",
                      "aesthetic", "expression", "original", "unique"],
        "color": "#4ecdc4",
    },
    {
        "id": "shadow",
        "name": "The Shadow Self",
        "keywords": ["shadow", "dark", "hidden", "secret", "taboo", "forbidden",
                      "repressed", "unconscious", "demon", "monster", "villain",
                      "corrupt", "sin", "guilt", "shame", "fear", "rage",
                      "destruct", "chaos", "void", "abyss", "underworld"],
        "color": "#f43f5e",
    },
    {
        "id": "wisdom",
        "name": "Wisdom & Knowledge",
        "keywords": ["wisdom", "knowledge", "truth", "learn", "teach", "understand",
                      "philosophy", "science", "reason", "logic", "insight",
                      "question", "answer", "seek", "search", "discover", "reveal",
                      "mystery", "enigma", "puzzle", "riddle", "study"],
        "color": "#38bdf8",
    },
    {
        "id": "connection",
        "name": "Connection & Belonging",
        "keywords": ["love", "family", "friend", "tribe", "community", "bond",
                      "loyalty", "trust", "together", "unity", "belong", "home",
                      "heart", "soul", "intimate", "relationship", "partner",
                      "companion", "brotherhood", "sisterhood"],
        "color": "#34d399",
    },
    {
        "id": "struggle",
        "name": "Struggle & Perseverance",
        "keywords": ["struggle", "hardship", "suffer", "endure", "survive",
                      "overcome", "resilience", "grit", "determination", "obstacle",
                      "challenge", "adversity", "pain", "sacrifice", "loss",
                      "grief", "mourning", "heal", "recover", "persevere"],
        "color": "#ef4444",
    },
    {
        "id": "freedom",
        "name": "Freedom & Rebellion",
        "keywords": ["freedom", "liberty", "free", "independent", "autonomy",
                      "rebel", "revolt", "revolution", "break", "escape",
                      "liberate", "anarchy", "defiance", "resist", "refuse",
                      "unbound", "wild", "untamed", "sovereign", "pirate"],
        "color": "#22d3ee",
    },
    {
        "id": "spiritual",
        "name": "Spiritual & Mystical",
        "keywords": ["spiritual", "divine", "sacred", "holy", "prayer", "meditation",
                      "enlighten", "nirvana", "cosmic", "universe", "transcendent",
                      "eternal", "infinite", "soul", "spirit", "faith", "ritual",
                      "ceremony", "oracle", "prophecy", "destiny", "fate"],
        "color": "#e879f9",
    },
    {
        "id": "trickster",
        "name": "The Trickster",
        "keywords": ["trickster", "joker", "fool", "clown", "prank", "mischief",
                      "cunning", "clever", "wit", "humor", "satire", "irony",
                      "paradox", "chaos", "disrupt", "subvert", "mock", "laugh",
                      "playful", "absurd", "nonsense", "riddle"],
        "color": "#6b7280",
    },
    {
        "id": "explorer",
        "name": "The Explorer",
        "keywords": ["explore", "discover", "journey", "travel", "adventure",
                      "frontier", "unknown", "territory", "map", "navigate",
                      "wander", "quest", "expedition", "voyage", "trek",
                      "uncharted", "horizon", "beyond", "new world"],
        "color": "#fbbf24",
    },
]

# Entity type affinities to patterns (entity types that tend to support certain patterns)
_TYPE_AFFINITIES = {
    "emotion": {"transformation": 0.3, "shadow": 0.3, "connection": 0.2, "struggle": 0.2},
    "skill": {"creation": 0.4, "wisdom": 0.3, "power": 0.1},
    "person": {"transformation": 0.2, "power": 0.2, "outsider": 0.2, "connection": 0.2},
    "work": {"creation": 0.3, "wisdom": 0.2, "spiritual": 0.1},
    "concept": {"wisdom": 0.3, "spiritual": 0.2, "transformation": 0.2},
    "place": {"explorer": 0.4, "spiritual": 0.2},
    "event": {"transformation": 0.3, "struggle": 0.3},
}


def _score_entity_pattern(entity, pattern, full_text=""):
    """Score how strongly an entity supports a pattern."""
    score = 0.0
    name_lower = entity["canonical"].lower()
    text_lower = full_text.lower()

    # Direct keyword match in entity name
    for kw in pattern["keywords"]:
        if kw in name_lower:
            score += 0.4

    # Keyword proximity in text
    for kw in pattern["keywords"][:5]:
        if kw in text_lower:
            # Find distance between entity mention and keyword
            e_idx = text_lower.find(name_lower)
            k_idx = text_lower.find(kw)
            if e_idx >= 0 and k_idx >= 0:
                dist = abs(e_idx - k_idx)
                if dist < 200:
                    score += 0.2 * (1 - dist / 200)

    # Type affinity
    etype = entity.get("type", "concept")
    affinity = _TYPE_AFFINITIES.get(etype, {})
    score += affinity.get(pattern["id"], 0.05)

    return min(score, 1.0)


def build_pattern_graph(entities, full_text=""):
    """Build the full pattern probability graph.

    Returns:
        dict with patterns, entity_scores, bridges, consensus, emergent_topic
    """
    if not entities:
        return {
            "patterns": [],
            "entity_scores": [],
            "bridges": [],
            "consensus_score": 0.0,
            "emergent_topic": "Unknown",
            "emergent_theme": "Not enough data",
            "emergent_color": "#666",
            "analysis_notes": ["No entities found to analyze."],
        }

    # Score every entity against every pattern
    raw_scores = defaultdict(lambda: defaultdict(float))
    for entity in entities:
        for pattern in PATTERNS:
            s = _score_entity_pattern(entity, pattern, full_text)
            if s > 0:
                raw_scores[entity["canonical"]][pattern["id"]] += s

    # Aggregate pattern scores
    pattern_totals = defaultdict(float)
    pattern_entity_counts = defaultdict(int)
    for entity_name, scores in raw_scores.items():
        for pid, score in scores.items():
            pattern_totals[pid] += score
            pattern_entity_counts[pid] += 1

    # Normalize to probabilities
    total_score = sum(pattern_totals.values()) or 1.0
    pattern_probs = {}
    for pid, total in pattern_totals.items():
        pattern_probs[pid] = total / total_score

    # Build pattern list sorted by probability
    result_patterns = []
    for p in PATTERNS:
        prob = pattern_probs.get(p["id"], 0.0)
        if prob > 0.01:
            result_patterns.append({
                "id": p["id"],
                "name": p["name"],
                "probability": round(prob, 4),
                "color": p["color"],
                "supporting_entities": pattern_entity_counts.get(p["id"], 0),
            })
    result_patterns.sort(key=lambda x: -x["probability"])

    # Entity scores for the matrix
    entity_scores = []
    for entity in entities:
        votes = {}
        for p in PATTERNS:
            s = raw_scores.get(entity["canonical"], {}).get(p["id"], 0.0)
            if s > 0:
                votes[p["id"]] = round(min(s, 1.0), 3)
        if votes:
            entity_scores.append({"name": entity["canonical"], "votes": votes})

    # Bridge detection: entities connecting unrelated patterns
    bridges = []
    for es in entity_scores:
        if len(es["votes"]) >= 2:
            sorted_v = sorted(es["votes"].items(), key=lambda x: -x[1])
            top_two = sorted_v[:2]
            p_a = next((p for p in result_patterns if p["id"] == top_two[0][0]), None)
            p_b = next((p for p in result_patterns if p["id"] == top_two[1][0]), None)
            if p_a and p_b:
                # Check if these patterns are not adjacent in ranking (bridge)
                idx_a = next((i for i, p in enumerate(result_patterns) if p["id"] == p_a["id"]), 0)
                idx_b = next((i for i, p in enumerate(result_patterns) if p["id"] == p_b["id"]), 0)
                if abs(idx_a - idx_b) > 1 and top_two[1][1] > 0.1:
                    bridges.append({
                        "entity": es["name"],
                        "pattern_a": p_a["name"],
                        "pattern_b": p_b["name"],
                        "color_a": p_a["color"],
                        "color_b": p_b["color"],
                        "score_a": top_two[0][1],
                        "score_b": top_two[1][1],
                    })

    # Consensus: how concentrated is the probability distribution
    if result_patterns:
        top_prob = result_patterns[0]["probability"]
        entropy = -sum(
            p["probability"] * math.log(p["probability"] + 1e-10)
            for p in result_patterns
            if p["probability"] > 0
        )
        max_entropy = math.log(len(result_patterns)) if len(result_patterns) > 1 else 1
        consensus = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0
    else:
        top_prob = 0
        consensus = 0.0

    # Emergent topic: highest consensus density (not just highest raw score)
    # Pattern with best ratio of supporting entities to probability spread
    emergent = result_patterns[0] if result_patterns else None
    if result_patterns and len(result_patterns) > 1:
        best_density = 0
        for p in result_patterns:
            density = p["supporting_entities"] * p["probability"]
            if density > best_density:
                best_density = density
                emergent = p

    # Analysis notes
    notes = []
    if result_patterns:
        notes.append(
            f"Dominant pattern: {result_patterns[0]['name']} "
            f"({result_patterns[0]['probability']*100:.0f}% probability)"
        )
    if bridges:
        notes.append(
            f"Bridge detected: '{bridges[0]['entity']}' connects "
            f"{bridges[0]['pattern_a']} and {bridges[0]['pattern_b']}"
        )
    if len(result_patterns) > 3:
        notes.append(
            f"Wide pattern distribution ({len(result_patterns)} patterns) "
            f"suggests a multifaceted identity"
        )
    if consensus > 0.6:
        notes.append("High consensus - identity has a clear core theme")
    elif consensus < 0.3:
        notes.append("Low consensus - identity draws from diverse, equally weighted influences")

    return {
        "patterns": result_patterns,
        "entity_scores": entity_scores[:10],
        "bridges": bridges[:5],
        "consensus_score": round(consensus, 3),
        "emergent_topic": emergent["name"] if emergent else "Unknown",
        "emergent_theme": _derive_theme(emergent, result_patterns) if emergent else "Insufficient data",
        "emergent_color": emergent["color"] if emergent else "#666",
        "analysis_notes": notes,
    }


def _derive_theme(emergent, all_patterns):
    """Derive a human-readable theme description."""
    name = emergent["name"]
    if len(all_patterns) <= 1:
        return f"A pure {name.lower()} archetype"
    secondary = all_patterns[1] if len(all_patterns) > 1 else None
    if secondary:
        return f"{name} blended with {secondary['name']} undertones"
    return name
