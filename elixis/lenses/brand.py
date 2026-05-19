"""Brand voice output lens for the pattern synthesis."""

_TONE_MAP = {
    "transformation": ("bold", "direct", "accessible", "warm"),
    "power": ("formal", "bold", "technical", "direct"),
    "outsider": ("casual", "bold", "accessible", "direct"),
    "creation": ("casual", "cautious", "accessible", "warm"),
    "shadow": ("formal", "bold", "technical", "direct"),
    "wisdom": ("formal", "cautious", "technical", "warm"),
    "connection": ("casual", "cautious", "accessible", "warm"),
    "struggle": ("formal", "bold", "accessible", "direct"),
    "freedom": ("casual", "bold", "accessible", "direct"),
    "spiritual": ("formal", "cautious", "accessible", "warm"),
    "trickster": ("casual", "bold", "accessible", "warm"),
    "explorer": ("casual", "bold", "accessible", "direct"),
}

_IDENTITY_TEMPLATES = {
    "transformation": (
        "A brand built on the premise that change is the only constant. "
        "It stands for reinvention, growth, and the courage to shed old skins. "
        "Every message carries the energy of becoming."
    ),
    "power": (
        "A brand that commands attention through authority and precision. "
        "It stands for mastery, legacy, and the relentless pursuit of excellence. "
        "Every message carries the weight of conviction."
    ),
    "outsider": (
        "A brand born on the margins, proud of its distance from the mainstream. "
        "It stands for independence, sharp observation, and the willingness to see what others miss. "
        "Every message carries the clarity of an outside perspective."
    ),
    "creation": (
        "A brand defined by craft and imagination. "
        "It stands for originality, attention to detail, and the belief that beauty is a form of truth. "
        "Every message carries a maker's intentionality."
    ),
    "shadow": (
        "A brand that embraces complexity without flinching. "
        "It stands for honesty about the uncomfortable, depth over surface, and the refusal to simplify what shouldn't be. "
        "Every message carries gravity without drama."
    ),
    "wisdom": (
        "A brand rooted in understanding and insight. "
        "It stands for clarity of thought, systems thinking, and the discipline of knowing when to speak. "
        "Every message carries the weight of considered perspective."
    ),
    "connection": (
        "A brand built on the power of genuine relationships. "
        "It stands for loyalty, emotional intelligence, and the belief that belonging is earned, not assumed. "
        "Every message carries warmth without performance."
    ),
    "struggle": (
        "A brand forged through adversity. "
        "It stands for resilience, earned strength, and the quiet confidence that comes from surviving. "
        "Every message carries the authority of experience."
    ),
    "freedom": (
        "A brand defined by autonomy and defiance. "
        "It stands for self-determination, breaking constraints, and choosing your own terms. "
        "Every message carries the energy of liberation."
    ),
    "spiritual": (
        "A brand that bridges the material and the transcendent. "
        "It stands for depth, contemplation, and the pursuit of meaning beyond the obvious. "
        "Every message carries resonance without pretension."
    ),
    "trickster": (
        "A brand that uses wit as a weapon and a mirror. "
        "It stands for subversion, cleverness, and the belief that humor reveals what seriousness obscures. "
        "Every message carries a point beneath the playfulness."
    ),
    "explorer": (
        "A brand driven by curiosity and the unknown. "
        "It stands for discovery, pushing boundaries, and the conviction that the best answers come from asking better questions. "
        "Every message carries the thrill of the unmapped."
    ),
}

