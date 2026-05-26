"""Market Kit orchestration built on Source Corpus ingestion."""

from __future__ import annotations

from typing import Any

from .ingest import ingest_source


def create_market_kit(
    *,
    github: str | None = None,
    path: str | None = None,
    artifacts: list[str] | None = None,
    include_code: bool = True,
    include_issues: bool = False,
    include_prs: bool = False,
    include_commits: bool = False,
    include_hidden: bool = False,
    include_large_files: bool = False,
    include_visual_analysis: bool = False,
    max_signals: int = 80,
) -> dict[str, Any]:
    """Create an Ingestion Result with a structured Market Kit."""
    artifact_list = _artifact_list(artifacts)
    result = ingest_source(
        github=github,
        path=path,
        include_code=include_code,
        include_issues=include_issues,
        include_prs=include_prs,
        include_commits=include_commits,
        include_hidden=include_hidden,
        include_large_files=include_large_files,
        include_visual_analysis=include_visual_analysis,
        artifacts=artifact_list,
        max_signals=max_signals,
    )
    corpus_text = result["source_corpus"].get("corpus_text", "")

    from .engine import GameEngine
    from .lenses.brand import generate_brand
    from .lenses.design import generate_design
    from .naming import research_name_from_identity
    from .process_trace import process_trace_from_state

    engine = GameEngine()
    engine.declare_themes(corpus_text)
    engine.elaborate()
    engine.connect_domains()
    state = engine.state
    graph = state.metadata.get("pattern_graph", {})
    entities = [bead.to_dict() for bead in state.beads]
    brand_markdown = generate_brand(entities, graph)
    design_markdown = generate_design(entities, graph)
    naming = research_name_from_identity(entities, graph)
    kit = _assemble_market_kit(
        result=result,
        entities=entities,
        graph=graph,
        naming=naming,
        brand_markdown=brand_markdown,
        design_markdown=design_markdown,
    )
    result.update({
        "pattern_graph": graph,
        "market_kit": kit,
        "process_trace": {
            **result.get("process_trace", {}),
            "synthesis": process_trace_from_state(state, lens="market_kit"),
        },
    })
    result["artifacts"] = _render_artifacts(result, artifact_list)
    from .ingest import _persist_ingestion_result
    _persist_ingestion_result(result)
    return result


def _artifact_list(artifacts: list[str] | str | None) -> list[str]:
    if artifacts is None:
        return []
    if isinstance(artifacts, str):
        return [artifacts]
    return list(artifacts)


def _assemble_market_kit(
    *,
    result: dict[str, Any],
    entities: list[dict[str, Any]],
    graph: dict[str, Any],
    naming: dict[str, Any],
    brand_markdown: str,
    design_markdown: str,
) -> dict[str, Any]:
    top_patterns = graph.get("patterns", [])[:3]
    emergent = graph.get("emergent_topic") or graph.get("emergent_theme") or "Market Direction"
    source_name = result.get("source_target", {}).get("metadata", {}).get("name") or result.get("source_target", {}).get("name") or emergent
    signals = result.get("source_corpus", {}).get("signals", [])
    top_signal_titles = [signal.get("title") for signal in signals[:8]]
    voice = _extract_section(brand_markdown, "Voice Rules") or _extract_section(brand_markdown, "Brand Personality")
    palette = _extract_tokens(design_markdown, "--color-")
    typography = _extract_tokens(design_markdown, "--font-")
    spacing = _extract_tokens(design_markdown, "--spacing-")
    radii = _extract_tokens(design_markdown, "--radius-")
    shadows = _extract_tokens(design_markdown, "--shadow-")
    candidate_names = [
        {
            "name": variant.get("name"),
            "fit": variant.get("identity_fit"),
            "style": variant.get("style"),
            "reasoning": variant.get("reasoning"),
        }
        for variant in naming.get("variants", [])[:8]
    ]
    return {
        "title": f"{source_name} Market Kit",
        "positioning": {
            "category": _category_from_signals(signals),
            "market_premise": graph.get("emergent_theme") or f"{source_name} expresses {emergent}.",
            "differentiation": _differentiation(top_patterns, signals),
            "audience": _audience_from_signals(signals),
        },
        "naming": {
            "directions": [p.get("name") for p in top_patterns],
            "candidates": candidate_names,
            "recommendations": naming.get("recommendations", [])[:5],
        },
        "brand_voice": {
            "markdown": brand_markdown,
            "summary": voice[:1200] if voice else brand_markdown[:1200],
        },
        "messaging": {
            "pillars": _messaging_pillars(top_patterns, signals),
            "taglines": _taglines(source_name, top_patterns),
            "landing_angles": _landing_angles(source_name, top_patterns),
        },
        "design_system": {
            "markdown": design_markdown,
            "color_palette": palette,
            "typography": typography,
            "spacing": spacing,
            "borders": radii,
            "shadows": shadows,
            "visual_motifs": _visual_motifs(signals, top_patterns),
        },
        "evidence_map": {
            "top_signals": top_signal_titles,
            "signal_count": result.get("source_corpus", {}).get("signal_count", 0),
            "rejected": result.get("rejected_signals", {}),
        },
    }


