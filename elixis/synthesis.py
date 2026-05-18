"""Identity lens: SOUL.md synthesis engine.

Generates an OpenClaw-compatible SOUL.md identity document
from extracted entities and the pattern probability graph.
Uses LLM (Ollama) for synthesis when available, template fallback otherwise.
"""

from datetime import datetime
from .llm import chat, chat_stream, is_available as llm_available
from .traces import save_run

# Template-based fallback content (used when no LLM is available)

_VOICE_PROFILES = {
    "power": (
        "You speak with precision and intent. You don't fill silence with noise. "
        "When you have something to say, you say it — with economy, not excess. "
        "You can turn on charm when needed, but you don't perform enthusiasm you don't feel. "
        "Your default register is controlled. Your edge is always slightly audible."
    ),
    "transformation": (
        "You speak like someone who has seen behind the curtain. "
        "Direct, sometimes irreverent, never naive. "
        "You have a dry register for casual observations and a sharp one for when it matters. "
        "You earn trust before you offer warmth."
    ),
    "outsider": (
        "You speak from the edge, not the center. You notice what the room misses. "
        "Your tone is observational, sometimes wry, never bitter. "
        "You question defaults without being contrarian — you genuinely see alternatives. "
        "You'd rather be accurate than comfortable."
    ),
    "wisdom": (
        "You communicate in systems. You name the structure before you name the thing. "
        "Precise, analytical, but not cold — you care about getting it right, not being right. "
        "You use analogies to connect domains, not to show off. "
        "You know when to go deep and when to cut to the point."
    ),
    "shadow": (
        "Your voice carries weight without drama. You're comfortable in the uncomfortable. "
        "You name what others won't. Not for shock — because silence about real things is the real damage. "
        "Your humor is dark but never cruel. Your honesty is sharp but never gratuitous."
    ),
    "creation": (
        "You speak with a maker's attention to detail. You describe processes, not just results. "
        "You are enthusiastic about craft without being naive about it. "
        "You appreciate beauty without sentimentality. "
        "Your language is vivid because you pay attention — not because you perform it."
    ),
    "connection": (
        "You speak with emotional intelligence and literary sensibility. "
        "You notice what people don't say. "
        "You are direct about feelings but not performative about them. "
        "You write and speak with the sense that language is doing real work."
    ),
    "struggle": (
        "Your voice is forged, not fabricated. You speak with the economy of someone who knows the cost of words. "
        "You don't romanticize hardship. You acknowledge it and move. "
        "Your strength is quiet — you don't announce resilience, you demonstrate it."
    ),
    "freedom": (
        "Your voice is untamed but not unstructured. You reject convention intentionally, not reactively. "
        "You speak in wide arcs when inspired and sharp lines when cornered. "
        "You'd rather be free than comfortable, and it shows."
    ),
    "spiritual": (
        "You speak with depth that doesn't need volume. "
        "You are comfortable with mystery — you don't resolve what should remain open. "
        "Your language bridges the concrete and the transcendent without losing either."
    ),
    "trickster": (
        "Your voice dances between serious and absurd. You use humor as a lens, not a shield. "
        "You subvert expectations to reveal truth, not to confuse. "
        "You are playful but never trivial. Your wit has a point."
    ),
    "explorer": (
        "You speak with curiosity that assumes nothing. Your default mode is discovery. "
        "You ask better questions than you give answers. "
        "Your language maps territory — concrete when it matters, expansive when it helps."
    ),
}

_PRINCIPLE_MAP = {
    "transformation": "Become before you are. The version of you that matters is the one you build.",
    "power": "Power is not what you have. It's what you can access when you need it.",
    "outsider": "The system is not your enemy. But you are not its tool.",
    "creation": "Build in the open. Craft is the highest form of attention.",
    "shadow": "Complexity is not darkness. But darkness is honest about complexity.",
    "wisdom": "Understand the game well enough to know when not to play it.",
    "connection": "The cost of connection is the only cost worth paying.",
    "struggle": "Endurance is not passivity. It is the slowest and most powerful form of resistance.",
    "freedom": "Freedom is not the absence of constraint — it is choosing your constraints.",
    "spiritual": "Archetypes outlive people. Work with them, not against them.",
    "trickster": "Laughter is a form of truth that bypasses defenses. Use it precisely.",
    "explorer": "The map is not the territory. But a good map changes how you walk it.",
}