_VOCABULARY_MAP = {
    "transformation": ["evolve", "become", "reinvent", "emerge", "transcend", "metamorphosis", "awaken", "ascend", "rebirth", "shed"],
    "power": ["command", "legacy", "master", "triumph", "dominion", "authority", "conquer", "empire", "sovereign", "will"],
    "outsider": ["marginal", "defiant", "observe", "renegade", "unbound", "independent", "fringe", "dissent", "unconventional", "edgewise"],
    "creation": ["craft", "envision", "forge", "original", "compose", "aesthetic", "invent", "inspire", "artistry", "imagine"],
    "shadow": ["depth", "unflinching", "complexity", "gravity", "reckoning", "subtext", "hidden", "unvarnished", "raw", "authentic"],
    "wisdom": ["insight", "clarity", "discern", "framework", "precision", "understanding", "analyze", "calibrate", "reason", "contemplate"],
    "connection": ["belong", "loyal", "fierce", "kinship", "genuine", "together", "anchor", "heartfelt", "bond", "trust"],
    "struggle": ["endure", "resilient", "forge", "withstand", "grit", "unyielding", "persevere", "earned", "unbroken", "resolve"],
    "freedom": ["liberate", "unbound", "autonomy", "defy", "unfettered", "sovereign", "revolt", "unchained", "wild", "untamed"],
    "spiritual": ["transcend", "sacred", "infinite", "contemplate", "resonance", "mystical", "destiny", "eternal", "destiny", "reverence"],
    "trickster": ["subvert", "clever", "disrupt", "irreverent", "wit", "paradox", "absurdity", "unmask", "provoke", "deft"],
    "explorer": ["discover", "frontier", "uncharted", "navigate", "venture", "horizon", "expedition", "wander", "territory", "pioneer"],
}

_ANTI_VOCABULARY_MAP = {
    "transformation": ["stay the same", "that's just how it is", "good enough", "settle", "maintain the status quo"],
    "power": ["humble brag", "almost", "maybe later", "we'll see", "good effort"],
    "outsider": ["fit in", "play it safe", "blend in", "everyone's doing it", "conventional wisdom"],
    "creation": ["good enough for government work", "ship it and forget", "that'll do", "overthinking it", "nobody will notice"],
    "shadow": ["look on the bright side", "it's fine", "sweep it under", "positive vibes only", "don't overthink it"],
    "wisdom": ["trust your gut", "everyone's entitled to their opinion", "it's complicated", "who can really say", "close enough"],
    "connection": ["self-made", "go it alone", "not my problem", "keep it professional", "boundary issues"],
    "struggle": ["easy win", "natural talent", "overnight success", "blessed", "gifted"],
    "freedom": ["stay in your lane", "know your place", "permission", "follow the rules", "because we've always done it this way"],
    "spiritual": ["just vibes", "it is what it is", "too deep", "overthinking", "who cares about meaning"],
    "trickster": ["serious business", "no room for humor", "that's not funny", "stick to the script", "inappropriate"],
    "explorer": ["stay put", "good enough here", "why bother", "too risky", "map says no"],
}

_FONT_MAP = {
    "transformation": ("DM Sans", "Playfair Display"),
    "power": ("Inter", "Helvetica Neue"),
    "outsider": ("Space Grotesk", "JetBrains Mono"),
    "creation": ("Cormorant Garamond", "Nunito"),
    "shadow": ("Bitter", "IBM Plex Serif"),
    "wisdom": ("Source Serif Pro", "Libre Baskerville"),
    "connection": ("Lora", "Karla"),
    "struggle": ("Oswald", "Roboto Condensed"),
    "freedom": ("Space Mono", "Architects Daughter"),
    "spiritual": ("Cormorant", "Cinzel"),
    "trickster": ("Baloo 2", "Bangers"),
    "explorer": ("Exo 2", "Rajdhani"),
}

