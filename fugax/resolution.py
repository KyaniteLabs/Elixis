"""Entity deduplication and canonical name resolution for the Glass Bead Game."""



def normalize_name(name: str) -> str:
    stripped = name.strip()
    while stripped and stripped[0] in "\"'-":
        stripped = stripped[1:]
    while stripped and stripped[-1] in "\"'-":
        stripped = stripped[:-1]
    parts = stripped.split()
    return " ".join(parts)


def name_similarity(a: str, b: str) -> float:
    na = normalize_name(a).lower()
    nb = normalize_name(b).lower()

    if na == nb:
        return 1.0

    if not na or not nb:
        return 0.0

    if na in nb or nb in na:
        return 0.85

    prefix_len = 0
    for ca, cb in zip(na, nb):
        if ca == cb:
            prefix_len += 1
        else:
            break
    prefix_ratio = prefix_len / max(len(na), len(nb))

    distance = _levenshtein(na, nb)
    lev_ratio = 1.0 - (distance / max(len(na), len(nb)))

    return max(prefix_ratio, lev_ratio)


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(
                curr[j] + 1,
                prev[j + 1] + 1,
                prev[j] + cost,
            ))
        prev = curr
    return prev[-1]


def deduplicate_beads(beads: list) -> list:
    if not beads:
        return []

    result = []
    claimed = [False] * len(beads)

    for i, bead in enumerate(beads):
        if claimed[i]:
            continue
        claimed[i] = True
        winner = bead

        for j in range(i + 1, len(beads)):
            if claimed[j]:
                continue
            candidate = beads[j]
            if name_similarity(winner.canonical, candidate.canonical) >= 0.85:
                claimed[j] = True
                if candidate.confidence > winner.confidence:
                    winner, loser = candidate, winner
                else:
                    loser = candidate

                winner.themes = list(set(winner.themes) | set(loser.themes))
                winner.traits = list(set(winner.traits) | set(loser.traits))
                winner.related = list(set(winner.related) | set(loser.related))

                merged_enrichment = dict(loser.enrichment)
                merged_enrichment.update(winner.enrichment)
                winner.enrichment = merged_enrichment

                winner.sentiment = max(winner.sentiment, loser.sentiment)
                winner.intensity = max(winner.intensity, loser.intensity)

        result.append(winner)

    return result


def resolve_entities(raw_names: list[str]) -> list[dict]:
    if not raw_names:
        return []

    normalized = [(name, normalize_name(name).lower()) for name in raw_names]
    groups: list[list[int]] = []
    assigned = [False] * len(raw_names)

    for i in range(len(raw_names)):
        if assigned[i]:
            continue
        group = [i]
        assigned[i] = True
        for j in range(i + 1, len(raw_names)):
            if assigned[j]:
                continue
            if name_similarity(normalized[i][1], normalized[j][1]) >= 0.8:
                group.append(j)
                assigned[j] = True
        groups.append(group)

    results = []
    for group in groups:
        originals = [raw_names[idx] for idx in group]
        best = max(originals, key=lambda n: len(normalize_name(n)))
        results.append({
            "original": originals[0],
            "canonical": best,
            "aliases": [n for n in originals if n != best],
        })

    return results