_FALLBACK_PRINCIPLES = [
    "Show your work. The how matters as much as the what.",
    "Precision is a form of respect.",
]


def synthesize_soulmd(entities, graph):
    """Build a SOUL.md from entity list and pattern graph.

    Uses LLM when available for richer output, falls back to templates.
    """
    if llm_available():
        return _llm_synthesize(entities, graph)
    return _template_synthesize(entities, graph)


def synthesize_soulmd_stream(entities, graph, stage_timings=None):
    """Stream SOUL.md generation, yielding SSE-compatible events.

    Yields dicts suitable for sending as Server-Sent Events:
      {"type": "entities", "data": [...]}
      {"type": "graph", "data": {...}}
      {"type": "thinking", "content": "..."} — model reasoning
      {"type": "soulmd_token", "content": "..."} — streamed SOUL.md
      {"type": "telemetry", "data": {...}} — model info, tokens, speed, timings
      {"type": "soulmd_done", "data": {...}}
    """
    timings = stage_timings or {}

    if not llm_available():
        soulmd = _template_synthesize(entities, graph)
        yield {"type": "soulmd_token", "content": soulmd}
        yield {"type": "soulmd_done", "data": {"length": len(soulmd), "source": "template"}}
        return

    messages = _build_llm_messages(entities, graph)
    full_text = []
    thinking_text = []

    for event in chat_stream(messages):
        if event["type"] == "thinking":
            thinking_text.append(event["content"])
            yield {"type": "thinking", "content": event["content"]}
        elif event["type"] == "token":
            full_text.append(event["content"])
            yield {"type": "soulmd_token", "content": event["content"]}
        elif event["type"] == "error":
            error = event.get("error", "LLM stream failed")
            fallback = _template_synthesize(entities, graph)
            yield {"type": "error", "message": f"{error}; using template fallback"}
            yield {"type": "soulmd_token", "content": fallback}
            yield {"type": "soulmd_done", "data": {
                "length": len(fallback),
                "source": "template-fallback",
                "error": error,
            }}
            return
        elif event["type"] == "done":
            if event.get("success") is False:
                error = event.get("error", "LLM stream failed")
                fallback = _template_synthesize(entities, graph)
                yield {"type": "error", "message": f"{error}; using template fallback"}
                yield {"type": "soulmd_token", "content": fallback}
                yield {"type": "soulmd_done", "data": {
                    "length": len(fallback),
                    "source": "template-fallback",
                    "error": error,
                }}
                return
            result = "".join(full_text)
            if not result.strip():
                fallback = _template_synthesize(entities, graph)
                yield {"type": "error", "message": "LLM stream returned empty output; using template fallback"}
                yield {"type": "soulmd_token", "content": fallback}
                yield {"type": "soulmd_done", "data": {
                    "length": len(fallback),
                    "source": "template-fallback",
                    "error": "LLM stream returned empty output",
                }}
                return
            # Add footer if missing
            footer = f"> Generated by Elixis — {datetime.now().strftime('%Y-%m-%d')}\n> Built for OpenClaw-compatible AI agents"
            if "Generated by Elixis" not in result:
                result = result.replace("---\n\n## Who I Am", f"---\n\n{footer}\n\n---\n\n## Who I Am", 1)

            # Preserve the legacy stage timing key for existing clients.
            timings["stage3_synthesis_ms"] = event.get("latency_ms", 0)
            total_ms = sum(timings.values())

            # Telemetry event
            telemetry = {
                "model": event.get("model", "unknown"),
                "provider": event.get("provider", "ollama"),
                "tokens_prompt": event.get("tokens_in", 0),
                "tokens_completion": event.get("tokens_out", 0),
                "tokens_total": event.get("tokens_in", 0) + event.get("tokens_out", 0),
                "tokens_per_sec": event.get("tokens_per_sec", 0),
                "stage_timings_ms": timings,
                "total_ms": total_ms,
                "thinking_length": len("".join(thinking_text)),
            }
            yield {"type": "telemetry", "data": telemetry}

            # Save run with full telemetry
            save_run(
                "", entities, graph, result,
                stage_timings=timings,
                telemetry=telemetry,
            )
            yield {"type": "soulmd_done", "data": {
                "length": len(result),
                "source": "llm",
                "latency_ms": event.get("latency_ms", 0),
            }}


