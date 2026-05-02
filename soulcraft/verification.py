"""Triple verification and quality checks for the Glass Bead Game."""

from .bead import VALID_TYPES as _VALID_BEAD_TYPES


def verify_pattern(pattern: dict) -> dict:
    cross_domain = (
        pattern.get("supporting_entities", 0) >= 2
        and len(pattern.get("themes", [])) >= 2
    )
    generative = (
        pattern.get("probability", 0) > 0.15
        and pattern.get("supporting_entities", 0) >= 2
    )
    exclusive = (
        pattern.get("probability", 0) > 0.05
        and len(pattern.get("name", "")) > 5
    )

    gates = {
        "cross_domain": cross_domain,
        "generative": generative,
        "exclusive": exclusive,
    }
    passed = sum(gates.values())

    if passed >= 2:
        level = "model"
        confidence = 0.9 if passed == 3 else 0.75
    elif passed == 1:
        level = "heuristic"
        confidence = 0.5
    else:
        level = "discard"
        confidence = 0.1

    return {
        "level": level,
        "confidence": confidence,
        "gates": gates,
    }


def verify_bead(bead) -> dict:
    issues = []
    warnings = []

    if hasattr(bead, "to_dict"):
        data = bead.to_dict()
    else:
        data = bead

    if not data.get("canonical"):
        issues.append("missing canonical name")

    if not data.get("themes"):
        warnings.append("no themes assigned")

    confidence = data.get("confidence", -1)
    if confidence <= 0:
        issues.append(f"invalid confidence: {confidence}")

    bead_type = data.get("type", "")
    if bead_type not in _VALID_BEAD_TYPES:
        issues.append(f"invalid type: {bead_type!r}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
    }


def verify_graph(graph: dict) -> dict:
    issues = []
    warnings = []

    if not graph.get("patterns"):
        warnings.append("graph has no patterns")

    emergent = graph.get("emergent_topic")
    if not emergent or emergent == "Unknown":
        warnings.append("missing or unknown emergent_topic")

    consensus = graph.get("consensus_score", -1)
    if not (0.0 <= consensus <= 1.0):
        issues.append(f"consensus_score out of range: {consensus}")

    if "entity_scores" not in graph:
        issues.append("no entity_scores present")

    models = 0
    heuristics = 0
    discarded = 0
    patterns_verified = 0

    for p in graph.get("patterns", []):
        result = verify_pattern(p)
        patterns_verified += 1
        level = result["level"]
        if level == "model":
            models += 1
        elif level == "heuristic":
            heuristics += 1
        else:
            discarded += 1

    return {
        "valid": len(issues) == 0,
        "patterns_verified": patterns_verified,
        "models": models,
        "heuristics": heuristics,
        "discarded": discarded,
        "issues": issues,
        "warnings": warnings,
    }