_TONE_TABLE = {
    "social media": {
        "transformation": ("Provocative and forward-looking", "\"The old you called. It wants its limits back.\""),
        "power": ("Confident and commanding", "\"We don't follow markets. We redefine them.\""),
        "outsider": ("Wry and observational", "\"While everyone zigged, we found a third direction.\""),
        "creation": ("Inspirational and tactile", "\"Made by hand. Approved by obsession.\""),
        "shadow": ("Direct and unflinching", "\"Comfortable lies sell. We don't.\""),
        "wisdom": ("Measured and insightful", "\"The real question isn't what to think. It's how.\""),
        "connection": ("Warm and genuine", "\"This isn't a community. It's a chosen family.\""),
        "struggle": ("Grounded and resolute", "\"Earned. Not given. Never borrowed.\""),
        "freedom": ("Defiant and electric", "\"Rules are suggestions for people without imagination.\""),
        "spiritual": ("Contemplative and expansive", "\"What if the answer isn't a destination but a direction?\""),
        "trickster": ("Playful and pointed", "\"Serious people built the Titanic. A trickster built the lifeboats.\""),
        "explorer": ("Curious and bold", "\"The edge of the map is where the best stories start.\""),
    },
    "website": {
        "transformation": ("Visionary and clear", "\"We build what comes next.\""),
        "power": ("Authoritative and precise", "\"Performance through conviction.\""),
        "outsider": ("Distinctive and sharp", "\"Built from the outside in.\""),
        "creation": ("Elegant and purposeful", "\"Where craft meets conviction.\""),
        "shadow": ("Honest and compelling", "\"We show what others hide.\""),
        "wisdom": ("Clear and structured", "\"Insight, not information.\""),
        "connection": ("Inviting and real", "\"Built for people who show up.\""),
        "struggle": ("Solid and earned", "\"Strength through experience.\""),
        "freedom": ("Bold and unapologetic", "\"Designed without permission.\""),
        "spiritual": ("Expansive and resonant", "\"Beyond the surface.\""),
        "trickster": ("Clever and engaging", "\"Smart enough to know better. Bold enough anyway.\""),
        "explorer": ("Open and adventurous", "\"The frontier starts here.\""),
    },
    "email": {
        "transformation": ("Direct and personal", "\"Ready for what's next? So are we.\""),
        "power": ("Concise and impactful", "\"Here's what matters this week.\""),
        "outsider": ("Conversational and sharp", "\"Something you won't hear elsewhere.\""),
        "creation": ("Thoughtful and detailed", "\"A closer look at what we're building.\""),
        "shadow": ("Candid and substantial", "\"No spin. Here's the reality.\""),
        "wisdom": ("Informative and considered", "\"Context you won't find anywhere else.\""),
        "connection": ("Personal and warm", "\"We noticed. We care. Here's why.\""),
        "struggle": ("Honest and grounded", "\"Real progress, measured in real terms.\""),
        "freedom": ("Unfiltered and real", "\"Uncut. Unfiltered. Unmissable.\""),
        "spiritual": ("Reflective and generous", "\"Something to sit with this week.\""),
        "trickster": ("Unexpected and memorable", "\"You didn't expect this in your inbox.\""),
        "explorer": ("Inviting and curious", "\"Something new to discover inside.\""),
    },
    "press": {
        "transformation": ("Strategic and forward-looking", "\"Announcing the next chapter.\""),
        "power": ("Formal and decisive", "\"Setting the standard, again.\""),
        "outsider": ("Bold and differentiated", "\"Not another announcement. A departure.\""),
        "creation": ("Polished and visionary", "\"Introducing what craftsmanship looks like now.\""),
        "shadow": ("Transparent and direct", "\"We're addressing what others won't.\""),
        "wisdom": ("Authoritative and data-driven", "\"The analysis that changes the conversation.\""),
        "connection": ("Community-focused and genuine", "\"Built with the people who matter most.\""),
        "struggle": ("Resilient and matter-of-fact", "\"Progress isn't always pretty. Here's ours.\""),
        "freedom": ("Independent and principled", "\"No board approval needed for this.\""),
        "spiritual": ("Purposeful and elevated", "\"Why we do what we do.\""),
        "trickster": ("Unconventional and quotable", "\"Breaking news: we did something unexpected.\""),
        "explorer": ("Pioneering and credible", "\"First to map this territory.\""),
    },
    "crisis": {
        "transformation": ("Calm and solutions-oriented", "\"We've identified the path forward.\""),
        "power": ("Firm and accountable", "\"Here's exactly what happened and what we're doing.\""),
        "outsider": ("Honest and direct", "\"No corporate spin. Here's the situation.\""),
        "creation": ("Transparent and constructive", "\"What broke, why, and how we're fixing it.\""),
        "shadow": ("Unflinching and responsible", "\"We won't minimize this. Here's the full picture.\""),
        "wisdom": ("Measured and thorough", "\"Context, cause, and correction.\""),
        "connection": ("Empathetic and clear", "\"We hear you. Here's what we're doing about it.\""),
        "struggle": ("Steady and resolute", "\"We've been through worse. We'll earn our way through this.\""),
        "freedom": ("Direct and unscripted", "\"No PR filter. Here's where we stand.\""),
        "spiritual": ("Grounded and humane", "\"People first. Everything else follows.\""),
        "trickster": ("Honest with appropriate restraint", "\"We messed up. Here's the fix, not the excuse.\""),
        "explorer": ("Adaptable and transparent", "\"New territory. We're learning out loud.\""),
    },
}