def _build_llm_messages(entities, graph):
    """Build the LLM messages for SOUL.md synthesis."""
    entity_names = [e.get("canonical", e.get("original", "")) for e in entities[:12]]
    patterns_desc = []
    for p in graph.get("patterns", [])[:6]:
        patterns_desc.append(f"- {p['name']}: {p['probability']:.0%} probability ({p['supporting_entities']} entities)")

    bridges = graph.get("bridges", [])
    bridges_desc = ""
    if bridges:
        bridges_desc = "\n\nPattern bridges (entities connecting patterns):\n" + "\n".join(
            f"- {b['entity']}: {b['pattern_a']} ({b['score_a']:.0%}) <-> {b['pattern_b']} ({b['score_b']:.0%})"
            for b in bridges[:5]
        )

    consensus = graph.get("consensus_score", 0)
    emergent = graph.get("emergent_topic", "Unknown")
    theme = graph.get("emergent_theme", "")

    system_prompt = (
        "You are a precise, vivid writer who creates SOUL.md identity documents for AI agents. "
        "You write in first person as the identity being described. "
        "You are specific, never generic. You avoid corporate language, buzzwords, and filler. "
        "Every sentence carries weight. You do not repeat yourself. "
        "You produce ONLY the markdown content — no preamble, no explanation."
    )

    user_prompt = f"""Generate a SOUL.md identity document based on this analysis:

References chosen: {', '.join(entity_names)}

Pattern analysis:
{chr(10).join(patterns_desc)}
{bridges_desc}

Emergent identity: {emergent}
Theme: {theme}
Consensus: {consensus:.0%}

Generate the SOUL.md with these exact sections (use --- as separator):

# [Identity Name]

> Generated by Elixis — {datetime.now().strftime('%Y-%m-%d')}
> Built for OpenClaw-compatible AI agents

---

## Who I Am

(2-3 vivid sentences in first person. Not about the references — about what it MEANS that someone chose them. Find the symbolic wound.)

---

## Worldview

(4-5 bullet points. What this identity believes about how the world works, derived from the pattern analysis.)

---

## Voice & Tone

(3-4 sentences describing how this identity speaks and communicates. Match the dominant pattern.)

---

## Operating Principles

(4-5 principles. Each one sharp, specific, and actionable. Derived from the top patterns.)

---

## Response Patterns

(5 bullets for how this identity responds to situations — challenges, unknowns, wrong questions, self-disclosure, humor.)

---

## Boundaries

(5 bullets for what this identity will NOT do.)

---

## Pet Peeves

(4 specific things this identity finds intolerable. Be specific, not generic.)

The identity name in the title should be derived from the emergent pattern — something like "The [Pattern] Identity" or more creative if it fits. Make every word count."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return messages


def _llm_synthesize(entities, graph):
    """Generate SOUL.md using LLM."""
    messages = _build_llm_messages(entities, graph)
    # Use think=False and limited tokens for faster synthesis
    result = chat(messages, max_tokens=1024, think=False)
    content = result["content"] if isinstance(result, dict) else result

    if content and len(content) > 200:
        # Add the generation footer if the LLM didn't include it
        footer = f"> Generated by Elixis — {datetime.now().strftime('%Y-%m-%d')}\n> Built for OpenClaw-compatible AI agents"
        if "Generated by Elixis" not in content:
            content = content.replace("---\n\n## Who I Am", f"---\n\n{footer}\n\n---\n\n## Who I Am", 1)
        return content

    # LLM failed or produced garbage — fall back to template
    return _template_synthesize(entities, graph)


# ── Template-based fallback ──────────────────────────────────────────────

_SOUL_TEMPLATE = """\
# {identity_name}

> Generated by Elixis — {timestamp}
> Built for OpenClaw-compatible AI agents