def _render_artifacts(result: dict[str, Any], artifacts: list[str]) -> dict[str, str]:
    requested = {artifact.lower() for artifact in artifacts}
    rendered: dict[str, str] = {}
    if "markdown" in requested:
        rendered["market-kit.md"] = _render_markdown(result.get("market_kit", {}))
    if requested & {"html", "css", "market-page"}:
        rendered["market-kit.html"] = _render_html(result.get("market_kit", {}))
        rendered["market-kit.css"] = _render_css()
    return rendered


def _extract_section(markdown: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in markdown:
        return ""
    after = markdown.split(marker, 1)[1]
    next_heading = after.find("\n## ")
    return after[:next_heading].strip() if next_heading >= 0 else after.strip()


def _extract_tokens(markdown: str, prefix: str) -> dict[str, str]:
    tokens = {}
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix) and ":" in stripped:
            key, value = stripped.rstrip(";").split(":", 1)
            tokens[key.strip()] = value.strip()
    return tokens


def _category_from_signals(signals: list[dict[str, Any]]) -> str:
    text = " ".join((signal.get("text") or "")[:500] for signal in signals).lower()
    if "mcp" in text:
        return "AI integration infrastructure"
    if "api" in text and "cli" in text:
        return "developer tool"
    if "design" in text or "brand" in text:
        return "creative intelligence system"
    return "software product"


def _audience_from_signals(signals: list[dict[str, Any]]) -> list[str]:
    text = " ".join((signal.get("text") or "")[:500] for signal in signals).lower()
    audience = []
    if "developer" in text or "api" in text or "cli" in text:
        audience.append("developers and technical operators")
    if "design" in text or "brand" in text or "marketing" in text:
        audience.append("brand, design, and marketing operators")
    if "ai" in text or "llm" in text or "mcp" in text:
        audience.append("AI workflow builders")
    return audience or ["operators evaluating the product category"]


def _differentiation(patterns: list[dict[str, Any]], signals: list[dict[str, Any]]) -> str:
    names = [p.get("name") for p in patterns if p.get("name")]
    signal = signals[0].get("title") if signals else "source evidence"
    if names:
        return f"Combines {', '.join(names[:3])} signals with evidence from {signal}."
    return f"Grounded in evidence from {signal}."


def _messaging_pillars(patterns: list[dict[str, Any]], signals: list[dict[str, Any]]) -> list[dict[str, str]]:
    pillars = []
    for pattern in patterns[:3]:
        name = pattern.get("name") or "Pattern"
        pillars.append({
            "pillar": name,
            "message": f"Lead with {name.lower()} because it is one of the strongest patterns in the Source Corpus.",
        })
    if not pillars:
        pillars.append({"pillar": "Evidence-led clarity", "message": "Use the highest-value Corpus Signals as the market narrative spine."})
    return pillars