_STYLE_ALIASES = {
    "caregiver": "connection",
    "sage": "wisdom",
    "achiever": "power",
    "loyalist": "connection",
    "enthusiast": "freedom",
    "challenger": "power",
    "peacemaker": "connection",
    "reformer": "wisdom",
    "herald": "explorer",
    "guardian": "connection",
    "shapeshifter": "transformation",
    "mentor": "wisdom",
}

_IDENTITY_TEMPLATES.update({
    "caregiver": (
        "A brand built around care as a disciplined practice. It stands for protection, "
        "repair, and the quiet work of making people feel held. Every message carries "
        "warmth with a spine."
    ),
    "sage": (
        "A brand devoted to discernment. It stands for patient understanding, clean "
        "models, and the courage to name what is true before it is popular. Every "
        "message carries earned clarity."
    ),
    "achiever": (
        "A brand organized around progress and standards. It stands for competence, "
        "momentum, and the satisfaction of measurable excellence. Every message carries "
        "forward motion."
    ),
    "loyalist": (
        "A brand grounded in commitment. It stands for trust, preparedness, and showing "
        "up when consistency matters most. Every message carries dependable presence."
    ),
    "enthusiast": (
        "A brand animated by possibility. It stands for curiosity, range, and the joy of "
        "finding another door to open. Every message carries contagious momentum."
    ),
    "challenger": (
        "A brand that protects by confronting. It stands for decisive action, strength in "
        "the open, and the refusal to outsource courage. Every message carries force "
        "under control."
    ),
    "peacemaker": (
        "A brand that turns tension into coherence. It stands for steadiness, mediation, "
        "and calm that does real work. Every message carries ease without avoidance."
    ),
    "reformer": (
        "A brand built on principled improvement. It stands for order, precision, and "
        "making the system worthy of the people inside it. Every message carries exacting "
        "care."
    ),
    "herald": (
        "A brand that signals the next threshold. It stands for clarity of invitation, "
        "timely revelation, and the call that makes action possible. Every message carries "
        "arrival."
    ),
    "guardian": (
        "A brand that makes trust visible. It stands for protection, boundaries, and "
        "stewardship without paranoia. Every message carries watchful calm."
    ),
    "shapeshifter": (
        "A brand fluent in change. It stands for adaptation, translation, and the ability "
        "to hold multiple truths without losing form. Every message carries elegant motion."
    ),
    "mentor": (
        "A brand that guides without grandstanding. It stands for experience, patience, "
        "and useful wisdom passed hand to hand. Every message carries generous authority."
    ),
})

_VOCABULARY_MAP.update({
    "caregiver": ["care", "repair", "shelter", "nourish", "protect", "tend", "restore", "hold", "comfort", "devotion"],
    "sage": ["discern", "clarify", "study", "counsel", "truth", "model", "context", "reason", "depth", "insight"],
    "achiever": ["progress", "standard", "momentum", "mastery", "measure", "execute", "advance", "competence", "finish", "earn"],
    "loyalist": ["trust", "steady", "prepared", "reliable", "covenant", "commit", "anchor", "defend", "vigilant", "faithful"],
    "enthusiast": ["possibility", "range", "spark", "discover", "momentum", "joy", "open", "wonder", "alive", "next"],
    "challenger": ["force", "confront", "protect", "decide", "command", "direct", "fierce", "boundary", "stand", "resolve"],
    "peacemaker": ["steady", "harmonize", "mediate", "ease", "balance", "listen", "settle", "calm", "reconcile", "cohere"],
    "reformer": ["clarity", "standard", "precision", "order", "principle", "improve", "correct", "system", "discipline", "integrity"],
    "herald": ["signal", "announce", "call", "threshold", "message", "reveal", "summon", "arrive", "declare", "awake"],
    "guardian": ["protect", "steward", "boundary", "watch", "safeguard", "preserve", "custody", "shield", "haven", "trust"],
    "shapeshifter": ["adapt", "translate", "fluid", "mirror", "shift", "form", "motion", "versatile", "bridge", "transform"],
    "mentor": ["guide", "teach", "prepare", "counsel", "practice", "legacy", "experience", "patience", "support", "wisdom"],
})

