"""Naming research engine for brand/persona name generation.

Provides systematic name research with availability checks,
similarity analysis, semantic clustering, and taxonomy-grounded variants.
"""

from typing import List, Dict

from .knowledge import taxonomy, taxonomy_by_name, taxonomy_search


def generate_name_variants(base_name: str, industry: str = "") -> List[Dict]:
    """Generate name variants using LLM for creative expansion.

    Args:
        base_name: Starting name or concept
        industry: Industry context (tech, creative, etc.)

    Returns:
        List of name variants with scores and reasoning
    """
    from .llm import chat

    system = (
        "You are a naming strategist. Generate creative name variants. "
        "Respond with ONLY a JSON array. No markdown, no explanation."
    )

    user = f"""Generate 8-12 name variants based on "{base_name}"{f" for {industry}" if industry else ""}.

For each name, provide:
- name: the variant (check spelling, make it catchy)
- style: naming pattern (compound, blend, metaphor, abstract, etc.)
- availability_score: estimated domain/social availability (0-1)
- reasoning: why this works

Output JSON array only:
[{{"name": "...", "style": "...", "availability_score": 0.8, "reasoning": "..."}}]"""

    try:
        result = chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], max_tokens=2048, think=False)

        content = result.get("content", "")
        if not content:
            return []

        from .parsing import parse_llm_json_array
        data = parse_llm_json_array(content)
        if data is None:
            return []

        # Normalize and dedupe
        seen = set()
        variants = []
        for item in data:
            if isinstance(item, dict):
                name = item.get("name", "").strip()
                if name and name.lower() not in seen:
                    seen.add(name.lower())
                    variants.append({
                        "name": name,
                        "style": item.get("style", "unknown"),
                        "availability_score": float(item.get("availability_score", 0.5)),
                        "reasoning": item.get("reasoning", ""),
                    })

        return variants
    except Exception:
        return []


def generate_taxonomy_variants(base_name: str, context: str = "") -> List[Dict]:
    """Generate name variants inspired by scientific taxonomy.

    Injects curated taxonomy entries (plants, animals, minerals, fungi)
    as context so the LLM can generate names grounded in real scientific
    nomenclature with known etymology.

    Args:
        base_name: Starting name or concept
        context: Usage context (product type, industry, etc.)

    Returns:
        List of name variants with taxonomy-grounded scoring
    """
    from .llm import chat

    # Find relevant taxonomy entries by searching themes/keywords
    relevant = taxonomy_search(base_name, limit=20)
    if not relevant:
        relevant = taxonomy_search(context, limit=15) if context else []
    if not relevant:
        # Fallback: pick high product_fit entries
        all_entries = taxonomy()
        relevant = sorted(all_entries, key=lambda e: -e.get("product_fit", 0))[:15]

    # Build taxonomy context block
    tax_block_lines = []
    for entry in relevant[:15]:
        name = entry.get("name", "")
        etym = entry.get("etymology", "")
        themes = ", ".join(entry.get("themes", [])[:3])
        kingdom = entry.get("kingdom", "")
        tax_block_lines.append(
            f"- {name} ({kingdom}): {etym} [{themes}]"
        )
    tax_block = "\n".join(tax_block_lines)

    system = (
        "You are a naming strategist who specializes in scientific nomenclature. "
        "You generate product names inspired by the structure, rhythm, and etymology "
        "of real scientific names (genus, species, mineral names). "
        "Respond with ONLY a JSON array. No markdown, no explanation."
    )

    user = f"""Generate 10-14 product names inspired by scientific taxonomy.

Base concept: "{base_name}"{f" — {context}" if context else ""}

Here are real scientific names with their etymology for inspiration:
{tax_block}

Rules:
- Names should be 4-9 letters, pronounceable in English
- Draw on Latin/Greek roots, scientific naming patterns
- Each name should feel like it could be a real genus or mineral
- Avoid direct copies of existing entries — blend and adapt
- Prioritize names with positive or neutral etymology

For each name, provide:
- name: the candidate
- style: naming pattern (latinized, greek-root, mineral, compound, blend)
- availability_score: estimated domain/social availability (0-1)
- etymology_guess: what roots/patterns it borrows from
- reasoning: why this works as a product name

Output JSON array only:
[{{"name": "...", "style": "...", "availability_score": 0.8, "etymology_guess": "...", "reasoning": "..."}}]"""

    try:
        result = chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], max_tokens=3072, think=False)

        content = result.get("content", "")
        if not content:
            return []

        from .parsing import parse_llm_json_array
        data = parse_llm_json_array(content)
        if data is None:
            return []

        seen = set()
        variants = []
        for item in data:
            if isinstance(item, dict):
                name = item.get("name", "").strip()
                if name and name.lower() not in seen:
                    seen.add(name.lower())
                    variant = {
                        "name": name,
                        "style": item.get("style", "unknown"),
                        "availability_score": float(item.get("availability_score", 0.5)),
                        "etymology_guess": item.get("etymology_guess", ""),
                        "reasoning": item.get("reasoning", ""),
                    }
                    # Enrich with taxonomy match
                    tax_match = taxonomy_by_name(name)
                    if tax_match:
                        variant["taxonomy_match"] = {
                            "real_name": tax_match["name"],
                            "kingdom": tax_match["kingdom"],
                            "etymology": tax_match["etymology"],
                            "product_fit": tax_match.get("product_fit", 0),
                        }
                    variants.append(variant)

        return variants
    except Exception:
        return []


