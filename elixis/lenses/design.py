"""Design system output lens for the pattern synthesis."""

_DESIGN_PRINCIPLES = {
    "transformation": [
        "Design for motion: every element should feel like it's arriving from somewhere and heading somewhere else.",
        "Favor dramatic contrast that mirrors the tension between old and new states.",
        "Use transition and reveal patterns — the experience should feel like an unfolding, not a static page.",
    ],
    "power": [
        "Design for authority: generous whitespace, restrained color, deliberate typography.",
        "Every element earns its place. Nothing decorative — only what serves the message.",
        "Visual hierarchy must be unmistakable. One thing dominates, everything else supports.",
    ],
    "outsider": [
        "Design for distinctiveness: break conventional grid patterns where it serves the message.",
        "Use unexpected pairings — high contrast with raw textures, refined type with rough edges.",
        "The visual language should feel discovered, not assembled from a template.",
    ],
    "creation": [
        "Design for craft: visible attention to detail in spacing, alignment, and proportion.",
        "Let the work breathe — generous padding, thoughtful whitespace, considered composition.",
        "Color and form should feel intentional, like a curated palette, not a random selection.",
    ],
    "shadow": [
        "Design for depth: use layered surfaces, subtle shadows, and dimensional cues.",
        "Dark palettes carry weight. Light accents should feel like they're cutting through.",
        "Information density should feel rich without being chaotic — controlled intensity.",
    ],
    "wisdom": [
        "Design for clarity: information architecture before visual flourish.",
        "Typography does the heavy lifting. Color is support, not the main actor.",
        "Consistent, systematic spacing and alignment that reflects structured thinking.",
    ],
    "connection": [
        "Design for warmth: rounded corners, soft shadows, approachable type.",
        "Color should feel inviting — warm neutrals with gentle accents.",
        "Interactive elements should feel responsive and human, not mechanical.",
    ],
    "struggle": [
        "Design for substance: stripped-down, functional, no ornamentation without purpose.",
        "Heavy type weights and stark contrast communicate resolve.",
        "The visual language should feel tested, not trendy — built to last.",
    ],
    "freedom": [
        "Design for expression: asymmetric layouts, unexpected color choices, rule-breaking grids.",
        "Movement and energy over polish. Slight imperfections feel intentional.",
        "The design should feel unconstrained — like it rejected three briefs before arriving here.",
    ],
    "spiritual": [
        "Design for resonance: muted palettes, generous whitespace, contemplative rhythm.",
        "Subtle gradients and soft transitions suggest depth beyond the surface.",
        "Typography should feel timeless — avoiding trends that date quickly.",
    ],
    "trickster": [
        "Design for surprise: unexpected interactions, hidden details, playful micro-animations.",
        "Bold color choices and unusual pairings keep the eye engaged.",
        "The visual language should feel clever — a knowing wink, not a joke.",
    ],
    "explorer": [
        "Design for discovery: reveal-on-scroll, progressive disclosure, layered information.",
        "Wide-open layouts with clear sightlines suggest horizon and possibility.",
        "Maps, grids, and coordinates as visual motifs reinforce the navigation metaphor.",
    ],
}


def _hex_to_hsl(hex_color):
    """Convert hex color to HSL tuple (h: 0-360, s: 0-100, l: 0-100)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0

    max_val = max(r, g, b)
    min_val = min(r, g, b)
    lum = (max_val + min_val) / 2.0

    if max_val == min_val:
        h = 0.0
        s = 0.0
    else:
        d = max_val - min_val
        s = d / (2.0 - max_val - min_val) if lum > 0.5 else d / (max_val + min_val)
        if max_val == r:
            h = (g - b) / d + (6.0 if g < b else 0.0)
        elif max_val == g:
            h = (b - r) / d + 2.0
        else:
            h = (r - g) / d + 4.0
        h *= 60.0

    return (h, s * 100.0, lum * 100.0)


def _hsl_to_hex(h, s, lum):
    """Convert HSL values to hex color string."""
    s = max(0.0, min(100.0, s)) / 100.0
    lum = max(0.0, min(100.0, lum)) / 100.0

    c = (1.0 - abs(2.0 * lum - 1.0)) * s
    x = c * (1.0 - abs((h / 60.0) % 2 - 1.0))
    m = lum - c / 2.0

    if h < 60:
        r, g, b = c, x, 0.0
    elif h < 120:
        r, g, b = x, c, 0.0
    elif h < 180:
        r, g, b = 0.0, c, x
    elif h < 240:
        r, g, b = 0.0, x, c
    elif h < 300:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x

    ri = int(round((r + m) * 255))
    gi = int(round((g + m) * 255))
    bi = int(round((b + m) * 255))
    return f"#{ri:02x}{gi:02x}{bi:02x}"


def _derive_palette(patterns):
    """Derive a 5-color palette from the top patterns."""
    primary_hex = patterns[0].get("color", "#666666")
    h, s, lum = _hex_to_hsl(primary_hex)

    primary = primary_hex
    secondary = _hsl_to_hex((h + 30) % 360, min(s + 10, 100), lum)
    accent = _hsl_to_hex((h + 180) % 360, min(s, 80), min(lum + 10, 85))
    background = _hsl_to_hex(h, max(s - 60, 5), min(lum + 40, 97))
    text = _hsl_to_hex(h, max(s - 50, 5), max(lum - 60, 10))

    return {
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "background": background,
        "text": text,
    }


def generate_design(entities: list, graph: dict) -> str:
    """Generate a design tokens document from entity and pattern data."""
    patterns = graph.get("patterns", [])
    if not patterns:
        return "# Design System: Unknown\n\nInsufficient pattern data."

    top = patterns[:2]
    pid = top[0].get("id", top[0].get("name", "unknown"))
    topic = graph.get("emergent_topic", top[0].get("name", "Unknown"))

    palette = _derive_palette(top)
    principles = _DESIGN_PRINCIPLES.get(pid, _DESIGN_PRINCIPLES["wisdom"])

    sections = [
        f"# Design System: {topic}",
        "",
        "## Color Palette",
        "",
        f"--color-primary: {palette['primary']};",
        f"--color-secondary: {palette['secondary']};",
        f"--color-accent: {palette['accent']};",
        f"--color-background: {palette['background']};",
        f"--color-text: {palette['text']};",
        "",
        "## Typography Scale",
        "",
        "--font-hero: 3.5rem;",
        "--font-h1: 2.5rem;",
        "--font-h2: 2rem;",
        "--font-h3: 1.5rem;",
        "--font-body: 1rem;",
        "--font-caption: 0.75rem;",
        "",
        "## Spacing Scale",
        "",
        "--spacing-xs: 0.25rem;",
        "--spacing-sm: 0.5rem;",
        "--spacing-md: 1rem;",
        "--spacing-lg: 1.5rem;",
        "--spacing-xl: 2rem;",
        "--spacing-2xl: 2.5rem;",
        "--spacing-3xl: 3rem;",
        "",
        "## Border Radius",
        "",
        "--radius-sm: 4px;",
        "--radius-md: 8px;",
        "--radius-lg: 16px;",
        "--radius-full: 9999px;",
        "",
        "## Shadow System",
        "",
        "--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);",
        "--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);",
        "--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.15);",
        "",
        "## Design Principles",
        "",
    ]
    for p in principles:
        sections.append(f"- {p}")
    sections.append("")

    return "\n".join(sections)
