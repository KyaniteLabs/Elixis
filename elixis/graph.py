"""Entity relationship graph for the pattern synthesis.

Builds a directed, weighted graph of entity relationships using
theme overlap, type affinity, and curated knowledge base data.
"""

from collections import defaultdict
from .knowledge import character_by_name
from .thread import Thread


def build_relationship_graph(beads):
    """Build a relationship graph between beads.

    Returns a dict with:
      - nodes: list of bead summaries
      - edges: list of Thread objects
      - clusters: groups of beads by dominant theme
      - centralities: dict of bead_name -> connection count
    """
    if not beads:
        return {"nodes": [], "edges": [], "clusters": {}, "centralities": {}}

    nodes = []
    for b in beads:
        nodes.append({
            "name": b.canonical,
            "type": b.type,
            "themes": b.themes,
            "domains": b.domains,
            "sentiment": b.sentiment,
            "intensity": b.intensity,
        })

    edges = []
    seen = set()

    for i, ba in enumerate(beads):
        for j, bb in enumerate(beads):
            if i >= j:
                continue
            key = (ba.canonical, bb.canonical)
            if key in seen:
                continue

            rel, strength = _compute_relationship(ba, bb)
            if rel and strength > 0.1:
                seen.add(key)
                edges.append(Thread(
                    bead_a=ba.canonical,
                    bead_b=bb.canonical,
                    relationship=rel,
                    strength=round(strength, 3),
                    isomorphic=_is_cross_domain(ba, bb),
                    domains_bridged=(
                        ba.domains[0] if ba.domains else "",
                        bb.domains[0] if bb.domains else "",
                    ),
                    evidence=_evidence_for(ba, bb, rel),
                ))

    clusters = _cluster_by_theme(beads)
    centralities = _compute_centralities(beads, edges)

    return {
        "nodes": nodes,
        "edges": [e.to_dict() for e in edges],
        "clusters": clusters,
        "centralities": centralities,
    }


def _compute_relationship(ba, bb):
    """Determine relationship type and strength between two beads."""
    shared_themes = set(ba.themes) & set(bb.themes)
    theme_strength = len(shared_themes) / max(len(ba.themes) or 1, len(bb.themes) or 1)

    shared_traits = set(t.lower() for t in ba.traits) & set(t.lower() for t in bb.traits)
    trait_strength = len(shared_traits) / max(len(ba.traits) or 1, len(bb.traits) or 1) * 0.3

    sentiment_diff = abs(ba.sentiment - bb.sentiment)
    sentiment_bonus = 0.1 if sentiment_diff > 0.5 else 0.0

    kb_a = character_by_name(ba.canonical)
    kb_b = character_by_name(bb.canonical)
    if kb_a and kb_b:
        shared_archetypes = set(kb_a.get("archetype_scores", {}).keys()) & set(kb_b.get("archetype_scores", {}).keys())
        if shared_archetypes:
            theme_strength += 0.2

    total = theme_strength + trait_strength + sentiment_bonus
    total = min(total, 1.0)

    if total < 0.1:
        return None, 0.0

    if sentiment_diff > 0.5:
        rel = "contrasts_with"
    elif shared_themes and _same_domain(ba, bb):
        rel = "parallels"
    elif shared_themes:
        rel = "complements"
    elif trait_strength > 0.2:
        rel = "identifies_with"
    else:
        rel = "fascinated_by"

    return rel, total


def _is_cross_domain(ba, bb):
    """Check if two beads come from different knowledge domains."""
    if not ba.domains or not bb.domains:
        return False
    return not bool(set(ba.domains) & set(bb.domains))


def _same_domain(ba, bb):
    """Check if two beads share at least one domain."""
    return bool(set(ba.domains) & set(bb.domains))


def _evidence_for(ba, bb, rel):
    """Generate human-readable evidence for a relationship."""
    evidence = []
    shared = set(ba.themes) & set(bb.themes)
    if shared:
        evidence.append(f"Shared themes: {', '.join(sorted(shared))}")
    if _is_cross_domain(ba, bb):
        evidence.append(f"Cross-domain: {ba.domains} <-> {bb.domains}")
    shared_traits = set(t.lower() for t in ba.traits) & set(t.lower() for t in bb.traits)
    if shared_traits:
        evidence.append(f"Shared traits: {', '.join(sorted(shared_traits))}")
    return evidence


def _cluster_by_theme(beads):
    """Group beads by their dominant theme."""
    clusters = defaultdict(list)
    for b in beads:
        if b.themes:
            clusters[b.themes[0]].append(b.canonical)
        else:
            clusters["unclassified"].append(b.canonical)
    return dict(clusters)


def _compute_centralities(beads, edges):
    """Compute simple degree centrality for each bead."""
    counts = defaultdict(int)
    for e in edges:
        counts[e.bead_a] += 1
        counts[e.bead_b] += 1
    for b in beads:
        if b.canonical not in counts:
            counts[b.canonical] = 0
    return dict(counts)


def find_bridges(graph_data):
    """Find bridge entities that connect different theme clusters.

    A bridge is a bead that appears in multiple clusters or connects
    beads from different clusters.
    """
    clusters = graph_data.get("clusters", {})
    if len(clusters) < 2:
        return []

    theme_to_beads = {}
    for theme, names in clusters.items():
        for name in names:
            if name not in theme_to_beads:
                theme_to_beads[name] = set()
            theme_to_beads[name].add(theme)

    bridges = []
    for name, themes in theme_to_beads.items():
        if len(themes) >= 2:
            bridges.append({
                "entity": name,
                "connects_themes": sorted(themes),
                "bridge_strength": len(themes) / len(clusters),
            })

    return sorted(bridges, key=lambda x: -x["bridge_strength"])