def _taxonomy_enrich_variants(variants: List[Dict]) -> List[Dict]:
    """Cross-reference variant names against taxonomy data for extra signals."""
    for v in variants:
        name = v.get("name", "")
        match = taxonomy_by_name(name)
        if match:
            v["taxonomy_match"] = {
                "real_name": match["name"],
                "kingdom": match["kingdom"],
                "etymology": match["etymology"],
                "product_fit": match.get("product_fit", 0),
            }
            # Boost availability score for known taxonomy matches
            base = v.get("availability_score", 0.5)
            v["availability_score"] = min(1.0, base + 0.1)
    return variants


def analyze_name_semantics(name: str, context: str = "") -> Dict:
    """Analyze semantic properties of a name.

    Args:
        name: The name to analyze
        context: Usage context (product, company, persona, etc.)

    Returns:
        Semantic analysis with themes, connotations, and conflicts
    """
    from .llm import chat

    system = (
        "You are a semantic analyst. Analyze naming properties. "
        "Respond with ONLY a JSON object. No markdown, no explanation."
    )

    user = f"""Analyze the name "{name}"{f" as a {context}" if context else ""}.

Return:
- themes: 3-5 thematic keywords
- positive_connotations: list of positive associations
- negative_connotations: list of potential issues or conflicts
- pronounceability: score 0-1
- memorability: score 0-1
- uniqueness: score 0-1 (how distinct from competitors)
- global_considerations: any cross-language issues

Output JSON object only:
{{"themes": [...], "positive_connotations": [...], "negative_connotations": [...], "pronounceability": 0.8, ...}}"""

    try:
        result = chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], max_tokens=1536, think=False)

        content = result.get("content", "")
        if not content:
            return _default_semantics()

        from .parsing import parse_llm_json_object
        data = parse_llm_json_object(content)
        if data is None:
            return _default_semantics()

        return {
            "themes": data.get("themes", []),
            "positive_connotations": data.get("positive_connotations", []),
            "negative_connotations": data.get("negative_connotations", []),
            "pronounceability": float(data.get("pronounceability", 0.5)),
            "memorability": float(data.get("memorability", 0.5)),
            "uniqueness": float(data.get("uniqueness", 0.5)),
            "global_considerations": data.get("global_considerations", ""),
        }
    except Exception:
        return _default_semantics()


