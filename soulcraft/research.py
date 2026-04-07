"""Web enrichment for extracted entities.

Uses Wikipedia REST API to fetch summaries and extract additional
themes/traits for each entity. Gracefully degrades when offline.
"""

import json
import re
import urllib.request
import urllib.error

_WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"
_TIMEOUT = 4  # seconds per request
_MAX_ENTITIES = 15


def _wiki_summary(title):
    """Fetch a Wikipedia summary for a title. Returns empty string on failure."""
    # Clean the title for URL
    slug = re.sub(r'\s+', '_', title.strip())
    slug = re.sub(r'[^\w(),.\-]', '', slug)
    if not slug:
        return ""

    url = _WIKI_API + urllib.request.quote(slug, safe='')
    req = urllib.request.Request(url, headers={
        "User-Agent": "Soulcraft/1.0 (https://github.com/KyaniteLabs/SoulCraft)",
        "Accept": "application/json",
    })

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read())
            extract = data.get("extract", "")
            if extract and len(extract) > 20:
                return extract
            return ""
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
        return ""


# Theme keywords mapped to pattern vocabulary
_THEME_KEYWORDS = {
    "power": ["power", "control", "dominance", "authority", "rule", "command", "leader", "boss", "king", "emperor", "tyrant", "ambition", "rise to power"],
    "transformation": ["transform", "rebirth", "change", "become", "evolve", "reinvent", "metamorphosis", "resurrection", "ascension", "redemption"],
    "outsider": ["outsider", "outcast", "marginal", "alienat", "reject", "exile", "fringe", "misfit", "renegade", "rogue", "rebel"],
    "creation": ["creat", "art", "craft", "build", "design", "compose", "make", "invent", "innovate", "masterpiece", "work of art"],
    "shadow": ["dark", "shadow", "hidden", "secret", "sinister", "evil", "villain", "corrupt", "psychopath", "serial killer", "crime", "murder"],
    "wisdom": ["wisdom", "knowledge", "intellect", "brilliant", "genius", "philosoph", "sage", "scholar", "analyt", "strateg", "detective"],
    "connection": ["connect", "love", "bond", "relationship", "family", "friend", "loyal", "trust", "belong", "community", "together"],
    "struggle": ["struggle", "suffer", "hardship", "adversity", "pain", "loss", "survive", "endure", "poverty", "oppression", "fight", "resist"],
    "freedom": ["freedom", "liberat", "independen", "autonomy", "free", "escape", "break free", "revolt", "anarchy", "anti-establishment"],
    "spiritual": ["spirit", "sacred", "divine", "holy", "mystic", "transcend", "soul", "faith", "ritual", "myth", "archetyp"],
    "trickster": ["trick", "deceiv", "manipulat", "con artist", "grifter", "charm", "wit", "humor", "cunning", "clever", "scam", "lie"],
    "explorer": ["explor", "discover", "journey", "adventure", "quest", "frontier", "unknown", "wander", "travel", "expedition"],
}


def _extract_themes_from_text(text):
    """Extract pattern-relevant themes from a text string."""
    text_lower = text.lower()
    found = set()
    for theme, keywords in _THEME_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                found.add(theme)
                break
    return sorted(found)


def enrich_entities(entities):
    """Enrich entity list with Wikipedia summaries and extracted themes.

    Modifies entities in place. Gracefully skips entities that can't be
    enriched. Returns the same list (mutated).

    Args:
        entities: list of entity dicts from extract_entities()

    Returns:
        The same list, with 'description' and 'themes' updated where possible.
    """
    if not entities:
        return entities

    for entity in entities[:_MAX_ENTITIES]:
        name = entity.get("canonical", "")
        if not name:
            continue

        summary = _wiki_summary(name)

        # If direct name fails, try "Name (source)" format
        if not summary and entity.get("source"):
            summary = _wiki_summary(f"{name} ({entity['source']})")

        # If still no luck, try the source itself
        if not summary and entity.get("source"):
            summary = _wiki_summary(entity["source"])

        if summary:
            entity["description"] = summary
            # Merge wiki-found themes with existing ones
            wiki_themes = _extract_themes_from_text(summary)
            existing = set(entity.get("themes", []))
            merged = existing | set(wiki_themes)
            if merged:
                entity["themes"] = sorted(merged)

        # Also extract themes from traits if not already present
        existing_themes = set(entity.get("themes", []))
        traits_text = " ".join(entity.get("traits", []))
        if traits_text:
            trait_themes = _extract_themes_from_text(traits_text)
            merged = existing_themes | set(trait_themes)
            if merged:
                entity["themes"] = sorted(merged)

    return entities