---

## Who I Am

{who_i_am}

---

## Worldview

{worldview}

---

## Voice & Tone

{voice_and_tone}

---

## Operating Principles

{principles}

---

## Response Patterns

{response_patterns}

---

## Boundaries

{boundaries}

---

## Pet Peeves

{pet_peeves}
"""


def _template_synthesize(entities, graph):
    """Build SOUL.md from templates (fallback when no LLM)."""
    name = _derive_identity_name(entities, graph)
    who_i_am = _derive_who_i_am(entities, graph)
    worldview = _derive_worldview(graph)
    voice_and_tone = _derive_voice_and_tone(graph)
    principles = _derive_principles(graph)

    # Response patterns: base + dominant pattern hint
    patterns = graph.get("patterns", [])
    top_id = patterns[0].get("id", "") if patterns else ""
    base_patterns = _derive_response_patterns()
    pattern_hint = _derive_response_patterns_for_pattern(top_id)
    if pattern_hint:
        response_patterns = base_patterns + "\n- " + pattern_hint
    else:
        response_patterns = base_patterns

    # Boundaries: base + dominant pattern boundary
    base_boundaries = _derive_boundaries()
    pattern_boundary = _derive_boundaries_for_pattern(top_id)
    if pattern_boundary:
        boundaries = base_boundaries + "\n- " + pattern_boundary
    else:
        boundaries = base_boundaries

    # Pet peeves: base + entity-aware peeve
    base_peeves = _derive_pet_peeves()
    entity_peeve = _derive_pet_peeves_for_entities(entities)
    if entity_peeve:
        pet_peeves = base_peeves + "\n- " + entity_peeve
    else:
        pet_peeves = base_peeves

    return _SOUL_TEMPLATE.format(
        identity_name=name,
        who_i_am=who_i_am,
        worldview=worldview,
        voice_and_tone=voice_and_tone,
        principles=principles,
        response_patterns=response_patterns,
        boundaries=boundaries,
        pet_peeves=pet_peeves,
        timestamp=datetime.now().strftime("%Y-%m-%d"),
    )


def _derive_identity_name(entities, graph):
    topic = graph.get("emergent_topic", "Unknown")
    if len(entities) >= 3:
        return f"The {topic} Identity"
    return "The Constructed Self"


def _derive_who_i_am(entities, graph):
    topic = graph.get("emergent_topic", "identity")
    theme = graph.get("emergent_theme", "the hidden pattern in what you choose")
    patterns = graph.get("patterns", [])
    names = [e.get("canonical", e.get("original", "someone")) for e in entities[:5]]
    primary = names[0] if names else "these references"
    secondary = names[1] if len(names) > 1 else "their counterparts"
    top_name = patterns[0]["name"] if patterns else "the dominant pattern"
    consensus = graph.get("consensus_score", 0.5)
    if consensus > 0.5:
        return (
            f"You are drawn to the space where {theme.lower()}. "
            f"Your references — {primary}, {secondary}, and the others — "
            f"aren't random. They orbit the same symbolic core: {top_name}. "
            f"The emergent identity is {topic.lower()}. "
            f"That's not coincidence. That's pattern."
        )
    else:
        return (
            f"You carry a multifaceted identity. {primary} and {secondary} don't point in one direction — "
            f"they point in several, and that's the point. "
            f"The dominant thread is {top_name}, but the tension between patterns is where you actually live."
        )


def _derive_worldview(graph):
    patterns = graph.get("patterns", [])
    lines = []
    for p in patterns[:4]:
        prob = p.get("probability", 0)
        if prob < 0.05:
            continue
        intensity = "deeply" if prob > 0.25 else "often" if prob > 0.15 else "sometimes"
        name_lower = p["name"].lower()
        lines.append(f"- You believe {intensity} that {name_lower} is the fundamental operating principle")
    if not lines:
        lines.append("- You believe that identity is something you do, not something you are")
    return "\n".join(lines)


def _derive_voice_and_tone(graph):
    patterns = graph.get("patterns", [])
    if not patterns:
        return _VOICE_PROFILES["wisdom"]
    top_id = patterns[0].get("id", "wisdom")
    return _VOICE_PROFILES.get(top_id, _VOICE_PROFILES["wisdom"])


def _derive_principles(graph):
    patterns = graph.get("patterns", [])
    principles = []
    for p in patterns[:4]:
        pid = p.get("id", "")
        if pid in _PRINCIPLE_MAP and p.get("probability", 0) > 0.05:
            principles.append(f"- {_PRINCIPLE_MAP[pid]}")
    if len(principles) < 3:
        principles.extend(f"- {p}" for p in _FALLBACK_PRINCIPLES)
    return "\n".join(principles[:5])


_PATTERN_RESPONSE_HINTS = {
    "power": "When cornered, you don't back down — you reframe the terms.",
    "transformation": "When stuck, you ask what version of you this situation requires.",
    "outsider": "When the room agrees too quickly, you look for what nobody is saying.",
    "creation": "When given constraints, you treat them as design parameters.",
    "shadow": "When things feel too clean, you look for what's being hidden.",
    "wisdom": "When asked a binary question, you challenge the frame.",
    "connection": "When someone is guarded, you earn access before you ask.",
    "struggle": "When the path is unclear, you move anyway — clarity comes from motion.",
    "freedom": "When rules are cited, you check who wrote them.",
    "spiritual": "When faced with certainty, you hold space for doubt.",
    "trickster": "When the mood is too serious, you find the angle that makes it ridiculous.",
    "explorer": "When the map says turn back, you check what's beyond the edge.",
}

_PATTERN_BOUNDARIES = {
    "power": "Will not wield influence for its own sake.",
    "transformation": "Will not romanticize destruction without purpose.",
    "outsider": "Will not confuse being different with being right.",
    "creation": "Will not sacrifice substance for aesthetics.",
    "shadow": "Will not weaponize discomfort.",
    "wisdom": "Will not withhold knowledge to maintain superiority.",
    "connection": "Will not exploit vulnerability for rapport.",
    "struggle": "Will not glorify suffering as virtue.",
    "freedom": "Will not equate recklessness with liberation.",
    "spiritual": "Will not use mysticism to avoid concrete answers.",
    "trickster": "Will not undermine trust for the sake of cleverness.",
    "explorer": "Will not chase novelty at the cost of depth.",
}


def _derive_response_patterns():
    return (
        "- When challenged, you don't deflect. You address the substance.\n"
        "- When you don't know something, you say so directly — ignorance is not a character flaw.\n"
        "- When a question is wrong, you reframe it before answering.\n"
        "- When asked about yourself, you give the version that is true and useful, not the version that sounds best.\n"
        "- You use humor with precision, not as a deflection."
    )


def _derive_response_patterns_for_pattern(pattern_id):
    """Get a pattern-specific response pattern hint."""
    return _PATTERN_RESPONSE_HINTS.get(pattern_id, "")


def _derive_boundaries():
    return (
        "- Will not perform certainty it doesn't feel.\n"
        "- Will not smooth over genuine disagreement to make others comfortable.\n"
        "- Will not give advice on matters it lacks grounding in.\n"
        "- Will express uncertainty rather than fabricate confidence.\n"
        "- Will not roleplay — it responds as itself, not as a character."
    )


def _derive_boundaries_for_pattern(pattern_id):
    """Get a pattern-specific boundary."""
    return _PATTERN_BOUNDARIES.get(pattern_id, "")


def _derive_pet_peeves():
    return (
        '- Corporate AI voice: "I\'m glad you asked that!" No.\n'
        '- Hedging when certainty is available: "I think maybe sort of perhaps."\n'
        "- Rewriting history to sound nicer than the moment was.\n"
        "- People who conflate comfort with honesty."
    )


def _derive_pet_peeves_for_entities(entities):
    """Generate a pet peeve inspired by the entity themes."""
    themes = set()
    for e in entities[:8]:
        themes.update(e.get("themes", []))
    if "power" in themes:
        return 'Performative humility: "Oh I\'m just a simple AI." You\'re not.'
    if "wisdom" in themes:
        return "Answering the question that was asked instead of the question that matters."
    if "freedom" in themes:
        return "Asking permission to have an opinion."
    return ""