_ANTI_VOCABULARY_MAP.update({
    "caregiver": ["not my problem", "sink or swim", "perform empathy", "soft enough", "ignore the wound"],
    "sage": ["trust the vibes", "close enough", "nobody reads context", "hot take", "obviously"],
    "achiever": ["someday", "good intentions", "activity theater", "almost done", "busy work"],
    "loyalist": ["fair-weather", "figure it out alone", "unreliable by design", "maybe later", "not my lane"],
    "enthusiast": ["nothing new here", "stay bored", "too much curiosity", "that's excessive", "kill the spark"],
    "challenger": ["let it slide", "avoid the hard thing", "looks strong enough", "permission first", "soft no"],
    "peacemaker": ["keep everyone comfortable", "avoid the conflict", "false harmony", "don't name it", "smooth it over"],
    "reformer": ["good enough", "messy is fine", "standards are optional", "nobody will notice", "ship the slop"],
    "herald": ["bury the lead", "maybe mention it", "signal later", "unclear ask", "soft launch forever"],
    "guardian": ["trust me blindly", "leave it exposed", "security theater", "boundaryless", "who's watching"],
    "shapeshifter": ["pick one forever", "never adapt", "rigid identity", "context doesn't matter", "same answer everywhere"],
    "mentor": ["because I said so", "figure it out", "perform expertise", "gatekeep", "lesson learned?"],
})

_FONT_MAP.update({
    "caregiver": ("Lora", "Nunito"),
    "sage": ("Source Serif Pro", "Inter"),
    "achiever": ("Inter Tight", "Inter"),
    "loyalist": ("IBM Plex Sans", "Karla"),
    "enthusiast": ("Fraunces", "Nunito"),
    "challenger": ("Oswald", "Inter"),
    "peacemaker": ("Lora", "Karla"),
    "reformer": ("Source Sans 3", "IBM Plex Mono"),
    "herald": ("Cinzel", "Inter"),
    "guardian": ("Libre Baskerville", "IBM Plex Sans"),
    "shapeshifter": ("Space Grotesk", "Inter"),
    "mentor": ("Source Serif Pro", "Karla"),
})


def _style_key(pattern_id):
    return pattern_id if pattern_id in _IDENTITY_TEMPLATES else _STYLE_ALIASES.get(pattern_id, "wisdom")


def _tone_style_key(pattern_id):
    return _STYLE_ALIASES.get(pattern_id, pattern_id if pattern_id in _TONE_MAP else "wisdom")


def _format_anchor(entity):
    name = entity.get("canonical") or entity.get("name") or entity.get("original") or "Unknown"
    themes = entity.get("themes") or []
    traits = entity.get("traits") or []
    context = ", ".join([*themes[:3], *traits[:1]])
    return f"- **{name}**" + (f": {context}" if context else "")


def _pattern_rationale(patterns, graph):
    lines = []
    for p in patterns[:4]:
        name = p.get("name", "Unknown")
        prob = p.get("probability")
        support = p.get("supporting_entities", 0)
        if isinstance(prob, (int, float)):
            lines.append(f"- **{name}**: {prob:.0%} probability across {support} supporting entities")
        else:
            lines.append(f"- **{name}**: {support} supporting entities")
    for bridge in graph.get("bridges", [])[:2]:
        lines.append(
            f"- **Bridge**: {bridge.get('entity')} connects {bridge.get('pattern_a')} "
            f"and {bridge.get('pattern_b')}"
        )
    return lines


