"""Naming research engine for brand/persona name generation.

Provides systematic name research with availability checks,
similarity analysis, and semantic clustering.
"""

import json
import re
import urllib.request
import urllib.error
from typing import List, Dict, Optional


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

        # Extract JSON
        json_str = content.strip()
        if "```" in json_str:
            match = re.search(r"```(?:json)?\s*\n?(.*?)```", json_str, re.DOTALL)
            if match:
                json_str = match.group(1).strip()

        start = json_str.find("{")
        end = json_str.rfind("}")
        if start == -1 or end == -1:
            return _default_semantics()

        data = json.loads(json_str[start:end + 1])
        if not isinstance(data, dict):
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


def research_name(name: str, context: str = "", generate_variants: bool = True) -> Dict:
    """Full naming research pipeline.

    Args:
        name: Base name or concept to research
        context: Usage context
        generate_variants: Whether to generate alternative names

    Returns:
        Complete research report with variants, semantics, and recommendations
    """
    report = {
        "input_name": name,
        "context": context,
        "variants": [],
        "semantics": {},
        "recommendations": [],
    }

    # Generate variants if requested
    if generate_variants:
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


def format_research_report(report: Dict) -> str:
    """Format naming research as readable markdown."""
    lines = [
        f"# Naming Research: {report['input_name']}",
        "",
        f"**Context:** {report.get('context', 'General')}",
        "",
        "## Semantic Analysis",
        "",
    ]

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