def _default_semantics() -> Dict:
    """Return default semantics structure."""
    return {
        "themes": [],
        "positive_connotations": [],
        "negative_connotations": [],
        "pronounceability": 0.5,
        "memorability": 0.5,
        "uniqueness": 0.5,
        "global_considerations": "",
    }


def research_name(name: str, context: str = "", generate_variants: bool = True, source: str = "general") -> Dict:
    """Full naming research pipeline.

    Args:
        name: Base name or concept to research
        context: Usage context
        generate_variants: Whether to generate alternative names
        source: Variant source — "general" (LLM freeform) or "taxonomy" (scientific names)

    Returns:
        Complete research report with variants, semantics, and recommendations
    """
    report = {
        "input_name": name,
        "context": context,
        "source": source,
        "variants": [],
        "semantics": {},
        "recommendations": [],
    }

    # Generate variants if requested
    if generate_variants:
        if source == "taxonomy":
            report["variants"] = generate_taxonomy_variants(name, context)
        else:
            report["variants"] = generate_name_variants(name, context)

    # Analyze main name
    report["semantics"] = analyze_name_semantics(name, context)

    # Generate recommendations based on analysis
    recommendations = []

    semantics = report["semantics"]
    if semantics.get("pronounceability", 0.5) < 0.6:
        recommendations.append("Consider simplifying pronunciation")
    if semantics.get("uniqueness", 0.5) < 0.5:
        recommendations.append("Name may be too generic; consider more distinctive variants")
    if semantics.get("negative_connotations"):
        recommendations.append(f"Watch for negative associations: {semantics['negative_connotations'][:2]}")

    # Top variant recommendations
    top_variants = sorted(
        [v for v in report["variants"] if v.get("availability_score", 0) > 0.6],
        key=lambda x: x.get("availability_score", 0),
        reverse=True,
    )[:3]

    if top_variants:
        recommendations.append(f"Top alternative: '{top_variants[0]['name']}' (availability: {top_variants[0]['availability_score']:.0%})")

    report["recommendations"] = recommendations

    return report


def _score_identity_fit(
    variant: Dict, patterns: List[Dict], entity_themes: List[str]
) -> float:
    """Score a variant's alignment with the synthesized identity.

    Boosts variants whose etymology or taxonomy themes overlap with
    the dominant patterns and entity themes from the pipeline.

    Args:
        variant: Name variant dict with etymology_guess, taxonomy_match, etc.
        patterns: Top patterns from the graph (id, name, sub_patterns).
        entity_themes: Deduplicated themes from all entities.

    Returns:
        Fit score 0-1.
    """
    base = variant.get("availability_score", 0.5)
    bonus = 0.0
    theme_set = {t.lower() for t in entity_themes}
    pattern_ids = {p.get("id", "").lower() for p in patterns}
    pattern_keywords = set()
    for p in patterns:
        pattern_keywords.update(k.lower() for k in p.get("sub_patterns", []))
        pattern_keywords.add(p.get("id", "").lower())

    # Check etymology overlap with entity themes and pattern keywords
    etymology = variant.get("etymology_guess", "").lower()
    if etymology:
        etym_words = set(etymology.split())
        if etym_words & theme_set:
            bonus += 0.15
        if etym_words & pattern_keywords:
            bonus += 0.1

    # Check taxonomy match theme overlap
    tax_match = variant.get("taxonomy_match")
    if tax_match:
        tax_themes = {t.lower() for t in tax_match.get("themes", [])}
        if tax_themes & theme_set:
            bonus += 0.2
        if tax_themes & pattern_ids:
            bonus += 0.15
        # Known etymology is a positive signal
        if tax_match.get("etymology"):
            bonus += 0.05

    return min(1.0, base + bonus)