def generate_brand(entities: list, graph: dict) -> str:
    """Generate a brand voice guidelines document from entity and pattern data."""
    patterns = graph.get("patterns", [])
    if not patterns:
        return "# Brand Voice: Unknown\n\nInsufficient pattern data."

    top = patterns[:3]
    primary = top[0]
    pid = primary.get("id", primary.get("name", "unknown"))
    style = _style_key(pid)
    tone_style = _tone_style_key(pid)
    topic = graph.get("emergent_topic", primary.get("name", "Unknown"))
    tones = _TONE_MAP.get(tone_style, ("formal", "bold", "accessible", "direct"))

    # Core Identity
    identity = _IDENTITY_TEMPLATES.get(style, _IDENTITY_TEMPLATES["wisdom"])

    # Voice Attributes
    voice_lines = [
        f"- **Formality**: {_tones_formal(tones[0])}",
        f"- **Boldness**: {_tones_bold(tones[1])}",
        f"- **Technical Level**: {_tones_tech(tones[2])}",
        f"- **Warmth**: {_tones_warm(tones[3])}",
    ]

    # Tone Spectrum
    tone_situations = ["social media", "website", "email", "press", "crisis"]
    tone_rows = []
    for situation in tone_situations:
        mapping = _TONE_TABLE.get(situation, {})
        entry = mapping.get(tone_style, mapping.get("wisdom", ("Measured", "\"...\"")))
        tone_rows.append(f"| {situation.title()} | {entry[0]} | {entry[1]} |")
    tone_table = "| Situation | Tone | Example |\n|---|---|---|\n" + "\n".join(tone_rows)

    # Vocabulary
    vocab = _VOCABULARY_MAP.get(style, _VOCABULARY_MAP["wisdom"])[:10]

    # Anti-Vocabulary
    anti_vocab = _ANTI_VOCABULARY_MAP.get(style, _ANTI_VOCABULARY_MAP["wisdom"])[:5]

    # Color Direction
    colors = []
    for p in top:
        colors.append(p.get("color", "#666666"))

    # Typography
    fonts = _FONT_MAP.get(style, _FONT_MAP["wisdom"])

    sections = [
        f"# Brand Voice: {topic}",
        "",
        "## Source Anchors",
        "",
    ]
    anchors = [_format_anchor(e) for e in entities[:8]]
    sections.extend(anchors or ["- No source anchors available."])
    sections.extend([
        "",
        "## Pattern Rationale",
        "",
    ])
    sections.extend(_pattern_rationale(patterns, graph))
    sections.extend([
        "",
        "## Core Identity",
        "",
        identity,
        "",
        "## Voice Attributes",
        "",
    ])
    sections.extend(voice_lines)
    sections.extend([
        "",
        "## Tone Spectrum",
        "",
        tone_table,
        "",
        "## Vocabulary",
        "",
    ])
    sections.extend(f"- {w}" for w in vocab)
    sections.extend([
        "",
        "## Anti-Vocabulary",
        "",
    ])
    sections.extend(f"- {w}" for w in anti_vocab)
    sections.extend([
        "",
        "## Color Direction",
        "",
    ])
    for i, c in enumerate(colors):
        label = ["Primary", "Secondary", "Tertiary"][i] if i < 3 else f"Color {i+1}"
        sections.append(f"- **{label}**: `{c}`")
    sections.extend([
        "",
        "## Typography Suggestion",
        "",
        f"- **Headings**: {fonts[0]}",
        f"- **Body**: {fonts[1]}",
    ])
    sections.append("")

    return "\n".join(sections)


def _tones_formal(val):
    return "Formal and structured" if val == "formal" else "Casual and conversational"


def _tones_bold(val):
    return "Bold and assertive" if val == "bold" else "Cautious and measured"


def _tones_tech(val):
    return "Technical and precise" if val == "technical" else "Accessible and plain-spoken"


def _tones_warm(val):
    return "Warm and empathetic" if val == "warm" else "Direct and no-nonsense"
