"""Web enrichment for extracted entities.

Uses Wikipedia REST API to fetch summaries and extract additional
themes/traits for each entity. Gracefully degrades when offline.
"""

import json
import logging
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("soulcraft.research")

_WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"
_TIMEOUT = 4  # seconds per request
_MAX_ENTITIES = 15


def _wiki_summary(title):
    """Fetch a Wikipedia summary for a title. Returns empty string on failure."""
    slug = re.sub(r'\s+', '_', title.strip())
    if not slug:
        return ""

    url = _WIKI_API + urllib.request.quote(slug, safe='()')
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
    "caregiver": ["care", "nurtur", "protect", "heal", "comfort", "compassion", "generous", "selfless", "devot", "shelter"],
    "sage": ["sage", "teach", "learn", "study", "contemplat", "insight", "enlighten", "guid", "mentor", "counsel"],
    "achiever": ["achieve", "succee", "accomplish", "goal", "drive", "ambit", "excel", "perform", "win", "productiv"],
    "loyalist": ["loyal", "faithful", "devote", "allegian", "commit", "depend", "reliable", "steadfast", "trustworth"],
    "enthusiast": ["enthusias", "excit", "adventur", "optimis", "spontaneous", "versatil", "curious", "variety", "experience"],
    "challenger": ["challeng", "confront", "assert", "domineer", "strong-will", "decisiv", "protector", "intense", "powerful"],
    "peacemaker": ["peace", "harmon", "mediat", "diplomat", "calm", "unify", "reconcil", "accommodat", "gentle"],
    "reformer": ["reform", "improv", "perfect", "principle", "moral", "ethic", "standard", "discipline", "integrity", "righteous"],
    "chaos": ["chaos", "disorder", "anarchy", "turmoil", "havoc", "entropy", "disrupt", "unpredict", "catastroph"],
    "destruction": ["destroy", "destruct", "devastat", "annihilat", "ruin", "wreck", "obliterat", "shatter", "demolish"],
    "honor": ["honor", "honour", "dignity", "respect", "integri", "nobility", "chivalr", "virtue", "code"],
    "justice": ["justice", "fair", "equit", "right", "lawful", "legitimat", "morality", "accountab", "consequence"],
    "loyalty": ["loyalty", "allegian", "devotion", "faithfulness", "commit", "stand by", "solidarity"],
    "mentor": ["mentor", "guide", "tutor", "coach", "advis", "instruc", "wisdom figure", "teacher"],
    "survival": ["survival", "surviv", "endur", "persever", "persist", "resilien", "adapt", "withstand", "overcome"],
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


_WIKI_SPARQL = "https://query.wikidata.org/sparql"
_SPARQL_TIMEOUT = 8


def _wikidata_lookup(name):
    """Query Wikidata for structured entity data. Returns dict or None."""
    safe_name = name.replace('"', '\\"')
    query = f"""SELECT ?item ?itemDescription (GROUP_CONCAT(DISTINCT ?typeLabel; separator=", ") AS ?types) WHERE {{
  ?item rdfs:label "{safe_name}"@en .
  ?item wdt:P31 ?type .
  ?type rdfs:label ?typeLabel . FILTER(LANG(?typeLabel) = "en")
  OPTIONAL {{ ?item schema:description ?itemDescription . FILTER(LANG(?itemDescription) = "en") }}
  FILTER EXISTS {{
    ?item wdt:P31 ?t .
    VALUES ?t {{ wd:Q5 wd:Q95074 wd:Q15632617 wd:Q11424 wd:Q5398426 }}
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}} GROUP BY ?item ?itemDescription LIMIT 3"""
    params = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(
        _WIKI_SPARQL,
        data=params,
        headers={
            "User-Agent": "Soulcraft/1.0 (https://github.com/KyaniteLabs/SoulCraft)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_SPARQL_TIMEOUT) as resp:
            data = json.loads(resp.read())
            results = data.get("results", {}).get("bindings", [])
            if not results:
                return None
            best = results[0]
            description = best.get("itemDescription", {}).get("value", "")
            types_str = best.get("types", {}).get("value", "")
            types = [t.strip() for t in types_str.split(",") if t.strip()] if types_str else []
            return {"description": description, "types": types[:3]}
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError, TimeoutError):
        return None


def _enrich_single(entity):
    """Fetch Wikipedia summary for one entity. Falls back to Wikidata."""
    name = entity.get("canonical", "")
    if not name:
        return ""

    summary = _wiki_summary(name)

    if not summary and entity.get("source"):
        summary = _wiki_summary(f"{name} ({entity['source']})")

    if not summary and entity.get("source"):
        summary = _wiki_summary(entity["source"])

    # Wikidata fallback for structured data
    if not summary:
        wd = _wikidata_lookup(name)
        if wd and wd.get("description"):
            return wd["description"]

    return summary


def enrich_entities(entities, telemetry=None):
    """Enrich entity list with Wikipedia summaries and extracted themes.

    Returns a new list with enriched copies. Does not mutate the input.

    Args:
        entities: list of entity dicts from extract_entities()
        telemetry: optional dict to populate with enrichment metrics

    Returns:
        New list with 'description' and 'themes' updated where possible.
    """
    if not entities:
        if telemetry is not None:
            telemetry["source"] = "empty_input"
        return entities

    t0 = time.time()
    batch = entities[:_MAX_ENTITIES]
    enriched = [dict(e) for e in entities]

    success_count = 0
    fail_count = 0
    timeout_hit = False

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_enrich_single, entity): i for i, entity in enumerate(batch)}
        try:
            for future in as_completed(futures, timeout=30):
                idx = futures[future]
                entity = enriched[idx]
                try:
                    summary = future.result()
                except Exception:
                    summary = ""
                    fail_count += 1

                if summary:
                    success_count += 1
                    entity["description"] = summary
                    wiki_themes = _extract_themes_from_text(summary)
                    existing = set(entity.get("themes", []))
                    merged = existing | set(wiki_themes)
                    if merged:
                        entity["themes"] = sorted(merged)
                else:
                    fail_count += 1

                existing_themes = set(entity.get("themes", []))
                traits_text = " ".join(entity.get("traits", []))
                if traits_text:
                    trait_themes = _extract_themes_from_text(traits_text)
                    merged = existing_themes | set(trait_themes)
                    if merged:
                        entity["themes"] = sorted(merged)
        except TimeoutError:
            timeout_hit = True

    duration_ms = int((time.time() - t0) * 1000)
    if telemetry is not None:
        telemetry.update({
            "source": "wikipedia",
            "duration_ms": duration_ms,
            "entity_count": len(batch),
            "success_count": success_count,
            "fail_count": fail_count,
            "timeout_hit": timeout_hit,
            "truncated": len(entities) > _MAX_ENTITIES,
        })
    logger.info("Enriched %d/%d entities in %dms (timeout: %s)",
                success_count, len(batch), duration_ms,
                "yes" if timeout_hit else "no")

    return enriched