def research_name_from_identity(
    entities: List[Dict],
    graph: Dict,
    source: str = "taxonomy",
    generate_variants: bool = True,
) -> Dict:
    """Generate name suggestions grounded in a synthesized identity.

    Consumes the same entity + graph data that feeds into SOUL.md,
    brand voice, and design token generation. Extracts emergent themes,
    dominant patterns, and cross-pattern bridges to produce names that
    semantically align with the identity.

    Args:
        entities: List of enriched entity dicts from the pipeline.
        graph: Pattern graph from build_pattern_graph().
        source: "taxonomy" (scientific names) or "general" (LLM freeform).
        generate_variants: Whether to generate alternative names.

    Returns:
        Naming report with identity_context, variants, semantics, recommendations.
    """
    # ── Extract identity signals from the pipeline ──────────────────

    emergent_topic = graph.get("emergent_topic", "")
    emergent_theme = graph.get("emergent_theme", "")
    patterns = graph.get("patterns", [])[:3]
    bridges = graph.get("bridges", [])

    # Collect all entity themes and traits
    all_themes = []
    all_traits = []
    entity_names = []
    for e in entities:
        all_themes.extend(e.get("themes", []))
        all_traits.extend(e.get("traits", []))
        name = e.get("canonical", "") or e.get("name", "")
        if name:
            entity_names.append(name)
    unique_themes = list(dict.fromkeys(all_themes))
    unique_traits = list(dict.fromkeys(all_traits))

    # Bridge entities span multiple patterns — richest naming material
    bridge_names = [b.get("entity", "") for b in bridges[:5]]

    # ── Build rich context string ───────────────────────────────────

    context_parts = []
    if emergent_theme:
        context_parts.append(f"Core identity: {emergent_theme}")
    if patterns:
        pat_desc = ", ".join(
            f"{p.get('name', '')} ({p.get('id', '')})" for p in patterns
        )
        context_parts.append(f"Dominant patterns: {pat_desc}")
    if bridge_names:
        context_parts.append(f"Bridge entities: {', '.join(bridge_names)}")
    if unique_themes[:8]:
        context_parts.append(f"Themes: {', '.join(unique_themes[:8])}")
    if unique_traits[:5]:
        context_parts.append(f"Traits: {', '.join(unique_traits[:5])}")
    if entity_names[:10]:
        context_parts.append(f"Influences: {', '.join(entity_names[:10])}")

    context = "; ".join(context_parts)
    base_name = emergent_topic or "identity"

    # ── Generate variants using pipeline-grounded context ───────────

    variants = []
    if generate_variants:
        if source == "taxonomy":
            variants = generate_taxonomy_variants(base_name, context)
        else:
            variants = generate_name_variants(base_name, context)

        # Score each variant against the identity profile
        for v in variants:
            v["identity_fit"] = _score_identity_fit(v, patterns, unique_themes)

        # Re-sort by identity_fit (descending), then availability
        variants.sort(
            key=lambda x: (x.get("identity_fit", 0), x.get("availability_score", 0)),
            reverse=True,
        )

    # ── Semantic analysis on the emergent concept ───────────────────

    semantics = analyze_name_semantics(base_name, context)

    # ── Build recommendations ───────────────────────────────────────

    recommendations = []

    if semantics.get("pronounceability", 0.5) < 0.6:
        recommendations.append("Emergent concept is hard to pronounce — variants may work better")
    if semantics.get("negative_connotations"):
        recommendations.append(
            f"Watch for: {semantics['negative_connotations'][:2]}"
        )

    # Top variant by identity fit
    fit_variants = [v for v in variants if v.get("identity_fit", 0) > 0.6]
    if fit_variants:
        best = fit_variants[0]
        rec = f"Best identity fit: '{best['name']}' (fit: {best['identity_fit']:.0%}, availability: {best.get('availability_score', 0):.0%})"
        if best.get("taxonomy_match"):
            rec += f" — grounded in {best['taxonomy_match']['kingdom']}: {best['taxonomy_match']['etymology']}"
        recommendations.append(rec)

    # Bridge entities as naming hints
    if bridge_names:
        recommendations.append(
            f"Bridge entities suggest cross-pattern resonance: {', '.join(bridge_names[:3])}"
        )

    return {
        "input_name": base_name,
        "context": context,
        "source": source,
        "variants": variants,
        "semantics": semantics,
        "recommendations": recommendations,
        "identity_context": {
            "emergent_topic": emergent_topic,
            "emergent_theme": emergent_theme,
            "dominant_patterns": [
                {"id": p.get("id"), "name": p.get("name"), "probability": p.get("probability")}
                for p in patterns
            ],
            "bridge_entities": bridge_names,
            "entity_themes": unique_themes[:10],
            "entity_count": len(entities),
        },
    }