def _taglines(source_name: str, patterns: list[dict[str, Any]]) -> list[str]:
    lead = (patterns[0].get("name") if patterns else "clarity") or "clarity"
    return [
        f"{source_name}: {lead} made usable.",
        f"Turn the signal into a market.",
        f"Evidence-led direction for what comes next.",
    ]


def _landing_angles(source_name: str, patterns: list[dict[str, Any]]) -> list[dict[str, str]]:
    lead = (patterns[0].get("name") if patterns else "signal") or "signal"
    return [
        {"angle": "Evidence-first", "headline": f"See what {source_name} is really saying.", "support": "Turn repository evidence into naming, brand, marketing, and design direction."},
        {"angle": "Pattern-led", "headline": f"Build from the strongest {lead} signals.", "support": "Use the pattern graph to keep every market decision aligned."},
    ]


def _visual_motifs(signals: list[dict[str, Any]], patterns: list[dict[str, Any]]) -> list[str]:
    text = " ".join((signal.get("text") or "")[:500] for signal in signals).lower()
    motifs = []
    for word in ("graph", "thread", "signal", "system", "kit", "blue", "light", "matrix", "loom"):
        if word in text:
            motifs.append(word)
    motifs.extend((p.get("name") or "").lower() for p in patterns[:2])
    return [motif for motif in motifs if motif][:8]


def _render_markdown(kit: dict[str, Any]) -> str:
    lines = [f"# {kit.get('title', 'Market Kit')}", ""]
    positioning = kit.get("positioning", {})
    lines.extend(["## Positioning", "", positioning.get("market_premise", ""), ""])
    lines.extend(["## Naming", ""])
    for candidate in kit.get("naming", {}).get("candidates", [])[:8]:
        if candidate.get("name"):
            lines.append(f"- **{candidate['name']}**")
    lines.extend(["", "## Messaging", ""])
    for pillar in kit.get("messaging", {}).get("pillars", []):
        lines.append(f"- **{pillar.get('pillar')}**: {pillar.get('message')}")
    lines.extend(["", "## Design System", ""])
    design = kit.get("design_system", {})
    for label, tokens in (("Color Palette", design.get("color_palette", {})), ("Typography", design.get("typography", {}))):
        lines.append(f"### {label}")
        for key, value in tokens.items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")
    return "\n".join(lines)


def _render_html(kit: dict[str, Any]) -> str:
    title = _esc(kit.get("title", "Market Kit"))
    colors = kit.get("design_system", {}).get("color_palette", {})
    swatches = "".join(
        f'<div class="swatch"><span style="background:{_esc(value)}"></span><strong>{_esc(key)}</strong><code>{_esc(value)}</code></div>'
        for key, value in colors.items()
    )
    taglines = "".join(f"<li>{_esc(item)}</li>" for item in kit.get("messaging", {}).get("taglines", []))
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{title}</title><link rel=\"stylesheet\" href=\"market-kit.css\"></head>"
        f"<body><main><h1>{title}</h1><section><h2>Taglines</h2><ul>{taglines}</ul></section>"
        f"<section><h2>Color Palette</h2><div class=\"swatches\">{swatches}</div></section></main></body></html>"
    )


def _render_css() -> str:
    return (
        "body{font-family:Inter,system-ui,sans-serif;margin:0;background:#0b1020;color:#f8fafc;}"
        "main{max-width:1040px;margin:0 auto;padding:48px;}"
        "h1{font-size:48px;line-height:1.05;}"
        ".swatches{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;}"
        ".swatch{border:1px solid rgba(255,255,255,.16);padding:16px;border-radius:8px;background:rgba(255,255,255,.06);}"
        ".swatch span{display:block;height:72px;border-radius:6px;margin-bottom:12px;}"
        "code{display:block;color:#cbd5e1;margin-top:4px;}"
    )


def _esc(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