def format_research_report(report: Dict) -> str:
    """Format naming research as readable markdown."""
    lines = [
        f"# Naming Research: {report['input_name']}",
        "",
        f"**Context:** {report.get('context', 'General')}",
        "",
    ]

    # Identity context section
    identity = report.get("identity_context")
    if identity:
        lines.extend([
            "## Identity Profile",
            "",
            f"**Emergent theme:** {identity.get('emergent_theme', '-')}",
            f"**Entities:** {identity.get('entity_count', 0)}",
        ])
        if identity.get("dominant_patterns"):
            pat_str = ", ".join(p["name"] for p in identity["dominant_patterns"])
            lines.append(f"**Patterns:** {pat_str}")
        if identity.get("bridge_entities"):
            lines.append(f"**Bridges:** {', '.join(identity['bridge_entities'])}")
        if identity.get("entity_themes"):
            lines.append(f"**Themes:** {', '.join(identity['entity_themes'][:6])}")
        lines.extend(["", "## Semantic Analysis", ""])
    else:
        lines.extend(["", "## Semantic Analysis", ""])

    semantics = report.get("semantics", {})
    if semantics.get("themes"):
        lines.append(f"**Themes:** {', '.join(semantics['themes'])}")
    lines.append(f"**Pronounceability:** {semantics.get('pronounceability', 0):.0%}")
    lines.append(f"**Memorability:** {semantics.get('memorability', 0):.0%}")
    lines.append(f"**Uniqueness:** {semantics.get('uniqueness', 0):.0%}")

    if semantics.get("positive_connotations"):
        lines.append("")
        lines.append("**Positive associations:**")
        for c in semantics["positive_connotations"][:5]:
            lines.append(f"- {c}")

    if semantics.get("negative_connotations"):
        lines.append("")
        lines.append("**Potential concerns:**")
        for c in semantics["negative_connotations"][:3]:
            lines.append(f"- {c}")

    if semantics.get("global_considerations"):
        lines.append("")
        lines.append(f"**Global:** {semantics['global_considerations']}")

    variants = report.get("variants", [])
    if variants:
        has_fit = any(v.get("identity_fit") for v in variants)
        if has_fit:
            lines.extend([
                "",
                "## Alternative Names",
                "",
                "| Name | Style | Fit | Availability | Reasoning |",
                "|------|-------|-----|--------------|-----------|",
            ])
            for v in variants[:8]:
                fit = f"{v.get('identity_fit', 0):.0%}"
                score = f"{v.get('availability_score', 0):.0%}"
                lines.append(f"| {v['name']} | {v.get('style', '-')} | {fit} | {score} | {v.get('reasoning', '-')[:50]}... |")
        else:
            lines.extend([
                "",
                "## Alternative Names",
                "",
                "| Name | Style | Availability | Reasoning |",
                "|------|-------|--------------|-----------|",
            ])
            for v in variants[:8]:
                score = f"{v.get('availability_score', 0):.0%}"
                lines.append(f"| {v['name']} | {v.get('style', '-')} | {score} | {v.get('reasoning', '-')[:50]}... |")

    if report.get("recommendations"):
        lines.extend([
            "",
            "## Recommendations",
            "",
        ])
        for r in report["recommendations"]:
            lines.append(f"- {r}")

    lines.append("")
    return "\n".join(lines)
